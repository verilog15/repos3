# coding=utf-8
# Copyright 2024 HuggingFace Inc.
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

import unittest

import numpy as np
import paddle
from ppdiffusers.transformers import AutoTokenizer, CLIPTextConfig, CLIPTextModelWithProjection, CLIPTokenizer, T5EncoderModel

from ppdiffusers import (
    AutoencoderKL,
    FlowMatchEulerDiscreteScheduler,
    SD3Transformer2DModel,
    StableDiffusion3ControlNetInpaintingPipeline,
)
from ppdiffusers.models import SD3ControlNetModel
from ppdiffusers.utils.testing_utils import (
    enable_full_determinism,
)
from ppdiffusers.utils import randn_tensor

from ..test_pipelines_common import PipelineTesterMixin


enable_full_determinism()


class StableDiffusion3ControlInpaintNetPipelineFastTests(unittest.TestCase, PipelineTesterMixin):
    pipeline_class = StableDiffusion3ControlNetInpaintingPipeline
    params = frozenset(
        [
            "prompt",
            "height",
            "width",
            "guidance_scale",
            "negative_prompt",
            "prompt_embeds",
            "negative_prompt_embeds",
        ]
    )
    batch_params = frozenset(["prompt", "negative_prompt"])

    def get_dummy_components(self):
        paddle.seed(seed=0)
        transformer = SD3Transformer2DModel(
            sample_size=32,
            patch_size=1,
            in_channels=8,
            num_layers=4,
            attention_head_dim=8,
            num_attention_heads=4,
            joint_attention_dim=32,
            caption_projection_dim=32,
            pooled_projection_dim=64,
            out_channels=8,
        )

        paddle.seed(seed=0)
        controlnet = SD3ControlNetModel(
            sample_size=32,
            patch_size=1,
            in_channels=8,
            num_layers=1,
            attention_head_dim=8,
            num_attention_heads=4,
            joint_attention_dim=32,
            caption_projection_dim=32,
            pooled_projection_dim=64,
            out_channels=8,
            extra_conditioning_channels=1,
        )
        clip_text_encoder_config = CLIPTextConfig(
            bos_token_id=0,
            eos_token_id=2,
            hidden_size=32,
            intermediate_size=37,
            layer_norm_eps=1e-05,
            num_attention_heads=4,
            num_hidden_layers=5,
            pad_token_id=1,
            vocab_size=1000,
            hidden_act="gelu",
            projection_dim=32,
        )

        paddle.seed(seed=0)
        text_encoder = CLIPTextModelWithProjection(clip_text_encoder_config)

        paddle.seed(seed=0)
        text_encoder_2 = CLIPTextModelWithProjection(clip_text_encoder_config)

        paddle.seed(seed=0)
        text_encoder_3 = T5EncoderModel.from_pretrained("hf-internal-testing/tiny-random-t5")

        tokenizer = CLIPTokenizer.from_pretrained("hf-internal-testing/tiny-random-clip")
        tokenizer_2 = CLIPTokenizer.from_pretrained("hf-internal-testing/tiny-random-clip")
        tokenizer_3 = AutoTokenizer.from_pretrained("hf-internal-testing/tiny-random-t5")

        paddle.seed(seed=0)
        vae = AutoencoderKL(
            sample_size=32,
            in_channels=3,
            out_channels=3,
            block_out_channels=(4,),
            layers_per_block=1,
            latent_channels=8,
            norm_num_groups=1,
            use_quant_conv=False,
            use_post_quant_conv=False,
            shift_factor=0.0609,
            scaling_factor=1.5035,
        )

        scheduler = FlowMatchEulerDiscreteScheduler()

        return {
            "scheduler": scheduler,
            "text_encoder": text_encoder,
            "text_encoder_2": text_encoder_2,
            "text_encoder_3": text_encoder_3,
            "tokenizer": tokenizer,
            "tokenizer_2": tokenizer_2,
            "tokenizer_3": tokenizer_3,
            "transformer": transformer,
            "vae": vae,
            "controlnet": controlnet,
        }

    def get_dummy_inputs(self, seed=0):
        generator = paddle.Generator().manual_seed(seed)
        control_image = randn_tensor(
            (1, 3, 32, 32),
            generator=generator,
            dtype=paddle.float16,
        )

        control_mask = randn_tensor(
            (1, 1, 32, 32),
            generator=generator,
            dtype=paddle.float16,
        )

        controlnet_conditioning_scale = 0.95

        inputs = {
            "prompt": "A painting of a squirrel eating a burger",
            "generator": generator,
            "num_inference_steps": 2,
            "guidance_scale": 7.0,
            "output_type": "np",
            "control_image": control_image,
            "control_mask": control_mask,
            "controlnet_conditioning_scale": controlnet_conditioning_scale,
        }

        return inputs

    def test_controlnet_inpaint_sd3(self):
        components = self.get_dummy_components()
        sd_pipe = StableDiffusion3ControlNetInpaintingPipeline(**components)
        sd_pipe.set_progress_bar_config(disable=None)

        inputs = self.get_dummy_inputs()
        output = sd_pipe(**inputs)
        image = output.images

        image_slice = image[0, -3:, -3:, -1]

        assert image.shape == (1, 32, 32, 3)

        expected_slice = np.array(
            [0.66951287, 0.10724381, 0.5473986,  0.15890905, 0.52206504, 0.44725734, 0.31528556, 0.41522938, 0.50141734]
        )

        assert (
            np.abs(image_slice.flatten() - expected_slice).max() < 1e-2
        ), f"Expected: {expected_slice}, got: {image_slice.flatten()}"

    @unittest.skip("xFormersAttnProcessor does not work with SD3 Joint Attention")
    def test_xformers_attention_forwardGenerator_pass(self):
        pass
