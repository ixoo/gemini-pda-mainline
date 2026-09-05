# C WIFI_START validation and readiness boundary

Credit correction: [CONFIG uses TC4; START uses TC0](INIT_CREDIT_CORRECTION.md).
Earlier shared-credit/TC0-CONFIG claims below are superseded; historical
validation receipts are preserved and do not validate the corrected pools.

The [existing C INIT header](src/hif_init_transaction.h) now includes
`mt6797_init_validate_start`, `mt6797_start_begin`,
`mt6797_start_submitted` and `mt6797_start_observe_ready`. These implement
the already-established [WIFI_START constructor contract](WIFI_START.md)
alongside the [CONFIG state boundary](INIT_TRANSACTION_C.md). The shared
transaction owns separate CONFIG/TC4 and START/TC0 credit counts, plus one
consumed-sequence bitmap for both command kinds; no generic transport interface is added.

The validator requires exactly 16 logical bytes, count 16, queue `0x8000`,
command 2, type `0xa0`, zero reserved byte, independently expected sequence
0–255 and override word zero or one. All address values remain
uninterpreted; accepting the record does not admit the address for execution.
Delay-calibration and other override bits remain outside this constructor
scope. This matches the Python decoder, including its broader coverage of
both constructor branches while the selected MT6797 call uses override off.

START begin validates, refuses prior sequence use, debits one INIT page and
enters START_DISPATCH. Successful finite PIO submission enters START_READY;
it does not report WLAN readiness. An uncertain submission poisons the
transaction with no refund. CONFIG-specific submission/reply methods refuse
START phases and poison the transaction; a CMD_RESULT cannot complete START.

`mt6797_start_observe_ready` accepts an attributable caller-provided WCIR
value only in START_READY. Source `mt6630_reg.h` defines WLAN_READY as bit 21;
the already-audited startup path polls this bit after sending START. The
header belongs to the [existing pinned PIO ledger](results/pio-sources.json)
at Planet `c5b0be85017ad0c599725e8273842efdbecdd88a`. No register address or
MMIO read is introduced. A clear bit returns `-EAGAIN`; a set bit returns to
IDLE with the credit still consumed and sequence still marked used.

The bit test is the source's level predicate, not a proof of a new transition
or command causality. The caller must supply a fresh observation in the
same owned firmware session after successful submission, enforce a finite
deadline and call `mt6797_init_abort` on timeout, ownership/session loss or
failed status read. Supplying a cached observation is outside this contract.
No clear-before-start rule is invented. Premature/duplicate observations or
submission notifications poison state, and POISONED cannot be revived by a
later ready bit. There is no ACK, retry, refund or transparent reset.

This remains an INIT control component. Returning to IDLE does not authorize
another boot phase, another START or post-start CONFIG merely because a new
sequence and credit are available. The caller owns legal firmware-phase
progression and resource lifetime, as with the existing CONFIG boundary.

The [focused C fixture](src/hif_start_transaction_test.c) tests CONFIG then
START, independent credits and shared sequence history, readiness pending/success, failed TX,
early observation, wrong ACK, duplicate submission, timeout/owner failure,
poison persistence, malformed command/credit state and exhaustion. Both
START and existing CONFIG state fixtures pass strict C11 warnings and
ASan/UBSan. The expanded [Python/C cross-check](scripts/test_init_c_crosscheck.py)
passes 17,225 comparisons across CONFIG, CMD_RESULT and WIFI_START: every
single-byte mutation, truncation/tail and expected sequence 0–256. The
existing Python fixtures remain independent inputs.

Kernel integration remains uncompiled. No polling, device/backend access,
raw evidence, firmware address permission or active driver claim is added.

## Integration review

Project Planning independently reviewed the six-file `3f3a1988` delta and ran
both C state fixtures with strict C11 warnings and ASan/UBSan. All 17,225
Python/C wire comparisons passed. The integrated repository gate passed all
192 profile checks with unchanged metadata debt of 37; its Linux-only artifact
fixture remains delegated to CI. These checks establish host-side protocol
logic only. Kernel adapter compilation, firmware loading and device usability
remain unproven. No device or backend action was part of this review.
