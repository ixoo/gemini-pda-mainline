#!/usr/bin/env bash

# Source-pin and mechanically derive the exact dual-modalias candidate
# assembler for the read-only event-envelope state kernel.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-dual-modalias-stage-state/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=8452c49a8f1669aae9385da08744c1a0d0dc9c021b8886fffb0a8234e9010b84
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
	s#923cfc9c54fbf58a4dd5052b0d4545f1bf2227f4ff4d1f5bb2fbfcf58fd8187d#8daf912d044fc23ba72b961fac12c2776a28d1dd9ba9de13b7afedff95b98cd8#g;
	s#dd3e5a8fa975f01dcca7f49919060aa164c9cb5202840be8cf670476813f09ad#e6e36c2bfe0513eaa1f9e779c5b6611298eeb94a3e5f5a395bf983416c46fda8#g;
	s#6f871fa1906d9938643e813625aed20d9595448a57bbf8ca1af09d9aa91501c4#de5590afd89b9d1e92136133d3be30e1af89c481af75887d107f1eeae17de20b#g;
	s#017c3ef9fbe9df3fd2fbbdc6daa5f31c17a6237a9aef86435500413956710ff5#48ad674db4e5a9b1b73804ce8fa74cff82046691a0894ed2138cfb38ff7ef4e9#g;
	s#gemini-mt6797-da921x-dual-modalias-stage-state\.boot\.img#gemini-mt6797-da921x-dual-modalias-envelope-state.boot.img#g;
	s#7\.1\.3-gemini-da921x-stagestate#7.1.3-gemini-da921x-envstate#g;
	s#2026-07-31-da921x-dual-modalias-stage-state#2026-07-31-da921x-dual-modalias-envelope-state#g;
	s#candidate-Gate3-da921x-stagestate-#candidate-Gate3-da921x-envstate-#g;
	s#da921x-dual-modalias-stage-state-candidate#da921x-dual-modalias-envelope-state-candidate#g;
	s#gemini-sstate#gemini-envstate#g;
	s#CONFIG_I2C_GEMINI_DA921X_VALIDATION_STAGE_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_ENVELOPE_STATE_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	923cfc9c54fbf58a4dd5052b0d4545f1bf2227f4ff4d1f5bb2fbfcf58fd8187d \
	dd3e5a8fa975f01dcca7f49919060aa164c9cb5202840be8cf670476813f09ad \
	6f871fa1906d9938643e813625aed20d9595448a57bbf8ca1af09d9aa91501c4 \
	017c3ef9fbe9df3fd2fbbdc6daa5f31c17a6237a9aef86435500413956710ff5 \
	gemini-mt6797-da921x-dual-modalias-stage-state.boot.img \
	7.1.3-gemini-da921x-stagestate \
	2026-07-31-da921x-dual-modalias-stage-state \
	candidate-Gate3-da921x-stagestate- \
	validation=da921x-dual-modalias-stage-state-candidate \
	gemini-sstate; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_ENVELOPE_STATE_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks envelope-state gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
