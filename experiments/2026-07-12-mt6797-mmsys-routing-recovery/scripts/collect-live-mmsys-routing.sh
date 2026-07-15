#!/usr/bin/env bash

# Read-only Gemini PDA MT6797 MMSYS routing evidence collector.

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

heading "running kernel"
uname -a

heading "MMSYS platform device"
device=/sys/bus/platform/devices/14000000.mmsys
if [[ -d "$device" ]]; then
	printf 'driver=%s\n' "$(readlink -f "$device/driver" 2>/dev/null || true)"
	[[ -r "$device/modalias" ]] && sed 's/^/modalias=/' "$device/modalias"
	[[ -r "$device/resource" ]] && sed 's/^/resource=/' "$device/resource"
fi

heading "MMSYS device-tree node"
node=/sys/firmware/devicetree/base/soc/mmsys@14000000
if [[ -d "$node" ]]; then
	for property in compatible clock-names status; do
		[[ -r "$node/$property" ]] || continue
		printf '%s=' "$property"
		tr '\0' ',' < "$node/$property" | sed 's/,$//'
		printf '\n'
	done
	for property in reg clocks mediatek,gce-client-reg; do
		[[ -r "$node/$property" ]] || continue
		printf '%s=' "$property"
		od -An -tx1 -v "$node/$property" | tr -d ' \n'
		printf '\n'
	done
fi

heading "display path history"
if (( READ_HISTORY )); then
	# Source-audited read-only callback. Keep the full input private: the
	# retained ring buffer may contain kernel and DMA addresses. Emit only the
	# fixed route/mutex lines needed to reproduce this contract.
	if [[ -r /sys/kernel/debug/mtkfb ]]; then
		grep -E '(^|[^[:alnum:]_])(OVL[01]_MOUT|DITHER_MOUT|UFOE_MOUT|DSC_MOUT|COLOR0_SEL|WDMA[01]_SEL|UFOE_SEL|DSC_SEL|DSI[01]_SEL|DPI0_SEL|OVL0_SEL|PATH0_SOUT|RDMA[01]_SOUT|OVL[01]_SOUT|MUTEX0:|ovl0 to dsi0 is connected)' \
			/sys/kernel/debug/mtkfb 2>/dev/null || true
	else
		printf 'unavailable\n'
	fi
else
	printf 'skipped; pass --read-history after auditing the running driver\n'
fi

heading "MMSYS kernel messages"
dmesg 2>/dev/null | grep -Ei 'mmsys|dispsys|ddp path' || true
