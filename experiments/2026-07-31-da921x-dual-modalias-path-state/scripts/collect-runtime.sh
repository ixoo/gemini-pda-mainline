#!/usr/bin/env bash

# Source-pin and mechanically derive the exact one-shot USB/netcat collector
# for the live-path-corrected dual-modalias state candidate.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-07-31-da921x-dual-modalias-state/scripts/collect-runtime.sh"
readonly SOURCE_COLLECTOR_SHA256=8264351895d0cf4c7bd57e65c28d6e93dcc12057651ee73f244abdc36991c805
[[ -f "$source_collector" && ! -L "$source_collector" &&
	"$(sha256sum "$source_collector" | awk '{print $1}')" == \
	"$SOURCE_COLLECTOR_SHA256" ]] || die 'source runtime collector changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-collect-runtime.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#repo_root="\$\(cd -- "\$script_dir/\.\./\.\./\.\." && pwd -P\)"#repo_root="\${GEMINI_REPO_ROOT_OVERRIDE:?missing}"#g;
	s#5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3#f3ef6a90777b14f3b1ffed2fa23f9497ec5472d380aaaa59db0fb8bd706c4015#g;
	s#d4fae94c17bdcd901c6c269b778a1ccd6cbdde37ff646bc503fcf0bef3254bc9#aab8af12585c8d6a74de8a2c25ef4882c72838681e96fa876fa2a020ae6df806#g;
	s#dual_modalias_state_result=PASS#dual_modalias_path_state_result=PASS#g;
	s#da921x-dualstate#da921x-pathstate#g;
	s#dualstate#pathstate#g;
	s#DUALSTATE#PATHSTATE#g;
	s#da921x-dual-modalias-state-runtime#da921x-dual-modalias-path-state-runtime#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"
for stale in \
	5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3 \
	d4fae94c17bdcd901c6c269b778a1ccd6cbdde37ff646bc503fcf0bef3254bc9 \
	dual_modalias_state_result=PASS \
	da921x-dualstate \
	dualstate \
	DUALSTATE; do
	! grep -Fq "$stale" "$derived" || die "derived collector retained $stale"
done
grep -Fq 'dual_modalias_path_state_result=PASS' "$derived" ||
	die 'derived collector lacks exact passing classifier'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived collector lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
