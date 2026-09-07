# A28: faithful-prefix reproduction instead of A27 adapters

Design parent: `7ab160dffddc334492de247405509e8b12864c2d`, verified clean
and equal to `origin/main`. Design input snapshot SHA-256:
`756570cd13a773644945fd2c5466fbe2e8e5af911c26d01e349cb238c4473780`.
This is contract-only. No source candidate, VM access or run is authorized here.

## Correction and immutable boundary

[A27](AMENDMENT-27.md), SHA-256
`02b74714ee2d5d86f7a639ef0190c554ad91cf25110676af0ad778c7b3d77920`,
remains the historical independently reviewed design. Its attempted source
construction stopped before writing a candidate, after generator-side
`NameError` failures for `EXPECTED_TOOL_SHA256` and then `CAPS`.
No candidate execution or private read occurred. The later audit found
substantive draft fidelity/adapter problems as well as those generator errors;
fixing names alone was not an acceptable restart.

A28 prospectively **replaces** A27's read/scandir/stat adapters, pre-operation
instrumentation, split predicates and newly introduced I/O caps with one
minimal reproduction of V10's technical prefix. This correction removes
observer-induced changes from the normal prefix. It does not modify A27,
V9/V10, their receipts, the private method, or their consumed run budgets.

Preserve every existing pin in [inputs.json](inputs.json), including all 108
design-parent controls/dependencies. Principal immutable inputs are:

| Input | SHA-256 |
| --- | --- |
| V9 result / expected tool authority | 334149f00090c18d6f51baf84d05d94844a15aece74da43aeb1282cf87b87fb3 |
| V10 bootstrap | 4e599c07d3fad2aabc6982383dbbc92dc9796136f388263045e59593cfcc4d8c |
| V10 embedded source | bd42ce6c91e1733f2fd0e849fae43d090849453c89c4a6f302c714f04d1dd633 |
| V10 refusal | 3e0caa5234b3bd1842e70cab0626929ea0ed044b59960fc03da84411c13fb193 |
| V10 source freeze | ae6135ab45ffaf23c85af2df63bbd1ebc574d390e8362cabf1cd7d3db5a846fb |

The complete expected tool literal retains canonical SHA-256
`4baaa1020f2d895a688c6675b5091aed77d63d3a9ad9103316c4dbb6e830b639`.
Use Python integer-preserving JSON/AST literal handling, not floating-point
conversion, a digest stub or new observations. No previous private/raw log,
target bytes or excluded provisional output is an input.

Astra Medium owns this correction; Sol Medium reviews; `/root` integrates
and owns workflow measurement. Current ownership is exactly this amendment
and minimal `WORK_ITEM.md`/`inputs.json` updates. Preserve unrelated work.
Future separately dispatched construction owns `inventory-diagnostic-v1.json`
and authorized state pins; future execution/results own
`inventory-diagnostic-result-v1.json`, `INVENTORY-DIAGNOSTIC.md`,
`verify-inventory-diagnostic.py` and state pins. These names remain unused;
there is no existing diagnostic candidate to repair or rerun.

## Exact startup exception; unchanged technical prefix

The future invocation is exactly
`/usr/bin/python3.12 -I -S -B - inventory-diagnostic`, through
`./scripts/dev-vm re-shell`. Accept exactly
`START_ARGS == ("-", "inventory-diagnostic")`. No method descriptor/hash
argument, private path, alternate mode, input pipe or environment-based
private/method route exists.

V10's `analysis_args()` requires twelve arguments, and its startup
`analysis_state()` requires analysis mode. The owner explicitly admitted
**exactly two no-I/O startup substitutions** to remove that authority:

1. Replace the `analysis_args()` call with an exact diagnostic argv check.
2. Replace only `analysis_state("startup")` with a closed diagnostic state
   check: diagnostic mode, method/pipe/private/callback state absent, their
   operation counters zero, and no engine/resource/queue entry.

These are named reproduction limitations, not verbatim V10 startup claims.
Freeze their complete expressions and effects for review. They may validate
existing state but must not create handles, parse inputs, install observers,
set invented analysis authorization, or invoke any removed route. No other
normal startup substitution is admitted. Preserve the existing run-counter,
expected-tool canonical identity and runtime tests, including their compound
expressions and ordering.

Retain V10's initial `import sys`, helper import statements/order, audit
installation order, relevant top-level constant values/initialization order,
and technical top-level checks/identity/root derivation. Keep the bodies of
`audit`, `fail`, `require`, `boundary`, `stage`, `passed`,
`identity`, `checked_directory`, `tree_inventory`, `signature`,
`discover_legacy`, `stdlib_inventory`, `snapshot`, `maps`,
`forbidden_loaded`, `canonical_sha` and every other reachable helper
verbatim. Preserve original defaults, closures and all condition expressions.

The entire main-body segment beginning at `stage("initial-inventory")`
and ending at its final `passed()`, immediately before
`stage("pre-entry-static")`, is copied verbatim. In particular:

- stdlib collection precedes baseline maps;
- baseline maps precede the unchanged compound interpreter/stdlib/native
  comparison;
- Capstone discovery precedes pyelftools discovery;
- cardinality and LEGACY/DISTRIBUTIONS comparisons retain their original
  compound expressions and short-circuit behavior;
- module iteration order, recursive directory traversal, namespace checks,
  duplicate source reads and repeated mapped-file identities stay unchanged.

Stop permanently at that segment's end. Never reach pre-entry static analysis,
package import, engine, resource/queue preload, method or private operations.
Prefer deleting their definitions when this does not change any reachable
body, constant dependency, helper import or top-level effect. Otherwise retain
only statically unreachable definitions and inert state: prove the only entry
point, audit callbacks, stage writes and call graph cannot reach them. There
is no external callable dispatch, exception fallback or second entry point.
Unreachable names are not authority; document the complete retained-dead set.

## Source-first and exact static acceptance

Freeze the complete source, source SHA-256, exact dispatch/input/control pins,
expected tool object, fixed failure-site map, closed output schema, source
delta report and UTC in `inventory-diagnostic-v1.json`. Keep generator-side
metadata separate from source-local constants. Derive hashes from actual
pinned bytes; never read variables out of the source by executing it.
The source hash follows final source construction; the complete container hash
is recorded externally. Do not embed a self-referential container hash.

Before writing or publishing the candidate, perform in-memory JSON and Python
AST literal round-trips, source compile-only checks at optimization 0/1/2,
name/dependency checks and a closed-delta review. Compare each retained helper
body's exact source text and normalized AST with V10. Verify the complete
initial-inventory segment's exact text/AST, imported helper order, relevant
top-level initialization/effects, reachable call graph and all direct/audit
I/O call sites and arguments. The two startup substitutions, terminal
truncation, unreachable-definition removal, and inert/post-failure reporting
machinery are the exhaustive allowed deltas. Any other delta stops construction.

No bounded-reader proxy, scandir/listdir/stat adapter, monkeypatch, new
profile/trace hook, per-operation label/counter update, warm-up, split
comparison, deduplication, pre-read or new normal-path reevaluation is allowed.
Do not execute a candidate, fixture, package body or guest probe for validation.
Source construction and the subsequent single RE-VM run require separate
bounded dispatches and independent review; publication alone dispatches neither.

## Failure-only localization from already-live state

Do not change `fail()` or `require()` to observe their callers. After the
original terminal exception reaches the outer handler, latch/preserve the
original failure first. Only then may a bounded observer inspect that
exception's existing traceback and selected already-live frame fields.

Freeze a mapping from candidate source locations to fixed semantic site IDs
and their V10 counterparts. Map exact AST call spans, qualified helper names
and the final candidate's line/column positions, not manually assumed line
numbers. Distinguish the original failure site from `require`/`fail`
plumbing. Matching is to the exact frozen candidate code, not arbitrary
stdlib frame text.

The complete permitted introspection boundary is: the caught exception's
`__traceback__`; traceback `tb_next/tb_frame/tb_lineno/tb_lasti`; selected
frame `f_code/f_locals/f_globals`; and code
`co_name/co_qualname/co_filename/co_positions()`. Use no new import,
traceback formatter, source-line loader, disassembler, evaluator, callback or
filesystem read. If line-only matching is ambiguous, the already-live code's
position iterator may distinguish a frozen span; cap it at 32,768 positions
per inspected code object and at 64 traceback frames total. For the pinned
CPython 3.12.3 code-unit layout, require a nonnegative even `tb_lasti`, select
the `co_positions()` tuple at index `tb_lasti // 2`, and match its complete
line/column span to the frozen callsite map. Missing/None positions, an
out-of-bound index or nonunique span produce `location-unresolved`; do not
guess an offset or decode bytecode. Freeze this rule in the candidate's
source/AST review before execution. Do not publish code,
bytecode, arbitrary filenames, frame dictionaries or object representations.

If no unique frozen site can be resolved within those bounds, emit
`location-unresolved` with a closed reason; never guess, inspect more inputs
or overwrite the original failure. A capture failure is secondary metadata,
not a replacement failure. No inspection occurs on an entirely passed prefix.

From whitelisted live values, report only existing closed stage/counter state
and optional known frozen path indices. Indices refer to a sorted immutable
expected-file pool. A non-string or unknown path is represented solely by a
fixed role such as `stdlib-file`, `mapped-file`, `metadata-entry`,
`package-entry` or `unknown`; no path conversion, arbitrary repr, basename,
path hash, path list or raw local value is emitted. Restrict local/global
lookups to a frozen frame-role/name allowlist; never enumerate their mappings.

There is no additional identity hashing, comparison-group evaluation,
boolean-expression replay or comparison of new observations to V9 inside
the failed child. The usual canonical serialization/hash of the sanitized
receipt remains allowed. Existing identity hashes may be copied only through
a frozen safe scalar schema, never by serializing a live identity dictionary
or unknown key. No read/stat/resolve, new iteration of discovery or retry
follows failure. Existing raw exception messages are not publication input.

This identifies the failed **callsite** of the new reproduction. An unchanged
compound `require()` may not expose which short-circuited operand failed;
preserve that uncertainty. It does not retroactively identify V10's unrecorded
failure, prove zero discovery from empty inventory counters, or establish an
accepted tool environment. Full prefix passage reports
`initial-inventory-not-reproduced` and stops, never a tool/private-analysis
admission or hardware claim.

## I/O fidelity, receipt, collector and cleanup

A28 intentionally withdraws A27's newly added whole-file byte caps, reader
counters and bounded metadata-enumeration adapters. Preserve V10's actual
`read_bytes/read_text`, repeated reads, discovery API behavior and original
tree/map caps. This is source-level I/O/audit fidelity, **not** a new exact
runtime syscall trace or a guarantee that every inherited whole-file or
directory operation has A27's proposed bound. No new root, input or read route
is admitted. Report only existing measured counters; uninstrumented totals
are unavailable, not zero. The audit body and its original refusals remain
unchanged. Do not claim a general Python or OS security sandbox.

The sanitized receipt is at most 256 KiB. Its frozen schema contains exact
source/container/dispatch/contract links, one-run state, outcome, existing
outer-stage state, preserved first failure, bounded fixed-site localization,
existing counters, cleanup results and false downstream-authority fields.
No full traceback, source text, raw log, private path, metadata content,
map base, pointer, instruction or target bytes are published.
If helper/top-level failure prevents a child receipt, retain the raw logs
privately and report `no-child-receipt` at collector level; do not add
normal-path imports/instrumentation or invent a child site to cover it.

One named custodian may execute one fresh process only after a separate
dispatch. The outer collector validates source/container bytes, supplies only
stdin source and the exact two-entry argv, disables debuginfod/download and
bytecode behavior, and captures stdout/stderr through two pipes into only two
mode-0600 files in a fresh mode-0700 managed RE work child. Install collector
cleanup immediately and bound its elapsed lifetime at 180 seconds; no retry
on timeout. Preserve unique raw evidence privately, its hashes and retention
location; remove no sole copy. No method pipe, input copy, package probe,
fixture, private/device/build/network/acquisition or automatic continuation.

After failure-only capture, perform only the existing applicable restoration/
reference cleanup and child/shell exit. Do not add a read, map snapshot,
wrapper or resource/profile operation to cleanup. Untouched state remains
untouched; record not-applicable separately from attempted/succeeded. A cleanup
exception cannot replace the original failure or turn refusal into success.
Release custody before host result construction; no secure-erasure claim.

Freeze the result before writing the assert-free host verifier. Run it normally
and with `-O`, covering identity/hash/chronology, exact source delta, outcome/
first-site linkage, ambiguous/unresolved-site handling, current-versus-historical
claims, available/unavailable counters, no-discovery inference, zero reachable
forbidden routes, source-first/run budget, cleanup, privacy and false authority.
Mutate all declared families; rebind receipt hashes for semantic mutations so
a generic digest mismatch is not the sole rejection. Never execute candidate
source or an input parser to validate public receipts.

## Design checks and handoff

Validate all inherited pins plus this amendment and updated work-item pin;
check V10's source/AST segment boundaries and the two explicitly authorized
startup exceptions, helper/import/I/O preservation requirements, source/hash
noncircularity, local links, privacy and whitespace. This design does not claim
that a candidate implementing them exists or has passed those future checks.

Current work has no source construction, VM/private/device/network access,
candidate/package execution, kernel build, result/validation/shared-document
edit, commit or push. Stop on any further ambiguity. Handoff is for Sol review
and `/root` integration; future construction and execution remain separately
unadmitted. Credits are unavailable; the integrator owns the measurement ledger.
