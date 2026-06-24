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

JSON="${1:?result json path}"
[[ -f "${JSON}" ]] || exit 0

if [[ -z "${GITHUB_STEP_SUMMARY:-}" ]]; then
  exit 0
fi

python3 - "${JSON}" <<'PY'
import json
import os
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
lines = [
    f"## Benchmark: {data['project']} / {data['suite']}",
    "",
    f"- target_ref: `{data.get('target_ref', '')}`",
    f"- users: {data['run']['users']}  duration: {data['run']['duration_s']}s",
    "",
    "| operation | p50_ms | p99_ms | rps | fail_rate |",
    "|-----------|--------|--------|-----|-----------|",
]
for name, m in sorted(data.get("metrics", {}).items()):
    lines.append(
        f"| {name} | {m.get('p50_ms', '-')} | {m.get('p99_ms', '-')} | {m.get('rps', '-')} | {m.get('fail_rate', '-')} |"
    )
Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("\n".join(lines) + "\n")
PY
