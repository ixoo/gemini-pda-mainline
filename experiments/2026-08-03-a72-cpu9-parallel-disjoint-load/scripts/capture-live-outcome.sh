#!/usr/bin/env bash

# Source-pin and derive the read-only pair-v6 USB/netcat collector. Changed-
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
source_collector="$repo_root/experiments/2026-08-03-a72-cpu9-multiline-integrity/scripts/capture-live-outcome.sh"
readonly SOURCE_COLLECTOR_SHA256=1ac4ab27737b46ceb718b76583b081408b0df977284b9adca1046cbb11013d9a
[[ -f "$source_collector" && ! -L "$source_collector" &&
	"$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_COLLECTOR_SHA256" ]] ||
	die 'source pair-v5 collector changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-parallel-collector.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_PARALLEL_SCRIPT_DIR:?missing}"#g;
	s#a72-cpu9-multiline-attempt-#a72-cpu9-parallel-attempt-#g;
	s#A72_CPU9_MULTILINE#A72_CPU9_PARALLEL#g;
	s#a72-cpu9-multiline-live#a72-cpu9-parallel-live#g;
	s#gemini-a72-pair-v5#gemini-a72-pair-v6#g;
	s#validation=a72-cpu9-multiline-live-outcome-pass#validation=a72-cpu9-parallel-live-outcome-pass#g;
	s#\Qml_actual=[0-9a-f]{16}\E#ml_actual=[0-9a-f]{16} pl_reported=-?[0-9]+ pl_rounds=128 pl_lines=1024 pl_words=8 pl_cpu8=-?[0-9]+ pl_cpu9=-?[0-9]+ pl_error8=-?[0-9]+ pl_error9=-?[0-9]+ pl_done8=[0-9]+ pl_done9=[0-9]+ pl_ready=[0-9]+ pl_written=[0-9]+ pl_verified=[0-9]+ pl_hash8w=[0-9a-f]{16} pl_hash8r=[0-9a-f]{16} pl_hash9w=[0-9a-f]{16} pl_hash9r=[0-9a-f]{16} pl_bad_round=-?[0-9]+ pl_bad_line=-?[0-9]+ pl_bad_word=-?[0-9]+ pl_expected=[0-9a-f]{16} pl_actual=[0-9a-f]{16}#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"

for token in \
	'a72-cpu9-parallel-attempt-N/runtime.txt' \
	'gemini-a72-pair-v6 result=(pass|fault)' \
	'pl_reported=-?[0-9]+ pl_rounds=128 pl_lines=1024 pl_words=8' \
	'pl_hash8w=[0-9a-f]{16} pl_hash8r=[0-9a-f]{16} pl_hash9w=[0-9a-f]{16} pl_hash9r=[0-9a-f]{16}' \
	'__A72_CPU9_PARALLEL_LIVE_TERMINAL_CAPTURED__' \
	'validation=a72-cpu9-parallel-live-outcome-pass'; do
	grep -Fq "$token" "$derived" || die "derived collector lacks: $token"
done
! grep -Fq 'gemini-a72-pair-v5' "$derived" || die 'old pair terminal remains'
export GEMINI_CPU9_PARALLEL_SCRIPT_DIR="$script_dir"
status=0
"$derived" "$@" || status=$?
exit "$status"
