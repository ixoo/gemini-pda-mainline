# One checked WMT negotiation lifetime

Status: completed negotiation lifetime. [Runtime 1](results/runtime-1.json)
records successful default/set/full wire exchanges, preservation, regression
and changed-boot Gemian recovery. [Classifier review](results/classifier-review.json)
records an offline false-positive correction; the original results remain unchanged.

This historical packet selected [candidate](results/candidate.json), kernel inputs
`c1348713`, release `7.1.3-gemini-a53-wmt-negotiate`, and padded boot2 SHA-256
`ed4503ebf70a41a024bda42f4cb4b1244013bec6dcbd8bea1df4a403dc4ef9f2`.
The lifetime is retired and must not be repeated.

## Hypothesis and unique observation

The successful mandatory default exchange can be followed by the source-matched
mandatory set-options event, full-STP software reseed, switch delay, and one full
options query. Success requires the exact private wire events, valid full header
checksum and payload CRC, peer credit, transmitted host ACK and final sequence
state. This establishes the mode boundary needed before common initialization.
It does not establish ROM patch applicability, calibration, reception,
association or traffic. No ROM/DLM/MCU-clock/PA/calibration/WLAN/scan action is
admitted by this packet.

A default, set or full failure retires this powered lifetime at its first error.
Preserve the phase, counters and bounded raw wire bytes, then use the reviewed
recovery path. Do not issue another trigger, wake, reset, FIFO repair, mode
change, alternative bit selection or release of clocks/power to compensate.
Only a fully checked result permits preparing subsequent common initialization.

## Prerequisites and inherited preparation

Root is the sole device custodian. Require a verified deployment receipt, fresh
mainline boot distinct from the Gemian predecessor, exact release and direct
USB route. The candidate disables WLAN and selects only the distinct root
`/sys/bus/platform/devices/10001340.consys/wmt_negotiate` trigger. No exchange
runs at probe. The original default-query lifetime is closed and is not repeated.

The candidate inherits the proven UART0 console, shared infracfg AP-DMA ID 46,
BTIF/sysirq route and region-19 reservation. The [previous clock admission](../2026-10-03-mt6797-wmt-default-query/results/clock-admission.json)
and [initial transport effects](../2026-10-03-mt6797-wmt-default-query/RUNTIME_PROTOCOL.md#exact-effects-and-budgets)
apply to the unchanged prerequisite and initial setup only. The same selected
UART driver, console configuration and clock relationships were checked in the
candidate constructor; this is source reasoning, not a new hardware observation.

Before preparation and immediately before negotiation, require the serial
console argument, enabled ttyS0 console, bound MediaTek UART0 driver, runtime
status active and positive CCF AP-DMA prepare/enable counters. One read-only
debugfs mount at its existing mountpoint is admitted during identification if
needed. Read only those two RAM counters. No console close/unbind, runtime or
system suspend, PM policy change, clock-summary walk or concurrent diagnostic
is allowed through evidence sealing. Missing observations refuse the trigger.

Preserve two equal complete private 512-KiB region-19 preimages, perform the
existing sole preparation and verify its 351232-byte zeroed prefix, untouched
suffix, exact remap/policy and complete records while CONSYS is held off. The
negotiation trigger rechecks the inherited domain/rail/reset/resource guards,
consumes its sole attempt and uses the existing fresh CONSYS power/reset release.
All HIF/copy/WLAN continuation arguments remain false. Temporary sysfs read-write
access has a restoration trap installed before remount and verified read-only
restoration afterward.

## Additional effects and finite budgets

One shared CONSYS lock spans all phases. The default query performs the inherited
channel-local AP-DMA observations and empty-FIFO/controller setup once. Its
DMA_EN read has the previously admitted possible timeout-acknowledgment effect.
No packet-DMA descriptors, starts, global DMA status or unrelated channels are
accessed. Retain clocks and power on both success and failure.

| Phase | Selected effects and limits |
| --- | --- |
| Default | One 11-byte mandatory query; up to 17 RBR reads, 32 IRQ entries; success requires 16 received bytes and 1–31 entries; matched-frame trailing queued data refuses success |
| Set | Separate persistent context, no clock acquisition/reset/FIFO clear; empty RX/TX check, one 15-byte mandatory request, exact 12-byte event; at most 32 services including initial kick, 13 RBR reads, 15 THR writes and 8 RX bytes per service |
| Switch | Only after checked set event: initialize full-STP TX/RX to zero and peer/local ACK to seven; one `usleep_range(10000,11000)`; no BTIF mode register write |
| Full | One 11-byte full query plus one 4-byte host ACK; at most 512 services, 1043 RBR reads, 8 frames and 8 RX bytes per service; exact options event and peer credit both required |
| IRQ ownership | Three sequential exclusive initially disabled IRQ registrations at most; each has one bounded exchange, source mask, CPU IRQ retirement, synchronization and free; no concurrent registration or retry |
| Deadlines | Each exchange is at most 500 ms clipped by one 1600-ms transport deadline; checked before later phase/effect advancement; no claim of a hard real-time bound on framework calls or scheduling |
| Evidence | Default TX/RX at most 11/17 bytes, set TX/RX 15/13, full command/ACK TX 11/4 and full RX 1043, logged from retained buffers with no extra hardware reads |

Set and full service use selected-source normal-bank LSR TX-empty/TX-room and
RX status, data-port byte access and local IER bits RX 0/TX 1. The [reviewed IO](../2026-10-03-mt6797-wifi-audit/FULL_STP_IO.md)
and [caller](../2026-10-03-mt6797-wifi-audit/NEGOTIATION_OWNER.md) specify ordering,
source/manual contradictions, IRQ retirement and finite failure paths. The
full leaf's generic 1015-THR bound is not a selected transfer: this caller
supplies only the fixed query and ACK (15 bytes). No patch payload is supplied.

## Classification, preservation and recovery

`capture-private.py` makes exactly one host attempt after preparation. A host
30-second timeout is not permission to retry. The private capture records all
stdout/stderr/process status and raw log before classification. Success requires
one terminal result zero, phase five, clocks held, bounded counts and final
TX/RX next sequence one, peer/local ACK zero. `classify-negotiation.py` also
requires complete contiguous bounded hex dumps, exact mandatory request/events,
full query checksum/CRC, one matching full event, valid ACK ordering and the
actual four host ACK bytes. Counters alone cannot establish success. Missing,
duplicate, malformed, truncated or extra evidence refuses success.

After every capture outcome, run `passive-host.py` for complete zero-through-seal
kernel-log preservation, the established bounded A53 regression and reviewed
native mainline-to-Gemian recovery. Require live boot identity and recovery-tool
identity before that request, preserve unique evidence first and confirm changed
known-good Gemian boot afterward. A missing prerequisite blocks recovery instead
of authorizing an alternate path. Keep raw wire logs, firmware, calibration and
region captures private; publish only sanitized phase/count/classification,
checksums, regression and recovery receipts.

Installation resolves logical boot2 from fresh live Gemian GPT, applies the
reviewed device guard twice, validates inactivity/root/mount/size/writability and
stable power, accepts only the pinned predecessor or already matching candidate,
and requires full-partition readback. Rely on the project backup. After verified
write, cleanly shut down; physical boot2 selection is an owner action. No automatic
reboot or different partition is admitted.
