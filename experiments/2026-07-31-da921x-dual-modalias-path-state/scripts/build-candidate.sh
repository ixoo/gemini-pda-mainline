#!/usr/bin/env bash

# Source-pin and mechanically derive the exact dual-modalias candidate
# assembler for the live-path-corrected read-only-state kernel.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-dual-modalias-state/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=a799ad8e338c88c672b9f963abad3d29d74398e9a5dda6596ba5f558261b978f
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
	s#b6c43d9824685b8dcd764a2261c8fb8568e7ee723031f7c8e9a30be2bd3574da#973a54b190b5ab96c5bc44399ae23c1b37c179383d6ef30fb33a0d0c1656007f#g;
	s#779ededc15cec4a6204d399299ff1476591de2e8297fbfe098c273e225180380#8c847eb40a943c28aac00c72651db1dcf61ea1b4b5258a29cfbc25a2c6daeca8#g;
	s#a280506dfbe9ae3ecadafc26cf7e6e4fd3ab9d504e1b69a1edf40684d89bca88#a9fe43f18b9eafb61b6ff14c02f1dfd8e7a201c7db80d676a6f548836d2a60bf#g;
	s#fd9f76342305a80929194a2e8d9442925bbf3b2e4e6804b8d5266aa4c406732a#1bf7ba7711c92547e22539f78d0a93d3a0fb6db72f20b56911532c97b0ed26d7#g;
	s#gemini-mt6797-da921x-dual-modalias-state\.boot\.img#gemini-mt6797-da921x-dual-modalias-path-state.boot.img#g;
	s#7\.1\.3-gemini-da921x-dualstate#7.1.3-gemini-da921x-pathstate#g;
	s#2026-07-31-da921x-dual-modalias-state#2026-07-31-da921x-dual-modalias-path-state#g;
	s#candidate-Gate3-da921x-dualstate-#candidate-Gate3-da921x-pathstate-#g;
	s#da921x-dual-modalias-state-candidate#da921x-dual-modalias-path-state-candidate#g;
	s#gemini-dstate#gemini-pstate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	b6c43d9824685b8dcd764a2261c8fb8568e7ee723031f7c8e9a30be2bd3574da \
	779ededc15cec4a6204d399299ff1476591de2e8297fbfe098c273e225180380 \
	a280506dfbe9ae3ecadafc26cf7e6e4fd3ab9d504e1b69a1edf40684d89bca88 \
	fd9f76342305a80929194a2e8d9442925bbf3b2e4e6804b8d5266aa4c406732a \
	gemini-mt6797-da921x-dual-modalias-state.boot.img \
	7.1.3-gemini-da921x-dualstate \
	2026-07-31-da921x-dual-modalias-state \
	candidate-Gate3-da921x-dualstate- \
	validation=da921x-dual-modalias-state-candidate \
	gemini-dstate; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done
grep -Fq 'CONFIG_I2C_GEMINI_DA921X_DUAL_MODALIAS_STATE_DIAGNOSTIC=y' \
	"$derived" || die 'derived builder lacks state diagnostic gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'

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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_ROOT_PATH_CORRECTION_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks root-path correction gate'

export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
