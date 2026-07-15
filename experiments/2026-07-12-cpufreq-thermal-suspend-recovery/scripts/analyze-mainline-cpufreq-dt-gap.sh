#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the Linux 7.1.3 MediaTek cpufreq DT/API contract with the current
# MT6797/Gemini patch set.  This is source-only: it never copies vendor code,
# reads device state, or writes a kernel/device artifact.

set -euo pipefail

LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
REPO_ROOT=${REPO_ROOT:-"$(git rev-parse --show-toplevel)"}
PATCH_DIR=${PATCH_DIR:-"$REPO_ROOT/patches/v7.1.3"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"

[[ -d "$LINUX_TREE/.git" ]] || die "Linux source tree is not a Git checkout: $LINUX_TREE"
[[ -d "$PATCH_DIR" ]] || die "patch directory is missing: $PATCH_DIR"

linux_file() {
	local path=$1
	[[ -f "$LINUX_TREE/$path" ]] || die "missing Linux source: $path"
	echo "$LINUX_TREE/$path"
}

sha256_file() {
	sha256sum "$1" | awk '{print $1}'
}

contains_fixed() {
	local file=$1
	local pattern=$2
	rg -F -q -- "$pattern" "$file"
}

contains_regex() {
	local file=$1
	local pattern=$2
	rg -q -- "$pattern" "$file"
}

cpufreq_c=$(linux_file drivers/cpufreq/mediatek-cpufreq.c)
opp_c=$(linux_file drivers/opp/core.c)
svs_c=$(linux_file drivers/soc/mediatek/mtk-svs.c)
clock_c=$(linux_file drivers/clk/mediatek/clk-mt6797.c)
clock_binding=$(linux_file include/dt-bindings/clock/mt6797-clk.h)
mt6797_dtsi=$(linux_file arch/arm64/boot/dts/mediatek/mt6797.dtsi)
gemini_board_patch="$PATCH_DIR/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch"
[[ -f "$gemini_board_patch" ]] || die "missing Gemini board patch: $gemini_board_patch"

echo "MT6797 mainline cpufreq Device Tree/API gap audit"
echo "linux_tree=$LINUX_TREE"
echo "linux_revision=$(git -C "$LINUX_TREE" rev-parse --verify HEAD 2>/dev/null || echo unknown)"
echo "linux_version=$(make -s -C "$LINUX_TREE" kernelversion)"
echo "patch_dir=$PATCH_DIR"
echo
echo "[source hashes]"
printf 'linux_sha256 drivers/cpufreq/mediatek-cpufreq.c %s\n' "$(sha256_file "$cpufreq_c")"
printf 'linux_sha256 drivers/opp/core.c %s\n' "$(sha256_file "$opp_c")"
printf 'linux_sha256 drivers/soc/mediatek/mtk-svs.c %s\n' "$(sha256_file "$svs_c")"
printf 'linux_sha256 drivers/clk/mediatek/clk-mt6797.c %s\n' "$(sha256_file "$clock_c")"
printf 'linux_sha256 include/dt-bindings/clock/mt6797-clk.h %s\n' "$(sha256_file "$clock_binding")"
printf 'linux_sha256 arch/arm64/boot/dts/mediatek/mt6797.dtsi %s\n' "$(sha256_file "$mt6797_dtsi")"
printf 'patch_sha256 0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch %s\n' "$(sha256_file "$gemini_board_patch")"

echo
echo "[Linux cpufreq consumer contract]"
for name in cpu intermediate; do
	if contains_fixed "$cpufreq_c" "clk_get(cpu_dev, \"$name\")"; then
		echo "linux_cpufreq_clock_$name=required"
	else
		echo "linux_cpufreq_clock_$name=not_found"
	fi
done
for name in proc sram; do
	if contains_fixed "$cpufreq_c" "regulator_get_optional(cpu_dev, \"$name\")"; then
		echo "linux_cpufreq_regulator_$name=optional-consumer"
	else
		echo "linux_cpufreq_regulator_$name=not_found"
	fi
done
if contains_fixed "$cpufreq_c" 'dev_pm_opp_of_get_sharing_cpus'; then
	echo "linux_cpufreq_opp_sharing=operating-points-v2+sharing-cpus"
else
	echo "linux_cpufreq_opp_sharing=not_found"
fi
if contains_fixed "$cpufreq_c" 'OPP_EVENT_ADJUST_VOLTAGE'; then
	echo "linux_cpufreq_opp_adjust=notifier-handled"
else
	echo "linux_cpufreq_opp_adjust=not_found"
fi
if contains_fixed "$cpufreq_c" 'of_machine_get_match_data'; then
	echo "linux_cpufreq_match=machine-compatible-platform-data"
else
	echo "linux_cpufreq_match=not_found"
fi
if contains_fixed "$cpufreq_c" 'mediatek,mt6797'; then
	echo "linux_cpufreq_mt6797_match=yes"
else
	echo "linux_cpufreq_mt6797_match=no"
fi

echo
echo "[Linux MT6797 clock-provider contract]"
if contains_fixed "$clock_c" 'PLL(CLK_APMIXED_MAINPLL'; then
	echo "linux_mt6797_apmixed_plls=main/univ/media-and-peripheral-plls-present"
else
	echo "linux_mt6797_apmixed_plls=not_found"
fi
if contains_fixed "$clock_c" 'armpll'; then
	echo "linux_mt6797_armpll=present"
else
	echo "linux_mt6797_armpll=missing"
fi
if contains_regex "$clock_c" 'cpu(_|-)sel|cpusel|mp0|mp1'; then
	echo "linux_mt6797_cpu_mux=present"
else
	echo "linux_mt6797_cpu_mux=missing"
fi
if contains_regex "$clock_c" 'cci(_|-)pll|ccipll|cci_sel'; then
	echo "linux_mt6797_cci_clock=present"
else
	echo "linux_mt6797_cci_clock=missing"
fi

echo
echo "[MT6797/Gemini DTS contract currently present]"
if contains_fixed "$mt6797_dtsi" 'operating-points-v2'; then
	echo "mt6797_soc_opp_table=present"
else
	echo "mt6797_soc_opp_table=missing"
fi
if contains_regex "$mt6797_dtsi" 'clock-names.*cpu'; then
	echo "mt6797_soc_cpu_clock_names=present"
else
	echo "mt6797_soc_cpu_clock_names=missing"
fi
if contains_fixed "$mt6797_dtsi" 'mediatek,cci'; then
	echo "mt6797_soc_cci_phandle=present"
else
	echo "mt6797_soc_cci_phandle=missing"
fi
if contains_fixed "$gemini_board_patch" 'clock-frequency'; then
	echo "gemini_board_cpu_clock_frequency=present-static-boot-hint"
else
	echo "gemini_board_cpu_clock_frequency=missing"
fi
for name in clocks clock-names proc-supply sram-supply operating-points-v2; do
	if contains_fixed "$gemini_board_patch" "$name"; then
		echo "gemini_board_$name=present"
	else
		echo "gemini_board_$name=missing"
	fi
done

echo
echo "[enablement decision]"
echo "reusable=generic-cpufreq-target+OPP-notifier+regulator-tracking+clock-reparenting"
echo "missing=MT6797-cpu-clocks+intermediate-clock+proc/sram-supplies+OPP-table+machine-data+EEM-calibrated-update-owner"
echo "safe_next_step=add-disabled-resource-contract-or-read-only-provider;do-not-enable-transitions"
echo "hardware_write=none"
