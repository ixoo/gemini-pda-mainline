#!/bin/sh

# One bounded read-only frame for the repaired thermal-serviceability DT.
set -u
export LC_ALL=C

BB=/bin/busybox
PWRAP=/sys/bus/platform/devices/1000d000.pwrap
THERMAL=/sys/bus/platform/devices/1100b000.thermal
MMC=/sys/bus/platform/devices/11230000.mmc
DT=/sys/firmware/devicetree/base

driver_name() {
	if [ -L "$1/driver" ]; then $BB basename "$($BB readlink "$1/driver")"; else $BB printf 'none\n'; fi
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

config_count() { $BB zcat /proc/config.gz 2>/dev/null | $BB grep -Fxc "$1"; }
dmesg_count() { $BB dmesg | $BB grep -Eic "$1"; }
dt_string() { if [ -r "$1" ]; then $BB tr -d '\000' <"$1"; $BB printf '\n'; else $BB printf 'missing\n'; fi; }
dt_hex() { if [ -r "$1" ]; then $BB od -An -tx1 -v "$1" | $BB tr -d '[:space:]'; $BB printf '\n'; else $BB printf 'missing\n'; fi; }

$BB printf '%s\n' __GEMINI_THERMAL_DT_REPAIR_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'console_active='; $BB cat /sys/class/tty/console/active 2>/dev/null || $BB printf 'missing\n'
$BB printf 'dt_model='; dt_string "$DT/model"
$BB printf 'pwrap_dt_resets_hex='; dt_hex "$DT/pwrap@1000d000/resets"
$BB printf 'thermal_dt_resets_hex='; dt_hex "$DT/thermal@1100b000/resets"
$BB printf 'thermal_dt_phandle_hex='; dt_hex "$DT/thermal@1100b000/phandle"
$BB printf 'thermal_dt_status='; dt_string "$DT/thermal@1100b000/status"
$BB printf 'thermal_nvmem_cell_names='; dt_string "$DT/thermal@1100b000/nvmem-cell-names"
$BB printf 'auxadc_dt_status='; dt_string "$DT/adc@11001000/status"
$BB printf 'provider_dt_compatible='; dt_string "$DT/firmware/atag-devinfo/compatible"
$BB printf 'provider_dt_read_only='; if [ -e "$DT/firmware/atag-devinfo/read-only" ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'usb_controller_dt_status='; dt_string "$DT/usb@11271000/status"
$BB printf 'usb_phy_dt_status='; dt_string "$DT/t-phy@11290000/usb-phy@11290800/status"
$BB printf 'keyboard_dt_status='; dt_string "$DT/keyboard-matrix/status"
$BB printf 'simplefb_dt_present='; if [ -e "$DT/chosen/framebuffer@7dfb0000" ]; then $BB printf '1\n'; else $BB printf '0\n'; fi

$BB printf 'pwrap_driver='; driver_name "$PWRAP"
$BB printf 'pwrap_bind_count='; driver_bind_count mt-pmic-pwrap
$BB printf 'mt6351_core_bind_count='; driver_bind_count mt6397
$BB printf 'mt6351_regulator_bind_count='; driver_bind_count mt6351-regulator
$BB printf 'thermal_driver='; driver_name "$THERMAL"
$BB printf 'thermal_bind_count='; driver_bind_count mtk-thermal
$BB printf 'standalone_auxadc_bind_count='; driver_bind_count mt6797-auxadc
$BB printf 'mmc_driver='; driver_name "$MMC"
$BB printf 'mmc_bind_count='; driver_bind_count mtk-msdc

provider_count=0
provider_name=none
for item in /sys/bus/platform/drivers/mediatek-mt6797-atag-devinfo/*; do
	[ -L "$item" ] || continue
	[ "$($BB basename "$item")" = module ] && continue
	provider_count=$((provider_count + 1))
	provider_name=$($BB basename "$item")
done
$BB printf 'provider_platform_bind_count=%s\nprovider_platform_device=%s\n' "$provider_count" "$provider_name"

nvmem_count=0
nvmem_name=none
for item in /sys/bus/nvmem/devices/mt6797-atag-calibration*; do
	[ -e "$item" ] || continue
	nvmem_count=$((nvmem_count + 1))
	nvmem_name=$($BB basename "$item")
done
$BB printf 'nvmem_provider_count=%s\nnvmem_provider_name=%s\n' "$nvmem_count" "$nvmem_name"
$BB printf 'nvmem_binary_content_read=no\n'

vemc=0
vio18=0
for item in /sys/class/regulator/regulator.*; do
	[ -r "$item/name" ] || continue
	name=$($BB cat "$item/name")
	[ "$name" = vemc_3v3 ] && vemc=$((vemc + 1))
	[ "$name" = vio18 ] && vio18=$((vio18 + 1))
done
$BB printf 'vemc_3v3_count=%s\nvio18_count=%s\n' "$vemc" "$vio18"

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
zone_name=none
zone_type=none
zone_device=none
zone_path=none
for item in /sys/class/thermal/thermal_zone[0-9]*; do
	[ -e "$item" ] || continue
	zone_count=$((zone_count + 1))
	zone_path=$item
	zone_name=$($BB basename "$item")
	zone_type=$($BB cat "$item/type" 2>/dev/null || $BB printf 'missing')
	[ ! -L "$item/device" ] || zone_device=$($BB basename "$($BB readlink "$item/device")")
done
$BB printf 'thermal_zone_count=%s\nthermal_zone_name=%s\nthermal_zone_type=%s\nthermal_zone_device=%s\n' "$zone_count" "$zone_name" "$zone_type" "$zone_device"
temperature_1=missing
temperature_2=missing
temperature_3=missing
if [ "$zone_count" = 1 ] && [ -r "$zone_path/temp" ]; then
	temperature_1=$($BB cat "$zone_path/temp" 2>/dev/null || $BB printf 'missing')
	$BB sleep 1
	temperature_2=$($BB cat "$zone_path/temp" 2>/dev/null || $BB printf 'missing')
	$BB sleep 1
	temperature_3=$($BB cat "$zone_path/temp" 2>/dev/null || $BB printf 'missing')
fi
$BB printf 'temperature_1_millicelsius=%s\ntemperature_2_millicelsius=%s\ntemperature_3_millicelsius=%s\n' "$temperature_1" "$temperature_2" "$temperature_3"

$BB printf 'config_thermal='; config_count 'CONFIG_THERMAL=y'
$BB printf 'config_mtk_thermal='; config_count 'CONFIG_MTK_THERMAL=y'
$BB printf 'config_thermal_ledger='; config_count 'CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER=y'
$BB printf 'config_cpufreq_disabled='; config_count '# CONFIG_CPU_FREQ is not set'
$BB printf 'config_cpuidle_disabled='; config_count '# CONFIG_CPU_IDLE is not set'
$BB printf 'config_suspend_disabled='; config_count '# CONFIG_SUSPEND is not set'
$BB printf 'pwrap_error_count='; dmesg_count '1000d000\.pwrap.*(failed|error|timeout|defer|returned -)'
$BB printf 'mmc_error_count='; dmesg_count '11230000\.mmc.*(failed|error|timeout|defer|returned -)'
$BB printf 'thermal_error_count='; dmesg_count '1100b000\.thermal.*(failed|error|timeout|defer|invalid|returned -)'
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none retained_ram_read_request=none
$BB printf '%s\n' sysfs_write_request=none cpu_trigger_request=none load_request=none cpufreq_request=none
$BB printf '%s\n' idle_request=none suspend_request=none nvmem_binary_content_output=none reboot_request=none
$BB printf '%s\n' dmesg_excerpt_begin
$BB dmesg | $BB grep -Ei '1000d000\.pwrap|mt6351-regulator|11230000\.mmc|mmc0:|atag-devinfo|1100b000\.thermal|mtk-thermal' | $BB sed 's/=/ : /g; s/^/log: /'
$BB printf '%s\n' dmesg_excerpt_end
$BB printf '%s\n' __GEMINI_THERMAL_DT_REPAIR_END__
