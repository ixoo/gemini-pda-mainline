#!/usr/bin/env bash

# Source-pin and derive the read-only bounded-coherency USB/netcat collector.
# Changed-cycle pstore remains the primary observation.
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

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-coherence-collector.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_COHERENCE_SCRIPT_DIR:?missing}"#g;
	s#a72-cpu9-attempt-#a72-cpu9-coherence-attempt-#g;
	s#A72_CPU9#A72_CPU9_COHERENCE#g;
	s#a72-cpu9-live#a72-cpu9-coherence-live#g;
	s#gemini-a72-pair-v1#gemini-a72-pair-v4#g;
	s#validation=a72-cpu9-live-outcome-pass#validation=a72-cpu9-coherence-live-outcome-pass#g;
	s#\Q( error8=-?[0-9]+ error9=-?[0-9]+)?\$\E#( error8=-?[0-9]+ error9=-?[0-9]+)? hps_reported=-?[0-9]+ hps_cpu=-?[0-9]+ hps_error=-?[0-9]+ hps_count=[0-9]+ coh_reported=-?[0-9]+ coh_rounds=[0-9]+ coh_cpu8=-?[0-9]+ coh_cpu9=-?[0-9]+ coh_error8=-?[0-9]+ coh_error9=-?[0-9]+ coh_seq8=[0-9]+ coh_seq9=[0-9]+\\\$#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"

for token in \
	'a72-cpu9-coherence-attempt-N/runtime.txt' \
	'gemini-a72-pair-v4 result=(pass|fault)' \
	'hps_reported=-?[0-9]+ hps_cpu=-?[0-9]+ hps_error=-?[0-9]+ hps_count=[0-9]+' \
	'coh_reported=-?[0-9]+ coh_rounds=[0-9]+ coh_cpu8=-?[0-9]+ coh_cpu9=-?[0-9]+ coh_error8=-?[0-9]+ coh_error9=-?[0-9]+ coh_seq8=[0-9]+ coh_seq9=[0-9]+' \
	'__A72_CPU9_COHERENCE_LIVE_TERMINAL_CAPTURED__' \
	'validation=a72-cpu9-coherence-live-outcome-pass'; do
	grep -Fq "$token" "$derived" || die "derived collector lacks: $token"
done
! grep -Fq 'gemini-a72-pair-v1' "$derived" || die 'old pair terminal remains'
export GEMINI_CPU9_COHERENCE_SCRIPT_DIR="$script_dir"
status=0
"$derived" "$@" || status=$?
exit "$status"
