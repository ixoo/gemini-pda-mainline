# Material correction: CONFIG TC4 and START TC0 are independent

This supersedes earlier claims that CONFIG and START both use TC0 or share
one debit pool. The prior host tests proved that implementation's behavior,
not its incorrect credit-class assumption. Historical validation receipts
are not rewritten. No earlier component is admitted to live/kernel use by
those receipts. This correction is submitted for independent review before
further payload layering.

At selected Planet pin `c5b0be85017ad0c599725e8273842efdbecdd88a`, gen3
`wlanImageSectionConfig` assigns `ucTC = TC4_INDEX` at line 2431 and passes
that variable to `nicTxAcquireResource` at lines 2474–2475. In the same file,
`wlanConfigWifiFunc` assigns `TC0_INDEX` at line 2845 and acquires that class
at lines 2866–2867. Both charge `nicTxGetPageCount(record_length, TRUE)`.
The actual call sites override the earlier mistaken generalization about
INIT traffic. [Pinned source identities](results/credit-correction-sources.json).

`nic_tx.h` seeds eight maximum-frame buffers independently for TC0 and TC4;
each therefore has 104 pages. CONFIG's 20 bytes consume one **TC4** page;
START's 16 bytes consume one **TC0** page. Returned counters likewise differ:
TC4 maps to CPU index 15, while TC0 maps to AC0 index 0. They participate in
the shared FFA accounting but are not interchangeable free-page balances.
The unresolved returned-counter acquisition/replenishment contract remains.

The C state now retains `free_pages` as the CONFIG/TC4 balance for minimal
API disruption and adds `start_free_pages` as START/TC0. Fresh admission must
set both independently if both are allowed; leaving START's field zero
correctly refuses START. Each begin checks and debits only its class. There
is no borrowing, automatic seed, refund or replenishment. The generic
`mt6797_init_debit` arithmetic is unchanged and can act on either explicitly
selected class. CONFIG phase composition continues to debit its existing
field, whose correct identity is now TC4.

Sequence history remains shared for a different, source-supported reason:
both constructors call `nicIncreaseCmdSeqNum`, and `nic.c:1025-1041` locks
and increments the same adapter `ucCmdSeqNum` byte. Its identity is separate
from `ucTC`. The bitmap's no-reuse policy remains deliberately stricter than
the vendor wrapping allocator. Sharing sequence history does not share
credits or imply ACK equivalence.

Focused tests consume 104 CONFIG pages while checking START remains at 104,
then consume 104 START pages with distinct sequences and check both exhausted.
Exhausted START also leaves CONFIG usable. Malformed selected pools, no refund
after failures, and CONFIG/START sequence reuse remain covered. The 208-command
synthetic exercise checks accounting only; it does not authorize repeatedly
starting firmware or bypass the caller's legal phase progression.

Payload composition started during the discovery is excluded from this
correction commit. It remains uncommitted pending correction review. The
correction changes no source pins, kernel patches, hardware state or backend.

## Independent source and integration review

The upstream-preparation worker independently audited the pinned gen3 call
sites: `common/wlan_lib.c:2431` selects TC4 for CONFIG and `:2845` selects TC0
for START; `nic/nic_tx.c:260-291` indexes each balance by the selected traffic
class. Its initialization at `:2296-2336` and header arithmetic establish the
two separate 104-page seeds. `nic/nic.c:1025-1041` and
`include/nic/adapter.h:880-884` establish one byte-wide sequence allocator.
This independently confirms credit separation and a common sequence namespace.

Vendor sequence allocation precedes resource acquisition and wraps through
zero. The project's bitmap and refusal-without-consuming-sequence behavior
are deliberate stronger policies under exclusive serialized INIT ownership,
not claims about vendor failure behavior. No 208-command device budget follows
from adding the two balances.

Project Planning preserved prior integration review sections while applying
`ef9c6bf6`. Independent strict C11/ASan/UBSan execution covers CONFIG, START
and connected CONFIG I/O. The source-derived literal oracle now explicitly
checks `(TC4, TC0) = (103, 104)` after CONFIG and rejects CONFIG-to-START
sequence reuse without touching TC0; the reciprocal reuse case and independent
pool depletion are retained. All 17,225 wire comparisons remain passing.
This corrects the host model; hardware and kernel-adapter acceptance remain
separate and no earlier receipt is promoted or rewritten.
