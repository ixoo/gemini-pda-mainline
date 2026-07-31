#!/usr/bin/env bash

# Source-pin and mechanically derive the exact one-shot USB/netcat collector
# for the bounded event-entry classification candidate.
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
source_collector="$repo_root/experiments/2026-07-31-da921x-dual-modalias-stage-state/scripts/collect-runtime.sh"
readonly SOURCE_COLLECTOR_SHA256=37bcf7c85a42b7d4bae591427ae55d9699e9ae7d8b70fd62a040d450042aa4f3
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
	s#2026-07-31-da921x-dual-modalias-stage-state/scripts/run-serviceability-check#2026-07-31-da921x-dual-modalias-entry-classification/scripts/run-serviceability-check#g;
	s#c755109e73f2148516942b2a31a3a06952abdf72c0154c5b70259836b8fcb736#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7#g;
	s#891457cb99f1729358aaa305599efc4f748a06cf3365d6e9a7ad7ed935407fc1#f67b579768c95bd4963f589e380a3142751de8cf6e23e061e631f578cb041880#g;
	s#dual_modalias_stage_state_result=PASS#dual_modalias_entry_classification_result=PASS#g;
	s#da921x-stagestate#da921x-entryclass#g;
	s#stagestate#entryclass#g;
	s#STAGESTATE#ENTRYCLASS#g;
	s#da921x-dual-modalias-stage-state-runtime#da921x-dual-modalias-entry-classification-runtime#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"
for stale in \
	c755109e73f2148516942b2a31a3a06952abdf72c0154c5b70259836b8fcb736 \
	891457cb99f1729358aaa305599efc4f748a06cf3365d6e9a7ad7ed935407fc1 \
	dual_modalias_stage_state_result=PASS \
	da921x-stagestate \
	stagestate \
	STAGESTATE; do
	! grep -Fq "$stale" "$derived" || die "derived collector retained $stale"
done
grep -Fq 'dual_modalias_entry_classification_result=PASS' "$derived" ||
	die 'derived collector lacks exact passing classifier'
# shellcheck disable=SC2016 # Require the literal deferred repository root.
grep -Fq 'runtime_check="$repo_root/experiments/2026-07-31-da921x-dual-modalias-entry-classification/scripts/run-serviceability-check.sh"' \
	"$derived" || die 'derived collector lacks exact runtime-check path'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived collector lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
