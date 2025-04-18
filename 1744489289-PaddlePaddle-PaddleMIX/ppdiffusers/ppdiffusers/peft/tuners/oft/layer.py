# coding=utf-8
# Copyright 2023-present the HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import warnings
from typing import Any, List, Optional, Set, Tuple

import paddle
import paddle.nn as nn

from ppdiffusers.peft.tuners.lycoris_utils import LycorisLayer


class OFTLayer(nn.Layer, LycorisLayer):
    # All names of layers that may contain adapter weights
    adapter_layer_names = ("oft_r",)
    # other_param_names is defined on parent class

    def __init__(self, base_layer: nn.Layer):
        super().__init__()
        LycorisLayer.__init__(self, base_layer)

        # OFT info
        self.oft_r = nn.ParameterDict({})
        self.coft = {}
        self.eps = {}
        self.block_share = {}

    @property
    def _available_adapters(self) -> Set[str]:
        return {*self.oft_r}

    def create_adapter_parameters(self, adapter_name: str, r: int, shape: Tuple[int, ...], block_share: bool):
        if block_share:
            self.oft_r[adapter_name] = nn.Parameter(
                paddle.empty([1, math.ceil(shape[0] / r), math.ceil(shape[0] / r)])
            )
        else:
            self.oft_r[adapter_name] = nn.Parameter(
                paddle.empty([r, math.ceil(shape[0] / r), math.ceil(shape[0] / r)])
            )

    def reset_adapter_parameters(self, adapter_name: str):
        nn.init.zeros_(self.oft_r[adapter_name])

    def reset_adapter_parameters_random(self, adapter_name: str):
        nn.init.kaiming_uniform_(self.oft_r[adapter_name], a=math.sqrt(5))

    def update_layer(
        self,
        adapter_name: str,
        r: int,
        module_dropout: float,
        init_weights: bool,
        coft: bool = False,
        eps: float = 6e-5,
        block_share: bool = False,
        **kwargs,
    ) -> None:
        """Internal function to create oft adapter

        Args:
            adapter_name (`str`): Name for the adapter to add.
            r (`int`): Rank for the added adapter.
            module_dropout (`float`): The dropout probability for disabling adapter during training.
            init_weights (`bool`): Whether to initialize weights.
            coft (`bool`): Whether to use the constrained variant of OFT or not.
            eps (`float`):
                The control strength of COFT. The freedom of rotation. Only has an effect if `coft` is set to True.
            block_share (`bool`): Whether to share the OFT parameters between blocks or not.
        """

        self.r[adapter_name] = r
        self.module_dropout[adapter_name] = module_dropout
        self.coft[adapter_name] = coft
        self.block_share[adapter_name] = block_share

        # Determine shape of OFT weights
        base_layer = self.get_base_layer()
        if isinstance(base_layer, nn.Linear):
            shape = tuple(base_layer.weight.shape)[::-1]
        elif isinstance(base_layer, nn.Conv2D):
            shape = (
                base_layer._out_channels,
                base_layer._in_channels * base_layer._kernel_size[0] * base_layer._kernel_size[1],
            )
        else:
            raise TypeError(f"OFT is not implemented for base layers of type {type(base_layer).__name__}")

        self.eps[adapter_name] = eps * math.ceil(shape[0] / r) * math.ceil(shape[0] / r)

        # Create weights with provided shape
        self.create_adapter_parameters(adapter_name, r, shape, block_share)

        # Initialize weights
        if init_weights:
            self.reset_adapter_parameters(adapter_name)
        else:
            self.reset_adapter_parameters_random(adapter_name)

        # Move new weights to device
        weight = getattr(self.get_base_layer(), "weight", None)
        if weight is not None:
            # the layer is already completely initialized, this is an update
            if paddle.is_floating_point(weight) or paddle.is_complex(weight):
                self.to(dtype=weight.dtype)

        self.set_adapter(self.active_adapters)

    def unscale_layer(self, scale=None) -> None:
        # scale is not used
        pass

    @paddle.no_grad()
    def merge(self, safe_merge: bool = False, adapter_names: Optional[List[str]] = None) -> None:
        """
        Merge the active adapter weights into the base weights

        Args:
            safe_merge (`bool`, *optional*):
                If `True`, the merge operation will be performed in a copy of the original weights and check for NaNs
                before merging the weights. This is useful if you want to check if the merge operation will produce
                NaNs. Defaults to `False`.
            adapter_names (`List[str]`, *optional*):
                The list of adapter names that should be merged. If `None`, all active adapters will be merged.
                Defaults to `None`.
        """
        if self.merged:
            warnings.warn(
                f"Already following adapters were merged {','.join(self.merged_adapters)}. "
                f"You are now additionally merging {','.join(self.active_adapters)}."
            )
        if adapter_names is None:
            adapter_names = self.active_adapters

        for active_adapter in adapter_names:
            if active_adapter in self._available_adapters:
                base_layer = self.get_base_layer()

                orig_weights = base_layer.weight.data

                if isinstance(base_layer, nn.Linear):
                    # do nothing
                    pass
                elif isinstance(base_layer, nn.Conv2D):
                    orig_weights = orig_weights.reshape(
                        [
                            base_layer._out_channels,
                            base_layer._in_channels * base_layer._kernel_size[0] * base_layer._kernel_size[1],
                        ]
                    )
                    orig_weights = orig_weights.T
                delta_weight = self.get_delta_weight(active_adapter)
                if orig_weights.shape[1] != delta_weight.shape[1]:
                    # when in channels is not divisible by r
                    delta_weight = delta_weight[: orig_weights.shape[1], : orig_weights.shape[1]]
                new_weights = paddle.mm(orig_weights, delta_weight)  # in,out x out,in

                if isinstance(base_layer, nn.Linear):
                    # do nothing
                    pass
                elif isinstance(base_layer, nn.Conv2D):
                    new_weights = new_weights.T
                    new_weights = new_weights.reshape(
                        [
                            base_layer._out_channels,
                            base_layer._in_channels,
                            base_layer._kernel_size[0],
                            base_layer._kernel_size[1],
                        ]
                    )

                if safe_merge and not paddle.isfinite(new_weights).all():
                    raise ValueError(
                        f"NaNs detected in the merged weights. The adapter {active_adapter} seems to be broken"
                    )

                base_layer.weight.data = new_weights
                self.merged_adapters.append(active_adapter)

    @paddle.no_grad()
    def unmerge(self) -> None:
        """
        This method unmerges all merged adapter layers from the base weights.
        """
        if not self.merged:
            warnings.warn("Already unmerged. Nothing to do.")
            return
        while len(self.merged_adapters) > 0:
            active_adapter = self.merged_adapters.pop()
            if active_adapter in self._available_adapters:
                base_layer = self.get_base_layer()
                new_weights = base_layer.weight.data
                if isinstance(base_layer, nn.Linear):
                    # do nothing
                    pass
                elif isinstance(base_layer, nn.Conv2D):
                    new_weights = new_weights.reshape(
                        [
                            base_layer._out_channels,
                            base_layer._in_channels * base_layer._kernel_size[0] * base_layer._kernel_size[1],
                        ]
                    )
                    new_weights = new_weights.T

                delta_weight = self.get_delta_weight(active_adapter)
                if new_weights.shape[1] != delta_weight.shape[1]:
                    # when in channels is not divisible by r
                    delta_weight = delta_weight[: new_weights.shape[1], : new_weights.shape[1]]
                delta_inv = paddle.inverse(delta_weight)
                orig_weights = paddle.mm(new_weights, delta_inv)

                if isinstance(base_layer, nn.Linear):
                    # do nothing
                    pass
                elif isinstance(base_layer, nn.Conv2D):
                    orig_weights = orig_weights.T
                    orig_weights = orig_weights.reshape(
                        [
                            base_layer._out_channels,
                            base_layer._in_channels,
                            base_layer._kernel_size[0],
                            base_layer._kernel_size[1],
                        ]
                    )
                base_layer.weight.data = orig_weights

    def get_delta_weight(self, adapter_name: str) -> paddle.Tensor:
        rank = self.r[adapter_name]
        coft = self.coft[adapter_name]
        eps = self.eps[adapter_name]
        opt_r = self.oft_r[adapter_name]

        if coft:
            with paddle.no_grad():
                opt_r.copy_(self._project_batch(opt_r, eps=eps), False)

        orth_rotate = self._cayley_batch(opt_r)
        weight = self._block_diagonal(orth_rotate, rank)

        return weight

    # Copied from https://github.com/Zeju1997/oft/blob/84cebb965df69781e3d9c3c875f5980b421eaf24/oft-control/oft.py#L144
    def _cayley_batch(self, data: paddle.Tensor) -> paddle.Tensor:
        b, r, c = data.shape
        # Ensure the input matrix is skew-symmetric
        skew = 0.5 * (data - data.transpose([0, 2, 1]))
        I = paddle.eye(r, dtype=skew.dtype).unsqueeze(0).expand([b, r, c])

        # Perform the Cayley parametrization
        Q = paddle.bmm(I - skew, paddle.inverse(I + skew))

        return Q

    # Copied from https://github.com/Zeju1997/oft/blob/84cebb965df69781e3d9c3c875f5980b421eaf24/oft-control/oft.py#L155
    def _block_diagonal(self, oft_r: paddle.Tensor, rank: int) -> paddle.Tensor:
        if oft_r.shape[0] == 1:
            # block share
            blocks = [oft_r[0, ...] for i in range(rank)]
        else:
            blocks = [oft_r[i, ...] for i in range(rank)]

        # Use torch.block_diag to create the block diagonal matrix
        from scipy.linalg import block_diag

        A = paddle.to_tensor(block_diag(*blocks))

        return A

    # Copied from https://github.com/Zeju1997/oft/blob/84cebb965df69781e3d9c3c875f5980b421eaf24/oft-control/oft.py#L52
    def _project_batch(self, oft_r, eps=1e-5):
        # scaling factor for each of the smaller block matrix
        eps = eps * 1 / paddle.sqrt(paddle.to_tensor(oft_r.shape[0]))
        I = paddle.zeros((oft_r.shape[1], oft_r.shape[1]), dtype=oft_r.dtype).unsqueeze(0).expand_as(oft_r)
        diff = oft_r - I
        norm_diff = paddle.norm(oft_r - I, axis=(1, 2), keepdim=True)
        mask = (norm_diff <= eps).cast("bool")
        out = paddle.where(mask, oft_r, I + eps * (diff / norm_diff))
        return out

    def forward(self, x: paddle.Tensor, *args, **kwargs) -> paddle.Tensor:
        previous_dtype = x.dtype

        if self.disable_adapters:
            if self.merged:
                self.unmerge()
            result = self.base_layer(x, *args, **kwargs)
        elif self.merged:
            result = self.base_layer(x, *args, **kwargs)
        else:
            result = self.base_layer(x, *args, **kwargs)
            if len(result.shape) == 4:
                result = result.transpose([0, 2, 3, 1])

            base_layer = self.get_base_layer()
            base_bias = base_layer.bias
            if base_bias is not None:
                # Bias should be added after OFT forward
                result = result - base_bias.data

            # Execute all the adapters
            for active_adapter in self.active_adapters:
                if active_adapter not in self._available_adapters:
                    continue

                module_dropout = self.module_dropout[active_adapter]

                # Modify current execution weights
                if (not self.training) or (self.training and paddle.rand(1) > module_dropout):
                    result = self._get_delta_activations(active_adapter, result, *args, **kwargs)

            if base_bias is not None:
                result = result + base_bias.data
            if len(result.shape) == 4:
                result = result.transpose([0, 3, 1, 2])

        result = result.cast(dtype=previous_dtype)
        return result


class Linear(OFTLayer):
    """OFT implemented in Linear layer"""

    def __init__(
        self,
        base_layer: nn.Layer,
        adapter_name: str = "default",
        r: int = 0,
        module_dropout: float = 0.0,
        init_weights: bool = True,
        **kwargs,
    ):
        super().__init__(base_layer)

        # Create adapter and set it active
        self._active_adapter = adapter_name
        self.update_layer(adapter_name, r, module_dropout, init_weights, **kwargs)

    def _get_delta_activations(
        self, adapter_name: str, input: paddle.Tensor, *args: Any, **kwargs: Any
    ) -> paddle.Tensor:
        delta_weight = self.get_delta_weight(adapter_name)

        base_layer = self.get_base_layer()
        base_weight = base_layer.weight.data
        delta_weight = delta_weight[: base_weight.shape[1], : base_weight.shape[1]]

        # don't add bias here, because the bias will be added after OFT forward
        return paddle.matmul(input, delta_weight)

    def __repr__(self) -> str:
        rep = super().__repr__()
        return "oft." + rep


class Conv2d(OFTLayer):
    """OFT implemented in Conv2d layer"""

    def __init__(
        self,
        base_layer: nn.Layer,
        adapter_name: str = "default",
        r: int = 0,
        module_dropout: float = 0.0,
        init_weights: bool = True,
        **kwargs,
    ):
        super().__init__(base_layer)

        # Create adapter and set it active
        self._active_adapter = adapter_name
        self.update_layer(adapter_name, r, module_dropout, init_weights, **kwargs)

    def _get_delta_activations(
        self, adapter_name: str, input: paddle.Tensor, *args: Any, **kwargs: Any
    ) -> paddle.Tensor:
        delta_weight = self.get_delta_weight(adapter_name)

        base_layer = self.get_base_layer()
        base_weight = base_layer.weight.data
        delta_weight = delta_weight[: base_weight.shape[0], : base_weight.shape[0]]

        # don't add bias here, because the bias will be added after OFT forward
        return paddle.matmul(input, delta_weight)

    def __repr__(self) -> str:
        rep = super().__repr__()
        return "oft." + rep
