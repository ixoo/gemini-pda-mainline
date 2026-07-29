#!/usr/bin/env bash

# Storage-inert Quasar assembler. The implementation is derived at runtime
# from the exact source-pinned Vega assembler and has no device interface.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$script_dir/derive-candidate.py" "$@"
