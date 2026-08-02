#!/usr/bin/env bash

# Source-pin and mechanically derive the exact natural-device-add candidate
# assembler from the validated normal-fallthrough workflow.
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
source_builder="$repo_root/experiments/2026-08-01-da921x-uevent-normal-fallthrough/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=048cfe65b32e109a2834b0af172fc67e1388a261a73e6337fa50913720c03cd7
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
	s#c01199475b346d7b83d5463ee11d3290e1daf74429fa92ff6692386a65c3c630#f554d18bb33c1ec9f9cdbde466f2d283d67c8f7f2a5c6167a1a127db35ac249f#g;
	s#d29c1c33370aa7edd322a2de55c4046858a1f3d25eb38e6464aaff6e33c83d2b#c96ee59324cdc2a806ebf8ad2d9ed5988c93637dad0c280da64d7fe0a233e1c9#g;
	s#40a7cd3831a1676846847a5e138a1a0dcc1219e77fe9d1e53aab71348b6ff9ab#7ef1fb9530cf4be10499c774cdc7328301782722f44af2cfc4cbdd9cd73ce875#g;
	s#a987db864163fb6ae90758e972fd6c134da7f398017e93730940b96b9a783ab4#b2e6dbc71c24191a1d5177031d3eb2ecf19aba6dfa6496719d1d147d23e6fabc#g;
	s#7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806#e2424e337a30dbc112496ae841bde655058c01d79cd399f2d518154d5faba60c#g;
	s#gemini-mt6797-da921x-uevent-normal-fallthrough\.boot\.img#gemini-mt6797-da921x-natural-device-add.boot.img#g;
	s#7\.1\.3-gemini-da921x-fallthrough#7.1.3-gemini-da921x-devadd#g;
	s#2026-08-01-da921x-uevent-normal-fallthrough#2026-08-01-da921x-natural-device-add#g;
	s#candidate-Gate3-da921x-fallthrough-#candidate-Gate3-da921x-devadd-#g;
	s#da921x-uevent-normal-fallthrough-candidate#da921x-natural-device-add-candidate#g;
	s#gemini-fall#gemini-devadd#g;
	s#CONFIG_I2C_GEMINI_DA921X_UEVENT_NORMAL_FALLTHROUGH_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_NATURAL_DEVICE_ADD_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	c01199475b346d7b83d5463ee11d3290e1daf74429fa92ff6692386a65c3c630 \
	d29c1c33370aa7edd322a2de55c4046858a1f3d25eb38e6464aaff6e33c83d2b \
	40a7cd3831a1676846847a5e138a1a0dcc1219e77fe9d1e53aab71348b6ff9ab \
	a987db864163fb6ae90758e972fd6c134da7f398017e93730940b96b9a783ab4 \
	7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806 \
	gemini-mt6797-da921x-uevent-normal-fallthrough.boot.img \
	7.1.3-gemini-da921x-fallthrough \
	2026-08-01-da921x-uevent-normal-fallthrough \
	candidate-Gate3-da921x-fallthrough- \
	validation=da921x-uevent-normal-fallthrough-candidate \
	gemini-fall; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_NATURAL_DEVICE_ADD_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks natural-device-add gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
