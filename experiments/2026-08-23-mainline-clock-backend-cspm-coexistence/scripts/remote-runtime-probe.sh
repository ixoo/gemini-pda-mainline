#!/bin/sh

# Read exact serviceability, resource ownership, and coexistence state over the
# initramfs netcat shell. This performs no memory, storage, CPU, or power action.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7
readonly CLOCK_PREFIX=GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1
readonly COEXIST_EXACT='GEMINI_CLOCK_BACKEND_CSPM_COEXISTENCE_V1 state=ready cspm_owner=handoff protected=0 bigidvfs=0 cpu=0'
readonly DRIVER_EXACT='GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1 stage=driver-init writes=1 protected=0 bigidvfs=0 cpu=0'
readonly ENTER_EXACT='GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1 stage=probe-enter writes=2 protected=0 bigidvfs=0 cpu=0'
readonly COMPLETE_EXACT='GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1 stage=probe-complete writes=2 protected=0 bigidvfs=0 cpu=0'
readonly OWNER_EXACT='protected clock readback transport ready; CSPM owner=handoff; state owner unregistered'
readonly OLD_CLOCK_PREFIX=GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_LIVE_V1
readonly FIRST_DMESG_PREFIX=GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1

clock_prefix_count="$($BB dmesg | $BB grep -Fc "$CLOCK_PREFIX" || true)"
coexistence_exact_count="$($BB dmesg | $BB grep -Fc "$COEXIST_EXACT" || true)"
driver_exact_count="$($BB dmesg | $BB grep -Fc "$DRIVER_EXACT" || true)"
enter_exact_count="$($BB dmesg | $BB grep -Fc "$ENTER_EXACT" || true)"
complete_exact_count="$($BB dmesg | $BB grep -Fc "$COMPLETE_EXACT" || true)"
owner_exact_count="$($BB dmesg | $BB grep -Fc "$OWNER_EXACT" || true)"
old_clock_prefix_count="$($BB dmesg | $BB grep -Fc "$OLD_CLOCK_PREFIX" || true)"
first_dmesg_prefix_count="$($BB dmesg | $BB grep -Fc "$FIRST_DMESG_PREFIX" || true)"
handoff_ebusy_count="$($BB dmesg | $BB grep -Ec '11015000\.dvfsp-handoff:.*(-16|EBUSY|resource)' || true)"

handoff=/sys/bus/platform/devices/11015000.dvfsp-handoff
i2c6=/sys/bus/platform/devices/1100e000.i2c
clock=/sys/bus/platform/devices/1001a000.dvfsp-clock-backend
handoff_bound=0
i2c6_bound=0
clock_backend_bound=0
[ -L "$handoff/driver" ] && handoff_bound=1
[ -L "$i2c6/driver" ] && i2c6_bound=1
[ -L "$clock/driver" ] && clock_backend_bound=1
handoff_state=missing
i2c6_handoff_ready_count=0
[ -r "$handoff/state" ] && handoff_state="$($BB cat "$handoff/state")"
[ -r "$i2c6/handoff_status" ] &&
	i2c6_handoff_ready_count="$($BB grep -c '^handoff=ready ' "$i2c6/handoff_status" || true)"

$BB printf '%s\n' __CLOCK_BACKEND_CSPM_COEXISTENCE_RUNTIME_BEGIN__
$BB printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'uptime_seconds='; $BB cut -d ' ' -f 1 /proc/uptime
$BB printf 'cmdline='; $BB cat /proc/cmdline
$BB printf 'model='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/model; $BB printf '\n'
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'udc_devices='; $BB find /sys/class/udc -mindepth 1 -maxdepth 1 2>/dev/null | $BB wc -l
$BB printf 'keyboard_matrix_inputs='; $BB grep -c 'Name="keyboard-matrix"' /proc/bus/input/devices || true
$BB printf 'da921x_i2c_clients='; $BB find /sys/bus/i2c/devices -maxdepth 1 -name '*-0068' 2>/dev/null | $BB wc -l
$BB printf 'same_value_write_attributes='; $BB find /sys/bus/i2c/devices -name same_value_write 2>/dev/null | $BB wc -l
$BB printf 'clock_backend_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-clock-backend*' 2>/dev/null | $BB wc -l
$BB printf 'bigidvfs_backend_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-bigidvfs-backend*' 2>/dev/null | $BB wc -l
$BB printf 'protected_readback_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*protected-readback*' 2>/dev/null | $BB wc -l
$BB printf 'handoff_bound=%s\ni2c6_bound=%s\nclock_backend_bound=%s\n' "$handoff_bound" "$i2c6_bound" "$clock_backend_bound"
$BB printf 'handoff_state=%s\ni2c6_handoff_ready_count=%s\n' "$handoff_state" "$i2c6_handoff_ready_count"
$BB printf 'cspm_range_count='; $BB grep -Ec '^[[:space:]]*11015000-11015fff : ' /proc/iomem || true
$BB printf 'cspm_handoff_owner_count='; $BB grep -Ec '^[[:space:]]*11015000-11015fff : 11015000\.dvfsp-handoff cspm$' /proc/iomem || true
$BB printf 'mcumixed_clock_owner_count='; $BB grep -Ec '^[[:space:]]*1001a000-1001afff : 1001a000\.dvfsp-clock-backend mcumixed$' /proc/iomem || true
$BB printf 'clock_prefix_count=%s\ncoexistence_exact_count=%s\n' "$clock_prefix_count" "$coexistence_exact_count"
$BB printf 'driver_init_exact_count=%s\nprobe_enter_exact_count=%s\n' "$driver_exact_count" "$enter_exact_count"
$BB printf 'probe_complete_exact_count=%s\nowner_exact_count=%s\n' "$complete_exact_count" "$owner_exact_count"
$BB printf 'old_clock_prefix_count=%s\nfirst_dmesg_prefix_count=%s\n' "$old_clock_prefix_count" "$first_dmesg_prefix_count"
$BB printf 'handoff_ebusy_count=%s\n' "$handoff_ebusy_count"
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none same_value_action_request=none
$BB printf '%s\n' protected_read_request=none secure_call_request=none
$BB printf '%s\n' mapped_mmio_transaction=none clock_enable_request=none
$BB printf '%s\n' owner_registration_request=none cpu_admission_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __CLOCK_BACKEND_CSPM_COEXISTENCE_RUNTIME_END__
