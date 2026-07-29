#!/bin/sh

# Run once as root from the exact Gate 3 serviceability initramfs.
set -eu

abort()
{
	printf 'gate3_result=FAIL\n'
	printf 'failure=%s\n' "$1"
	exit 1
}

counter()
{
	# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
	printf '%s\n' "$1" | /bin/busybox awk -F= -v key="$2" \
		'$1 == key { print $2; found = 1 } END { if (!found) exit 1 }'
}

require_phase()
{
	phase="$1"
	status="$2"
	combined="$3"
	primary="$4"
	page2="$5"

	[ "$(counter "$status" oracle_combined_pointer_reads)" = "$combined" ] ||
		abort "$phase-combined-count"
	[ "$(counter "$status" oracle_primary_pointer_reads)" = "$primary" ] ||
		abort "$phase-primary-count"
	[ "$(counter "$status" oracle_page2_pointer_reads)" = "$page2" ] ||
		abort "$phase-page2-count"
	for key in oracle_write_only_messages \
		oracle_register_data_write_messages oracle_other_transfers \
		oracle_other_address_transfers; do
		[ "$(counter "$status" "$key")" = 0 ] ||
			abort "$phase-$key"
	done
}

emit_phase()
{
	phase="$1"
	status="$2"
	for key in oracle_combined_pointer_reads \
		oracle_primary_pointer_reads oracle_page2_pointer_reads \
		oracle_write_only_messages oracle_register_data_write_messages \
		oracle_other_transfers oracle_other_address_transfers; do
		printf '%s_%s=%s\n' "$phase" "$key" "$(counter "$status" "$key")"
	done
}

[ "$(/bin/busybox id -u)" = 0 ] || abort not-root
[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-da921x-life ] ||
	abort kernel-identity
/bin/busybox grep -q 'maxcpus=8' /proc/cmdline || abort maxcpus-missing
[ "$(/bin/busybox cat /sys/devices/system/cpu/online)" = 0-7 ] ||
	abort cpu-online-set
[ "$(/bin/busybox cat /sys/devices/system/cpu/offline)" = 8-9 ] ||
	abort cpu-offline-set

i2c6=
for path in /sys/bus/platform/devices/1100e000.i2c \
	/sys/devices/platform/soc/1100e000.i2c; do
	if [ -r "$path/handoff_status" ]; then
		i2c6="$path"
		break
	fi
done
[ -n "$i2c6" ] || abort i2c6-status-absent

driver=/sys/bus/i2c/drivers/da9213-legacy-regulator
[ -w "$driver/unbind" ] || abort unbind-control-absent
[ -w "$driver/bind" ] || abort bind-control-absent
device=
for link in "$driver"/*-0068; do
	if [ -L "$link" ]; then
		[ -z "$device" ] || abort multiple-bound-devices
		device="${link##*/}"
	fi
done
[ -n "$device" ] || abort initial-driver-not-bound

initial_status="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort initial-status-read
require_phase initial "$initial_status" 14 8 6

printf '%s' "$device" >"$driver/unbind" || abort unbind-write
[ ! -L "$driver/$device" ] || abort driver-remained-bound
post_unbind_status="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort post-unbind-status-read
require_phase post_unbind "$post_unbind_status" 14 8 6

printf '%s' "$device" >"$driver/bind" || abort bind-write
[ -L "$driver/$device" ] || abort driver-did-not-rebind
post_rebind_status="$(/bin/busybox cat "$i2c6/handoff_status")" ||
	abort post-rebind-status-read
require_phase post_rebind "$post_rebind_status" 28 16 12

matches="$(/bin/busybox dmesg | /bin/busybox grep -c \
	'DA9214 legacy direct-address identity matched; no regulators exposed')" ||
	true
[ "$matches" -eq 2 ] || abort identity-log-count

printf 'experiment=2026-07-29-da921x-legacy-lifecycle\n'
printf 'kernel_release=%s\n' "$(/bin/busybox uname -r)"
printf 'cpu_online=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
printf 'cpu_offline=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/offline)"
printf 'i2c_device=%s\n' "$device"
printf 'identity_log_count=%s\n' "$matches"
emit_phase initial "$initial_status"
emit_phase post_unbind "$post_unbind_status"
emit_phase post_rebind "$post_rebind_status"
printf 'provider=absent\n'
printf 'consumer=absent\n'
printf 'automatic_reboot=no\n'
printf 'gate3_result=PASS\n'
