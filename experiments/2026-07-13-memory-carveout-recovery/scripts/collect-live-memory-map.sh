#!/usr/bin/env bash

# Read-only memory ownership inventory. The optional /proc/iomem section uses
# sudo -n and reports a permission gate instead of prompting or writing state.

set -u
export LC_ALL=C

section() { printf '\n[%s]\n' "$1"; }

section meminfo
grep -E '^(MemTotal|MemFree|MemAvailable|CmaTotal|CmaFree|SwapTotal|SwapFree):' \
	/proc/meminfo 2>/dev/null || true

section reserved-memory
for dev in /sys/firmware/devicetree/base/reserved-memory/*; do
	[ -d "$dev" ] || continue
	printf 'node=%s' "${dev##*/}"
	if [ -r "$dev/reg" ]; then
		printf ' reg='
		od -An -tx1 -v "$dev/reg" | tr -d ' \n'
	fi
	if [ -r "$dev/size" ]; then
		printf ' size='
		od -An -tx1 -v "$dev/size" | tr -d ' \n'
	fi
	[ -e "$dev/no-map" ] && printf ' no-map'
	printf '\n'
done

section iomem
if sudo -n true 2>/dev/null; then
	sudo -n cat /proc/iomem
else
	echo 'iomem=owner-authorized-sudo-required'
fi

section firmware-tree
if [ -r /sys/firmware/fdt ]; then
	stat -c 'fdt_size=%s' /sys/firmware/fdt 2>/dev/null || true
else
	echo 'fdt=unreadable'
fi
