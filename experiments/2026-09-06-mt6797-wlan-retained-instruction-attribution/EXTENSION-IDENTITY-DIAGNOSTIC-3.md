# Direct-resolver extension identity diagnostic

## Result

**Complete-positive:** all 13 pre-open stages and all 15 inherited content,
ELF and maps stages passed in the sole [Amendment 22](AMENDMENT-22.md) run.

The exact installed file
`/usr/lib/python3.12/lib-dynload/_queue.cpython-312-aarch64-linux-gnu.so`
has the following bounded identity:

| Field | Observation |
| --- | --- |
| SHA-256 | `0ab94b7c54af74d78b85b00bea6527e4dffc56304625995b0016429defe8edba` |
| Size | 68,496 bytes |
| Permission bits | `0644` |
| mtime ns | 1781873160000000000 |
| ELF | ELF64, little-endian, AArch64, `ET_DYN` |
| ELF header size | 64 bytes |
| Program headers | 7 entries, 56 bytes each |
| Dynamic entries through first terminating `DT_NULL` | 20 |
| Dynamic string-table size | 855 bytes |
| Parsed `DT_NEEDED` names | none |
| Candidate absent from isolated-process maps | true |

No `DT_NEEDED` entry was present in the bounded parsed dynamic table. This
does not prove that the extension has no external symbol/runtime dependencies.
No dependency was resolved, opened, hashed or loaded.

The map check parsed 49 strict rows and established only absence of the exact
candidate path in this isolated process. It did not construct or publish a
mapping dictionary or make a cross-process mapping claim.

## Frozen inputs and chronology

- Published clean dispatch: `0e7faceb96b168380e8fe7c1b0062a79598f43eb`.
- Contract: [WORK_ITEM.md](WORK_ITEM.md), [Amendment 22](AMENDMENT-22.md),
  and all inherited pinned controls.
- Dispatch [inputs.json](inputs.json) SHA-256:
  `19e4d4ca7a252365e2d27fd482845a20234a832c755e5bc5a8c21ce372cdb167`.
  All 85 dispatch pins passed.
- [Frozen source container](extension-identity-diagnostic-v3.json) SHA-256:
  `ed0070168a86e91da9c84c2d03d1617f21e2f333919bb32495419a6b77d2db81`.
- Embedded source SHA-256:
  `cb87b5e1d9ec80d26ae08c72686208f3ff673056e0c29095ee4d4a3cf48e838e`.
- Freeze: `2026-09-07 06:40:50 UTC`.
- Sole execution: `2026-09-07T06:41:33.443606+00:00` through
  `2026-09-07T06:41:33.444151+00:00`.
- [Complete sanitized result](extension-identity-diagnostic-result-v3.json)
  SHA-256:
  `eac9d08935b88bb565d4bab87ed1d02699a79ac0f10bcc9198068a531ff66508`.
- Canonical receipt SHA-256:
  `b7d82b7cc4f5e39cc4091b33377c0b8b8045eb7f199ef7e308e98041309c2b18`.

The source embeds the exact accepted event path/digest, Amendment 20 result
digest and complete accepted stat tuple, with exact nanosecond integers.

The approved RE shell supplied the frozen source once on stdin to
`/usr/bin/python3.12 -I -S -B -`, with empty `DEBUGINFOD_URLS`,
no-user-site and no-bytecode controls. The source preloaded exactly the nine
named helpers: `sys`, `os`, `stat`, `builtins`, `struct`, `re`,
`json`, `hashlib` and `datetime`. It contained no `pathlib` import or
path object and no hidden resolver.

The original raw receipt was preserved as text. Host Python parsed/formatted it
losslessly and verified its canonical digest before publication; no JavaScript
numeric round-trip was used.

## Sequential evidence

All 28 ordered stage outcomes are `passed`, with no terminal stage, missing
class or refusal class.

Both complete counted metadata passes matched exactly across ordered component
paths/full stat tuples, resolver paths/full tuples, resolved path and empty
symlink traces. The resolved path equaled the captured path, remained in the
installed root, and every observed component was nonsymlinked. The two
captured-path snapshots matched each other and the corresponding final tuples
in both passes. Their full tuple equaled the accepted Amendment 20 tuple.

The conditional zero resolved-path snapshot count was a passing outcome:
captured and resolved paths were identical.

| Pre-open metadata operation | Pass 1 | Pass 2 | Total |
| --- | ---: | ---: | ---: |
| Component `lstat` | 6 | 6 | 12 |
| Resolver `lstat` | 6 | 6 | 12 |
| `readlink` | 0 | 0 | 0 |
| Symlink expansions | 0 | 0 | 0 |
| Processed components | 5 | 5 | 10 |

Captured snapshot `lstat`: 2; resolved snapshot `lstat`: 0.
Total pre-open metadata `lstat`: 26, within the 82-call ceiling.

Only after that gate passed was the exact original import object restored and
verified, with wrapper count zero and all audit counts zero. The content gate
then admitted exactly one candidate open. Pre/post-read `fstat` and the final
`lstat` matched the accepted full tuple; the single bounded read reached EOF
at exactly 68,496 bytes. Hashing and ELF parsing reused those retained bytes.

The inherited numeric ELF/program-header/dynamic/string/name bounds passed.
One subsequent maps open/read met its byte, row and field limits and proved
the exact candidate absent. No raw bytes or rows are published.

Final counts:

- candidate open/read: 1/1;
- maps open/read: 1/1;
- `fstat`: 2; final post-read `lstat`: 1;
- terminal-wrapper calls: 0; original import restored: true;
- audit import/dynamic-load/write/mutation/network/process/other: all 0;
- private reads, package execution, engine instances and callbacks: zero/false.

The single final content `lstat` is separate from the pre-open 26-call
metadata total. Both candidate/maps streams were closed; the interpreter and
outer RE shell exited normally. The named custodian released RE-VM custody.

## Checks actually run

- Exact clean dispatch identity/status and all 85 pins: passed.
- Host AST parse and compile-only checks before freeze: passed.
- AST checks: exact nine helpers; no hidden resolver or `assert`; exact
  accepted tuple; 13+15 ordered stages; counted metadata routes; exactly two
  named open sites; no loader/dynamic-evaluation route.
- Source comparison: inherited ELF and maps stage blocks were byte-identical
  to the frozen Amendment 21 implementation.
- Frozen container/source digest verification before execution: passed.
- Exactly one isolated RE diagnostic: complete-positive.
- Lossless raw/published canonical receipt digest, JSON/schema, ordered stages,
  metadata/read/audit counters, accepted identity fields, numeric parser bounds,
  absence/authority and UTC chronology: passed.
- Updated controlling/dependency pins, local Markdown links, source license,
  sensitive-string checks, new-file whitespace and `git diff --check`: passed.

Missing, symlink-expansion, drift, parser-refusal and candidate-present branches
were reviewed in source but not exercised. No fixture path or alternate file
was probed, and the diagnostic was not rerun.

## Bounded handoff

The one-run budget is consumed. The single private analysis remains unused and
is not admitted by this result.

Only the three named artifacts and authorized `WORK_ITEM.md`/`inputs.json`
post-result state/pin updates changed. Dispatch hashes above remain the exact
pre-execution references; current pins additionally cover this trio and the
updated handoff state. No commit or push was performed. Roadmap, support and
workflow ledger files were not changed.

This result establishes only the current exact installed file's bounded content
identity/ELF metadata and absence from this isolated process. It does not load
or initialize `_queue`, prove return behavior or package usability, admit a
general extension route, identify the earlier lazy import or retrospectively
explain Amendment 19. Any extension admission or dependent execution requires
prospective review.

No private-binary behavior, runtime driver invocation, teardown, firmware,
radio or hardware support is established.
