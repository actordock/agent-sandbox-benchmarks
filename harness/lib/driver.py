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

"""Portable sandbox driver interface for shared benchmark suites."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SandboxHandle:
    sandbox_id: str


class SandboxDriver(ABC):
    @abstractmethod
    def create(self) -> SandboxHandle:
        """Create a new sandbox (may not be ready yet)."""

    @abstractmethod
    def wait_ready(self, handle: SandboxHandle) -> None:
        """Block until the sandbox can accept work."""

    @abstractmethod
    def exec_command(self, handle: SandboxHandle, command: str) -> str:
        """Run a shell command and return combined stdout."""

    @abstractmethod
    def suspend(self, handle: SandboxHandle) -> None:
        """Suspend or pause the sandbox."""

    @abstractmethod
    def wait_suspended(self, handle: SandboxHandle) -> None:
        """Block until the sandbox is fully suspended."""

    @abstractmethod
    def resume(self, handle: SandboxHandle) -> None:
        """Resume a suspended sandbox (may not be ready yet)."""

    @abstractmethod
    def delete(self, handle: SandboxHandle) -> None:
        """Delete the sandbox."""

    @abstractmethod
    def close(self) -> None:
        """Release driver resources."""
