#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --patch FILE [--checkpatch FILE]\n' "$0" >&2
}

patch_file=
checkpatch_file=${CHECKPATCH:-}
while (($#)); do
	case "$1" in
	--patch|--checkpatch)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--patch) patch_file=$2 ;;
		--checkpatch) checkpatch_file=$2 ;;
		esac
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		usage
		die "unknown option: $1"
		;;
	esac
done

[[ -r "$patch_file" && -s "$patch_file" ]] || die "controller patch is missing"
for command in awk grep perl sed sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

if [[ -z "$checkpatch_file" ]]; then
	for candidate in \
		"${HOME}/src/gemini-pda/linux-7.1.3/scripts/checkpatch.pl" \
		"${HOME}/src/gemini-pda-v-build2-5f9f1dcf/linux-7.1.3/scripts/checkpatch.pl"; do
		if [[ -f "$candidate" ]]; then
			checkpatch_file=$candidate
			break
		fi
	done
fi
[[ -f "$checkpatch_file" && -r "$checkpatch_file" ]] || \
	die "pass the pinned Linux 7.1.3 checkpatch.pl with --checkpatch"

readonly target=drivers/i2c/busses/i2c-mt65xx.c
readonly expected_added=$'\t{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },'
readonly expected_diff=$'diff --git a/drivers/i2c/busses/i2c-mt65xx.c b/drivers/i2c/busses/i2c-mt65xx.c\n--- a/drivers/i2c/busses/i2c-mt65xx.c\n+++ b/drivers/i2c/busses/i2c-mt65xx.c\n@@ -527,6 +527,7 @@ static const struct of_device_id mtk_i2c_of_match[] = {\n \t{ .compatible = "mediatek,mt2712-i2c", .data = &mt2712_compat },\n \t{ .compatible = "mediatek,mt6577-i2c", .data = &mt6577_compat },\n \t{ .compatible = "mediatek,mt6589-i2c", .data = &mt6589_compat },\n+\t{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },\n \t{ .compatible = "mediatek,mt7622-i2c", .data = &mt7622_compat },\n \t{ .compatible = "mediatek,mt7981-i2c", .data = &mt7981_compat },\n \t{ .compatible = "mediatek,mt7986-i2c", .data = &mt7986_compat },'

diff_count="$(grep -c '^diff --git ' "$patch_file" || true)"
hunk_count="$(grep -c '^@@ ' "$patch_file" || true)"
[[ "$diff_count" == 1 ]] || die "controller patch must change exactly one file"
[[ "$hunk_count" == 1 ]] || die "controller patch must contain exactly one hunk"
grep -Fqx "diff --git a/$target b/$target" "$patch_file" || \
	die "controller patch target changed"

actual_diff="$(awk '
	/^diff --git / { capture = 1 }
	capture && $0 == "-- " { exit }
	capture { print }
' "$patch_file")"
[[ "$actual_diff" == "$expected_diff" ]] || \
	die "controller patch is not the exact one-line MT6797-to-MT8173 match"

added_lines="$(sed -n 's/^+\([^+]\)/\1/p' "$patch_file")"
deleted_count="$(sed -n 's/^-\([^-]\)/\1/p' "$patch_file" | awk 'END { print NR + 0 }')"
[[ "$added_lines" == "$expected_added" ]] || die "controller patch adds unexpected code"
[[ "$deleted_count" == 0 ]] || die "controller patch must not remove source lines"

set +e
checkpatch_output="$(perl "$checkpatch_file" --strict --no-tree "$patch_file" 2>&1)"
checkpatch_rc=$?
set -e
diagnostics="$(printf '%s\n' "$checkpatch_output" | \
	awk '/^(ERROR|WARNING|CHECK):/ { print }')"

if [[ "$checkpatch_rc" == 0 ]]; then
	[[ -z "$diagnostics" ]] || die "checkpatch returned success with diagnostics"
	checkpatch_result=clean
else
	[[ "$checkpatch_rc" == 1 ]] || die "checkpatch failed unexpectedly (exit $checkpatch_rc)"
	[[ "$diagnostics" == 'ERROR: Missing Signed-off-by: line(s)' ]] || {
		printf '%s\n' "$checkpatch_output" >&2
		die "checkpatch reported a finding other than the known missing DCO"
	}
	printf '%s\n' "$checkpatch_output" | \
		grep -Eq '^total: 1 errors, 0 warnings, 0 checks, [0-9]+ lines checked$' || {
		printf '%s\n' "$checkpatch_output" >&2
		die "checkpatch summary exceeds the missing-DCO allowlist"
	}
	checkpatch_result=allowed-missing-dco
fi

printf 'validation=candidate-w-mt6797-controller-patch\n'
printf 'patch_sha256=%s\n' "$(sha256sum "$patch_file" | awk '{print $1}')"
printf 'target=%s\n' "$target"
printf 'source_delta=one-line-mt6797-to-mt8173-match\n'
printf 'checkpatch=%s\n' "$checkpatch_result"
printf 'hardware_write=none\n'
