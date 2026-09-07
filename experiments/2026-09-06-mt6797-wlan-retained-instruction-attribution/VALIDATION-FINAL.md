# Bootstrap v3 refusal — no instruction analysis

Dispatch `06ab1cccacfc687e683f7fcab2d969c9cee25b92` was clean. All
twenty-seven controlling-contract and dependency hashes passed before the
fresh preflight. Historical bootstraps, amendments and refusal records remain
unchanged. Despite this reserved filename, this is a refusal record, not an
accepted final instruction result.

## Freeze and checks actually run

[bootstrap-v3.json](bootstrap-v3.json) was frozen before its first execution
at `2026-09-07T02:39:35Z`:

- File SHA-256:
  `b523898001078f8db04b52235e3d3139a6f260ce584088b1c77695231f4c21cf`.
- Embedded source SHA-256:
  `a53d3d67cd0a21c7b182e10e4963bd8d8394be602518e3de7f81ef155580d0e2`.
- Source digest and host syntax-only compilation passed.

Exactly one fresh `/usr/bin/python3.12 -I -S -B` no-ELF preflight ran through
the approved RE-VM shell. The irreversible audit hook was installed before
standard-library metadata discovery and remained active until child exit.
The sanitized receipt was:

```json
{"asset_opens_by_phase": {"final-drift": 0, "initial-inventory": 28, "pre-import-drift": 0}, "decoder_modules_executed": 0, "events": {"cache_write_attempts": 0, "native_requests": 0, "network_attempts": 0, "optional_requests": 0, "process_attempts": 0, "write_attempts": 0}, "package_inventory_counts": {"entries": 67, "inert": 14, "regular_files": 64, "sources": 25, "stat_only_bytecode": 25}, "private_reads": 0, "reason": "missing distribution file inventory: pyelftools", "status": "refused", "type": "RuntimeError"}
```

The initial Capstone tree inventory completed with 67 entries and 64 regular
files: 25 Python sources, 14 inert assets and 25 stat-only bytecode files.
Each inert asset was opened twice in the initial identity phase, once for its
complete hash and once for its fixed sixteen-byte prefix. No inert asset was
parsed, compiled, used as an input or loaded. Bytecode was never opened or
hashed: its recorded identity is stat-only, not byte identity. These aggregate
counts do not replace an accepted complete frozen tool receipt.

The next source gate refused because the exact selected pyelftools
distribution returned `None` for its `importlib.metadata` file inventory.
The required RECORD-backed source rule could not be established. This does
not prove that no RECORD exists anywhere. No broader search or repair followed.

## Unresolved gates and handoff

Neither decoder was imported. Native closure, optional/native load routes,
pre-import/final tree drift, named restoration and instruction analysis were
not reached. There is no accepted tool preflight, method freeze, result JSON,
result verifier or hardware-support claim. Mapping conclusions are not claimed.

The single private-analysis budget remains unused. The RE shell was closed;
no private capture files were created. No device operation, network research,
tool acquisition, build, commit or push occurred. `git diff --check` passed.
Only this refusal record and `bootstrap-v3.json` are the worker delta.

The next discriminating check requires a prospective provenance decision:
permit bounded metadata-only inspection of the exact installed pyelftools
distribution to establish whether RECORD-backed source identity can be
obtained from retained installed metadata. A direct-tree inventory would be a
separate reviewed rule change, not an implicit extension of Capstone's exception.
