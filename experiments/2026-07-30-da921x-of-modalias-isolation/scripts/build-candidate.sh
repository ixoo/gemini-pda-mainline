#!/usr/bin/env bash

# Source-pin and mechanically derive the exact real-compatible, module-free
# candidate assembler for the focused OF-modalias kernel.
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
	s#ffb201241bcd4561c6d3a4c6d9e140f40acaaa7a5d711dabc6b508498e46a9d6#4a14211d890914128d115ae9bd4821d7a3a919e0109431753214f4ead5c5396a#g;
	s#23f3affc7acb0e3ddda7ace6b51921225fd260d06eccb514e8547fadb0480964#0eb39a7b405a06a8870d3625a7fefcb63fb8e63622c36e138ecc29078618af72#g;
	s#52babe9403bce7a2f58b9bf82e3c8f71626c4f7887727b3310a772444ade2d0c#3c4baf78f3b8a9e3b6fed3331d320c1542181f3f2ae893cbd5ad0a06ea1125d9#g;
	s#c182057b01b29d74972ad0264420b96f430e9cd2668d1a6cb79c02a7d849716e#577001f9b52aba46bc7eddc18f2b18ce99727cc7887440a95591a569c8bdd0ba#g;
	s#gemini-mt6797-da921x-real-compatible-no-module\.boot\.img#gemini-mt6797-da921x-of-modalias-isolation.boot.img#g;
	s#7\.1\.3-gemini-da921x-mod#7.1.3-gemini-da921x-ofalias#g;
	s#2026-07-30-da921x-module-file-isolation#2026-07-30-da921x-of-modalias-isolation#g;
	s#candidate-Gate3-da921x-real-compatible-no-module-#candidate-Gate3-da921x-of-modalias-isolation-#g;
	s#da921x-real-compatible-no-module-candidate#da921x-of-modalias-isolation-candidate#g;
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
