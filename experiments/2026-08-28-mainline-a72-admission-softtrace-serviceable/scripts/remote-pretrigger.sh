#!/bin/sh

# Read-only live frame for the exact serviceable trace-softfail CPU8 candidate.
set -eu
export LC_ALL=C
BB=/bin/busybox
GROUP=/sys/bus/platform/devices/a72-admission-controller/gemini_admission
STATUS="$GROUP/status"
TRIGGER="$GROUP/trigger"

$BB printf '%s\n' __GEMINI_A72_LIVE_PRETRIGGER_BEGIN__
$BB printf '%s\n' installed_full_sha256=df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60
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
$BB printf 'controller_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name 'a72-admission-controller' 2>/dev/null | $BB wc -l
$BB printf 'controller_bound='; if $BB test -L /sys/bus/platform/devices/a72-admission-controller/driver; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'group_present='; if $BB test -d "$GROUP"; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'status_mode='; $BB stat -c '%a' "$STATUS" 2>/dev/null || $BB printf 'absent\n'
$BB printf 'status_uid='; $BB stat -c '%u' "$STATUS" 2>/dev/null || $BB printf 'absent\n'
$BB printf 'trigger_mode='; $BB stat -c '%a' "$TRIGGER" 2>/dev/null || $BB printf 'absent\n'
$BB printf 'trigger_uid='; $BB stat -c '%u' "$TRIGGER" 2>/dev/null || $BB printf 'absent\n'
$BB printf 'sysfs_options='; $BB awk "\$2 == \"/sys\" {print \$4; n++} END {if (n != 1) exit 1}" /proc/mounts
$BB printf 'live_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' sysfs_write_request=none
$BB printf '%s\n' supplier_resolution_request=none
$BB printf '%s\n' cpu_admission_request=none
$BB printf '%s\n' cpu_off_request=none
$BB printf '%s\n' retry_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __GEMINI_A72_LIVE_PRETRIGGER_END__
