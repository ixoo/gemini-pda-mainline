#!/bin/sh

# Read the exact serviceability, ownership, and one-shot protected-clock result
# over the initramfs netcat shell. The probe itself performs no hardware action.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6
readonly CLOCK_PREFIX='GEMINI_PROTECTED_READBACK_V1 clock ret='
readonly CLOCK_SUCCESS_PREFIX='GEMINI_PROTECTED_READBACK_V1 clock ret=0 abi=1 generation=1 '
readonly TERMINAL_PREFIX='GEMINI_PROTECTED_READBACK_V1 state=complete'
readonly TERMINAL_EXACT='GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=0 cpu_requests=0 owner_registration=0'
readonly BIGIDVFSP_PREFIX='GEMINI_PROTECTED_READBACK_V1 bigidvfs ret='
readonly OWNER_EXACT='protected clock readback transport ready; CSPM owner=handoff; state owner unregistered'

dmesg="$($BB dmesg)"
clock_prefix_count="$(printf '%s\n' "$dmesg" | $BB grep -Fc "$CLOCK_PREFIX" || true)"
clock_success_prefix_count="$(printf '%s\n' "$dmesg" | $BB grep -Fc "$CLOCK_SUCCESS_PREFIX" || true)"
clock_shape_count="$(printf '%s\n' "$dmesg" | $BB grep -Ec \
	'GEMINI_PROTECTED_READBACK_V1 clock ret=0 abi=1 generation=1 muxsel=0x[[:xdigit:]]{8} ckdiv=0x[[:xdigit:]]{8} pll_ll=0x[[:xdigit:]]{8},0x[[:xdigit:]]{8},0x[[:xdigit:]]{8} pll_l=0x[[:xdigit:]]{8},0x[[:xdigit:]]{8},0x[[:xdigit:]]{8} pll_cci=0x[[:xdigit:]]{8},0x[[:xdigit:]]{8},0x[[:xdigit:]]{8} cspm_swctrl=0x[[:xdigit:]]{8},0x[[:xdigit:]]{8},0x[[:xdigit:]]{8} cspm_hwsta=0x[[:xdigit:]]{8},0x[[:xdigit:]]{8},0x[[:xdigit:]]{8},0x[[:xdigit:]]{8}$' || true)"
terminal_prefix_count="$(printf '%s\n' "$dmesg" | $BB grep -Fc "$TERMINAL_PREFIX" || true)"
terminal_exact_count="$(printf '%s\n' "$dmesg" | $BB grep -Fc "$TERMINAL_EXACT" || true)"
bigidvfs_record_count="$(printf '%s\n' "$dmesg" | $BB grep -Fc "$BIGIDVFSP_PREFIX" || true)"
owner_exact_count="$(printf '%s\n' "$dmesg" | $BB grep -Fc "$OWNER_EXACT" || true)"
handoff_ebusy_count="$(printf '%s\n' "$dmesg" | $BB grep -Ec '11015000\.dvfsp-handoff:.*(-16|EBUSY|resource)' || true)"

handoff=/sys/bus/platform/devices/11015000.dvfsp-handoff
i2c6=/sys/bus/platform/devices/1100e000.i2c
clock=/sys/bus/platform/devices/1001a000.dvfsp-clock-backend
observer=/sys/bus/platform/devices/protected-readback-observer
handoff_bound=0
i2c6_bound=0
clock_backend_bound=0
observer_bound=0
[ -L "$handoff/driver" ] && handoff_bound=1
[ -L "$i2c6/driver" ] && i2c6_bound=1
[ -L "$clock/driver" ] && clock_backend_bound=1
[ -L "$observer/driver" ] && observer_bound=1
handoff_state=missing
i2c6_handoff_ready_count=0
[ -r "$handoff/state" ] && handoff_state="$($BB cat "$handoff/state")"
[ -r "$i2c6/handoff_status" ] &&
	i2c6_handoff_ready_count="$($BB grep -c '^handoff=ready ' "$i2c6/handoff_status" || true)"

$BB printf '%s\n' __PROTECTED_CLOCK_FIRST_DMESG_RUNTIME_BEGIN__
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
$BB printf 'handoff_bound=%s\ni2c6_bound=%s\nclock_backend_bound=%s\nobserver_bound=%s\n' \
	"$handoff_bound" "$i2c6_bound" "$clock_backend_bound" "$observer_bound"
$BB printf 'handoff_state=%s\ni2c6_handoff_ready_count=%s\n' "$handoff_state" "$i2c6_handoff_ready_count"
$BB printf 'cspm_range_count='; $BB grep -Ec '^[[:space:]]*11015000-11015fff : ' /proc/iomem || true
$BB printf 'cspm_handoff_owner_count='; $BB grep -Ec '^[[:space:]]*11015000-11015fff : 11015000\.dvfsp-handoff cspm$' /proc/iomem || true
$BB printf 'mcumixed_clock_owner_count='; $BB grep -Ec '^[[:space:]]*1001a000-1001afff : 1001a000\.dvfsp-clock-backend mcumixed$' /proc/iomem || true
$BB printf 'clock_prefix_count=%s\nclock_success_prefix_count=%s\nclock_shape_count=%s\n' \
	"$clock_prefix_count" "$clock_success_prefix_count" "$clock_shape_count"
$BB printf 'terminal_prefix_count=%s\nterminal_exact_count=%s\n' \
	"$terminal_prefix_count" "$terminal_exact_count"
$BB printf 'bigidvfs_record_count=%s\nowner_exact_count=%s\nhandoff_ebusy_count=%s\n' \
	"$bigidvfs_record_count" "$owner_exact_count" "$handoff_ebusy_count"
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none same_value_action_request=none
$BB printf '%s\n' observer_trigger=automatic-probe-once
$BB printf '%s\n' protected_clock_caller_retries=zero bigidvfs_calls=zero
$BB printf '%s\n' mapped_clock_mmio_read_snapshots=one clock_enable_disable_pairs=one
$BB printf '%s\n' secure_calls=zero owner_registration_request=none
$BB printf '%s\n' cpu_admission_request=none reboot_request=none
$BB printf '%s\n' __PROTECTED_CLOCK_FIRST_DMESG_RUNTIME_END__
