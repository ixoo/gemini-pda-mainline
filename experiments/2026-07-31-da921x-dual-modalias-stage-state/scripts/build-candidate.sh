#!/usr/bin/env bash

# Source-pin and mechanically derive the exact dual-modalias candidate
# assembler for the ordered-stage read-only-state kernel.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-dual-modalias-path-state/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=1cb2cb25f6fb30939aeb2c0ad7818758d21aa91f1c60c3e3e1fe4d8f9d2c8b0c
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
	s#973a54b190b5ab96c5bc44399ae23c1b37c179383d6ef30fb33a0d0c1656007f#923cfc9c54fbf58a4dd5052b0d4545f1bf2227f4ff4d1f5bb2fbfcf58fd8187d#g;
	s#8c847eb40a943c28aac00c72651db1dcf61ea1b4b5258a29cfbc25a2c6daeca8#dd3e5a8fa975f01dcca7f49919060aa164c9cb5202840be8cf670476813f09ad#g;
	s#a9fe43f18b9eafb61b6ff14c02f1dfd8e7a201c7db80d676a6f548836d2a60bf#6f871fa1906d9938643e813625aed20d9595448a57bbf8ca1af09d9aa91501c4#g;
	s#1bf7ba7711c92547e22539f78d0a93d3a0fb6db72f20b56911532c97b0ed26d7#017c3ef9fbe9df3fd2fbbdc6daa5f31c17a6237a9aef86435500413956710ff5#g;
	s#gemini-mt6797-da921x-dual-modalias-path-state\.boot\.img#gemini-mt6797-da921x-dual-modalias-stage-state.boot.img#g;
	s#7\.1\.3-gemini-da921x-pathstate#7.1.3-gemini-da921x-stagestate#g;
	s#2026-07-31-da921x-dual-modalias-path-state#2026-07-31-da921x-dual-modalias-stage-state#g;
	s#candidate-Gate3-da921x-pathstate-#candidate-Gate3-da921x-stagestate-#g;
	s#da921x-dual-modalias-path-state-candidate#da921x-dual-modalias-stage-state-candidate#g;
	s#gemini-pstate#gemini-sstate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	973a54b190b5ab96c5bc44399ae23c1b37c179383d6ef30fb33a0d0c1656007f \
	8c847eb40a943c28aac00c72651db1dcf61ea1b4b5258a29cfbc25a2c6daeca8 \
	a9fe43f18b9eafb61b6ff14c02f1dfd8e7a201c7db80d676a6f548836d2a60bf \
	1bf7ba7711c92547e22539f78d0a93d3a0fb6db72f20b56911532c97b0ed26d7 \
	gemini-mt6797-da921x-dual-modalias-path-state.boot.img \
	7.1.3-gemini-da921x-pathstate \
	2026-07-31-da921x-dual-modalias-path-state \
	candidate-Gate3-da921x-pathstate- \
	validation=da921x-dual-modalias-path-state-candidate \
	gemini-pstate; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_VALIDATION_STAGE_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks validation-stage gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
