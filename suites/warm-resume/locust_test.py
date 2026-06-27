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

from locust import User, task, between

from suites.common.driver_loader import get_driver
from suites.common.record import record_request


class WarmResumeUser(User):
    wait_time = between(0.5, 1.0)

    def on_start(self):
        self.driver = get_driver()
        self.handle = self.driver.create()
        self.driver.wait_ready(self.handle)
        self.driver.suspend(self.handle)
        self.driver.wait_suspended(self.handle)

    def on_stop(self):
        try:
            self.driver.delete(self.handle)
        except Exception:
            pass
        self.driver.close()

    @task
    def warm_resume(self):
        record_request(
            "WarmResume",
            self._resume_cycle,
            user_class=self.__class__.__name__,
        )

    def _resume_cycle(self):
        self.driver.resume(self.handle)
        self.driver.wait_ready(self.handle)
        self.driver.suspend(self.handle)
        self.driver.wait_suspended(self.handle)
