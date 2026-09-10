# Native CONN provider OFF capture

This unselected component implements the kind-9 records in the
[provider contract](PERSISTENT_CAPTURE.md#provider-off-sequence). It observes
one native CONN shutdown. It does not prove that WLAN was the last shared
consumer or admit a new power operation, candidate or recovery sequence.

The [patch](patches/provider-off/0001-clk-capture-native-CONN-provider-shutdown.patch)
and [source receipt](results/provider-off-capture-sources.json) pin the native
provider and its two existing headers, plus the new observation header.
The patch changes the provider file and adds the header; the existing headers
remain unchanged. It is not in the canonical kernel series and its synthetic
archive identity supplies no DCO certification.

## Operation and attribution

`disable_subsys()` owns a stack context. Only the first active capture of
`SYS_CONN` receives provider/invocation ordinal 1. A second attempt closes
observation. A mismatched CONN state/disable callback also closes observation.
The existing internal callbacks accept the context explicitly; non-CONN
callbacks ignore it and state inspection outside shutdown passes null. There
is no global pointer to a callback's stack lifetime.

The entry records the normal, bring-up or control-limit route. For the normal
route, callback presence is recorded in the existing before-off branch. The
state callback records its two existing reads, computed state and consequent
shortcut/dispatch decision. Actual callback dispatch then reaches the CONN
control function with that same context.

After the native key store, capture records its issued value and the protection
request. The locked protection helper retains its original input read, issued
store, verification read and only the reads in its wait condition. Diagnostic
reads remain untouched and excluded from the counters. Verification/count-limit
faults emit a summary before the native BUG. A normal summary is emitted by the
caller after the helper has actually returned, with its returned status.

Each of the five native CONN control updates retains its own input read and
issued store. The OFF loop preserves primary-then-conditional-secondary read
order. The final validity bits describe the last condition evaluation, not an
earlier read. Overflow emits a fault summary and closes observation while the
native loop keeps its original behavior. Compiled-out ACK polling records a
skipped reason. The provider return record contains the inner callback result
and the status selected for return by `disable_subsys()`.

No new hardware read, store, readback, timeout, retry, reset or recovery action
is added. The native protection count limit and fault branches remain intact;
the terminal power-status loop is still unbounded. Nine records occupy 1152
bytes in the successful normal path. Capture adds retained-memory work under
the existing locks; complete stack, lock-duration and recovery budgets remain
unmeasured. Bring-up, control-limit, state shortcut and partial paths cannot
pass the normal provider check.

## Validation and remaining work

`test-provider-off-capture.py PARENT CHANGED` composes the actual provider,
CONN control, protection helper and record writer with injected register,
lock, callback, time and BUG behavior. It compares the native effect sequence
and return value with capture enabled and disabled. Eight paths cover normal
OFF, initially OFF, mixed initial status, verification fault, protection timeout,
before-off callback, control-limit skip and a mismatched callback. Four builds
cover ordinary execution, diagnostic reads, skipped ACK polling and bring-up.
Nine lost-record sites retain an incomplete capture; primary/secondary counter
overflow and a second attempt close observation. Successful normal records pass
`check_provider_off()`, including unequal primary/secondary condition counts.

The fixture's BUG uses a nonlocal exit to preserve the prefix for inspection;
it does not claim recovery from a native kernel BUG. Register values and callback
behavior are injected, not hardware observations. A consistency check of an
individual recorded operation cannot override a rejected overall capture.

`check-startup-objects.py COMMIT --provider-off` composes the prior sixteen
pstore/WLAN/EMI patches and this provider patch in a clean pushed Buildbox
checkout. It compiles eight complete source files and checks the actual patched
provider headers and emitted capture calls. The
[Buildbox receipt](results/provider-off-object-compile.json) records a successful
compile at `89902aad3813b2a06f61a8233c48863ec3df9690`, with the 41-file package
inventory verified remotely and locally. The first attempt compiled all units
but its verifier incorrectly required an inlined static helper name. Only that
verification was corrected; the native patch remained unchanged.

The emitted code retains the indirect state/disable callbacks and stack context,
five control helper calls, and short-circuited primary/secondary OFF condition.
Individual provider, CONN callback and protection-helper frames are 208, 80 and
128 bytes, excluding callers and capture-writer frames. Native compiler flags
retain `-w`; empty diagnostics do not establish warning-clean code. These object
checks establish neither a complete stack budget nor a full kernel link.

CCF/common-owner request attribution, competing-consumer isolation, full kernel
linking, controller/recovery integration and an admitted device test remain
outstanding. No runtime support claim follows from these host checks.
