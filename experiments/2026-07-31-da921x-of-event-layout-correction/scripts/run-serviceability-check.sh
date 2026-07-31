#!/bin/sh

# Read-only acceptance check for one fresh selected corrected-layout boot.
set -eu

abort()
{
	printf 'of_event_layout_correction_result=FAIL\nfailure=%s\n' "$1"
	exit 1
}

counter()
{
	# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
	printf '%s\n' "$1" | /bin/busybox tr ' ' '\n' |
		/bin/busybox awk -F= -v key="$2" \
		'$1 == key { print $2; found = 1 } END { if (!found) exit 1 }'
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
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-ofevent ] ||
	abort kernel-identity
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
for path in "$state_path" "$stage_path" "$envelope_path" \
	"$classification_path"; do
	[ -r "$path" ] || abort "observation-absent-${path##*/}"
done
state="$(/bin/busybox cat "$state_path")" || abort validation-state-read
stage="$(/bin/busybox cat "$stage_path")" || abort validation-stage-read
envelope="$(/bin/busybox cat "$envelope_path")" || abort envelope-read
classification="$(/bin/busybox cat "$classification_path")" ||
	abort classification-read
[ "$state" = validated ] || abort validation-state
[ "$stage" = 17 ] || abort validation-stage
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

printf 'kernel=7.1.3-gemini-da921x-ofevent\n'
printf 'validation_state=%s\nvalidation_stage=%s\n' "$state" "$stage"
printf 'envp_idx=9\nenvp_capacity=64\nterminator_null=1\n'
printf 'buflen=245\nbuf_capacity=2048\n'
printf 'present_mask=0xff\nduplicate_mask=0x0\n'
printf 'ordered_prefix=8\nseqnum_count=1\nseqnum_index=8\n'
printf 'unexpected_count=0\n'
printf 'adapter=%s\nclient=%s\n' "$adapter" "${client##*/}"
printf 'client_name=da9214-legacy\nclient_of_node=present\n'
printf 'client_sysfs_modalias=of-real-compatible\n'
printf 'validation_observation=read-only-sysfs\nvalidation_printk=absent\n'
printf 'event_transport=skipped\nclient_driver=unbound\ni2c_activity=zero\n'
printf 'post_creation_serviceability=PASS\n'
printf 'of_event_layout_correction_result=PASS\n'
