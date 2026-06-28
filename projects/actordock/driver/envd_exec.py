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
import socket
import struct
import time
from typing import Iterator

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import DataReceived, ResponseReceived, StreamEnded, WindowUpdated

ENVD_PORT = int(os.environ.get("BENCH_ENVD_PORT", "80"))
WAIT_TIMEOUT_S = float(os.environ.get("BENCH_WAIT_TIMEOUT_S", "120"))
POLL_INTERVAL_S = float(os.environ.get("BENCH_POLL_INTERVAL_S", "0.2"))

_CONNECT_VERSION = "1"


def actor_backend(sandbox_pod_ip: str, *, envd_port: int = ENVD_PORT) -> str:
    if not sandbox_pod_ip:
        raise RuntimeError("actor has no sandbox_pod_ip (worker not assigned)")
    return f"{sandbox_pod_ip}:{envd_port}"


def _split_backend(backend: str) -> tuple[str, int]:
    host, _, port = backend.rpartition(":")
    if not host:
        raise ValueError(f"invalid envd backend: {backend!r}")
    return host, int(port or ENVD_PORT)


def _h2c_exchange(
    backend: str,
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes = b"",
    *,
    timeout_s: float = 5.0,
) -> tuple[int, bytes]:
    host, port = _split_backend(backend)
    sock = socket.create_connection((host, port), timeout=timeout_s)
    sock.settimeout(timeout_s)
    conn = H2Connection(config=H2Configuration(client_side=True))
    conn.initiate_connection()
    sock.sendall(conn.data_to_send())

    stream_id = conn.get_next_available_stream_id()
    h2_headers = [
        (":method", method),
        (":path", path),
        (":scheme", "http"),
        (":authority", backend),
    ] + [(k.lower(), v) for k, v in headers.items()]
    conn.send_headers(stream_id, h2_headers, end_stream=not body)
    if body:
        conn.send_data(stream_id, body, end_stream=True)
    sock.sendall(conn.data_to_send())

    status_code = 0
    chunks: list[bytes] = []
    while True:
        data = sock.recv(65536)
        if not data:
            break
        events = conn.receive_data(data)
        for event in events:
            if isinstance(event, ResponseReceived):
                for name, value in event.headers:
                    if name == b":status":
                        status_code = int(value.decode())
            elif isinstance(event, DataReceived):
                if event.flow_controlled_length:
                    conn.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id
                    )
                if event.stream_id == stream_id:
                    chunks.append(event.data)
            elif isinstance(event, StreamEnded):
                if event.stream_id == stream_id:
                    sock.close()
                    return status_code, b"".join(chunks)
            elif isinstance(event, WindowUpdated):
                pass
        out = conn.data_to_send()
        if out:
            sock.sendall(out)


def _h2c_stream(
    backend: str,
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes,
    *,
    timeout_s: float = 60.0,
) -> Iterator[bytes]:
    host, port = _split_backend(backend)
    sock = socket.create_connection((host, port), timeout=timeout_s)
    sock.settimeout(timeout_s)
    conn = H2Connection(config=H2Configuration(client_side=True))
    conn.initiate_connection()
    sock.sendall(conn.data_to_send())

    stream_id = conn.get_next_available_stream_id()
    h2_headers = [
        (":method", method),
        (":path", path),
        (":scheme", "http"),
        (":authority", backend),
    ] + [(k.lower(), v) for k, v in headers.items()]
    conn.send_headers(stream_id, h2_headers, end_stream=False)
    conn.send_data(stream_id, body, end_stream=True)
    sock.sendall(conn.data_to_send())

    status_code = 0
    ended = False
    while not ended:
        data = sock.recv(65536)
        if not data:
            break
        events = conn.receive_data(data)
        for event in events:
            if isinstance(event, ResponseReceived):
                for name, value in event.headers:
                    if name == b":status":
                        status_code = int(value.decode())
            elif isinstance(event, DataReceived):
                if event.flow_controlled_length:
                    conn.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id
                    )
                if event.stream_id == stream_id and event.data:
                    yield event.data
            elif isinstance(event, StreamEnded):
                if event.stream_id == stream_id:
                    ended = True
        out = conn.data_to_send()
        if out:
            sock.sendall(out)
    sock.close()
    if status_code >= 400:
        raise RuntimeError(f"envd stream {path} failed with status {status_code}")


def wait_envd_ready(
    backend: str,
    *,
    timeout_s: float = WAIT_TIMEOUT_S,
    poll_interval_s: float = POLL_INTERVAL_S,
) -> None:
    """Poll envd process.List until the sandbox accepts Connect RPC."""
    path = "/process.Process/List"
    headers = {
        "Content-Type": "application/json",
        "Connect-Protocol-Version": _CONNECT_VERSION,
    }
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            status, _ = _h2c_exchange(
                backend, "POST", path, headers, b"{}", timeout_s=5.0
            )
            if status < 400:
                return
            last_err = RuntimeError(f"envd list returned status {status}")
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
    path = "/process.Process/Start"
    headers = {
        "Content-Type": "application/connect+json",
        "Connect-Protocol-Version": _CONNECT_VERSION,
    }

    stdout_parts: list[str] = []
    exit_code = None
    buf = b""
    for chunk in _h2c_stream(
        backend, "POST", path, headers, body, timeout_s=timeout_s
    ):
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
