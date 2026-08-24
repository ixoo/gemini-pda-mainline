#!/bin/sh

# Bounded read-only probe for the exact A72 early-initcall live DT control.
# It emits only fixed identities, bounded counters, and exact GAEI markers.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef
readonly PURE='GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f'
readonly CORE='GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5'
readonly REFUSAL='GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=primary-refused slot=2 crc32=5767e326'

$BB printf '%s\n' __A72_EARLY_LIVE_CONTROL_BEGIN__
$BB printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'uptime_seconds='; $BB cut -d ' ' -f 1 /proc/uptime
$BB printf 'model='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/model; $BB printf '\n'
$BB printf 'compatible='; $BB tr '\000' ',' </sys/firmware/devicetree/base/compatible; $BB printf '\n'
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'maxcpus8_tokens='; $BB grep -Eoc '(^| )maxcpus=8( |$)' /proc/cmdline || true
$BB printf 'udc_devices='; $BB find /sys/class/udc -mindepth 1 -maxdepth 1 2>/dev/null | $BB wc -l
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf '%s\n' __A72_EARLY_MARKERS_BEGIN__
for file in $($BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null); do
	$BB grep -aF "$PURE" "$file" || true
	$BB grep -aF "$CORE" "$file" || true
	$BB grep -aF "$REFUSAL" "$file" || true
done
$BB dmesg 2>/dev/null | $BB grep -aF "$PURE" || true
$BB dmesg 2>/dev/null | $BB grep -aF "$CORE" || true
$BB dmesg 2>/dev/null | $BB grep -aF "$REFUSAL" || true
$BB printf '%s\n' __A72_EARLY_MARKERS_END__
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none
$BB printf '%s\n' regulator_action_request=none
$BB printf '%s\n' clock_action_request=none
$BB printf '%s\n' secure_call_request=none
$BB printf '%s\n' owner_registration_request=none
$BB printf '%s\n' cpu_admission_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __A72_EARLY_LIVE_CONTROL_END__
