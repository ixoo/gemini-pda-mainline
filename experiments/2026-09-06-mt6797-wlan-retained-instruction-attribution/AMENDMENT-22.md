# Direct-resolver extension identity amendment

This twenty-second prospective amendment follows the accepted
[Amendment 21 refusal](EXTENSION-IDENTITY-DIAGNOSTIC-2.md). In that exact fresh
isolated process, evaluating `pathlib.Path(TARGET)` at the first guarded stage
called the nondelegating terminal import wrapper once. The wrapper stopped
before the original import function, audit import event, metadata operation or
content gate. This establishes the live lazy-helper mechanism for that run; it
does not identify the requested import or retrospectively prove Amendment 19's
cause.

The accepted [Amendment 20 diagnostic](EXTENSION-PATH-STAT-DIAGNOSTIC.md)
already demonstrated an explicit counted `os.lstat`/`os.readlink` resolver with
no import or other audit event on the observed nonsymlink path. Its `readlink`
branch was reviewed but not exercised because the exact path had no symlink.
This amendment replaces the guarded `pathlib` operations with that method. It
does not weaken the import guard or admit the unknown lazy import.

Before execution, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier controls and the complete accepted Amendment 19–21 diagnostic trios.
Reject drift.

## One corrected sequential diagnostic

Create and freeze `extension-identity-diagnostic-v3.json` containing the
complete independently written source and embedded SHA-256. Run it exactly once
with `/usr/bin/python3.12 -I -S -B` through the approved RE-VM shell. Embed the
exact event path/digest, accepted Amendment 20 result digest and full captured
stat tuple. Do not import `pathlib`, construct a path object, import `_queue`,
resolve a module spec, reproduce package execution or call a loader.

Preload only `sys`, `os`, `stat`, `builtins`, `struct`, `re`, `json`,
`hashlib` and `datetime`, then install the irreversible audit hook and counted
nondelegating terminal import wrapper before any target metadata operation.
Any wrapper call is `refused` at its exact closed stage with count one; any
audit event outside the later two exact opens is rejected and counted exactly
as in [Amendment 21](AMENDMENT-21.md).

Validate the exact bounded ASCII target. Reuse Amendment 20's directly
implemented component resolver through counted `os.lstat`/`os.readlink`
wrappers, with no `os.path.realpath`, `pathlib` or hidden metadata helper. Use
the same two complete observation passes bracketing two captured-path snapshots
and, only when different, two resolved-path snapshots. Preserve the same
per-pass caps—component `lstat` 8, resolver `lstat` 32, `readlink` 8, symlink
expansions 8 and processed components 32—and aggregate `lstat` ceiling 82.

Require exact equality across ordered component/resolver full stat tuples,
resolved path and bounded symlink traces, and require snapshots to match the
corresponding final tuples. The resolved path must equal the captured path,
have no final or intermediate symlink, remain beneath `/usr/lib` or
`/usr/local/lib`, and its full tuple must equal the accepted Amendment 20 tuple.
Stable first-pass missing or a false canonicality/kind/mode/size comparison is
`complete-negative` at the exact stage and stops before content. A second-pass
missing, metadata exception, mismatch, wrapper/audit event, counter overflow or
schema failure is `refused`. Retain no dynamic exception text, and mark every
later stage `not-evaluated` after the first terminal outcome.

Use this exact ordered pre-open stage set before inheriting Amendment 21's 15
post-gate stages: `lexical`, `pass1-component-walk`, `pass1-resolution`,
`metadata-snapshots`, `pass2-component-walk`, `pass2-resolution`,
`cross-pass-stability`, `canonicality`, `accepted-tuple`, `kind`, `mode`,
`size`, and `import-restoration`. The conditional resolved-path snapshot count
of zero when both paths are equal is a passing `metadata-snapshots` outcome,
not a skipped stage.

Classify outcomes with this closed table:

| Observation | Status and stage |
| --- | --- |
| invalid frozen lexical input or schema | `refused` at `lexical` |
| stable first-pass missing lexical component | `complete-negative` at `pass1-component-walk` |
| stable first-pass missing resolver component, whether ordinary or introduced by symlink substitution | `complete-negative` at `pass1-resolution` |
| snapshot mismatch/missing, second-pass missing, operation overflow or metadata exception | `refused` at the current exact stage |
| component/resolver/snapshot/symlink-trace mismatch across passes | `refused` at `cross-pass-stability` |
| resolved path outside installed roots, unequal to captured path or containing an observed symlink | `complete-negative` at `canonicality` |
| stable full target tuple differs from accepted Amendment 20 | `complete-negative` at `accepted-tuple` |
| nonregular kind, mode other than `0644`, or size over 1 MiB | `complete-negative` at `kind`, `mode` or `size` respectively |
| wrapper call, audit event, import identity failure, counter mismatch or internal failure | `refused` at the current exact stage |
| every pre-open predicate passes and original import identity is restored | proceed to Amendment 21 post-gate stages |

Record each completed stage as `passed`, the first terminal stage as
`complete-negative` or `refused`, and the entire ordered suffix as
`not-evaluated`. No terminal catch may advance.

Only after the two-pass metadata gate succeeds, restore the exact original
import function and prove object identity, wrapper count zero and audit counts
zero. Then execute the unchanged Amendment 21 post-gate stages and outcomes:
exactly one read-only candidate open; accepted tuple checks with pre/post
`fstat` and final `lstat`; one bounded EOF read; content hash; bounded
ELF64/little-endian/AArch64/`ET_DYN`, program-header, dynamic-table, string-table
and at-most-eight `DT_NEEDED` checks; exactly one bounded strict
`/proc/self/maps` read; candidate-absence classification; and exact final audit
counters. All Amendment 21 numeric parser/map bounds and its no-partial-identity
rule remain controlling.

Write only `extension-identity-diagnostic-result-v3.json` and
`EXTENSION-IDENTITY-DIAGNOSTIC-3.md`, with source/result hashes, lossless
canonical receipt hash, UTC chronology, closed stage outcomes, wrapper/audit/
metadata/read counters, sanitized positive identity fields only when admitted,
mapping-absence boolean and `private_reads: 0`. Publish no bytes, virtual
address, maps row, dynamic exception text, requested lazy-import identity,
credential or private path.

Stop after the one diagnostic; refusal consumes its budget. A positive result
establishes only the current exact installed extension's bounded identity and
absence from this isolated process. It does not load or initialize `_queue`,
prove package usability, admit a general extension route, explain Amendment 19
retrospectively or authorize retained private analysis. No package execution,
engine, method, callback, private content, acquisition, network, device action
or build is admitted.
