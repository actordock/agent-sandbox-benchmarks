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

Workflow `benchmark.yaml` runs:

- **Nightly** (04:00 UTC) against `actordock` `main`
- **On `workflow_dispatch`** (manual, optional `actordock_ref` input)
- **On `repository_dispatch`** when upstream `actordock` pushes to `main`

Results are uploaded as JSON artifacts (`results/actordock-<suite>.json`) and summarized in the GitHub Actions job summary.

### Upstream auto-trigger

`actordock` repo workflow `trigger-benchmarks.yaml` dispatches `actordock-updated` to this repo.

Create a fine-grained PAT (or classic token) with `contents: read` on this repo and `actions: write` if needed, then add to **actordock** repo secret:

`BENCHMARKS_DISPATCH_TOKEN`
