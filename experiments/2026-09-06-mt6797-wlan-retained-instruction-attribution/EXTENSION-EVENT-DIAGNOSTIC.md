# First extension-event diagnostic: terminal capture, validation refusal

## Frozen identity and chronology

- Contract: [WORK_ITEM.md](WORK_ITEM.md) and
  [Amendment 19](AMENDMENT-19.md), with all inherited pinned controls.
- Published dispatch: `18cd30203f996f28c1878e6d0472d36a0b516726`.
- [inputs.json](inputs.json) SHA-256:
  `6a0baa8cfc28397303f41dd79a78ef82993eab56e6306f073974721644b89cb5`.
  All 73 hashes passed: 55 controlling artifacts and 18 dependencies.
- [Frozen diagnostic](extension-event-diagnostic-v1.json) SHA-256:
  `f1c1777520598070d4500e75179d78e90cade6c63fa74a4a4c13fa3ca14bb5cd`.
- Embedded source SHA-256:
  `93c8e359ab643484a7399d8633e20096dd10dcad66db8d2493ba88c4d65267e3`.
- Freeze: `2026-09-07 05:25:48 UTC`.
- Sole execution: `2026-09-07T05:26:26.581972+00:00` through
  `2026-09-07T05:26:27.084384+00:00`.
- [Complete sanitized result](extension-event-diagnostic-result-v1.json)
  SHA-256:
  `04e1fdfc801b5deb6a6da033a5fc9f79eabc0a9a56324c923397264ed98cfa82`.

The approved RE shell ran the frozen source once on stdin using
`/usr/bin/python3.12 -I -S -B - preflight`, with empty `DEBUGINFOD_URLS`,
no-user-site and no-bytecode controls. No guest source file or analysis database
was created. The child and outer RE shell exited after refusal.

## Observed terminal event

The first generic extension-refusal branch captured module `_queue`, with
lexical event filename
`/usr/lib/python3.12/lib-dynload/_queue.cpython-312-aarch64-linux-gnu.so`.

This is an **audit-event filename**, not a validated installed-file identity.
The five-field audit shape and lexical bounds passed. The three search fields
were all absent (`None`); live path/meta-path/path-hook object identities and
order matched the frozen state.

The active mapped source was `elftools.dwarf.structs`. The first matching
package frame supplied exact source context at line 10, with frozen source
SHA-256
`b7f4d190c9edd4a27a1a7700dc470ae9a8616fd87026e7176fa9f3e2c0c91347`.
The literal import-statement join is **unresolved**. This execution context does
not prove that the package directly imported `_queue`, nor identify an
intermediate import chain.

The canonical UTF-8 event record has SHA-256
`1f44854434c4d88a28f07834aff0629e5de462ee8cbbb3a6a6d3cd9245e56cf1`.
It was latched before the audit hook returned. A payload-free dedicated
`BaseException` reached its exact outer handler. Propagation counters were
audit 1, source 3, wrapped import 8 and outer import 1. The active stack's
maximum depth was 7 and final depth was 0.

## Post-stop refusal and limits

Overall status is `refused`, failure class
`post-stop-validation-refusal`.

The strict validation audit recorded:

| Counter | Observed | Required for success |
| --- | ---: | ---: |
| candidate open | 0 | 1 |
| maps open | 0 | 1 |
| profile restoration | 1 | 1 |
| other events | 0 | 0 |

The failure occurred before a candidate content open or post-stop map open.
The receipt does not preserve a specific metadata predicate, exception type or
failure stage within that pre-open interval. No claim is made that the path
was canonical, nonsymlinked, mode `0644`, within the byte bound, or that any
particular check caused refusal. Do not diagnose a symlink, mode difference or
size overflow from this result.

Consequently, candidate SHA-256/size/mtime, ELF identity, `DT_NEEDED` closure
and post-stop mapping absence are **not established**. No candidate bytes were
read. The hook raised before allowing the captured extension load; the
independent post-stop map confirmation was not reached.

All seven named restorations returned true: profile, original import object,
native-load endpoint, finder/meta-path, isolated path and both resource-loader
methods. The profile restoration was the sole allowed post-stop audit event;
all other restoration operations generated zero recorded audit events.

The inherited resource query remained `returned`, with one
lookup/create/exec/extension/cached request/function call/function return and
zero function exceptions. The separate reference returned 4096 once, with
`SC_PAGE_SIZE` mapped to 30 and its guarded state unchanged. The pre-event
checks retained the accepted file-backed map dictionary/permission-offset
rows, and all eight recorded map stages preserved the full vDSO row.

The complete 25-source Capstone and 52-source pyelftools inventories passed.
56 module bodies entered and 53 completed before the terminal stop. There was
one admitted Capstone native request; optional-route, write, cache-write,
network and process counters were zero. Engine instances, method presence,
callback presence/invocations and private reads were zero.

## Checks actually run

- Clean published dispatch identity/status and all 73 pinned hash checks.
- Host AST parsing and compile-only checks before execution.
- AST checks for unique top-level function names, no `assert`, exactly one
  page-size reference, and absence of engine/callback calls and method/private
  entry functions.
- Review of bounded source stack, original-caller tuple, terminal propagation,
  canonical event schema and strict post-stop audit allowlist.
- Frozen JSON and embedded-source digest verification before the sole run.
- Exactly one no-private RE diagnostic: terminal event captured, post-stop
  validation refused.
- Result/source JSON, canonical event SHA-256, source syntax, chronology,
  counter/restoration checks, local Markdown links, source license,
  sensitive-string and new-file whitespace checks: passed.
- `git diff --check`: passed.

No second diagnostic, candidate loader, private analysis, network acquisition,
device operation, kernel build or hardware test ran.

## Escalation and handoff

The one diagnostic budget is consumed; no retry or candidate admission is
authorized. The single private analysis remains unused.

Evidence retained: exact first event, canonical digest, bounded source context,
unresolved literal import join, terminal propagation and restoration receipt.
Missing evidence: candidate pre-open validation outcome, file identity/ELF/
dependency closure and independent post-stop map result.

The next discriminating check would be a prospective, separately frozen
stat-only diagnostic of the **captured exact filename**, with explicit bounded
stage/outcome fields for canonicality, symlink status, regular-file mode and
size, and sanitized exception classes. It must distinguish those failures
without reading candidate bytes or loading the extension unless independently
authorized. This is a proposal only; no further probe was performed here.

This result grants no successful initialization, return behavior, package
usability, extension admission, private-binary inference, runtime-driver,
teardown, firmware, radio or hardware-support claim.
