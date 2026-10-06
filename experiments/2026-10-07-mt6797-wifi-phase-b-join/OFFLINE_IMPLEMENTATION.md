# Phase B offline implementation checkpoint

Status: incomplete, compile-only. Compile 2 covers patches through 0132. Profile
`mt6797-a53-wifi-phase-b-compile` selects thirteen original format-patches in
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
  upward station and managed-TX callbacks are not implemented. Event polling
  now has a separate gate from TX admission, so pending control replies can
  later be consumed while frame dequeue remains closed.
- Default-off join option and copied BSS/channel snapshots: no stack BSS,
  STA or channel-context pointer is retained. The compile profile enables
  snapshot preparation, with no new firmware submission or open TX gate.
- Legacy rate normalization: translate the advertised eight 5 GHz OFDM slots
  to gen3 software bits 6..13, validating basic-rate membership and fixed
  6 Mbps support before modifying outputs.

Selected patches are listed in
[`series-a53-wifi-phase-b-compile`](../../patches/series-a53-wifi-phase-b-compile).
Their public wire source is gen3 at revision
`c5b0be85017ad0c599725e8273842efdbecdd88a`; source links are in the experiment
[design](README.md). Vendor headers are not added to this repository.

## Validation completed

The initial eight-patch [compile 1](COMPILE_1.md) passed on Buildbox-1.
Its receipt excludes follow-up patches 0130 through 0132, which passed
[compile 2](COMPILE_2.md) with the snapshot option enabled.

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
management TX and all four typed command entry points, including the fixed
directed/broadcast receive filter. Credits remain
retired after ambiguous failure. Corrupt limits, free-page counts and missing
sequence ledgers retire the command owner before any bus write. These Linux fixtures use bounded non-PIE
ASan/UBSan: the initial PIE sanitizer executable repeated a signal failure
and was stopped; the unchanged non-PIE fixture passed. That host limitation
is not evidence about the device.

Patch whitespace checks passed. Checkpatch found no remaining errors after
indentation correction; style warnings/checks remain, and its Python SPDX
checker was unavailable on the author host. Added headers and fixtures carry
GPL-2.0-only identifiers. This is not an upstream submission.
MAC preparation through patch 0132 compiled, but callback concurrency and hardware
behavior remain untested. Helper/HIF fixtures do not validate those MAC paths.

`python3 tests/run-rates-test.py KERNEL_TREE` passed all 65,536 eight-bit
supported/basic-rate combinations, every unknown high bit and null-output
rejection against the prepared header with non-PIE ASan/UBSan. Snapshot and
pending-only event-pump preparation is covered by compile 2; its runtime
behavior remains untested.

## Lifetime and directed-filter preparation awaiting build

The compile profile now selects corrected patch 0133 and filter patch 0134.
Their selected kernel build is still pending; no candidate is admitted.
Patch 0133 retains the active AIS BSS only after an exact successful channel-40 scan
with complete valid normal-credit/history/query accounting. The event pump
starts with TX closed and a ten-second setup deadline. A healthy unused
handoff may request deactivation once on close or expiry, after a fresh
100 ms owner/accounting guard and the existing at-most-one-second submission
budget. No peer, grant or poisoned session is cleaned up by that idle path.
Failures retire the session for recovery; they authorize no retry or reuse.

`python3 tests/run-handoff-test.py KERNEL_TREE` extracts the production
scan-finish, close, cancellation and idle-retirement functions. Its
join-on/off ASan/UBSan cases passed successful retention, canceled/poisoned scans, eleven incomplete or
corrupt handoff conditions and the retired-completion boundary, single
unused-BSS deactivation and guard/write failures. A deterministic close/scan-completion interleaving failed before
moving the permanent producer fence under the MAC mutex, and passed after
that fix. Completion before close and late scan cancellation also retire the
poller without a duplicate completion. The I/O/work scheduling stubs prove
host decisions only, not firmware execution or actual concurrent workqueue
behavior. Focused source review found no remaining concrete producer-fence
bug within the current closed-TX scope. The first station callback still
needs a scan-worker fence; full peer teardown is unfinished. No candidate
admits this changed BSS lifetime.

Patch 0134 adds only the typed HIF receive-filter command. Public gen3
[`wlan_oid.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/wlan_oid.h)
defines DIRECTED as bit 0 and BROADCAST as bit 3, so the admitted word is
exactly 0x09. Other filter modes are refused before changing the credit,
sequence history or output buffer. The existing scan filter stays 0x08.
No MAC callback submits the new filter yet. Actual HIF host fixtures passed
its success, every scalar-write fault, expired deadlines and sequence reuse
with non-PIE ASan/UBSan. Those fixtures do not prove firmware application.

## Remaining work

Wire the scan-worker fence and validated rate conversion into station
callbacks, normalize the successful AID, implement managed-TX callbacks,
current-state RX/TX admission and healthy peer teardown. Follow the [BSS lifetime correction](BSS_LIFETIME_REVIEW.md): retain
one AIS owner through scan/join; no quiet window proves a drain. Preserve
single-use peer/PID/channel tokens and exactly-once skb disposal after every
partial failure. No cleanup command may follow terminal firmware poison.

Then validate a concrete candidate and bounded authentication/association
protocol before the device test. Successful join is a prerequisite for the
subsequent PIO data TX/RX admission. This checkpoint is not usable Wi-Fi.
