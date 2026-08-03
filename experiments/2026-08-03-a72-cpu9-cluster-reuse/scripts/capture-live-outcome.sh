#!/usr/bin/env bash

# Source-pin and derive the read-only CPU9 USB/netcat terminal collector.
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
source_collector="$repo_root/experiments/2026-08-02-a72-cpu8-held-online/scripts/capture-live-outcome.sh"
readonly SOURCE_COLLECTOR_SHA256=0b316d4028df77a1ae03263ea185c9f34955dc35260e4bced5de395cb3078f16
[[ -f "$source_collector" && ! -L "$source_collector" &&
	"$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_COLLECTOR_SHA256" ]] ||
	die 'source held-online collector changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-collector.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_SCRIPT_DIR:?missing}"#g;
	s#a72-held-attempt-#a72-cpu9-attempt-#g;
	s#A72_HELD#A72_CPU9#g;
	s#a72-held-live#a72-cpu9-live#g;
	s#hold_terminal#pair_terminal#g;
	s#hold_trace#pair_trace#g;
	s#gemini-a72-hold-v1#gemini-a72-pair-v1#g;
	s#validation=a72-held-live-outcome-pass#validation=a72-cpu9-live-outcome-pass#g;
	s#pair_terminal_line=\.\*gemini-a72-pair-v1 result=.*?\$#pair_terminal_line=.*gemini-a72-pair-v1 result=(pass|fault) sample=[123] cpu8=-?[0-9]+ cpu9=-?[0-9]+ online8=[01] online9=[01] hits8=[0-9]+ hits9=[0-9]+( error8=-?[0-9]+ error9=-?[0-9]+)?\$#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"

for token in \
	'a72-cpu9-attempt-N/runtime.txt' \
	'gemini-a72-pair-v1 result=(pass|fault)' \
	'pair_terminal_line=.*gemini-a72-pair-v1 result=(pass|fault) sample=[123]' \
	'__A72_CPU9_LIVE_TERMINAL_CAPTURED__' \
	'validation=a72-cpu9-live-outcome-pass'; do
	grep -Fq "$token" "$derived" || die "derived collector lacks: $token"
done
! grep -Fq 'gemini-a72-hold-v1' "$derived" || die 'old terminal version remains'
export GEMINI_CPU9_SCRIPT_DIR="$script_dir"
status=0
"$derived" "$@" || status=$?
exit "$status"
