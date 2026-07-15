#!/usr/bin/env bash

# Read-only Gemini MT6797 connectivity inventory.
#
# This avoids rfkill changes, network scans, HCI commands, WMT ioctls,
# debugfs writes, and firmware loading. It records platform contracts visible
# through procfs/sysfs and hashes only named firmware files already installed.

set -u
export LC_ALL=C

heading() {
	printf '\n===== %s =====\n' "$1"
}

first_line() {
	[[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

property_text() {
	local path="$1"
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"
	tr '\0' ',' < "$path" | sed 's/,$//'
	printf '\n'
}

property_hex() {
	local path="$1"
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"
	od -An -tx1 -v "$path" | tr -d ' \n'
	printf '\n'
}

heading "running kernel"
uname -a
if [[ -r /proc/device-tree/model ]]; then
	printf 'model='
	tr '\0' '\n' < /proc/device-tree/model
fi

heading "sanitized Android connectivity properties"
if command -v getprop >/dev/null 2>&1; then
	getprop 2>/dev/null | grep -Ei \
		'\[(mediatek\.wlan\.chip|mediatek\.wlan\.module\.postfix|persist\.mtk\.wcn\.combo\.chipid|persist\.mtk\.connsys\.poweron\.ctl|ro\.mtk_agps_app|ro\.mtk_gps_support|ro\.wlan\.mtk\.wifi\.5g|fmradio\.driver\.enable|wifi\.interface|wifi\.direct\.interface|wifi\.tethering\.interface|ro\.mediatek\.platform|ro\.board\.platform|init\.svc\.(wmt_launcher|wmt_loader|stp_dump))\]:' \
		|| true
fi

heading "network interfaces without identifiers"
for net in /sys/class/net/*; do
	[[ -e "$net" ]] || continue
	device="$net/device"
	printf '%s|type=%s|operstate=%s|carrier=%s|driver=%s|modalias=%s|uevent=' \
		"${net##*/}" "$(first_line "$net/type")" \
		"$(first_line "$net/operstate")" "$(first_line "$net/carrier")" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(first_line "$device/modalias")"
	tr '\0' ';' < "$net/uevent" 2>/dev/null || true
	printf '\n'
done

heading "connectivity platform devices"
for device in /sys/bus/platform/devices/*; do
	[[ -e "$device" ]] || continue
	base="${device##*/}"
	case "$base" in
		*wifi*|*wlan*|*wmt*|*btif*|*gps*|*fm*|*conn*|*consys*)
			printf '%s|driver=%s|of_node=%s|modalias=%s\n' "$base" \
				"$(readlink -f "$device/driver" 2>/dev/null || true)" \
				"$(readlink -f "$device/of_node" 2>/dev/null || true)" \
				"$(first_line "$device/modalias")"
			;;
	esac
done

heading "device tree connectivity nodes"
dt_base=/sys/firmware/devicetree/base
while IFS= read -r node; do
	case "$node" in
		*/wifi@*|*/btif@*|*/btif_tx@*|*/btif_rx@*|*/consys@*|*/gps|*/gps_emi|*/connsys-wifi|*/consys-reserve-memory)
			printf '[%s]\n' "${node#"$dt_base"/}"
			for property in compatible status clock-names pinctrl-names; do
				property_text "$node/$property"
			done
			for property in reg interrupts clocks pinctrl-0 pinctrl-1 pinctrl-2 pinctrl-3 \
				vcn18-supply vcn28-supply vcn33_bt-supply vcn33_wifi-supply \
				size alignment alloc-ranges; do
				property_hex "$node/$property"
			done
			;;
	esac
done < <(find "$dt_base" -type d 2>/dev/null)

heading "connectivity IRQs"
grep -Ei 'wifi|wlan|wmt|btif|bluetooth|bgf|conn|gps|fm|stp|sdio' \
		/proc/interrupts 2>/dev/null || true

heading "vendor WMT status"
for path in /proc/driver/wmt_aee /proc/driver/wmt_dbg /proc/driver/stp_sdio_own \
		/proc/driver/stp_sdio_rxdbg /proc/driver/stp_sdio_txdbg; do
	[[ -r "$path" ]] || continue
	printf '[%s]\n' "$path"
	head -n 160 "$path" 2>/dev/null || true
done

heading "connectivity device nodes"
ls -l /dev/stp* /dev/wmt* /dev/gps* /dev/fm* /dev/ttyMT* 2>/dev/null || true

heading "installed connectivity firmware metadata"
for firmware in \
	/system/vendor/firmware/WMT_SOC.cfg \
	/system/vendor/firmware/ROMv3_patch_1_0_hdr.bin \
	/system/vendor/firmware/ROMv3_patch_1_1_hdr.bin \
	/system/vendor/firmware/WIFI_RAM_CODE_6797 \
	/system/vendor/firmware/fm_cust.cfg \
	/system/vendor/firmware/mt6631_fm_v1_coeff.bin \
	/system/vendor/firmware/mt6631_fm_v1_patch.bin; do
	[[ -r "$firmware" ]] || continue
	stat -c '%n|size=%s|mode=%a' "$firmware" 2>/dev/null || true
	sha256sum "$firmware" 2>/dev/null || true
done

heading "non-periodic connectivity log evidence"
dmesg 2>/dev/null | grep -Ei \
	'(WMT|HIF-SDIO|mt-wifi|wlan|BTIF|stp|gps|MT6631|ROMv3|WIFI_RAM|firmware|conninfra|CONSYS|FM)' | \
	grep -Ev '(therm_ctrl|Power/swap|temp_query|current_temp|STP SDIO|stp_sdio|pbuf\()' | \
	head -n 260 || true

heading "Linux config symbols when exposed"
if [[ -r /proc/config.gz ]] && command -v zgrep >/dev/null 2>&1; then
	zgrep -Ei '(^CONFIG_(WLAN|BT|GNSS|RFKILL|MEDIA|MTK|MEDIATEK|SERDEV|MMC).*=|^# CONFIG_(WLAN|BT|GNSS|RFKILL|MEDIA|MTK|MEDIATEK|SERDEV|MMC) is not set)' \
		/proc/config.gz 2>/dev/null || true
fi
