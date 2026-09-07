# Prospective initial-inventory predicate diagnostic

Design parent: `aad053da8b19ff6ae6189f2f1ac5d4a61d02d3ce`, verified clean
and equal to `origin/main`. Design-time [inputs.json](inputs.json) SHA-256:
`811d60b03e02a1aafeff2dfee58571b639b337714358fa4a924bf46ac04911e7`.
All 107 existing pins passed. This amendment designs a diagnostic only; it
does not construct source, open the RE VM or dispatch a run.

## Question, immutable evidence and ownership

V10's sole run returned `validation-failure` at `initial-inventory`, after
startup and one baseline map read. Its receipt records no package body entry,
asset open, engine, method or private read. It does **not** identify the failing
predicate or establish zero distribution-discovery activity. Map file-identity
checks, complete-group comparisons and early discovery predicates can all
precede populated package inventory counters. Do not infer an interpreter,
stdlib or package difference from the stage label alone.

Retain every existing input/control pin, especially:

| Immutable input | SHA-256 |
| --- | --- |
| V9 bootstrap | c8de911c9d62b389b04beafb08aa5c30beb72c1898190177190e764214cb922a |
| V9 result | 334149f00090c18d6f51baf84d05d94844a15aece74da43aeb1282cf87b87fb3 |
| V9 validation | 53041673f137ae1613570cfcc881327fb70c10c3b7f224a4a924d04f74cee6e6 |
| V10 bootstrap | 4e599c07d3fad2aabc6982383dbbc92dc9796136f388263045e59593cfcc4d8c |
| V10 source | bd42ce6c91e1733f2fd0e849fae43d090849453c89c4a6f302c714f04d1dd633 |
| V10 method, provenance only; never supplied or compiled | f85e00a2a2d0b64b9af7369be1ef6d564d5b28aa2dbd5d791f53f0dbd656ffe1 |
| V10 source freeze | ae6135ab45ffaf23c85af2df63bbd1ebc574d390e8362cabf1cd7d3db5a846fb |
| V10 refusal result | 3e0caa5234b3bd1842e70cab0626929ea0ed044b59960fc03da84411c13fb193 |
| V10 analysis-not-evaluated record | 7851369cee4966e0302ede5123da07c4e28f9e91b7bf14893984ed1d38293ff3 |
| V10 edges-not-evaluated record | d9df19be8b727d623f29edbef6fbddca13a15e03a49a7175eb47162e48868d45 |
| V10 validation at design parent | e7e51748d9f3daa99e2df563eb4b4621cbed3caf4e9856cca1886902e59ce7a0 |
| V10 public refusal verifier | 74ed48cf5a2214b3f4cd34dda11c4f603d0149dfa9ed85ac74c2fc0c5933864c |

The expected tool object is copied losslessly from accepted V9, canonical
SHA-256 `4baaa1020f2d895a688c6675b5091aed77d63d3a9ad9103316c4dbb6e830b639`.
Retain [Amendment 24](AMENDMENT-24.md), [Amendment 25](AMENDMENT-25.md) and
[Amendment 26](AMENDMENT-26.md) pins. Those consumed runs are not renewed.
No previous raw output, target bytes or excluded provisional evidence is an input.

Astra Medium owns the observation/predicate uncertainty; Sol Medium reviews;
`/root` integrates and owns workflow measurement. Design owns only this file
and minimal `WORK_ITEM.md`/`inputs.json` updates. Future separately dispatched
construction/execution owns exactly `inventory-diagnostic-v1.json`,
`inventory-diagnostic-result-v1.json`, `INVENTORY-DIAGNOSTIC.md`, an assert-free
`verify-inventory-diagnostic.py`, and authorized work-item/input pins.
No old source/result/method, hardware/support, roadmap, queue or ledger edits.
A future execution dispatch must name its sole RE-VM custodian.

## Source-first boundary and one run

Freeze complete independent source, source SHA-256, exact dispatch/input/
contract/dependency identities, expected tool object, predicate manifest,
I/O route/counter manifest, source-only AST delta report, output schema and UTC
in `inventory-diagnostic-v1.json`. Publish and independently review that
complete container before execution. Record its digest externally in the
result. No expected value may be replaced with a new observation.

The only future mode is `inventory-diagnostic`, with exactly
`/usr/bin/python3.12 -I -S -B - inventory-diagnostic` through the approved
`./scripts/dev-vm re-shell` path. Exactly one fresh isolated process and one
stdout/stderr collector are admitted by a subsequent dispatch. No method
descriptor, private path argument, second mode, fixture, probe or rehearsal.
A refusal, exception or successful diagnostic consumes that one-run budget.

Derive the technical prefix from immutable V10. Keep its initial `import sys`
and complete helper import statements/order exactly, including unused names.
Do not add a helper import, warm-up, package import or native preload to make
the initial inventory match. Removing dormant analysis/queue/resource/package
loader code and constants may change memory layout; that is not file drift.
Remove their invocable routes completely. Keep only inert zero counters needed
to prove their absence. There is no `ELFFile` class import/instance, Capstone
engine/version/decoder call, resource or queue request, `needed()`, source AST
parse, target parser, callback compiler, method pipe or private path/read.

The initial audit hook precedes helper imports as in V10. Instrumentation may
add only builtin counter/closed-label bookkeeping before them. The trust
boundary remains the pinned interpreter and inherited standard-library
bootstrap; do not claim that the hook observes interpreter startup before its
installation. There are no package-source compile/exec routes. Normal cached/
source stdlib helper imports retain their existing bootstrap role, not authority
to execute installed Capstone/pyelftools source.

## Preserve order; identify every predicate

Retain outer `startup`, then `initial-inventory`; stop at the latter's end.
No later V10 stage runs. The diagnostic may wrap the whole startup in a
payload-free terminal handler so early failures also receive a receipt.
Argument-shape validation uses only `sys` and builtins. The original technical
operation order remains: helper imports; isolation/version/module checks;
saved live import/path/meta-path/hooks/profile state; interpreter identity;
root derivation; main startup invariants; stdlib inventory; baseline maps;
three accepted-group comparisons; Capstone then pyelftools legacy discovery;
source cardinalities; legacy/distribution equality.

Freeze stable predicate IDs for **every** explicit V10 `require()` reachable
through that prefix, not just each function. Split boolean conjunctions in
their original left-to-right, short-circuit order into labeled subpredicates.
Preserve the original values, iteration order, repeated reads and comparisons.
Do not sort the sys.modules traversal or deduplicate mapped-file identity
calls to improve counts. A label is set before each operation; nested helper
checks retain caller, operation and bounded ordinal. Never serialize the
original error message, exception payload, arbitrary path or source text.

| Ordered phase | Required closed sub-stage boundary |
| --- | --- |
| startup | argument schema; helper startup; isolated flags/version; forbidden module checks; original object/profile checks; interpreter identity; installed-root derivation; embedded expected identity digest |
| stdlib collection | module snapshot and each `__file__`/`__cached__` probe; existing regular-file test; installed-origin test; every nested identity predicate; collected unique-key set |
| baseline maps | exact single snapshot sequence/open/read; byte/row/field/range/path grammar; early queue absence; pseudo/vDSO predicates; each mapped-file identity; unique native-file cap |
| accepted groups | interpreter equality, then stdlib equality, then baseline-native equality; each with key-set, individual field comparison and canonical digest result from already-read data |
| Capstone discovery | entered-call marker; candidate iteration/name access; unique/version predicate; selected root and directory checks; metadata containment/tree; metadata-name uniqueness; explicit email parse/name/version; package tree; each source namespace/module collision/read; initializer presence; distribution-file inventory state |
| pyelftools discovery | the same sequence, only if every Capstone predicate passed |
| inventory completion | source counts 25/52 and mapped-source count 77; exact LEGACY equality then DISTRIBUTIONS equality, split by ordered package/group; success receipt |

`identity()` distinctions must include regular-kind, nonsymlink, absolute,
canonical path and bounded content read/hash. Record left-to-right behavior
of `is_symlink()` and `resolve()`, not an assumed one-stat implementation.
`tree_inventory()` distinctions include entry/file/source/inert/bytecode caps,
case-fold/inode collisions, containment/canonicality, file kind/link/execute
bits, source signature and metadata fields. Iteration failure receives the
current iterator/call predicate, even before its first yielded entry.

Increment discovery-attempt and completion counters explicitly at each of the
two literal calls. Zero discovery is reportable only when its attempt counter
is zero. Preserve `("capstone","capstone","4.0.2")` then
`("pyelftools","elftools","0.30")`; never query a third target or substitute a
direct metadata reader for V10's discovery selection.

Comparisons may explain the already captured mismatch using bounded pure
in-memory operations before latching refusal. They must not run another
filesystem read, later comparison group or discovery call after a false
predicate. Extra/missing keys and unequal fields are observations, not new
accepted expectations.

## Bounded I/O and exact counter meanings

There is exactly one baseline `/proc/self/maps` open/read, retaining V10's
512 KiB exclusive byte bound, 256 rows, 1,024 bytes per row, 512-byte path
bound, strict grammar, one exact 4-KiB executable vDSO and at most 32 pseudo
rows/128 unique file paths. Do not read maps again during cleanup or claim
within-process stability across an unperformed second snapshot.

Keep the accepted 221 unique stdlib identities and 18 baseline native
identities as expectations, not assumed observed counts. Expected file
references have stable indices in a sorted frozen path pool. Extra live
module/file keys are reported without public path text. An unexpected path
outside the inherited installed roots, symlink, special file, deleted mapping,
archive provider or unsupported read interface is a diagnostic safety refusal.

All **post-helper content routes**, including transitive stdlib metadata
reads, must use counted bounded read handles: instrument the exact
`builtins.open`/`io.open` routes used by the frozen prefix, saving and restoring
their original objects. No generic alternate reader, `os.open/read`, mmap,
archive/decompression, supplementary metadata provider or descriptor input is
allowed. The maps route is the sole proc-file exception. Freeze the reader
proxy's complete explicit API/data flow; `read`, `readline`, iteration,
`seek`, `tell`, context/close and any actually necessary text-wrapper
operations must remain finite and counted. An undeclared method refuses before
delegation; never forward arbitrary attributes. Preserve text decoding semantics
of the inherited metadata calls. Proxy construction is not package entry.

For regular files: require bounded pre-open metadata, one read-only open,
opened-fstat equality, bounded reads with one sentinel allowance, and final
fstat equality; no symlink-following or retry after short/error/drift.
A whole-file `read()` is replaced by the frozen finite cap-plus-sentinel read,
not an unbounded delegated read. Retain duplicate application reads where V10
performs them, but never add a reread for reporting or drift explanation.
Source-prefix classification retains V10's full source read followed by
`[:16]`; the inert-prefix route remains a 16-byte read.

The source freeze must enumerate all direct open/read/stat/hash sites and
reader-proxy APIs. Counters distinguish attempted/completed/failed
application opens/reads/closes, audit-open events, bytes returned, SHA-256
operations/bytes, explicit `stat/lstat/fstat/is_file/is_symlink/resolve`
calls and directory/iterator operations, by phase and frozen role.
Nested stdlib `resolve` or importlib metadata operations are not silently
counted as one OS stat/syscall: report their API boundary and the separately
observed audit/handle operations. Helper-startup audit-open counts are separate
from the post-helper reader totals. The diagnostic does not promise kernel
syscall counts or pre-hook observations.

Prospective hard caps, checked before advancing/delegating, are:

| Counter/input | Bound |
| --- | ---: |
| modules in the stdlib snapshot | 512 |
| file/cache attributes probed | 1,024 |
| initial installed roots | at most 3, exactly V10's derived set |
| entries returned per discovery root enumeration | 4,096 |
| distributions examined per literal discovery call | 1,024 |
| opened regular-file size | 64 MiB |
| metadata-text size per file | 1 MiB |
| total post-helper content opens / application read calls | 4,096 / 16,384 |
| total returned content bytes / bytes hashed | 1 GiB / 1 GiB |
| explicit stat-family calls / directory entries visited | 65,536 / 16,384 |
| closed operation/predicate events retained | 8,192 |
| public serialized receipt | 256 KiB |

Metadata enumeration must be bounded **before** materializing an unbounded
directory listing or complete file read. A narrow counted directory adapter
may use the already imported `os.scandir` to bound V10's list-producing
metadata enumeration; preserve yielded ordering and path/provider semantics,
and freeze that explicit adapter plus restoration. If this cannot be done
without a new import, provider, package execution, extra input or unsupported
API, stop construction and escalate; do not weaken the bound. Label new
reader/enumeration safety failures as `diagnostic-boundary`, not as a proved
original V10 mismatch. No run is necessary to discover a static API ambiguity.

Retain V10's selected tree caps: Capstone `(512,256,96,64,192)`, pyelftools
`(768,512,384,128,64)`; metadata trees at most 32 entries/16 files.
Accepted first-pass facts are 7 metadata files, 77 sources, 14 inert assets
and 77 stat-only bytecode entries. Thus successful direct tree/source work has
231 full source reads, 14 inert full hashes plus 14 inert 16-byte reads,
91 prefix classifications and two explicit email Parser/parsestr calls.
There are seven direct metadata identity reads and two explicit metadata text
reads, **in addition to** bounded transitive discovery/name/version/files
metadata accesses. Do not invent a fixed count for those transitive accesses;
freeze their bounded routes, measure their exact attempts/completions and
reconcile audit totals against handle/direct-route counters.

No source bytes, bytecode, archive or signature-classified asset may execute.
Selected package .pyc files stay stat-only. Metadata reads of other installed
distributions are only the bounded original name-selection prefix, not source
inspection or permission to publish their names. Successful selection retains
the existing `d.metadata/version/locate_file/_path/files` routes and two
explicit selected email parses. No CSV/RECORD/base64 endpoint, JSON input
parser, native ELF metadata parser or target parser is added.

## Audit, relational observations and safe output

Keep the irreversible audit latch. Reject target-package imports/compile/exec,
resource/queue/optional routes, non-helper native loads, filesystem writes,
network/process operations, and reads outside the active frozen role. Inert
asset hashing does not admit loading. Standard-library bootstrap import events
and the original ctypes helper initialization retain only their exact inherited
phase; no later ctypes load is allowed. No source-finder/loader or profile is
installed. Do not use an existing broad read allowance to bypass the new
post-helper counted reader gate.

Do not compare addresses or object IDs from different processes. V10/V9
file-content/path/size/mode/mtime expectations are stable comparisons; vDSO
base, anonymous rows, heap size, object pointers and live container addresses
are not. Validate current map shape and compare frozen file identity groups.
Object preservation/restoration is equality to saved objects within this
single process only. Publish relational booleans, counts and stable canonical
digests, never ASLR bases, full maps or object pointers. A new process cannot
identify V10's unrecorded live objects.

For each reached comparison group publish its closed name, evaluated/equal
state, expected and observed count/canonical digest and bounded mismatch
summary. At most eight mismatches: known frozen path index, closed field mask,
expected/observed content hash, size/mode/mtime where safe. Extra unknown
paths get count and a canonical aggregate digest only, never names; no
unrelated path list, metadata text, source text, exception payload or raw log
is public. Overflow is terminal, not a truncated success. Preserve source,
dispatch, expected-input, accepted-result and raw-log hashes.

The first failure contains only fixed outer/substage/predicate IDs, role,
bounded ordinals and `validation-failure`, `diagnostic-boundary`,
`audit-rejection` or `internal-exception`. On the first false predicate,
latch it before any later normal operation; mark later stages not evaluated.
Do not continue other groups to complete a matrix. A passed prefix is not
an accepted environment, usable tool preflight, private-analysis admission,
binary attribution, runtime or hardware-support result. If the whole initial
prefix passes, report `initial-inventory-not-reproduced` and stop.

## Cleanup, verification and final handoff

Restore only diagnostic-owned reader/directory wrappers and verify saved
import/path/meta-path/hooks/profile identities without installing replacements
for untouched objects. Close all owned handles, then exit child and RE shell;
the audit hook cannot be removed. Cleanup has no content/map read and cannot
overwrite the first failure. No secure-memory-erasure claim.

The outer collector retains only stdout/stderr as two mode-0600 files in one
fresh mode-0700 child below the existing managed RE root, with immediate
cleanup handling and private retention of unique raw logs. No package/input
copy, cache, database or extra pipe is created. Preserve raw hashes privately;
never clean the sole unique evidence. Disable network/download/debuginfod and
bytecode behavior as in the accepted protocols. Release named custody before
host result construction.

Freeze the sanitized result before writing its public assert-free verifier.
Normal and optimized verification must cover identities, exact predicate/
operation order, first-refusal propagation, evaluated/unevaluated comparisons,
bounds and counter reconciliation, pure-memory mismatch summaries, relational
map/object checks, all zero forbidden routes, no-partial promotion, cleanup
and authority. Mutations must rebind receipt hashes when testing semantics
so hash mismatch alone is not the rejection. No synthetic parser/decoder or
guest fixture runs. Source construction requires host-only syntax/AST/data-flow
review of the complete retained prefix, adapters and removed forbidden routes.

The design check is source/metadata-only: 107 existing pins, exact V10 AST
operation order, accepted inventory arithmetic and complete local links.
No source candidate, VM, private read, package body, build, device operation,
commit or push occurred. The design hands off for independent review; future
construction and execution each require their own bounded dispatch. Credits
are unavailable; measurement and publication remain with the integrator.
