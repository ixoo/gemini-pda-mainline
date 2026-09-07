# Bundled database identity and conditional query boundary

The installed RECORD resolves to three verified files and one explicitly
excluded generated cache. The source selects the verified `database.sqlite3`
beside `database.py`; it constructs a Peewee database and calls `db.connect()`
at import time. It does not supply read-only flags or a cleanup call. The
complete selected package source contains no explicit schema mutation,
download or subprocess action. The caller performs metadata selections and
logs their results, including URLs and suggested commands, without invoking
them. Exact citations and field paths are in [analysis.json](analysis.json).

One independent immutable read-only SQLite inspection passed. The file has
eight tables, twenty indexes and no views. Only the six directly traced
models were counted. No row values were published. All three verified files
retained identical hashes, sizes, modes and mtimes, and no cache, journal or
other distribution file appeared. The [inventory](inventory.json) records the
exact source/data identities; the excluded bytecode was neither read nor hashed.

This establishes conditional eligibility for a future guarded metadata query,
not permission to import the package now. Ordinary import is not proven
read-only. A future contract must prospectively freeze a source-only loader,
all required package-module pins and any connection adapter needed to enforce
immutable read-only opening. It must prove which source bytes supplied each
module, reject all cache use and unexpected opens/writes, and verify unchanged
state afterward. `-B` alone does not prevent loading existing bytecode.
If those checks cannot be established, bypass the package import/metadata path.

The immutable connection used here does not establish Peewee's runtime
behavior. No ORM dependency source was inspected and no package, parser or ORM
query was executed. No kernel input, prior parser result, device, network or
build was involved. This result does not resolve architecture-bypass or
instruction-analysis admission.

See [FREEZE.md](FREEZE.md) and [VALIDATION.md](VALIDATION.md) for the frozen
records, exact checks and handoff time.
