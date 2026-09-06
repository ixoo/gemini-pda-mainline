# Pre-Buildbox integration review

Sol Medium accepted the repaired frozen integration at
`2026-09-06T05:51:12Z`. The first review found that the initial bridge admitted
a CLEAR selector below the predecessor EMI ABI's representable range, claimed
unavailable freshness validation, incompletely poisoned refusal outputs, and
lacked an explicit start-after-end fixture. Two bounded repair passes closed
those gaps.

The experiment and shared proposal are byte-identical at SHA-256
`3266942a0b62e61feb525da07faef33e8767f89f7c90e9ff66c44716a3100136`.
Proposal 0010 occurs once immediately after 0009 in both the canonical and
selected series. The manifest-series validator checked all 194 profiles, and
its eight invariant mutations remained rejected.

Strict host compilation and ASan/UBSan fixtures cover SET at address zero,
CLEAR at its exact lower boundary, a CLEAR-below-boundary refusal, minimum and
larger resources, 1 MiB-only alignment, the highest representable first MiB,
start-after-end, all reported-interval mismatches, invalid selectors, overflow,
identical-object refusal before input reads, null pointers, and complete output
clearing. Every semantic output field is poisoned before relevant refusals and
then checked as zero. The bridge links and calls the predecessor remap encoder.
Pinned strict Checkpatch reports only the expected synthetic missing-DCO error
and new-file/MAINTAINERS warning.

The patch adds only `resource-layout.{c,h}` and its Kbuild object. It adds no
caller, export, registration, probe, initcall, permission word, MMIO, regmap,
lock, mapping, firmware, SMC, DMA, IRQ, power or reset path. The input remains
descriptive initialized state, not freshness, reservation or exclusion
authority. Selector equality does not prove provenance, and the temporary WLAN
directory does not own shared CONSYS/WMT/remap/MPU resources.

The remaining gate is procedural: stage only this reviewed scope plus any other
independently accepted sanitized evidence, inspect it, commit and push a clean
tree, then build the exact `mt6797-hif-parser-compile` profile on Buildbox and
preserve replay, AArch64 object, command, symbol and no-caller evidence. No
hardware or device action is admitted.
