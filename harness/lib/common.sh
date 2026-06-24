# shellcheck shell=bash
# Shared helpers for benchmark harness scripts.

benchmarks_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

log_step() {
  printf '\033[1;36m[benchmark] %s\033[0m\n' "$1" >&2
}

die() {
  echo "error: $*" >&2
  exit 1
}

require_cmd() {
  local cmd
  for cmd in "$@"; do
    command -v "${cmd}" >/dev/null 2>&1 || die "missing required command: ${cmd}"
  done
}

project_dir() {
  local project="$1"
  local root
  root="$(benchmarks_root)"
  local dir="${root}/projects/${project}"
  [[ -d "${dir}" ]] || die "unknown project: ${project} (expected ${dir})"
  printf '%s\n' "${dir}"
}
