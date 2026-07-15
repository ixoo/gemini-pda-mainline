#!/usr/bin/env bash

# Read-only Gemini ASoC/AFE evidence collector. Run on the device through SSH;
# it never opens PCM streams, changes mixer controls, or writes any sysfs,
# PMIC, codec, or audio registers.

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

heading "ALSA card and endpoint inventory"
cat /proc/asound/cards 2>/dev/null || true
printf '\n[devices]\n'
cat /proc/asound/devices 2>/dev/null || true
for info in /proc/asound/card*/pcm*/info; do
	[[ -r "$info" ]] || continue
	card="$(awk -F': ' '/^card:/{print $2}' "$info")"
	device="$(awk -F': ' '/^device:/{print $2}' "$info")"
	stream="$(awk -F': ' '/^stream:/{print $2}' "$info")"
	id="$(awk -F': ' '/^id:/{sub(/^id: /, ""); print}' "$info")"
	printf 'pcm=card%s_device%s|stream=%s|id=%s\n' \
		"$card" "$device" "$stream" "$id"
done

heading "audio platform devices"
for device in /sys/bus/platform/devices/*audio* \
	/sys/bus/platform/devices/*afe* /sys/bus/platform/devices/soc-audio; do
	[[ -e "$device" ]] || continue
	printf '[%s]|modalias=%s|driver=%s|of_node=%s\n' \
		"${device##*/}" "$(first_line "$device/modalias")" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(readlink -f "$device/of_node" 2>/dev/null || true)"
	if [[ -r "$device/uevent" ]]; then
		printf '%s/uevent=' "${device##*/}"
		tr '\0' ';' < "$device/uevent"
		printf '\n'
	fi
done

heading "device-tree AFE, codec, and sound nodes"
dt_base=/sys/firmware/devicetree/base
while IFS= read -r node; do
	printf '[%s]\n' "${node#"$dt_base"/}"
	for property in compatible status name clock-names interrupt-names; do
		property_text "$node/$property"
	done
	for property in reg interrupts interrupt-parent clocks power-domains \
		mediatek,platform mediatek,audio-codec; do
		property_hex "$node/$property"
	done
	done < <(find "$dt_base" -type d 2>/dev/null | grep -Ei \
	'/((audio|afe|sound|codec)(@|$)|mt_soc_.*pcm|mt_soc_codec|mt6351$)')

heading "audio interrupts"
grep -Ei 'audio|afe|asys|snd|mt_soc|i2s|pcm' /proc/interrupts 2>/dev/null || true

heading "focused audio kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(audio|afe|asoc|snd|mt6351|codec|pcm|i2s|mt-snd-card)' || true
