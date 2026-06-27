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

PROJECT="${1:-actordock}"
RUN_ID="${2:-}"
DATA_ROOT="${BENCH_DATA_ROOT:-${BENCH_ROOT}/benchmark-data}"
RESULTS_DIR="${RESULTS_DIR:-${BENCH_ROOT}/results}"
MANIFEST="${DATA_ROOT}/manifest.json"
DEST_ROOT="${DATA_ROOT}/${PROJECT}"

usage() {
  cat <<EOF
Usage: $0 [project] [run_id]

Write results/<project>-*.json into benchmark-data/ and update manifest.json.
The website reads this directory via GitHub raw URLs.

Environment:
  BENCH_DATA_ROOT   output root (default: ./benchmark-data)
  RESULTS_DIR       benchmark JSON source (default: ./results)

Example:
  $0 actordock
  $0 actordock 49ff499
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd python3

mkdir -p "${DATA_ROOT}"

if [[ -z "${RUN_ID}" ]]; then
  RUN_ID="local"
  for f in "${RESULTS_DIR}/${PROJECT}-"*.json; do
    [[ -f "${f}" ]] || continue
    ref="$(python3 -c "import json; print(json.load(open('${f}')).get('target_ref','')[:7])")"
    if [[ -n "${ref}" ]]; then
      RUN_ID="${ref}"
      break
    fi
  done
fi

DEST="${DEST_ROOT}/${RUN_ID}"
mkdir -p "${DEST}"

copied=0
for f in "${RESULTS_DIR}/${PROJECT}-"*.json; do
  [[ -f "${f}" ]] || continue
  suite="$(basename "${f}" .json)"
  suite="${suite#${PROJECT}-}"
  cp "${f}" "${DEST}/${suite}.json"
  copied=$((copied + 1))
done
[[ "${copied}" -gt 0 ]] || die "no result files in ${RESULTS_DIR} for project ${PROJECT}"

log_step "Wrote ${copied} suite(s) to ${DEST}"

python3 - "${MANIFEST}" "${PROJECT}" "${RUN_ID}" "${PROJECT}/${RUN_ID}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest_path, project_id, run_id, base_path = sys.argv[1:5]
root = Path(manifest_path).parent
path = Path(manifest_path)
manifest = json.loads(path.read_text()) if path.is_file() else {
    "schema": "benchmark-manifest.v1",
    "suite_groups": {
        "shared": ["cold-start", "warm-resume", "agent-loop"],
        "private": {"actordock": ["runtime-api", "sleep-workload"]},
    },
    "projects": [],
}

projects = manifest.setdefault("projects", [])
project = next((p for p in projects if p["id"] == project_id), None)
if project is None:
    project = {
        "id": project_id,
        "name": project_id.replace("-", " ").title(),
        "description": "",
        "runs": [],
    }
    projects.append(project)

target_ref = ""
recorded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
run_dir = root / base_path
sample = run_dir / "cold-start.json"
if not sample.is_file():
    candidates = sorted(run_dir.glob("*.json"))
    sample = candidates[0] if candidates else sample
if sample.is_file():
    data = json.loads(sample.read_text())
    target_ref = data.get("target_ref") or ""
    recorded_at = data.get("timestamp") or recorded_at

runs = project.setdefault("runs", [])
runs = [r for r in runs if r["id"] != run_id]
runs.insert(0, {
    "id": run_id,
    "label": recorded_at.replace("+00:00", "Z"),
    "target_ref": target_ref,
    "recorded_at": recorded_at,
    "base_path": base_path,
})
project["runs"] = runs[:20]
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"updated manifest: {manifest_path}")
PY

log_step "Updated benchmark-data/${PROJECT}/${RUN_ID}"
