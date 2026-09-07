# Replacement bootstrap v2 — package-tree refusal

Dispatch `e8e33bff0bcd92d9aa3560f442be648eb9a34384` was clean and all
twenty-four controlling-contract/dependency hashes passed before preflight.
Historical refusal files were left unchanged.

The replacement [bootstrap-v2.json](bootstrap-v2.json) was frozen before its
first execution at `2026-09-07T02:30:38Z`:

- File SHA-256:
  `189f83ebac5fdb64e9450ccff5e4f508f5a546d91b3d6b613ce710f29bf44038`.
- Embedded source SHA-256:
  `803ea8e4465a4bf3a6ecba48cfa3cdd6d10d6361a95a55f8379351dba2841e22`.
- Source-hash comparison and host syntax-only compilation passed.

One fresh `/usr/bin/python3.12 -I -S -B` no-ELF preflight was executed through
the approved RE-VM shell. Its irreversible audit hook was installed before
standard-library metadata discovery and remained active through exit.
The exact sanitized receipt was:

```json
{"decoder_modules_executed": 0, "events": {"cache_write_attempts": 0, "native_requests": 0, "network_attempts": 0, "optional_requests": 0, "process_attempts": 0, "write_attempts": 0}, "private_reads": 0, "reason": "legacy excluded regular entry: include/capstone/arm.h", "status": "refused", "type": "RuntimeError"}
```

The recursive legacy package inventory encountered a regular header at the
relative name `include/capstone/arm.h`. Amendment 2 rejects every non-`.py`
regular file except named pre-existing bytecode. The bootstrap therefore
stopped immediately without opening the header or skipping it. No complete
package inventory is claimed. Pyelftools provenance, decoder imports, native
mapping/closure, optional-load routes and restoration checks were not reached.

No repair, second preflight, private ELF access or instruction decoding was
attempted. The one private-analysis execution remains unused. The RE shell was
closed and no private capture files were created. No network research, device
operation, build, commit or push occurred.

The next discriminating check requires a prospective provenance-rule decision:
whether a bounded, complete identity inventory of bundled nonexecuting headers
may coexist with the Python-only source-loader map. Until reviewed, neither
ignoring the header nor broadening the admitted file kinds is authorized.

Tests actually run: twenty-four frozen SHA-256 comparisons, bootstrap-v2 source
hash comparison, syntax-only compilation, and one isolated no-ELF preflight.
Final `git diff --check` passed. Only `bootstrap-v2.json` and this validation
record are the worker delta. There is no final method, result verifier,
instruction result or hardware-support claim.
