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

import os
import time
import uuid

from common import runtimeapi_pb2
from common.grpc_client import control_stub
from harness.lib.driver import SandboxDriver, SandboxHandle
from projects.actordock.driver.envd_exec import exec_command

TEMPLATE_NAMESPACE = os.environ.get("BENCH_TEMPLATE_NAMESPACE", "actordock")
TEMPLATE_NAME = os.environ.get("BENCH_TEMPLATE_NAME", "base")
ACTOR_ID_PREFIX = os.environ.get("BENCH_ACTOR_ID_PREFIX", "bench-")
WAIT_TIMEOUT_S = float(os.environ.get("BENCH_WAIT_TIMEOUT_S", "120"))
POLL_INTERVAL_S = float(os.environ.get("BENCH_POLL_INTERVAL_S", "0.2"))

_STATUS_RUNNING = runtimeapi_pb2.Actor.STATUS_RUNNING
_STATUS_SUSPENDED = runtimeapi_pb2.Actor.STATUS_SUSPENDED


def create_driver() -> SandboxDriver:
    return ActordockGrpcDriver()


class ActordockGrpcDriver(SandboxDriver):
    def __init__(self):
        self._channel, self._stub = control_stub()

    def create(self) -> SandboxHandle:
        actor_id = f"{ACTOR_ID_PREFIX}{uuid.uuid4()}"
        self._stub.CreateActor(
            runtimeapi_pb2.CreateActorRequest(
                actor_id=actor_id,
                actor_template_namespace=TEMPLATE_NAMESPACE,
                actor_template_name=TEMPLATE_NAME,
            )
        )
        return SandboxHandle(sandbox_id=actor_id)

    def wait_ready(self, handle: SandboxHandle) -> None:
        self._stub.ResumeActor(
            runtimeapi_pb2.ResumeActorRequest(actor_id=handle.sandbox_id)
        )
        self._wait_for_status(handle.sandbox_id, _STATUS_RUNNING)

    def exec_command(self, handle: SandboxHandle, command: str) -> str:
        return exec_command(handle.sandbox_id, command)

    def suspend(self, handle: SandboxHandle) -> None:
        self._stub.SuspendActor(
            runtimeapi_pb2.SuspendActorRequest(actor_id=handle.sandbox_id)
        )

    def wait_suspended(self, handle: SandboxHandle) -> None:
        self._wait_for_status(handle.sandbox_id, _STATUS_SUSPENDED)

    def delete(self, handle: SandboxHandle) -> None:
        actor = self._get_actor(handle.sandbox_id)
        if actor.status != _STATUS_SUSPENDED:
            self.suspend(handle)
            self.wait_suspended(handle)
        self._stub.DeleteActor(
            runtimeapi_pb2.DeleteActorRequest(actor_id=handle.sandbox_id)
        )

    def resume(self, handle: SandboxHandle) -> None:
        self._stub.ResumeActor(
            runtimeapi_pb2.ResumeActorRequest(actor_id=handle.sandbox_id)
        )

    def close(self) -> None:
        self._channel.close()

    def _get_actor(self, actor_id: str):
        return self._stub.GetActor(
            runtimeapi_pb2.GetActorRequest(actor_id=actor_id)
        ).actor

    def _wait_for_status(self, actor_id: str, want_status: int) -> None:
        deadline = time.time() + WAIT_TIMEOUT_S
        while time.time() < deadline:
            actor = self._get_actor(actor_id)
            if actor.status == want_status:
                return
            time.sleep(POLL_INTERVAL_S)
        raise TimeoutError(
            f"actor {actor_id} did not reach status {want_status} within {WAIT_TIMEOUT_S}s"
        )
