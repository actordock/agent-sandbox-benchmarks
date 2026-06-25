# agent-sandbox-benchmarks

Cross-project sandbox performance benchmarks for the [actordock](https://github.com/orgs/actordock) org.

Each target lives under `projects/<name>/` with install scripts, Locust suites, and CI matrix entries. Results use a unified JSON schema in `schema/result.v1.json`.

## Layout

```
projects/actordock/   # Actordock + runtime (first target)
harness/              # Shared runner and summarizer
schema/               # result.v1.json
.github/workflows/    # CI matrix: project x suite
```

## Quick start (actordock)

```bash
cd projects/actordock
./install.sh
./deploy-deps.sh --workloads    # required for sleep-workload suite
./build-locust-image.sh
../../harness/run_suite.sh actordock runtime-api
```

Results are written to `results/actordock-runtime-api.json`.

## Suites (actordock)

| Suite | Measures |
|-------|----------|
| `runtime-api` | gRPC GetActor / ResumeActor / SuspendActor |
| `sleep-workload` | Suspend / Resume on busybox sleep template |

## CI

Workflow `benchmark.yaml` is **manual only** (`workflow_dispatch`).

```bash
gh workflow run benchmark.yaml -R actordock/agent-sandbox-benchmarks -f actordock_ref=main
```

Results are uploaded as JSON artifacts (`results/actordock-<suite>.json`) and summarized in the GitHub Actions job summary.

