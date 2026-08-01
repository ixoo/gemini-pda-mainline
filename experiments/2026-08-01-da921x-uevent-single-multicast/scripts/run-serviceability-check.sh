#!/bin/sh

# Read-only except for a temporary writable remount of the virtual sysfs and
# one exact-token write to each of the predecessor and experiment triggers. The sysfs mount is
# restored read-only before result evaluation and from the exit trap on every
# failure path. The two separately staged listeners are removed by the host
# collector after this one fresh selected-boot check.
set -eu

sysfs_restore_required=0

restore_sysfs()
{
	[ "$sysfs_restore_required" = 1 ] || return 0
	/bin/busybox mount -o remount,ro /sys >/dev/null 2>&1 || true
}

handle_signal()
{
	restore_sysfs
	exit 1
}

trap restore_sysfs EXIT
trap handle_signal HUP INT TERM

abort()
{
	printf 'uevent_single_multicast_result=FAIL\nfailure=%s\n' "$1"
	exit 1
}

counter()
{
	# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
	printf '%s\n' "$1" | /bin/busybox tr ' ' '\n' |
		/bin/busybox awk -F= -v key="$2" \
		'$1 == key { print $2; found = 1 } END { if (!found) exit 1 }'
}

sysfs_options()
{
	# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
	/bin/busybox awk '$2 == "/sys" && $3 == "sysfs" {
		print $4; found++
	} END { if (found != 1) exit 1 }' /proc/mounts
}

require_mount_option()
{
	case ",$1," in
	*,"$2",*) ;;
	*) abort "sysfs-mount-not-$2" ;;
	esac
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

predecessor_listener=/run/.gemini-bounded-listener
predecessor_listener_sha256=056618b3a508fa49e1d171e1667dbd6db22466fc408e6effb0f90fa099c84a21
listener=/run/.gemini-single-multicast-listener
listener_sha256=08f0afeb04b43c049418df420e6a136a14aea1d9ee9026b8ffaffdde6a56502f
[ "$(/bin/busybox id -u)" = 0 ] || abort not-root
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-mcast1 ] ||
	abort kernel-identity
[ -x "$predecessor_listener" ] || abort predecessor-listener-helper-absent
# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
[ "$(/bin/busybox sha256sum "$predecessor_listener" | /bin/busybox awk '{print $1}')" = \
	"$predecessor_listener_sha256" ] || abort predecessor-listener-helper-identity
[ -x "$listener" ] || abort listener-helper-absent
# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
[ "$(/bin/busybox sha256sum "$listener" | /bin/busybox awk '{print $1}')" = \
	"$listener_sha256" ] || abort listener-helper-identity
[ "$(/bin/busybox cat /sys/devices/system/cpu/online)" = 0-7 ] ||
	abort cpu-online-set
[ "$(/bin/busybox cat /sys/devices/system/cpu/offline)" = 8-9 ] ||
	abort cpu-offline-set
[ ! -e /lib/da9213-legacy-regulator.ko ] || abort module-file-present
[ ! -e /sbin/modprobe ] || abort modprobe-present
[ ! -d /sys/module/da9213_legacy_regulator ] || abort module-resident
[ ! -d /sys/bus/i2c/drivers/da9213-legacy-regulator ] ||
	abort matching-driver-present

state_path=/sys/kernel/gemini_da921x_dual_modalias_state
stage_path=/sys/kernel/gemini_da921x_dual_modalias_stage
envelope_path=/sys/kernel/gemini_da921x_dual_modalias_envelope
classification_path=/sys/kernel/gemini_da921x_dual_modalias_entry_classification
listener_path=/sys/kernel/gemini_da921x_uevent_listener_state
delivery_path=/sys/kernel/gemini_da921x_uevent_no_listener_state
bounded_path=/sys/kernel/gemini_da921x_uevent_bounded_listener
multicast_path=/sys/kernel/gemini_da921x_uevent_single_multicast
for path in "$state_path" "$stage_path" "$envelope_path" \
	"$classification_path" "$listener_path" "$delivery_path" "$bounded_path" \
	"$multicast_path"; do
	[ -r "$path" ] || abort "observation-absent-${path##*/}"
done
state="$(/bin/busybox cat "$state_path")" || abort validation-state-read
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-read
envelope="$(/bin/busybox cat "$envelope_path")" || abort envelope-read
classification="$(/bin/busybox cat "$classification_path")" ||
	abort classification-read
listener_state="$(/bin/busybox cat "$listener_path")" || abort listener-state-read
delivery_state="$(/bin/busybox cat "$delivery_path")" || abort delivery-state-read
bounded_state="$(/bin/busybox cat "$bounded_path")" || abort bounded-state-read
multicast_state="$(/bin/busybox cat "$multicast_path")" || abort multicast-state-read
[ "$state" = validated ] || abort validation-state
[ "$stage" = 20 ] || abort validation-stage-before-trigger
[ "$(counter "$listener_state" sockets)" = 1 ] || abort listener-sockets-before
[ "$(counter "$listener_state" listeners)" = 0 ] || abort listener-count-before
[ "$(counter "$delivery_state" sockets)" = 1 ] || abort delivery-sockets
[ "$(counter "$delivery_state" listeners)" = 0 ] || abort delivery-listeners
[ "$(counter "$delivery_state" allocations)" = 0 ] || abort delivery-allocations
[ "$(counter "$delivery_state" broadcasts)" = 0 ] || abort delivery-broadcasts
[ "$(counter "$delivery_state" retval)" = 0 ] || abort delivery-retval
[ "$bounded_state" = \
	'attempts=0 baseline_sockets=-1 sockets=-1 listeners=-1 broadcasts=-1' ] ||
	abort bounded-state-before-trigger
[ "$multicast_state" = \
	'attempts=0 baseline_sockets=-1 sockets=-1 listeners=-1 allocations=-1 broadcasts=-1 retval=-1' ] ||
	abort multicast-state-before-trigger

mount_options="$(sysfs_options)" || abort sysfs-mount-identity-before
require_mount_option "$mount_options" ro
/bin/busybox mount -o remount,rw /sys || abort sysfs-remount-rw
sysfs_restore_required=1
mount_options="$(sysfs_options)" || abort sysfs-mount-identity-during
require_mount_option "$mount_options" rw

set +e
predecessor_result="$("$predecessor_listener" 2>&1)"
predecessor_status=$?
set -e
if [ "$predecessor_status" -ne 0 ]; then
	printf '%s\n' "$predecessor_result"
	abort predecessor-listener-helper-failed
fi
printf '%s\n' "$predecessor_result" | /bin/busybox grep -qx \
	'listener_ready=1' || abort predecessor-listener-ready-result
printf '%s\n' "$predecessor_result" | /bin/busybox grep -qx \
	'listener_groups=0x1' || abort predecessor-listener-group-result
printf '%s\n' "$predecessor_result" | /bin/busybox grep -qx \
	'trigger_write=exact-probe-token' || abort predecessor-trigger-result
printf '%s\n' "$predecessor_result" | /bin/busybox grep -qx \
	'listener_receipt=none-bounded-timeout' || abort predecessor-receipt-result
printf '%s\n' "$predecessor_result" | /bin/busybox grep -qx \
	'bounded_listener_result=PASS' || abort predecessor-listener-pass-result

state="$(/bin/busybox cat "$state_path")" || abort validation-state-reread
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-reread
envelope="$(/bin/busybox cat "$envelope_path")" || abort envelope-reread
classification="$(/bin/busybox cat "$classification_path")" ||
	abort classification-reread
listener_state="$(/bin/busybox cat "$listener_path")" || abort listener-state-reread
bounded_state="$(/bin/busybox cat "$bounded_path")" || abort bounded-state-reread
[ "$state" = validated ] || abort validation-state-after-trigger
[ "$stage" = 21 ] || abort validation-stage-after-trigger
[ "$(counter "$envelope" envp_idx)" = 9 ] || abort envelope-envp-idx
[ "$(counter "$envelope" envp_capacity)" = 64 ] || abort envelope-envp-capacity
[ "$(counter "$envelope" terminator_null)" = 1 ] || abort envelope-terminator
[ "$(counter "$envelope" buflen)" = 245 ] || abort envelope-buflen
[ "$(counter "$envelope" buf_capacity)" = 2048 ] || abort envelope-buf-capacity
[ "$(counter "$classification" present_mask)" = 0xff ] || abort present-mask
[ "$(counter "$classification" duplicate_mask)" = 0x0 ] || abort duplicate-mask
[ "$(counter "$classification" ordered_prefix)" = 8 ] || abort ordered-prefix
[ "$(counter "$classification" seqnum_count)" = 1 ] || abort seqnum-count
[ "$(counter "$classification" seqnum_index)" = 8 ] || abort seqnum-index
[ "$(counter "$classification" unexpected_count)" = 0 ] || abort unexpected-count
[ "$(counter "$listener_state" sockets)" = 1 ] || abort listener-sockets-after
[ "$(counter "$listener_state" listeners)" = 1 ] || abort listener-count-after
[ "$bounded_state" = \
	'attempts=1 baseline_sockets=1 sockets=1 listeners=1 broadcasts=0' ] ||
	abort bounded-state-after-trigger

set +e
listener_result="$("$listener" 2>&1)"
listener_status=$?
set -e
/bin/busybox mount -o remount,ro /sys || abort sysfs-remount-ro
mount_options="$(sysfs_options)" || abort sysfs-mount-identity-after
require_mount_option "$mount_options" ro
sysfs_restore_required=0
if [ "$listener_status" -ne 0 ]; then
	printf '%s\n' "$listener_result"
	abort listener-helper-failed
fi
printf '%s\n' "$listener_result" | /bin/busybox grep -qx 'listener_ready=1' ||
	abort listener-ready-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx 'listener_groups=0x1' ||
	abort listener-group-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'trigger_write=exact-probe-token' || abort trigger-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'listener_receipt=one-exact-datagram' || abort receipt-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'receipt_bytes=293' || abort receipt-size-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'receipt_entries=9' || abort receipt-entry-result
printf '%s\n' "$listener_result" | /bin/busybox grep -Eq \
	'^seqnum_digits=[1-9][0-9]*$' || abort receipt-seqnum-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'receipt_source=kernel-group-1' || abort receipt-source-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'receipt_credentials=root' || abort receipt-credentials-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'duplicate_receipt=none-bounded-timeout' || abort duplicate-result
printf '%s\n' "$listener_result" | /bin/busybox grep -qx \
	'single_multicast_result=PASS' || abort listener-pass-result

state="$(/bin/busybox cat "$state_path")" || abort validation-state-final
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-final
multicast_state="$(/bin/busybox cat "$multicast_path")" || abort multicast-state-final
[ "$state" = validated ] || abort validation-state-after-multicast
[ "$stage" = 22 ] || abort validation-stage-after-multicast
[ "$multicast_state" = \
	'attempts=1 baseline_sockets=1 sockets=1 listeners=1 allocations=1 broadcasts=1 retval=0' ] ||
	abort multicast-state-after-trigger
[ "$(/bin/busybox dmesg | /bin/busybox grep -c \
	'GEMINI_DA921X_DUAL_MODALIAS_PRE_DISPATCH')" = 0 ] ||
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
	*1100e000.i2c/i2c-*)
		[ -z "$adapter" ] || abort multiple-i2c6-adapters
		adapter="${path##*/i2c-}"
		;;
	esac
done
[ -n "$adapter" ] || abort i2c6-adapter-absent
client="/sys/bus/i2c/devices/$adapter-0068"
[ -d "$client" ] || abort client-absent
[ "$(/bin/busybox cat "$client/name")" = da9214-legacy ] || abort client-name
[ -e "$client/of_node" ] || abort of-node-absent
[ "$(/bin/busybox tr -d '\000' <"$client/of_node/compatible")" = \
	dlg,da9214-legacy ] || abort of-compatible
[ ! -L "$client/driver" ] || abort unexpected-driver-bind
[ "$(/bin/busybox cat "$client/modalias")" = \
	'of:NregulatorT(null)Cdlg,da9214-legacy' ] || abort sysfs-modalias

printf '%s\n' "$predecessor_result"
printf '%s\n' "$listener_result"
printf 'kernel=7.1.3-gemini-da921x-mcast1\n'
printf 'validation_state=%s\nvalidation_stage=%s\n' "$state" "$stage"
printf 'envp_idx=9\nenvp_capacity=64\nterminator_null=1\n'
printf 'buflen=245\nbuf_capacity=2048\n'
printf 'present_mask=0xff\nduplicate_mask=0x0\n'
printf 'ordered_prefix=8\nseqnum_count=1\nseqnum_index=8\n'
printf 'unexpected_count=0\n'
printf 'uevent_sockets=1\nuevent_group1_listeners=1\n'
printf 'delivery_sockets=1\ndelivery_listeners=0\n'
printf 'delivery_allocations=0\ndelivery_broadcasts=0\ndelivery_retval=0\n'
printf 'bounded_attempts=1\nbounded_baseline_sockets=1\n'
printf 'bounded_sockets=1\nbounded_listeners=1\nbounded_broadcasts=0\n'
printf 'multicast_attempts=1\nmulticast_baseline_sockets=1\n'
printf 'multicast_sockets=1\nmulticast_listeners=1\n'
printf 'multicast_allocations=1\nmulticast_broadcasts=1\nmulticast_retval=0\n'
printf 'adapter=%s\nclient=%s\n' "$adapter" "${client##*/}"
printf 'client_name=da9214-legacy\nclient_of_node=present\n'
printf 'client_sysfs_modalias=of-real-compatible\n'
printf 'validation_observation=read-only-sysfs\nvalidation_printk=absent\n'
printf 'event_transport=one-exact-single-multicast-and-receipt\n'
printf 'sysfs_trigger_mount=temporary-rw-restored-ro\n'
printf 'client_driver=unbound\ni2c_activity=zero\n'
printf 'post_creation_serviceability=PASS\n'
printf 'uevent_single_multicast_result=PASS\n'
