#!/usr/bin/env bash

# Source-pin and derive the read-only pair-v5 USB/netcat collector. Changed-
# cycle pstore remains the primary observation.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-03-a72-cpu9-cluster-reuse/scripts/capture-live-outcome.sh"
readonly SOURCE_COLLECTOR_SHA256=30d3ac6fa33ac95e1909271ea50227f4e943cab29f61f692dfe5e66ec73ac51c
[[ -f "$source_collector" && ! -L "$source_collector" &&
	"$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_COLLECTOR_SHA256" ]] ||
	die 'source CPU9 collector changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-multiline-collector.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_MULTILINE_SCRIPT_DIR:?missing}"#g;
	s#a72-cpu9-attempt-#a72-cpu9-multiline-attempt-#g;
	s#A72_CPU9#A72_CPU9_MULTILINE#g;
	s#a72-cpu9-live#a72-cpu9-multiline-live#g;
	s#gemini-a72-pair-v1#gemini-a72-pair-v5#g;
	s#validation=a72-cpu9-live-outcome-pass#validation=a72-cpu9-multiline-live-outcome-pass#g;
	s#\Q( error8=-?[0-9]+ error9=-?[0-9]+)?\$\E#( error8=-?[0-9]+ error9=-?[0-9]+)? hps_reported=-?[0-9]+ hps_cpu=-?[0-9]+ hps_error=-?[0-9]+ hps_count=[0-9]+ coh_reported=-?[0-9]+ coh_rounds=[0-9]+ coh_cpu8=-?[0-9]+ coh_cpu9=-?[0-9]+ coh_error8=-?[0-9]+ coh_error9=-?[0-9]+ coh_seq8=[0-9]+ coh_seq9=[0-9]+ ml_reported=-?[0-9]+ ml_rounds=64 ml_lines=256 ml_words=8 ml_cpu8=-?[0-9]+ ml_cpu9=-?[0-9]+ ml_error8=-?[0-9]+ ml_error9=-?[0-9]+ ml_done8=[0-9]+ ml_done9=[0-9]+ ml_hash8w=[0-9a-f]{16} ml_hash8r=[0-9a-f]{16} ml_hash9w=[0-9a-f]{16} ml_hash9r=[0-9a-f]{16} ml_bad_round=-?[0-9]+ ml_bad_line=-?[0-9]+ ml_bad_word=-?[0-9]+ ml_expected=[0-9a-f]{16} ml_actual=[0-9a-f]{16}\\\$#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"

for token in \
	'a72-cpu9-multiline-attempt-N/runtime.txt' \
	'gemini-a72-pair-v5 result=(pass|fault)' \
	'ml_reported=-?[0-9]+ ml_rounds=64 ml_lines=256 ml_words=8' \
	'ml_hash8w=[0-9a-f]{16} ml_hash8r=[0-9a-f]{16} ml_hash9w=[0-9a-f]{16} ml_hash9r=[0-9a-f]{16}' \
	'__A72_CPU9_MULTILINE_LIVE_TERMINAL_CAPTURED__' \
	'validation=a72-cpu9-multiline-live-outcome-pass'; do
	grep -Fq "$token" "$derived" || die "derived collector lacks: $token"
done
! grep -Fq 'gemini-a72-pair-v1' "$derived" || die 'old pair terminal remains'
export GEMINI_CPU9_MULTILINE_SCRIPT_DIR="$script_dir"
status=0
"$derived" "$@" || status=$?
exit "$status"
