#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare a private, sanitized runtime capture with the tracked static
# mainline handoff result. Only an explicit allow-list is emitted.

set -euo pipefail
export LC_ALL=C

usage() {
	cat <<'EOF'
Usage: compare-runtime-boundaries.sh --runtime FILE --handoff FILE [--output FILE]

The runtime file must be the private output of
collect-mainline-runtime-evidence.sh. The generated report is sanitized and
contains no raw device-tree ranges, regulator voltages, identifiers, or logs.
EOF
}

runtime_file=""
handoff_file=""
output_file=""
while (($#)); do
	case "$1" in
		--runtime)
			(($# >= 2)) || { echo "--runtime requires FILE" >&2; exit 2; }
			runtime_file=$2
			shift 2
			;;
		--handoff)
			(($# >= 2)) || { echo "--handoff requires FILE" >&2; exit 2; }
			handoff_file=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || { echo "--output requires FILE" >&2; exit 2; }
			output_file=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "unknown argument: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

[[ -r "$runtime_file" ]] || { echo "unreadable runtime capture: $runtime_file" >&2; exit 1; }
[[ -r "$handoff_file" ]] || { echo "unreadable handoff result: $handoff_file" >&2; exit 1; }

first_value() {
	local file=$1
	local key=$2
	awk -F= -v key="$key" '$1 == key { print substr($0, length(key) + 2); exit }' "$file"
}

path_value() {
	local file=$1
	local path=$2
	awk -F= -v path="$path" '$1 == path { print substr($0, length(path) + 2); exit }' "$file"
}

platform_driver() {
	local file=$1
	local device=$2
	awk -v device="$device" '
		$0 == "platform_device=" device { wanted=1; next }
		wanted && /^platform_driver=/ { sub(/^platform_driver=/, ""); print; exit }
		/^platform_device=/ { wanted=0 }
	' "$file"
}

count_matches() {
	local file=$1
	local expression=$2
	awk -v expression="$expression" '$0 ~ expression { count++ } END { print count + 0 }' "$file"
}

runtime_sha256=$(shasum -a 256 "$runtime_file" | awk '{print $1}')
handoff_sha256=$(shasum -a 256 "$handoff_file" | awk '{print $1}')
vendor_kernel=$(first_value "$runtime_file" kernel_release)
vendor_model=$(first_value "$runtime_file" model)
vendor_compatible=$(first_value "$runtime_file" compatible)
vendor_online=$(path_value "$runtime_file" /sys/devices/system/cpu/online)
vendor_possible=$(path_value "$runtime_file" /sys/devices/system/cpu/possible)
vendor_present=$(path_value "$runtime_file" /sys/devices/system/cpu/present)
vendor_cpufreq=$(path_value "$runtime_file" /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver)
vendor_mmc=$(path_value "$runtime_file" /sys/block/mmcblk0/device/name)
vendor_mmc_type=$(path_value "$runtime_file" /sys/block/mmcblk0/device/type)
vendor_mmc_ro=$(path_value "$runtime_file" /sys/block/mmcblk0/ro)
vendor_modules=$(first_value "$runtime_file" proc_modules)
vendor_pwrap=$(platform_driver "$runtime_file" 1000d000.pwrap)
vendor_pmic=$(platform_driver "$runtime_file" mt-pmic)
vendor_rtc=$(platform_driver "$runtime_file" mt-rtc)
vendor_pinctrl=$(platform_driver "$runtime_file" 10005000.pinctrl)
vendor_uart=$(platform_driver "$runtime_file" 11002000.apuart0)
vendor_reserved_dynamic=$(count_matches "$runtime_file" '^reserved_node=(consys-reserve-memory|reserve-memory-scp_share|spm-reserve-memory)$')
vendor_reserved_mblock=$(count_matches "$runtime_file" '^reserved_node=mblock-[1-7]')
vendor_regulators=$(count_matches "$runtime_file" '^/sys/class/regulator/regulator\.[0-9]+/name=')
vendor_enabled_regulators=$(count_matches "$runtime_file" '^/sys/class/regulator/regulator\.[0-9]+/state=enabled')
vendor_mmc_irqs=$(count_matches "$runtime_file" 'mtk-msdc')
vendor_btif_irqs=$(count_matches "$runtime_file" 'mtk btif')
vendor_cpufreq_logs=$(count_matches "$runtime_file" 'Power/cpufreq|MT_CPU_DVFS')
vendor_wlan_wakeups=$(count_matches "$runtime_file" 'WLAN')

mainline_kernel=$(first_value "$handoff_file" source_revision)
mainline_patch_count=$(first_value "$handoff_file" patch_count)
mainline_patchset=$(first_value "$handoff_file" patchset_sha256)
mainline_package=$(first_value "$handoff_file" package)
mainline_boot=$(first_value "$handoff_file" runtime_mainline_boot)
mainline_uart=$(grep -c '^config=CONFIG_SERIAL_8250_MT6577=y$' "$handoff_file" || true)
mainline_psci=$(grep -c '^dtb=psci$' "$handoff_file" || true)
mainline_mmc=$(grep -c '^config=CONFIG_MMC_MTK=y$' "$handoff_file" || true)
mainline_watchdog=$(grep -c '^config=CONFIG_MEDIATEK_WATCHDOG=y$' "$handoff_file" || true)
mainline_dynamic=$(grep -Ec '^dtb=(dynamic_reserve-memory-ccci_md1|dynamic_reserve-memory-ccci_share|dynamic_consys-reserve-memory|dynamic_spm-reserve-memory|dynamic_reserve-memory-scp_share)$' "$handoff_file" || true)

emit() {
	if [[ -n "$output_file" ]]; then
		mkdir -p "$(dirname "$output_file")"
		tee "$output_file"
	else
		cat
	fi
}

emit <<EOF
validation=live-vendor-mainline-gap-audit
runtime_capture=$runtime_file
runtime_capture_sha256=$runtime_sha256
handoff_result=$handoff_file
handoff_result_sha256=$handoff_sha256
runtime_kernel=$vendor_kernel
runtime_model=$vendor_model
runtime_compatible=$vendor_compatible
mainline_source=$mainline_kernel
mainline_patch_count=$mainline_patch_count
mainline_patchset_sha256=$mainline_patchset
mainline_package=$mainline_package
runtime_mainline_boot=$mainline_boot
hardware_write=none

[vendor_observations]
cpu_online=$vendor_online
cpu_possible=$vendor_possible
cpu_present=$vendor_present
cpufreq_driver=$vendor_cpufreq
eMMC_type=$vendor_mmc_type
eMMC_name=$vendor_mmc
eMMC_read_only=$vendor_mmc_ro
proc_modules=$vendor_modules
pwrap_driver=$vendor_pwrap
pmic_driver=$vendor_pmic
rtc_driver=$vendor_rtc
pinctrl_driver=$vendor_pinctrl
uart_driver=$vendor_uart
dynamic_vendor_reservation_classes=$vendor_reserved_dynamic
mblock_reservation_nodes=$vendor_reserved_mblock
regulator_entries=$vendor_regulators
regulators_enabled=$vendor_enabled_regulators
msdc_observation_lines=$vendor_mmc_irqs
btif_observation_lines=$vendor_btif_irqs
cpufreq_dmesg_lines=$vendor_cpufreq_logs
wlan_dmesg_lines=$vendor_wlan_wakeups

[mainline_static_contract]
source_revision=$mainline_kernel
serial_8250_mt6577_config_present=$([[ "$mainline_uart" -gt 0 ]] && echo yes || echo no)
psci_dtb_contract_present=$([[ "$mainline_psci" -gt 0 ]] && echo yes || echo no)
mtk_mmc_config_present=$([[ "$mainline_mmc" -gt 0 ]] && echo yes || echo no)
mediatek_watchdog_config_present=$([[ "$mainline_watchdog" -gt 0 ]] && echo yes || echo no)
dynamic_reservation_classes_present=$mainline_dynamic
mainline_runtime_probe=not_attempted

[decisions]
uart=resource_match_candidate;vendor_mtk-uart;mainline_8250_mtk;boot_and_console_log_required
psci_timer_gic=generic_handoff_static_only;runtime_cpu_online_and_recovery_required
emmc=resource_match_candidate;vendor_DF4064;mainline_mmc@11230000;read_only_probe_required
pwrap_mt6351=probe_model_differs;vendor_pwrap_unbound_but_mt-pmic_and_mt-rtc_bound;mainline_parent_pwrap_with_mt6351_children;probe_and_rail_readback_required
cpu_power=do_not_enable_from_vendor_logs;vendor_mt-cpufreq_and_DVFS_activity;mainline_MT6797_DVFS_absent;recover_EEM_voltage_clock_contract
reservations=roles_correspond_but_vendor_mblock_labels_differ;pre-LK_dynamic_contract_is_static_only;final_allocator_ownership_requires_mainline_boot
connectivity=vendor_BTIF_WLAN_activity;mainline_MT6797_transport_absent;new_transport_and_firmware_boundary_work
modules=vendor_namespace_absent;mainline_modules_are_optional_1570-object_package;boot_initramfs_boundary_is_separate

conclusion=static_comparison_confirmed;mainline_runtime_inconclusive
EOF
