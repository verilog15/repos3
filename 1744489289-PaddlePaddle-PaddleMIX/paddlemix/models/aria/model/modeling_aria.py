# Copyright (c) 2024 PaddlePaddle Authors. All Rights Reserved.
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

import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import paddle

from paddlenlp.transformers.model_utils import PretrainedModel
from paddlenlp.transformers.model_outputs import ModelOutput

from .configuration_aria import AriaConfig
from .moe_lm import AriaMoELMForCausalLM
from .projector import AriaProjector
from .vision_encoder import AriaVisionModel

logger = paddle.utils.try_import("logging").getLogger(name=__name__)


class AriaPretrainedModel(PretrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained models.
    """

    config_class = AriaConfig
    base_model_prefix = "model"
    _no_split_modules = []
    supports_gradient_checkpointing = True
    _skip_keys_device_placement = "past_key_values"
    _supports_flash_attn_2 = True
    _supports_cache_class = True
    _supports_static_cache = True

    @property
    def _supports_sdpa(self):
        """
        Retrieve language_model's attribute to check whether the model supports
        SDPA (Scaled Dot Product Attention) or not.
        """
        return self.language_model._supports_sdpa


@dataclass
class AriaCausalLMOutputWithPast(ModelOutput):
    """
    Base class for Aria causal language model (or autoregressive) outputs.

    Args:
        loss (`torch.FloatTensor` of shape `(1,)`, *optional*, returned when `labels` is provided):
            Language modeling loss (for next-token prediction).
        logits (`torch.FloatTensor` of shape `(batch_size, sequence_length, config.vocab_size)`):
            Prediction scores of the language modeling head (scores for each vocabulary token before SoftMax).
        past_key_values (`tuple(tuple(torch.FloatTensor))`, *optional*, returned when `use_cache=True` is passed or when `config.use_cache=True`):
            Tuple of `tuple(torch.FloatTensor)` of length `config.n_layers`, with each tuple having 2 tensors of shape
            `(batch_size, num_heads, sequence_length, embed_size_per_head)`)

            Contains pre-computed hidden-states (key and values in the self-attention blocks) that can be used (see
            `past_key_values` input) to speed up sequential decoding.
        hidden_states (`tuple(torch.FloatTensor)`, *optional*, returned when `output_hidden_states=True` is passed or when `config.output_hidden_states=True`):
            Tuple of `torch.FloatTensor` (one for the output of the embeddings, if the model has an embedding layer, +
            one for the output of each layer) of shape `(batch_size, sequence_length, hidden_size)`.

            Hidden-states of the model at the output of each layer plus the optional initial embedding outputs.
        attentions (`tuple(torch.FloatTensor)`, *optional*, returned when `output_attentions=True` is passed or when `config.output_attentions=True`):
            Tuple of `torch.FloatTensor` (one for each layer) of shape `(batch_size, num_heads, sequence_length,
            sequence_length)`.

            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.
        image_hidden_states (`tuple(torch.FloatTensor)`, *optional*):
            Tuple of `torch.FloatTensor` (one for the output of the image embeddings, `(batch_size, num_images,
            sequence_length, hidden_size)`.

            image_hidden_states of the model produced by the vision encoder, and optionally by the perceiver
    """

    loss: Optional[paddle.Tensor] = None
    logits: paddle.float32 = None
    past_key_values: Optional[List[paddle.Tensor]] = None
    hidden_states: Optional[Tuple[paddle.Tensor]] = None
    attentions: Optional[Tuple[paddle.Tensor]] = None
    image_hidden_states: Optional[Tuple[paddle.Tensor]] = None


def build_mm_projector(config: AriaConfig):
    """
    Builds and returns an AriaProjector instance based on the provided configuration.

    Args:
        config (AriaConfig): The configuration object containing necessary parameters.

    Returns:
        AriaProjector: An instance of the AriaProjector class.
    """
    return AriaProjector(
        patch_to_query_dict=config.projector_patch_to_query_dict,
        embed_dim=config.vision_config.hidden_size,
        num_heads=config.vision_config.num_attention_heads,
        kv_dim=config.vision_config.hidden_size,
        ff_dim=config.text_config.hidden_size,
        output_dim=config.text_config.hidden_size,
    )


class AriaForConditionalGeneration(AriaPretrainedModel):
    """
    Aria model for conditional generation tasks.

    This model combines a vision tower, a multi-modal projector, and a language model
    to perform tasks that involve both image and text inputs.
    """

    def __init__(self, config: AriaConfig):
        super().__init__(config)
        self.vision_tower = AriaVisionModel(config.vision_config)
        self.multi_modal_projector = build_mm_projector(config)
        self.vocab_size = config.text_config.vocab_size
        self.language_model = AriaMoELMForCausalLM(config.text_config)
        self.pad_token_id = (
            self.config.pad_token_id if self.config.pad_token_id is not None else -1
        )
        # self.post_init()
        self.use_pixel_values = False

    def freeze_vit(self):
        """Freeze the parameters of the vision tower."""
        for param in self.vision_tower.parameters():
            param.stop_gradient = not False

    def freeze_projector(self):
        """Freeze the parameters of the multi-modal projector."""
        for param in self.multi_modal_projector.parameters():
            param.stop_gradient = not False

    def freeze_llm(self):
        """Freeze the parameters of the language model."""
        for param in self.language_model.parameters():
            param.stop_gradient = not False

    def get_input_embeddings(self) -> paddle.nn.Layer:
        """Retrieve the input embeddings from the language model."""
        return self.language_model.get_input_embeddings()

    def set_input_embeddings(self, value):
        """Set the input embeddings for the language model."""
        self.language_model.set_input_embeddings(value)

    def get_output_embeddings(self):
        """Retrieve the output embeddings from the language model."""
        return self.language_model.get_output_embeddings()

    def set_output_embeddings(self, value):
        """Set the output embeddings for the language model."""
        self.language_model.set_output_embeddings(value)

    def set_moe_z_loss_coeff(self, value):
        """
        Set the z-loss coefficient for Mixture of Experts (MoE) models.

        Args:
            value: The z-loss coefficient value to set.
        """
        self.language_model.set_z_loss_coeff(value)

    def set_moe_aux_loss_coeff(self, value):
        """
        Set the auxiliary loss coefficient for Mixture of Experts (MoE) models.

        Args:
            value: The auxiliary loss coefficient value to set.
        """
        self.language_model.set_aux_loss_coeff(value)

    def forward(
        self,
        input_ids: paddle.Tensor = None,
        pixel_values: paddle.Tensor = None,
        pixel_mask: paddle.Tensor = None,
        attention_mask: Optional[paddle.Tensor] = None,
        position_ids: Optional[paddle.Tensor] = None,
        past_key_values: Optional[List[paddle.Tensor]] = None,
        inputs_embeds: Optional[paddle.Tensor] = None,
        labels: Optional[paddle.Tensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        cache_position: Optional[paddle.Tensor] = None,
        num_logits_to_keep: int = 0,
    ) -> Union[Tuple, AriaCausalLMOutputWithPast]:
        """
        Forward pass of the AriaForConditionalGeneration model.

        This method processes both text and image inputs, merges them if necessary,
        and generates output using the language model.

        Args:
            input_ids (torch.LongTensor, optional): Input token ids.
            pixel_values (torch.FloatTensor, optional): Pixel values of the images.
            pixel_mask (torch.LongTensor, optional): Mask for the pixel values.
            attention_mask (torch.Tensor, optional): Attention mask.
            position_ids (torch.LongTensor, optional): Position ids.
            past_key_values (List[torch.FloatTensor], optional): Past key values for efficient processing.
            inputs_embeds (torch.FloatTensor, optional): Input embeddings.
            labels (torch.LongTensor, optional): Labels for computing the language modeling loss.
            use_cache (bool, optional): Whether to use the model's cache mechanism.
            output_attentions (bool, optional): Whether to output attention weights.
            output_hidden_states (bool, optional): Whether to output hidden states.
            return_dict (bool, optional): Whether to return a ModelOutput object.

        Returns:
            Union[Tuple, AriaCausalLMOutputWithPast]: Model outputs.
        """
        return_dict = True if return_dict is None else return_dict
        output_attentions = (
            output_attentions
            if output_attentions is not None
            else self.config.output_attentions
        )
        output_hidden_states = (
            output_hidden_states
            if output_hidden_states is not None
            else self.config.output_hidden_states
        )
        return_dict = (
            return_dict if return_dict is not None else self.config.use_return_dict
        )
        if inputs_embeds is None:
            inputs_embeds = self.get_input_embeddings()(input_ids)
        image_features = None
        if pixel_values is not None:
            image_outputs, image_attn_mask = self.vision_tower(
                pixel_values, pixel_mask=pixel_mask, return_dict=True
            )
            selected_image_feature = image_outputs.last_hidden_state
            image_features = self.multi_modal_projector(
                selected_image_feature, attn_mask=image_attn_mask
            )
        if image_features is not None:
            n_image_tokens = (input_ids == self.config.image_token_index).sum().item()
            n_image_features = (
                tuple(image_features.shape)[0] * tuple(image_features.shape)[1]
            )
            if n_image_tokens != n_image_features:
                raise ValueError(
                    f"Image features and image tokens do not match: tokens: {n_image_tokens}, features {n_image_features}"
                )
            special_image_mask = (
                (input_ids == self.config.image_token_index)
                .unsqueeze(axis=-1)
                .expand_as(y=inputs_embeds)
                .to(inputs_embeds.place)
            )
            image_features = image_features.to(inputs_embeds.place, inputs_embeds.dtype)
#             """Class Method: *.masked_scatter, can not convert, please check whether it is torch.Tensor.*/Optimizer.*/nn.Module.*/torch.distributions.Distribution.*/torch.autograd.function.FunctionCtx.*/torch.profiler.profile.*/torch.autograd.profiler.profile.*, and convert manually"""
# >>>>>>            inputs_embeds = inputs_embeds.masked_scatter(
#                 special_image_mask, image_features
#             )

            # 将PyTorch的masked_scatter转换为Paddle实现
            # 创建一个填充后的 image_features
            padded_image_features = paddle.zeros_like(inputs_embeds)  # [1, 287, 2560]
            padded_image_features[:, :256, :] = image_features

            masked_inputs = paddle.where(
                special_image_mask,
                padded_image_features,
                inputs_embeds
            )

            inputs_embeds = masked_inputs
        
        # dtype


        # Fix 
        outputs = self.language_model(
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
            # cache_position=cache_position,
            # num_logits_to_keep=num_logits_to_keep,
        )
        logits = outputs[0]
        loss = None
        if labels is not None:
            if attention_mask is not None:
                shift_attention_mask = attention_mask[
                    :, -(tuple(logits.shape)[1] - 1) :
                ].to(logits.place)
                shift_logits = logits[..., :-1, :][
                    shift_attention_mask.to(logits.place) != 0
                ].contiguous()
                shift_labels = labels[..., 1:][
                    shift_attention_mask.to(labels.place) != 0
                ].contiguous()
            else:
                shift_logits = logits[..., :-1, :].contiguous()
                shift_labels = labels[..., 1:].contiguous()
            loss_fct = paddle.nn.CrossEntropyLoss()
            loss = loss_fct(
                shift_logits.view(-1, shift_logits.shape[-1]),
                shift_labels.view(-1).to(shift_logits.place),
            )
        if not return_dict:
            output = (logits,) + outputs[1:]
            return (loss,) + output if loss is not None else output
        return AriaCausalLMOutputWithPast(
            loss=loss,
            logits=logits,
            past_key_values=outputs.past_key_values,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

    def prepare_inputs_for_generation(
        self,
        input_ids,
        past_key_values=None,
        inputs_embeds=None,
        pixel_values=None,
        pixel_mask=None,
        attention_mask=None,
        cache_position=None,
        num_logits_to_keep=None,
        **kwargs,
    ):
        model_inputs = self.language_model.prepare_inputs_for_generation(
            input_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            cache_position=cache_position,
            num_logits_to_keep=num_logits_to_keep,
            **kwargs,
        )
        # if cache_position[0] == 0:
        #     model_inputs["pixel_values"] = pixel_values
        #     model_inputs["pixel_mask"] = pixel_mask
        # if  model_inputs["pixel_values"]
        if not self.use_pixel_values:
            model_inputs["pixel_values"] = pixel_values
            model_inputs["pixel_mask"] = pixel_mask
            self.use_pixel_values = True
        else:
            pass

        return model_inputs
