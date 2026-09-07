# Validation and handoff

review_ready_utc = 2026-09-07T00:26:45Z

## Frozen identity and path gates

The dispatch HEAD and three predecessor hashes matched before analysis.
`inputs.json` was recorded before source inspection. Through
`./scripts/dev-vm re-shell`, installed METADATA, RECORD and Kallsyms hashes
matched; distribution name/version and Python 3.12.3 matched.

The RECORD filter selected exactly four distinct subtree entries. For every
path, components were checked for symlinks and the final regular-file path
was required to remain below the installed root. The designated cache entry
had exactly the two expected missing RECORD fields. Only its permitted
path/regular-file checks were made: no content/hash/size was inspected.
Each other entry's decoded RECORD SHA-256 and decimal size matched the actual
file before content inspection. The partition was one Python source, one
SQLite data file, one documentation file and one excluded cache.

A fresh mode-0700 RE-VM child stored only this audit's metadata. Environment
included `PYTHONDONTWRITEBYTECODE=1`, `-B`, `PIP_NO_INDEX=1`, empty
`DEBUGINFOD_URLS`, `DEBUGINFOD_PROGRESS=0`, `LC_ALL=C` and umask 077.
No package/parser import or compilation was performed. The complete 107-line
verified database source and pinned Kallsyms import/caller were read as text;
no dependency source was inspected.

## One immutable SQLite inspection

The verified data file passed the SQLite header check. Standard-library
SQLite 3.45.1 opened that exact file once using an immutable `mode=ro` URI.
`PRAGMA query_only=ON` was set and its value checked before metadata reads.
The connection was closed in `finally`.

The permitted schema inspection read `sqlite_master` table/index/view names
and definitions, plus `table_info` and foreign-key metadata for the six
directly traced models. Only their `COUNT(*)` aggregates were read from data
tables. No row values, kernel versions, URLs or stored commands were output.
The connection reported user_version 0 and journal_mode delete. The bounded
model counts, schema facts and private audit-log hash are in `analysis.json`.

Every verified file's hash, size, mode and mtime matched immediately before
the open and after the close. Distribution filename snapshots were identical;
the fresh work child had no cache/journal/WAL/temp file. A Python audit hook
rejected socket/DNS, subprocess and shell acquisition; zero attempts occurred.
The RE shell was closed. No database copy or private-kernel/prior-parser-output
access occurred.

This independent read-only connection does not certify the package's Peewee
connection. The package itself calls `db.connect()` at import time without
explicit read-only flags. Conditional eligibility therefore retains the
prospective source-loader/connection guards and refuses ordinary import.

## Host checks

JSON evidence was frozen before constructing the assert-free verifier.

```text
python3 experiments/2026-09-06-vmlinux-to-elf-kernel-db-provenance-v2/verify.py
  PASS; mutations=86; admission=conditional-only
python3 -O experiments/2026-09-06-vmlinux-to-elf-kernel-db-provenance-v2/verify.py
  PASS; mutations=86; admission=conditional-only
git diff --check
  PASS
```

Refusal mutations cover identity and RECORD drift, exact entry partition,
unhashed/cache use, source/data role and path, pre/post state, SQLite modes,
schema/query/row-output limits, source-forcing and effect guards, admission,
private content and mutable expected digests. These tests validate the frozen
audit; they do not execute Peewee or prove future source-loader behavior.

The initial repository check ran before this record existed and refused the
README's missing validation link. The completed-record check is recorded in
the final handoff below. No hardware/build checks are claimed.

## Review-ready handoff

The completed-record `./scripts/check-repository` passed its repository,
publication, invariant, workflow and bounded privacy gates. It reported the
documented Linux-only provenance/package skips. Kernel build, Checkpatch,
DT schemas and device tests were not run.

All eight acceptance predicates are addressed: exact identities and four-entry
partition; deterministic source/model/database selection; import-time open
and absence of explicit selected-path mutations/acquisition; immutable schema
and count facts with unchanged state; exact metadata query semantics; a
fail-closed future source-selection design; and conditional query eligibility
with ordinary import refused. Future loader/connection execution and generic
ORM behavior remain unproved and require their own prospectively frozen guards.

The owned seven-file packet is review-ready. No commit, push or shared-file
integration was performed. Raw audit metadata remains private in the new
RE-VM child; no cleanup touched the excluded predecessor or installed cache.
