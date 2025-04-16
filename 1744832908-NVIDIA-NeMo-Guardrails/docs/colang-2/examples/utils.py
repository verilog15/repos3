# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from typing import Optional

from nemoguardrails.rails.llm.config import RailsConfig
from nemoguardrails.rails.llm.llmrails import LLMRails
from tests.utils import FakeLLM
from tests.v2_x.chat import ChatInterface

YAML_CONFIG = """
colang_version: "2.x"
"""


async def run_chat_interface_based_on_test_script(
    test_script: str,
    colang: str,
    wait_time_s: float,
    llm_responses: Optional[list] = None,
) -> str:
    rails_config = RailsConfig.from_content(
        colang_content=colang,
        yaml_content=YAML_CONFIG,
    )
    interaction_log = []

    if llm_responses:
        llm = FakeLLM(responses=llm_responses)
        rails_app = LLMRails(rails_config, verbose=True, llm=llm)
    else:
        rails_app = LLMRails(rails_config, verbose=True)

    chat = ChatInterface(rails_app)

    lines = test_script.split("\n")
    for line in lines:
        if line.startswith("#"):
            continue
        if line.startswith(">"):
            interaction_log.append(line)
            user_input = line.replace("> ", "")
            print(f"sending '{user_input}' to process")
            response = await chat.process(user_input, wait_time_s)
            interaction_log.append(response)

    chat.should_terminate = True
    await asyncio.sleep(0.5)

    return "\n".join(interaction_log)


def cleanup(content):
    output = []
    lines = content.split("\n")
    for line in lines:
        if len(line.strip()) == 0:
            continue
        if line.strip() == ">":
            continue
        if line.startswith("#"):
            continue
        if "Starting the chat" in line:
            continue

        output.append(line.strip())

    return "\n".join(output)


async def compare_interaction_with_test_script(
    test_script: str,
    colang: str,
    wait_time_s: float = 1.0,
    llm_responses: Optional[list] = None,
) -> None:
    result = await run_chat_interface_based_on_test_script(
        test_script, colang, wait_time_s, llm_responses=llm_responses
    )
    clean_test_script = cleanup(test_script)
    clean_result = cleanup(result)
    assert (
        clean_test_script == clean_result
    ), f"\n----\n{clean_result}\n----\n\ndoes not match test script\n\n----\n{clean_test_script}\n----"
