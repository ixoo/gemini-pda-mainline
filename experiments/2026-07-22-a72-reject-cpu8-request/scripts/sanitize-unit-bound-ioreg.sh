#!/usr/bin/env bash

# Adapter used only by collect-unit-bound-cycle.sh.  The source cycle watcher
# needs to know whether the candidate's non-unit-unique marker is present, but
# must never persist the host's raw USB registry or any plaintext serial.

set -euo pipefail
export LC_ALL=C

readonly CANDIDATE_MARKER=GEMINI_OBSERVABILITY_20260717_L

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

real_ioreg=${AJ_UNIT_BOUND_REAL_IOREG:-}
[[ "$real_ioreg" == /* && "$real_ioreg" != *$'\n'* ]] || \
	die 'AJ_UNIT_BOUND_REAL_IOREG is not one absolute path'
[[ -f "$real_ioreg" && ! -L "$real_ioreg" && -x "$real_ioreg" ]] || \
	die 'real ioreg command is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$real_ioreg")" && pwd -P)/$(basename -- "$real_ioreg")" == \
	"$real_ioreg" ]] || die 'real ioreg path contains an intermediate symlink'

# awk sees the raw stream only in memory.  Its sole output is a generic marker
# state.  It cannot emit a USB serial, product string, registry path, or other
# host/device property.
"$real_ioreg" "$@" | awk -v marker="$CANDIDATE_MARKER" '
	index($0, marker) { present = 1 }
	END {
		if (present) {
			print "candidate_mainline_marker=GEMINI_OBSERVABILITY_20260717_L"
		} else {
			print "candidate_mainline_marker=absent"
		}
	}
'
