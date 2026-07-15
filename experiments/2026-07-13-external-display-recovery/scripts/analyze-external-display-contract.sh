#!/usr/bin/env bash

# Compare the vendor bridge declarations with Linux 7.1.3. This is source-only
# analysis; vendor files are evidence and are never copied into the repository.

set -eu
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}

[[ -d "$vendor_tree" ]] || { printf 'missing vendor tree: %s\n' "$vendor_tree" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing Linux tree: %s\n' "$linux_tree" >&2; exit 1; }

printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD 2>/dev/null || printf unknown)"
printf 'linux_tree=%s\n' "$linux_tree"

printf '\n[vendor bridge declarations]\n'
rg -n -C 3 -i 'sii9022|siiedid|hdmi|mhl|edid' \
	"$vendor_tree/arch/arm64/boot/dts" \
	"$vendor_tree/drivers" | head -n 300 || true

printf '\n[vendor bridge source in Git objects]\n'
vendor_tpi=drivers/misc/mediatek/hdmi/sil9024/siHdmiTx_902x_TPI.c
vendor_hdmi=drivers/misc/mediatek/hdmi/sil9024/hdmi_drv.c
if git -C "$vendor_tree" cat-file -e "HEAD:$vendor_tpi"; then
	printf 'vendor_driver_source=present:%s\n' "$vendor_tpi"
	for file in "$vendor_hdmi" "$vendor_tpi"; do
		printf '%s ' "$file"
		git -C "$vendor_tree" cat-file blob "HEAD:$file" | sha256sum
	done
	git -C "$vendor_tree" show "HEAD:$vendor_tpi" |
		rg -n -C 2 'SII902XA_DEVICE_ID|StartTPI|ReadByteTPI\(0x1B\)|DoEdidRead|siiReadSegmentBlockEDID' |
		head -n 180 || true
else
	printf 'vendor_driver_source=absent:%s\n' "$vendor_tpi"
fi

printf '\n[vendor source hashes]\n'
while IFS= read -r file; do
	sha256sum "$file"
done < <(find "$vendor_tree/drivers" -type f \( -iname '*sii*' -o -iname '*hdmi*' -o -iname '*mhl*' \) | sort | head -n 80)

printf '\n[linux bridge coverage]\n'
find "$linux_tree/drivers/gpu/drm" "$linux_tree/Documentation/devicetree/bindings" \
	-type f 2>/dev/null | rg -i 'sii902|hdmi|mhl|edid|bridge' | sort | head -n 240
if rg -n -i 'sii9022|sii902x' "$linux_tree/drivers/gpu/drm" \
	"$linux_tree/Documentation/devicetree/bindings"; then
	printf 'linux_sii902x_driver=present\n'
else
	printf 'linux_sii902x_driver=absent\n'
fi

printf '\n[decision]\n'
printf '%s\n' \
	'live_i2c_sii9022_and_edid_nodes_are_unbound' \
	'live_hdmitx_node_exists_but_no_bridge_driver_or_dmesg_binding_was_observed' \
	'linux_sii902x_support_must_be_checked_against_the_vendor_transport_and_board_graph' \
	'keep_external_display_disabled_until_physical_connector_bridge_power_reset_irq_and_graph_are_proven'
