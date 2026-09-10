# Retain resources after incomplete WLAN removal

The unselected [patch](patches/remove-retain/0001-wlan-retain-resources-after-incomplete-removal.patch)
prevents the selected built-in MT6797 AHB OFF path from releasing resources
when WLAN removal cannot establish its native completion conditions. It follows
the 28-patch [removal-wait composition](STOP_HOOKS.md#removal-wait-witness).
The [source receipt](results/remove-retain-sources.json) pins four changed
parent/output files and three baseline fixture inputs. No canonical profile
selects this patch. Its archive identity is synthetic, without DCO certification.

## Failure path and change

The native path has three separate loss points. `wlanRemove()` continues into
adapter cleanup after a failed halt-lock acquisition or worker wait. Its
`remove_card` callback type has no return value, so `HifAhbRemove()` always
continues to the WLAN power-control call and returns zero. Even when a subsystem
callback reports an error, `opfunc_func_off()` clears its state and can power
down common CONSYS. The earlier error-preservation patch fixes the final return
value, but deliberately preserves those cleanup effects.

The new patch changes the complete selected error path:

- `wlanRemove()` returns the halt-lock error before changing halt state or
  waiting for workers; it neither completes another caller's OID nor unlocks
  a semaphore it did not acquire. Capture is aborted on this branch.
- With the lock acquired, the existing three waits and timeout diagnostics run.
  Their existing summary is recorded. Any failed selected wait aborts capture,
  releases the acquired halt lock and returns `-ETIMEDOUT` before thread-pointer
  clearing, adapter cleanup, IRQ release or netdev destruction.
- Missing adapter bookkeeping returns `-ENODEV`. A missing glue pointer no
  longer causes an unproven early `free_netdev()`.
- The internal `remove_card` callback returns `INT_32`. `HifAhbRemove()` passes
  a nonzero return upward before its WLAN power-control operation.
- WMT retains the Wi-Fi state on a failed or unavailable Wi-Fi OFF callback.
  It skips the UART-associated SDIO slot shutdown and common power-off on that
  path. Other subsystem callback-error behavior is unchanged.

The ordinary successful path retains the existing calls and state transitions.
No new wait, cancellation, reset, hardware access or cleanup attempt is added.
Earlier removal bookkeeping, such as performance-monitor destruction and work
flushing, is not rolled back. A retained failure is terminal for this experiment:
no retry, reinitialization or continued networking is selected. Resources remain
for an independently admitted recovery owner; this patch is not that recovery
mechanism. Concurrent reset, probe-failure cleanup, module unload and other HIF
variants remain outside the validated contract. In particular, it does not
make a void bus-unregister path capable of refusing module unload.

## Completion-tail correction

The source review initially treated `prGlueInfo->prAdapter` in the post-completion
wake-lock macros as an evaluated adapter access. The baseline `gl_kal.h`
definitions at 407-420 discard that argument. The three wake locks are local
to their worker functions; the final cleanup calls use those local objects.
The fixture compiles the exact tails after `complete()` with the actual enabled
macro definitions and deliberately supplies no `prGlueInfo` declaration. All
three tails compile and execute their injected wake-lock cleanup. A surviving
adapter expression would fail compilation.

Thus the trailing wake-lock calls are not evidence of adapter use after native
completion. They also do not establish that the kernel task has exited, or
exclude other callers of the adapter. No completion-order patch is justified
by this review. The timeout path remains a real resource-retention problem
because no worker completion was observed on that path.

## Validation and limits

The [native call-chain fixture](test-remove-retain.py) compiles actual parent
and child `wlanRemove()`, `HifAhbRemove()`, `wmt_func_wifi_off()`,
`opfunc_func_off()` and `opfunc_pwr_off()` bodies. It injects worker completions,
locks, hardware, adapter teardown and capture helpers. Ancillary P2P, BoW,
AGPS and proc branches are not enabled in this fixture. It does not execute
worker bodies, the scheduler, actual frees, reset or recovery.

432 comparisons cover every three-worker timeout combination, halt-lock
failures, normal and UART common routes, missing bookkeeping/callbacks,
positive callback errors, capture enabled/disabled and an unrelated subsystem
error. All 380 failure cases retain adapter state and avoid the selected
resource-release calls. Successful and unrelated-subsystem sequences retain
the parent effects. Host compilation uses `-Wall -Wextra -Werror`, with explicit
unused-parameter/function/assigned-variable exceptions for native bodies and
injected stubs. The separate completion-tail compilation needs no exceptions.
Strict Checkpatch passes with the established `CAMELCASE` and synthetic
`MISSING_SIGN_OFF` exceptions. Patch replay and reversal match the pinned files.

`check-startup-objects.py COMMIT --remove-retain` selects 29 patches and 19
native translation units on Buildbox, verifies source pins and the overridden
callback-type header dependency, and runs the actual-function fixtures.
Native compilation is pending. There is no full kernel link, boot candidate,
new hardware observation or device admission.
