#!/usr/bin/env bash

# Source-pin and mechanically derive the exact one-shot USB/netcat collector
# for the uevent listener-discovery candidate.
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
source_collector="$repo_root/experiments/2026-07-31-da921x-netlink-skb-serialization/scripts/collect-runtime.sh"
readonly SOURCE_COLLECTOR_SHA256=2e3207c3ff4ebeabe0f8444bd6b24f5e15868ad2b86f2b6faf15efc252a88f40
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
	s#2026-07-31-da921x-netlink-skb-serialization/scripts/run-serviceability-check#2026-07-31-da921x-uevent-listener-discovery/scripts/run-serviceability-check#g;
	s#64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;
	s#8f6ba4eb337dd1c8695b8b1cfceb87af54b8e71a0f542ab183f3005167639903#f5a6f58e2ddaee84e6f1653f13945ee9113b385b3c9c75187745125e5d5dc542#g;
	s#netlink_serialization_result=PASS#uevent_listener_discovery_result=PASS#g;
	s#da921x-netlink-skb-serialization-runtime#da921x-uevent-listener-discovery-runtime#g;
	s#da921x-skbser#da921x-listen#g;
	s#skbser#listen#g;
	s#SKBSER#LISTEN#g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"
for stale in \
	64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec \
	8f6ba4eb337dd1c8695b8b1cfceb87af54b8e71a0f542ab183f3005167639903 \
	'netlink_serialization_result=PASS' \
	da921x-skbser \
	skbser \
	SKBSER; do
	! grep -Fq "$stale" "$derived" || die "derived collector retained $stale"
done
grep -Fq 'uevent_listener_discovery_result=PASS' "$derived" ||
	die 'derived collector lacks exact passing listener-discovery result'
# shellcheck disable=SC2016 # Require the literal deferred repository root.
grep -Fq 'runtime_check="$repo_root/experiments/2026-07-31-da921x-uevent-listener-discovery/scripts/run-serviceability-check.sh"' \
	"$derived" || die 'derived collector lacks exact runtime-check path'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived collector lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
