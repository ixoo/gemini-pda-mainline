# MT6797 passive scan with explicit channel dwell

Status: source-reviewed timing successor; build, candidate and runtime pending.
The installed [broadcast parent](../2026-10-02-mt6797-passive-scan-broadcast/README.md)
remains unconsumed and is superseded for the next scan by this timing candidate.

## Listening-time evidence

The [retained analysis](results/dwell-analysis.json) joins V2 payload offset 154
to the passive decoder's unchanged halfword, nominal default 100, selected dwell
state and timer argument. The timer splits at 60000 and its local conversion
uses 32768, 999 and divisor 1000, matching the millisecond timer API in the
pinned gen3 source. The arithmetic helper and physical clock remain unmeasured;
the host V2 TU comment alone is not the selected firmware path's unit proof.

The known-good connection's retained cache reported 5200 MHz and a 100 TU
(102.4 ms) beacon interval. This stale cache is context, not a new observation.
A nominal 100 ms window is shorter than one cached beacon interval. A 500 ms
request covers about 4.88 such intervals; unknown beacon loss and actual RF
scheduling still limit negative results. Firmware branches can shorten dwell,
including an unresolved internal-state clamp to 18. No register write or guessed
state repair is derived from that branch.

## Candidate change and finite protocol

Patch 0079 requests fixed 500 ms dwell and accepts exactly one currently
permitted channel per scan. The named profile appends it to the broadcast
parent in canonical order. Standard channel policy, private record, firmware,
broadcast setup, PIO owner and receive parser remain inherited. The test selects
channel 40 with `iw dev wlan0 scan freq 5200 passive`, with no SSID or probe TX.
A multi-channel request is refused before the lifetime or first write.

The one-boot observation is whether the new request reaches matching completion,
how long submission-to-completion takes, and whether a valid native beacon and
standard BSS appear on that channel. The candidate logs requested milliseconds,
channel count and host elapsed microseconds before cleanup. Host elapsed includes
setup, scheduling and delivery; even a long result is not measured RF dwell.
This scan is also the admitted bounded timing observation for the parent's
listening-time requirement; it does not assume all shortening branches are off.

Keep one scan, one filter submission, one BSS activation, the existing five-second
host deadline, 256 polls, sixteen RX packets per tick and 4096 packets overall.
The half-second one-channel request leaves time for grant/setup and delivery
within that unchanged deadline. Existing maximum-one cancellation/deactivation,
terminal no-retry and reviewed recovery remain mandatory. No active probes,
association, key operation, packet DMA, IRQ or direct radio/register write is
added. Build and exact boot2 identity checks must precede runtime.

A valid beacon/BSS establishes management reception for the exact candidate and
permits association design. A completed empty scan with elapsed time shorter
than 500 ms contradicts the intended nominal window and prioritizes firmware
timing/shortening diagnosis. An empty scan lasting at least 500 ms still leaves
actual RF dwell and tuning unverified; it cannot establish a filter cause or
justify repeating an identical image. Transport, ownership or protocol failure
stops I/O and retires the lifetime. Preserve evidence before reviewed recovery
and require changed-boot Gemian plus the inherited A53/provider regressions.

## Focused validation

The wire test checks the source-defined 500 ms halfword at offset 154, one-channel
layout, unchanged reserved/probe/timeout/IE bytes and refusal of multi-channel or
invalid requests without output mutation. Compile it with the selected patched
`scan-wire.h` and the existing
[compatibility header](../2026-10-01-mt6797-normal-sets/tests/test-compat.h), using
C11, Werror, ASan and UBSan. Kernel builds use
`./scripts/build-kernel --backend buildbox` from clean committed/pushed inputs.
No build or host fixture establishes Wi-Fi support.
