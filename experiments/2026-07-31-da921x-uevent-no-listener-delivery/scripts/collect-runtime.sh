#!/usr/bin/env bash

# Source-pin and mechanically derive the exact one-shot USB/netcat collector
# for the no-listener delivery candidate.
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
source_collector="$repo_root/experiments/2026-07-31-da921x-uevent-listener-discovery/scripts/collect-runtime.sh"
readonly SOURCE_COLLECTOR_SHA256=b28b807c33aa806a5ce06d45120a62549ddeeaae25bfc1a38d61a8e193b07758
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
	s#2026-07-31-da921x-uevent-listener-discovery/scripts/run-serviceability-check#2026-07-31-da921x-uevent-no-listener-delivery/scripts/run-serviceability-check#g;
	s#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0#g;
	s#f5a6f58e2ddaee84e6f1653f13945ee9113b385b3c9c75187745125e5d5dc542#6a14a5d1218a4d10fb3b9966ff4b829a53dd980d5a29e2221fed971b0e715cd9#g;
	s#uevent_listener_discovery_result=PASS#uevent_no_listener_delivery_result=PASS#g;
	s#da921x-uevent-listener-discovery-runtime#da921x-uevent-no-listener-delivery-runtime#g;
	s#da921x-listen#da921x-nodeliv#g;
	s{s\#skbser\#listen\#g;}{s#skbser#nodeliv#g;}g;
	s{s\#SKBSER\#LISTEN\#g;}{s#SKBSER#NODELIV#g;}g;
' "$source_collector" >"$derived"
chmod 0700 "$derived"
for stale in \
	2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a \
	f5a6f58e2ddaee84e6f1653f13945ee9113b385b3c9c75187745125e5d5dc542 \
	'uevent_listener_discovery_result=PASS' \
	da921x-listen \
	's#skbser#listen#g;' \
	's#SKBSER#LISTEN#g;'; do
	! grep -Fq "$stale" "$derived" || die "derived collector retained $stale"
done
grep -Fq 'uevent_no_listener_delivery_result=PASS' "$derived" ||
	die 'derived collector lacks exact passing no-listener result'
# shellcheck disable=SC2016 # Require the literal deferred repository root.
grep -Fq 'runtime_check="$repo_root/experiments/2026-07-31-da921x-uevent-no-listener-delivery/scripts/run-serviceability-check.sh"' \
	"$derived" || die 'derived collector lacks exact runtime-check path'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived collector lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
