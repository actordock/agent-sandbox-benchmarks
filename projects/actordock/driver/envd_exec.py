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

"""Direct envd Connect RPC helpers (runtime-api backend, no platform router)."""

from __future__ import annotations

import base64
import json
import os
import struct
import time

import httpx

ENVD_PORT = int(os.environ.get("BENCH_ENVD_PORT", "80"))
WAIT_TIMEOUT_S = float(os.environ.get("BENCH_WAIT_TIMEOUT_S", "120"))
POLL_INTERVAL_S = float(os.environ.get("BENCH_POLL_INTERVAL_S", "0.2"))

_CONNECT_HEADERS = {
    "Content-Type": "application/connect+json",
    "Connect-Protocol-Version": "1",
}


def actor_backend(sandbox_pod_ip: str, *, envd_port: int = ENVD_PORT) -> str:
    if not sandbox_pod_ip:
        raise RuntimeError("actor has no sandbox_pod_ip (worker not assigned)")
    return f"{sandbox_pod_ip}:{envd_port}"


def wait_envd_ready(
    backend: str,
    *,
    timeout_s: float = WAIT_TIMEOUT_S,
    poll_interval_s: float = POLL_INTERVAL_S,
) -> None:
    """Poll envd process.List until the sandbox accepts Connect RPC."""
    url = f"http://{backend}/process.Process/List"
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    with httpx.Client(http2=True, timeout=5.0) as client:
        while time.time() < deadline:
            try:
                resp = client.post(url, headers=_CONNECT_HEADERS, content=b"{}")
                resp.raise_for_status()
                return
            except Exception as err:
                last_err = err
                time.sleep(poll_interval_s)
    raise TimeoutError(
        f"envd at {backend} not ready within {timeout_s}s: {last_err}"
    ) from last_err


def exec_command_at_backend(
    backend: str,
    command: str,
    *,
    timeout_s: float = 60.0,
) -> str:
    body = json.dumps(
        {"process": {"cmd": "/bin/sh", "args": ["-c", command]}}
    ).encode("utf-8")
    url = f"http://{backend}/process.Process/Start"

    stdout_parts: list[str] = []
    exit_code = None

    with httpx.Client(http2=True, timeout=timeout_s) as client:
        with client.stream("POST", url, headers=_CONNECT_HEADERS, content=body) as resp:
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
