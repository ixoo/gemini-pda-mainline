# Amended isolated preflight refusal

Dispatch: `9c88c111c109c6d44ef9e5c16b2d4fadd0ad4401`.
The twenty-one controlling-contract and dependency hashes passed before the
fresh preflight. The existing [PREFLIGHT.md](PREFLIGHT.md) remains unchanged because its
digest is controlling evidence.

## Frozen bootstrap and actual execution

The complete [bootstrap-refused.json](bootstrap-refused.json) was frozen at
`2026-09-07T02:21:22Z`, before its first execution or decoder import:

- Bootstrap file SHA-256:
  `53adefdb21a8bc966930b14cedb0683f7ae0bb11c1184c2d5fc94cbf011aed42`.
- Embedded source SHA-256:
  `a05e04ad8bcf0471816a074bafd16d71cf0569fc092d9997fb0e5074a18b561f`.
- Host source-digest comparison and syntax-only compilation: passed.
- Fresh RE-VM `/usr/bin/python3.12 -I -S -B` tool preflight: refused.

The irreversible audit hook was installed immediately after importing builtin
`sys`, before standard-library metadata discovery and before any decoder
import. It remained installed through child exit. No private ELF was opened.
The isolated preflight did not reuse normal-startup component observations.

The exact sanitized child receipt was:

```json
{"decoder_modules_executed": 0, "events": {"cache_write_attempts": 0, "native_requests": 0, "network_attempts": 0, "optional_requests": 0, "process_attempts": 0, "write_attempts": 0}, "private_reads": 0, "reason": "missing distribution file inventory: capstone", "status": "refused", "type": "RuntimeError"}
```

This refusal occurred when the exact selected Capstone distribution returned
`None` for its `importlib.metadata` file inventory. The RECORD-backed source
gate could therefore not be established. It does not independently prove that
no RECORD file exists anywhere, and no broader metadata search was performed
after the refusal.

## Handoff

No repair or private analysis execution was attempted. There is no accepted
tool inventory, method freeze, instruction result or normal/optimized result
verifier. The one private-analysis budget remains unused. No native decoder
load or optional-module lookup occurred. The RE shell was closed, and no
private capture files were created.

The next discriminating check requires a prospective contract decision:
permit a bounded metadata-only inspection of the exact installed Capstone
distribution to determine whether a complete independently checkable source
manifest exists. If only package-manager manifests exist, their acceptance
would require an explicitly reviewed provenance-rule change; they must not be
silently substituted for RECORD. No tool acquisition is authorized.

Tests actually run: twenty-one frozen SHA-256 comparisons, bootstrap
source-hash comparison, bootstrap syntax-only compilation, and one no-ELF
isolated bootstrap preflight. No decoder execution, private-ELF analysis,
device operation, network research, build, commit or push occurred. Final
`git diff --check` passed; both new JSON/Markdown files were reviewed as the
complete worker delta. The bootstrap's later native/mapping/restoration paths
remain unexecuted and unvalidated.
