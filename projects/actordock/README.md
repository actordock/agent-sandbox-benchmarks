# Actordock benchmarks

Locust load tests against the Actordock runtime control plane (adapted from Substrate `benchmarking/`).

## Prerequisites

- Docker, kubectl, go, git
- Kind cluster created by `actordock/hack/install-local.sh` (via `install.sh`)

## Environment

| Variable | Default |
|----------|---------|
| `ACTORDOCK_REPO` | `https://github.com/actordock/actordock.git` |
| `ACTORDOCK_REF` | `main` |
| `BUCKET_NAME` | `actordock-snapshots` |
| `LOCUST_IMAGE` | `localhost:5001/locust-actordock:latest` |
| `BENCH_RUN_TIME` | `90s` (sleep-workload), `60s` (runtime-api) |

## Suites

- **runtime-api** — headless `runtime_api.py` (Substrate `ate-api` style).
- **sleep-workload** — `sleep.py` with `BurstShape`; deploy with `deploy-deps.sh --workloads`.
