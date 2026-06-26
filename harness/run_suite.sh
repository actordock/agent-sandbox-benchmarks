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
  BENCH_RUN_TIME     sleep-workload default: 90s (3x BurstShape cycles)
                     runtime-api default: 60s
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

LOCUST_IMAGE="${LOCUST_IMAGE:-localhost:5001/locust-actordock:latest}"
SUMMARY_USERS=0
SUMMARY_SPAWN=0
case "${SUITE}" in
  sleep-workload)
    BENCH_RUN_TIME="${BENCH_RUN_TIME:-90s}"
    SUMMARY_USERS=3
    SUMMARY_SPAWN=1
    ;;
  runtime-api)
    BENCH_RUN_TIME="${BENCH_RUN_TIME:-60s}"
    ;;
  *)
    BENCH_RUN_TIME="${BENCH_RUN_TIME:-60s}"
    ;;
esac

JOB_NAME="locust-${SUITE}"
NS="monitoring"
WORKDIR="${BENCH_ROOT}/.work/run-${PROJECT}-${SUITE}"
OUT_JSON="${BENCH_ROOT}/results/${PROJECT}-${SUITE}.json"

require_cmd kubectl python3 envsubst

mkdir -p "${WORKDIR}" "${BENCH_ROOT}/results"

log_step "Deleting prior job ${JOB_NAME} if any"
kubectl delete job "${JOB_NAME}" -n "${NS}" --ignore-not-found --wait=true

log_step "Applying Locust job for ${PROJECT}/${SUITE}"
export LOCUST_IMAGE BENCH_RUN_TIME
envsubst < "${JOB_TMPL}" | kubectl apply -f -

log_step "Waiting for locust pod"
kubectl wait --for=condition=Ready "pod" -l "job-name=${JOB_NAME}" -n "${NS}" --timeout=300s

POD="$(kubectl get pods -n "${NS}" -l "job-name=${JOB_NAME}" -o jsonpath='{.items[0].metadata.name}')"
[[ -n "${POD}" ]] || die "no pod for job ${JOB_NAME}"

DURATION_S="${BENCH_RUN_TIME%s}"
STATS_CSV="/tmp/results_stats.csv"
log_step "Waiting for locust stats csv (up to $((DURATION_S + 60))s)"
copied=0
for _ in $(seq 1 "$((DURATION_S + 60))"); do
  if kubectl exec -n "${NS}" "${POD}" -c locust -- test -f "${STATS_CSV}" 2>/dev/null; then
    log_step "Copying Locust CSV from pod ${POD}"
    kubectl cp "${NS}/${POD}:${STATS_CSV}" "${WORKDIR}/results_stats.csv"
    copied=1
    break
  fi
  sleep 1
done
if [[ "${copied}" -ne 1 ]]; then
  log_step "Locust logs (stats csv missing)"
  kubectl logs -n "${NS}" "${POD}" -c locust >&2 || true
  die "missing locust stats csv in pod ${POD}"
fi

log_step "Waiting for job completion"
kubectl wait --for=condition=complete "job/${JOB_NAME}" -n "${NS}" --timeout=900s

TARGET_REF=""
if [[ -f "${PDIR}/.target_ref" ]]; then
  TARGET_REF="$(tr -d '[:space:]' < "${PDIR}/.target_ref")"
fi

python3 "${BENCH_ROOT}/harness/summarize_locust_csv.py" \
  --project "${PROJECT}" \
  --suite "${SUITE}" \
  --stats-csv "${WORKDIR}/results_stats.csv" \
  --out "${OUT_JSON}" \
  --target-ref "${TARGET_REF}" \
  --users "${SUMMARY_USERS}" \
  --spawn-rate "${SUMMARY_SPAWN}" \
  --duration-s "${DURATION_S}"

log_step "Done: ${OUT_JSON}"
cat "${OUT_JSON}"
