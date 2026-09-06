#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only

set -eu

[ "$#" -eq 3 ] || {
	printf 'collector requires expected release, boot ID and model\n' >&2
	exit 64
}

expected_release=$1
expected_boot_id=$2
expected_model=$3
dt=/proc/device-tree
platform=/sys/bus/platform/devices

read_release() {
	uname -r
}

read_boot_id() {
	tr -d '\n' </proc/sys/kernel/random/boot_id
}

read_model() {
	tr -d '\000\n' <"$dt/model"
}

require_identity() {
	stage=$1
	release=$(read_release)
	boot_id=$(read_boot_id)
	model=$(read_model)
	[ "$release" = "$expected_release" ] || {
		printf '%s identity release mismatch\n' "$stage" >&2
		exit 65
	}
	[ "$boot_id" = "$expected_boot_id" ] || {
		printf '%s identity boot ID mismatch\n' "$stage" >&2
		exit 65
	}
	[ "$model" = "$expected_model" ] || {
		printf '%s identity model mismatch\n' "$stage" >&2
		exit 65
	}
	printf 'release_%s=%s\n' "$stage" "$release"
	printf 'boot_id_%s=%s\n' "$stage" "$boot_id"
	printf 'model_%s=%s\n' "$stage" "$model"
}

emit_hex_file() {
	label=$1
	path=$2
	if [ ! -e "$path" ]; then
		printf '%s_status=missing\n' "$label"
		return
	fi
	if [ ! -r "$path" ]; then
		printf '%s_status=unreadable\n' "$label"
		return
	fi
	if ! raw=$(od -An -tx1 -v "$path" 2>/dev/null); then
		printf '%s_status=read-error\n' "$label"
		return
	fi
	bytes=$(wc -c <"$path" | tr -d ' ')
	hex=$(printf '%s' "$raw" | tr -d ' \n')
	printf '%s_status=present\n' "$label"
	printf '%s_bytes=%s\n' "$label" "$bytes"
	printf '%s_hex=%s\n' "$label" "$hex"
}

require_identity start

reserved=$dt/reserved-memory
printf 'reserved_context_begin\n'
emit_hex_file root_address_cells "$dt/#address-cells"
emit_hex_file root_size_cells "$dt/#size-cells"
emit_hex_file reserved_address_cells "$reserved/#address-cells"
emit_hex_file reserved_size_cells "$reserved/#size-cells"
emit_hex_file reserved_ranges "$reserved/ranges"
printf 'reserved_context_end\n'

printf 'reserved_nodes_begin\n'
if [ -d "$reserved" ]; then
	for node in "$reserved"/*; do
		[ -d "$node" ] || continue
		name=${node##*/}
		case "$name" in
			*consys*|*conn*|*wmt*|*wifi*)
				printf 'reserved_node=%s\n' "$name"
				emit_hex_file reserved_reg "$node/reg"
				if [ -e "$node/no-map" ]; then
					printf 'reserved_no_map=yes\n'
				else
					printf 'reserved_no_map=no\n'
				fi
				if [ -e "$node/reusable" ]; then
					printf 'reserved_reusable=yes\n'
				else
					printf 'reserved_reusable=no\n'
				fi
				;;
		esac
	done
else
	printf 'reserved_directory_status=missing\n'
fi
printf 'reserved_nodes_end\n'

printf 'platform_owners_begin\n'
for dev in "$platform"/18070000.* "$platform"/180f0000.* \
		"$platform"/10001000.* "$platform"/11000000.*; do
	[ -e "$dev" ] || continue
	device=${dev##*/}
	case "$device" in
		180f0000.*) printf 'platform_role=wlan-attribution-crosscheck\n' ;;
		*) printf 'platform_role=additional-owner-observation\n' ;;
	esac
	printf 'platform_device=%s\n' "$device"
	if [ -L "$dev/driver" ]; then
		driver=$(readlink -f "$dev/driver")
		printf 'platform_driver=%s\n' "${driver##*/}"
	else
		printf 'platform_driver=unbound\n'
	fi
	if [ ! -e "$dev/resource" ]; then
		printf 'platform_resource_status=missing\n'
	elif [ ! -r "$dev/resource" ]; then
		printf 'platform_resource_status=unreadable\n'
	elif sed 's/^/platform_resource=/' "$dev/resource"; then
		printf 'platform_resource_status=present\n'
	else
		printf 'platform_resource_status=read-error\n'
	fi
done
printf 'platform_owners_end\n'

printf 'iomem_begin\n'
if [ ! -e /proc/iomem ]; then
	printf 'iomem_status=missing\n'
elif [ ! -r /proc/iomem ]; then
	printf 'iomem_status=unreadable\n'
elif awk 'tolower($0) ~ /consys|conn|wifi|wmt|18070000|180f0000|10001000|11000000/' /proc/iomem; then
	printf 'iomem_status=present\n'
else
	printf 'iomem_status=read-error\n'
fi
printf 'iomem_end\n'

require_identity end
