#!/usr/bin/env bash

# Read-only Gemini PDA MT6797 display-mutex evidence collector.

set -u
export LC_ALL=C

READ_DRIVER_DUMP=0
case "${1:-}" in
	"") ;;
	--read-driver-dump) READ_DRIVER_DUMP=1 ;;
	*)
		printf 'usage: %s [--read-driver-dump]\n' "${0##*/}" >&2
		exit 2
		;;
esac

heading() {
	printf '\n===== %s =====\n' "$1"
}

read_one() {
	[[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

heading "running kernel"
uname -a

heading "display mutex interrupts"
grep -Ei 'mutex' /proc/interrupts 2>/dev/null || true

heading "display mutex interrupt activity over two seconds"
before="$(grep -E '^[[:space:]]*[0-9]+:.*mutex' /proc/interrupts 2>/dev/null || true)"
sleep 2
after="$(grep -E '^[[:space:]]*[0-9]+:.*mutex' /proc/interrupts 2>/dev/null || true)"
printf 'before=%s\nafter=%s\n' "$before" "$after"

heading "display mutex platform device"
for path in /sys/bus/platform/devices/*mutex* \
	/sys/bus/platform/drivers/*mutex*; do
	[[ -e "$path" ]] || continue
	printf '%s|target=%s\n' "$path" "$(readlink -f "$path" 2>/dev/null || true)"
done

device=/sys/bus/platform/devices/1401f000.mm_mutex
if [[ -d "$device" ]]; then
	printf 'driver=%s\n' "$(readlink -f "$device/driver" 2>/dev/null || true)"
	printf 'modalias=%s\n' "$(read_one "$device/modalias")"
	[[ -r "$device/resource" ]] && sed 's/^/resource=/' "$device/resource"
	for field in runtime_status runtime_active_time runtime_suspended_time control; do
		value="$(read_one "$device/power/$field")"
		[[ -n "$value" ]] && printf 'power.%s=%s\n' "$field" "$value"
	done
fi

heading "display mutex clock search"
found=0
for directory in /sys/kernel/debug/clk/*mutex*; do
	[[ -d "$directory" ]] || continue
	found=1
	printf '%s' "${directory##*/}"
	for field in clk_rate clk_accuracy clk_phase clk_enable_count \
		clk_prepare_count clk_flags; do
		value="$(read_one "$directory/$field")"
		[[ -n "$value" ]] && printf '|%s=%s' "$field" "$value"
	done
	printf '\n'
done
[[ "$found" -eq 1 ]] || printf 'no-matching-clock\n'

heading "display mutex device-tree node"
node=/sys/firmware/devicetree/base/soc/mm_mutex@1401f000
if [[ -d "$node" ]]; then
	for property in compatible clock-names status; do
		[[ -r "$node/$property" ]] || continue
		printf '%s=' "$property"
		tr '\0' ',' < "$node/$property" | sed 's/,$//'
		printf '\n'
	done
	for property in reg interrupts clocks; do
		[[ -r "$node/$property" ]] || continue
		printf '%s=' "$property"
		od -An -tx1 -v "$node/$property" | tr -d ' \n'
		printf '\n'
	done
	printf 'properties='
	find "$node" -maxdepth 1 -type f -exec basename {} \; 2>/dev/null |
		sort | tr '\n' ','
	printf '\n'
else
	printf 'not-found=%s\n' "$node"
fi

heading "source-audited vendor display dump"
if [[ "$READ_DRIVER_DUMP" -eq 0 ]]; then
	printf 'not-read=rerun as root with --read-driver-dump after reviewing privacy notes\n'
else
	dump=/sys/kernel/debug/disp/dump
	if [[ ! -r "$dump" ]]; then
		printf 'error=unreadable:%s\n' "$dump"
		exit 1
	fi
	cat "$dump"
fi

heading "display mutex kernel messages"
dmesg 2>/dev/null | grep -Ei 'mutex|ddp' || true
