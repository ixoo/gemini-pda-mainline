# D2 RX boundary: source-supported facts and remaining ambiguity

Bounded retained-source review following the [D2 refusal](SSH_D2_RESULT.md).
No new register access, firmware reverse engineering, driver change or candidate.
The retained C10 integration snapshot `0b88350b26679568c7fc27fcd117994122ddc7fa`
is clean. All six files match the [validated C10 build](results/ccmp10-build-validation.json),
including `mac.c` SHA-256
`9c436a627a5b23a416b9fc2a1401f349a10e971af4086464117bc6d50890ef88`
and `hif.c`
`1d5b6b636a027536ef7115b03cf25a96ce1da5fb36b644876e26310037c0ad3f`.

## Evidence table

| Established | Excluded for this fault | Still ambiguous |
| --- | --- | --- |
| Same C10 image and runtime driver as the three-run baseline; one mask enable, no SET_MONITOR | A new kernel, C11 group observer or D2 local query causing this acquisition directly: no local query/SSH process executed | Host scheduling/import timing effects are not disproved |
| Guard succeeded, then mask enable was submitted; receive in ENABLE_PENDING refused 94 versus 142 | This is -EPROTO/branch 4, not channel-grant, frame or credit timeout; receive returned 97.243462 ms before the pending credit deadline | Which producer/queue condition gave incompatible advertised/descriptor lengths |
| Guard status WHISR 0x2 is retained immediately before arm; source admission checks TX/credit/in-flight quiescence, not RX emptiness | No basis to claim an RX-empty boundary before changing metadata | Whether an older queued frame, a transition during acquisition or another producer condition caused the mismatch |
| Requested PIO transaction completed; mismatch precedes memcpy and success publication | No partial-transfer success, post-read dependency, accepted framing exception or data-frame delivery | Actual complete producer frame/body and FIFO-pop extent are not measured |
| Enable-time difference +48; prior close-time observations -48 | A universal -48 correction | Metadata-group arithmetic is a clue, not a validated length contract |
| No ACTIVE or healthy stage-3 cleanup; one page pending; key disables uncredited | Healthy re-arm, resource-debt forgiveness or key retirement | The source-supported RX/control/queue ordering needed for reusable lifetimes |

## Exact host ordering

In C10 `mac.c`, `mt6797_mac_join_guard()` records the existing WHCR/WHISR/credit
acquisition on success (lines 1157–1175). `join_work` calls this guard before
`mt6797_native_diag_step()` (2185–2190). The latter sets `c.quiescent` from only
pending credit, page debt and in-flight TX, submits mask enable, then charges its
one-page ledger (1765–1840). It does not test RX FIFO emptiness. The same worker
can then acquire RX while ENABLE_PENDING (receive path 2380–2440); its pre-read
gate permits this phase within the existing sample/drain bounds (1693 onward).
The MAC mutex excludes another MAC caller updating that stored guard between
these operations. The terminal record is emitted before later cleanup attempts.

D2 retained guard-return `68292076004` ns. The arm-step `now` reconstructed from
the unchanged credit deadline minus 100 ms is `68292076773` ns, 769 ns later.
Port-0 receive return is `68294833311` ns. These ktime-domain comparisons do not
mix with printk timestamps and do not timestamp the internal register reads.

The public [gen3 register map](https://android.googlesource.com/kernel/mediatek/+/android-mtk-3.18/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/mt6630_reg.h)
names WHISR bit 1 RX0-done, with matching WHISR/WRPLR/data-port offsets. Thus
interpreting the already retained pre-arm 0x2 as a receive indication is consistent
with that public gen3 map. It is not an independent exact-silicon proof of FIFO
contents, emptiness, read-clear semantics or a producer queue fence. The observed
source predicate does not establish any of those stronger properties.

In `hif.c` 1093–1208, receive reads WRPLR under the HIF mutex, selects the port's
halfword, completes advertised length plus appended-word PIO, checks the guard,
then requires descriptor length equality. Mismatch retains only admitted base
hints, poisons the transaction and bypasses memcpy/logical-byte publication.
Runtime post-read is false; a mismatch would precede it in either option state.
The public [gen3 single-packet receive path](https://android.googlesource.com/kernel/mediatek/+/android-mtk-3.18/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c)
also compares the advertised length with the descriptor RX byte count. This
supports retaining equality; it does not explain this firmware's transition.

## Focused regression and next source question

The existing [mask-control actual-source fixture](tests/run-mask-control-test.py)
now includes valid 94-byte transfers, every injected I/O fault at that length,
and the observed 94/142 refusal on both ports through legacy/runtime and selected
APIs, alongside all five prior mismatches. Local ASan/UBSan passes against exact
C9/C10 sources; parent/child RX I/O/publication tables remain equal. Complete
advertised transfer, no-copy, sticky poison and no second I/O are preserved.
The [framing-hint fixture](tests/refused-framing-hif-test.c) also exercises the
exact 94/142, 0x5faf/0xce/0xc000 tuple on both ports and all three APIs against
retained C8/C9 receive sources; local ASan/UBSan passes. The mask-control suite
separately checks unchanged C9/C10 receive behavior. These are host behavior
tests, not a simulated hardware FIFO/producer proof.
No kernel compilation or Linux-only validation was performed for this test-only
extension; the runtime kernel/image is unchanged.

No host correction is proved by the current producer evidence. The next bounded
source question is how metadata-format ownership can avoid changing the receive
layout across queued/acquired frames while preserving EAPOL, strict PTK/GTK PN
and complete cleanup. Compare stationary-format initialization with the current
runtime arm/close ordering before choosing one justified successor. A TX-ledger
predicate, a single interrupt indication or command credit alone is not a queue
retirement contract. Do not add a speculative register, assert an unexplained
callback fence or select a predetermined fix. The owner has not released the
instruction to hold new candidate builds.

## Follow-up source decision

The [fixed-format proposal](RX_FORMAT_OWNERSHIP_SUCCESSOR.md) records the bounded
WHCR/public-host review, existing decoder compatibility and the required change
of completion/configuration owner. Linux ASan/UBSan against exact C10 EAPOL
headers passed all 48 existing layout/padding cases. No firmware effect or fixed
format stability is proved. This selects one proposal for implementation/review,
not a candidate build or device admission; the owner's build hold remains.
