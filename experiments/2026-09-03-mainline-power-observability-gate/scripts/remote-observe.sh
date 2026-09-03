#!/bin/sh
# shellcheck disable=SC2016

# Read-only current-candidate calibration and power-observability inventory.
set -u
export LC_ALL=C

BB=/bin/busybox
GROUP=/sys/bus/platform/devices/a72-admission-controller/gemini_admission
STATUS="$GROUP/status"
TRIGGER="$GROUP/trigger"
RECORD=/sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity
ATAG=/sys/firmware/devicetree/base/chosen/atag,devinfo
PROVIDER=/sys/firmware/devicetree/base/firmware/atag-devinfo
THERMAL=/sys/firmware/devicetree/base/thermal@1100b000
AUXADC=/sys/firmware/devicetree/base/adc@11001000

$BB printf '%s\n' __GEMINI_POWER_OBSERVABILITY_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'controller_bound='; if [ -r "$STATUS" ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'binder_bound='; if [ -d /sys/bus/platform/devices/a72-binder ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'platform_state_bound='; if [ -d /sys/bus/platform/devices/10222000.a72-platform-state ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'status_mode='; $BB stat -c '%a' "$STATUS" 2>/dev/null || $BB printf 'missing\n'
$BB printf 'trigger_mode='; $BB stat -c '%a' "$TRIGGER" 2>/dev/null || $BB printf 'missing\n'
$BB printf 'sysfs_options='; $BB awk '$2 == "/sys" { print $4 }' /proc/mounts
$BB printf 'record_identity='; if [ -r "$RECORD" ]; then $BB od -An -tx1 -v "$RECORD" | $BB tr -d '[:space:]'; $BB printf '\n'; else $BB printf 'missing\n'; fi
$BB printf 'live_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'

$BB printf 'atag_property_present='; if [ -r "$ATAG" ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'atag_property_bytes='; $BB wc -c <"$ATAG" 2>/dev/null | $BB tr -d '[:space:]'; $BB printf '\n'
$BB printf 'atag_property_sha256='; $BB sha256sum "$ATAG" 2>/dev/null | $BB awk '{print $1}'
$BB printf 'provider_dt_compatible='; $BB tr '\000' '\n' <"$PROVIDER/compatible" 2>/dev/null
$BB printf 'provider_dt_read_only='; if [ -e "$PROVIDER/read-only" ]; then $BB printf '1\n'; else $BB printf '0\n'; fi

platform_count=0
platform_name=none
for item in /sys/bus/platform/drivers/mediatek-mt6797-atag-devinfo/*; do
	[ -L "$item" ] || continue
	platform_count=$((platform_count + 1))
	platform_name=$($BB basename "$item")
done
$BB printf 'provider_platform_bind_count=%s\n' "$platform_count"
$BB printf 'provider_platform_device=%s\n' "$platform_name"
$BB printf 'provider_driver=mediatek-mt6797-atag-devinfo\n'

nvmem_count=0
nvmem_name=none
for item in /sys/bus/nvmem/devices/mt6797-atag-calibration*; do
	[ -e "$item" ] || continue
	nvmem_count=$((nvmem_count + 1))
	nvmem_name=$($BB basename "$item")
done
$BB printf 'nvmem_provider_count=%s\n' "$nvmem_count"
$BB printf 'nvmem_provider_name=%s\n' "$nvmem_name"
$BB printf 'nvmem_binary_content_read=no\n'

$BB printf 'thermal_dt_status='; $BB tr -d '\000' <"$THERMAL/status" 2>/dev/null || $BB printf 'missing'; $BB printf '\n'
$BB printf 'auxadc_dt_status='; $BB tr -d '\000' <"$AUXADC/status" 2>/dev/null || $BB printf 'missing'; $BB printf '\n'
thermal_count=0
for item in /sys/class/thermal/thermal_zone[0-9]*; do [ -e "$item" ] && thermal_count=$((thermal_count + 1)); done
cpufreq_count=0
for item in /sys/devices/system/cpu/cpufreq/policy[0-9]*; do [ -e "$item" ] && cpufreq_count=$((cpufreq_count + 1)); done
$BB printf 'thermal_zone_count=%s\n' "$thermal_count"
$BB printf 'cpufreq_policy_count=%s\n' "$cpufreq_count"

$BB printf '%s\n' device_partition_reads=none device_storage_writes=none
$BB printf '%s\n' sysfs_write_request=none cpu_admission_request=none cpu_off_request=none
$BB printf '%s\n' nvmem_payload_output=none calibration_value_output=none
$BB printf '%s\n' retry_request=none reboot_request=none
$BB printf '%s\n' __GEMINI_POWER_OBSERVABILITY_END__
