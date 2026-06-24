#!/usr/bin/env python3
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

"""Summarize Locust *_stats.csv into schema/result.v1.json."""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def load_stats(csv_path: Path):
    metrics = {}
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            if not name or name == "Aggregated":
                continue
            try:
                count = int(float(row.get("Request Count", 0)))
                fail_count = int(float(row.get("Failure Count", 0)))
                avg = float(row.get("Average Response Time", 0))
                rps = float(row.get("Requests/s", 0))
            except (TypeError, ValueError):
                continue
            fail_rate = (fail_count / count) if count else 0.0
            metrics[name] = {
                "count": count,
                "fail_rate": round(fail_rate, 6),
                "rps": round(rps, 4),
                "avg_ms": round(avg, 2),
                "p50_ms": round(avg, 2),
                "p95_ms": round(float(row.get("95%", avg)), 2),
                "p99_ms": round(float(row.get("99%", avg)), 2),
            }
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--stats-csv", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--target-ref", default="")
    parser.add_argument("--users", type=int, default=5)
    parser.add_argument("--spawn-rate", type=float, default=5)
    parser.add_argument("--duration-s", type=int, default=60)
    args = parser.parse_args()

    if not args.stats_csv.is_file():
        print(f"missing stats csv: {args.stats_csv}", file=sys.stderr)
        sys.exit(1)

    result = {
        "schema": "result.v1",
        "project": args.project,
        "suite": args.suite,
        "target_ref": args.target_ref,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": {"runner": "harness", "cluster": "kind"},
        "run": {
            "users": args.users,
            "spawn_rate": args.spawn_rate,
            "duration_s": args.duration_s,
        },
        "metrics": load_stats(args.stats_csv),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
