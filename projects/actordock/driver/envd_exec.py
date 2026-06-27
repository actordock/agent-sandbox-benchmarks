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

import base64
import json
import os
import struct
import time
import uuid

import httpx

ROUTER_ADDR = os.environ.get(
    "BENCH_ROUTER_ADDR", "router.actordock.svc.cluster.local:8081"
)
SANDBOX_ID_HEADER = "E2b-Sandbox-Id"


def exec_command(sandbox_id: str, command: str, *, timeout_s: float = 60.0) -> str:
    body = json.dumps(
        {"process": {"cmd": "/bin/sh", "args": ["-c", command]}}
    ).encode("utf-8")
    url = f"http://{ROUTER_ADDR}/process.Process/Start"
    headers = {
        "Content-Type": "application/connect+json",
        "Connect-Protocol-Version": "1",
        SANDBOX_ID_HEADER: sandbox_id,
    }

    stdout_parts: list[str] = []
    exit_code = None

    with httpx.Client(http2=True, timeout=timeout_s) as client:
        with client.stream("POST", url, headers=headers, content=body) as resp:
            resp.raise_for_status()
            buf = b""
            for chunk in resp.iter_bytes():
                buf += chunk
                while len(buf) >= 5:
                    length = struct.unpack(">I", buf[1:5])[0]
                    if len(buf) < 5 + length:
                        break
                    payload = buf[5 : 5 + length]
                    buf = buf[5 + length :]
                    msg = json.loads(payload)
                    event = msg.get("event") or {}
                    if "data" in event:
                        data = event["data"]
                        stdout = data.get("stdout")
                        if stdout:
                            if isinstance(stdout, str):
                                stdout_parts.append(
                                    base64.b64decode(stdout).decode("utf-8", "replace")
                                )
                            else:
                                stdout_parts.append(str(stdout))
                    end = event.get("end")
                    if end is not None:
                        exit_code = end.get("exitCode", end.get("exit_code", 0))

    if exit_code not in (0, None):
        raise RuntimeError(
            f"command failed with exit code {exit_code}: {command!r}"
        )
    return "".join(stdout_parts)
