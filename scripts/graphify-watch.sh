#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_path_file="$project_dir/graphify-out/.graphify_python"

if [ ! -f "$python_path_file" ]; then
  echo "Önce proje kökünde tam bir graphify çalıştırın." >&2
  exit 1
fi

"$(cat "$python_path_file")" -m graphify.watch "$project_dir" --debounce 3
