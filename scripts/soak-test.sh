#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 PID [DURATION_HOURS]" >&2
  exit 2
fi

project_root="$(cd "$(dirname "$0")/.." && pwd)"
target_process_id="$1"
duration_hours="${2:-72}"

exec "$project_root/.venv/bin/garage-lpr-soak" \
  --pid "$target_process_id" \
  --duration-hours "$duration_hours" \
  --interval-seconds 60 \
  --warmup-minutes 10 \
  --report "$project_root/runtime/soak/latest.json"
