# Copyright 2026 The Actordock Authors
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

from __future__ import annotations

import time
from typing import Callable, TypeVar

from locust import events

T = TypeVar("T")


def record_request(
    name: str,
    fn: Callable[[], T],
    *,
    request_type: str = "sandbox",
    user_class: str,
) -> T:
    start = time.time()
    exc = None
    result = None
    try:
        result = fn()
        return result
    except Exception as e:
        exc = e
        raise
    finally:
        events.request.fire(
            request_type=request_type,
            name=name,
            response_time=(time.time() - start) * 1000,
            response_length=0,
            exception=exc,
            user_class=user_class,
        )
