#!/bin/sh

# Validate one natural bind, one software-only unbind, and one exact rebind.
set -eu

sysfs_rw=0
i2c6=

restore_sysfs_ro()
{
	if /bin/busybox mount -o remount,ro /sys; then
		sysfs_rw=0
		return 0
	fi
	return 1
}

cleanup()
{
	if [ "$sysfs_rw" = 1 ]; then
		if ! restore_sysfs_ro; then
			printf 'cleanup_failure=sysfs-remount-ro\n'
		fi
	fi
}
trap cleanup EXIT HUP INT TERM

abort()
{
	printf 'post_event_lifecycle_result=FAIL\nfailure=%s\n' "$1"
	if [ -n "$i2c6" ] && [ -r "$i2c6/handoff_status" ]; then
		printf '__FAILURE_I2C6_STATUS_BEGIN__\n'
		/bin/busybox cat "$i2c6/handoff_status" || true
		printf '__FAILURE_I2C6_STATUS_END__\n'
	fi
	exit 1
}

counter()
{
	# shellcheck disable=SC2016 # The awk program is intentionally single-quoted.
	printf '%s\n' "$1" | /bin/busybox tr ' ' '\n' |
		/bin/busybox awk -F= -v key="$2" \
		'$1 == key { print $2; found = 1 } END { if (!found) exit 1 }'
}

sysfs_options()
{
	# shellcheck disable=SC2016 # The awk program is intentionally single-quoted.
	/bin/busybox awk '$2 == "/sys" && $3 == "sysfs" {
		print $4; found++
	} END { if (found != 1) exit 1 }' /proc/mounts
}

require_mount_option()
{
	case ",$1," in *,$2,*) ;; *) abort "sysfs-mount-not-$2" ;; esac
}

require_phase()
{
	phase="$1"
	status="$2"
	wanted="$3"
	primary="$4"
	page2="$5"

	[ "$(counter "$status" handoff)" = ready ] || abort "$phase-handoff"
	for key in transfer_attempts nonzero_starts irq_count; do
		[ "$(counter "$status" "$key")" = "$wanted" ] ||
			abort "$phase-$key"
	done
	[ "$(counter "$status" dma_starts)" = 0 ] || abort "$phase-dma_starts"
	[ "$(counter "$status" oracle_combined_pointer_reads)" = "$wanted" ] ||
		abort "$phase-combined-count"
	[ "$(counter "$status" oracle_primary_pointer_reads)" = "$primary" ] ||
		abort "$phase-primary-count"
	[ "$(counter "$status" oracle_page2_pointer_reads)" = "$page2" ] ||
		abort "$phase-page2-count"
	for key in oracle_write_only_messages \
		oracle_register_data_write_messages oracle_other_transfers \
		oracle_other_address_transfers suspend_checks resume_checks \
		resume_failures; do
		[ "$(counter "$status" "$key")" = 0 ] || abort "$phase-$key"
	done
}

emit_phase()
{
	phase="$1"
	status="$2"
	for key in transfer_attempts dma_starts nonzero_starts irq_count \
		oracle_combined_pointer_reads oracle_primary_pointer_reads \
		oracle_page2_pointer_reads oracle_write_only_messages \
		oracle_register_data_write_messages oracle_other_transfers \
		oracle_other_address_transfers; do
		printf '%s_%s=%s\n' "$phase" "$key" "$(counter "$status" "$key")"
	done
}

require_serviceability()
{
	phase="$1"
	[ "$(/bin/busybox cat /sys/devices/system/cpu/online)" = 0-7 ] ||
		abort "$phase-cpu-online"
	[ "$(/bin/busybox cat /sys/devices/system/cpu/offline)" = 8-9 ] ||
		abort "$phase-cpu-offline"
	[ "$(/bin/busybox cat /sys/class/net/usb0/operstate)" = up ] ||
		abort "$phase-usb-operstate"
	[ "$(/bin/busybox cat /sys/class/net/usb0/carrier)" = 1 ] ||
		abort "$phase-usb-carrier"
	[ -d /sys/class/tty/tty1 ] || abort "$phase-tty1"
	[ "$(/bin/busybox grep -c 'Name="keyboard-matrix"' /proc/bus/input/devices)" = 1 ] ||
		abort "$phase-keyboard"
}

wait_for_page2_dummy()
{
	attempt=0
	while [ "$attempt" -lt 30 ]; do
		if [ -d "$page2" ] &&
		   [ "$(/bin/busybox readlink -f "$page2/driver" 2>/dev/null || true)" = \
		     "$(/bin/busybox readlink -f "$dummy_driver")" ]; then
			return 0
		fi
		attempt=$((attempt + 1))
		/bin/busybox sleep 1
	done
	return 1
}

[ "$(/bin/busybox id -u)" = 0 ] || abort not-root
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-life27 ] ||
	abort kernel-identity
require_mount_option "$(sysfs_options)" ro
require_serviceability initial

natural_state="$(/bin/busybox cat /sys/kernel/gemini_da921x_natural_device_add)" ||
	abort natural-state-read
[ "$natural_state" = \
	'attempts=1 register_entries=1 register_returns=1 register_retval=0 callsite_entries=1 callsite_returns=1 public_returns=1 wrapper_entries=2 wrapper_returns=2 namespace_checks=2 untagged_routes=2 tagged_routes=0 sockets=1 listeners=0 allocations=0 broadcasts=0 uevent_retval=0' ] ||
	abort natural-state
[ "$(/bin/busybox cat /sys/kernel/gemini_da921x_dual_modalias_stage)" = 20 ] ||
	abort natural-stage

for path in /sys/bus/platform/devices/1100e000.i2c \
	/sys/devices/platform/soc/1100e000.i2c; do
	if [ -r "$path/handoff_status" ]; then
		i2c6="$path"
		break
	fi
done
[ -n "$i2c6" ] || abort i2c6-status-absent

driver=/sys/bus/i2c/drivers/da9213-legacy-regulator
dummy_driver=/sys/bus/i2c/drivers/dummy
client=/sys/bus/i2c/devices/1-0068
page2=/sys/bus/i2c/devices/1-0069
[ -d "$driver" ] || abort driver-absent
[ -d "$dummy_driver" ] || abort dummy-driver-absent
[ "$(/bin/busybox readlink -f "$client/driver")" = \
	"$(/bin/busybox readlink -f "$driver")" ] || abort initial-driver-not-bound
[ -d "$page2" ] || abort initial-page2-client-absent
[ "$(/bin/busybox readlink -f "$page2/driver")" = \
	"$(/bin/busybox readlink -f "$dummy_driver")" ] ||
	abort initial-page2-driver-mismatch
[ ! -d "$client/regulator" ] || abort provider-present

initial_status="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort initial-status-read
require_phase initial "$initial_status" 14 8 6
initial_matches="$(/bin/busybox dmesg | /bin/busybox grep -c \
	'DA9214 legacy direct-address identity matched; no regulators exposed')" || true
[ "$initial_matches" = 1 ] || abort initial-identity-log-count

/bin/busybox mount -o remount,rw /sys || abort sysfs-remount-rw
sysfs_rw=1
require_mount_option "$(sysfs_options)" rw
[ -w "$driver/unbind" ] || abort unbind-control-absent
[ -w "$driver/bind" ] || abort bind-control-absent

printf '%s' 1-0068 >"$driver/unbind" || abort unbind-write
[ ! -L "$client/driver" ] || abort driver-remained-bound
[ ! -e "$page2" ] || abort page2-client-remained
post_unbind_status="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort post-unbind-status-read
require_phase post_unbind "$post_unbind_status" 14 8 6

printf '%s' 1-0068 >"$driver/bind" || abort bind-write
[ "$(/bin/busybox readlink -f "$client/driver")" = \
	"$(/bin/busybox readlink -f "$driver")" ] || abort driver-did-not-rebind
wait_for_page2_dummy || abort rebound-page2-dummy-timeout
[ ! -d "$client/regulator" ] || abort rebound-provider-present
post_rebind_status="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort post-rebind-status-read
require_phase post_rebind "$post_rebind_status" 28 16 12

matches="$(/bin/busybox dmesg | /bin/busybox grep -c \
	'DA9214 legacy direct-address identity matched; no regulators exposed')" || true
[ "$matches" = 2 ] || abort final-identity-log-count

restore_sysfs_ro || abort sysfs-remount-ro
require_mount_option "$(sysfs_options)" ro
require_serviceability final
[ "$(/bin/busybox cat /sys/kernel/gemini_da921x_natural_device_add)" = \
	"$natural_state" ] || abort natural-state-changed

printf 'kernel=7.1.3-gemini-da921x-life27\n'
printf 'validation_stage=20\nnatural_device_add_state=%s\n' "$natural_state"
printf 'i2c_device=1-0068\nidentity_log_count=%s\n' "$matches"
printf 'page2_device=1-0069\npage2_driver=dummy\n'
emit_phase initial "$initial_status"
emit_phase post_unbind "$post_unbind_status"
emit_phase post_rebind "$post_rebind_status"
printf 'provider=absent\nconsumer=absent\n'
printf 'cpu_online=0-7\ncpu_offline=8-9\n'
printf 'sysfs=restored-read-only\nusb=serviceable\ntty1=present\nkeyboard=present\n'
printf 'device_storage_access=none\nautomatic_reboot=no\n'
printf 'post_event_lifecycle_result=PASS\n'
