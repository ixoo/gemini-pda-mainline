# First-delta terminal diagnostic amendment

This eleventh prospective amendment resolves only the import-budget/partial-
serialization stop in [MAPPING-DIAGNOSTIC-3.md](MAPPING-DIAGNOSTIC-3.md). The
v3 diagnostic source, result and refusal document remain immutable. Its warm
and nonreentrancy proof passed, and it counted one affected ordinary file with
four mapping rows before later reaching the 256-event cap, but it did not retain
their identity or event. No mapping/native exception, engine, method, callback
or private access occurred; the single private analysis remains unused.

This amendment does not increase the event budget. Instead, the next diagnostic
terminates as soon as the first fully validated mapping delta is observed and
serializes only that bounded record. It also makes the previously clarified
repository dependency directories explicit in [inputs.json](inputs.json), so
hash verification no longer relies on guessing among similarly named
experiments.

Before another diagnostic, pin and verify in `inputs.json` the exact SHA-256
values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all earlier
amendments, every earlier bootstrap/refusal record and all three earlier
mapping-diagnostic trios. Reject drift. Verify every file through the explicit
`dependency_paths` mapping; a hash match at any other path is not a substitute.

## First accepted delta is terminal

Create and freeze `mapping-diagnostic-v4.json` containing the complete source
and embedded SHA-256 before first execution. Reproduce every Amendment-9/10
identity, package, Capstone-closure, vDSO, warm, observer-inertness, wrapper and
privacy predicate. Keep the 256 total external import-event cap and all affected
file/row bounds unchanged.

When an after-delegation observer first detects a nonempty mapping delta:

1. validate the event, caller/request/fromlist, affected paths, exact before/
   after identities, mapping rows, caps and absence of virtual addresses;
2. construct `first_delta` containing only the already admitted event, file and
   exact-source-join fields, immediately encode it as canonical UTF-8 JSON,
   record its SHA-256 and retain only those immutable bytes plus digest;
3. update the global last-seen dictionary once; and
4. set an irreversible process-local terminal latch and raise a dedicated
   `BaseException` subclass handled by the top-level diagnostic harness.

Do not claim that Python source cannot catch a `BaseException`. Instead, make
the latch controlling: every later wrapper entry raises the same terminal
signal without delegating or observing; each source loader checks the latch
immediately after its `exec` returns and raises before marking that module
completed; and the outer wrapped request checks it immediately after delegation
returns. Thus a broad handler cannot permit a later import delegation, mapping
observation or successful module completion. The top-level harness handles the
signal whether it propagated directly or was re-raised at one of these
boundaries, and records which bounded propagation path occurred.
Every already-active wrapper frame must check the latch before its `finally`
observation; once set, it skips that observation and unwinds with the dedicated
signal. It must not overwrite the first record or attach another exception's
dynamic text.

The top-level handler must always attempt, in a fixed `finally` path, to restore
the exact original `builtins.__import__`, Capstone native-load endpoint,
terminal finder and isolated path. Only a successful diagnostic receipt may be
serialized after all four restoration checks pass. Require the terminal signal
to carry no dynamic payload; the handler reads only the already frozen canonical
bytes and re-verifies their digest. Do not require the interrupted pyelftools
import to complete, instantiate an engine or perform another observation after
the latch. This is a successful diagnostic stop, not a successful package
preflight.

If any refusal occurs after `first_delta` has been validated but before normal
diagnostic serialization, including failure of one or more restoration checks,
the handler first attempts every restoration and then a narrow refusal
serializer may emit only the already frozen canonical record, its verified
digest, a closed failure-class enum and four restoration booleans. This is a
refused receipt, never a successful diagnostic. It must not include the active
stack, raw map, virtual address, dynamic exception text, unvalidated path or
other import events. The serializer uses only modules frozen before
instrumentation; process exit is the terminal cleanup boundary if restoration
failed. If validation fails before freezing `first_delta`, publish no partial
identity.

The v3 aggregate evidence establishes that a first delta occurred before the
256-event refusal, so terminal-on-first-delta is the discriminating change. Do
not raise the event cap, omit observation, preload a guessed component or treat
the terminal import interruption as evidence that the imported module is
usable.

## Output and decision boundary

Run exactly one fresh `/usr/bin/python3.12 -I -S -B` diagnostic through the
approved RE-VM shell. The audit hook precedes metadata discovery and remains
active through exit. Write only `mapping-diagnostic-result-v4.json` and
`MAPPING-DIAGNOSTIC-4.md`, then stop.

The result may identify the first-observing import event and exact affected
system component, but it proves neither causation nor admissibility. A later
reviewed amendment must decide whether that component/route belongs in the
frozen standard-library baseline or native closure. No mapping exception,
engine, method freeze, callback, private analysis, acquisition, network, device
action or build is admitted.
