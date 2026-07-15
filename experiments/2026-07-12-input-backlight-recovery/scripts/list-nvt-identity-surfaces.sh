#!/usr/bin/env bash

# Read-only inventory of NVT touchscreen endpoint names and modes.
#
# This intentionally lists metadata only. It never opens an attribute, reads
# /proc/NVTflash, follows a client endpoint, unbinds the driver, or performs an
# I2C transaction. Run on the device through SSH.

set -u
export LC_ALL=C

printf '%s\n' 'validation=nvt-identity-surface-inventory'
printf '%s\n' '[client_files]'
find /sys/bus/i2c/devices/4-0062 -maxdepth 3 -type f \
	-printf '%p mode=%m\n' 2>/dev/null | sort

printf '%s\n' '[driver_files]'
find /sys/bus/i2c/drivers/NVT-ts -maxdepth 2 -type f \
	-printf '%p mode=%m\n' 2>/dev/null | sort

printf '%s\n' '[proc_endpoints]'
for path in /proc/NVTflash /proc/NVTflash*; do
	[[ -e "$path" ]] || continue
	stat -c '%n mode=%a type=%F' "$path" 2>/dev/null || true
done | sort -u

printf '%s\n' '[safety]'
printf '%s\n' \
	'attribute_reads=none' \
	'i2c_transactions=none' \
	'driver_unbind=none' \
	'firmware_update=none' \
	'hardware_write=none'
