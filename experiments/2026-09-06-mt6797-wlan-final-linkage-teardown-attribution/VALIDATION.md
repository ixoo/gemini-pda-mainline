# Preflight evidence

## Superseding resumed result

At 2026-09-06T23:03:25Z the coordinator's relocated retained artifact was
independently verified as the exact frozen SHA-256, ELF64 little-endian EXEC
AArch64, with embedded family `Linux version 3.18.41+`. This clears only the
earlier missing-location blocker. No second ELF was substituted or analyzed.

All four required symbol entries are unique `GLOBAL FUNC DEFAULT` entries in
section 1, `.kernel`, a reconstructed WAX PROGBITS region. Every `st_size` is
zero. The exact addresses and private metadata-log hash are in
`analysis.json`. This triggers the contract's reconstruction/range stop before
any body inspection. No strength, branch edge, callback owner, runtime event or
teardown result is inferred from those entries.

The source/input/symbol/function-selection/raw-evidence tuple was frozen in
`FREEZE.md` before verifier construction. Executed host checks:

```text
python3 experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/verify.py
  PASS; refusal mutations=34; binary semantic tests=not-run
python3 -O experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/verify.py
  PASS; refusal mutations=34; binary semantic tests=not-run
git diff --check
  PASS
```

Mutations cover source/repository/ELF identities, duplicate/missing symbol
entries, size/binding/type/section/address drift, unknown versus no-hit counts,
invented edges including a non-BL claim, budget expansion, each unresolved
predicate, each authority bit, private paths and mutable expected digests.
These are frozen-packet refusal tests, not executable branch-decoder tests.
The verifier has no device, ELF, subprocess or network path.

The RE shell was closed after preserving the unique metadata log privately.
No repairs were attempted. The next discriminating check requires an admitted
reconstruction/boundary rule or original sized-symbol evidence.

Review-ready UTC after normal and optimized validation:
`2026-09-06T23:05:18Z`.

Independent Sol review initially rejected the publishable path-shaped mutation
literal and missing review-ready timestamp. After those two packet-only repairs,
the reviewer reproduced both 34-mutation verifier modes, Python compilation,
`git diff --check` and the complete repository publication gate, then accepted
the bounded unresolved result at `2026-09-06T23:09:23Z`. The review did not
promote any binary-semantic, linkage, runtime or teardown claim.

## Historical missing-location attempt

UTC: 2026-09-06T22:59:20Z.

The repository parent and all six predecessor hashes plus the accepted active
ELF identity-record hash match `inputs.json`. Inputs were recorded before the
attempted ELF preflight. GNU readelf reports Ubuntu Binutils 2.42 and Python
reports 3.12.3 in the RE VM.

Access used `./scripts/dev-vm re-shell`. `DEBUGINFOD_URLS` was empty,
`DEBUGINFOD_PROGRESS=0`, `R2_CURL=0`, `LC_ALL=C`, and umask was 077. No network
lookup, binary reconstruction, device action, or build was attempted.

The historical active ELF location recorded by the existing
`analyze-active-aw9523-elf.sh` helper is absent. SHA-256, ELF-header,
embedded-release, and required-symbol commands against that location all
returned missing-file errors; none analyzed a binary. A bounded filename-only
inventory of the existing RE work directory found one differently named
retained vmlinux. Its bytes have not been opened or substituted for the frozen
input. The coordinator was asked to resolve the current exact input location.

Function bodies inspected: 0. Executable branch scans: 0. ELF xref scans: 0.
Normal/optimized semantic verification and mutation fixtures: not run because
the binary identity gate has not passed. No linkage or teardown claim follows.
