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
# shellcheck source=../../harness/lib/common.sh
source "${ROOT}/../../harness/lib/common.sh"

LOCUST_IMAGE="${LOCUST_IMAGE:-localhost:5001/locust-actordock:latest}"
KO_DOCKER_REPO="${KO_DOCKER_REPO:-localhost:5001}"

require_cmd docker

if [[ -x "${ROOT}/generate_protos.sh" ]]; then
  ACTORDOCK_ROOT="${ACTORDOCK_ROOT:-${ROOT}/.work/actordock}"
  if [[ -f "${ACTORDOCK_ROOT}/runtime/pkg/proto/runtimeapipb/runtimeapi.proto" ]]; then
    log_step "Generating gRPC Python stubs"
    ACTORDOCK_ROOT="${ACTORDOCK_ROOT}" "${ROOT}/generate_protos.sh"
  fi
fi

log_step "Building ${LOCUST_IMAGE}"
docker build -t "${LOCUST_IMAGE}" -f "${ROOT}/locust/Dockerfile" "${ROOT}/locust/"

log_step "Pushing to registry"
docker push "${LOCUST_IMAGE}"

echo "Locust image ready: ${LOCUST_IMAGE}"
