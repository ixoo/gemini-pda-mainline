# Latched pre-open and one-open extension identity amendment

This twenty-first prospective amendment follows the accepted
[Amendment 20 result](EXTENSION-PATH-STAT-DIAGNOSTIC.md). That stat-only run
proved that the exact `_queue` audit-event path currently resolves to itself,
has no symlink component, and is a stable regular mode-`0644` file of 68,496
bytes. It did not read the file or identify the historical Amendment 19
refusal.

A source-only audit of the immutable Amendment 19 diagnostic narrows that
refusal to `candidate_identity()` before its first `open`. The recorded terminal
signal, propagation, event digest and empty active-source stack satisfy the two
checks immediately before that call. The frozen `terminal_import` wrapper was
still installed with its terminal latch set; any later import would have raised
the dedicated terminal signal again. The broad handler retained neither this
possibility nor a path-predicate/metadata exception class or stage. This proves
a reporting defect, not which alternative occurred. Do not infer a filesystem
defect or relax the import guard.

Before this diagnostic, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier controls, both immutable Amendment 19 event artifacts, and the complete
accepted Amendment 20 trio. Reject drift.

## One sequential diagnostic

Create and freeze `extension-identity-diagnostic-v2.json` containing the
complete independently written source and embedded SHA-256 before first
execution. Run it exactly once with `/usr/bin/python3.12 -I -S -B` through the
approved RE-VM shell. Embed the exact accepted event path, event digest,
Amendment 20 result digest and complete accepted captured-path stat tuple. Do
not reproduce package execution, import `_queue`, resolve a module spec or call
a loader.

Preload only the frozen standard-library helpers required for path metadata,
bounded binary parsing, maps parsing, JSON, hashing and UTC time. Save the exact
original import function, install an irreversible audit hook, then install a
counted terminal import wrapper before any target metadata operation. The
wrapper must record only its call count and the current closed stage, then
raise a payload-free dedicated `BaseException` before delegating. No post-hook
helper import is allowed.

The audit hook admits no event until the content gate. At that gate it admits
exactly one read-only `open` of the exact candidate path, and afterward exactly
one read-only `open` of `/proc/self/maps`. It rejects before returning from any
overflow, write-capable open, import, dynamic load, mutation, socket/network,
subprocess/shell/fork or other event. Increment the appropriate closed counter
before every rejection. No command or external utility is admitted.

## Stage-preserving pre-open gate

Evaluate the frozen Amendment 19 pre-open operations one at a time with a
closed stage set: `path-object`, `absolute`, `strict-resolve`, `final-symlink`,
`first-lstat`, `kind`, `mode`, `size`, `second-lstat`, and `import-restoration`.
After each operation require the terminal-wrapper count remains zero. Require:

- the path is the exact bounded ASCII event path and absolute;
- strict resolution equals that path and the final component is nonsymlinked;
- both full `lstat` tuples equal one another and the exact accepted Amendment
  20 tuple, including device, inode, mode, link count, size, mtime ns and ctime
  ns; and
- regular-file kind, exact mode `0644` and size at most 1 MiB.

On a false comparison, return `complete-negative` with the first stage and stop
before content. On a terminal-wrapper signal, return `refused` with class
`latched-wrapper-reentry`, first wrapper stage and exact count one. On
`FileNotFoundError`, `NotADirectoryError`, `PermissionError`, another
`OSError`, an audit rejection or an internal/schema exception, return only the
corresponding closed refusal class and stage. Never retain dynamic exception
text. No catch may allow execution past the first failure.

After `import-restoration`, extend the same closed stage set in this exact
order: `candidate-open`, `opened-fstat`, `bounded-read`, `post-read-fstat`,
`final-lstat`, `elf-header`, `program-headers`, `dynamic-table`, `string-table`,
`needed-names`, `maps-open`, `maps-read`, `maps-parse`, `candidate-absence`, and
`final-audit`. A candidate-open/read/maps error, file-identity or metadata
drift, short/oversize read, malformed or out-of-bounds ELF structure,
non-ASCII/overflowing dependency name, maps bound/parse error, audit rejection,
counter mismatch or internal/schema failure is `refused` at that exact stage.
Do not publish a partial file or ELF identity from a refused path. If all prior
content and parser stages pass but the exact candidate is present in maps,
return `complete-negative` at `candidate-absence`, retain only the already
completed identity/ELF evidence, and make no absence claim. Passing every stage
is `complete-positive`. No catch may advance to a later stage after either
terminal status.

Only after every metadata stage passes, restore the exact original import
function and prove its object identity while the audit hook remains active.
Require wrapper count zero and all audit counters zero. This is the sequential
admission gate for the single content read; failure cannot consume or fall
through to that read.

## One-open identity and absence check

Open the candidate read-only exactly once. Match `fstat` to the accepted tuple,
read at most 1 MiB plus one byte, require EOF at the accepted size, and require
the same `fstat` before/after plus a final matching `lstat`. Hash and parse only
those retained public bytes. Require an exact 64-byte ELF64 little-endian
AArch64 `ET_DYN` header, program-header entry size 56 and 1–256 program headers.
Validate every offset/size using subtraction before addition or slicing; the
table and every file-backed segment must fit in the accepted candidate size.
Require exactly one dynamic segment with file size 16–65,536 bytes divisible by
16, at most 4,096 entries and one terminating `DT_NULL` within that segment.
Require exactly one `DT_STRTAB` and `DT_STRSZ`, a string-table size of 1–1,048,576
bytes, and exactly one file-backed load segment containing that virtual range;
validate its translated file range before slicing. Record at most eight unique
`DT_NEEDED` names, each 1–128 ASCII bytes matching `[A-Za-z0-9_.+-]+` and
terminated within the string table. Do not resolve, open, hash or load
dependencies.

Then open `/proc/self/maps` read-only exactly once, read at most 512 KiB, require
EOF, at most 256 strict rows and at most 1,024 bytes per row, and establish only
whether the exact candidate path is absent. Validate the address range,
permission field, hexadecimal offset, device major/minor, decimal inode and
optional absolute/pseudo path shape without retaining the rows. Do not publish
addresses, pointers, unrelated paths or a map dictionary. Require exact final
audit counts `candidate_open=1`, `maps_open=1`, and every
import/dynamic-load/write/mutation/network/process/other counter zero.

Write only `extension-identity-diagnostic-result-v2.json` and
`EXTENSION-IDENTITY-DIAGNOSTIC-2.md`, with source/result hashes, UTC chronology,
closed pre-open stage outcomes, wrapper and audit counters, sanitized file
identity/ELF/needed fields, mapping-absence boolean and `private_reads: 0`.
Publish no bytes, virtual address, raw maps row, dynamic exception text,
credentials or private path.

Stop after the one diagnostic. A positive result establishes only the current
exact installed extension's content identity, bounded ELF/dependency metadata
and absence from that isolated process's maps. It does not explain the earlier
transient/refused operation, load or initialize `_queue`, prove package
usability, admit a general extension route, or authorize the retained private
analysis. A refusal consumes the run budget and must not be retried. No engine,
method, callback, private content, acquisition, network, device action or build
is admitted.
