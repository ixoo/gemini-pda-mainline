#!/usr/bin/env bash

# Read-only Gemini PDA MT6797 CMDQ/GCE evidence collector.

set -u
export LC_ALL=C

READ_PROC=0
case "${1:-}" in
	"") ;;
	--read-proc) READ_PROC=1 ;;
	*)
		printf 'usage: %s [--read-proc]\n' "${0##*/}" >&2
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

heading "GCE interrupts"
grep -Ei 'cmdq|gce' /proc/interrupts 2>/dev/null || true

heading "GCE interrupt activity over two seconds"
before="$(grep -E '^[[:space:]]*[0-9]+:.*(cmdq|gce)' /proc/interrupts 2>/dev/null || true)"
sleep 2
after="$(grep -E '^[[:space:]]*[0-9]+:.*(cmdq|gce)' /proc/interrupts 2>/dev/null || true)"
printf 'before=%s\nafter=%s\n' "$before" "$after"

heading "GCE platform device"
for path in /sys/bus/platform/devices/*gce* /sys/bus/platform/drivers/*cmdq* \
	/sys/bus/platform/drivers/*gce*; do
	[[ -e "$path" ]] || continue
	printf '%s|target=%s\n' "$path" "$(readlink -f "$path" 2>/dev/null || true)"
done

device=/sys/bus/platform/devices/10212000.gce
if [[ -d "$device" ]]; then
	printf 'driver=%s\n' "$(readlink -f "$device/driver" 2>/dev/null || true)"
	printf 'modalias=%s\n' "$(read_one "$device/modalias")"
	[[ -r "$device/resource" ]] && sed 's/^/resource=/' "$device/resource"
	for field in runtime_status runtime_active_time runtime_suspended_time control; do
		value="$(read_one "$device/power/$field")"
		[[ -n "$value" ]] && printf 'power.%s=%s\n' "$field" "$value"
	done
fi

heading "GCE clock"
for directory in /sys/kernel/debug/clk/*gce*; do
	[[ -d "$directory" ]] || continue
	printf '%s' "${directory##*/}"
	for field in clk_rate clk_accuracy clk_phase clk_enable_count \
		clk_prepare_count clk_flags; do
		value="$(read_one "$directory/$field")"
		[[ -n "$value" ]] && printf '|%s=%s' "$field" "$value"
	done
	printf '\n'
done

heading "GCE device-tree node"
node=/sys/firmware/devicetree/base/soc/gce@10212000
if [[ -d "$node" ]]; then
	for property in compatible clock-names status; do
		[[ -r "$node/$property" ]] || continue
		printf '%s=' "$property"
		tr '\0' ',' < "$node/$property" | sed 's/,$//'
		printf '\n'
	done
	for property in reg interrupts clocks disp_mutex_reg; do
		[[ -r "$node/$property" ]] || continue
		printf '%s=' "$property"
		od -An -tx1 -v "$node/$property" | tr -d ' \n'
		printf '\n'
	done
	printf 'properties=' 
	find "$node" -maxdepth 1 -type f -exec basename {} \; 2>/dev/null | sort | tr '\n' ','
	printf '\n'
	printf '%s\n' 'numeric-properties:'
	for path in "$node"/*; do
		[[ -f "$path" ]] || continue
		property="${path##*/}"
		case "$property" in
			compatible|clock-names|name|status) continue ;;
		esac
		size="$(wc -c < "$path" 2>/dev/null || printf 0)"
		[[ "$size" -le 128 ]] || continue
		printf '%s=' "$property"
		od -An -tx1 -v "$path" | tr -d ' \n'
		printf '\n'
	done
else
	printf 'not-found=%s\n' "$node"
fi

heading "CMDQ debug interfaces"
find /sys/kernel/debug /proc -maxdepth 3 \
	\( -iname '*cmdq*' -o -iname '*gce*' \) -print 2>/dev/null | sort

heading "source-audited CMDQ proc snapshots"
if [[ "$READ_PROC" -eq 0 ]]; then
	printf 'not-read=rerun as root with --read-proc after reviewing privacy and MMIO notes\n'
else
	for path in /proc/mtk_cmdq_debug/record /proc/mtk_cmdq_debug/status; do
		printf '[%s]\n' "$path"
		[[ -r "$path" ]] && cat "$path"
	done
fi

heading "GCE kernel messages"
dmesg 2>/dev/null | grep -Ei 'cmdq|gce' || true
