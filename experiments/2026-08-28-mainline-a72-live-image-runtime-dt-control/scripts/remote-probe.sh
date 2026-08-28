#!/bin/sh

# Bounded read-only identity and serviceability probe.
set -eu
export LC_ALL=C
BB=/bin/busybox
readonly CANDIDATE=c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab

$BB printf '%s\n' __A72_RUNTIME_DT_CONTROL_BEGIN__
$BB printf 'installed_full_sha256=%s\n' "$CANDIDATE"
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
$BB printf 'controller_nodes='; $BB grep -aFl 'mediatek,mt6797-a72-admission-controller' /sys/firmware/devicetree/base/*/*/compatible 2>/dev/null | $BB wc -l
$BB printf 'binder_nodes='; $BB grep -aFl 'mediatek,mt6797-a72-admission-binder' /sys/firmware/devicetree/base/*/*/compatible 2>/dev/null | $BB wc -l
$BB printf 'platform_state_nodes='; $BB grep -aFl 'mediatek,mt6797-a72-platform-state' /sys/firmware/devicetree/base/*/*/compatible 2>/dev/null | $BB wc -l
$BB printf 'composed_observer_nodes='; $BB grep -aFl 'mediatek,mt6797-a72-platform-provider-clock-observer' /sys/firmware/devicetree/base/*/*/compatible 2>/dev/null | $BB wc -l
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none retained_ram_writes=none regulator_action_request=none clock_action_request=none secure_call_request=none owner_mutation_request=none cpu_admission_request=none reboot_request=none
$BB printf '%s\n' __A72_RUNTIME_DT_CONTROL_END__
