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
| `BENCH_USERS` | `3` (Substrate `BurstShape` peak) |
| `BENCH_SPAWN_RATE` | `1` |
| `BENCH_RUN_TIME` | `60s` |

## Suites

- **runtime-api** — uses `actordock/base` ActorTemplate; no extra workloads.
- **sleep-workload** — deploy with `deploy-deps.sh --workloads`.
