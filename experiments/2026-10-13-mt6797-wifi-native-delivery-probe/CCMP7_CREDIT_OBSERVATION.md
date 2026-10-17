# C7: distinguish shared credit pairing and exact timeout site

Status: consumed once, 2026-10-17. [C7 result](CCMP7_RESULT.md) records returned
monitor-disable credit, two real ping replies, failed SSH and post-CLOSED
receive-length refusal. No unchanged C7 retry. [Preparation](CCMP7_PREPARATION.md)
owns real pins and tooling gates. Ordinary secure Wi-Fi, ten-minute SSH and
healthy reconnect remain the objective; this diagnostic is not acceptance.

## Concrete gap after C6

[C6](CCMP6_RESULT.md) completed both data TXs and DHCP, then stopped with
monitor disable pending and one shared page owed. No frame was in flight.
The cached WHCR/WHISR and port history cannot identify which half of a
CPU/FFA credit pair is missing or which of branch 1's three failure sites ran.

The pinned public gen3
[credit allocator](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c#L384-L525)
accumulates per-queue TX-done and FFA counts separately. Its optional extra-
TX-done path can distribute available FFA against outstanding use, recording
pre-used pages so a later queue count does not refund them twice.
`ucExtraTxDone` is a host-side configuration property: the pinned tree has
only its declaration, the default-1 lookup in `wlan_lib.c:5476`, and this
allocator use. This source fact is not evidence of C6's returned counts or a
selected policy change.

The current owner deliberately uses strict paired reconciliation. Its
`normal_command.h` matches CPU/TC4 and AC1/TC1 accrual against the shared FFA
pool, refuses foreign queues/over-release, and retains unmatched remainders.
C6 did not retain those validated remainders. Neither an invented refund nor
a longer deadline is justified without the missing distinction.

## Minimal source change

[0197](../../patches/proposals/0197-wifi-mt6797-retain-terminal-credit-pairing-and-timeout-site.patch)
extends C6's existing terminal history only:

- Cache WTQCR7 and the full seven-field `mt6797_normal_release` result from
  the same existing successful reconciliation. Raw CPU/FFA deltas and pending
  accumulated counts remain distinct. Capture TC1 state too, because FFA is
  shared rather than intrinsically owned by TC4.
- Tag the existing branch-1 failure sites: 1 overall-lifetime check, 2 combined
  scan/poison/closing/poll/frame check, 3 pending command-credit expiry. The
  original conditions, short-circuit increment, deadline and return paths are
  byte-identical after removing only the diagnostic assignments.
- Add one once-only terminal line with that site, native state, pending flag,
  credit/lifetime deadlines, poll/scan/closing/error fields and cached credit
  history. Existing first-line validity and return timestamp govern the cached
  fields; these are not extra reads or fault-time snapshots.

No HIF, reconciliation algorithm, RX helper, boot reader, frame gate, key,
PN, command, budget, timeout origin, cleanup or re-arm behavior changes.
No extra line is emitted during ACTIVE. Total new terminal output is four
lines instead of C6's three; logging follows the already selected terminal.

Profile `mt6797-a53-wifi-ccmp-credit-observe` selects exact C6 ordered 691
patches plus 0197, with the same 26 configuration fragments. Other explicit
profiles and series remain unchanged. This stays a default-off diagnostic.

## Validation and experiment decisions

The [fixture](tests/run-ccmp7-credit-observation-test.py) reuses the C6 C
fixture and compiles the actual C7 helpers under ASan/UBSan. It checks raw
CPU-only versus FFA-only inputs, pending counts carried across a zero-delta
snapshot, no input/ledger mutation or refund, off admission, both ports,
failure metadata, once-only four-line output and frozen terminal state.
It verifies exact parent recovery by reversing 0197, unchanged HIF/ledger/
other-driver/boot files and byte-identical timeout gates after tag removal.
These checks pass locally and on Linux against an isolated actual-source
child. Applied-build-source/kernel validation must precede candidate selection.
Strict checkpatch reports only the intentionally absent truthful DCO sign-off,
with zero warnings/checks; this internal proposal is not submission-ready.

One later fresh, package-validated, receipt-bound candidate may use the
unchanged C6 one-capture/one-session/one-return protocol, all-RX 512/1 MiB,
delivery 64/wall 10 s-or-lower and existing grants/deadlines. It must preserve
the exact historical host/recovery sources and current credentials separately.
No binding-only kernel rebuild and no completed-tool mutation.

Hypothesis: retained valid credit-pair state and the actual timeout site can
separate a missing CPU completion, missing FFA availability, a different stop
predicate or a consumed-credit handling defect. Unique observation: the raw
and accumulated return state that C6 lacked, with zero additional I/O.

1. FFA pending without CPU: audit the public pre-used-accounting contract and
   exclusive-owner bounds before proposing any ledger change. Do not refund
   pages just because FFA is nonzero.
2. CPU pending without FFA, or neither: retain the missing obligation and
   trace its producer/consumption contract. No synthetic credit or timeout
   extension follows.
3. A different site/condition: classify separately; no assumed disable-credit
   repair from absence of that timeout.
4. Healthy network/cleanup: apply the unchanged real DHCP/ping/SSH and cleanup
   verdicts. It is bounded compatibility, not firmware replay/key-retirement
   proof or maintained operation. The earlier gap-48 remains a separate gate.

Preserve/seal/quiesce and use the reviewed return in every admitted outcome.
Owner physical boot2 selection remains mandatory after guarded full readback
and shutdown; no unchanged-artifact retry is admitted.
