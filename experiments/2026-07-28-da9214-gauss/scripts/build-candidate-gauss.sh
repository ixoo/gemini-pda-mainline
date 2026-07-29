#!/usr/bin/env bash

# Storage-inert Gauss assembler, derived at runtime from exact Fermi machinery.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$script_dir/derive-candidate.py" "$@"
