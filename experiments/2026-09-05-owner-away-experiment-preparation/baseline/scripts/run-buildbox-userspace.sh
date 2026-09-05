#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Exact Git-based userspace build or validated package recovery; no kernel tree.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$here/buildbox_userspace.py" "$@"
