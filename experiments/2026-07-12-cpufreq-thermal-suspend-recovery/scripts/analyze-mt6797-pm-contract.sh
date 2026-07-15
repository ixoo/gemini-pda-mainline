#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 vendor power-management contracts with the
# prepared Linux 7.1.3 source tree.  This script is source-only: it never
# copies vendor source, firmware, calibration data, or device dumps.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/planet-mt6797-3.18"}
LEGACY_VENDOR_TREE=${LEGACY_VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"

[[ -d "$VENDOR_TREE/.git" ]] || die "vendor tree is not a Git checkout: $VENDOR_TREE"
[[ -d "$LEGACY_VENDOR_TREE/.git" ]] || die "legacy vendor tree is not a Git checkout: $LEGACY_VENDOR_TREE"
[[ -d "$LINUX_TREE" ]] || die "Linux source tree is missing: $LINUX_TREE"

vendor_ref=''
vendor_ref=$(git -C "$VENDOR_TREE" rev-parse HEAD)
legacy_vendor_ref=''
legacy_vendor_ref=$(git -C "$LEGACY_VENDOR_TREE" rev-parse HEAD)

vendor_exists() {
	git -C "$VENDOR_TREE" cat-file -e "HEAD:$1" 2>/dev/null
}

vendor_hash() {
	local path=$1
	if vendor_exists "$path"; then
		git -C "$VENDOR_TREE" rev-parse "HEAD:$path"
	else
		echo "missing"
	fi
}

vendor_show() {
	local path=$1
	vendor_exists "$path" || return 0
	git -C "$VENDOR_TREE" show "HEAD:$path"
}

legacy_vendor_exists() {
	git -C "$LEGACY_VENDOR_TREE" cat-file -e "HEAD:$1" 2>/dev/null
}

legacy_vendor_hash() {
	local path=$1
	if legacy_vendor_exists "$path"; then
		git -C "$LEGACY_VENDOR_TREE" rev-parse "HEAD:$path"
	else
		echo "missing"
	fi
}

linux_hash() {
	local path=$1
	if [[ -f "$LINUX_TREE/$path" ]]; then
		sha256sum "$LINUX_TREE/$path" | awk '{print $1}'
	else
		echo "missing"
	fi
}

vendor_matches() {
	local path=$1
	local pattern=$2
	if vendor_exists "$path"; then
		vendor_show "$path" | rg -n "$pattern" | head -n 24 || true
	else
		echo "(missing: $path)"
	fi
}

legacy_vendor_matches() {
	local path=$1
	local pattern=$2
	if legacy_vendor_exists "$path"; then
		git -C "$LEGACY_VENDOR_TREE" show "HEAD:$path" | rg -n "$pattern" | head -n 24 || true
	else
		echo "(missing: $path)"
	fi
}

linux_matches() {
	local path=$1
	local pattern=$2
	if [[ -f "$LINUX_TREE/$path" ]]; then
		rg -n "$pattern" "$LINUX_TREE/$path" | head -n 24 || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 power-management contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_commit=$vendor_ref"
echo "legacy_vendor_tree=$LEGACY_VENDOR_TREE"
echo "legacy_vendor_commit=$legacy_vendor_ref"
echo "linux_tree=$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi

echo
echo "[source hashes]"
for path in \
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c \
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.h \
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c \
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid_fw.h \
	drivers/misc/mediatek/base/power/mt6797/mt_eem.c \
	drivers/misc/mediatek/base/power/mt6797/mt_eem2.c \
	drivers/misc/mediatek/base/power/mt6797/mt_eem2.h \
	drivers/misc/mediatek/base/power/mt6797/mt_ptp.h \
	drivers/misc/mediatek/base/power/mt6797/mt_defptp.h \
	drivers/clk/mediatek/clk-mt6797-pll.c \
	arch/arm64/boot/dts/mt6797.dtsi \
	drivers/misc/mediatek/base/power/spm_v2/mt_spm.c \
	drivers/misc/mediatek/base/power/spm_v2/mt_spm_dpidle_mt6797.c \
	drivers/misc/mediatek/base/power/spm_v2/mt_spm_vcorefs_mt6797.c \
	drivers/misc/mediatek/base/power/mt6797/mt_pm_init.c \
	drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	drivers/misc/mediatek/auxadc/mt6797/mt_auxadc_hw.h \
	drivers/misc/mediatek/thermal/mt6797/inc/mt_ts_setting.h \
	drivers/misc/mediatek/base/power/include/spm_v2/mt_spm_reg_mt6797.h \
	Documentation/devicetree/bindings/misc/mediatek,dvfsp.txt; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_hash "$path")"
	printf 'legacy_vendor_blob %s %s\n' "$path" "$(legacy_vendor_hash "$path")"
done
for path in \
	drivers/cpufreq/mediatek-cpufreq.c \
	drivers/thermal/mediatek/auxadc_thermal.c \
	drivers/firmware/psci/psci.c \
	drivers/cpufreq/cpufreq-dt.c \
	drivers/soc/mediatek/mtk-svs.c \
	drivers/opp/core.c \
	Documentation/devicetree/bindings/soc/mediatek/mtk-svs.yaml \
	Documentation/devicetree/bindings/thermal/mediatek,thermal.yaml; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor cpufreq and DVFSP anchors]"
vendor_matches drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c \
	'NR_MT_CPU_DVFS|ARMCA|PLL|VPROC|VSRAM|DA9214|efuse|date.?code|PTP|EEM|cluster|cpufreq_frequency_table|hybrid|DVFSP|0x[0-9A-Fa-f]+'
vendor_matches drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c \
	'CSPM_BASE|CSRAM_BASE|PCM|firmware|request_firmware|DVFS_TIMEOUT|0x11015000|0x0012a000'
if vendor_exists drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid_fw.h; then
	echo "hybrid firmware header: present (instruction contents intentionally not printed)"
else
	echo "hybrid firmware header: missing"
fi
vendor_matches drivers/misc/mediatek/base/power/mt6797/mt_eem.c \
	'efuse|PTP|EEM|temperature|volt|freq|CPU|0x[0-9A-Fa-f]+'

echo
echo "[derived MT6797 CPU-DVFS contract]"
required_vendor_sources=(
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.h
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c
	drivers/misc/mediatek/base/power/mt6797/mt_eem.c
	drivers/misc/mediatek/base/power/mt6797/mt_eem2.c
	drivers/misc/mediatek/base/power/mt6797/mt_eem2.h
	drivers/misc/mediatek/base/power/mt6797/mt_ptp.h
	drivers/misc/mediatek/base/power/mt6797/mt_defptp.h
	drivers/clk/mediatek/clk-mt6797-pll.c
)
vendor_source_complete=yes
for path in "${required_vendor_sources[@]}"; do
	if ! vendor_exists "$path"; then
		vendor_source_complete=no
	fi
done
echo "vendor_source_complete=$vendor_source_complete"
echo "vendor_clusters=LL:L:B:CCI"
echo "vendor_armpll_con_offsets=LL:0x200/0x204/0x208,L:0x210/0x214/0x218,CCI:0x220/0x224/0x228,backup:0x230/0x234/0x238;B=special-BigiDVFS"
echo "vendor_armplldiv_offsets=muxsel:0x270,ckdiv:0x274"
echo "vendor_pll_access=mt6797_0x1001AXXX_reg_read/write/set"
echo "vendor_efuse_selection=function:index22[3:0],date:index61[7:4]"
echo "vendor_table_variants=date:1221|0119;levels:0|1|2|3;tt_override=B:level1"
echo "vendor_voltage_contract=DA9214-vproc+SRAM;vproc_max:120000;vsram:100000..120000;delta:10000..30000"
echo "vendor_eem_detectors=BIG:bank0,L:bank3,2L:bank4,CCI:bank5;GPU/SOC=separate"
echo "vendor_eem_register_window=0x1100b000+0x1000;shared-with=thermal-controller"
echo "vendor_eem_phases=INIT01:DC+AGE;INIT02:VOP30+VOP74+interpolate16;MON=thermal-adjusted-voltage"
echo "vendor_eem_units=eem:base70000_step625;cpu-pmic:base30000_step1000;sram:base90000_step2500;10uV"
echo "vendor_eem_adjustment=temperature<=33000-or-invalid:+6250;clamp=VMIN..VMAX;cap=recordTbl;callback=mt_cpufreq_update_volt"
echo "vendor_transition_contract=raise-voltage;clock-switch;PLL-program;CCI-coupling;lower-voltage"
echo "vendor_transition_latency_ns=1000"
echo "vendor_hybrid_contract=CSPM:0x11015000;CSRAM:0x0012a000;embedded-PCM:not-Linux-firmware"
for path in \
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c \
	drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c \
	drivers/misc/mediatek/base/power/mt6797/mt_eem.c \
	drivers/clk/mediatek/clk-mt6797-pll.c; do
	if vendor_exists "$path"; then
		echo "vendor_source_present $path=yes"
	else
		echo "vendor_source_present $path=no"
	fi
done

echo
echo "[vendor thermal and AUXADC anchors]"
vendor_matches drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	'compatible|THERMINTST|THERM|AUXADC|auxadc|IRQ|interrupt|calib|efuse|INVALID|invalid|PTPSPARE|TEMPADCMUX|TEMPADCEN|TEMPMSR'
vendor_matches drivers/misc/mediatek/auxadc/mt6797/mt_auxadc_hw.h \
	'AUXADC_BASE|EFUSEC_BASE|AUXADC_|0x[0-9A-Fa-f]+'
vendor_matches drivers/misc/mediatek/thermal/mt6797/inc/mt_ts_setting.h \
	'THERMAL|BANK|SENSOR|0x[0-9A-Fa-f]+|INVALID|TEMP'

echo
echo "[vendor SPM, idle, and suspend firmware anchors]"
vendor_matches drivers/misc/mediatek/base/power/spm_v2/mt_spm.c \
	'ENABLE_DYNA_LOAD_PCM|request_firmware|pcm_(suspend|sodi|deepidle|vcorefs)|mediatek,sleep|efuse|thermal|DDR|vcore|CSRAM|SPM_'
vendor_matches drivers/misc/mediatek/base/power/spm_v2/mt_spm_dpidle_mt6797.c \
	'PMIC|26M|MIPID|MIPIC|MDPLLGP|SSUSB|PLL|power|spm_|0x[0-9A-Fa-f]+'
vendor_matches drivers/misc/mediatek/base/power/spm_v2/mt_idle_mt6797.c \
	'dpidle|soidle|mcidle|SODI|PLL|power|mm|block|PSCI|0x[0-9A-Fa-f]+'
vendor_matches drivers/misc/mediatek/base/power/mt6797/mt_pm_init.c \
	'psci|idle|suspend|spm|mtcmos|cpu|0x[0-9A-Fa-f]+'

echo
echo "[Linux 7.1.3 comparison]"
echo "mediatek-cpufreq compatibles and OPP/regulator contract:"
linux_matches drivers/cpufreq/mediatek-cpufreq.c \
	'compatible|opp|regulator|clock|transition|mt6797'
echo "AUXADC thermal compatibles and calibration contract:"
linux_matches drivers/thermal/mediatek/auxadc_thermal.c \
	'compatible|mt6797|mt8173|mt2701|mt2712|mt8183|mt7986|mt8365|auxadc|efuse|calibration'
echo "thermal binding compatibles:"
linux_matches Documentation/devicetree/bindings/thermal/mediatek,thermal.yaml \
	'compatible|mt6797|mt8173|auxadc|clocks|resets|interrupts'
echo "generic cpufreq-dt and PSCI entry points:"
linux_matches drivers/cpufreq/cpufreq-dt.c \
	'operating-points|opp|clock|regulator|cpufreq_generic'
linux_matches drivers/firmware/psci/psci.c \
	'CPU_SUSPEND|power_state|suspend|cpuidle|conduit|PSCI_'
echo "MediaTek SVS and OPP voltage-adjustment comparison:"
linux_matches drivers/soc/mediatek/mtk-svs.c \
	'compatible|SVSB_PHASE|efuse|thermal|dev_pm_opp_adjust_voltage|opp|vmin|vmax|VOP30|VOP74'
linux_matches drivers/opp/core.c \
	'dev_pm_opp_adjust_voltage|OPP_EVENT_ADJUST_VOLTAGE'
linux_matches Documentation/devicetree/bindings/soc/mediatek/mtk-svs.yaml \
	'compatible|svs-calibration-data|t-calibration-data|opp|thermal|buck|clocks|resets'

if rg -q 'mediatek,mt6797' "$LINUX_TREE/drivers/cpufreq/mediatek-cpufreq.c"; then
	echo "linux_mtk_cpufreq_mt6797_match=yes"
else
	echo "linux_mtk_cpufreq_mt6797_match=no"
fi
if rg -q 'mt6797' "$LINUX_TREE/drivers/cpufreq/cpufreq-dt.c"; then
	echo "linux_cpufreq_dt_mt6797_match=yes"
else
	echo "linux_cpufreq_dt_mt6797_match=no"
fi
echo "linux_mtk_cpufreq_reusable=OPP+proc/sram-regulators+intermediate-clock+clock-reparent"
echo "linux_mtk_cpufreq_missing=MT6797-PLL-mux+efuse/date/calibration+CCI/DA9214-board-contract"
if rg -q 'mediatek,mt6797' "$LINUX_TREE/drivers/soc/mediatek/mtk-svs.c"; then
	echo "linux_mtk_svs_mt6797_match=yes"
else
	echo "linux_mtk_svs_mt6797_match=no"
fi
echo "linux_mtk_svs_reusable=phase-machine+NVMEM-calibration+thermal-offset+dev_pm_opp_adjust_voltage+default-voltage-rollback"
echo "linux_mtk_svs_missing=MT6797-EEM-registers+efuse-layout+DA9214/CCI/PLL-contract"

echo
echo "[decision]"
echo "generic PSCI/topology and the mainline OPP/regulator transition framework"
echo "are reusable, including the SVS pattern for phase/error handling and"
echo "runtime OPP voltage adjustment. The complete MT6797 implementation still"
echo "has a distinct"
echo "PLL/mux register map, efuse/date/segment table selection, CCI coupling,"
echo "DA9214/SRAM sequencing, and optional private PCM protocol. Add an"
echo "MT6797 variant or new cpufreq driver after clock, regulator, calibration,"
echo "and rollback evidence proves the boundary; do not transcribe the live"
echo "table as a board-default OPP set. Keep DVFSP, deep idle, and suspend"
echo "disabled meanwhile."
