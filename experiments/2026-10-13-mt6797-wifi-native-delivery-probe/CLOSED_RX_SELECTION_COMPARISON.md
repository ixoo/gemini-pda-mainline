# Post-CLOSED receive selection comparison

Status: built and composed successor, not a proved repair or hardware result,
2026-10-17. C7 is consumed; no unchanged repetition. The full Wi-Fi delivery
objective and its crypto, lifetime and ten-minute acceptance gates remain.

## Evidence and smallest question

[C7](CCMP7_RESULT.md) returned monitor-disable credit, entered CLOSED, submitted
deauthentication, then refused FIFO/header lengths 427/379. Runtime success
post-reads were already absent. Cached release counts do not explain the older
C6 timeout, and the receive refusal is a separate transport result.

The pinned public gen3
[single-packet reader](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c#L2826-L2908)
reads one whole WRPLR word, selects port 0 if nonempty, otherwise port 1,
then reads that selected FIFO and requires descriptor/advertised equality.
The current MAC instead requests each port separately with fresh whole-word
acquisitions. In C7, port 1 had no successful receives but 467 acquisitions
with port-0 work advertised. This difference is established; a consuming
AP-bridge read or producer cause is not.

A bounded retained-firmware review completed its checked window, reproduced
its retained handler anchor and stopped at an indirect call. It established
no RX enqueue/length-store mechanism. No further callback or image-wide scan
is selected. Raw analysis, binary identities and excerpts remain private.

A repeated scalar cannot identify whether two same-length records refer to
the same packet. C7 already retained the refused lengths and type hint.
Additional counters alone would not settle the effect of the unmatched
selected-half acquisitions. The smallest remaining source-backed comparison
changes only their post-CLOSED selection, using the public reader's sequence.

## Hypothesis, observation and decisions (before implementation)

Hypothesis: cleanup's fresh acquisitions for an empty requested port while
another port is advertised contribute to the length/data pairing failure.
This is a sequence-sensitivity test, not an asserted pop/latch mechanism.

Unique observation: the first bounded cleanup under one acquisition followed
by selection from that same word, with no extra empty-request/opposite-work
acquisition. Preserve the chosen port as result metadata from the existing
read. The previous per-port ACTIVE sequence, scan, firmware commands and
budgets remain unchanged. CLOSED gets at most eight packets per worker tick,
no more than its previous eight-per-port bound. Port-0-first priority can
starve port 1 under continuous port-0 traffic; this comparison is not an
operational arbitration policy or proof of healthy queue ownership.

Earlier ACTIVE, scan and boot acquisitions are deliberately unchanged. A
repeat refusal cannot exclude pairing damage accumulated before CLOSED; it
only tests the incremental cleanup sequence. Equal length values also do not
establish packet identity.

1. Same header refusal: the public selection sequence is insufficient; no
   cache, shorter read, length subtraction or unchecked copy follows. Preserve
   exact port, lengths, type hint, credit and cleanup history.
2. Healthy cleanup: supports sensitivity to this source sequence, with timing
   alternatives remaining. Require actual network and teardown verdicts; one
   success is not causal proof, replay safety or maintained operation.
3. Earlier timeout/different failure: classify separately; it does not test
   the post-CLOSED comparison if that boundary is not reached. No unchanged
   retry or timeout extension.
4. Port-1 starvation/credit debt: preserve as a distinct result. Do not relax
   priority, guards or deadlines during the session.

## Implementation and admission boundaries

One internal HIF entry point selects the port from its existing pre-WRPLR
word and returns selected-port metadata. The legacy boot and requested-port
entry points retain their complete operation/publication behavior. No cache,
new register, post-failure read, packet interpretation or extra firmware action.
Keep full advertised transfer plus existing appended-word/block span, strict
header equality, poison/no-copy and poisoned-context no-I/O behavior.

Only opted-in stable-CCMP, engaged, CLOSED join reads use this entry point.
No scan or ACTIVE selection change. Retain the existing ordinary PN/key gates,
all-RX512/1MiB/delivery64/wall10s-or-lower and finite drain/grant/deadline limits.
One new logical proposal and actual-source tests precede profile selection,
clean pushed Buildbox build, validated package, receipt binding and guarded
installation. No existing receipt/tool mutation or device action is authorized
by this design alone; later admission must identify the real candidate and
review its exact tooling. Owner physical boot2 selection remains mandatory.

Focused tests reuse the actual HIF fixtures: both selected ports, both nonempty
(port-0 priority), both empty, valid lengths and all observed mismatch pairs,
capacity and every reachable transport failure, complete transfer, no-copy,
poison and no second I/O. Compare the full legacy tables byte-for-byte to C7;
verify only post-CLOSED MAC routing changes and unchanged scan/boot sources.
Mocks establish host ordering and selection, not hardware FIFO semantics.

## Authored input and focused local validation

[Proposal 0198](../../patches/proposals/0198-wifi-mt6797-compare-post-CLOSED-RX-port-selection.patch)
changes only HIF selection/result metadata and the opted-in CLOSED MAC routing.
The [actual-source fixture](tests/run-closed-selected-comparison-test.py) passes
ASan/UBSan locally: byte-identical legacy boot/requested-port tables, both
selected ports, both-nonzero priority, empty/capacity/deadline paths, all four
observed mismatch pairs, and 1846 injected I/O faults. It preserves no-copy,
poison and poisoned second-call no-I/O. The actual MAC routing block passes
80 flag/state/port cases with the option compiled on, and another 80 with it
off. Exact patch reversal recovers C7; other driver/boot files, scan and every
MAC gate outside the routing/reporting block remain byte-identical.

The mock extension only supplies the independent opposite advertised halfword;
it models no FIFO-pop mechanism. Empty whole-word queries have no selected
port: retained legacy per-port attempt counters use the loop's port-0 bucket
for those queries, not an observed port-0 FIFO read. Nonempty chosen-port
metadata is valid even on later refusal, and does not certify an RX packet.

Profile `mt6797-a53-wifi-ccmp-closed-select` selects C7's ordered 692 patches
plus 0198 with identical 26 fragments. Existing named series/profiles remain
unchanged; the canonical superset gains 0198. Linux actual-source fixture
validation and the ordinary clean pushed Buildbox build subsequently passed. [C8 preparation](CCMP8_PREPARATION.md) owns
the real validated package, receipt and tooling; no runtime result yet.

Strict checkpatch reports only the deliberately absent truthful DCO sign-off
(one error, zero warnings/checks) on this internal non-certifying archive.
Repository checks pass, including all 31 profile selections; the profile audit
confirms every existing profile unchanged and the new series in canonical order.
No kernel/DT change beyond the named Wi-Fi selection; no DT schema check needed.

Frozen proposal SHA-256: `55fdbe7c1a738b9b3705ac467bcd2e9e2723378e4b7d8abca6fb58cf797c5f34`.
