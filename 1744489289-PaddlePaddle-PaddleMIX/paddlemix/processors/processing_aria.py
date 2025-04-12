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

import inspect
import logging
from typing import List, Optional, Union

from paddlenlp.transformers import LlamaTokenizer 
from paddlenlp.transformers.feature_extraction_utils import BatchFeature
from paddlenlp.transformers.image_utils import ImageInput
from paddlenlp.transformers.processing_utils import ProcessorMixin
from paddlenlp.transformers.tokenizer_utils_base import (
    PaddingStrategy,
    PreTokenizedInput,
    TensorType,       
    TextInput,
    TruncationStrategy,
)

from ..models.aria.model.vision_processor import AriaVisionProcessor

logger = logging.getLogger(__name__)

class AriaLlamaTokenizer(LlamaTokenizer):
    resource_files_names = {
        "vocab_file": "tokenizer.model",
    }

class AriaProcessor(ProcessorMixin):
    """
    AriaProcessor is a processor for the Aria model which wraps the Aria image preprocessor and the LLama slow tokenizer.
    Args:
        image_processor(AriaVisionProcessor): The AriaVisionProcessor to use for image preprocessing.
        tokenizer(AutoTokenizer): The AutoTokenizer to use for tokenizing the text.
        patch_size(int): The patch size to use for the image processor.
        chat_template(str): The chat template to use for the tokenizer.
        image_token(str): The image token to use for the tokenizer.
    """

    attributes = []
    valid_kwargs = ["chat_template", "patch_size", "image_token"]
    image_processor_class = None
    tokenizer_class = "LlamaTokenizer"
    

    def __init__(
        self,
        image_processor: AriaVisionProcessor = None,
        tokenizer: Union[AriaLlamaTokenizer, str] = None,
        patch_size: int = 490,
        chat_template: str = None,
        image_token: str = "<|img|>",
    ):
        super().__init__()
        self.chat_template = chat_template 
        if image_processor is None:
            self.image_processor = AriaVisionProcessor(max_image_size=patch_size)
        else:
            self.image_processor = image_processor
        if isinstance(tokenizer, str):
            self.tokenizer = AriaLlamaTokenizer.from_pretrained(
                tokenizer, trust_remote_code=True, use_fast=False
            )
        else:
            self.tokenizer = tokenizer
        if self.tokenizer is not None and self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.unk_token
        self.image_token = image_token

    def __call__(
        self,
        text: Union[
            TextInput,
            PreTokenizedInput,
            List[TextInput],
            List[PreTokenizedInput],
        ],
        images: ImageInput = None,
        padding: Union[
            bool, str, PaddingStrategy
        ] = False,
        truncation: Union[
            bool, str, TruncationStrategy
        ] = None,
        max_length: Optional[int] = None,
        max_image_size: Optional[int] = 980,
        split_image: Optional[bool] = False,
        return_tensors: Optional[
            Union[str, TensorType]
        ] = TensorType.PADDLE,  #PYTORCH,
        return_final_prompts: Optional[bool] = False,
    ) -> BatchFeature:
        """
        Main method to prepare for the model one or several sequences(s) and image(s). Please refer to the doctsring
        of the above two methods for more information.

        Args:
            text (`str`, `List[str]`, `List[List[str]]`):
                The sequence or batch of sequences to be encoded. Each sequence can be a string or a list of strings
                (pretokenized string). If the sequences are provided as list of strings (pretokenized), you must set
                `is_split_into_words=True` (to lift the ambiguity with a batch of sequences).
            images (`PIL.Image.Image`, `np.ndarray`, `torch.Tensor`, `List[PIL.Image.Image]`, `List[np.ndarray]`, `List[torch.Tensor]`):
                The image or batch of images to be prepared. Each image can be a PIL image, NumPy array or PyTorch
                tensor. Both channels-first and channels-last formats are supported.
            padding (`bool`, `str` or [`~utils.PaddingStrategy`], *optional*, defaults to `False`):
                Select a strategy to pad the returned sequences (according to the model's padding side and padding
                index) among:
                - `True` or `'longest'`: Pad to the longest sequence in the batch (or no padding if only a single
                  sequence if provided).
                - `'max_length'`: Pad to a maximum length specified with the argument `max_length` or to the maximum
                  acceptable input length for the model if that argument is not provided.
                - `False` or `'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of different
                  lengths).
            max_length (`int`, *optional*):
                Maximum length of the returned list and optionally padding length (see above).
            max_image_size (`int`, *optional*):
                Maximum size of the image to be processed.
            split_image (`bool`, *optional*):
                Whether to split the image into patches before processing.
            truncation (`bool`, *optional*):
                Activates truncation to cut input sequences longer than `max_length` to `max_length`.
            return_tensors (`str` or [`~utils.TensorType`], *optional*):
                If set, will return tensors of a particular framework. Acceptable values are:

                - `'tf'`: Return TensorFlow `tf.constant` objects.
                - `'pt'`: Return PyTorch `torch.Tensor` objects.
                - `'np'`: Return NumPy `np.ndarray` objects.
                - `'jax'`: Return JAX `jnp.ndarray` objects.

        Returns:
            [`BatchFeature`]: A [`BatchFeature`] with the following fields:

            - **input_ids** -- List of token ids to be fed to a model. Returned when `text` is not `None`.
            - **attention_mask** -- List of indices specifying which tokens should be attended to by the model (when
              `return_attention_mask=True` or if *"attention_mask"* is in `self.model_input_names` and if `text` is not
              `None`).
            - **pixel_values** -- Pixel values to be fed to a model. Returned when `images` is not `None`.
            - **pixel_mask** -- Pixel mask to be fed to a model. Returned when `images` is not `None`.
        """
        if isinstance(text, str):
            text = [text]
        elif not isinstance(text, list) and not isinstance(text[0], str):
            raise ValueError(
                "Invalid input text. Please provide a string, or a list of strings"
            )
        if images is not None:
            image_inputs = self.image_processor(
                images,
                return_tensors=return_tensors,
                max_image_size=max_image_size,
                split_image=split_image,
            )
            prompt_strings = []

            num_crops = int(image_inputs.pop("num_crops").numpy()[0])  # 转换为整数
            for prompt in text:
                prompt_strings.append(
                    prompt.replace(self.image_token, self.image_token * num_crops)
                )
            max_image_size = (
                max_image_size
                if max_image_size is not None
                else self.image_processor.max_image_size
            )
            if max_image_size == 490:
                num_image_tokens = 128
            elif max_image_size == 980:
                num_image_tokens = 256
            else:
                raise ValueError(
                    f"max_image_size must be either 490 or 980, got {max_image_size}"
                )
            prompt_strings = [
                sample.replace(self.image_token, self.image_token * num_image_tokens)
                for sample in prompt_strings
            ]
        else:
            image_inputs = {}
            prompt_strings = text
        text_inputs = self.tokenizer(
            prompt_strings,
            return_tensors=return_tensors,
            padding=padding,
            truncation=truncation,
            max_length=max_length,
        )
        if return_final_prompts:
            return (
                BatchFeature(data={**text_inputs, **image_inputs}),
                prompt_strings,
            )
        else:
            return BatchFeature(data={**text_inputs, **image_inputs})
    
    @staticmethod
    def _extract_kwargs(func: callable, **kwargs) -> dict:
        """
        Extract the kwargs that are valid for the given function.
        """
        return {
            k: v for k, v in kwargs.items() if k in inspect.signature(func).parameters
        }

    def save_pretrained(self, save_directory, **kwargs):
        """
        Save both the image processor and tokenizer.
        """
        if self.image_processor is not None:
            self.image_processor.save_pretrained(
                save_directory,
                **self._extract_kwargs(self.image_processor.save_pretrained, **kwargs),
            )
        if self.tokenizer is not None:
            self.tokenizer.save_pretrained(
                save_directory,
                **self._extract_kwargs(self.tokenizer.save_pretrained, **kwargs),
            )

    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path,
        tokenizer_path=None,
        image_processor_path=None,
        **kwargs,
    ):
        """
        Load both the image processor and tokenizer from a pretrained model path.
        """
        tokenizer_path = (
            tokenizer_path
            if tokenizer_path is not None
            else pretrained_model_name_or_path
        )
        image_processor_path = (
            image_processor_path
            if image_processor_path is not None
            else pretrained_model_name_or_path
        )
        image_processor = AriaVisionProcessor.from_pretrained(
            image_processor_path,
            **cls._extract_kwargs(AriaVisionProcessor.from_pretrained, **kwargs),
        )
        if "use_fast" in kwargs:
            logger.warning("use_fast is not supported for AriaProcessor. Ignoring...")
            kwargs.pop("use_fast")
        try:
            tokenizer = AriaLlamaTokenizer.from_pretrained(
                tokenizer_path,
                use_fast=False,
                **cls._extract_kwargs(
                    AriaLlamaTokenizer.from_pretrained, **kwargs
                ),
            )
            chat_template = tokenizer.chat_template
        except Exception as e:
            logger.warning(f"Failed to load tokenizer from {tokenizer_path}: {e}")
            tokenizer = None
            chat_template = None
        return cls(
            image_processor=image_processor,
            tokenizer=tokenizer,
            chat_template=chat_template,
        )

    def batch_decode(self, *args, **kwargs):
        """
        This method forwards all its arguments to LlamaTokenizerFast's [`~PreTrainedTokenizer.batch_decode`]. Please
        refer to the docstring of this method for more information.
        """
        if self.tokenizer is None:
            raise ValueError(
                "Tokenizer is not initialized. Please provide a valid tokenizer."
            )
        return self.tokenizer.batch_decode(*args, **kwargs)

    def decode(self, *args, **kwargs):
        """
        This method forwards all its arguments to LlamaTokenizerFast's [`~PreTrainedTokenizer.decode`]. Please refer to
        the docstring of this method for more information.
        """
        if self.tokenizer is None:
            raise ValueError(
                "Tokenizer is not initialized. Please provide a valid tokenizer."
            )
        return self.tokenizer.decode(*args, **kwargs)

    @property
    def model_input_names(self):
        tokenizer_input_names = self.tokenizer.model_input_names
        image_processor_input_names = self.image_processor.model_input_names
        return list(dict.fromkeys(tokenizer_input_names + image_processor_input_names))
