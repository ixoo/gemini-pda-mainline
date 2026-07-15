#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Recover the MT6797 CPU-clock backend contract from the pinned Planet vendor
# source and compare it with Linux 7.1.3.  This is source-only: it never copies
# vendor code, reads device state, or writes a kernel/device artifact.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/planet-mt6797-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"

[[ -d "$VENDOR_TREE/.git" ]] || die "vendor source tree is not a Git checkout: $VENDOR_TREE"
[[ -d "$LINUX_TREE/.git" ]] || die "Linux source tree is not a Git checkout: $LINUX_TREE"

vendor_show() {
	local path=$1
	git -C "$VENDOR_TREE" show "HEAD:$path"
}

vendor_hash() {
	local path=$1
	vendor_show "$path" | sha256sum | awk '{print $1}'
}

linux_file() {
	local path=$1
	[[ -f "$LINUX_TREE/$path" ]] || die "missing Linux source: $path"
	echo "$LINUX_TREE/$path"
}

linux_hash() {
	sha256sum "$(linux_file "$1")" | awk '{print $1}'
}

vendor_contains_fixed() {
	local path=$1
	local pattern=$2
	# Do not use rg -q here: with pipefail, its early exit makes git show
	# report SIGPIPE and turns a real match into a false negative.
	vendor_show "$path" | rg -F -- "$pattern" >/dev/null
}

vendor_contains_regex() {
	local path=$1
	local pattern=$2
	vendor_show "$path" | rg -- "$pattern" >/dev/null
}

linux_contains_fixed() {
	local path=$1
	local pattern=$2
	rg -F -q -- "$pattern" "$(linux_file "$path")"
}

linux_contains_regex() {
	local path=$1
	local pattern=$2
	rg -q -- "$pattern" "$(linux_file "$path")"
}

cpufreq=drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c
freqhopping=drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c
idvfs_h=drivers/misc/mediatek/base/power/mt6797/mt_idvfs.h
idvfs_c=drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c
vendor_clock=drivers/clk/mediatek/clk-mt6797.c
vendor_pll=drivers/clk/mediatek/clk-mt6797-pll.c
linux_clock=drivers/clk/mediatek/clk-mt6797.c
linux_cpufreq=drivers/cpufreq/mediatek-cpufreq.c

for path in "$cpufreq" "$freqhopping" "$idvfs_h" "$idvfs_c" "$vendor_clock" "$vendor_pll"; do
	vendor_show "$path" >/dev/null || die "missing vendor source: $path"
done
linux_file "$linux_clock" >/dev/null
linux_file "$linux_cpufreq" >/dev/null

echo "MT6797 CPU clock backend audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_revision=$(git -C "$VENDOR_TREE" rev-parse --verify HEAD)"
echo "linux_tree=$LINUX_TREE"
echo "linux_revision=$(git -C "$LINUX_TREE" rev-parse --verify HEAD 2>/dev/null || echo unknown)"
echo "linux_version=$(make -s -C "$LINUX_TREE" kernelversion)"
echo

echo "[source hashes]"
for path in "$cpufreq" "$freqhopping" "$idvfs_h" "$idvfs_c" "$vendor_clock" "$vendor_pll"; do
	printf 'vendor_sha256 %s %s\n' "$path" "$(vendor_hash "$path")"
done
printf 'linux_sha256 %s %s\n' "$linux_clock" "$(linux_hash "$linux_clock")"
printf 'linux_sha256 %s %s\n' "$linux_cpufreq" "$(linux_hash "$linux_cpufreq")"

echo
echo "[vendor CPU PLL and divider map]"
if vendor_contains_fixed "$cpufreq" 'ARMCAXPLL0_CON0' &&
	vendor_contains_fixed "$cpufreq" 'ARMCAXPLL1_CON0' &&
	vendor_contains_fixed "$cpufreq" 'ARMCAXPLL2_CON0' &&
	vendor_contains_fixed "$cpufreq" 'ARMCAXPLL3_CON0'; then
	echo "vendor_cpu_pll_windows=LL:0x200/0x204/0x208;L:0x210/0x214/0x218;CCI:0x220/0x224/0x228;backup:0x230/0x234/0x238"
else
	echo "vendor_cpu_pll_windows=not-confirmed"
fi
if vendor_contains_fixed "$cpufreq" 'ARMPLLDIV_MUXSEL' &&
	vendor_contains_fixed "$cpufreq" 'ARMPLLDIV_CKDIV'; then
	echo "vendor_cpu_divider_registers=ARMPLLDIV_MUXSEL:0x270;ARMPLLDIV_CKDIV:0x274"
else
	echo "vendor_cpu_divider_registers=not-confirmed"
fi
if vendor_contains_fixed "$cpufreq" 'ARMCAXPLL0_CON1' &&
	vendor_contains_fixed "$cpufreq" 'ARMCAXPLL1_CON1' &&
	vendor_contains_fixed "$cpufreq" 'BigiDVFSPllSetFreq' &&
	vendor_contains_fixed "$cpufreq" 'ARMCAXPLL2_CON1'; then
	echo "vendor_cpu_cluster_paths=LL:CON1@0x204;L:CON1@0x214;B:secure-BigiDVFS;CCI:CON1@0x224"
else
	echo "vendor_cpu_cluster_paths=not-confirmed"
fi
if vendor_contains_fixed "$cpufreq" '3 : 2' && vendor_contains_fixed "$cpufreq" '5 : 4' &&
	vendor_contains_fixed "$cpufreq" '1 : 0' && vendor_contains_fixed "$cpufreq" '7 : 6'; then
	echo "vendor_cpu_mux_fields=LL:3:2;L:5:4;B:1:0;CCI:7:6"
else
	echo "vendor_cpu_mux_fields=not-confirmed"
fi
if vendor_contains_fixed "$cpufreq" '9 : 5' && vendor_contains_fixed "$cpufreq" '14 : 10' &&
	vendor_contains_fixed "$cpufreq" '4 : 0' && vendor_contains_fixed "$cpufreq" '19 : 15'; then
	echo "vendor_cpu_div_fields=LL:9:5;L:14:10;B:4:0;CCI:19:15"
else
	echo "vendor_cpu_div_fields=not-confirmed"
fi
if vendor_contains_fixed "$vendor_pll" 'mt_clk_arm_pll_ops' &&
	vendor_contains_fixed "$vendor_pll" '26000000' && vendor_contains_fixed "$cpufreq" '_BITMASK_(26:24)' &&
	vendor_contains_fixed "$cpufreq" '_BITMASK_(20:0)' && vendor_contains_fixed "$cpufreq" 'PLL_SETTLE_TIME'; then
	echo "vendor_cpu_armpll_math=generic-ops-present;26MHz-parent;posdiv:26:24;pcw:20:0;change:31;settle:20us"
else
	echo "vendor_cpu_armpll_math=not-confirmed"
fi

echo
echo "[cross-owner clock access boundary]"
if vendor_contains_fixed "$freqhopping" 'ioremap_nocache(0x1001A000, 0x1000)' &&
	vendor_contains_fixed "$freqhopping" 'g_sema_base + (0x440)' &&
	vendor_contains_fixed "$freqhopping" '0x0b160001' &&
	vendor_contains_fixed "$freqhopping" 'SEMA_GET_TIMEOUT  2000' &&
	vendor_contains_fixed "$freqhopping" 'local_irq_save(flags)' &&
	vendor_contains_fixed "$freqhopping" 'spin_lock(&g_mt6797_0x1001AXXX_lock)'; then
	echo "vendor_cpu_clock_access=MCUMIXED:0x1001a000+0x1000;semaphore:DVFSP+0x440;internal_cg_write:0x0b160001;timeout_us:2000;irq_save+spinlock"
else
	echo "vendor_cpu_clock_access=not-confirmed"
fi
if vendor_contains_fixed "$freqhopping" 'For ATF, SPM and kernel protecting 0x1001AXXX access' &&
	vendor_contains_fixed "$freqhopping" 'All clock driver might call the API'; then
	echo "vendor_cpu_clock_owners=kernel+SPM+ATF;direct-MMIO-unsafe"
else
	echo "vendor_cpu_clock_owners=not-confirmed"
fi

echo
echo "[B-cluster secure backend]"
if vendor_contains_fixed "$idvfs_h" '0xC20003B0' &&
	vendor_contains_fixed "$idvfs_h" '0xC20003C1' &&
	vendor_contains_fixed "$idvfs_h" '0xC200035F' &&
	vendor_contains_fixed "$idvfs_h" '0xC200035E'; then
	echo "vendor_bigi_secure_smc=arm64-C20003B0..C20003C1;read:C200035F;write:C200035E"
else
	echo "vendor_bigi_secure_smc=not-confirmed"
fi
if vendor_contains_fixed "$idvfs_c" 'SEC_BIGIDVFS_READ(0x102224a4)' &&
	vendor_contains_fixed "$idvfs_c" 'SEC_BIGIDVFS_WRITE(0x102224a0' &&
	vendor_contains_fixed "$idvfs_c" 'SEC_BIGIDVFS_READ(0x102222b0)' &&
	vendor_contains_fixed "$idvfs_c" 'SEC_BIGIDVFS_WRITE(0x10222470'; then
	echo "vendor_bigi_secure_offsets=pll-pcw:0x102224a4;pll-posdiv-en:0x102224a0;sram-selector:0x102222b0;control:0x10222470"
else
	echo "vendor_bigi_secure_offsets=not-confirmed"
fi
if vendor_contains_fixed "$idvfs_c" 'Freq < 250' &&
	vendor_contains_fixed "$idvfs_c" 'Freq > 3000' &&
	vendor_contains_fixed "$idvfs_c" 'mVolts_x100 < 50000' &&
	vendor_contains_fixed "$idvfs_c" 'mVolts_x100 > 120000'; then
	echo "vendor_bigi_secure_ranges=freq:250..3000MHz;sram:50000..120000(mV*100)"
else
	echo "vendor_bigi_secure_ranges=not-confirmed"
fi

echo
echo "[Linux 7.1.3 CCF gap]"
if linux_contains_regex "$linux_clock" 'armpll|ARMPLL'; then
	echo "linux_mt6797_armpll=present"
else
	echo "linux_mt6797_armpll=missing"
fi
if linux_contains_regex "$linux_clock" 'cpu(_|-)sel|cpusel|mp0|mp1'; then
	echo "linux_mt6797_cpu_mux=present"
else
	echo "linux_mt6797_cpu_mux=missing"
fi
if linux_contains_regex "$linux_clock" 'cci(_|-)pll|ccipll|cci_sel'; then
	echo "linux_mt6797_cci_clock=present"
else
	echo "linux_mt6797_cci_clock=missing"
fi
if linux_contains_fixed "$linux_cpufreq" 'clk_get(cpu_dev, "cpu")' &&
	linux_contains_fixed "$linux_cpufreq" 'clk_get(cpu_dev, "intermediate")'; then
	echo "linux_cpufreq_backend=cpu+intermediate-clocks-required"
else
	echo "linux_cpufreq_backend=not-confirmed"
fi

echo
echo "[implementation boundary]"
echo "reusable=MediaTek-CCF-PLL-math+generic-clk-provider+OPP-notifier+regulator-tracking"
echo "new=MT6797-CPU-PLL+mux+divider-provider;MCUMIXED-semaphore-owner;BigiDVFS-SMC-backend"
echo "safe_next_step=register-disabled-read-only-clock-contract;prove-cross-owner-and-secure-firmware-ownership-before-transition-writes"
echo "hardware_write=none"
