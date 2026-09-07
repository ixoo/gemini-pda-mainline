# Sequential extension identity diagnostic: path-object wrapper refusal

## Outcome

The sole [Amendment 21](AMENDMENT-21.md) run returned `refused` at
`path-object`, with closed class `latched-wrapper-reentry`. The blocking
import wrapper recorded exactly one call, at that same stage, and raised its
payload-free dedicated signal before delegating.

In the frozen source, this stage validates the constant lexical string and then
evaluates `pathlib.Path(TARGET)`. The observation localizes wrapper re-entry
to path-object construction in this fresh isolated process. No import name,
helper source or deeper caller was captured; none is inferred.

All 24 later stages were `not-evaluated`. All explicit `lstat`, `fstat`,
candidate-read and maps-read counters were zero. Every audit counter was zero,
including import: the wrapper stopped before delegating to the original import
function and before an import audit event.

The content gate remained closed. No candidate identity, ELF metadata,
dependency list, mapping-absence boolean or partial content identity was
published. This is not a negative filesystem predicate.

The result establishes the wrapper-re-entry mechanism in this diagnostic. It
does not retrospectively prove which operation caused the historical Amendment
19 refusal, nor identify the import requested inside path construction.
The accepted [stat-only result](EXTENSION-PATH-STAT-DIAGNOSTIC.md) remains
unchanged.

## Frozen inputs and chronology

- Published clean dispatch: `1095538ba8c2b4197d0ea0d9879ed10e14a560f0`.
- Contract: [WORK_ITEM.md](WORK_ITEM.md), [Amendment 21](AMENDMENT-21.md)
  and all inherited pinned controls.
- Dispatch [inputs.json](inputs.json) SHA-256:
  `4cc512dc75088ef71646297150094066b75b9082699077ef630c7978e59bd0d4`.
  All 81 dispatch pins passed.
- [Frozen source container](extension-identity-diagnostic-v2.json) SHA-256:
  `1b08a0f029287117ef07abf07e32cc02b0571628482cda8fcdeb200b6c8840e2`.
- Embedded source SHA-256:
  `23fee3dd87a083d4f35f065dd98a8d2ffcd8d93f12853bb1aa0af3bb791571f6`.
- Freeze: `2026-09-07 06:20:18 UTC`.
- Sole run: `2026-09-07T06:20:56.848397+00:00` through
  `2026-09-07T06:20:56.848437+00:00`.
- [Complete sanitized result](extension-identity-diagnostic-result-v2.json)
  SHA-256:
  `0594feadfe743487cbff6489d0d9d1f0b145439e1228efbd9a144dd91b7865f9`.
- Canonical receipt SHA-256:
  `759a3010fc3cd53f144adc87ec81bfea3878665fe5907eb56053f59aae104c26`.

The source embeds the exact accepted event path, canonical event digest,
Amendment 20 result digest and all seven fields of its accepted captured-path
stat tuple, including the exact nanosecond integers. This run did not reach
their metadata comparison.

The approved RE shell supplied the frozen source once on stdin to
`/usr/bin/python3.12 -I -S -B -`, with empty `DEBUGINFOD_URLS`,
no-user-site and no-bytecode controls. Only the frozen standard-library helpers
were preloaded before the irreversible audit hook and nondelegating import
wrapper were installed. No guest source file was created.

The raw child receipt was preserved as text and parsed/formatted losslessly
with host Python. Its canonical digest matched before publication; no
JavaScript numeric round-trip was used.

## Closed stage and guard evidence

- `path-object`: refused.
- Remaining nine pre-open stages: not evaluated.
- All fifteen content/parser/maps/final-audit stages: not evaluated.
- Wrapper count: 1; first stage: `path-object`.
- Audit counts: candidate open 0, maps open 0, import 0, dynamic load 0,
  write 0, mutation 0, network 0, process 0, other 0.
- Explicit operations: pre-open `lstat` 0, `fstat` 0, post-read
  `lstat` 0, candidate read 0, maps read 0.
- Content gate: false; import-restoration stage: not reached.
- Identity, candidate absence and maps row count: null.
- Private reads, package execution, engine instances and callbacks: zero/false.

The wrapper remained installed because failure preceded the admitted
import-restoration stage. No handler advanced to that stage or to content.
Interpreter exit was the cleanup boundary; the outer RE shell also exited.
The named custodian then released RE-VM custody.

## Checks actually run

- Clean published dispatch identity/status and all 81 pinned hashes: passed.
- Host AST parse and compile-only checks before freeze: passed.
- AST checks for no `assert`, unique function definitions, exactly two
  named open sites, no loader/dynamic-evaluation route, nondelegating wrapper,
  exact accepted stat tuple and all 25 ordered stage entries: passed.
- Frozen container/source digest checks before the sole execution: passed.
- Exactly one isolated RE diagnostic: refused at `path-object`.
- Lossless raw/published canonical receipt digest verification: passed.
- Host JSON/schema, closed stages/refusal class, wrapper/audit/operation
  counters, no-partial-identity rule, authority and UTC chronology: passed.
- Updated controlling/dependency pins, local Markdown links, source license,
  sensitive-string checks, new-file whitespace and `git diff --check`: passed.

The later metadata, content, ELF, dependency, maps and final-audit branches were
reviewed in source but not exercised. No diagnostic retry, alternate path,
candidate content inspection, package execution, device operation, network
acquisition or build ran.

## Bounded handoff

The one-run budget is consumed. The single private analysis remains unused.

Only the three named artifacts and authorized `WORK_ITEM.md`/`inputs.json`
post-result state/pin updates changed. Dispatch hashes above remain the exact
pre-execution inputs; current pins additionally cover this trio and the updated
handoff state. No commit or push was performed; roadmap, support and workflow
ledger files were not changed.

Unresolved question: which exact helper import occurs during path-object
construction under this guarded Python environment? The current source/receipt
does not identify it. Any prospective correction or additional observation must
preserve the no-import boundary or explicitly review a new bounded contract;
this result does not authorize weakening the wrapper, rerunning, or proceeding
to content.

No content identity, ELF/dependency structure, mapping state, extension
initialization, package usability, private-binary behavior, runtime driver,
teardown, firmware, radio or hardware support is established.
