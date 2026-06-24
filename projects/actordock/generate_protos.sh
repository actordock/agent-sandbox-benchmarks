#!/usr/bin/env bash
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

set -o errexit -o nounset -o pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ACTORDOCK_ROOT="${ACTORDOCK_ROOT:-${ROOT}/.work/actordock}"
PROTO_PATH="${ACTORDOCK_ROOT}/runtime/pkg/proto/runtimeapipb"
PROTO_FILE="${PROTO_PATH}/runtimeapi.proto"
OUT_DIR="${ROOT}/locust/common"
VENV_DIR="${ROOT}/locust/venv"

[[ -f "${PROTO_FILE}" ]] || { echo "missing ${PROTO_FILE}" >&2; exit 1; }

python3 -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
pip install --quiet --upgrade pip grpcio-tools

python3 -m grpc_tools.protoc \
  -I"${PROTO_PATH}" \
  --python_out="${OUT_DIR}" \
  --grpc_python_out="${OUT_DIR}" \
  "${PROTO_FILE}"

GRPC_FILE="${OUT_DIR}/runtimeapi_pb2_grpc.py"
if [[ -f "${GRPC_FILE}" ]]; then
  if sed --version >/dev/null 2>&1; then
    sed -i 's/^import runtimeapi_pb2 as runtimeapi__pb2/from . import runtimeapi_pb2 as runtimeapi__pb2/' "${GRPC_FILE}"
  else
    sed -i '' 's/^import runtimeapi_pb2 as runtimeapi__pb2/from . import runtimeapi_pb2 as runtimeapi__pb2/' "${GRPC_FILE}"
  fi
fi

echo "Generated stubs in ${OUT_DIR}"
