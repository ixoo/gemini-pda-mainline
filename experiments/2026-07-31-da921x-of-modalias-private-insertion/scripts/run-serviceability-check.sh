#!/bin/sh

# Read-only acceptance check for one fresh selected boot.
set -eu

abort()
{
	printf 'private_insertion_result=FAIL\nfailure=%s\n' "$1"
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
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-ofinsert ] ||
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

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] ||
	i2c6=/sys/devices/platform/soc/1100e000.i2c
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

marker='GEMINI_DA921X_OF_MODALIAS_PRIVATE_INSERTION alias_length=38 entry_length=47 buflen=48 envp_idx=1 fallback=i2c'
marker_count="$(/bin/busybox dmesg | /bin/busybox grep -Fc "$marker")"
[ "$marker_count" = 1 ] || abort private-insertion-marker-count

printf 'kernel=7.1.3-gemini-da921x-ofinsert\n'
printf 'adapter=%s\nclient=%s\n' "$adapter" "${client##*/}"
printf 'client_name=da9214-legacy\nclient_of_node=present\n'
printf 'client_sysfs_modalias=of-real-compatible\n'
printf 'private_of_modalias_generated=exact\nprivate_of_modalias_length=38\n'
printf 'private_uevent_entry=exact\nprivate_uevent_entry_length=47\n'
printf 'private_uevent_buflen=48\nprivate_uevent_envp_idx=1\n'
printf 'client_uevent_modalias=i2c-fallback\nclient_driver=unbound\n'
printf 'i2c_activity=zero\npost_creation_serviceability=PASS\n'
printf 'private_insertion_result=PASS\n'
