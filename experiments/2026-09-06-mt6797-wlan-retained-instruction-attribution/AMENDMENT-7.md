# Complete decoder-module budget amendment

This seventh prospective amendment resolves only the source-loader cap stop in
[VALIDATION-V5-REFUSED.md](VALIDATION-V5-REFUSED.md). All earlier contracts,
bootstraps, refusals and diagnostics remain immutable. `bootstrap-v5.json` and
`VALIDATION-V5-REFUSED.md` are an explicit refusal pair. No private ELF was
opened and the single private analysis remains unused.

V5 completed both exact package inventories and reached 64 entered package
source executions before the terminal loader refused the next mapped module.
The complete frozen maps contain exactly 25 Capstone and 52 pyelftools Python
sources: 77 possible modules total. The terminal finder admits no module name
outside those maps. This supports replacing the undersized arbitrary global
cap with the complete-map cardinality, not an unbounded increase or a reduced
guessed dependency closure.

Before a replacement preflight, pin and verify in [inputs.json](inputs.json)
the exact SHA-256 values of this amendment, the amended
[WORK_ITEM.md](WORK_ITEM.md), all earlier amendments, every earlier
bootstrap/refusal record and the mapping diagnostic trio. Reject drift.

## Exact execution budget

Require the freshly reproduced inventories to contain exactly 25 Capstone and
52 pyelftools `.py` sources and exactly 77 distinct module-map entries. Set the
combined entered-module budget to exactly that derived cardinality. Before
entering any source module, require its name to be present in the complete map,
not previously entered, and the entered count to be below 77. Ordinary finder,
namespace, bytecode, archive and path-based fallback remain forbidden.

For each source execution, append a record before evaluating its body with the
exact module name, frozen source identity, source-derived code hash and state
`entered`; change that same record to `completed` only after the body returns
normally. Refuse duplicate entry, more than 77 entries, a map/count mismatch,
an entered record left incomplete in an otherwise successful receipt, or any
executed code object absent from its one frozen source identity. A refusal may
report aggregate entered/completed counts but must not promote an entered
module to successfully executed. A successful preflight requires every entered
record completed; it need not require all 77 mapped sources to be demanded.

This amendment changes only the finite loader budget and completion accounting.
It does not admit a new package, module, source, finder, native route, repeated
import, method repair or private-analysis retry.

## Replacement chronology

Create and freeze `bootstrap-v6.json` with the complete amended bootstrap and
embedded SHA-256 before first execution. Run exactly one fresh isolated no-ELF
preflight, reproducing every package, provenance, inert/bytecode, native,
mapping, vDSO, drift and restoration predicate from Amendments 1–6. Only a
complete successful v6 receipt may feed the frozen `method.json`; only after
that freeze may the still-unused single private child run the original bounded
instruction analysis.

A v6 preflight failure creates only `VALIDATION-V6-REFUSED.md` and stops. An
accepted result uses `VALIDATION-RESULT.md`. Refuse an inventory cardinality or
module-state mismatch, loader/finder drift, or any earlier-amendment refusal.
No acquisition, network, device action or build is admitted.
