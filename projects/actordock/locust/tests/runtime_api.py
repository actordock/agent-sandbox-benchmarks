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

# Actordock-private benchmark: steady-state runtime-api control plane RPCs.

from locust import User, task, events
import time
import uuid

from common import runtimeapi_pb2
from common.grpc_client import control_stub
from common.metrics import init_metrics, update_user_count
from common.wait_time import init_wait_time, dynamic_wait_time

init_metrics()
init_wait_time()

TEMPLATE_NAMESPACE = "actordock"
TEMPLATE_NAME = "base"


class RuntimeAPIUser(User):
    wait_time = dynamic_wait_time

    def on_start(self):
        update_user_count(1, self.__class__.__name__)
        self.channel, self.stub = control_stub()
        self.actor_id = str(uuid.uuid4())
        self.stub.CreateActor(
            runtimeapi_pb2.CreateActorRequest(
                actor_id=self.actor_id,
                actor_template_namespace=TEMPLATE_NAMESPACE,
                actor_template_name=TEMPLATE_NAME,
            )
        )

    def on_stop(self):
        update_user_count(-1, self.__class__.__name__)
        try:
            self.stub.SuspendActor(
                runtimeapi_pb2.SuspendActorRequest(actor_id=self.actor_id)
            )
        except Exception:
            pass
        self.channel.close()

    @task
    def invoke_target(self):
        for name, fn in (
            ("GetActor", lambda: self.stub.GetActor(
                runtimeapi_pb2.GetActorRequest(actor_id=self.actor_id))),
            ("ResumeActor", lambda: self.stub.ResumeActor(
                runtimeapi_pb2.ResumeActorRequest(actor_id=self.actor_id))),
            ("SuspendActor", lambda: self.stub.SuspendActor(
                runtimeapi_pb2.SuspendActorRequest(actor_id=self.actor_id))),
        ):
            start = time.time()
            exc = None
            try:
                fn()
            except Exception as e:
                exc = e
            duration = (time.time() - start) * 1000
            events.request.fire(
                request_type="grpc",
                name=name,
                response_time=duration,
                response_length=0,
                exception=exc,
                user_class=self.__class__.__name__,
            )
