#!/bin/sh

# Run exactly once as root through the direct USB shell.
set -eu

abort()
{
	printf 'name_only_result=FAIL\n'
	printf 'failure=%s\n' "$1"
	exit 1
}

counter()
{
	# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
	printf '%s\n' "$1" | /bin/busybox awk -F= -v key="$2" \
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
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-mod ] ||
	abort kernel-identity
[ "$(/bin/busybox cat /sys/devices/system/cpu/online)" = 0-7 ] ||
	abort cpu-online-set
[ "$(/bin/busybox cat /sys/devices/system/cpu/offline)" = 8-9 ] ||
	abort cpu-offline-set

child=/sys/firmware/devicetree/base/i2c@1100e000/regulator@68
[ "$(/bin/busybox tr '\000' ' ' <"$child/compatible")" = dlg,da9214-legacy ] ||
	abort child-compatible
[ "$(/bin/busybox tr '\000' ' ' <"$child/status")" = disabled ] ||
	abort child-not-disabled
[ ! -e /lib/da9213-legacy-regulator.ko ] || abort module-file-present
[ ! -e /sbin/modprobe ] || abort modprobe-present
[ ! -d /sys/module/da9213_legacy_regulator ] || abort module-resident
[ ! -d /sys/bus/i2c/drivers/da9213-legacy-regulator ] ||
	abort matching-driver-present
[ "$(/bin/busybox grep -c -E 'da9213|da921x' /proc/kallsyms || true)" = 0 ] ||
	abort matching-symbol-present

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] ||
	i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || abort i2c6-status-absent
before="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort pre-status-read
require_zero_status "$before"
[ "$(counter "$before" handoff)" = ready ] || abort handoff-not-ready

adapter=
for path in /sys/bus/i2c/devices/i2c-*; do
	[ -d "$path" ] || continue
	parent="$(/bin/busybox readlink -f "$path/device")"
	case "$parent" in
	*1100e000.i2c)
		[ -z "$adapter" ] || abort multiple-i2c6-adapters
		adapter="${path##*/i2c-}"
		;;
	esac
done
[ -n "$adapter" ] || abort i2c6-adapter-absent
client="/sys/bus/i2c/devices/$adapter-0068"
[ ! -e "$client" ] || abort client-already-present
control="/sys/bus/i2c/devices/i2c-$adapter/new_device"
[ -w "$control" ] || abort new-device-control-unavailable

printf 'pre_creation_serviceability=PASS\n'
printf 'adapter=%s\nclient_name=da9214-legacy\nclient_address=0x68\n' "$adapter"
printf 'da9214-legacy 0x68\n' >"$control" || abort new-device-write
/bin/busybox sleep 2

[ -d "$client" ] || abort client-not-created
[ "$(/bin/busybox cat "$client/name")" = da9214-legacy ] ||
	abort client-name-changed
[ ! -e "$client/of_node" ] || abort unexpected-of-node
[ ! -L "$client/driver" ] || abort unexpected-driver-bind
after="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort post-status-read
require_zero_status "$after"

printf 'created_client=%s\n' "${client##*/}"
printf 'created_client_of_node=absent\n'
printf 'created_client_driver=unbound\n'
printf 'post_creation_serviceability=PASS\n'
printf 'i2c_activity=zero\n'
printf 'name_only_result=PASS\n'
