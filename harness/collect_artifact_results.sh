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

BENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/common.sh
source "${BENCH_ROOT}/harness/lib/common.sh"

ARTIFACTS_DIR="${1:-artifacts}"
OUT_DIR="${OUT_DIR:-${BENCH_ROOT}/results}"

usage() {
  cat <<EOF
Usage: $0 [artifacts_dir]

Flatten downloaded workflow artifacts into results/*.json.

Example (CI):
  actions/download-artifact → artifacts/
  $0 artifacts
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

[[ -d "${ARTIFACTS_DIR}" ]] || die "artifacts dir not found: ${ARTIFACTS_DIR}"

mkdir -p "${OUT_DIR}"
found=0
while IFS= read -r -d '' f; do
  cp "${f}" "${OUT_DIR}/"
  found=$((found + 1))
done < <(find "${ARTIFACTS_DIR}" -name '*.json' -type f -print0)

[[ "${found}" -gt 0 ]] || die "no JSON files under ${ARTIFACTS_DIR}"

log_step "Collected ${found} JSON file(s) into ${OUT_DIR}"
