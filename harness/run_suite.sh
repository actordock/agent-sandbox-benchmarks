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

PROJECT="${1:-}"
SUITE="${2:-}"

usage() {
  cat <<EOF
Usage: $0 <project> <suite>

Example: $0 actordock runtime-api

Environment:
  BENCH_USERS        (default: 5)
  BENCH_SPAWN_RATE   (default: 5)
  BENCH_RUN_TIME     (default: 60s)
  LOCUST_IMAGE       (default: localhost:5001/locust-actordock:latest)
EOF
}

if [[ -z "${PROJECT}" || -z "${SUITE}" ]]; then
  usage
  exit 1
fi

PDIR="$(project_dir "${PROJECT}")"
JOB_TMPL="${PDIR}/locust/jobs/${SUITE}.yaml.tmpl"
[[ -f "${JOB_TMPL}" ]] || die "missing job template: ${JOB_TMPL}"

BENCH_USERS="${BENCH_USERS:-5}"
BENCH_SPAWN_RATE="${BENCH_SPAWN_RATE:-5}"
BENCH_RUN_TIME="${BENCH_RUN_TIME:-60s}"
LOCUST_IMAGE="${LOCUST_IMAGE:-localhost:5001/locust-actordock:latest}"
JOB_NAME="locust-${SUITE}"
NS="monitoring"
WORKDIR="${BENCH_ROOT}/.work/run-${PROJECT}-${SUITE}"
OUT_JSON="${BENCH_ROOT}/results/${PROJECT}-${SUITE}.json"

require_cmd kubectl python3 envsubst

mkdir -p "${WORKDIR}" "${BENCH_ROOT}/results"

log_step "Deleting prior job ${JOB_NAME} if any"
kubectl delete job "${JOB_NAME}" -n "${NS}" --ignore-not-found --wait=true

log_step "Applying Locust job for ${PROJECT}/${SUITE}"
export LOCUST_IMAGE BENCH_USERS BENCH_SPAWN_RATE BENCH_RUN_TIME
envsubst < "${JOB_TMPL}" | kubectl apply -f -

log_step "Waiting for job completion"
kubectl wait --for=condition=complete "job/${JOB_NAME}" -n "${NS}" --timeout=900s

POD="$(kubectl get pods -n "${NS}" -l "job-name=${JOB_NAME}" -o jsonpath='{.items[0].metadata.name}')"
[[ -n "${POD}" ]] || die "no pod for job ${JOB_NAME}"

log_step "Copying Locust CSV from pod ${POD}"
kubectl cp "${NS}/${POD}:/tmp/results_stats.csv" "${WORKDIR}/results_stats.csv"

TARGET_REF=""
if [[ -f "${PDIR}/.target_ref" ]]; then
  TARGET_REF="$(tr -d '[:space:]' < "${PDIR}/.target_ref")"
fi

DURATION_S="${BENCH_RUN_TIME%s}"

python3 "${BENCH_ROOT}/harness/summarize_locust_csv.py" \
  --project "${PROJECT}" \
  --suite "${SUITE}" \
  --stats-csv "${WORKDIR}/results_stats.csv" \
  --out "${OUT_JSON}" \
  --target-ref "${TARGET_REF}" \
  --users "${BENCH_USERS}" \
  --spawn-rate "${BENCH_SPAWN_RATE}" \
  --duration-s "${DURATION_S}"

log_step "Done: ${OUT_JSON}"
cat "${OUT_JSON}"
