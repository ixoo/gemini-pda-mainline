#!/usr/bin/env bash

# Source-pin and mechanically derive the exact real-compatible, module-free
# candidate assembler for the private OF-modalias generation kernel.
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
source_builder="$repo_root/experiments/2026-07-30-da921x-module-file-isolation/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=a92dd900070e0e9f216af74f1504a08ed28b04d5aa6545cc1ae8f8dfbd04d8f7
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
	s#ffb201241bcd4561c6d3a4c6d9e140f40acaaa7a5d711dabc6b508498e46a9d6#b0b9f5aea15c553e8dea65e42247a240f9b5bedb06f6a4768e19a1147328a5bf#g;
	s#23f3affc7acb0e3ddda7ace6b51921225fd260d06eccb514e8547fadb0480964#cc7b5fc393f4db17f722b2c210b0d85f7b998d8ceb8ce63bcdc6eb84b83d07e5#g;
	s#52babe9403bce7a2f58b9bf82e3c8f71626c4f7887727b3310a772444ade2d0c#f2cbbdc388d65b8e65f41dac6299c09787682623a8dfee523c9873dd0fff9d4c#g;
	s#c182057b01b29d74972ad0264420b96f430e9cd2668d1a6cb79c02a7d849716e#6d6091f948d3fdd907086a59f66f1af8d2004d12ff842945436d3546e0a447dd#g;
	s#gemini-mt6797-da921x-real-compatible-no-module\.boot\.img#gemini-mt6797-da921x-of-modalias-private-generation.boot.img#g;
	s#7\.1\.3-gemini-da921x-mod#7.1.3-gemini-da921x-ofgen#g;
	s#2026-07-30-da921x-module-file-isolation#2026-07-30-da921x-of-modalias-private-generation#g;
	s#candidate-Gate3-da921x-real-compatible-no-module-#candidate-Gate3-da921x-of-modalias-private-generation-#g;
	s#da921x-real-compatible-no-module-candidate#da921x-of-modalias-private-generation-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	ffb201241bcd4561c6d3a4c6d9e140f40acaaa7a5d711dabc6b508498e46a9d6 \
	23f3affc7acb0e3ddda7ace6b51921225fd260d06eccb514e8547fadb0480964 \
	52babe9403bce7a2f58b9bf82e3c8f71626c4f7887727b3310a772444ade2d0c \
	c182057b01b29d74972ad0264420b96f430e9cd2668d1a6cb79c02a7d849716e \
	gemini-mt6797-da921x-real-compatible-no-module.boot.img \
	7.1.3-gemini-da921x-mod \
	2026-07-30-da921x-module-file-isolation \
	candidate-Gate3-da921x-real-compatible-no-module- \
	validation=da921x-real-compatible-no-module-candidate; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
