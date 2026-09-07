# Captured extension-path stat-only diagnostic amendment

This twentieth prospective amendment resolves only the pre-open validation
refusal in [EXTENSION-EVENT-DIAGNOSTIC.md](EXTENSION-EVENT-DIAGNOSTIC.md).
The v1 diagnostic trio remains immutable. It captured the first refused event
as module `_queue` with lexical filename
`/usr/lib/python3.12/lib-dynload/_queue.cpython-312-aarch64-linux-gnu.so`, then
refused before candidate or maps opens. It did not establish canonicality,
symlink status, file kind, mode, size, identity, ELF format or mapping absence.
No extension was loaded and the single private analysis remains unused.

Before this diagnostic, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier controlling artifacts and the complete v1 extension-event diagnostic
trio. Reject drift.

## One exact stat-only probe

Create and freeze `extension-path-stat-diagnostic-v1.json` containing the
complete independently written source and embedded SHA-256 before first
execution. Run it exactly once with `/usr/bin/python3.12 -I -S -B` through the
approved RE-VM shell. Its sole target is the exact captured lexical filename
above. Do not import `_queue`, resolve a module spec, open the candidate, read
candidate bytes, inspect mappings or reproduce package execution.

Preload only the frozen standard-library helpers required for path, stat,
bounded JSON and hashing operations, then install an irreversible audit hook
before any target metadata operation. From that point through exit, require
zero `open`, import, dynamic-load, write/mutation, socket/network, subprocess,
shell or fork events. Record only closed event-class counters; reject any
nonzero counter. No command or external utility is admitted.

Validate the exact ASCII target string and Amendment 19's numeric lexical
bounds first. In each observation pass, walk its path components from `/` with
a separately counted maximum of eight `lstat` calls. Retain internally the full
permitted stat tuple for cross-pass comparison; publish for each component only
its absolute system path, kind enum `directory`/`regular`/`symlink`/`other`,
permission bits and whether it is a symlink. In the first pass, a first missing
result must be repeated against the identical component: two matching
`FileNotFoundError` or
`NotADirectoryError` classes are a stable complete-negative result; a changed
result is drift. Any other exception is a closed metadata-error refusal. Do not
retain dynamic exception text.

In each pass, compute the strict real path without opening the target. Use a
directly implemented component resolver through counted `lstat` and `readlink`
wrappers; do not call `pathlib.Path.resolve`, `os.path.realpath` or another
helper whose internal metadata operations are not counted. Per pass, permit at
most 32 resolver `lstat` calls, eight `readlink` calls, eight symlink expansions
and 32 processed components. Retain every permitted resolver stat tuple and the
ordered bounded symlink trace internally. Every immediate link text must be
ASCII and at most 512 bytes;
after every absolute or relative substitution, the normalized pending/result
path must remain absolute, at most 512 ASCII bytes and free of `.`/`..`.
A repeated stable missing class while resolving is a complete-negative strict-
resolution result; a changed result is drift and any other exception is a
closed metadata-error refusal. Require a successful result to be beneath
`/usr/lib` or `/usr/local/lib`. Stage 2 ends after resolver success and
installed-root containment; it does not classify equality with the captured
path. At stage 3, record and compare that equality together with the captured
final component's independently observed symlink status. For at most eight
resolved symlinks, record only the component path and immediate bounded link
text. Do not call the captured name canonical merely because resolution
succeeds.

After a successful first component walk and strict resolution, take exactly two
separately counted `lstat` snapshots of the captured path and, when different,
exactly two separately counted snapshots of the resolved path. Each snapshot
may contain only device, inode, file-type/permission mode, link count, size,
mtime ns and ctime ns. Require each pair identical. Then repeat the complete
component walk and strict resolver as a second observation pass. Require exact
equality of the two passes' ordered component paths and full stat tuples,
ordered resolver paths and full stat tuples, resolved path, symlink component
paths and immediate link texts. Also require the captured snapshots to equal
the corresponding final lexical-component tuples and, when different, the
resolved snapshots to equal the corresponding final resolved-target tuples in
both passes. Any second-pass missing result, exception or mismatch is drift or
the applicable closed metadata-error refusal, never a complete-negative.

The closed operation counters are therefore per-pass
`component_lstat <= 8`, `resolution_lstat <= 32`, `readlink <= 8`,
`symlink_expansions <= 8` and `processed_components <= 32`, with successful
two-pass totals bounded by 16, 64, 16, 16 and 64 respectively.
`captured_snapshot_lstat` is in `{0, 2}` and `resolved_snapshot_lstat` is in
`{0, 2}`, with at most 82 aggregate `lstat` calls. Snapshot and second-pass
counts are zero only after a first-pass complete-negative or refusal; otherwise
the captured count is two, the resolved count is two exactly when the paths
differ, and both observation passes must be complete. A missing or changed
snapshot after first-pass success is drift, not a new missing-file predicate.
Classify independently and in fixed order:

1. lexical/path-component validation;
2. strict resolution and installed-root containment;
3. captured-path canonicality and final-component symlink status;
4. resolved target existence and regular-file kind;
5. exact permission comparison with `0644`; and
6. size comparison with the 1 MiB diagnostic bound.

Return a stage-coded complete result even when a comparison is false. Use this
closed status table:

| Observation | Status | First stage |
| --- | --- | --- |
| stable missing lexical component | `complete-negative` | 1 |
| stable missing symlink target during strict resolution | `complete-negative` | 2 |
| resolved path outside the two installed roots | `complete-negative` | 2 |
| resolved path differs from the captured path or its final component is a symlink | `complete-negative` | 3 |
| resolved target is nonregular | `complete-negative` | 4 |
| resolved regular file mode differs from `0644` | `complete-negative` | 5 |
| resolved regular file exceeds 1 MiB | `complete-negative` | 6 |
| all six predicates true | `complete-positive` | none |
| audit activity, counter/bound/schema failure, non-ASCII value, metadata exception outside the two admitted missing classes, or any repeated/snapshot mismatch | `refused` | closed refusal stage |

Populate later predicates as `not-evaluated` after the first false predicate;
never relabel a stable false predicate as a harness refusal. Record exception
classes only through the closed missing/refusal enums above. The diagnostic
succeeds when it deterministically identifies the first false predicate or
proves all six metadata predicates.

Write only `extension-path-stat-diagnostic-result-v1.json` and
`EXTENSION-PATH-STAT-DIAGNOSTIC.md`, with script/result hashes, UTC chronology,
the closed classification, bounded metadata snapshots, audit counters and
`private_reads: 0`. Publish no candidate bytes/hash/ELF content, virtual
address, package source, credentials, private path or dynamic exception text.

Stop after the one diagnostic. Its result may explain which pre-open predicate
blocked Amendment 19 and may establish a stable canonical target path, but it
does not establish content identity, ELF/dependency structure, mapping state,
successful extension loading or package usability. A later prospective review
must decide whether a bounded content/ELF inspection of the resolved regular
file is warranted. No package execution, engine, method, callback, private
analysis, acquisition, network, device action or build is admitted.
