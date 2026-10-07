# Phase B compile 9: config radio index fix

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `68e3a3c860c267bd5ecd062da6e9feedac0ffc30`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 642 patches: the compile-8
  selection plus proposal 0144. Proposal 0140 stays unselected.
- Builder: Buildbox-1, 32 jobs; one submission, generated `2026-10-07T02:21:55Z`.
- Job: `68e3a3c860c267bd5ecd062da6e9feedac0ffc30-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `bb1659e08954ca44deccd3775d8103b564a346f5442a6e9b8f87daef25b6d1b3`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `d4cd9d3b62059a9b29baa6ba48cc447e07bb06e399bfad68ac0d66ccf58dce82`.
- `Image.gz` SHA-256: `c6a5fed7e70694f18a7381d4b9f22cdb57bea885c76ee0693f0fe906d6ecd0d1`.

Kernel-only change. `kernel.config` (`153ea2d0…`) and the board DT
(`07b097d5…`) are byte-identical to the compile-8 and compile-7 packages;
only the image differs. All 796 package checksums pass after fetch, proposals
0143 and 0144 are in the package provenance, and the build log has no MT6797
driver warning. Before submission every fixture in `tests/` passed against
the identical source tree with ASan and UBSan, including the new config
fixture, and `check-repository` exited 0.

Candidate 4 pairs this package with a RAM root carrying the reviewed
`bin/join-connect` helper; see the
[runtime 5 bindings](README.md#runtime-5-bindings-2026-10-07) for the
composer change that is still required.
