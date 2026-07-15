#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Read-only boot handoff probe for the authorized Gemini device.

set -u
export LC_ALL=C

read_text() {
	local path=$1
	if [[ -r "$path" ]]; then
		tr '\000' ' ' < "$path" 2>/dev/null | sed 's/[[:space:]]*$//'
	fi
}

sanitize() {
	sed -E \
		-e 's/((androidboot\.)?(serialno|imei|meid|cid|wifi_mac|bt_mac|macaddr))=[^ ]+/\1=<redacted>/Ig' \
		-e 's/([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}/<redacted-mac>/g'
}

echo "boot-contract-probe=read-only"
uname -a
printf 'model=%s\n' "$(read_text /sys/firmware/devicetree/base/model)"
printf 'compatible=%s\n' "$(read_text /sys/firmware/devicetree/base/compatible)"
if [[ -r /sys/firmware/devicetree/base/chosen/bootargs ]]; then
	printf 'chosen.bootargs='
	read_text /sys/firmware/devicetree/base/chosen/bootargs | sanitize
	printf '\n'
fi
for property in linux,initrd-start linux,initrd-end; do
	if [[ -r "/sys/firmware/devicetree/base/chosen/$property" ]]; then
		printf 'chosen.%s=' "$property"
		od -An -v -tx1 "/sys/firmware/devicetree/base/chosen/$property" | tr -d ' \n'
		printf '\n'
	fi
done
printf 'root-mounts=\n'
awk '$1 ~ /^\/dev\/mmcblk0p/ {print $1, $2, $3}' /proc/mounts
printf 'partitions=\n'
cat /proc/partitions
printf 'boot-device-nodes=\n'
for node in /sys/class/block/mmcblk0boot0 /sys/class/block/mmcblk0boot1 /sys/class/block/mmcblk0p*; do
	[[ -e "$node" ]] || continue
	printf '%s|size=%s|ro=%s\n' "$node" "$(read_text "$node/size")" "$(read_text "$node/ro")"
done
