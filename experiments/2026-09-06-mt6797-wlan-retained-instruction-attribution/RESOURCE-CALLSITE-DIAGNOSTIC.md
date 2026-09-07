# Resource callsite diagnostic: pre-join refusal

The single [Amendment 14](AMENDMENT-14.md) diagnostic refused before capturing
a runtime resource-function event. Its bounded static inventory found one
direct candidate, `resource.getpagesize` in `elftools.elf.elffile`, line 17,
column 15. That is candidate evidence only: there is no exact runtime callable
or first-callsite join, and no function execution is admitted.

## Freeze and chronology

- Dispatch: `5663b51271d6aa3a70c1decdce3d575e0a5d2422`; Astra Medium.
- All 42 controlling and 18 explicit dependency-path hashes passed.
- [Frozen diagnostic](resource-callsite-diagnostic-v1.json), frozen
  `2026-09-07 04:34:22 UTC`, file SHA-256
  `178a3f12cabfce91dabad67feb3a10fcd0e8b4fc5a36d585478a0af2aa794914`;
  embedded source SHA-256
  `f5f6ff91ebe34740676fa6efaec5acdca4aa7e097761b722e440a27f59e8d157`.
- Exactly one fresh `/usr/bin/python3.12 -I -S -B` diagnostic through the
  approved RE-VM shell, from `2026-09-07T04:34:52.297945+00:00` to
  `2026-09-07T04:34:52.625069+00:00`.
- [Result](resource-callsite-diagnostic-result-v1.json), SHA-256
  `baccf01f941d959489747159f72443d153dc8e64c012e4362593108ee9ef7e27`.

## Evidence and limits

The result's closed failure class is `guard-or-predicate-refusal`. No dynamic
exception text was retained. `first_callsite` and its digest are null; the
terminal latch, exact signal-handler flag and profile-auto-unset proof are
false. All seven restoration checks passed: profile, original import object,
native-load endpoint, finder, isolated path, resource loader creation endpoint
and resource loader execution endpoint.

The common 77-entry map, Capstone closure and exact resource preload completed.
Resource spec/create/exec/extension-audit counts are one each, cached requests
and function attempts zero. The diagnostic reached 28 entered and 27 completed
package modules. All five reached mapping stages preserve the exact in-process
vDSO row. It did not reach the pre-call mapping/identity join or any later
profile event.

All 52 frozen pyelftools sources were parsed. The sole direct candidate uses
the `import-resource` binding form, local spelling `resource`, and literal
callable name `getpagesize`. Its exact source is
`/usr/lib/python3/dist-packages/elftools/elf/elffile.py`, SHA-256
`457c93c8be327cbce2a86869aa40d9067f12f7c33052730f7e1cbcccb99b9b54`,
37,150 bytes. The candidate has line/end-line 17 and column 15. This does not
identify a runtime callable object, establish its arguments or return value,
or classify its effects as safe.

There is a static harness integration defect consistent with the stop: the
new `terminal_import` frame calls `cached_resource_import`, while that inherited
helper still uses `sys._getframe(1)` as the package caller and requires the
frozen source filename and line 16. Its immediate caller is now the diagnostic
wrapper, not the package frame. This is a source-level finding, not a claim
that the closed runtime failure enum uniquely records that predicate. The
diagnostic was not changed or rerun after refusal.

One Capstone native request was recorded; optional, filesystem/cache, network,
process, engine, callback and private-read counts are zero. No resource function,
method freeze, private analysis, device action or build was admitted. The RE
shell was closed immediately; no raw map, callable representation, pointer,
private path or private capture file was retained. Earlier artifacts are
unchanged and the private-analysis budget remains unused.

## Checks and escalation

Tests actually run: 60 exact dependency hashes; frozen source digest and Python
syntax compilation before execution; the single guarded diagnostic; result,
candidate-schema and refusal-predicate checks; relative Markdown links; and
`git diff --check`. No alternate latch/restoration fixture or second diagnostic
was run. The runtime terminal-signal/profile-auto-unset path remains untested.

Attempts: one diagnostic, no repair. Unresolved: the exact runtime callable and
frame join. Next discriminating check requires a prospective bounded correction
that passes the original package frame explicitly through the wrapper/helper
boundary while retaining every pre-call refusal, terminal-latch and restoration
predicate. Static candidate evidence does not authorize calling `getpagesize`.
Only the three named diagnostic files are handed off; stop here.
