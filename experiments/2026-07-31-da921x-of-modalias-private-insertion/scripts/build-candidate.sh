#!/usr/bin/env bash

# Source-pin and mechanically derive the exact real-compatible, module-free
# candidate assembler for the private uevent-insertion kernel.
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
	s#ffb201241bcd4561c6d3a4c6d9e140f40acaaa7a5d711dabc6b508498e46a9d6#eb41b8db9b889ae60b103d35590e8916ef33e12890760674d628b45e86142e32#g;
	s#23f3affc7acb0e3ddda7ace6b51921225fd260d06eccb514e8547fadb0480964#2a714a8139f24fe9d8e6cbb1b809c8f496351cc92254f90f00238e5e89913c12#g;
	s#52babe9403bce7a2f58b9bf82e3c8f71626c4f7887727b3310a772444ade2d0c#e07181784060734290098f28233aa11a9cbd5bc58fafa164b1cd7870dc491403#g;
	s#c182057b01b29d74972ad0264420b96f430e9cd2668d1a6cb79c02a7d849716e#72e2a605e205c8ab259e00042c4954915008101b0e8b7c5e5061be5434979f65#g;
	s#gemini-mt6797-da921x-real-compatible-no-module\.boot\.img#gemini-mt6797-da921x-of-modalias-private-insertion.boot.img#g;
	s#7\.1\.3-gemini-da921x-mod#7.1.3-gemini-da921x-ofinsert#g;
	s#2026-07-30-da921x-module-file-isolation#2026-07-31-da921x-of-modalias-private-insertion#g;
	s#candidate-Gate3-da921x-real-compatible-no-module-#candidate-Gate3-da921x-of-modalias-private-insertion-#g;
	s#da921x-real-compatible-no-module-candidate#da921x-of-modalias-private-insertion-candidate#g;
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
