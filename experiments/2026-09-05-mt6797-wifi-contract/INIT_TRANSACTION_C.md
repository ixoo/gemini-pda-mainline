# C CONFIG transaction boundary

Credit correction: [CONFIG uses TC4; START uses TC0](INIT_CREDIT_CORRECTION.md).
Earlier shared-credit/TC0-CONFIG claims below are superseded; historical
validation receipts are preserved and do not validate the corrected pools.

[`hif_init_transaction.h`](src/hif_init_transaction.h) connects the existing
[INIT wire contract](INIT_PROTOCOL.md), [page debit/RX span](INIT_CREDITS_RX.md)
and [finite PIO primitive](HIF_PIO.md) without implementing transport discovery,
MMIO, polling or recovery. It is original GPL-2.0-only C suitable for a future
kernel adapter. No vendor implementation is copied. Public source attribution
remains the earlier INIT protocol and bounds ledgers.

`mt6797_init_validate_result` accepts exactly 28 logical bytes, declared
length 28, packet type `0xe000`, event 1 and an independently expected sequence
in 0–255. Status zero succeeds; nonzero status returns `-EIO` with the firmware
status byte. Malformed records return `-EPROTO`, invalid pointers/sequence
return `-EINVAL`. Reserved/diagnostic fields remain uninterpreted and do not
become invented refusal gates. Status output is cleared before validation.
Never pass the 32-byte RX staging span as the logical record.

The CONFIG validator enforces the existing Python model's exact 20-byte
header, expected sequence, constructor mode/ACK rules, nonzero section size
and non-wrapping 32-bit destination interval. An interval ending exactly at
2^32 is allowed, matching the Python model. No destination permission or
firmware authenticity is inferred.

## Adapter call sequence

The caller zero-initializes one transaction and sets CONFIG/TC4 `free_pages` from proven
fresh INIT admission. It holds ownership, resource lifetime, session identity
and a lock serializing every state call. The packet and structures must be
valid, distinct and stable for each call. After begin, the caller must submit
the same validated immutable command; the state retains scalars, not a
command copy or identity verifier.

1. `mt6797_init_begin` validates CONFIG with the independently supplied
   sequence, refuses reuse, debits one page and enters DISPATCH. Malformed
   command or exhausted credit refuses before debit/dispatch. A reentrant
   begin, malformed state or consumed sequence poisons the transaction.
2. Invoke the finite PIO primitive for that command. Pass its result to
   `mt6797_init_submitted`. Zero enters REPLY, not IDLE/success. Any uncertain
   or failed submission poisons the transaction without refund.
3. Under the caller's finite monotonic deadline, feed port-0 reported length
   to `mt6797_init_prepare_reply`. Zero length returns `-EAGAIN` without
   changing REPLY; malformed length/capacity poisons it. A valid result gives
   the accepted 32-byte staging span. Perform the bounded PIO read and call
   `mt6797_init_abort` on any uncertain read outcome.
4. After a successful read, call `mt6797_init_accept_reply` with exactly the
   first 28 bytes and a status output. Only matching status-zero returns to
   IDLE. Malformed, stale, failed, premature or duplicate replies poison the
   transaction. There is no scan past another event or fallback format.
5. Deadline expiry, ownership/session generation change or caller failure
   calls `mt6797_init_abort`. POISONED is permanent for this object. Do not
   recreate it to erase sequence history, uncertain credits or pending data.

All deadlines and generation observations belong to the existing owner;
this boundary does not read time or turn missing observations into success.
Its 32-byte sequence bitmap prevents reuse within the session. Without credit
replenishment the accepted 104-page seed permits at most 104 CONFIG debits.
There is no refund/reset API; a successful ACK does not restore credits.
The caller may not mutate bookkeeping to bypass these constraints. A fresh
session needs independently established recovery, not another constructor.

## Validation

The [C fixture](src/hif_init_transaction_test.c) passes strict C11 warnings
and address/undefined sanitizers. It exercises submit-versus-reply separation,
zero-length pending response, exact RX span, stale/nonzero/truncated/padded
reply poisoning, early reply, failed submission, timeout/owner abort,
malformed capacity, sequence reuse, malformed credit state and 104-credit
exhaustion without refund.

The [differential test](scripts/test_init_c_crosscheck.py) loads an explicitly
built local test library and reuses the existing Python synthetic `command`
and `result` fixtures. It compares 12,854 outcomes: every single-byte value
at every command/result position, truncations, extra tails and expected
sequences 0–256. Both validators agree on success, well-formed firmware
failure and refusal. The library is a test artifact only, built without
sanitizers for loading into the host Python process; the state fixture runs
separately with sanitizers. Temporary binaries are removed on exit. On macOS
use `-dynamiclib`; a Linux host would use `-shared -fPIC` for this test seam.

Kernel includes/adapter integration remain uncompiled. Runtime protocol
applicability, resource/ownership admission, credit replenishment and recovery
remain explicit adapter requirements. This component adds no device/backend
action and no claim of active driver readiness.
