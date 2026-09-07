# Prospective V10 retained-instruction analysis contract

Design parent: `3edf660c1ff2c47b8b5404cf261fbffd3e7cc71f`, verified clean
and equal to `origin/main`. This document does not execute or admit a run by
itself. A separate owner dispatch, source/method freeze and independent static
review are required. V9 remains accepted, immutable and consumed. No old
two-mode bootstrap or unexecuted analysis branch is renewed wholesale.

## Exact inputs and ownership

Preserve every dependency/control pin in [inputs.json](inputs.json). In
particular, the complete V9 container/result/validation SHA-256 values are
`c8de911c9d62b389b04beafb08aa5c30beb72c1898190177190e764214cb922a`,
`334149f00090c18d6f51baf84d05d94844a15aece74da43aeb1282cf87b87fb3`, and
`53041673f137ae1613570cfcc881327fb70c10c3b7f224a4a924d04f74cee6e6`.
V9 embedded source SHA-256 is
`d1e807146ab4983142e817bec3be79fb6db5894bb9ebd74f2fb09759c25301e1`.
[Amendment 24](AMENDMENT-24.md) and [Amendment 25](AMENDMENT-25.md) retain
their pinned identities and govern the inherited tools phase except the
explicit deltas below. Copy literal expected tool/file/module identities from
the accepted receipt into the freeze; never replace expectations from the
new process's observations. Process-local objects and randomized map bases
are checked relationally, not against pointers from V9.

The sole private input remains SHA-256
`cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`.
The accepted v3 `intervals.json`, SHA-256
`e44de0d978edbaaccc5f5d05afc5fc913bd691c2ab56e2e03c02edbc23ebef0c`,
and its already pinned provenance are the sole envelope authority. No new
Kallsyms loader, reconstruction, excluded provisional tuple or previous raw
output is an input. Public accepted metadata may be embedded losslessly in
the frozen method; source dependencies supply context, not replacement edges.

Astra Medium designs the named integration/control-flow uncertainty; Sol
Medium reviews; `/root` integrates and owns workflow measurement. This design
owns only this amendment and minimal work-item/input updates. A future dispatch
must name one RE-VM custodian and separately authorize construction of
`bootstrap-v10.json`, `method.json`, `FREEZE.md`, `bootstrap-v10-result.json`,
`analysis.json`, `edges.json`, `verify-result.py`, `VALIDATION-RESULT.md` and
the final experiment `README.md`, plus state pins. No dependency or shared
project file is implementation-owned. This design creates none of those files.

## Freeze and execution chronology

1. Verify the exact clean published dispatch parent, this contract and all
   pins. Derive V10 only from V9 with a reviewed AST/data-flow delta inventory.
   V10 has one `analysis` mode; reject other/missing modes and extra arguments
   before package entry. No separately executable preflight/diagnostic mode.
2. Freeze complete bootstrap source, its SHA-256, dispatch/input/control/tool
   identities, argument schema, operation budgets and UTC in
   `bootstrap-v10.json`. Then freeze complete independent method source,
   source SHA-256, bootstrap container/source hashes, accepted interval data,
   expected tool identities, closed result schema and exact parser/API routes
   in `method.json`. Neither source contains a self-referential container hash.
   Record both complete container hashes externally in `FREEZE.md` and pass
   the expected method container hash through the frozen invocation. No
   observations may change an expected digest or either source after freeze.
3. Independently review source-only AST/data flow, syntax under normal and
   optimized Python, bounds and refusal paths. Publish the source/method freeze
   before the run when practical; otherwise record their immutable hashes and
   review-ready UTC before invocation, and preserve that exact source-first
   chronology in the later publication. No guest rehearsal, synthetic ELF,
   package probe, alternate binary or method fixture execution is admitted.
4. Dispatch exactly one isolated Python 3.12 analysis process through
   `./scripts/dev-vm re-shell`, using `/usr/bin/python3.12 -I -S -B - analysis`
   with only the frozen descriptor/hash schema. Disable network, downloads,
   debuginfod and bytecode. The bootstrap source enters through stdin; one
   inherited read-only method pipe supplies the exact bounded method container
   once. Its descriptor is not a filesystem path. The sole private path is
   passed privately and never serialized publicly. A failure consumes the run;
   no repair/retry or second private input read follows.

The method pipe is read only after `post-engine` succeeds, not during resource
or queue setup. Set its cap to 1 MiB plus one sentinel byte, require EOF within
1 MiB, verify the externally frozen whole-container hash before exactly one
bootstrap-owned `json.loads`, reject duplicate keys and unknown schema fields,
then verify the embedded source hash and all linked identities. Exactly one
method `compile` and one `exec` may create exactly one entry callback. Freeze
the compilation filename/flags and explicit namespace; reject imports,
top-level effects beyond function/constant definitions, generic dispatch,
dynamic evaluators and additional compiler inputs. Record runtime code digest
as an observation bound to that verified source, not an invented pre-run hash.
The callback is invoked exactly once, after pre-analysis gates. Nested helper
construction and every direct parser/decoder API must be enumerated in the
source freeze; no undeclared helper, package API or import route is admitted.

## V9 lifecycle retained; exhaustive new routes

Preserve V9 helper import statements/order, dual inventories, source-forced
finder/loader, installed roots, native/resource identities, optional route,
one Capstone ARM64 little-endian detail-enabled engine, one queue preload,
cached queue wrapper, resource profile and one page-size reference. Preserve
the exact 12 queue stages and all their overlay/event/stat/module predicates.
Method pipe/compile/callback/private/parser/decode counters remain zero through
`post-engine`. In particular, the resource pre-call observer still sees the
same zero-analysis state as V9; no earlier method loading is reintroduced.

Keep all 20 outer V9 stages in order. Insert only `method-freeze`,
`pre-analysis-drift`, `pre-analysis-maps`, `private-read`, `analysis-callback`,
`post-analysis-integrity`, `post-analysis-maps` between `post-engine` and
`named-restoration`. The irreversible audit hook stays active throughout.
The final V9 component/tree/maps/stdlib checks and named restorations run
after analysis, not before it. Preserve their original code and exact
profile install/restore counts. No second engine, resource invocation,
preload, optional route, package discovery, package-source compilation or module
entry is allowed during the new phase. Require the exact V9 completed-entry
set (25 Capstone and 48 pyelftools) and identities before method loading;
the four other inventoried sources remain unentered. A newly demanded body
is a refusal, not permission to expand the environment.

The two new map stages use the unchanged strict maps reader and queue-extended
baseline. Therefore successful maps reads increase from 13 to **15**; candidate
content checks increase from 17 to **25**, with exactly four at each new
stage. Candidate totals become `lstat=54`, `fstat=50`, `content_open=25`,
`content_read=25`. The unchanged final-component check is already included.
Every new read retains the same exact tuple/hash and per-operation counters;
no new candidate ELF parse. Queue wrapper/delegation remain `1/1`, extension
event one, wrapped cached requests `0..8`; no claim of a literal package join.

`pre-analysis-drift` adds exactly one existing complete legacy tree/signature
and standard-library drift pass, and checks already frozen component/module/
engine/resource/queue object identities without reconstructing them. The
candidate content checks occur only in the named map/final-component sites,
not these object checks. Asset phase opens become `28/28/28/28` for
initial/pre-import/pre-analysis/final. Prefix signature calls become **364**
(four passes over 91 entries). The explicit two email parses, 56 frozen-source
AST parses and two native `needed()` routes remain unchanged. No additional
explicit bootstrap AST parse is required: method AST review occurs on host.
The new method JSON parse, method compile/exec, private buffer, `BytesIO` and
ELF/instruction routes are the only additions to Amendment 25's exhaustive
boundary. CSV/RECORD/base64 and obsolete discovery routes stay absent.

## Exactly one private open/read and one parser lifetime

Before content access require unchanged frozen tools, module set, engine,
resource-returned state, queue objects and maps. Validate each private path
component as nonsymlink and the final file as regular using bounded metadata
only. Open that exact file read-only with no-follow semantics exactly once;
compare pre-open `lstat` to opened `fstat` (device, inode, mode, link count,
size, mtime_ns, ctime_ns). Require positive size at most **64 MiB**. This is
a prospective safety cap, not a claim about the retained ELF's recorded size.
Perform exactly one counted high-level `read(64 MiB + 1)` through that handle;
require returned length equals the pinned-by-stat size, below the cap, and
the entire buffer SHA-256 equals the sole admitted ELF hash. This budget is
one application read, not a claim that buffering uses one OS syscall.
No second EOF read, seek/re-read, chunk loop, mmap, reopen or external copy.
Check descriptor stat after read and again after callback, final path `lstat`,
and buffer hash after callback; close the descriptor on success or refusal.
The content identity comes from the complete digest, not the size cap.

Construct exactly one in-memory `io.BytesIO` over that verified immutable
buffer and exactly one already imported `ELFFile` object; both live for the
one callback. Parser seeks/reads are memory-only and separately counted from
the one private filesystem read. The independent raw parser uses only bounded
`struct.unpack_from`/slices on the same buffer; no second parser object,
reconstruction or database. The source freeze must enumerate ELFFile and
section/symbol/relocation methods and iterator counts, plus raw header/table
formats and range checks. Refuse any route requiring a new import, compressed
section decompression, archive parsing, supplementary file, DWARF, debug link
or external string/symbol lookup. On refusal do not print exception payloads,
bytes, disassembly or private path information.

Independently check ELF64/little-endian/AArch64/ET_EXEC, release-family marker,
table extents/entry sizes/links and the exact `.kernel` tuple from inputs.
Reject integer wrap, overlap/ambiguous mapping, out-of-file tables, unsupported
extended numbering or malformed strings before affected parsing. Raw header/
section/symbol metadata and pyelftools must agree. Iterate the retained symbol
table once, bounded by its validated file extent; require the four unique
starts/type/binding/section/zero-size tuples already accepted in v3. Nearest
labels for candidates are metadata from this same table, not new envelopes.

For each accepted range require exact start/end/length and `.kernel`
containment, and independently agree on file offset and VA conversion. Record
range hash/size and the complete `.kernel` hash/size, never bytes. Rehashing
in-memory ranges does not consume another private read. Accepted ranges are:

| Symbol | Start | Exclusive boundary | Bytes |
| --- | --- | --- | --- |
| `do_connectivity_driver_init` | `0xffffffc0006e3a70` | `0xffffffc0006e3be0` | 368 |
| `do_wlan_drv_init` | `0xffffffc0006e3ed0` | `0xffffffc0006e3fe8` | 280 |
| `mtk_wcn_wlan_gen3_init` | `0xffffffc0007415a0` | `0xffffffc000741898` | 760 |
| `mtk_wcn_wlan_gen3_exit` | `0xffffffc000741898` | `0xffffffc000741938` | 160 |

## Decoding, traversal and scans

Decode exactly the 392 aligned words in those four envelopes once each with
the retained engine (one bounded one-instruction disassembly request per
word) and the independent fixed-mask decoder; traversal reuses these records.
Require width/address, control-flow class, mnemonic and signed immediate
agreement for `B`, `BL`, `B.cond`, `CBZ/CBNZ`, `TBZ/TBNZ`, `BR`, `BLR`, `RET`
and exception/terminal classes. The frozen method must explicitly enumerate
all supported terminal masks and Capstone groups; an unsupported branch or
interrupt is refusal, never implicit fallthrough. No publication of the
underlying instruction words or operand text. Non-control words fall through
four bytes without inferred dataflow/effects.

Retain the original entry-only four traversals, 512 reachable-address and
128-basic-block caps per target, deterministic ascending pending-address order,
and sixteen total reachable direct calls. A reachable `BL` records its exact
target and continues; conditional edges follow both paths; direct in-range
branches follow the target; out-of-range `B` is only a tail candidate. `RET`
or supported terminal ends its path. `BR` ends unresolved; `BLR` records an
unresolved indirect call and continues. Such correctly decoded indirect
instructions are expected bounded uncertainty, not a decode failure. They
cannot support a complete-effects, complete-return or teardown-safety claim.
Boundary fallthrough, unaligned target, inconsistent overlap, decode conflict,
unclassified control flow or cap overflow is a terminal refusal. Do not
continue with other targets/scans after that refusal.

An init-chain edge requires a reachable agreed `BL` exactly targeting the
accepted next entry. Exit callees require the same reachability and exact
retained symbol-start equality; unmatched targets remain unnamed direct
targets, not invented functions. A missing edge after a complete traversal is
a bounded negative, not an error. Publish all reachable direct targets within
the sixteen-call cap, including unmatched ones.

Retain one raw aligned `.kernel` BL scan (**5,003,312** words), one relocation
scan and one eight-byte-aligned exact-exit-address scan across file-backed
`SHF_ALLOC` sections. No Capstone decoding outside the four envelopes. Deduce
scan extents from validated tables and file bounds; record section counts,
word/record totals and completion. Never scan NOBITS as file content. Each
class permits at most eight candidates; stop at the ninth before continuing.
Only the proved reachable set may promote a BL encoding to a call. Raw
address words never prove address-taking/registration. Relocations are
candidates only where the frozen method explicitly supports exact symbol/
addend resolution; unsupported or ambiguous relocation interpretation refuses
that analysis, rather than being silently omitted. The method must enumerate
supported AArch64 relocation types/formulas before run. No ADR/ADRP, dataflow,
jump-table, unaligned, recursive caller or extra-body analysis.

## First refusal, artifacts and verification

Every guard/identity/mapping/decoder conflict, unexpected I/O/import, missing
method route or exceeded budget latches the first closed refusal class and
stage before operation; subsequent normal stages are `not-evaluated`. Retain
only a bounded partial receipt, not accepted partial semantic conclusions.
Expected bounded negatives/indirect uncertainty are explicit result states,
not permission to bypass a false predicate. Preserve V9's payload-free
terminal exception, package-boundary latch and independent named restoration
attempts. Refusal cleanup adds no content or maps reads; close the private
handle/pipe and release memory references, attempt applicable restorations,
then exit the interpreter and close the RE shell. Do not claim secure memory
erasure. A failed cleanup cannot overwrite the first refusal.

The outer collector captures only stdout/stderr in two named mode-0600 pipe
logs in one fresh mode-0700 managed RE-VM child, with cleanup handling installed
immediately. Preserve unique raw evidence privately with hashes and retention
location recorded privately; remove empty/partial regenerable staging after
classification, not the sole raw evidence. Child filesystem writes, sockets,
processes, downloads and additional inputs remain forbidden. No raw ELF,
disassembly, map bases, object pointers or private paths may enter public JSON.

Publish source/method identities and freeze chronology; lossless canonical
receipt/hash and raw-log hashes; all inherited/new stage/counter/restoration
results; parser/engine/callback counts; mappings/range hashes; per-target
decode/traversal status; exact direct edges and bounded candidates; and only
independently worded static conclusions. `bootstrap-v10-result.json` owns
environment/guard evidence, `analysis.json` owns mapping/decoding/traversal
evidence and `edges.json` owns derived edges/candidates with source-record
references. All three must cross-bind exact source/method/input identities.
Only an entirely passed lifecycle may report an accepted bounded analysis.
Successful construction/import/build is not hardware support.

Freeze the result files before writing the assert-free host verifier. Run it
normally and with `python -O` against only public receipts and source/container
identities. Predeclare mutations covering every identity/link, chronology,
parser/engine/callback/private counter, map/queue/resource budget, range/hash,
decoder agreement, traversal/refusal/boundary, edge/target/reachability,
candidate count/class/completion, cleanup and authority predicate. Record
actual cases/counts/results. A missing mutation family is incomplete validation;
do not rerun private analysis to repair it. This verifier checks internal
consistency and source-bound reported hashes, not independently recomputed
private-byte truth; explicitly retain that limitation and require Sol review
of the frozen method and derivations. No synthetic parser or decoder execution
is hidden in the host validation plan.

Rights remain unchanged: independently written method/tooling and sanitized
facts only; retained proprietary bytes stay private. No device, runtime,
firmware, radio, boot2, network, acquisition, build, upstream certification or
publication authority is added. Any unenumerated necessary API/format/input
or contradiction stops before execution and returns evidence, attempts,
unresolved question and the next discriminating check. Handoff ends this work;
future source construction/run requires its own dispatch.
