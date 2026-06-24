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

from locust import events
import random

_initialized = False


def init_wait_time():
    global _initialized
    if _initialized:
        return

    @events.init_command_line_parser.add_listener
    def on_init_parser(parser):
        parser.add_argument(
            "--min-wait-time",
            type=float,
            default=0.0,
            env_var="LOCUST_MIN_WAIT_TIME",
            help="Minimum wait time between tasks (seconds)",
        )
        parser.add_argument(
            "--max-wait-time",
            type=float,
            default=0.5,
            env_var="LOCUST_MAX_WAIT_TIME",
            help="Maximum wait time between tasks (seconds)",
        )

    _initialized = True


def dynamic_wait_time(user_instance):
    opts = user_instance.environment.parsed_options
    min_wait = getattr(opts, "min_wait_time", 0.0) or 0.0
    max_wait = getattr(opts, "max_wait_time", 0.5) or 0.5
    return random.uniform(min_wait, max_wait)
