#!/usr/bin/env bash

# Source-pin and mechanically derive the exact normal-fallthrough candidate
# assembler from the validated untagged-dispatch workflow.
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
source_builder="$repo_root/experiments/2026-08-01-da921x-uevent-untagged-dispatch/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=2a3e5b9bec62a12c444997b780ef184009ffa1ccc58be4b4202c732284d563f7
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
	s#6bac74cbe4f997ec874b7d72054acd6132d35f120b5505df08868e434a8cc126#c01199475b346d7b83d5463ee11d3290e1daf74429fa92ff6692386a65c3c630#g;
	s#1476e35697d41535cf6fe3b670cdecf1a3dda248b88549afe6f9afb050e984b3#d29c1c33370aa7edd322a2de55c4046858a1f3d25eb38e6464aaff6e33c83d2b#g;
	s#864a3ed384f4ae2ed7b67595189c0a5a016f843002e6d523e3dc38d84b2d94a7#40a7cd3831a1676846847a5e138a1a0dcc1219e77fe9d1e53aab71348b6ff9ab#g;
	s#3670e482ae6185018e7232af82004dbc61ea4936f0e794d9ec542cba92c15309#a987db864163fb6ae90758e972fd6c134da7f398017e93730940b96b9a783ab4#g;
	s#gemini-mt6797-da921x-uevent-untagged-dispatch\.boot\.img#gemini-mt6797-da921x-uevent-normal-fallthrough.boot.img#g;
	s#7\.1\.3-gemini-da921x-untag#7.1.3-gemini-da921x-fallthrough#g;
	s#2026-08-01-da921x-uevent-untagged-dispatch#2026-08-01-da921x-uevent-normal-fallthrough#g;
	s#candidate-Gate3-da921x-untag-#candidate-Gate3-da921x-fallthrough-#g;
	s#da921x-uevent-untagged-dispatch-candidate#da921x-uevent-normal-fallthrough-candidate#g;
	s#gemini-untag#gemini-fall#g;
	s#CONFIG_I2C_GEMINI_DA921X_UEVENT_UNTAGGED_DISPATCH_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_UEVENT_NORMAL_FALLTHROUGH_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	6bac74cbe4f997ec874b7d72054acd6132d35f120b5505df08868e434a8cc126 \
	1476e35697d41535cf6fe3b670cdecf1a3dda248b88549afe6f9afb050e984b3 \
	864a3ed384f4ae2ed7b67595189c0a5a016f843002e6d523e3dc38d84b2d94a7 \
	3670e482ae6185018e7232af82004dbc61ea4936f0e794d9ec542cba92c15309 \
	gemini-mt6797-da921x-uevent-untagged-dispatch.boot.img \
	7.1.3-gemini-da921x-untag \
	2026-08-01-da921x-uevent-untagged-dispatch \
	candidate-Gate3-da921x-untag- \
	validation=da921x-uevent-untagged-dispatch-candidate \
	gemini-untag; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_UEVENT_NORMAL_FALLTHROUGH_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks normal-fallthrough gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
