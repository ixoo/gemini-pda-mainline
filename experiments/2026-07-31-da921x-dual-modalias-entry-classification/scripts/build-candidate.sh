#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded classifier candidate
# assembler from the validated event-envelope candidate workflow.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-dual-modalias-envelope-state/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=a303f606bf6d7c45f7c359502cc5279f7648d89535e85de7c2d2d653fee075a3
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
	s#8daf912d044fc23ba72b961fac12c2776a28d1dd9ba9de13b7afedff95b98cd8#db0b03d4dce1065019f6802ae9c4c55f334d945028ab3c4822a2b6fe4e17435f#g;
	s#e6e36c2bfe0513eaa1f9e779c5b6611298eeb94a3e5f5a395bf983416c46fda8#7ffed94fb7da03163aa7f5d6432b67a1bc82feca73fcd2e83be43e207d235fe9#g;
	s#de5590afd89b9d1e92136133d3be30e1af89c481af75887d107f1eeae17de20b#6763573e3f5d67aa3f2950d73ba6a4d0e3242c57d31ba8ab3f457ad9c58b6cf8#g;
	s#48ad674db4e5a9b1b73804ce8fa74cff82046691a0894ed2138cfb38ff7ef4e9#5f8d101c7df23e74860ac517b5055b14e39f302726c80223a6bc713a19d9d453#g;
	s#gemini-mt6797-da921x-dual-modalias-envelope-state\.boot\.img#gemini-mt6797-da921x-dual-modalias-entry-classification.boot.img#g;
	s#7\.1\.3-gemini-da921x-envstate#7.1.3-gemini-da921x-entryclass#g;
	s#2026-07-31-da921x-dual-modalias-envelope-state#2026-07-31-da921x-dual-modalias-entry-classification#g;
	s#candidate-Gate3-da921x-envstate-#candidate-Gate3-da921x-entryclass-#g;
	s#da921x-dual-modalias-envelope-state-candidate#da921x-dual-modalias-entry-classification-candidate#g;
	s#gemini-envstate#gemini-entrycls#g;
	s#CONFIG_I2C_GEMINI_DA921X_ENVELOPE_STATE_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_ENTRY_CLASSIFICATION_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	8daf912d044fc23ba72b961fac12c2776a28d1dd9ba9de13b7afedff95b98cd8 \
	e6e36c2bfe0513eaa1f9e779c5b6611298eeb94a3e5f5a395bf983416c46fda8 \
	de5590afd89b9d1e92136133d3be30e1af89c481af75887d107f1eeae17de20b \
	48ad674db4e5a9b1b73804ce8fa74cff82046691a0894ed2138cfb38ff7ef4e9 \
	gemini-mt6797-da921x-dual-modalias-envelope-state.boot.img \
	7.1.3-gemini-da921x-envstate \
	2026-07-31-da921x-dual-modalias-envelope-state \
	candidate-Gate3-da921x-envstate- \
	validation=da921x-dual-modalias-envelope-state-candidate \
	gemini-envstate; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_ENTRY_CLASSIFICATION_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks entry-classification gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
