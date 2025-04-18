# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from paddle import nn
from paddle import optimizer as optim
from paddle import regularizer
from paddle.incubate import optimizer as incubate_optim
from typing_extensions import Literal

from ppsci.optimizer.soap import SOAP as SOAP_impl
from ppsci.utils import logger
from ppsci.utils import misc

if TYPE_CHECKING:
    import paddle

__all__ = ["SGD", "Momentum", "Adam", "RMSProp", "AdamW", "LBFGS", "OptimizerList"]


class SGD:
    """Stochastic Gradient Descent.

    Args:
        learning_rate (Union[float, optim.lr.LRScheduler], optional): The learning rate
            used to update parameter(s). Defaults to 0.001.
        weight_decay (Optional[Union[float, regularizer.L1Decay, regularizer.L2Decay]]):
            Regularization strategy. Defaults to None.
        grad_clip (Optional[Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]]):
            Gradient clipping strategy. Defaults to None.

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.SGD(1e-3)(model)
    """

    def __init__(
        self,
        learning_rate: Union[float, optim.lr.LRScheduler] = 0.001,
        weight_decay: Optional[
            Union[float, regularizer.L1Decay, regularizer.L2Decay]
        ] = None,
        grad_clip: Optional[
            Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]
        ] = None,
    ):
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.grad_clip = grad_clip

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = (
            sum([m.parameters() for m in model_list], []) if model_list else None
        )
        opt = optim.SGD(
            learning_rate=self.learning_rate,
            parameters=parameters,
            weight_decay=self.weight_decay,
            grad_clip=self.grad_clip,
        )
        return opt


class Momentum:
    """Simple Momentum optimizer with velocity state.

    Args:
        learning_rate (Union[float, optim.lr.LRScheduler]): The learning rate
            used to update parameter(s).
        momentum (float): Momentum factor.
        weight_decay (Optional[Union[float, regularizer.L1Decay, regularizer.L2Decay]]):
            Regularization strategy. Defaults to None.
        grad_clip (Optional[Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]]):
            Gradient clipping strategy. Defaults to None.
        use_nesterov (bool, optional): Whether to use nesterov momentum. Defaults to False.
        no_weight_decay_name (Optional[str]): List of names of no weight decay parameters split by white space. Defaults to None.

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.Momentum(1e-3, 0.9)(model)
    """

    def __init__(
        self,
        learning_rate: Union[float, optim.lr.LRScheduler],
        momentum: float,
        weight_decay: Optional[
            Union[float, regularizer.L1Decay, regularizer.L2Decay]
        ] = None,
        grad_clip: Optional[
            Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]
        ] = None,
        use_nesterov: bool = False,
        no_weight_decay_name: Optional[str] = None,
    ):
        super().__init__()
        self.learning_rate = learning_rate
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.grad_clip = grad_clip
        self.use_nesterov = use_nesterov
        self.no_weight_decay_name_list = (
            no_weight_decay_name.split() if no_weight_decay_name else []
        )

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = None
        if len(self.no_weight_decay_name_list) > 0:
            params_with_decay = []
            params_without_decay = []
            for m in model_list:
                params = [
                    p
                    for n, p in m.named_parameters()
                    if not any(nd in n for nd in self.no_weight_decay_name_list)
                ]
                params_with_decay.extend(params)
                params = [
                    p
                    for n, p in m.named_parameters()
                    if any(nd in n for nd in self.no_weight_decay_name_list)
                ]
                params_without_decay.extend(params)
            parameters = [
                {"params": params_with_decay, "weight_decay": self.weight_decay},
                {"params": params_without_decay, "weight_decay": 0.0},
            ]
        else:
            parameters = (
                sum([m.parameters() for m in model_list], []) if model_list else None
            )
        opt = optim.Momentum(
            learning_rate=self.learning_rate,
            momentum=self.momentum,
            weight_decay=self.weight_decay,
            grad_clip=self.grad_clip,
            use_nesterov=self.use_nesterov,
            parameters=parameters,
        )
        if hasattr(opt, "_use_multi_tensor"):
            opt = optim.Momentum(
                learning_rate=self.learning_rate,
                momentum=self.momentum,
                weight_decay=self.weight_decay,
                grad_clip=self.grad_clip,
                parameters=parameters,
                use_nesterov=self.use_nesterov,
                use_multi_tensor=True,
            )
        return opt


class Adam:
    """Adam: A Method for Stochastic Optimization.

    Args:
        learning_rate (Union[float, optim.lr.LRScheduler], optional): The learning rate
            used to update parameter(s). Defaults to 0.001.
        beta1 (float, optional): The exponential decay rate for the 1st moment estimates. Defaults to 0.9.
        beta2 (float, optional): The exponential decay rate for the 2nd moment estimates. Defaults to 0.999.
        epsilon (float, optional): A small float value for numerical stability. Defaults to 1e-08.
        weight_decay (Optional[Union[float, regularizer.L1Decay, regularizer.L2Decay]]): Regularization strategy. Defaults to None.
        grad_clip (Optional[Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]]): Gradient clipping strategy. Defaults to None.
        lazy_mode (bool, optional): Whether to enable lazy mode for moving-average. Defaults to False.
        amsgrad (bool, optional): Whether to use the AMSGrad variant of this algorithm from the paper
            `On the Convergence of Adam and Beyond <https://openreview.net/forum?id=ryQu7f-RZ>`_. Defaults to False.

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.Adam(1e-3)(model)
    """

    def __init__(
        self,
        learning_rate: Union[float, optim.lr.LRScheduler] = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-08,
        weight_decay: Optional[
            Union[float, regularizer.L1Decay, regularizer.L2Decay]
        ] = None,
        grad_clip: Optional[
            Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]
        ] = None,
        lazy_mode: bool = False,
        amsgrad: bool = False,
    ):
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.grad_clip = grad_clip
        self.lazy_mode = lazy_mode
        self.amsgrad = amsgrad

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = (
            sum([m.parameters() for m in model_list], []) if model_list else None
        )
        import inspect

        extra_kwargs = {}
        if "amsgrad" in inspect.signature(optim.Adam.__init__).parameters:
            extra_kwargs["amsgrad"] = self.amsgrad
        opt = optim.Adam(
            learning_rate=self.learning_rate,
            beta1=self.beta1,
            beta2=self.beta2,
            epsilon=self.epsilon,
            weight_decay=self.weight_decay,
            grad_clip=self.grad_clip,
            lazy_mode=self.lazy_mode,
            parameters=parameters,
            **extra_kwargs,
        )
        return opt


class LBFGS:
    """The L-BFGS is a quasi-Newton method for solving an unconstrained optimization
        problem over a differentiable function. Closely related is the Newton method for minimization.

    Args:
        learning_rate (float, optional): The learning rate
            used to update parameter(s). Defaults to 1.0.
        max_iter (int, optional): Maximal number of iterations per optimization step.
            Defaults to 1.
        max_eval (Optional[int]): Maximal number of function evaluations per
            optimization step. Defaults to None.
        tolerance_grad (float, optional): Termination tolerance on first order optimality.
            Defaults to 1e-07.
        tolerance_change (float, optional): Termination tolerance on function
            value/parameter changes. Defaults to 1e-09.
        history_size (int, optional): Update history size. Defaults to 100.
        line_search_fn (Optional[Literal["strong_wolfe"]]): Either 'strong_wolfe' or None.
            Defaults to "strong_wolfe".

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.LBFGS(1e-3)(model)
    """

    def __init__(
        self,
        learning_rate: float = 1.0,
        max_iter: int = 1,
        max_eval: Optional[int] = None,
        tolerance_grad: float = 1e-07,
        tolerance_change: float = 1e-09,
        history_size: int = 100,
        line_search_fn: Optional[Literal["strong_wolfe"]] = "strong_wolfe",
    ):
        self.lr = learning_rate
        self.max_iter = max_iter
        self.max_eval = max_eval
        self.tolerance_grad = tolerance_grad
        self.tolerance_change = tolerance_change
        self.history_size = history_size
        self.line_search_fn = line_search_fn

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = (
            sum([m.parameters() for m in model_list], []) if model_list else None
        )
        try:
            opt = getattr(optim, "LBFGS")(
                learning_rate=self.lr,
                max_iter=self.max_iter,
                max_eval=self.max_eval,
                tolerance_grad=self.tolerance_grad,
                tolerance_change=self.tolerance_change,
                history_size=self.history_size,
                line_search_fn=self.line_search_fn,
                parameters=parameters,
            )
        except AttributeError:
            opt = getattr(incubate_optim, "LBFGS")(
                learning_rate=self.lr,
                max_iter=self.max_iter,
                max_eval=self.max_eval,
                tolerance_grad=self.tolerance_grad,
                tolerance_change=self.tolerance_change,
                history_size=self.history_size,
                line_search_fn=self.line_search_fn,
                parameters=parameters,
            )
        return opt


class RMSProp:
    """Root Mean Squared Propagation (RMSProp) is an unpublished, adaptive learning rate method.

    Args:
        learning_rate (Union[float, optim.lr.LRScheduler]): The learning rate
            used to update parameter(s)
        rho (float, optional): Factor ρ in equation. Defaults to 0.95.
        epsilon (float, optional): Factor ϵ in equation as a smoothing term. Defaults to 1e-6.
        momentum (float, optional):β in equation is the momentum term. Defaults to 0.0.
        weight_decay (Optional[Union[float, regularizer.L1Decay, regularizer.L2Decay]]):
            Regularization strategy. Defaults to None.
        grad_clip (Optional[Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]]):
            Gradient clipping strategy. Defaults to None.

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.RMSProp(1e-3)(model)
    """

    def __init__(
        self,
        learning_rate: Union[float, optim.lr.LRScheduler],
        rho: float = 0.95,
        epsilon: float = 1e-6,
        momentum: float = 0.0,
        weight_decay: Optional[
            Union[float, regularizer.L1Decay, regularizer.L2Decay]
        ] = None,
        grad_clip: Optional[
            Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]
        ] = None,
    ):
        super().__init__()
        self.learning_rate = learning_rate
        self.momentum = momentum
        self.rho = rho
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.grad_clip = grad_clip

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = (
            sum([m.parameters() for m in model_list], []) if model_list else None
        )
        opt = optim.RMSProp(
            learning_rate=self.learning_rate,
            momentum=self.momentum,
            rho=self.rho,
            epsilon=self.epsilon,
            weight_decay=self.weight_decay,
            grad_clip=self.grad_clip,
            parameters=parameters,
        )
        return opt


class AdamW:
    """AdamW is implemented based on DECOUPLED WEIGHT DECAY REGULARIZATION.

    Args:
        learning_rate (Union[float, optim.lr.LRScheduler], optional): The learning rate
            used to update parameter(s). Defaults to 0.001.
        beta1 (float, optional): The exponential decay rate for the 1st moment estimates. Defaults to 0.9.
        beta2 (float, optional): The exponential decay rate for the 2nd moment estimates. Defaults to 0.999.
        epsilon (float, optional): A small float value for numerical stability. Defaults to 1e-8.
        weight_decay (float, optional): Regularization coefficient. Defaults to 0.01.
        grad_clip (Optional[Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]]): Gradient clipping strategy. Defaults to None.
        no_weight_decay_name (Optional[str]): List of names of no weight decay parameters split by white space. Defaults to None.
        one_dim_param_no_weight_decay (bool, optional): Apply no weight decay on 1-D parameter(s). Defaults to False.
        amsgrad (bool, optional): Whether to use the AMSGrad variant of this algorithm from the paper
            `On the Convergence of Adam and Beyond <https://openreview.net/forum?id=ryQu7f-RZ>`_. Defaults to False.

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.AdamW(1e-3)(model)
    """

    def __init__(
        self,
        learning_rate: Union[float, optim.lr.LRScheduler] = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
        weight_decay: float = 0.001,
        grad_clip: Optional[
            Union[nn.ClipGradByNorm, nn.ClipGradByValue, nn.ClipGradByGlobalNorm]
        ] = None,
        no_weight_decay_name: Optional[str] = None,
        one_dim_param_no_weight_decay: bool = False,
        amsgrad: bool = False,
    ):
        super().__init__()
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.grad_clip = grad_clip
        self.weight_decay = weight_decay
        self.no_weight_decay_name_list = (
            no_weight_decay_name.split() if no_weight_decay_name else []
        )
        self.one_dim_param_no_weight_decay = one_dim_param_no_weight_decay
        self.amsgrad = amsgrad

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = (
            sum([m.parameters() for m in model_list], []) if model_list else None
        )

        # TODO(gaotingquan): Model_list is None when in static graph, "no_weight_decay" not work.
        if model_list is None:
            if (
                self.one_dim_param_no_weight_decay
                or len(self.no_weight_decay_name_list) != 0
            ):
                msg = '"AdamW" does not support setting "no_weight_decay" in static graph. Please use dynamic graph.'
                logger.error(Exception(msg))
                raise Exception(msg)

        self.no_weight_decay_param_name_list = (
            [
                p.name
                for model in model_list
                for n, p in model.named_parameters()
                if any(nd in n for nd in self.no_weight_decay_name_list)
            ]
            if model_list
            else []
        )

        if self.one_dim_param_no_weight_decay:
            self.no_weight_decay_param_name_list += (
                [
                    p.name
                    for model in model_list
                    for n, p in model.named_parameters()
                    if len(p.shape) == 1
                ]
                if model_list
                else []
            )
        import inspect

        extra_kwargs = {}
        if "amsgrad" in inspect.signature(optim.AdamW.__init__).parameters:
            extra_kwargs["amsgrad"] = self.amsgrad

        opt = optim.AdamW(
            learning_rate=self.learning_rate,
            beta1=self.beta1,
            beta2=self.beta2,
            epsilon=self.epsilon,
            parameters=parameters,
            weight_decay=self.weight_decay,
            grad_clip=self.grad_clip,
            apply_decay_param_fun=self._apply_decay_param_fun,
            **extra_kwargs,
        )
        return opt

    def _apply_decay_param_fun(self, name):
        return name not in self.no_weight_decay_param_name_list


class SOAP:
    """
    Improving and Stabilizing Shampoo using Adam. Implements SOAP algorithm (https://arxiv.org/abs/2409.11321).

    Args:
        learning_rate (float, optional):
            The learning rate to use. defaults to 0.003.
        beta1 (float, optional):
            Adam's betas parameters beta1. defaults to 0.95.
        beta2 (float, optional):
            Adam's betas parameters beta2. defaults to 0.95.
        shampoo_beta (float, optional):
            If >= 0, use this beta for the preconditioner (L and R in paper, state['GG'] below) moving average instead of betas[1].
            defaults to -1.
        epsilon (float, optional):
            Adam's epsilon for numerical stability. defaults to 1e-08.
        weight_decay (float, optional): weight decay coefficient. defaults to 0.01.
        precondition_frequency (int, optional):
            How often to update the preconditioner. defaults to 10.
        max_precond_dim (int, optional):
            Maximum dimension of the preconditioner.
            Set to 10000, so that we exclude most common vocab sizes while including layers. defaults to 10000.
        merge_dims (bool, optional):
            Whether or not to merge dimensions of the preconditioner. defaults to `False`.
        precondition_1d (bool, optional):
            Whether or not to precondition 1D gradients. defaults to `False`.
        normalize_grads (bool, optional):
            Whether or not to normalize gradients per layer.
            Helps at large precondition_frequency (~100 in our experiments),
            but hurts performance at small precondition_frequency (~10 in our experiments). defaults to `False`.
        data_format (str, optional):
            Data format of the input for convolutional layers.
            Should be "channels_last" for data_format of NHWC and "channels_first" for NCHW. defaults to `channels_first`.
        correct_bias (bool, optional):
            Whether or not to use bias correction in Adam. defaults to `True`.

    Examples:
        >>> import ppsci
        >>> model = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt = ppsci.optimizer.SOAP(1e-3)(model)
    """

    def __init__(
        self,
        learning_rate: float = 3e-3,
        beta1: float = 0.95,
        beta2: float = 0.95,
        shampoo_beta: float = -1,
        epsilon: float = 1e-8,
        weight_decay: float = 0.01,
        precondition_frequency: int = 10,
        max_precond_dim: int = 10000,  #
        merge_dims: bool = False,  # Merge dimensions till the product of the dimensions is less than or equal to max_precond_dim.
        precondition_1d: bool = False,
        normalize_grads: bool = False,
        data_format: str = "channels_first",
        correct_bias: bool = True,
    ):
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.shampoo_beta = shampoo_beta
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.precondition_frequency = precondition_frequency
        self.max_precond_dim = max_precond_dim
        self.merge_dims = merge_dims
        self.precondition_1d = precondition_1d
        self.normalize_grads = normalize_grads
        self.data_format = data_format
        self.correct_bias = correct_bias

    def __call__(self, model_list: Union[nn.Layer, Tuple[nn.Layer, ...]]):
        # model_list is None in static graph
        if not isinstance(model_list, (tuple, list)):
            model_list = (model_list,)
        parameters = (
            sum([m.parameters() for m in model_list], []) if model_list else None
        )
        opt = SOAP_impl(
            parameters=parameters,
            learning_rate=self.learning_rate,
            beta1=self.beta1,
            beta2=self.beta2,
            shampoo_beta=self.shampoo_beta,
            epsilon=self.epsilon,
            weight_decay=self.weight_decay,
            precondition_frequency=self.precondition_frequency,
            max_precond_dim=self.max_precond_dim,
            merge_dims=self.merge_dims,
            precondition_1d=self.precondition_1d,
            normalize_grads=self.normalize_grads,
            data_format=self.data_format,
            correct_bias=self.correct_bias,
        )
        return opt


class OptimizerList:
    """OptimizerList which wrap more than one optimizer.
    NOTE: LBFGS is not supported yet.

    Args:
        optimizer_list (Tuple[optim.Optimizer, ...]): Optimizers listed in a tuple.

    Examples:
        >>> import ppsci
        >>> model1 = ppsci.arch.MLP(("x",), ("u",), 5, 20)
        >>> opt1 = ppsci.optimizer.Adam(1e-3)(model1)
        >>> model2 = ppsci.arch.MLP(("y",), ("v",), 5, 20)
        >>> opt2 = ppsci.optimizer.Adam(1e-3)(model2)
        >>> opt = ppsci.optimizer.OptimizerList((opt1, opt2))
    """

    def __init__(self, optimizer_list: Tuple[optim.Optimizer, ...]):
        super().__init__()
        self._opt_list = optimizer_list
        if "LBFGS" in set(misc.typename(opt) for opt in optimizer_list):
            raise ValueError("LBFGS is not supported in OptimizerList yet.")

    def step(self):
        for opt in self._opt_list:
            opt.step()

    def clear_grad(self):
        for opt in self._opt_list:
            opt.clear_grad()

    def get_lr(self) -> float:
        """Return learning rate of first optimizer"""
        return self._opt_list[0].get_lr()

    def set_state_dict(self, state_dicts: List[Dict[str, "paddle.Tensor"]]):
        for i, opt in enumerate(self._opt_list):
            opt.set_state_dict(state_dicts[i])

    def state_dict(self) -> List[Dict[str, "paddle.Tensor"]]:
        state_dicts = [opt.state_dict() for opt in self._opt_list]
        return state_dicts

    def __len__(self) -> int:
        return len(self._opt_list)

    def __getitem__(self, idx):
        return self._opt_list[idx]

    def __setitem__(self, idx, opt):
        raise NotImplementedError("Can not modify any item in OptimizerList.")

    def __iter__(self):
        yield from iter(self._opt_list)
