#!/bin/sh

# Bounded read-only live probe for the exact provider-ready candidate.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e
readonly TAG=GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1

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
$BB printf 'platform_state_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*a72-platform-state*' 2>/dev/null | $BB wc -l
$BB printf 'platform_state_bound='; if $BB test -L /sys/bus/platform/devices/10222000.a72-platform-state/driver; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'clock_backend_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-clock-backend*' 2>/dev/null | $BB wc -l
$BB printf 'clock_backend_bound='; if $BB test -L /sys/bus/platform/devices/1001a000.dvfsp-clock-backend/driver; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'bigidvfs_backend_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-bigidvfs-backend*' 2>/dev/null | $BB wc -l
$BB printf 'bigidvfs_backend_bound='; if $BB test -L /sys/bus/platform/devices/dvfsp-bigidvfs-backend/driver; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'composed_observer_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*a72-platform-provider-snapshot-observer*' 2>/dev/null | $BB wc -l
$BB printf 'composed_observer_bound='; if $BB test -L /sys/bus/platform/devices/a72-platform-provider-snapshot-observer/driver; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'platform_only_observer_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*a72-platform-snapshot-observer*' 2>/dev/null | $BB wc -l
$BB printf 'physical_observer_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*a72-physical-source-observer*' 2>/dev/null | $BB wc -l
$BB printf 'provider_i2c_devices='; $BB find /sys/bus/i2c/devices -mindepth 1 -maxdepth 1 -name '*-0068' 2>/dev/null | $BB wc -l
$BB printf 'provider_i2c_bound='; $BB find /sys/bus/i2c/drivers/da9213-legacy-regulator -mindepth 1 -maxdepth 1 -name '*-0068' 2>/dev/null | $BB wc -l
$BB printf 'usb_controller_status='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/usb@11271000/status; $BB printf '\n'
$BB printf 'tphy_status='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/t-phy@11290000/status; $BB printf '\n'
$BB printf 'i2c5_status='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/i2c@1101c000/status; $BB printf '\n'
$BB printf 'keyboard_status='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/keyboard-matrix/status; $BB printf '\n'
$BB printf '%s\n' __A72_EARLY_MARKERS_BEGIN__
$BB printf '%s\n' __A72_EARLY_MARKERS_END__
snapshot_log=$($BB dmesg 2>/dev/null | $BB grep -aF "$TAG" || true)
$BB printf 'snapshot_log_b64='; $BB printf '%s\n' "$snapshot_log" | $BB base64 | $BB tr -d '\n'; $BB printf '\n'
$BB printf 'snapshot_log_lines='; $BB printf '%s\n' "$snapshot_log" | $BB grep -aFc "$TAG" || true
$BB printf 'snapshot_failure_lines='; $BB dmesg 2>/dev/null | $BB grep -aFc 'platform/provider snapshot failed' || true
$BB printf '%s\n' platform_snapshot_request=boot-observer-one-shot
$BB printf '%s\n' platform_snapshot_calls_expected=1
$BB printf '%s\n' platform_samples_expected=2
$BB printf '%s\n' platform_register_observations_expected=26
$BB printf '%s\n' provider_readiness_request=explicit-phandle-bound-device
$BB printf '%s\n' provider_snapshot_request=one-stable-read-only
$BB printf '%s\n' provider_snapshots_expected=1
$BB printf '%s\n' provider_samples_expected=2
$BB printf '%s\n' provider_i2c_reads_expected=10
$BB printf '%s\n' provider_i2c_writes_expected=0
$BB printf '%s\n' clock_backend_read_request=none
$BB printf '%s\n' bigidvfs_backend_read_request=none
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none
$BB printf '%s\n' regulator_action_request=none
$BB printf '%s\n' clock_action_request=none
$BB printf '%s\n' secure_call_request=none
$BB printf '%s\n' provider_acquire_release_request=none
$BB printf '%s\n' observer_registration_request=dt-probe-only
$BB printf '%s\n' owner_registration_request=none
$BB printf '%s\n' cpu_admission_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __A72_EARLY_LIVE_CONTROL_END__
