#!/bin/sh

# Bounded read-only probe for the exact one-shot CPU8 admission candidate.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0
readonly ADMISSION_TAG=GEMINI_A72_ADMISSION_V1

$BB printf '%s\n' __A72_ADMISSION_RUNTIME_BEGIN__
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
$BB printf 'transition_ledger_hex='
$BB dd if=/dev/mem bs=1 skip=$((0x44410000)) count=84 2>/dev/null |
	$BB od -An -v -tx1 | $BB tr -d ' \n'
$BB printf '\n'
$BB printf '%s\n' __A72_ADMISSION_MARKERS_BEGIN__
$BB dmesg 2>/dev/null | $BB grep -aF "$ADMISSION_TAG" || true
$BB printf '%s\n' __A72_ADMISSION_MARKERS_END__
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none
$BB printf '%s\n' userspace_regulator_request=none
$BB printf '%s\n' userspace_clock_request=none
$BB printf '%s\n' userspace_secure_call_request=none
$BB printf '%s\n' userspace_cpu_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __A72_ADMISSION_RUNTIME_END__
