#!/bin/sh

# Read-only validation of the boot-time natural device-add boundary.
set -eu

abort()
{
	printf 'natural_device_add_result=FAIL\nfailure=%s\n' "$1"
	exit 1
}

counter()
{
	# shellcheck disable=SC2016
	printf '%s\n' "$1" | /bin/busybox tr ' ' '\n' |
		/bin/busybox awk -F= -v key="$2" \
		'$1 == key { print $2; found = 1 } END { if (!found) exit 1 }'
}

sysfs_options()
{
	# shellcheck disable=SC2016
	/bin/busybox awk '$2 == "/sys" && $3 == "sysfs" {
		print $4; found++
	} END { if (found != 1) exit 1 }' /proc/mounts
}

require_mount_option()
{
	case ",$1," in *,$2,*) ;; *) abort "sysfs-mount-not-$2" ;; esac
}

require_zero_status()
{
	status="$1"
	for key in transfer_attempts dma_starts nonzero_starts irq_count \
		oracle_combined_pointer_reads oracle_primary_pointer_reads \
		oracle_page2_pointer_reads oracle_write_only_messages \
		oracle_register_data_write_messages oracle_other_transfers \
		oracle_other_address_transfers; do
		[ "$(counter "$status" "$key")" = 0 ] || abort "nonzero-$key"
	done
}

[ "$(/bin/busybox id -u)" = 0 ] || abort not-root
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-devadd ] || abort kernel-identity
[ "$(/bin/busybox cat /sys/devices/system/cpu/online)" = 0-7 ] || abort cpu-online-set
[ "$(/bin/busybox cat /sys/devices/system/cpu/offline)" = 8-9 ] || abort cpu-offline-set
[ ! -e /lib/da9213-legacy-regulator.ko ] || abort module-file-present
[ ! -e /sbin/modprobe ] || abort modprobe-present
[ ! -d /sys/module/da9213_legacy_regulator ] || abort module-resident
[ ! -d /sys/bus/i2c/drivers/da9213-legacy-regulator ] || abort matching-driver-present

state_path=/sys/kernel/gemini_da921x_dual_modalias_state
stage_path=/sys/kernel/gemini_da921x_dual_modalias_stage
listener_path=/sys/kernel/gemini_da921x_uevent_listener_state
no_listener_path=/sys/kernel/gemini_da921x_uevent_no_listener_state
natural_path=/sys/kernel/gemini_da921x_natural_device_add
for path in "$state_path" "$stage_path" "$listener_path" \
	"$no_listener_path" "$natural_path"; do
	[ -r "$path" ] || abort "observation-absent-${path##*/}"
done
state="$(/bin/busybox cat "$state_path")" || abort validation-state-read
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-read
listener_state="$(/bin/busybox cat "$listener_path")" || abort listener-state-read
no_listener_state="$(/bin/busybox cat "$no_listener_path")" || abort no-listener-state-read
natural_state="$(/bin/busybox cat "$natural_path")" || abort natural-state-read
[ "$state" = validated ] || abort validation-state
[ "$stage" = 26 ] || abort validation-stage
[ "$listener_state" = 'sockets=1 listeners=0' ] || abort listener-state
[ "$no_listener_state" = \
	'sockets=1 listeners=0 allocations=0 broadcasts=0 retval=0' ] ||
	abort no-listener-state
[ "$natural_state" = \
	'attempts=1 register_entries=1 register_returns=1 register_retval=0 callsite_entries=1 callsite_returns=1 public_returns=1 wrapper_entries=1 wrapper_returns=1 namespace_checks=1 untagged_routes=1 tagged_routes=0 sockets=1 listeners=0 allocations=0 broadcasts=0 uevent_retval=0' ] ||
	abort natural-state
[ "$(/bin/busybox dmesg | /bin/busybox grep -c 'GEMINI_DA921X_DUAL_MODALIAS_PRE_DISPATCH')" = 0 ] ||
	abort predecessor-printk-present
require_mount_option "$(sysfs_options)" ro

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || abort i2c6-status-absent
status="$(/bin/busybox cat "$i2c6/handoff_status")" || abort status-read
require_zero_status "$status"
[ "$(counter "$status" handoff)" = ready ] || abort handoff-not-ready

adapter=
for path in /sys/bus/i2c/devices/i2c-*; do
	[ -d "$path" ] || continue
	parent="$(/bin/busybox readlink -f "$path")"
	case "$parent" in
	*1100e000.i2c/i2c-*)
		[ -z "$adapter" ] || abort multiple-i2c6-adapters
		adapter="${path##*/i2c-}"
		;;
	esac
done
[ "$adapter" = 1 ] || abort i2c6-adapter-identity
client="/sys/bus/i2c/devices/$adapter-0068"
[ -d "$client" ] || abort client-absent
[ "$(/bin/busybox cat "$client/name")" = da9214-legacy ] || abort client-name
[ -e "$client/of_node" ] || abort of-node-absent
[ "$(/bin/busybox tr -d '\000' <"$client/of_node/compatible")" = dlg,da9214-legacy ] ||
	abort of-compatible
[ ! -L "$client/driver" ] || abort unexpected-driver-bind
[ "$(/bin/busybox cat "$client/modalias")" = \
	'of:NregulatorT(null)Cdlg,da9214-legacy' ] || abort sysfs-modalias

[ -d /sys/class/net/usb0 ] || abort usb0-absent
[ "$(/bin/busybox cat /sys/class/net/usb0/operstate)" = up ] || abort usb0-not-up
[ "$(/bin/busybox cat /sys/class/net/usb0/carrier)" = 1 ] || abort usb0-no-carrier
[ -d /sys/class/tty/tty1 ] || abort tty1-absent
[ "$(/bin/busybox grep -c 'Name="keyboard-matrix"' /proc/bus/input/devices)" = 1 ] ||
	abort keyboard-matrix-count

printf 'kernel=7.1.3-gemini-da921x-devadd\n'
printf 'validation_state=%s\nvalidation_stage=%s\n' "$state" "$stage"
printf 'natural_device_add_state=%s\n' "$natural_state"
printf 'uevent_listener_state=%s\nuevent_no_listener_state=%s\n' \
	"$listener_state" "$no_listener_state"
printf 'adapter=%s\nclient=%s\nclient_driver=unbound\n' "$adapter" "${client##*/}"
printf 'cpu_online=0-7\ncpu_offline=8-9\n'
printf 'i2c_activity=zero\noracle_activity=zero\n'
printf 'sysfs=read-only\nusb=serviceable\ntty1=present\nkeyboard=present\n'
printf 'device_storage_access=none\nnatural_device_add_result=PASS\n'
