# Preserve native common shutdown errors

The native common shutdown path can report success after a failed teardown.
In `opfunc_func_off()`, the subsystem callback result is overwritten by
`opfunc_pwr_off()` when the seven software consumer states permit common OFF.
Within `opfunc_pwr_off()`, the hardware-control result overwrites an earlier
`wmt_core_stp_deinit()` failure. A zero return from the last operation can
therefore erase the error that should stop the proposed controller's normal
cycle. The same masking can hide the missing-subsystem-callback error.

The [patch](patches/common-off-errors/0001-wmt-preserve-common-shutdown-errors.patch)
preserves the first nonzero result across these two boundaries. It still runs
the existing teardown and common power-off sequence, including native state
assignments and shortcut behavior. Later failures retain their diagnostics;
the first failure is returned. The [source receipt](results/common-off-errors-sources.json)
pins the complete parent and changed `wmt_core.c` and verifies patch replay
and reversal after the existing single-startup-attempt patch on public Gemian
revision `59e00a9144d782e148332009a835b99c43382467`. The first Buildbox attempt
refused the original receipt's unpatched baseline hash at this composition
boundary. Regenerating against the actual parent preserves the same two
shutdown-function edits and the earlier startup correction.

This is an unselected native experiment correction. It changes no canonical
series or device candidate and supplies no DCO certification. The planned
controller uses the [direct WMT ioctl route](CYCLE_CONTROL.md#controller-route-and-operation-timeout);
other wrappers' reactions to a newly visible failure are not admitted by this
patch. In particular, it is not permission to run a wrapper with reset/retry
behavior after an error.

## Validation

`test-common-off-errors.py PARENT CHANGED` compiles the actual two functions
with injected subsystem, STP and hardware-control calls. Its 297 cases cover
zero, negative and positive results, first-error precedence, active competing
consumer, missing callback, already-off and blocked common states, common
POWER_ON without STP deinit, invalid type/state, UART cleanup and loopback.
The original produces 37 false-success results across these cases; the fix
preserves all injected cleanup call sequences and final software states.
The fixture treats diagnostic assertions as returning and does not model
kernel concurrency, actual teardown or provider effects.

The host compiler used `-Wall -Wextra -Werror`, with an unused-parameter
exception for native callback signatures. Strict Checkpatch passes with
explicit legacy `CAMELCASE` and synthetic `MISSING_SIGN_OFF` exceptions.
The compile reproduction path is `check-startup-objects.py COMMIT --common-off-safe`
on a clean pushed Buildbox checkout. It composes the four existing startup
patches and this correction and compiles five complete native source files.
The [Buildbox receipt](results/common-off-errors-object-compile.json) records
successful compilation at `5a713c73d75e53cf49be6cd932371c74b338dbf1`; its
24-file package inventory passed remote and local checksum checks. Inspection
of the emitted code confirms both earlier results survive the later calls
and are selected when nonzero. The baseline objects use the original source;
the host regression instead compares the actual four-patch parent and child.
Native compiler flags include `-w`, so empty diagnostics are not a
warning-clean result. No complete kernel was linked.

A successful return remains insufficient: existing shortcuts, software-only
consumer states, lower-layer discarded results and the void CCF wrapper remain.
This fix does not supply common-owner attribution, consumer isolation,
successful firmware stop, DMA quiescence or coherent provider OFF. Those need
their actual observations joined to the controller request. No hardware action
or recovery test was performed.
