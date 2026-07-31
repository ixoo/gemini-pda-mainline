#!/usr/bin/env bash

# Source-pin and mechanically derive the no-module assembler. The sole boot
# semantic change disables the real-compatible DT child.
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
readonly DTB_BUILDER_SHA256=8429af31ec88df40882d7711ee3a87718b651ae2c703d1a15699141104d521fe
dtb_builder="$repo_root/experiments/2026-07-29-da921x-probe-isolation/scripts/build-isolation-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" &&
	"$(sha256sum "$source_builder" | awk '{print $1}')" == \
	"$SOURCE_BUILDER_SHA256" ]] || die 'source candidate builder changed'
[[ -f "$dtb_builder" && ! -L "$dtb_builder" &&
	"$(sha256sum "$dtb_builder" | awk '{print $1}')" == \
	"$DTB_BUILDER_SHA256" ]] || die 'DT builder changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-build-candidate.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#readonly OUTPUT_BOOT=gemini-mt6797-da921x-real-compatible-no-module\.boot\.img#readonly OUTPUT_DTB=mt6797-gemini-pda-da921x-name-only-client.dtb\nreadonly OUTPUT_DTB_SHA256=f2d9aa764219e408b740e3f619659bc0a621cd9879a6235d5a92866487ce5621\nreadonly OUTPUT_BOOT=gemini-mt6797-da921x-name-only-client.boot.img#;
	s#analyzer="\$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image\.py"#analyzer="\$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"\ndtb_builder="\$repo_root/experiments/2026-07-29-da921x-probe-isolation/scripts/build-isolation-dtb.sh"#;
	s#for input in "\$serializer" "\$analyzer"#for input in "\$serializer" "\$analyzer" "\$dtb_builder"#;
	s#install -m 0600 "\$gate3_artifact/\$GATE3_DTB" "\$stage/\$GATE3_DTB"#for destination in "\$stage/\$OUTPUT_DTB" "\$replica/\$OUTPUT_DTB"; do\n\t"\$dtb_builder" --gate3-dtb "\$gate3_artifact/\$GATE3_DTB" \\\n\t\t--output "\$destination" >"\${destination}.validation"\ndone\ncmp -s "\$stage/\$OUTPUT_DTB" "\$replica/\$OUTPUT_DTB" ||\n\tdie "two disabled DT derivations differ"\n[[ "\$(sha256sum "\$stage/\$OUTPUT_DTB" | awk '\''{print \$1}'\'')" == "\$OUTPUT_DTB_SHA256" ]] ||\n\tdie "disabled DT checksum changed"\nmv "\$stage/\$OUTPUT_DTB.validation" "\$stage/dtb-validation.txt"\nrm "\$replica/\$OUTPUT_DTB.validation"#;
	s#"\$stage/\$GATE3_DTB"#"\$stage/\$OUTPUT_DTB"#g;
	s#experiment=2026-07-30-da921x-module-file-isolation#experiment=2026-07-30-da921x-name-only-client#g;
	s#printf '\''enabled_real_compatible_dtb_sha256=%s\\n'\'' "\$GATE3_DTB_SHA256"#printf '\''disabled_real_compatible_dtb_sha256=%s\\n'\'' "\$OUTPUT_DTB_SHA256"#;
	s#candidate-Gate3-da921x-real-compatible-no-module-#candidate-Gate3-da921x-name-only-client-#g;
	s#da921x-real-compatible-no-module-candidate#da921x-name-only-client-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	gemini-mt6797-da921x-real-compatible-no-module.boot.img \
	'experiment=2026-07-30-da921x-module-file-isolation' \
	candidate-Gate3-da921x-real-compatible-no-module- \
	'validation=da921x-real-compatible-no-module-candidate'; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
