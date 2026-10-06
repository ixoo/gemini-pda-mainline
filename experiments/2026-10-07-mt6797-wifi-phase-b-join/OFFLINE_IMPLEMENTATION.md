# Phase B offline implementation checkpoint

Status: driver incomplete; bounded join callbacks are implemented and built
through 0139 in [compile 6](COMPILE_6.md). The first concrete candidate/test is
pinned in [PROTOCOL.md](PROTOCOL.md). No device result yet. Earlier checkpoints
below retain their historical scope. Compile 2 covers patches through 0132. Profile
`mt6797-a53-wifi-phase-b-compile` selects thirteen original format-patches in
canonical order after the Phase A baseline. It has a distinct kernel release.
The proven Phase A profile is unchanged. Earlier checkpoints admitted no candidate or device test.

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
[compile 2](COMPILE_2.md) with the snapshot option enabled. Patches 0133 and
0134 failed [compile 3](COMPILE_3.md) on a private HIF struct access and,
after the fix, passed [compile 4](COMPILE_4.md).

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
The peer-setup callback below submits this filter. Actual HIF host fixtures passed
its success, every scalar-write fault, expired deadlines and sequence reuse
with non-PIE ASan/UBSan. Those fixtures do not prove firmware application.

## Peer and managed-frame callback checkpoint

Preparation patches `0135` and `0136` connect one copied peer to the retained
scan owner. The first station callback quiesces scan work outside driver locks,
reserves the peer once, and submits the directed filter, channel request and
pre-auth STA record in order. Each command waits for its actual TC4 credits;
the channel grant is a separate validated event. Waits release the MAC mutex
so the poller can run. A STA activation event cannot release command debt.
Close, regulatory retirement and worker failure wake callbacks without
claiming returned credits. No failure permits a second peer attempt.

Managed-TX callbacks admit one authentication or association request only in
their current copied state and live channel grant. The initial legacy scope
advertises one queue, preventing mac80211 from adding WMM. Received responses
must follow a successful PIO submission; authentication advances the host STA
only after a received successful response. Association status and AID are
copied, but state-3 admission remains refused pending the next implementation.
This checkpoint is incomplete and is not a device candidate.

Run the production-function host fixtures against the prepared kernel tree:

```sh
python3 experiments/2026-10-07-mt6797-wifi-phase-b-join/tests/run-peer-test.py KERNEL_TREE
python3 experiments/2026-10-07-mt6797-wifi-phase-b-join/tests/run-handoff-test.py KERNEL_TREE
```

The peer fixture covers setup order, every command-stage failure, partial and
excess credit returns, spurious/expired/retired waits, activation separate from
credit, copied addresses, one-shot refusal, managed callback gates and refusal
to authenticate without a response. Both fixtures pass with ASan/UBSan. They
do not establish kernel races, firmware behavior or RF transmission. The
selected full kernel build for this checkpoint is pending.

## Associated state and finite cleanup checkpoint

Patches 0137–0139 implement the next bounded join stage. A host STA can
advance only after the exact management TX acknowledgement and actual TC4
credit return. Accepted association applies BSS/RLM before STA state 3, then
requires its separately matched activation event. The original BSS encoder
uses an 88-byte payload, legacy 5 GHz rates, 20 MHz channel 40 and no security,
HT/VHT or WMM. An independent compiled layout oracle from the pinned public
vendor typedefs matched 8,192 input vectors; vendor headers remain outside the
repository. This comparison proves encoding only.

An accepted join queues exactly one owned deauthentication with the next
12-bit frame sequence. Cleanup waits for its matched successful TX done and
returned pages, then sends STA removal, channel ABORT and BSS deactivation,
waiting for actual credit between each command. A refused attempt uses the
same healthy cleanup without deauthentication. mac80211 removes a refused
STA before managed completion; those callbacks now preserve polling, and a
later completion cannot close the queued owned frame. No slot is reused or
claimed firmware-drained. A poisoned session sends no teardown command.

The production-function peer fixture passes acceptance/refusal callback order,
separate TX completion and credit, partial/excess releases, allocation failure,
command faults at all three cleanup stages, sequence budgets and retired waits
with ASan/UBSan. Actual HIF fault fixtures now include BSS setup. Ordered replay of all three patches matched every driver file byte for byte.
Checkpatch reported no errors: 0137 retains one line-length warning and seven
style checks; 0138/0139 have none. The missing sign-off check is deliberately
excluded because no DCO certification or upstream submission is asserted.
Repository checks, all 21 profile-order audits and Python syntax passed.
The exact full kernel build passed in [compile 6](COMPILE_6.md);
kernel races and all RF behavior remain untested.
Sanitized stage logs expose submission, TX done, directed response status,
credits, grant, activation and terminal cleanup without AP identities or
frame bodies. The same bounded debug/sleepy notifications as the proven scan
consumer are accepted; malformed and unknown events remain terminal.

## Remaining work

Run the concrete [first bounded protocol](PROTOCOL.md), preserving exact
identity/evidence gates and its failure branches. Successful join is a prerequisite for the
subsequent PIO data TX/RX admission. This checkpoint is not usable Wi-Fi.
