#!/usr/bin/env bash

# Read-only Gemini UART and console inventory. It does not open a tty, change
# termios, write console data, bind/unbind a driver, or inspect user sessions.

set -u
export LC_ALL=C

section() { printf '\n[%s]\n' "$1"; }

read_text() {
	[ -r "$1" ] || return 0
	tr '\000' ' ' < "$1"
}

dump_property() {
	local file=$1
	local label=$2
	[ -r "$file" ] || return 0
	printf '  %s=' "$label"
	case "$label" in
		name|compatible|clock-names|pinctrl-names|status)
			read_text "$file"
			printf '\n'
			;;
		*)
			od -An -tx1 -v "$file" | tr -d ' \n'
			printf '\n'
			;;
	esac
}

section identity
uname -a 2>/dev/null || true

section consoles
cat /proc/consoles 2>/dev/null || true

section command-line
if sudo -n true 2>/dev/null; then
	# Keep only console-related tokens; omit the complete boot argument string.
	sudo -n cat /proc/cmdline 2>/dev/null | tr ' ' '\n' |
		grep -E '^(console|earlycon|earlyprintk|tty)' || true
else
	echo 'cmdline=owner-authorized-sudo-required'
fi

section tty-class
for device in /sys/class/tty/ttyMT* /sys/class/tty/ttyS*; do
	[ -e "$device" ] || continue
	name=${device##*/}
	printf 'tty=%s' "$name"
	[ -r "$device/dev" ] && printf ' dev=%s' "$(cat "$device/dev")"
	[ -L "$device/device" ] && printf ' device=%s' "$(readlink -f "$device/device")"
	[ -L "$device/device/driver" ] &&
		printf ' driver=%s' "$(basename "$(readlink -f "$device/device/driver")")"
	printf '\n'
done

section uart-platform
for device in \
	/sys/bus/platform/devices/11002000.apuart0 \
	/sys/bus/platform/devices/11003000.apuart1 \
	/sys/bus/platform/devices/11004000.apuart2 \
	/sys/bus/platform/devices/11005000.apuart3; do
	[ -e "$device" ] || continue
	printf 'device=%s' "${device##*/}"
	[ -L "$device/driver" ] &&
		printf ' driver=%s' "$(basename "$(readlink -f "$device/driver")")"
	printf '\n'
	dump_property "$device/of_node/compatible" compatible
	dump_property "$device/of_node/reg" reg
	dump_property "$device/of_node/interrupts" interrupts
	dump_property "$device/of_node/clocks" clocks
	dump_property "$device/of_node/clock-names" clock-names
	dump_property "$device/of_node/status" status
	dump_property "$device/of_node/pinctrl-names" pinctrl-names
done

section live-device-tree
for node in \
	/sys/firmware/devicetree/base/soc/apuart0@11002000 \
	/sys/firmware/devicetree/base/soc/apuart1@11003000 \
	/sys/firmware/devicetree/base/soc/apuart2@11004000 \
	/sys/firmware/devicetree/base/soc/apuart3@11005000; do
	[ -d "$node" ] || continue
	printf 'node=%s\n' "${node##*/}"
	dump_property "$node/name" name
	dump_property "$node/compatible" compatible
	dump_property "$node/reg" reg
	dump_property "$node/interrupts" interrupts
	dump_property "$node/clocks" clocks
	dump_property "$node/clock-names" clock-names
	dump_property "$node/status" status
	dump_property "$node/pinctrl-names" pinctrl-names
done

section chosen-and-aliases
for file in \
	/sys/firmware/devicetree/base/chosen/stdout-path \
	/sys/firmware/devicetree/base/aliases/serial0 \
	/sys/firmware/devicetree/base/aliases/serial1; do
	[ -e "$file" ] || continue
	printf '%s=' "${file##*/}"
	if [ -L "$file" ]; then
		readlink "$file"
	else
		read_text "$file"
		printf '\n'
	fi
done

section uart-interrupts
grep -Ei 'uart|serial|ttyMT|ttyS|mtk-uart' /proc/interrupts 2>/dev/null || true

section uart-devices
for path in /dev/ttyMT* /dev/ttyS*; do
	[ -e "$path" ] || continue
	ls -l "$path" 2>/dev/null || true
done

section uart-kernel-messages
# The vendor dmesg ring can be large and may contain user/network data. Keep
# this collector bounded; use an owner-authorized, separately filtered dmesg
# capture only when a later experiment needs it.
echo 'dmesg=omitted_from_bounded_collector'
