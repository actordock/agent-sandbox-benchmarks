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

BUCKET_NAME="${BUCKET_NAME:-actordock-snapshots}"

usage() {
  cat <<EOF
Usage: $0 [--workloads]

Deploy benchmark dependencies:
  - monitoring namespace (Prometheus)
  - optional benchmark-workloads (sleep template; for sleep-workload suite)
EOF
}

DEPLOY_WORKLOADS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workloads) DEPLOY_WORKLOADS=true ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

require_cmd kubectl

log_step "Installing monitoring stack"
kubectl apply -f "${ROOT}/monitoring/monitoring.yaml"

if [[ "${DEPLOY_WORKLOADS}" == "true" ]]; then
  ACTORDOCK_ROOT="${ACTORDOCK_ROOT:-${ROOT}/.work/actordock}"
  [[ -f "${ACTORDOCK_ROOT}/runtime/hack/run-tool.sh" ]] \
    || die "ACTORDOCK_ROOT not found; run install.sh first"
  log_step "Deploying benchmark workloads"
  sed "s|\${BUCKET_NAME}|${BUCKET_NAME}|g" "${ROOT}/workloads/workloads.yaml.tmpl" \
    | (cd "${ACTORDOCK_ROOT}/runtime" && ./hack/run-tool.sh ko apply -f -)
  kubectl wait --for=condition=Ready actortemplate/sleep -n benchmark-workloads --timeout=600s
fi

log_step "Benchmark dependencies ready"
