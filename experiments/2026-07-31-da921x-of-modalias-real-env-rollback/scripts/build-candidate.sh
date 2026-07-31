#!/usr/bin/env bash

# Source-pin and mechanically derive the exact real-compatible, module-free
# candidate assembler for the real uevent rollback kernel.
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
	s#ffb201241bcd4561c6d3a4c6d9e140f40acaaa7a5d711dabc6b508498e46a9d6#92620e87657134a7479ed87df3c3fa74773672fd5089b68e69ecb1e7dfd3937c#g;
	s#23f3affc7acb0e3ddda7ace6b51921225fd260d06eccb514e8547fadb0480964#46cb6d8eb286b03f831b252980dc365bcf6bffd4aa722287821097552ebf72ec#g;
	s#52babe9403bce7a2f58b9bf82e3c8f71626c4f7887727b3310a772444ade2d0c#3e79ab0a9a9b112fe4811b245d9244433e955c8f047ac0d344d05daf2805b91a#g;
	s#c182057b01b29d74972ad0264420b96f430e9cd2668d1a6cb79c02a7d849716e#0b56beea6057353392fb5c77901f4edd997afc288f08c720c45be80127581e25#g;
	s#gemini-mt6797-da921x-real-compatible-no-module\.boot\.img#gemini-mt6797-da921x-of-modalias-real-env-rollback.boot.img#g;
	s#7\.1\.3-gemini-da921x-mod#7.1.3-gemini-da921x-ofrollback#g;
	s#2026-07-30-da921x-module-file-isolation#2026-07-31-da921x-of-modalias-real-env-rollback#g;
	s#candidate-Gate3-da921x-real-compatible-no-module-#candidate-Gate3-da921x-of-modalias-real-env-rollback-#g;
	s#da921x-real-compatible-no-module-candidate#da921x-of-modalias-real-env-rollback-candidate#g;
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
