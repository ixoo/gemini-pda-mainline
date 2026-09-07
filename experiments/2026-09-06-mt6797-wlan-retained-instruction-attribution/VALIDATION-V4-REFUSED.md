# Bootstrap v4 refusal — executable baseline mapping

Dispatch `7b2360da57313ec12ab72a446008fab72d6c60da` was clean. All thirty
controlling-contract and dependency hashes passed. Earlier files remain
unchanged.

[bootstrap-v4.json](bootstrap-v4.json) was frozen before its first execution
at `2026-09-07T02:45:35Z`:

- File SHA-256:
  `1ebac170bd804fe0dd292240500c30ee5a56f7ff073d1ba0cac0c259f91defee`.
- Embedded source SHA-256:
  `ce3c6b06d33e77a4a083dd2f9517a7e62d9bf60e35c373a4274e1abb748d2f99`.
- Source digest and host syntax-only compilation passed.

Exactly one fresh `/usr/bin/python3.12 -I -S -B` no-ELF preflight ran via the
approved RE-VM shell. Its audit hook preceded metadata discovery and remained
active through child exit. The sanitized receipt was:

```json
{"asset_opens_by_phase": {"final-drift": 0, "initial-inventory": 28, "pre-import-drift": 28}, "decoder_modules_executed": 0, "events": {"cache_write_attempts": 0, "native_requests": 0, "network_attempts": 0, "optional_requests": 0, "process_attempts": 0, "write_attempts": 0}, "package_inventory_counts": {"capstone": {"entries": 67, "inert": 14, "regular_files": 64, "sources": 25, "stat_only_bytecode": 25}, "elftools": {"entries": 117, "inert": 0, "regular_files": 104, "sources": 52, "stat_only_bytecode": 52}}, "private_reads": 0, "reason": "anonymous or pseudo-file executable mapping", "status": "refused", "type": "RuntimeError"}
```

Both complete initial package inventories and their pre-import drift checks
passed. Capstone had 67 entries, 64 regular files, 25 Python sources, 14 inert
assets and 25 stat-only bytecode files. Pyelftools independently had 117
entries, 104 regular files, 52 Python sources, zero inert assets and 52
stat-only bytecode files. Both use their respective direct-installed-tree
provenance exceptions, not RECORD or package-manager provenance. No bytecode
was opened or hashed; no byte-identity claim is made for it. Inert asset opens
were confined to the two named identity phases reached.

The process-baseline mapping parser then encountered an executable mapping
whose name was absent or began with `[`. Its frozen predicate refused this
class before decoder imports. The receipt does not retain the specific name
or permission tuple, so it does not distinguish an unnamed executable region
from a kernel pseudo-file mapping. It is not evidence identifying a vDSO,
decoder mapping or package asset. The claim is limited to this guarded process.

No repair, repeated preflight or additional mapping inspection followed.
Native loading, decoder imports, final drift and restoration were not reached.
There is no successful tool receipt, method freeze, private instruction
analysis or result verifier. The single private-analysis budget remains unused.
The RE shell was closed; no private capture files were created. No network,
device, acquisition, build, commit or push operation occurred.

The next discriminating check needs a prospective protocol decision: retain
the refused baseline mapping's bounded name/permission classification in an
isolated no-ELF diagnostic, then decide whether any specifically identified
kernel-provided pseudo-file mapping belongs outside the file-backed native
closure. Do not silently whitelist anonymous executable mappings or infer the
missing mapping identity from typical Linux behavior.

Checks actually run: thirty frozen hash comparisons, bootstrap source hash and
syntax-only checks, and one isolated no-ELF preflight. `git diff --check`
passed. Only `bootstrap-v4.json` and this refusal record are the worker delta.
