#!/usr/bin/env bash

# Source-pin and mechanically derive the prior exact-artifact assembler. The
# only construction change selects this experiment's compatible-only DT tool.
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
source_builder="$repo_root/experiments/2026-07-30-da921x-module-client-isolation/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=a43cd6f984f9d087f7cb7c78948ddf4a2800f0af05bced14291a26e1a6b3b4d5
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
	s#2026-07-30-da921x-module-client-isolation#2026-07-30-da921x-unmatched-client#g;
	s#mt6797-gemini-pda-da921x-module-client-disabled\.dtb#mt6797-gemini-pda-da921x-unmatched-client.dtb#g;
	s#gemini-mt6797-da921x-module-client-disabled\.boot\.img#gemini-mt6797-da921x-unmatched-client.boot.img#g;
	s#8429af31ec88df40882d7711ee3a87718b651ae2c703d1a15699141104d521fe#ea47ee9578654ff9fab24502fba7458f8cff78f72977c403776443739966d68e#g;
	s#experiments/2026-07-29-da921x-probe-isolation/scripts/build-isolation-dtb\.sh#experiments/2026-07-30-da921x-unmatched-client/scripts/build-unmatched-dtb.sh#g;
	s#\.module-client-isolation#\.unmatched-client#g;
	s#/i2c\@1100e000/regulator\@68-status-disabled#/i2c\@1100e000/regulator\@68-compatible-dlg,da9214-legacy-to-dlg,da9214-unbound#g;
	s#candidate-Gate3-da921x-module-client-disabled-#candidate-Gate3-da921x-unmatched-client-#g;
	s#da921x-module-client-isolation-candidate#da921x-unmatched-client-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	2026-07-30-da921x-module-client-isolation \
	mt6797-gemini-pda-da921x-module-client-disabled.dtb \
	8429af31ec88df40882d7711ee3a87718b651ae2c703d1a15699141104d521fe \
	build-isolation-dtb.sh \
	'/i2c@1100e000/regulator@68-status-disabled'; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
