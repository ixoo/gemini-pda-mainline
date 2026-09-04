#!/bin/sh

# One read-only serviceability frame for the exact PWRAP-reset candidate.
set -u
export LC_ALL=C

BB=/bin/busybox
PWRAP=/sys/bus/platform/devices/1000d000.pwrap
PWRAP_DT=/sys/firmware/devicetree/base/pwrap@1000d000
MMC=/sys/bus/platform/devices/11230000.mmc

driver_name() {
	if [ -L "$1/driver" ]; then
		$BB basename "$($BB readlink "$1/driver")"
	else
		$BB printf '%s\n' none
	fi
}

driver_bind_count() {
	count=0
	for item in "/sys/bus/platform/drivers/$1"/*; do
		[ -L "$item" ] || continue
		[ "$($BB basename "$item")" = module ] && continue
		count=$((count + 1))
	done
	$BB printf '%s\n' "$count"
}

config_count() {
	$BB zcat /proc/config.gz 2>/dev/null | $BB grep -Fxc "$1"
}

dmesg_count() {
	$BB dmesg | $BB grep -Ec "$1"
}

$BB printf '%s\n' __GEMINI_PWRAP_SERVICEABILITY_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline

$BB printf 'pwrap_dt_resets_hex='
if [ -r "$PWRAP_DT/resets" ]; then
	$BB od -An -tx1 -v "$PWRAP_DT/resets" | $BB tr -d '[:space:]'
	$BB printf '\n'
else
	$BB printf '%s\n' missing
fi
$BB printf 'pwrap_driver='; driver_name "$PWRAP"
$BB printf 'pwrap_bind_count='; driver_bind_count mt-pmic-pwrap
$BB printf 'mt6351_core_bind_count='; driver_bind_count mt6397
$BB printf 'mt6351_regulator_bind_count='; driver_bind_count mt6351-regulator
$BB printf 'mmc_driver='; driver_name "$MMC"
$BB printf 'mmc_bind_count='; driver_bind_count mtk-msdc

vemc=0
vio18=0
regulator_count=0
for item in /sys/class/regulator/regulator.*; do
	[ -r "$item/name" ] || continue
	regulator_count=$((regulator_count + 1))
	name=$($BB cat "$item/name")
	[ "$name" = vemc_3v3 ] && vemc=$((vemc + 1))
	[ "$name" = vio18 ] && vio18=$((vio18 + 1))
done
$BB printf 'regulator_count=%s\n' "$regulator_count"
$BB printf 'vemc_3v3_count=%s\n' "$vemc"
$BB printf 'vio18_count=%s\n' "$vio18"

card_count=0
card_type=none
for item in /sys/class/mmc_host/mmc0/mmc0:*; do
	[ -r "$item/type" ] || continue
	card_count=$((card_count + 1))
	card_type=$($BB cat "$item/type")
done
partition_count=0
for item in /sys/class/block/mmcblk0p*; do
	[ -e "$item" ] && partition_count=$((partition_count + 1))
done
$BB printf 'mmc_card_count=%s\n' "$card_count"
$BB printf 'mmc_card_type=%s\n' "$card_type"
$BB printf 'mmcblk0_present='
if [ -e /sys/class/block/mmcblk0 ]; then
	$BB printf '1\n'
else
	$BB printf '0\n'
fi
$BB printf 'mmcblk0_partition_count=%s\n' "$partition_count"
$BB printf 'mmcblk0_sectors='; $BB cat /sys/class/block/mmcblk0/size 2>/dev/null || $BB printf 'missing\n'

$BB printf 'config_pwrap='; config_count 'CONFIG_MTK_PMIC_WRAP=y'
$BB printf 'config_mt6397='; config_count 'CONFIG_MFD_MT6397=y'
$BB printf 'config_mt6351_regulator='; config_count 'CONFIG_REGULATOR_MT6351=y'
$BB printf 'config_mmc_mtk='; config_count 'CONFIG_MMC_MTK=y'
$BB printf 'config_kunit_disabled='; config_count '# CONFIG_KUNIT is not set'
$BB printf 'config_thermal_disabled='; config_count '# CONFIG_THERMAL is not set'
$BB printf 'config_cpufreq_disabled='; config_count '# CONFIG_CPU_FREQ is not set'
$BB printf 'config_cpuidle_disabled='; config_count '# CONFIG_CPU_IDLE is not set'
$BB printf 'config_suspend_disabled='; config_count '# CONFIG_SUSPEND is not set'

$BB printf 'pwrap_initcall_success_count='; dmesg_count '1000d000\.pwrap.*returned 0'
$BB printf 'pmic_initcall_success_count='; dmesg_count '1000d000\.pwrap:pmic.*returned 0'
$BB printf 'mt6351_regulator_success_count='; dmesg_count 'mt6351-regulator.*returned 0'
$BB printf 'mmc_initcall_success_count='; dmesg_count '11230000\.mmc.*returned 0'
$BB printf 'mmc_card_log_count='; dmesg_count 'mmc0:.*GiB'
$BB printf 'pwrap_error_count='; dmesg_count '1000d000\.pwrap.*(failed|error|timeout|defer|returned -)'
$BB printf 'mmc_error_count='; dmesg_count '11230000\.mmc.*(failed|error|timeout|defer|returned -)'

thermal_count=0
for item in /sys/class/thermal/thermal_zone[0-9]*; do
	[ -e "$item" ] && thermal_count=$((thermal_count + 1))
done
cpufreq_count=0
for item in /sys/devices/system/cpu/cpufreq/policy[0-9]*; do
	[ -e "$item" ] && cpufreq_count=$((cpufreq_count + 1))
done
$BB printf 'thermal_zone_count=%s\n' "$thermal_count"
$BB printf 'cpufreq_policy_count=%s\n' "$cpufreq_count"
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none
$BB printf '%s\n' sysfs_write_request=none cpu_trigger_request=none load_request=none
$BB printf '%s\n' thermal_value_read=none reboot_request=none
$BB printf '%s\n' dmesg_excerpt_begin
$BB dmesg | $BB grep -E '1000d000\.pwrap|mt6351-regulator|11230000\.mmc|mmc0:' | \
	$BB sed 's/=/ : /g; s/^/log: /'
$BB printf '%s\n' dmesg_excerpt_end
$BB printf '%s\n' __GEMINI_PWRAP_SERVICEABILITY_END__
