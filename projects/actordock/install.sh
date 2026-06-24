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

ACTORDOCK_REPO="${ACTORDOCK_REPO:-https://github.com/actordock/actordock.git}"
ACTORDOCK_REF="${ACTORDOCK_REF:-main}"
ACTORDOCK_ROOT="${ACTORDOCK_ROOT:-${ROOT}/.work/actordock}"

usage() {
  cat <<EOF
Usage: $0

Clone and install Actordock on a Kind cluster (same as actordock/hack/install-local.sh).

Environment:
  ACTORDOCK_REPO   Git remote (default: actordock org)
  ACTORDOCK_REF    Branch, tag, or SHA to test
  ACTORDOCK_ROOT   Checkout directory (default: projects/actordock/.work/actordock)
  KIND_CLUSTER_NAME  Kind cluster name (default: actordock)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd git docker kubectl go

mkdir -p "$(dirname "${ACTORDOCK_ROOT}")"
if [[ ! -d "${ACTORDOCK_ROOT}/.git" ]]; then
  log_step "Cloning ${ACTORDOCK_REPO} -> ${ACTORDOCK_ROOT}"
  git clone "${ACTORDOCK_REPO}" "${ACTORDOCK_ROOT}"
else
  log_step "Using existing checkout at ${ACTORDOCK_ROOT}"
fi

log_step "Checking out ${ACTORDOCK_REF}"
git -C "${ACTORDOCK_ROOT}" fetch --depth 1 origin "${ACTORDOCK_REF}" 2>/dev/null \
  || git -C "${ACTORDOCK_ROOT}" fetch --depth 1 origin
git -C "${ACTORDOCK_ROOT}" checkout "${ACTORDOCK_REF}"

log_step "Recording target ref"
git -C "${ACTORDOCK_ROOT}" rev-parse HEAD | tee "${ROOT}/.target_ref"

log_step "Installing Actordock stack on Kind"
"${ACTORDOCK_ROOT}/hack/install-local.sh"

echo "Actordock install complete at $(cat "${ROOT}/.target_ref")"
