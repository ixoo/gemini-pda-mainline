# Exact extension-path stat-only diagnostic

## Result

**Complete-positive:** all six ordered metadata predicates passed in the single
[Amendment 20](AMENDMENT-20.md) execution. There is no first false predicate
or refusal stage.

The exact captured path,
`/usr/lib/python3.12/lib-dynload/_queue.cpython-312-aarch64-linux-gnu.so`,
resolved to itself. Every lexical/resolver component was nonsymlinked. The
target was one regular file, permission bits `0644`, size 68,496 bytes, within
the 1 MiB bound. Both complete observation passes and the two captured-path
snapshots matched exactly.

This is a current, bounded metadata observation—not a candidate content
identity. It does not establish which pre-open operation refused in the earlier
[extension-event diagnostic](EXTENSION-EVENT-DIAGNOSTIC.md). That earlier
receipt did not identify a failed predicate; there is no earlier recorded
metadata-negative result to contradict.

## Frozen inputs and chronology

- Published clean dispatch: `06d55bc2601c4f898121eec5ab288ee6ef8fc456`.
- Contract: [WORK_ITEM.md](WORK_ITEM.md),
  [Amendment 20](AMENDMENT-20.md), and every inherited pinned control.
- Dispatch [inputs.json](inputs.json) SHA-256:
  `14a232f79c7ce663fe9480a75216aa4856b878d2a9d6c8dccb46b5dd0ce6ecb0`.
  All 77 dispatch pins passed before construction/execution.
- [Frozen source container](extension-path-stat-diagnostic-v1.json) SHA-256:
  `4fb9bb6880b1a7450c778b27c5d6eb30eceb1711243ebddd35986d7afd1fc3ac`.
- Embedded source SHA-256:
  `208a35fe5666258ef7541dfa1d885fe18e6e082420635c5a03d3e864c949c15e`.
- Freeze: `2026-09-07 05:50:01 UTC`.
- Sole execution: `2026-09-07T05:50:36.382211+00:00` through
  `2026-09-07T05:50:36.382380+00:00`.
- [Complete sanitized result](extension-path-stat-diagnostic-result-v1.json)
  SHA-256:
  `be64ee02da0daa61068e3dfdf25972d52b2bd70370183817583b632a2e5155dc`.
- Canonical metadata-only receipt SHA-256:
  `7dc81c311ff7402df50a55eae5ab88620e0da2ecf233827490ea7d187e4086fa`.
  This hashes the serialized receipt, never candidate bytes.

The approved RE shell supplied the frozen source once on stdin to
`/usr/bin/python3.12 -I -S -B -`, with empty `DEBUGINFOD_URLS`,
no-user-site and no-bytecode environment controls. The source checked Python
3.12.3 and isolated/no-site/no-bytecode flags, preloaded only its named
standard-library helpers, then installed its irreversible audit hook before
target metadata operations. No guest source file was created. The interpreter
and outer RE shell exited normally.

The current inputs file adds the resulting trio and updated handoff-state
contract hash after execution. The dispatch hashes above remain the immutable
pre-execution references; this administrative update grants no further run.

The first host serialization draft rounded a large nanosecond integer and
failed the canonical receipt check. The intact original receipt independently
matched the child digest above. After escalation, the integration coordinator
confirmed the host-only lossless reserialization. Both captured snapshots retain
exact `ctime_ns: 1785067980603724344`, and the corrected published receipt
matches that same child digest. No source change, child rerun or target metadata
access was used for this host-only correction.

## Ordered classification

| Stage | Predicate | Result |
| --- | --- | --- |
| 1 | Exact lexical string and all path components | true |
| 2 | Strict counted resolution within installed roots | true |
| 3 | Resolved path equals captured path; final component nonsymlinked | true |
| 4 | Resolved target exists and is regular | true |
| 5 | Exact permission bits equal `0644` | true |
| 6 | Size at most 1 MiB | true |

Each pass observed the same six components: `/`, `/usr`, `/usr/lib`,
`/usr/lib/python3.12`, `/usr/lib/python3.12/lib-dynload` and the exact target.
The five directories had permission bits `0755`; the final component was
regular `0644`. No missing class, metadata exception or symlink text occurred.

The full permitted stat tuples were compared internally for every component and
resolver observation, including device, inode, mode, link count, size, mtime ns
and ctime ns. Only the allowed reduced component metadata is published in the
result. The separately permitted captured-path snapshot pair is also included;
both snapshots have size 68,496, link count 1 and
mtime 1781873160000000000 ns. There are no resolved-path snapshots because
the resolved path is identical to the captured path.

## Exact operation and audit counters

| Operation | Pass 1 | Pass 2 | Total |
| --- | ---: | ---: | ---: |
| component `lstat` | 6 | 6 | 12 |
| resolver `lstat` | 6 | 6 | 12 |
| `readlink` | 0 | 0 | 0 |
| symlink expansions | 0 | 0 | 0 |
| processed resolver components | 5 | 5 | 10 |

Captured-path snapshot `lstat`: **2**.
Resolved-path snapshot `lstat`: **0**.
Aggregate `lstat`: **26**, within the 82-call ceiling.

All seven closed audit classes were zero: open, import, dynamic load, mutation,
network, process and other. The hook remained active. Candidate-content opens,
private reads, package execution, engine instances and callback invocations
were zero/false.

Both passes completed. Ordered component paths/full tuples, resolver paths/full
tuples, resolved paths and empty symlink traces matched. The captured snapshots
matched the final lexical and resolved-target tuples in both passes.

## Checks actually run

- Exact clean dispatch/status and all 77 pinned SHA-256 checks: passed.
- Host AST parsing and compile-only source checks before freeze: passed.
- AST audit: no `assert`, no file-open or uncounted `os.stat`,
  `realpath`/`Path.resolve`, dynamic evaluation or late-import call.
  Both `os.lstat` sites are confined to counted wrappers; the sole
  `os.readlink` site is in its counted wrapper.
- Frozen source-container and embedded-source digest checks: passed.
- Exactly one approved RE metadata-only execution: complete-positive.
- Host result schema, canonical receipt digest, source syntax, UTC chronology,
  ordered predicates, paired snapshots, per-pass/aggregate counters,
  no-content/no-private authority and zero audit checks: passed.
- Updated controlling/dependency pins, local Markdown links, source license,
  sensitive-string checks, new-file whitespace and `git diff --check`: passed.

Stable-missing, symlink-expansion, negative-comparison, drift and audit-refusal
branches were reviewed in source but not executed. No alternate path or fixture
was probed, and the diagnostic was not rerun.

## Bounded handoff

The stat-only diagnostic budget is consumed. Its RE-VM custodian released
custody after preserving the sanitized receipt and closing the shell. The
single private analysis remains unused.

Only the three named diagnostic artifacts and the authorized post-result
`WORK_ITEM.md`/`inputs.json` state/pin updates changed. No commit or push
was performed. No roadmap, support, workflow ledger or unrelated file changed.

Remaining uncertainty: the exact operation that caused Amendment 19's pre-open
refusal remains unidentified. A source-only review of that frozen handler can
discriminate harness behavior without assuming a filesystem defect. Any later
content/ELF inspection of this exact regular file requires the prospective
review specified by Amendment 20; it was not performed or admitted here.

No candidate bytes/hash, ELF/dependency structure, mapping state, successful
extension loading, package usability, private-binary behavior, device runtime,
teardown, firmware, radio or hardware support is established.
