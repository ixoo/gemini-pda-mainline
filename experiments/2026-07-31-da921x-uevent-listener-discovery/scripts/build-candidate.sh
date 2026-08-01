#!/usr/bin/env bash

# Source-pin and mechanically derive the exact uevent-listener discovery
# candidate assembler from the validated netlink-serialization workflow.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-netlink-skb-serialization/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=2faa6e4abfbd93ff0858f5e17f3670cdd7310b31bd8b8c7ec73551afcb86215d
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
	s#d1030e6ab652ba753ff7a0956fc822950e42c6b2eb3fc3371781831919b4f3ee#c01521d725e39f7384efa43b9287b5623f1378f72c3559c2279d48ba4420f035#g;
	s#6dda215803c4993bfe4e8c5b67b00c63c47c8e44f14a5a564c9d8b7aa74c31fa#1c18061416f0ec1d2a281c6bd94bcdb076dbd9e2748b8c6f89fbd934bd6c65f1#g;
	s#d17642fc2f62260be390ece7c36389402b96ff2017880bb20c4808200e17a929#d9c493efb68e4fcdbf49eff4f29ff1b18fb7f779999af230cb8e71d307cada4f#g;
	s#606a532288f2455a029e6d8537ac18d9f6ed9d54e61972b871b8f9563f71050c#75b333ba0ca0b5bede5c247f0dfcff5b6a145450a191ed6e7ad5e087a0e66615#g;
	s#gemini-mt6797-da921x-netlink-skb-serialization\.boot\.img#gemini-mt6797-da921x-uevent-listener-discovery.boot.img#g;
	s#7\.1\.3-gemini-da921x-skbser#7.1.3-gemini-da921x-listen#g;
	s#2026-07-31-da921x-netlink-skb-serialization#2026-07-31-da921x-uevent-listener-discovery#g;
	s#candidate-Gate3-da921x-skbser-#candidate-Gate3-da921x-listen-#g;
	s#da921x-netlink-skb-serialization-candidate#da921x-uevent-listener-discovery-candidate#g;
	s#gemini-skbser#gemini-listen#g;
	s#CONFIG_I2C_GEMINI_DA921X_NETLINK_SERIALIZATION_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_UEVENT_LISTENER_DISCOVERY_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	d1030e6ab652ba753ff7a0956fc822950e42c6b2eb3fc3371781831919b4f3ee \
	6dda215803c4993bfe4e8c5b67b00c63c47c8e44f14a5a564c9d8b7aa74c31fa \
	d17642fc2f62260be390ece7c36389402b96ff2017880bb20c4808200e17a929 \
	606a532288f2455a029e6d8537ac18d9f6ed9d54e61972b871b8f9563f71050c \
	gemini-mt6797-da921x-netlink-skb-serialization.boot.img \
	7.1.3-gemini-da921x-skbser \
	2026-07-31-da921x-netlink-skb-serialization \
	candidate-Gate3-da921x-skbser- \
	validation=da921x-netlink-skb-serialization-candidate \
	gemini-skbser; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_UEVENT_LISTENER_DISCOVERY_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks uevent listener-discovery gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
