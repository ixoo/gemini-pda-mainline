# Synchronous common OFF attribution

The [patch](patches/common-off/0001-wmt-bind-common-OFF-to-native-CONN-provider.patch)
joins one native `opfunc_func_off()` common-power call to the actual CCF clock
object and CONN provider observation. This closes the previously missing
synchronous attribution between those sites. It does not yet join the worker
operation to the outer userspace ioctl or establish competing-consumer isolation.

The [source receipt](results/common-off-capture-sources.json) pins the composed
parent after the [shutdown-error correction](COMMON_OFF_ERRORS.md) and
[provider capture](PROVIDER_OFF_HOOKS.md), plus the original MT6797 common
hardware wrapper. Patch replay and reversal are checked. The patch is unselected,
outside the canonical kernel series, with a synthetic non-certifying author.

## Scope and native operations

The common scope starts in the existing all-consumers-off branch of
`opfunc_func_off()`, immediately before `opfunc_pwr_off()`. It records the
requested native function type and the earlier subsystem callback result.
Only native Wi-Fi type 3 with a zero callback result can pass the checker.
The scope ends after the existing result selection, recording the common-power
result and the selected function-off result. The software status condition is
not a coherent hardware ownership observation: its reads are short-circuited,
and native state assignments can mark a failed subsystem OFF.

The two existing CCF branches of `mtk_wcn_consys_hw_reg_ctrl()` bracket their
original `clk_disable_unprepare(clk_scp_conn_main)` call. Capture compares the
software clock's `__clk_get_hw()` result with the `hw` actually passed to
`pg_unprepare()`, and requires `SYS_CONN`. The existing provider context must
bind inside that callback. Callback return is recorded after the existing
pre-clock release; clock return is recorded only after the original CCF call.
The native clock reference counts, dispatch decisions and operations are intact.

A small global scope is needed because the CCF callback does not accept an
observer argument. Its calling-task and clock-hardware pointers are only
compared under a raw spinlock and neither is encoded. One task reference
prevents address reuse if the caller dies mid-scope. Normal completion releases
it while the matching current task is still live, so this cannot be its last
reference. A failed or incomplete scope retains at most that one reference
until recovery; it cannot start another scope or take another reference.
The clock pointer is cleared on completion or failure, and the original clock
consumer owns the passed clock lifetime. There is no borrowed stack pointer,
asynchronous observer worker, ownership transfer or scope reset/retry API.

The scope lock protects only bookkeeping and bounded capture appends. It is
released before every original native call. The added nesting is existing
caller locks, scope lock, then the pstore capture lock; the writer has no call
back into the scope. A foreign task, wrong clock, missing provider callback,
direct provider bypass, nested/repeated scope or unexpected stage fails capture.
All original native operations continue; capture does not repair a failed or
stalled shutdown. Non-CONN provider callbacks are outside this attribution
check and cannot substitute for the matching CONN callback.

No new hardware access, timeout, recovery or power operation is added. Additional
software checks, locking and retained-memory writes have unmeasured latency.
Complete stack, lock-duration and recovery budgets remain admission work.

## Records and checks

Kind 10 assigns common-scope subtypes 1–6. All fields are little-endian `u32`
except signed status fields. The producer uses common and invocation ordinal 1
for its single allowed scope; no kernel address or process identifier is stored.

| Subtype | Fields, including subtype |
| --- | --- |
| 1 | subtype, common ordinal, native function type, subsystem status `s32` |
| 2 | subtype, common ordinal, clock hardware present (1) |
| 3 | subtype, common ordinal, native subsystem ID, clock hardware matched (1) |
| 4 | subtype, common ordinal; provider callback returned |
| 5 | subtype, common ordinal; native clock call returned |
| 6 | subtype, common ordinal, common-power status `s32`, selected function-off status `s32` |

`check_common_off()` requires subtypes 1,2,3, the complete nine-record provider
operation, then subtypes 4,5,6. Common, provider and invocation ordinals must
agree, both identity predicates must be true and all recorded results zero.
It rejects a failed producer terminal. A complete scope within a retained
prefix remains an operation-level result, not proof of a completed capture or
cycle. The pmsg reader and rejected-access tail checks remain required.

Six added records consume 768 bytes; the combined provider/common sequence
uses 15 records, or 1,920 bytes. Other lifecycle records consume separate slots.
Kind 10 framing remains opaque to the general framing decoder; only this
typed checker interprets these subtypes. Broader isolation payloads are still
unimplemented and cannot be inferred from this scope.

## Validation

`test-common-off-capture.py PARENT CHANGED` executes the actual provider,
protection, CONN control and CCF callback functions with injected clock dispatch
and task identity. Eight provider paths, fifteen scope faults and fifteen
lost-record sites preserve native effects and returned values. Record mutations
reject malformed, missing and mismatched common records, plus an independently
valid provider moved outside or renamed away from its scope. Another 297 cases
execute the actual parent/changed common shutdown functions with injected
cleanup operations, checking scope placement and unchanged cleanup/results.
The injected CCF dispatcher is not execution of the complete CCF core, and
task substitution is not a kernel concurrency test.

The host tests and 22 existing decoder groups pass. Strict Checkpatch passes
with legacy `CAMELCASE`, synthetic `MISSING_SIGN_OFF` and new-file
`FILE_PATH_CHANGES` exceptions. `check-startup-objects.py COMMIT --common-off`
composes all 23 patches and compiles fourteen complete source files on a clean
pushed Buildbox checkout. The [Buildbox receipt](results/common-off-capture-object-compile.json) records
successful compilation at `8eff6a81974f742fed433e865a255ca289b6d57f` and exact
remote/local validation of all 67 package files. Emitted code retains the
common-call and clock-call brackets, provider completion after pre-clock release,
and task reference acquisition plus completion-only release. Native compiler
flags include `-w`, so empty diagnostics do not establish warning-clean code.
No full kernel link, live controller, candidate or hardware test is established.
