# WMT operation ownership after reset completion

The [two-file correction](patches/operation-ownership/0001-wmt-retain-worker-ownership-after-reset-completion.patch)
repairs the [reproduced waiter/reset race](CYCLE_CONTROL.md#reset-completion-is-not-worker-completion)
in the selected native experiment. A reset notification can end the caller's
wait while the worker still uses the operation. A successful wait therefore
cannot transfer the worker's ownership back to the free pool.

## Lifetime and result handling

One private metadata entry per existing WMT pool object tracks its reference
count and whether reset signaled it. The shared OSAL layout is unchanged.
The caller owns one reference after allocation. Submission acquires a second
reference before active-queue publication; the queue transfers that reference
to either the worker or the reset queue drainer. Failed queue insertion drops
only the unpublished queue reference, followed by ordinary caller cleanup.

Worker or queue-drain completion publishes its result, clears a matching
current-operation pointer and signals a waiting caller, then drops its own
reference. Reset signaling holds the same mutex while locating the current
operation, marking its error sticky and waking the caller. It drops no
reference. Later worker completion preserves that error. The waiter reads its
result under this mutex and releases only its caller reference. The pool sees
the operation again only after both owners release it.

Asynchronous submission releases the caller reference while leaving queue or
worker ownership intact. The earlier timeout policy remains: a nonpositive
wait deliberately retains the caller reference, including after eventual
worker completion. This is a bounded experiment retention policy, not an
indefinite-service reclamation scheme. The first failed cycle ends normal
requests; library reinitialization remains outside the admitted experiment.

The private mutex covers only ownership metadata, current-pointer access and
result/signal publication. It is never held across a core operation, native
reset step, signal wait or free/active queue operation. Pool insertion happens
after the mutex is released. Native completion signaling can wake a waiter
that subsequently takes the mutex; it does not wait for that waiter.
The queued or running reference keeps the current operation alive during
reset inspection. The native test-reset function check now snapshots its
answer under the same mutex instead of borrowing an unprotected pointer.

The worker saves its EXIT opcode before completion can release its reference.
The selected function-control wrapper uses its request parameters for final
logging, avoiding access to a recycled operation. This log now reports the
requested type, including when the optional AUTOK mapping changes the internal
operation type to Wi-Fi.

## Limits

This is software ownership repair, not reset exclusion or a complete cycle
verdict. The original hardware/software reset calls and retry policy remain.
The worker's reset-state admission check is unchanged; reset may race with
core entry. A reset that does not signal this current operation is not recorded
by its sticky bit. The future capture must independently invalidate the entire
request on a competing reset and establish resource isolation.

Other native debug and loopback callers still inspect operation fields after
`wmt_lib_put_act_op()` has released caller ownership. Their existing interfaces
are not admitted by this correction. The unused native raw current-pointer
getter also remains; the reviewed reset paths no longer call it. This patch
supplies no new public operation API, controller, capture join, kernel profile,
boot candidate or runtime support claim.

## Validation

The [source receipt](results/operation-ownership-sources.json) pins the public
parent after the existing reply and timeout corrections, the two outputs and
format-patch replay/reversal. The patch is outside the canonical series and
uses a synthetic, non-certifying experiment identity.

`test-operation-ownership.py CHANGED_WMT_LIB` compiles actual ownership helpers,
worker, waiter, allocation, release and queue-drain functions with pthread
mutexes and directed injected scheduling. Thirteen cases cover normal success,
worker failure, both reset/worker/waiter orderings, asynchronous submission,
zero and negative waits, EXIT, insertion refusal, coredump blocking, explicit
release, and synchronous/asynchronous queue draining. A second pool object
checks that unrelated allocation cannot obtain the still-owned operation.
The test validates the source digest and reset helper call placement.

All thirteen cases pass with `-std=c11 -Wall -Wextra -Werror -pthread`.
The original ten-case waiter test still reproduces the pre-correction faults.
Strict Checkpatch passes with only legacy `CAMELCASE` and synthetic
`MISSING_SIGN_OFF` exceptions. These tests execute no kernel scheduler,
completion implementation, reset machinery or hardware operation.

`check-startup-objects.py COMMIT --operation-ownership` composes all 24 patches
and includes the complete `wmt_exp.c` alongside the previous fourteen units.
The [Buildbox receipt](results/operation-ownership-object-compile.json) records
successful compilation at `5a63e161522f463c7a9be3f69dfe6b602f8d8bde`, with
source-boundary and native header-dependency checks and exact remote/local
validation of all 73 package files. Emitted code retains the queue reference
before publication, sticky reset error, locked result read and separate worker
release. Native compile flags include `-w`; this is not warning-clean evidence.
Full kernel linking, lock/timing budgets and device admission remain separate.
