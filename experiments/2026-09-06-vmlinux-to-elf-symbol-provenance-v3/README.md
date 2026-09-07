# Fresh no-database Kallsyms provenance and inspection envelopes

The single source-forced run recovered unique original `T` entries for all four
targets in the pinned retained image. They are ordinary global text symbols,
not classifications inferred from reconstructed ELF `GLOBAL` alone. Each has
zero same-address aliases and an admissible next-distinct-symbol inspection
envelope:

| Target | Start | Exclusive inspection boundary | Bytes |
| --- | --- | --- | ---: |
| `do_connectivity_driver_init` | `0xffffffc0006e3a70` | `0xffffffc0006e3be0` | 368 |
| `do_wlan_drv_init` | `0xffffffc0006e3ed0` | `0xffffffc0006e3fe8` | 280 |
| `mtk_wcn_wlan_gen3_init` | `0xffffffc0007415a0` | `0xffffffc000741898` | 760 |
| `mtk_wcn_wlan_gen3_exit` | `0xffffffc000741898` | `0xffffffc000741938` | 160 |

These are **not exact function ends**. No instructions, calls, returns, xrefs,
runtime execution, teardown safety or resource quiescence were analyzed. The
envelopes may feed a separately scoped instruction-analysis contract after
independent Sol review; this record neither starts nor authorizes that work.

## Frozen scope and lineage

[WORK_ITEM.md](WORK_ITEM.md), [inputs.json](inputs.json) and the reviewed
[metadata-only parent amendment](AMENDMENT.md) define this item. The earlier
pre-execution source-parent refusal remains in [PREFLIGHT.md](PREFLIGHT.md).
The analysis parent is `cd9fbe8e0e8f7eda29b553ae131821d9facd8cf0`.

Execution used the explicitly authorized successor
`f35c050cff62de6278e7788cad0ff775587fb0c9`. Its complete delta from amended
dispatch `3942e5af4fc6887befdc6f301da15e0415bb99e7` was the unrelated workflow
YAML change named in [loader.json](loader.json); all v3 and dependency paths
remained byte-identical. Work paused on that HEAD difference until the
coordinator authorized the successor. The unrelated commit was preserved.

A second pre-execution clarification scoped the no-new-files claim to the
guarded process: zero attempted writes, unchanged exact admitted-source
hashes/sizes/modes/mtimes, and an empty fresh cache. No database subtree was
enumerated or statted. No claim is made about files created externally.
The outer collector separately performed two explicit private evidence writes
from child-process pipes; these are not represented as guarded-child writes.

## Method and observations

The complete independently written loader, poisoned database stub, synthetic
`core` parent and collector are frozen in [loader.json](loader.json).
[method.json](method.json) records the exact two-method subclass, architecture
read/write inventory, diagnostic-only database dataflow, original type/case
transformation and unchanged-method checks. Both files were frozen at
`2026-09-07T01:06:19Z`, before private content access.

One fresh Python 3.12.3 process loaded seven RECORD-backed source modules and
registered 160 source-derived code objects. Only the statically required
standard library was bootstrapped for the parser; no third-party dependency
provided parser semantics. Every executed package frame was checked against
its source-derived code identity. The metadata-only parent executed no code,
used separate immutable one-entry paths, and retained its exact spec, binding
and admitted children.

The original constructor and parsing methods were inherited unchanged.
Architecture selection and database diagnostics were each overridden once.
The original architecture detector was poisoned, called zero times, and its
exact descriptor restored. Five database names were retrieved once to satisfy
the import, the sixth remained unused, and all six sentinels had zero
contract-enumerated downstream read/use operations. All twelve prohibited
guard classes recorded zero.

Sol Medium accepted that read/use scope on source-only review. Ordinary
instance attribute writes/deletes and subscript mutations fail naturally,
but were not separately counted or fault-injected. This sentinel is not
claimed to be a general-purpose exhaustive mutation proxy. The frozen source
confines all database-name uses to the overridden metadata method; no reparse
was performed for the ruling.

After all four private input hashes passed, the one construction recovered
64,417 monotonic tuples. Fresh exact-name matching, complete alias groups,
immediate distinct neighbors and retained-ELF starts passed for every target.
The retained ELF still has zero target `st_size`; its broad synthetic
`.kernel` executable flags are reconstruction metadata, not instruction or
function-boundary evidence. Full bounded neighborhoods are in
[intervals.json](intervals.json).

The run occurred at
`2026-09-07T01:07:09.223614Z–2026-09-07T01:07:10.261116Z`.
[analysis.json](analysis.json) retains its sanitized counters, source snapshots,
postconditions, raw-log hashes and explicit limitations. Nanosecond mtimes
are exact decimal strings to avoid JSON consumer precision loss. The two
mode-0600 raw evidence files remain in one fresh mode-0700 RE-VM child;
private paths and log contents are not published. Its empty cache was removed.

## Validation and handoff

The five JSON records were frozen before creating the verifier.
[verify.py](verify.py) checks their identities, twenty predecessor/dependency
hashes without parsing those predecessors, and the substantive evidence
predicates. Normal and optimized self-tests each reject 261 in-memory evidence
mutations. They do not inject runtime failures or consume a second parser run.

See [VALIDATION.md](VALIDATION.md) for tests actually run and
[FREEZE.md](FREEZE.md) for file identities and review-ready time. Independent
Sol Medium review accepted the result on first full review at
`2026-09-07T01:30:38Z`. No kernel patch, device state or hardware-support claim
was changed by the experiment.
