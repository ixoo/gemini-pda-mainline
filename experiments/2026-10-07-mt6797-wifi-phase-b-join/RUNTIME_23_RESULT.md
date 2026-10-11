# Runtime 23 result: negative, the pairwise key command refused by the driver's own credit wait

Boot: mainline `e9db919c-a0ed-45b5-ab8d-e345d8f6b9eb` on candidate 22 (compile 27,
package `d1cbc042…`, boot2 `419797dd…`), session tools at c234187b, launched by the
custodian after deployment 22 (predecessor candidate 21 `79cde346…`, stock boot
`720fcced…`). Evidence: the custodian's sanitized uploads (join diagnostic records,
log, supplicant-log, session, native-request and Wi-Fi SSH results, body fields);
kernel log sealed complete (154647 bytes, 2029 records, SHA-256 `f73e5247…`);
supplicant log exported (25233 bytes) but not complete, one process still alive. No
raw log, address, body or identifier is published.

## Observed

- Phase A: common init 285/285, calibration task 4, ready for scan; the scan ran.
- Join: authentication and association (status 0) exchanged and acknowledged; two
  clear broadcast Action frames of the runtime 21 class discarded and recorded
  (counts 1 and 2; proposal 0168 observed on hardware); no group-data discard
  (the 0169 class unobserved in this boot); message 1 delivered (tag 15), message 2
  sent and acknowledged, message 3 delivered (tag 1).
- The pairwise key command submitted (sequence 25); one credit of one page returned
  7.9 ms later; message 4 sent 1.1 ms after that (pid 4, 2 pages); the first
  add-key-done event recorded 1.1 ms after that; then the pairwise command refused
  with status -110 while the lifetime was running, 11.5 ms after submission (kernel
  timestamps: command, credit, message 4, key-done, refusal), and the group command
  refused -95 with the lifetime stopped. No TX done for message 4, no stopped
  footer, no cleanup or removal record before the seal. The credit's attribution
  to the command is by order only.
- Host: the join phase's SSH session exited 255 after 60.7 s with the device script
  still waiting; the framed result was never produced (userspace transport
  incomplete, body unframed); the Wi-Fi SSH check saw no readiness marker (92 s) and
  attempted nothing. Verdicts: bounded join, handshake and data false; C2 false;
  C3 false; the classifier reports the run malformed (no terminal record, pairwise
  completion incomplete) with a refusal recorded; `group_action_frame_discards` 2,
  `group_data_discard_records` 0. These host verdicts stand as computed.
- Not firmware evidence: the supplicant's CONNECTED and DISCONNECTED (one each) are
  its own state, not key installation; the one-page credit after the command is
  attributed to the command by order only.

## Diagnosis (source, not hardware proof)

Two defects of the driver at 85cbc78f, both reproduced by fixtures:

1. The key command's credit wait tested the shared page debt after waking. The
   worker clears the command's pending flag when its page returns and, in the same
   iteration, submits the queued message 4 and recharges the debt for it; the waiter
   then saw a debt that was the frame's and returned -ETIMEDOUT although the credit
   had returned in time. Runtimes 20 to 22 did not meet this ordering because
   message 4 had already gone out when the key arrived.
2. The refusal path retired the lifetime directly, without the worker's footer or
   discard: no terminal record, the frame in flight never completed, the device
   script waited for a record that could not come, and the USB listener's 60 s idle
   timeout closed the session.

## Not observed and not claimed

Nothing about the firmware's key handling, add-key-done semantics, or the executing
image follows from this run; the add-key-done event is attributed by order only. No
network function, no replay protection, no operational claim.

## Recovery

One native recovery was requested after the evidence was sealed; the collector
confirmed a changed-identity stock boot `89d49b95-ddf6-4cba-b38a-81311ff6bc4a` on its
fourth attempt after 45.7 s, with recovery, regression and session verification
true. One request only. The installed boot2 remains candidate 22 (`419797dd…`).

## Decision

Proposal 0170: the credit waiter owns exactly its pending credit (the worker's
cleared flag) and no longer consults the shared page debt; a key command refused
while the lifetime runs ends it through the worker's fail-stop (footer with that
status, discard, waiters completed) instead of retiring directly. The classifier
closes a submitted command's accounting on its running refusal. The device script
prints one keepalive line every 20 ticks so the USB listener's idle timeout cannot
close the join phase during the 100 s wait. Compile 28 follows the custodian's
source review; a candidate and one boot follow after that. No repeat of
candidate 22.
