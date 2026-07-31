#!/usr/bin/env bash

# Source-pin and mechanically derive the exact read-only acceptance check for
# one fresh selected netlink skb serialization boot.
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
source_check="$repo_root/experiments/2026-07-31-da921x-of-event-layout-correction/scripts/run-serviceability-check.sh"
readonly SOURCE_CHECK_SHA256=d260464c5bfe84e93efdcb0696a33c40b129614c4aaf7d44667473cb6f67e5a8
[[ -f "$source_check" && ! -L "$source_check" &&
	"$(sha256sum "$source_check" | awk '{print $1}')" == \
	"$SOURCE_CHECK_SHA256" ]] || die 'source runtime check changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-runtime-check.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#7\.1\.3-gemini-da921x-ofevent#7.1.3-gemini-da921x-skbser#g;
	s#\[ "\$stage" = 17 \]#\[ "\$stage" = 18 \]#g;
	s#event_transport=skipped#event_transport=skb-consumed-before-socket-traversal-or-multicast#g;
	s#of_event_layout_correction_result=PASS#netlink_serialization_result=PASS#g;
' "$source_check" >"$derived"
chmod 0700 "$derived"
for stale in \
	7.1.3-gemini-da921x-ofevent \
	'event_transport=skipped' \
	'of_event_layout_correction_result=PASS'; do
	! grep -Fq "$stale" "$derived" || die "derived runtime check retained $stale"
done
# shellcheck disable=SC2016 # Require the literal deferred device-side stage.
grep -Fq '[ "$stage" = 18 ]' "$derived" ||
	die 'derived runtime check lacks exact stage 18 gate'
grep -Fq 'netlink_serialization_result=PASS' "$derived" ||
	die 'derived runtime check lacks exact passing result'
status=0
"$derived" "$@" || status=$?
exit "$status"
