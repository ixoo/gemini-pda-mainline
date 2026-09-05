# Connected CONFIG request/ACK phase

Credit correction: [CONFIG uses TC4; START uses TC0](INIT_CREDIT_CORRECTION.md).
Earlier shared-credit/TC0-CONFIG claims below are superseded; historical
validation receipts are preserved and do not validate the corrected pools.

[`hif_config_phase.h`](src/hif_config_phase.h) is the first connected
firmware-download phase: validated CONFIG, credit debit, actual finite PIO
submission, response-length admission, PIO receive and matching ACK acceptance.
It composes the existing components instead of adding another validator or
transport framework. It intentionally stops at successful section
configuration; it does not claim to download the payload or start firmware.

## Confirmed ordering, chunk and credit rules

The [three rechecked public sources](results/config-phase-sources.json) use
Planet `c5b0be85017ad0c599725e8273842efdbecdd88a`, selected gen3.
`wlanImageSectionDownloadStage` calls CONFIG first and only enters its
payload loop on success. `CFG_ENABLE_FW_DOWNLOAD_ACK=1` selects CONFIG ACK
checking. `CMD_PKT_SIZE_FOR_IMAGE` in `include/nic/hif_tx.h:50` is 2048 payload
bytes. Each ordinary download section is divided into chunks no larger than
that, with an eight-byte PDA header and queue `0xc000`, CID zero, type `0xa0`
and sequence zero. The payload helper goes directly to `nicTxInitCmd`; it
does **not** acquire TC0 credit or wait for a per-chunk ACK. The no-download-ACK
query-pending-error branch is not the selected policy. START follows the
overall download stage and uses readiness rather than a CMD_RESULT ACK.

Thus extending the CONFIG credit/sequence/ACK state over each PDA chunk
would be incorrect. Conversely, source absence of a debit in that helper
does not authorize manufacturing credits in a new live transport. The
selected MT6797 image also has separately handled EMI sections, so a single
CONFIG ACK cannot authorize START or stand in for all required section work.
This bounded implementation completes the CONFIG phase without pretending
those later phase adapters already exist.

## Concrete call boundary

`mt6797_config_send` checks idle state, both scalar I/O callbacks and the
command before dispatch. It copies the validated 20 bytes into fixed stack
staging, calls the accepted CONFIG/TC4 transaction begin/debit, submits through the
accepted PIO primitive, and records its outcome. A zero return means
submitted and waiting for a reply, not section configuration success.
The copy ensures the submitted bytes are the validated bytes within this
call; caller input must remain stable during validation/copy.

The caller performs its bounded, session-attributed WRPLR port-0 wait and
calls `mt6797_config_receive`. Length zero returns `-EAGAIN` with no I/O.
Length 28 causes one setup plus eight reads into fixed 32-byte staging,
then validates only the first 28 bytes with the outstanding sequence. A
matching status-zero return completes the CONFIG phase. Diagnostic and extra
read bytes do not escape as raw output. No function re-reads the length,
polls, retries, refunds or searches past an unexpected event.

Each reported I/O failure after admission poisons state; partial replies are
never validated. Unexpected length, stale/failed reply or duplicate receive
also poisons it. The caller calls the existing abort on deadline expiry or
ownership loss; subsequent receive makes no I/O. A bad pre-dispatch command
or exhausted credit makes no I/O and does not debit. The established
caller-held power, ownership and serialization contract applies across both
calls, including the wait. This split puts the real timed wait in the future
kernel adapter without inventing another callback or unbounded loop.

## Kernel adapter dependencies still required

| Dependency | Required integration behavior |
| --- | --- |
| Powered HIF mapping and lifecycle owner | Supply ordered scalar I/O callbacks and hold resources across send/wait/receive; exclude reset and firmware-own release. |
| Shared setup/data access | Serialize with register commands and other FIFO consumers; implement the reviewed interrupt/status ordering. |
| Phase/session admission | Establish exact firmware/image applicability, fresh INIT credit seed and expected sequence; prevent stale RX data from being attributed to this request. |
| Timed port-length wait | Read WRPLR through the selected logical register path, enforce a monotonic deadline, abort on ownership/read failure and pass only port-0 length. |
| Payload phase | Connect separately validated image sections to the selected PDA framing/chunk path; preserve its distinct no-per-chunk-ACK behavior and resolve its transport admission without invented CONFIG debit. |
| EMI and final START | Complete selected EMI ownership/download handling and all ordinary sections before using the existing START/readiness boundary. |
| Failure lifecycle | Preserve uncertainty, forbid automatic replay/refund, and use an independently reviewed recovery/teardown path. |

## Fake-transport integration result

The [fixture](src/hif_config_phase_test.c) runs the real encoder, credit
debit, PIO primitive and C transaction validator together. Literal expected
TX words match the existing Python CONFIG fixture; the fake response uses
its 28-byte layout with intentionally nonzero diagnostics and extra tail.
The complete success flow is six TX operations followed by one RX setup
and eight data reads. Zero-length waiting makes no access. Tests fail every
one of those 15 operations individually and require immediate exit, poison
and no refund; they also cover stale/failed reply, bad length, deadline abort,
duplicate receive, malformed request, sequence mismatch and exhausted credit.
Strict C11 warnings and ASan/UBSan pass. This is host-tested composition, not
usable Wi-Fi or a kernel build. No device/backend action or feature push occurs.

## Coordinator integration review

Project Planning reviewed the complete five-file `a27fab0e` delta and its
composition with the previously accepted PIO and INIT transaction interfaces.
Independent strict C11/ASan/UBSan execution passed the complete request/ACK
flow and all 15 individual I/O failure positions. All three public source
files were independently fetched in memory and matched the recorded lengths
and SHA-256 identities. The integrated repository gate covers 192 profiles
with unchanged metadata debt of 37; the worker's 189-profile record remains
its historical scope. This accepts host-side composition only; timed register
waiting, ordinary payloads, EMI handling and a compiled kernel adapter remain
unfinished, and no live Wi-Fi capability follows from these checks.
