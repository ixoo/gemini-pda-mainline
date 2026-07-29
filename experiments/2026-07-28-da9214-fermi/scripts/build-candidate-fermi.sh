#!/usr/bin/env bash

# Storage-inert Fermi assembler. The implementation is derived at runtime
# from exact source-pinned Quasar assembly machinery and has no device interface.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$script_dir/derive-candidate.py" "$@"
