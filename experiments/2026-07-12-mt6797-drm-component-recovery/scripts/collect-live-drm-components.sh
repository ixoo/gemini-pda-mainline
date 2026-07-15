#!/usr/bin/env bash

# Read-only Gemini PDA MT6797 DRM component evidence collector.

set -u
export LC_ALL=C

READ_HISTORY=0
case "${1:-}" in
	"") ;;
	--read-history) READ_HISTORY=1 ;;
	*)
		printf 'usage: %s [--read-history]\n' "${0##*/}" >&2
		exit 2
		;;
esac

heading() {
	printf '\n===== %s =====\n' "$1"
}

read_clock() {
	local directory=$1 field value

	if [[ ! -d "$directory" ]]; then
		printf '%s|absent\n' "${directory##*/}"
		return
	fi

	printf '%s' "${directory##*/}"
	for field in clk_rate clk_enable_count clk_prepare_count; do
		[[ -r "$directory/$field" ]] || continue
		# debugfs clock attributes reject seeks; cat reads each attribute once.
		value="$(cat "$directory/$field" 2>/dev/null || true)"
		printf '|%s=%s' "$field" "$value"
	done
	printf '\n'
}

heading "running kernel"
uname -a

heading "display component interrupts"
grep -Ei 'ovl|rdma|wdma|aal|gamma|dither|ccorr|color|ufoe|dsi|dpi' \
	/proc/interrupts 2>/dev/null || true

heading "active display clocks"
for clock in \
	mm_disp_ovl0 \
	mm_disp_ovl0_2l \
	mm_disp_ovl1_2l \
	mm_disp_rdma0 \
	mm_disp_color \
	mm_disp_ccorr \
	mm_disp_aal \
	mm_disp_gamma \
	mm_disp_od \
	mm_disp_dither \
	mm_disp_ufoe \
	'mm_dsi0_mm clock' \
	mm_dsi0_interface_clock; do
	read_clock "/sys/kernel/debug/clk/$clock"
done

heading "display component platform resources"
for address in \
	1400b000 1400d000 1400e000 1400f000 14013000 14014000 \
	14015000 14016000 14017000 14018000 14019000 1401c000; do
	for device in /sys/bus/platform/devices/"$address".*; do
		[[ -d "$device" ]] || continue
		printf '%s|driver=%s\n' "${device##*/}" \
			"$(readlink -f "$device/driver" 2>/dev/null || true)"
		[[ -r "$device/resource" ]] && sed 's/^/resource=/' "$device/resource"
	done
done

heading "source-audited retained display history"
if (( READ_HISTORY )); then
	if [[ -r /sys/kernel/debug/mtkfb ]]; then
		# The full ring buffer may include addresses. Retain it privately and
		# emit only the fixed component analysis and register lines.
		grep -Ei '== DISP (ovl0|ovl0_2l|ovl1_2l|COLOR0|CCORR|AAL|GAMMA|OD|DITHER|RDMA0|UFOE) (ANALYSIS|REGS) ==|DSI0 (Start|Lane Num)|MIPITX Clock|\(0x[0-9a-fA-F]+\)(OVL|COLOR|CCORR|AAL|GAMMA|OD|DITHER|RDMA|UFOE)_' \
			/sys/kernel/debug/mtkfb 2>/dev/null || true
	else
		printf 'unavailable\n'
	fi
else
	printf 'skipped; pass --read-history after auditing the running driver\n'
fi

heading "display kernel messages"
dmesg 2>/dev/null | grep -Ei 'ovl|rdma|aal|gamma|dither|ccorr|ufoe|dsi' || true
