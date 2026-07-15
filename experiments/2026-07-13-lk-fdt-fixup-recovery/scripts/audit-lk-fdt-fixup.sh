#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the retained LK device-tree fixups and the candidate
# mainline DT. It never flashes, writes partitions, or executes vendor code.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=${REPO_ROOT:-"$(cd "$SCRIPT_DIR/../../.." && pwd -P)"}
LK_TREE=${LK_TREE:-"$HOME/src/reference/dguidipc-gemini-lk-android8"}
LK_COMMIT=${LK_COMMIT:-HEAD}
CURRENT_PACKAGE=${CURRENT_PACKAGE:-"$HOME/artifacts/gemini-pda/linux-7.1.3-gemini-363bf3942a1b"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
command -v dtc >/dev/null || die "dtc is required"
command -v rg >/dev/null || die "rg is required"
[[ -d "$LK_TREE/.git" ]] || die "LK Git tree is missing: $LK_TREE"
DTB=$CURRENT_PACKAGE/dtbs/mediatek/mt6797-gemini-pda.dtb
[[ -f "$DTB" ]] || die "candidate Gemini DTB is missing: $DTB"

LK_COMMIT=$(git -C "$LK_TREE" rev-parse "$LK_COMMIT")
TMP_DTS=$(mktemp)
trap 'rm -f "$TMP_DTS"' EXIT
dtc -q -I dtb -O dts -o "$TMP_DTS" "$DTB"

source_contains() {
	local file=$1
	local text=$2
	git -C "$LK_TREE" show "$LK_COMMIT:$file" | grep -Fq -- "$text" || \
		die "LK source contract changed: $file does not contain: $text"
}

source_contains lk/platform/mt6797/rules.mk 'CFG_DTB_EARLY_LOADER_SUPPORT := yes'
source_contains lk/platform/mt6797/rules.mk 'MBLOCK_LIB_SUPPORT := yes'
source_contains lk/platform/mt6797/rules.mk 'DEFINES += MBLOCK_LIB_SUPPORT=2'
source_contains lk/platform/mt6797/rules.mk 'KERNEL_DECOMPRESS_SIZE := 0x03200000'
source_contains lk/platform/mt6797/platform.c 'bldr_load_dtb("boot")'
source_contains lk/app/mt_boot/mt_boot.c 'memcpy((void *)dtb_kernel_addr'
source_contains lk/app/mt_boot/mt_boot.c 'target_fdt_model'
source_contains lk/app/mt_boot/mt_boot.c 'target_fdt_cpus'
source_contains lk/app/mt_boot/mt_boot.c 'mblock_sanity_check(fdt'
source_contains lk/app/mt_boot/mt_boot.c 'mblock_reserved_append(fdt)'
source_contains lk/lib/mblock/mblock_v2.c 'reserved_memory_conflict_check'
source_contains lk/lib/mblock/mblock_v2.c 'fdt_memory_append'
source_contains lk/app/mt_boot/mt_boot.c 'fdt_setprop_string(fdt, offset, "bootargs"'

POST_LK_RANGES=(
	7dfb0000 7ff40000 7ff80000 88000000 8f000000
	b4000000 be000000 bfa00000 bfdf0000
)
for start in "${POST_LK_RANGES[@]}"; do
	if rg -q "memory@${start}[[:space:]]*\\{" "$TMP_DTS"; then
		die "candidate DT statically duplicates post-LK mblock range 0x$start"
	fi
done

for node in reserve-memory-ccci_md1 reserve-memory-ccci_share \
	consys-reserve-memory spm-reserve-memory reserve-memory-scp_share; do
	rg -q "${node}[[:space:]]*\\{" "$TMP_DTS" || die "missing dynamic reservation: $node"
done

printf 'validation=retained-lk-fdt-fixup-and-reservation-contract\n'
printf 'lk_tree=%s\n' "$LK_TREE"
printf 'lk_commit=%s\n' "$LK_COMMIT"
printf 'lk_rules_sha256=%s\n' "$(git -C "$LK_TREE" show "$LK_COMMIT:lk/platform/mt6797/rules.mk" | sha256sum | awk '{print $1}')"
printf 'lk_platform_sha256=%s\n' "$(git -C "$LK_TREE" show "$LK_COMMIT:lk/platform/mt6797/platform.c" | sha256sum | awk '{print $1}')"
printf 'lk_boot_sha256=%s\n' "$(git -C "$LK_TREE" show "$LK_COMMIT:lk/app/mt_boot/mt_boot.c" | sha256sum | awk '{print $1}')"
printf 'lk_atags_sha256=%s\n' "$(git -C "$LK_TREE" show "$LK_COMMIT:lk/platform/mt6797/atags.c" | sha256sum | awk '{print $1}')"
printf 'lk_mblock_sha256=%s\n' "$(git -C "$LK_TREE" show "$LK_COMMIT:lk/lib/mblock/mblock_v2.c" | sha256sum | awk '{print $1}')"
printf 'candidate_package=%s\n' "$CURRENT_PACKAGE"
printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$DTB" | awk '{print $1}')"
printf 'candidate_dtb_size=%s\n' "$(stat -c '%s' "$DTB")"
printf 'early_dtb_loader=yes\n'
printf 'lk_rewrites_memory_chosen_model_cpu_firmware=yes\n'
printf 'post_lk_static_mblock_overlap=none\n'
printf 'pre_lk_dynamic_reservation_contract=preserved\n'
printf 'mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
