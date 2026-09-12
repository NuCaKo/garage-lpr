#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
venv_python="$project_dir/.venv/bin/python"

if [ ! -x "$venv_python" ]; then
  python3 -m venv "$project_dir/.venv"
  "$venv_python" -m pip install -e "$project_dir/backend[dev]"
fi

if [ ! -d "$project_dir/frontend/node_modules" ]; then
  npm --prefix "$project_dir/frontend" install
fi

"$venv_python" -m alembic -c "$project_dir/backend/alembic.ini" upgrade head
npm --prefix "$project_dir/frontend" run dev &
frontend_pid=$!
trap 'kill "$frontend_pid" 2>/dev/null || true' EXIT INT TERM
"$venv_python" -m garage_lpr
