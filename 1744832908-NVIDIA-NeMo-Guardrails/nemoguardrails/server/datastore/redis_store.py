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

import aioredis

from nemoguardrails.server.datastore.datastore import DataStore


class RedisStore(DataStore):
    """A datastore implementation using Redis."""

    def __init__(
        self, url: str, username: Optional[str] = None, password: Optional[str] = None
    ):
        """Constructor.

        Args:
            url: The URL to the redis instance, in the format used by aioredis.
              e.g. redis://localhost:6379/1
            username: [Optional] The username to use for authentication.
            password: [Optional] The password to use for authentication
        """
        self.url = url
        self.username = username
        self.password = password
        self.client = aioredis.from_url(
            url=url, username=username, password=password, decode_responses=True
        )

    async def set(self, key: str, value: str):
        """Save data into the datastore.

        Args:
            key: The key to use.
            value: The value associated with the key.

        Returns:
            None
        """
        await self.client.set(key, value)

    async def get(self, key: str) -> Optional[str]:
        """Return the value for the specified key.
        Args:
            key: The key to lookup.

        Returns:
            None if the key does not exist.
        """
        return await self.client.get(key)
