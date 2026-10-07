# Phase B compile 8: refused-peer diagnostic

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `a5951349237d39271e20b9480a2574292224d498`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 641 patches: the compile-7
  selection plus proposal 0143. Proposal 0140 stays unselected.
- Builder: Buildbox-1, 32 jobs; one submission, generated `2026-10-07T00:40:37Z`.
- Job: `a5951349237d39271e20b9480a2574292224d498-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `9c5a73001fed6707c23edff4d6332b1aa17b6a9be7bfa0d86255022e21e2f8ae`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `2e75b9026b18dd9bda3d282e2c2dd742761b9e3602ef237cff18c4b2ab106f1b`.
- `Image.gz` SHA-256: `bc0bad2b6fafa83e725cfe232ecf7b317eb33cf821a4802a7c9d0f3e38c57d6d`.

Kernel-only change. `kernel.config` (`153ea2d0…`) and the board DT
(`07b097d5…`) are byte-identical to the compile-7 package used by runtimes 2
and 3; only the image differs. All 795 package checksums pass after fetch, and
proposal 0143 is in the package provenance. The build log has no MT6797
driver warning.

Before submission every fixture in `tests/` passed against the identical
source tree with ASan and UBSan, including the peer fixture's new exact
refusal-bit assertions, and `check-repository` exited 0. The candidate-3
bindings in this directory point at this package; see the
[runtime 4 bindings](README.md#runtime-4-bindings-2026-10-07).
