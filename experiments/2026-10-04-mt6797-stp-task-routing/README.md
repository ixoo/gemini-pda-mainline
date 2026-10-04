# MT6797 STP task-routing preparation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-mt6797-stp-task-routing` |
| Status | Driver dependency draft; host and Buildbox checks pass; runtime untested |
| Subsystem | Shared STP task delivery before sequence/ACK commitment |
| Date | 2026-10-04 |
| Device action | None; owner unavailable; hardware testing deferred |

## Problem and changes

The [shared link checkpoint](../2026-10-04-mt6797-stp-link-state/README.md)
requires an owner to reserve delivery storage before advancing sequence and
credit. Task routing must ensure a refused packet does not acknowledge either
its receive sequence or a piggyback transmit ACK. Otherwise a full Bluetooth
queue can lose a packet that the peer believes was accepted.

Two logical patches prepare that boundary:

- [original 0105](https://github.com/ixoo/gemini-pda-mainline/blob/fcca630d04918a30dd3038e3ca46301798ce19d5/patches/proposals/0105-soc-mediatek-ignore-out-of-window-full-STP-ACK-credit.patch)
  corrects the earlier helper's strict out-of-window ACK refusal. The selected
  Gemian `stp_process_rxack()` grants credit only when an ACK matches a transmitted
  sequence. Its caller still accepts a new receive sequence when that ACK grants
  no credit. Ignoring such credit allows a data retry after separate ACK traffic
  has advanced TX. WMT's independent command ACK check remains strict.
- [0106](../../patches/proposals/0106-soc-mediatek-route-full-STP-tasks-before-committing-credit.patch)
  routes new payloads to a unique ordinary-task binding, validates the entire
  binding set before invocation, and commits both credit windows only after the
  callback accepts the whole packet. The production WMT command matcher now
  uses this path, avoiding the previous double decode in its state transition.

The [receipt](results/validation.json) pins the selected source and authored
parent/child identities. The preceding link receipt remains historical evidence
for its stricter ACK behavior; it is not rewritten as proof of this correction.

Bindings are immutable during a serialized call. Callbacks may consume or copy
the packet, or explicitly discard it under an owner's inactive-task policy.
They must publish nothing on refusal and must neither sleep nor reenter the
owner when called from an IRQ. Result payloads alias the wire buffer and must
be consumed before reuse. Unknown new tasks refuse; explicit inactive-task
handling requires an intentional binding rather than automatic silent discard.
ACK-only traffic needs no task binding. Duplicates repeat ACK accounting without
calling a client, including after that client unbinds.

Delivery before credit is this draft's host policy. The reference's ordinary
queue branch updates ACK state before enqueueing; that source does not prove
queue-full behavior or firmware acceptance of the new ordering. The callback
refusal contract is established by the host fixtures.

The WMT adapter uses one synchronous validation binding. It preserves exact event
contents, length limits, command ACK checks and duplicate-reply refusal before
publishing its link state. The current production IRQ path remains WMT-only
with one-command lifetime. The BT/GPS callbacks in the fixture demonstrate
routing, not registered kernel clients. Real receive queues, long-lived IRQ
ownership, retransmission, client/reset lifetime and a standard HCI device are
unimplemented. The roadmap limits the next Bluetooth draft to its bounded
positive-control path. This patch adds no resource, power or radio operation and does
not implement NAK, resynchronization or firmware-message tasks.

The isolated `mt6797-a53-stp-task-routing-compile` profile extends the previous
link-state profile by just these two patches. Configuration, DT and installed
candidate remain unchanged. It is a compile checkpoint, not a boot candidate.
Both format patches carry synthetic non-certifying internal authorship and no
DCO. They are not submission-ready. Their destination is a reviewed common
MediaTek connectivity transport; delete the temporary patches when superseded
by an upstream implementation.

## Validation and reproduction

The [runner](test-tasks.py) compiles actual task, link, WMT and IRQ headers with
strict warnings, ASan and UBSan. The historical WMT sources remain unchanged;
temporary fixture copies adapt only the existing `transport` member paths.
Unchanged historical helper headers retain their original mocked dependencies.
All nine WMT framing/state/IRQ/negotiation/version fixtures and the prior task
framing fixture pass. This is not kernel IRQ concurrency evidence.

The [task fixture](test-tasks.c) verifies callback invocation before credit
publication, positive and negative callback refusal, unknown tasks, malformed
bindings, corruption, duplicates after unbind, 48 alternating task deliveries
across sequence wrap and a 2048-byte payload. Its queue-full sequence refuses a
BT packet with piggyback ACK0, accepts a separate ACK2, then delivers the original
packet without granting its stale ACK0 any credit. The
[current link fixture](test-link.c) retains the preceding 512-case transmitted-
entry oracle with the corrected ignored-ACK result; the old fixture is preserved.

```sh
python3 experiments/2026-10-04-mt6797-stp-task-routing/test-tasks.py \
  /path/to/prepared/linux/drivers/soc/mediatek
KERNEL_PROFILE=mt6797-a53-stp-task-routing-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-stp-task-routing-compile ./scripts/buildbox fetch-package
```

Both patches pass strict checkpatch with only the established draft exclusions:
`MISSING_SIGN_OFF`, inherited API `TYPO_SPELLING`, and `FILE_PATH_CHANGES` for
the new temporary header's absent upstream maintainer entry.

The full Buildbox build and remote package validator pass for input commit
`fcca630d`. All three changed headers in the prepared kernel match the host-tested
source hashes. The production WMT path compiles through the new task router.
The fetched inventory, Image.gz and configuration identities are recorded in
the receipt. Configuration is byte-identical to the parent link-state profile.
No new compiler warning appears; historical patch 0261 whitespace and the
unused CPU rollback callback warning are inherited. Repository checks pass
across all 275 manifest profiles. No binding or DT content changed, so no
additional schema check was run. The Linux-only provenance fixture is skipped
on macOS; the package itself passed the remote Linux validator.

The later receipt update changes documentation only; the package remains
attributed to its original input commit. No device access, candidate construction,
installation or hardware support is claimed.

## Consolidation after validation

The corrected link state is now one [0104 patch](../../patches/proposals/0104-soc-mediatek-share-full-STP-sequence-and-ACK-state.patch),
combining the original 0104 and 0105. The original receipt above remains
attributed to `fcca630d`; its package is not relabeled. The
[consolidation receipt](results/consolidation.json) records replay of the new
0104 followed by unchanged 0106 onto the exact pre-link parent. The complete
tracked driver/header tree is byte-identical to the previously built child.
Every other selected patch and all retained profile settings are unchanged.
The focused host runner passes again; consolidated 0104 passes strict
checkpatch with the same exclusions. No kernel rebuild was run for this
source-identical consolidation, and no device action occurred.

The AFE, task-framing and link-state compile profiles and their series copies
are retired. Their historical receipts and commands describe the original
commits. Current reproduction uses only
`mt6797-a53-stp-task-routing-compile`, now selecting 581 patches. All 272
remaining profiles must preserve canonical series order. New packages built
from this inventory need their own build provenance before candidate selection.
