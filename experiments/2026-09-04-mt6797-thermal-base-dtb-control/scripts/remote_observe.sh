#!/bin/sh

# One bounded read-only serviceability frame for the base-DT control.
set -u
export LC_ALL=C

BB=/bin/busybox
PWRAP=/sys/bus/platform/devices/1000d000.pwrap
THERMAL=/sys/bus/platform/devices/1100b000.thermal
MMC=/sys/bus/platform/devices/11230000.mmc
DT=/sys/firmware/devicetree/base

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

dt_string() {
	if [ -r "$1" ]; then $BB tr -d '\000' <"$1"; $BB printf '\n'; else $BB printf 'missing\n'; fi
}

dmesg_count() { $BB dmesg | $BB grep -Eic "$1"; }
config_count() { $BB zcat /proc/config.gz 2>/dev/null | $BB grep -Fxc "$1"; }

$BB printf '%s\n' __GEMINI_THERMAL_BASE_DTB_CONTROL_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'console_active='; $BB cat /sys/class/tty/console/active 2>/dev/null || $BB printf 'missing\n'
$BB printf 'dt_model='; dt_string "$DT/model"
$BB printf 'thermal_dt_status='; dt_string "$DT/thermal@1100b000/status"
$BB printf 'auxadc_dt_status='; dt_string "$DT/adc@11001000/status"
$BB printf 'thermal_zone_node='; if [ -e "$DT/thermal-zones" ]; then $BB printf 'present\n'; else $BB printf 'absent\n'; fi
$BB printf 'pwrap_driver='; driver_name "$PWRAP"
$BB printf 'pwrap_bind_count='; driver_bind_count mt-pmic-pwrap
$BB printf 'mt6351_core_bind_count='; driver_bind_count mt6397
$BB printf 'mt6351_regulator_bind_count='; driver_bind_count mt6351-regulator
$BB printf 'thermal_driver='; driver_name "$THERMAL"
$BB printf 'thermal_bind_count='; driver_bind_count mtk-thermal
$BB printf 'mmc_driver='; driver_name "$MMC"
$BB printf 'mmc_bind_count='; driver_bind_count mtk-msdc

vemc=0
vio18=0
for item in /sys/class/regulator/regulator.*; do
	[ -r "$item/name" ] || continue
	name=$($BB cat "$item/name")
	[ "$name" = vemc_3v3 ] && vemc=$((vemc + 1))
	[ "$name" = vio18 ] && vio18=$((vio18 + 1))
done
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
for item in /sys/class/block/mmcblk0p*; do [ -e "$item" ] && partition_count=$((partition_count + 1)); done
$BB printf 'mmc_card_count=%s\nmmc_card_type=%s\n' "$card_count" "$card_type"
$BB printf 'mmcblk0_present='; if [ -e /sys/class/block/mmcblk0 ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'mmcblk0_partition_count=%s\n' "$partition_count"

zone_count=0
for item in /sys/class/thermal/thermal_zone[0-9]*; do [ -e "$item" ] && zone_count=$((zone_count + 1)); done
$BB printf 'thermal_zone_count=%s\n' "$zone_count"
$BB printf 'config_thermal='; config_count 'CONFIG_THERMAL=y'
$BB printf 'config_thermal_ledger='; config_count 'CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER=y'
$BB printf 'config_cpufreq_disabled='; config_count '# CONFIG_CPU_FREQ is not set'
$BB printf 'config_cpuidle_disabled='; config_count '# CONFIG_CPU_IDLE is not set'
$BB printf 'config_suspend_disabled='; config_count '# CONFIG_SUSPEND is not set'
$BB printf 'pwrap_error_count='; dmesg_count '1000d000\.pwrap.*(failed|error|timeout|defer|returned -)'
$BB printf 'mmc_error_count='; dmesg_count '11230000\.mmc.*(failed|error|timeout|defer|returned -)'
$BB printf 'thermal_error_count='; dmesg_count '1100b000\.thermal.*(failed|error|timeout|defer|invalid|returned -)'
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none
$BB printf '%s\n' retained_ram_write_request=none temperature_read_request=none
$BB printf '%s\n' cpu_trigger_request=none load_request=none cpufreq_request=none
$BB printf '%s\n' idle_request=none suspend_request=none reboot_request=none
$BB printf '%s\n' dmesg_excerpt_begin
$BB dmesg | $BB grep -Ei '1000d000\.pwrap|mt6351-regulator|11230000\.mmc|mmc0:|1100b000\.thermal|mtk-thermal' | $BB sed 's/=/ : /g; s/^/log: /'
$BB printf '%s\n' dmesg_excerpt_end
$BB printf '%s\n' __GEMINI_THERMAL_BASE_DTB_CONTROL_END__
