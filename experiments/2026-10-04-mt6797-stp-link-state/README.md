# MT6797 shared STP link-state preparation

Historical compile checkpoint: this intermediate profile and series have been
retired after the [task-routing consolidation](../2026-10-04-mt6797-stp-task-routing/README.md#consolidation-after-validation).
Receipts and commands below refer to their original input commits. Current
compile reproduction uses `mt6797-a53-stp-task-routing-compile`.

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-mt6797-stp-link-state` |
| Status | Driver dependency draft; host and Buildbox checks pass; runtime untested |
| Subsystem | Shared STP sequence and cumulative ACK ownership |
| Date | 2026-10-04 |
| Device action | None; runtime testing deferred until owner returns |

## Problem and implementation

The [task codec](../2026-10-04-mt6797-stp-task-framing/README.md) can decode
Bluetooth and WMT frames, but the current state helper couples link advancement
to one exact WMT reply. The selected Gemian reference instead owns one
seven-frame transmit window and one expected receive sequence across tasks.
A Bluetooth event must not create a separate sequence epoch or require an
active WMT command. The [receipt](results/validation.json) pins both the selected
STP implementation and its seven-frame window definition.

Patch [original 0104](https://github.com/ixoo/gemini-pda-mainline/blob/fcca630d04918a30dd3038e3ca46301798ce19d5/patches/proposals/0104-soc-mediatek-share-full-STP-sequence-and-ACK-state.patch)
introduces a serialized link helper and places the existing WMT command client
on it. The production WMT IRQ owner and diagnostic access paths now use the
embedded shared state. WMT still validates the exact event before mutation,
admits only one command, rejects duplicate command replies, and requires
complete peer and host ACK accounting before successful retirement.
The command-client rule does not limit the shared helper to one TX frame.

The helper accepts cumulative ACKs only within its transmitted window;
repeated current ACKs consume no additional credit. New receive frames advance
the shared sequence independent of task. Recent duplicate sequences request
another cumulative ACK without delivery or piggyback TX credit. A valid frame
whose sequence is outside the available receive history refuses. At seven
accepted but unacknowledged RX frames, new data refuses until a complete host
ACK frees credit. No refusal implicitly clears link state.

An outgoing ACK snapshot can finish after a newer frame was accepted. Completing
that snapshot frees its own credit, leaving the newer ACK owed. Fully transmitted
new data also accounts for its piggyback host ACK. Call the TX transition only
after all bytes are sent; retransmitted copies must not allocate new sequence
credit. Initialization belongs only to an admitted full-mode boundary after
retiring the prior transport. Ordinary WMT reset events do not reseed it.

The helper has no allocation, lock, MMIO, timer, power or reset action. Its owner
must serialize access and reserve delivery storage before accepting a new frame,
or explicitly discard an inactive task. Result payloads alias the frame buffer.
The current production IRQ owner still accepts only WMT; Bluetooth and GPS
clients and receive queues are not wired. Retransmission storage/timers,
aggregate IRQ budgets and client/reset lifetime remain the next transport work.
NAK, resynchronization and firmware-message tasks remain outside this draft.
This is not a completed Bluetooth driver or evidence of radio support.

The isolated `mt6797-a53-stp-link-compile` profile adds only this patch to the
previous task-framing profile, with unchanged configuration and DT. It is not a
boot candidate and leaves the installed version-read candidate unchanged.
The internal format-patch uses a synthetic non-certifying author without DCO;
it is not submission-ready. The expected destination is a reviewed common
MediaTek connectivity transport, after which this temporary patch can be deleted.

## Validation and reproduction

The [runner](test-link.py) compiles actual kernel framing, link, WMT adapter and
WMT IRQ headers with strict C warnings, ASan and UBSan. Historical fixtures
remain unchanged in the repository. Temporary copies mechanically change only
access to the four link fields and ACK flag now under `transport`; their
assertions and expected results are retained. Other unchanged historical helper
headers supply their original mocked dependencies. This is host integration
coverage, not a kernel IRQ concurrency test.

The [link fixture](test-link.c) uses a transmitted-entry queue oracle for all
512 combinations of modulo-eight start, window occupancy and ACK value.
It covers full-window refusal, cumulative and repeated ACKs, task alternation,
64 receive deliveries across wrap, duplicate suppression, older ACK snapshot
completion, piggyback credit, RX bounds and unchanged state/results on refusal.
The prior task-framing fixture and all nine WMT framing, state, FIFO/IRQ,
negotiation and version fixtures also pass. Negotiation/version owner leaves
remain mocked as stated in those fixtures.

```sh
python3 experiments/2026-10-04-mt6797-stp-link-state/test-link.py \
  /path/to/prepared/linux/drivers/soc/mediatek
KERNEL_PROFILE=mt6797-a53-stp-link-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-stp-link-compile ./scripts/buildbox fetch-package
```

Strict checkpatch passes with the same internal-draft exclusions as the preceding
framing checkpoint: `MISSING_SIGN_OFF`, inherited API `TYPO_SPELLING`, and
`FILE_PATH_CHANGES` for the temporary new header's absent maintainer entry.
The full Buildbox build and remote package validation pass for input commit
`f2138c82`; the fetched inventory, Image.gz and configuration hashes match the
receipt. All four changed files in the prepared source match the host-tested
child. The production WMT path compiles against the new state layout. The
configuration is byte-identical to the parent task-framing compile profile.
Repository checks pass, including all 274 manifest profiles. No new compiler
warning appears: historical patch 0261 whitespace and the unused CPU rollback
callback warning are inherited from the parent build. No DT or binding content
changed, so no additional schema check was run. The local Linux-only provenance
fixture is skipped on macOS; the package itself passed the remote Linux validator.

The later receipt update changes documentation only; the package retains its
original input-commit identity. No device access, candidate construction,
installation or hardware result is claimed.
