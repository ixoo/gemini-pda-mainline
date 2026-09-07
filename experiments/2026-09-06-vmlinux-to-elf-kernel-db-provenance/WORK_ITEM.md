# Installed vmlinux-to-elf kernel-database provenance audit

- **Outcome:** identify and freeze the exact installed package source and data
  behind `vmlinux_to_elf.kernel_db.database.KernelVersion`, determine how its
  database is located/opened and whether the exact metadata path used by
  `KallsymsFinder.extract_db_information()` is read-only and locally bounded,
  then decide whether a later parser contract may admit it under explicit
  guards or must bypass it. This audit performs no parser construction and
  reads no private kernel content.
- **Parent:** repository commit
  `1fb9bbdb11e0424ea583d70af4b3f4db62a2fe84`. Its direct v2 preflight is
  pinned as WORK_ITEM
  `0b8cd7c91db6fa52cfb940d9d51cde1ff1659e77243f3d82688731a65a25fcf8`,
  inputs `4a2d2f65bea8422a8fabe75e5927ed2a76454c12de53da9cf7aeeca9a445524b`
  and validation
  `3f6c864b95ab3afe9850ea18c41dbb91157dba674d32592851c7a52959c612ad`.
  Verify all three before work and record them in `inputs.json`.
- **Frozen installed-distribution root:** `vmlinux-to-elf` 1.3.6 under Python
  3.12.3, with METADATA
  `133b5a6b7fab8081a7c201f2fc63b8a2d7a215475c423c8fe3938aff6a708c43`
  and RECORD
  `ac8d68216a496f0f4dedede5e3ea0d72051bbab7983ab196189da05f5aebdc1f`.
  The already pinned `core/kallsyms.py` identity is
  `2bff550d9486e90782a4320cec7bc26b249ead5048f58839eec6578b52c06c2d`;
  its admitted import and caller anchors are lines 20–25, 236 and 455–469.
  No install, update, package download, database download or network.
- **Owner and reviewer:** Astra Medium owns this named local database and
  effect-boundary uncertainty. Sol Medium independently reviews the frozen
  result; `/root` integrates. The owner is not alone in the repository and
  must not revert or edit concurrent files.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium for database
  provenance/effects; `gemini_reasoner`, `gpt-5.6-sol`, medium for review. No
  implementation route is selected.
- **Owned scope:** create only this experiment's `README.md`, `inputs.json`,
  `inventory.json`, `analysis.json`, `FREEZE.md`, an assert-free
  normal/optimized verifier and `VALIDATION.md`. Do not edit the parser
  experiments, hardware facts, support, roadmap, queue, workstreams, workflow
  ledger, configs, manifest, series or patches.
- **RE-VM and content boundary:** run through `./scripts/dev-vm re-shell` only.
  Do not locate, hash, open or otherwise access Image.gz, Image, vmlinux,
  reconstruction logs, prior parser output or any other private kernel input.
  Inspect only installed open-source distribution files selected by the pinned
  RECORD as described below. Raw logs remain in a fresh mode-0700 work child.
- **RECORD-anchored discovery:** before reading unpinned package content,
  verify version/METADATA/RECORD and the pinned Kallsyms source. Enumerate only
  RECORD entries below `vmlinux_to_elf/kernel_db/`, following no symlink and
  requiring every resolved path to remain below the installed distribution
  root. Permit at most 16 total entries, at most four Python source files and at
  most two database/data files. Decode each RECORD digest, hash and size the
  actual file, and require an exact match before content inspection. Record only
  distribution-relative paths, hashes, sizes and declared file roles.
- **Static source trace:** inspect only the verified Kallsyms source plus the
  verified Python files in that kernel-db subtree. Trace the direct import,
  model definitions, connection initialization, database path construction,
  open flags/pragmas, schema creation/migration hooks, import-time statements,
  download/network/subprocess hooks and cleanup. Trace the exact
  `select().where(...)` calls used by `extract_db_information` to their model
  fields and returned metadata. Do not inspect ORM/runtime dependency source;
  if required behavior cannot be bounded without it, return unresolved.
- **Database identity and read-only inspection:** if the verified subtree
  contains exactly one SQLite database selected by the traced source, inspect
  that exact file only through an immutable read-only URI with query-only mode.
  Permit only SQLite header validity, `sqlite_master` table/index/view names and
  SQL definitions, `PRAGMA table_info`, `PRAGMA user_version`, current
  `journal_mode`, foreign-key metadata and row counts for the directly traced
  models. Do not emit row values, URLs, kernel releases or other bulk content.
  Hash and stat every selected source/data file before and after; any content,
  size, mode or mtime change is a refusal. Do not import the package, instantiate
  ORM models, execute the package query, create journals/WAL files or copy the
  database.
- **Effect classification:** distinguish static facts from inference. A query
  is eligible for later guarded admission only if the complete pinned source
  path selects existing rows from the one frozen local database, contains no
  schema mutation/download/subprocess/network path on import or query, and all
  database/model identities needed by the caller are exact. Generic ORM
  behavior remains outside this audit; a future execution contract must still
  use network/subprocess/write sentinels plus before/after package hashes.
  Logging a URL or reading a URL column is not itself a download, but any
  callable acquisition path must be documented and kept unreachable.
- **Bound:** one installed distribution, one pinned RECORD, one kernel-db
  subtree, at most 16 entries/four Python files/two data files, one immutable
  SQLite inspection and the exact Kallsyms metadata call path. No parser/module
  import, ORM query execution, dependency-source expansion, private kernel,
  prior raw result, binary instruction analysis, device, network or build.
- **Acceptance predicates:** independently establish (1) parent and installed
  distribution identities; (2) complete RECORD-verified subtree inventory;
  (3) exact KernelVersion import/model/database path; (4) import/open/schema and
  potential acquisition effects; (5) immutable SQLite identity/schema/count
  facts with unchanged before/after state; (6) exact selected-query semantics;
  and (7) a conditional admission or bypass verdict for a later parser run with
  its mandatory guards. A bounded negative result is acceptable.
- **Refusal and validation:** reject parent/package/RECORD/file hash drift,
  symlink/out-of-root path, inventory/file-count overflow, extra database,
  unsupported data format, database write/journal/temp side effect, before/after
  state change, package import, query execution, dependency-source expansion,
  unresolved dynamic path, hidden network/subprocess/acquisition, private
  kernel access, row-value publication, inferred no-effect claim, mutable
  expected digest, private path/content or authority expansion. Freeze the
  inventory and analysis before writing the verifier. Normal and optimized
  modes must use active checks and mutations for every identity, inventory,
  path, database/schema, effect, query and authority class.
- **Rights and privacy:** installed GPL-3.0-or-later package source/data are
  analysis inputs. Publish only hashes, relative paths, sizes, bounded schema
  metadata/counts and independently worded behavior; no long source/SQL
  excerpts, row values, raw database, personal paths, proprietary content,
  credentials, serial/IMEI/calibration data or private kernel material.
- **Hardware/build effects:** none. The device remains known-good Gemian with
  custody released. No SSH/device action, firmware/radio action, parser run,
  build, patch integration, commit or push by the owner.
- **Stop/escalation:** stop on any identity/inventory/path mismatch, need for
  dependency-source expansion or package import/query execution, database side
  effect, dynamic/unresolved selected path, private-kernel dependency or
  conflict with the v2 stop. Return exact evidence, attempts, unresolved
  question and next discriminating check.
- **Handoff:** exact parent/tool/RECORD identities; bounded subtree inventory;
  source/database/model/open/effect trace; sanitized schema/count facts;
  before/after identities; conditional admission/bypass verdict and guards;
  private raw-log hashes; normal/optimized mutation counts; limitations; and
  review-ready UTC.
- **Efficiency loop:** if independently accepted, append one sanitized item to
  the active workflow cohort with actual routes/timestamps, first-review result,
  rework/escalation and measured credits or explicit unavailability.
- **State:** frozen for offline specialist dispatch; no private kernel or
  device action.
