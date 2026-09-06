# Pre-Buildbox integration review

Sol Medium accepted the frozen integration at `2026-09-06T04:09:47Z`.
The experiment and shared proposal patches are byte-identical at SHA-256
`ac87496f89b81419bbf2219acf7f9f140fec14d3b4cf37075107f2afa2f396f9`.
Proposal 0008 occurs once after 0007 in both the canonical series and the
`mt6797-hif-parser-compile` profile's selected series; all 194 manifest profiles
preserve the canonical-order invariant.

The patch creates a real out-of-line implementation, builds `emi-abi.o`, and
leaves both functions unreferenced. The strict host test links that exact object
and passes 131,070 alignment refusals plus confinement, selector, policy,
region, output-clearing and signed-result cases under ASan/UBSan. Pinned strict
Checkpatch, with its pinned spelling and const-struct dictionaries, reports no
source finding; the synthetic missing-DCO error and new-file/MAINTAINERS warning
remain expected because this experiment is explicitly not submission-ready.

No runtime caller, export, initcall, registration, secure call, MMIO, mapping,
firmware, PM, DMA, IRQ, DT, probe, selector default or policy default is added.
No credential, private identifier, personal absolute path or hardware evidence
is present. The object is linked but unreferenced and therefore proves neither
ownership nor Wi-Fi support.

The remaining gate is procedural: stage only this experiment, proposal and two
series additions; inspect the staged scope; commit and push the exact clean tree;
then run the explicit Buildbox profile and retain real `__KERNEL__` object,
symbol, command and package evidence.
