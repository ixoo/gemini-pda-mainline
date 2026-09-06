# Pre-Buildbox integration review

Sol Medium accepted the repaired frozen integration at
`2026-09-06T04:42:18.834405Z`. The first review accepted the arithmetic,
refusal, effect and source boundaries but rejected an incomplete predecessor
provenance claim. The bounded repair now verifies the frozen byte identity and
exact order of all eleven entries in `patches/series-mt6797-provider-compile`,
every selected patch, and both source-evidence documents.

The experiment and shared proposal are byte-identical at SHA-256
`84e6abef1139e744ecb59846b3fb3160b98ac50df4a59e058250a77b92d09cb6`.
Proposal 0009 occurs once immediately after 0008 in both the canonical and
selected series. The manifest-series validator checked all 194 profiles, and
its eight invariant mutations remained rejected.

The exact implementation passes strict host compilation and ASan/UBSan tests
covering 8,192 common encodings, 65,536 WLAN encodings, every alignment
residue, both range boundaries, 524,288 common neighboring patterns, 65,536
WLAN neighboring patterns, malformed fields, state mismatch, cleared refusal
outputs and null outputs. Pinned strict Checkpatch reports no source finding;
the synthetic missing-DCO error and new-file/MAINTAINERS warning remain the two
expected experiment-only findings.

The patch adds only `remap-fields.{c,h}` and one Kbuild object. It adds no
caller, export, registration, probe, initcall, MMIO, regmap, lock, mapping,
firmware, MPU/SMC, DMA, IRQ, power, reset or policy path. Expected-field
equality depends on an external owner-supplied exact observation; it does not
prove provenance, serialization or exclusion of another writer. Placement in
the private WLAN compile directory is scaffolding, not final shared-resource
ownership.

The repository publication gate passed over all changed files. The remaining
gate is procedural: stage only the reviewed scope, inspect it, commit and push
the exact clean tree, build the isolated `mt6797-hif-parser-compile` profile on
Buildbox, and preserve exact replay, object, command, symbol and no-caller
evidence. No hardware or device action is admitted.
