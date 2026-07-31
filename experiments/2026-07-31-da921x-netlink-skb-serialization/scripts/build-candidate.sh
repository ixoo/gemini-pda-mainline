#!/usr/bin/env bash

# Source-pin and mechanically derive the exact netlink-skb serialization
# candidate assembler from the validated corrected-event workflow.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-of-event-layout-correction/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=d7bfd5f8e28d0a4003cf6acf7744bb953ce78860b958a138d5fe01060d3ddd49
[[ -f "$source_builder" && ! -L "$source_builder" &&
	"$(sha256sum "$source_builder" | awk '{print $1}')" == \
	"$SOURCE_BUILDER_SHA256" ]] || die 'source candidate builder changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-build-candidate.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#repo_root="\$\(cd -- "\$script_dir/\.\./\.\./\.\." && pwd -P\)"#repo_root="\${GEMINI_REPO_ROOT_OVERRIDE:?missing}"#g;
	s#a768b874378c063f7cbf4f6204cedc25f0359a1a911718539acf16ce0c0cd43d#d1030e6ab652ba753ff7a0956fc822950e42c6b2eb3fc3371781831919b4f3ee#g;
	s#6a8b0a15ffc978f0dd69ae427cc5c6cb68948fe8e6e06f31d33cb40651d594ce#6dda215803c4993bfe4e8c5b67b00c63c47c8e44f14a5a564c9d8b7aa74c31fa#g;
	s#160a459e161a08cb84dcb7ce769639f6c1565b6391693afd28ae15a5b058e969#d17642fc2f62260be390ece7c36389402b96ff2017880bb20c4808200e17a929#g;
	s#7a09af3082468076966242470cd30a6fef32ea5475e0ebf7ef4879bb361a0d5b#606a532288f2455a029e6d8537ac18d9f6ed9d54e61972b871b8f9563f71050c#g;
	s#gemini-mt6797-da921x-of-event-layout-correction\.boot\.img#gemini-mt6797-da921x-netlink-skb-serialization.boot.img#g;
	s#7\.1\.3-gemini-da921x-ofevent#7.1.3-gemini-da921x-skbser#g;
	s#2026-07-31-da921x-of-event-layout-correction#2026-07-31-da921x-netlink-skb-serialization#g;
	s#candidate-Gate3-da921x-ofevent-#candidate-Gate3-da921x-skbser-#g;
	s#da921x-of-event-layout-correction-candidate#da921x-netlink-skb-serialization-candidate#g;
	s#gemini-ofevent#gemini-skbser#g;
	s#CONFIG_I2C_GEMINI_DA921X_OF_EVENT_LAYOUT_CORRECTION_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_NETLINK_SERIALIZATION_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	a768b874378c063f7cbf4f6204cedc25f0359a1a911718539acf16ce0c0cd43d \
	6a8b0a15ffc978f0dd69ae427cc5c6cb68948fe8e6e06f31d33cb40651d594ce \
	160a459e161a08cb84dcb7ce769639f6c1565b6391693afd28ae15a5b058e969 \
	7a09af3082468076966242470cd30a6fef32ea5475e0ebf7ef4879bb361a0d5b \
	gemini-mt6797-da921x-of-event-layout-correction.boot.img \
	7.1.3-gemini-da921x-ofevent \
	2026-07-31-da921x-of-event-layout-correction \
	candidate-Gate3-da921x-ofevent- \
	validation=da921x-of-event-layout-correction-candidate \
	gemini-ofevent; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done

package=
previous=
for argument in "$@"; do
	if [[ "$previous" == --package ]]; then
		package=$argument
		break
	fi
	previous=$argument
done
[[ -n "$package" && -f "$package/kernel.config" ]] ||
	die 'exact package argument is required'
grep -qx 'CONFIG_I2C_GEMINI_DA921X_NETLINK_SERIALIZATION_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks netlink serialization gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
