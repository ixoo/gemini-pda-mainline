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
reserved=$dt/reserved-memory
node=$reserved/consys-reserve-memory

read_release() { uname -r; }
read_boot_id() { tr -d '\n' </proc/sys/kernel/random/boot_id; }
read_model() { tr -d '\000\n' <"$dt/model"; }

require_identity() {
	stage=$1
	release=$(read_release)
	boot_id=$(read_boot_id)
	model=$(read_model)
	[ "$release" = "$expected_release" ] || exit 65
	[ "$boot_id" = "$expected_boot_id" ] || exit 65
	[ "$model" = "$expected_model" ] || exit 65
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
[ -d "$node" ] || {
	printf 'exact_node_status=missing\n'
	exit 66
}
printf 'declaration_begin\n'
emit_hex_file root_address_cells "$dt/#address-cells"
emit_hex_file root_size_cells "$dt/#size-cells"
emit_hex_file reserved_address_cells "$reserved/#address-cells"
emit_hex_file reserved_size_cells "$reserved/#size-cells"
emit_hex_file reserved_ranges "$reserved/ranges"
emit_hex_file node_reg "$node/reg"
emit_hex_file node_size "$node/size"
emit_hex_file node_alignment "$node/alignment"
emit_hex_file node_alloc_ranges "$node/alloc-ranges"
if [ -e "$node/no-map" ]; then
	printf 'node_no_map=yes\n'
else
	printf 'node_no_map=no\n'
fi
if [ -e "$node/reusable" ]; then
	printf 'node_reusable=yes\n'
else
	printf 'node_reusable=no\n'
fi
printf 'declaration_end\n'
require_identity end
