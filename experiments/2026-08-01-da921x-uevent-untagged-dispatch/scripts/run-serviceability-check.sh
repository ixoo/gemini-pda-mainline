#!/bin/sh

# Continue only from the independently reconstructed stage-22 predecessor.
# Read-only except for one exact-token trigger while virtual sysfs is
# temporarily writable; the exit trap restores it read-only on every path.
set -eu

sysfs_restore_required=0
restore_sysfs()
{
	[ "$sysfs_restore_required" = 1 ] || return 0
	/bin/busybox mount -o remount,ro /sys >/dev/null 2>&1 || true
}
handle_signal() { restore_sysfs; exit 1; }
trap restore_sysfs EXIT
trap handle_signal HUP INT TERM

abort()
{
	printf 'uevent_untagged_dispatch_result=FAIL\nfailure=%s\n' "$1"
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
	case ",$1," in *,"$2",*) ;; *) abort "sysfs-mount-not-$2" ;; esac
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

listener=/run/.gemini-untagged-dispatch-listener
listener_sha256=6ca94f0197026b43ba651cc15f2b2b6eb9cc5c328781cd0fb68e04669fb292e2
[ "$(/bin/busybox id -u)" = 0 ] || abort not-root
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-untag ] || abort kernel-identity
[ -x "$listener" ] || abort listener-helper-absent
# shellcheck disable=SC2016
[ "$(/bin/busybox sha256sum "$listener" | /bin/busybox awk '{print $1}')" = \
	"$listener_sha256" ] || abort listener-helper-identity
[ "$(/bin/busybox cat /sys/devices/system/cpu/online)" = 0-7 ] || abort cpu-online-set
[ "$(/bin/busybox cat /sys/devices/system/cpu/offline)" = 8-9 ] || abort cpu-offline-set
[ ! -e /lib/da9213-legacy-regulator.ko ] || abort module-file-present
[ ! -e /sbin/modprobe ] || abort modprobe-present
[ ! -d /sys/module/da9213_legacy_regulator ] || abort module-resident
[ ! -d /sys/bus/i2c/drivers/da9213-legacy-regulator ] || abort matching-driver-present

state_path=/sys/kernel/gemini_da921x_dual_modalias_state
stage_path=/sys/kernel/gemini_da921x_dual_modalias_stage
multicast_path=/sys/kernel/gemini_da921x_uevent_single_multicast
untagged_path=/sys/kernel/gemini_da921x_uevent_untagged_dispatch
for path in "$state_path" "$stage_path" "$multicast_path" "$untagged_path"; do
	[ -r "$path" ] || abort "observation-absent-${path##*/}"
done
state="$(/bin/busybox cat "$state_path")" || abort validation-state-read
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-read
multicast_state="$(/bin/busybox cat "$multicast_path")" || abort multicast-state-read
untagged_state="$(/bin/busybox cat "$untagged_path")" || abort untagged-state-read
[ "$state" = validated ] || abort validation-state
[ "$stage" = 22 ] || abort validation-stage-before-trigger
[ "$multicast_state" = \
	'attempts=1 baseline_sockets=1 sockets=1 listeners=1 allocations=1 broadcasts=1 retval=0' ] ||
	abort multicast-predecessor-state
[ "$untagged_state" = \
	'attempts=0 entries=0 returns=0 baseline_sockets=-1 sockets=-1 listeners=-1 allocations=-1 broadcasts=-1 retval=-1' ] ||
	abort untagged-state-before-trigger

mount_options="$(sysfs_options)" || abort sysfs-mount-identity-before
require_mount_option "$mount_options" ro
/bin/busybox mount -o remount,rw /sys || abort sysfs-remount-rw
sysfs_restore_required=1
mount_options="$(sysfs_options)" || abort sysfs-mount-identity-during
require_mount_option "$mount_options" rw
set +e
listener_result="$("$listener" 2>&1)"
listener_status=$?
set -e
/bin/busybox mount -o remount,ro /sys || abort sysfs-remount-ro
mount_options="$(sysfs_options)" || abort sysfs-mount-identity-after
require_mount_option "$mount_options" ro
sysfs_restore_required=0
[ "$listener_status" -eq 0 ] || { printf '%s\n' "$listener_result"; abort listener-helper-failed; }
for exact in \
	'listener_ready=1' 'listener_groups=0x1' 'trigger_write=exact-probe-token' \
	'listener_receipt=one-exact-datagram' 'receipt_bytes=293' 'receipt_entries=9' \
	'receipt_source=kernel-group-1' 'receipt_credentials=root' \
	'duplicate_receipt=none-bounded-timeout' 'untagged_dispatch_result=PASS'; do
	printf '%s\n' "$listener_result" | /bin/busybox grep -qx "$exact" || abort listener-result
done
printf '%s\n' "$listener_result" | /bin/busybox grep -Eq '^seqnum_digits=[1-9][0-9]*$' ||
	abort receipt-seqnum-result

state="$(/bin/busybox cat "$state_path")" || abort validation-state-final
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-final
untagged_state="$(/bin/busybox cat "$untagged_path")" || abort untagged-state-final
[ "$state" = validated ] || abort validation-state-after-trigger
[ "$stage" = 23 ] || abort validation-stage-after-trigger
[ "$untagged_state" = \
	'attempts=1 entries=1 returns=1 baseline_sockets=1 sockets=1 listeners=1 allocations=1 broadcasts=1 retval=0' ] ||
	abort untagged-state-after-trigger
[ "$(/bin/busybox dmesg | /bin/busybox grep -c 'GEMINI_DA921X_DUAL_MODALIAS_PRE_DISPATCH')" = 0 ] ||
	abort predecessor-printk-present

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
	*1100e000.i2c/i2c-*) [ -z "$adapter" ] || abort multiple-i2c6-adapters; adapter="${path##*/i2c-}" ;;
	esac
done
[ -n "$adapter" ] || abort i2c6-adapter-absent
client="/sys/bus/i2c/devices/$adapter-0068"
[ -d "$client" ] || abort client-absent
[ "$(/bin/busybox cat "$client/name")" = da9214-legacy ] || abort client-name
[ -e "$client/of_node" ] || abort of-node-absent
[ "$(/bin/busybox tr -d '\000' <"$client/of_node/compatible")" = dlg,da9214-legacy ] || abort of-compatible
[ ! -L "$client/driver" ] || abort unexpected-driver-bind
[ "$(/bin/busybox cat "$client/modalias")" = 'of:NregulatorT(null)Cdlg,da9214-legacy' ] || abort sysfs-modalias

printf '%s\n' "$listener_result"
printf 'kernel=7.1.3-gemini-da921x-untag\nvalidation_state=%s\nvalidation_stage=%s\n' "$state" "$stage"
printf 'untagged_attempts=1\nuntagged_entries=1\nuntagged_returns=1\n'
printf 'untagged_baseline_sockets=1\nuntagged_sockets=1\nuntagged_listeners=1\n'
printf 'untagged_allocations=1\nuntagged_broadcasts=1\nuntagged_retval=0\n'
printf 'adapter=%s\nclient=%s\nclient_driver=unbound\n' "$adapter" "${client##*/}"
printf 'i2c_activity=zero\nsysfs_trigger_mount=temporary-rw-restored-ro\n'
printf 'post_creation_serviceability=PASS\nuevent_untagged_dispatch_result=PASS\n'
