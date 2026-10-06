# Phase B offline implementation checkpoint

Status: incomplete, compile-only, not built yet. Profile
`mt6797-a53-wifi-phase-b-compile` selects eight original format-patches in
canonical order after the Phase A baseline. It has a distinct kernel release.
The proven Phase A profile is unchanged. No candidate or device test is admitted.

## Implemented preparation

- Event decoders: exact framing, asynchronous TX PID/WLAN matching, channel
  identity/finite interval, and pending state-3 command/STA/BSS/AP matching.
  TXdone count/rate are zero unless the firmware advanced-information flag is
  set; parsing alone does not imply an ACK.
- TX descriptors: native authentication, association-request and deauthentication,
  MCU queue 1, 24-byte headers, explicit sequence/PID, finite attempt count
  and lifetime, fixed OFDM 6 Mbps. Zero lifetime means unlimited and is refused.
  Finite lifetimes use 32 TU units with minimum one and saturation at 255;
  requested milliseconds are not exact hardware deadlines.
- Directed RX: complete firmware group/padding bounds, allowed subtype and
  channel/address/BSSID checks, Open System transaction 2, fixed body and
  association IE bounds. Firmware fragmentation metadata is rejected. RCPI
  converts to whole dBm, rounding odd RCPI down. Firmware headers/groups are
  excluded from the frame.
- Station/channel payloads: legacy 5 GHz state 1/state 3, activation response
  requested for state 3, targeted single-STA removal and channel request/abort.
  AMPDU command option 1 explicitly disables aggregation (zero is AUTO).
  HT/VHT, QoS and keepalive fields remain zero. Fixed slot values are project
  reservations, never allocation acknowledgements.
- Shared HIF submission: descriptor/frame pages and fixed join commands use
  the existing normal TC4 credit owner, scratch and guarded PIO. Command
  sequences remain single-use. PIO success does not refund pages or prove
  firmware execution; ambiguous errors poison the session without refund.
- MAC draft: bounded atomic TX queue, one process-context pump/inflight skb,
  separate page debt and TXdone, dual-port finite RX, and serialized notifications
  outside the MAC mutex. Pending channel/activation replies are consumed once;
  grant expiry is monotonic. Stop/remove retire pending host state before disposal.
  Downward station transitions cannot fail. Queue admission remains closed;
  upward station and managed-TX callbacks are not implemented.

Selected patches are listed in
[`series-a53-wifi-phase-b-compile`](../../patches/series-a53-wifi-phase-b-compile).
Their public wire source is gen3 at revision
`c5b0be85017ad0c599725e8273842efdbecdd88a`; source links are in the experiment
[design](README.md). Vendor headers are not added to this repository.

## Validation completed

`python3 tests/run-events-test.py` extracts the actual selected headers and
runs focused C fixtures with warnings as errors, ASan and UBSan. Event, TX,
RX and payload fixtures passed, including every RX group combination, both
padding modes, truncation, identity mismatch and malformed IE/body cases.

TX descriptors additionally matched the public vendor typedef/setter macros
for 60 combinations: frame lengths 30/100/101/2304, lifetimes
1/32/33/500/10000 ms and encoded attempt counts 1/3/30. Five independent
public-typedef vectors matched station state 1/state 3, channel request/abort
and single-station removal. These compare layout/values, not firmware
acceptance, legal channel operation, AP capabilities or slot ownership.

`python3 tests/run-submit-test.py KERNEL_TREE` checks management credit
preparation against actual prepared normal/HIF headers. It passed page debit,
zero bus padding, untouched command sequence history, separate CPU/FFA credit
reconciliation, prior-debt refusal and unchanged outputs on validation errors.

`python3 tests/run-hif-test.py KERNEL_TREE` exercises actual patched `hif.c`
through its existing host-test seam. It passed successful ordered submission,
every scalar-write fault, expired deadlines and sequence-reuse refusal for
management TX and all three typed command entry points. Credits remain
retired after ambiguous failure. Corrupt limits, free-page counts and missing
sequence ledgers retire the command owner before any bus write. These Linux fixtures use bounded non-PIE
ASan/UBSan: the initial PIE sanitizer executable repeated a signal failure
and was stopped; the unchanged non-PIE fixture passed. That host limitation
is not evidence about the device.

Patch whitespace checks passed. Checkpatch found no remaining errors after
indentation correction; style warnings/checks remain, and its Python SPDX
checker was unavailable on the author host. Added headers and fixtures carry
GPL-2.0-only identifiers. This is not an upstream submission.
The new MAC draft has not been compiled,
concurrency tested or run on hardware. Helper/HIF fixtures do not validate it.
A selected kernel build is the next checkpoint.

## Remaining work

Implement scan-to-join ownership handoff, supported-rate/AID normalization,
station and managed-TX callbacks, current-state RX/TX admission and healthy
teardown. Follow the [BSS lifetime correction](BSS_LIFETIME_REVIEW.md): retain
one AIS owner through scan/join; no quiet window proves a drain. Preserve
single-use peer/PID/channel tokens and exactly-once skb disposal after every
partial failure. No cleanup command may follow terminal firmware poison.

Then validate a concrete candidate and bounded authentication/association
protocol before the device test. Successful join is a prerequisite for the
subsequent PIO data TX/RX admission. This checkpoint is not usable Wi-Fi.
