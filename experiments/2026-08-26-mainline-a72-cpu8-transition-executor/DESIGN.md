# CPU8 transition coordinator contract

## Entry

The caller must serialize a controller and supply a request that proves:

- the target is CPU8;
- the candidate-specific token matched;
- the platform/provider/protected-clock prefix completed;
- CPU8 and CPU9 are both offline; and
- the controller's atomic one-shot has not already been consumed.

All callbacks are validated before the one-shot is consumed. A bad gate or
incomplete operation table returns without a checkpoint or hardware callback.
The controller uses a construction-time initializer and exposes no reset
function. Its one-shot is consumed before watchdog arming and cannot be reset
through the executor API.

## Ordered stages

Every stage emits a before checkpoint, invokes exactly one injected operation,
and emits an after checkpoint only on success:

1. hardware recovery watchdog arm, fixed at 15 seconds;
2. P27 acquire;
3. provider acquire;
4. isolation-clear attempt;
5. SRAM-LDO enable/verification;
6. one CPU8 CPU_ON request;
7. bounded online wait, fixed at 10 seconds;
8. one CPU8 IPI/accounting proof; and
9. DCM update/readback.

There is deliberately no watchdog-cancel, CPU_OFF, retry, CPU9, device model,
userspace trigger, or physical implementation in this phase.

## Failure boundary

A watchdog-arm failure is a prestate rejection. P27/provider callbacks report
whether they hold exact attempt-owned state even when returning an error.
Before the isolation attempt, exact provider ownership is released first and
exact P27 ownership second. A malformed success without ownership proof or a
release failure is a pre-isolation rollback fault and retains the unresolved
resource for watchdog recovery.

The isolation callback marks the no-guessed-inverse boundary before it runs.
Its failure and every later failure retain P27/provider power, issue no inverse
or retry, and wait for reset recovery. Success retains P27, provider, and CPU8
because no CPU8-off inverse has yet been admitted.

## Evidence

The result records terminal class, last stage, stage and rollback errno,
attempt/watchdog/isolation/online state, exact CPU request/off/retry counts,
checkpoint count, rollback and retained masks, and watchdog identity. The KUnit
fixture also records exact before/effect/after callback order entirely in
memory.

Runtime proof is limited to the exact checksum-validated Buildbox package and
the sole `mt6797-a72-transition-executor` suite. The runner permits no network,
uses a 45-second timeout, and accepts the expected missing-root-filesystem panic
only after all seven exact cases and the suite summary have passed. Its
classifier mutation test rejects a failed case, extra suite, renamed case,
changed totals or plan, missing post-test panic, wrong kernel release, and
wrong QEMU exit status.
