# First connection-loss teardown: ledger not retired; driver waiter candidate

Offline review of [invalid baseline 1](THROUGHPUT_BASELINE_RESULT.md), distinct
from its SSH idle-policy error. No kernel change, rebuild or device action.

## Sealed observations

The firmware CCMP BSS timeout reason=4 arrived at kmsg time 387.342600 s.
The beacon observation had since_pm=19, age 364290 ms; checked RX age was
143 ms. The driver reported connection loss from its own monitor. This was
the **first end-to-end exercise of the connection-loss path**. Its teardown
**did not retire its ledger**.

After the loss, mask-disable and PM-abort credit returned. Reserved deauth
completed status 0. Pairwise removal op=2/sequence=32 was submitted and
credited; group removal op=3/sequence=33 was submitted successfully, but no
credit was observed before the host fail-stop. The first stop was -110,
first_error=0, debt=1, cleanup=0, branch=8. There is no whole-ledger stage 3.

The terminal credit observation is decisive about the available wait:
now_ns=387474231023, pending=1, credit_deadline_ns=387571152869,
lifetime_deadline_ns=392302823715. The command still had **96.921846 ms** left
at that snapshot. The HIF guard was valid, TC4 free=26, CPU pending=0,
FFA pending=0; no released page was available at that instant. The group
submission log precedes the stop log by 12.498 ms. The worker was retired
before this command's 100 ms credit allowance had been observed to expire.

Therefore the group command was **not withheld** by the host. A short period
without released pages, followed by a host stop, is not proof that the transport
was already unsatisfiable or that firmware refuses commands after BSS timeout.
Pairwise removal's post-loss credit independently rules out a blanket claim
that no key-removal command can be processed after that notification.

## Actual-source candidate, independently reproduced

The retained Buildbox source for the installed private delivery profile was
read without building or modifying it. Its `mac.c` SHA-256 is
`20a29c7a54d6eddd52d15a9e8c2fdfde4f455743a06cf111e2812e472ada8d82`.
`mt6797_ccmp_disable_key()` can wait for an in-flight management frame and
then its credit through `mt6797_mac_join_wait_management()` and
`mt6797_mac_join_wait_credit()`.

The worker clears the shared `join_credit_pending` and completes
`join_credit_done` when the earlier command is credited. Before releasing the
same MAC mutex it can advance cleanup and submit the next command, reinitialize
that completion and set the shared pending flag again. The resumed waiter
tests that shared flag, without an operation identity, and returns -ETIMEDOUT
even though its earlier credit completed and the new deadline is in the future.
The disable callback can then fail-stop the lifetime at branch 8, retaining
the newly charged page.

The [fixture](tests/loss-credit-wait-test.py) extracts and compiles the exact
waiter body from the pinned source. It demonstrates success after the earlier
credit, premature -110 after a next-command interleave, and preservation of an
existing -EPROTO poison. It changes no kernel code. This is a **driver fix
candidate consistent with the trace**, not a captured call stack proving the
exact scheduler interleave in this boot. Correct ownership of the credit being
waited for is the proposed repair boundary; clearing debt, accepting another
command's credit or extending a timeout is not a repair.

## Firmware gates and limits of the answer

Retained key-handler evidence was inspected in the RE VM only. The pinned
CID 0x07 listing has SHA-256
`7da9d74cbb6210c509803000edcdc8b5aac36eb31261ccc7cf26579dc25d3dc1`.
Its entry checks the command shape and selects the per-BSS context; its
add/remove branch uses the payload operation byte. Diagnostic/global-state
branches and indirect callbacks remain explicit in that listing. Those
unresolved callbacks are not evidence for a post-timeout command-drop policy.
The previously recorded dispatcher releases the command page after handler
return; that credit is not a fence for later firmware events.

No new binary decode, firmware command or timing test was used to fill gaps.
There is **no source-proven firmware rule here that drops the group removal
after timeout**. The supported answer is the host waiter candidate and the
observed loss-path limitation: host polling/ownership was retired before the
group credit could be judged over its full allowance. Eventual firmware
consumption and key removal remain unproved. Do not publish a firmware-drop
diagnosis or a healthy cleanup claim.

## Next measurement

The owner requests the installed image, without rebuilding this candidate fix.
The [corrected measurement](THROUGHPUT_BASELINE_2_PREDECLARATION.md) therefore
retains this known loss-path limitation, measures both directions with progress
and independent control keepalives, and disconnects promptly. Any loss/error
stops traffic, preserves evidence and uses the reviewed return; report the
whole-ledger verdict honestly. This is a measurement, not validation of a
loss-path fix. No reconnect, admission, key reuse or dormant safeguard changes.
