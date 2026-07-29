#!/usr/bin/env bash
set -euo pipefail

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)

export PYTHONDONTWRITEBYTECODE=1
exec python3 "$script_dir/derive-candidate.py" "$@"
