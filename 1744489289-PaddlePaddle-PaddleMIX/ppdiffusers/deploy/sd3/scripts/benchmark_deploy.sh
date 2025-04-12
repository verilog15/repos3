# Copyright (c) 2025 PaddlePaddle Authors. All Rights Reserved.
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

set -eux

# 安装 triton并适配paddle
python -m pip install triton
python -m pip install git+https://github.com/zhoutianzi666/UseTritonInPaddle.git
python -c "import use_triton_in_paddle; use_triton_in_paddle.make_triton_compatible_with_paddle()"
# 安装paddlemix库,使用集成在paddlemix库中的自定义算子。
cd PaddleMIX
pip install -e .
cd PaddleMIX/ppdiffusers/deploy/sd3

# text_to_image_generation-stable_diffusion_3.py中设置exp_enable_use_cutlass=False
python  text_to_image_generation-stable_diffusion_3.py  --dtype float16 --height 1024 --width 1024 --num-inference-steps 50 --inference_optimize 1  --benchmark yes


# 执行多卡推理指令
python -m paddle.distributed.launch --gpus "0,1,2,3" text_to_image_generation-stable_diffusion_3.py \
--dtype float16 \
--height 1024 \
--width 1024 \
--num-inference-steps 20 \
--inference_optimize 1 \
--mp_size 2 \
--dp_size 2 \
--benchmark 1
