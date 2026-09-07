# Nonreentrant mapping-observer amendment

This tenth prospective amendment resolves only the observer recursion in
[MAPPING-DIAGNOSTIC-2.md](MAPPING-DIAGNOSTIC-2.md). The v2 diagnostic source,
result and refusal document are immutable. They identified no affected mapping
file or row, grant no exception, and leave the original v6 mapping delta
unresolved. No engine, method, callback or private access occurred; the single
private analysis remains unused.

The frozen v2 source calls its mapping observer before and after every wrapped
import. That observer itself uses Python helpers while the wrapper remains
installed, so an observer-internal import can reenter the wrapper and request
another observation. The 143-event `RecursionError` is consistent with this
uncontrolled interface, but the refusal did not retain the recursive sequence
and does not prove a particular helper or import caused it. This amendment
removes the reentrant interface and requires a warm/stability proof; it does not
raise the recursion limit, suppress real nested package imports or infer the
underlying mapping delta.

Before another diagnostic, pin and verify in [inputs.json](inputs.json) the
exact SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md),
all earlier amendments, every earlier bootstrap/refusal record and both mapping
diagnostic trios. Reject drift.

## Warm and nonreentrant observer

Create and freeze `mapping-diagnostic-v3.json` containing the complete source
and embedded SHA-256 before first execution. Reproduce the v2 diagnostic up to
the successful post-Capstone mapping/closure baseline, without an engine or
private access.

Before installing the import wrapper, invoke the exact complete mapping
inventory and normalization path twice. Require the second warm invocation to
produce an identical full file-backed mapping dictionary and pseudo/vDSO
classification, add no module name or change any existing module-object
identity in `sys.modules`, cause no native-load audit event, and perform no
write/cache/network/process/private operation. While the second warm invocation
runs, set `observer_active`; the already installed audit hook must count and
immediately refuse every `import` audit event. Require the observer-import
counter to remain zero. Freeze the set and object identities of every module
present after this warm step as the observer module baseline.

Install one process-local `builtins.__import__` wrapper. Each call still records
the real request, caller and nesting event and delegates exactly once to the
original import object. Real nested imports during that delegation continue to
pass through the wrapper and remain eligible to own the first observed delta.

For only the mapping snapshot before and after delegation, set an explicit
`observer_active` state, temporarily restore `builtins.__import__` to its exact
original object, run the already warmed mapping path, then reinstall the exact
wrapper before returning to import instrumentation. Refuse recursive observer
entry, a wrong import-object identity at any transition, any new or replaced
`sys.modules` object during the observer-only interval, a native-load request or
prohibited audit event during that interval, or failure to restore the wrapper.
Snapshot the observer-import audit counter immediately before and after each
interval and require it unchanged at zero. The audit hook must raise before an
observer-interval import event can return a mapping result for attribution.
The unchanged complete `sys.modules` name/object-identity map, native counters
and prohibited-event counters are additional postconditions, not substitutes
for that zero-import-event proof. No count or identity claim is made for cached
`__import__` calls that emit no audit event. Observer mechanics cannot own a
mapping delta.

After each observer interval, compare its mapping result to the one global
last-seen dictionary exactly as in Amendment 9. Because the mapping path is
warmed, module/object-stable and native-event-stable, any accepted change is
first observed around the external delegated import, not inside an unbounded
recursive observer. Preserve Amendment 9's distinction between first
observation and causation, exact source join or unresolved result, and all
event/file/row/privacy caps.

## One replacement diagnostic

Run the v3 diagnostic exactly once with `/usr/bin/python3.12 -I -S -B` through
the approved RE-VM shell. The audit hook precedes metadata discovery and remains
active until exit. Restore the exact original import object after the top-level
pyelftools import or any refusal. Write only
`mapping-diagnostic-result-v3.json` and `MAPPING-DIAGNOSTIC-3.md`, then stop.

Refuse observer-module drift, reentrancy, wrapper/original identity drift,
unowned mapping change, instrumentation changes to import result/exception, or
any Amendment-9 refusal. No mapping/native admission, engine, method freeze,
callback, private analysis, acquisition, network, device action or build is
authorized. A later prospective amendment must classify any successfully
identified exact component and route.
