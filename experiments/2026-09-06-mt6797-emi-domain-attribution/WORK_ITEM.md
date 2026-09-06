# Work item: attribute MT6797 EMI domains and overlap priority

- **Outcome:** produce a bounded, independently reviewable evidence decision on
  whether the selected MT6797 sources establish (1) which of the eight packed
  EMI policy fields govern AP and CONSYS/WLAN accesses and (2) how overlapping
  MPU regions are prioritized. A negative or inconclusive result is acceptable
  and must name the next discriminating observation.
- **Owner and reviewer:** an Astra Medium specialist owns this hard source/ABI
  uncertainty and files only under this experiment; `/root` integrates; Sol
  Medium reviews the evidence and scope boundary.
- **Scope:** inspect only the public GPL-2.0-noticed Planet/Gemian kernel
  repository `https://github.com/lineage-geminipda/android_kernel_planet_mt6797.git`
  at commit `c5b0be85017ad0c599725e8273842efdbecdd88a`, limited to its complete
  recursive commit-tree index and these exact paths:
  `drivers/misc/mediatek/emi_mpu/mt6797/emi_mpu.c`,
  `drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h`,
  `drivers/misc/mediatek/devapc/mt6797/devapc.c`,
  `drivers/misc/mediatek/devapc/mt6797/devapc.h`,
  `drivers/misc/mediatek/eccci/mt6797/ccci_platform.c`, and
  `drivers/misc/mediatek/eccci/mt6797/ccci_platform.h`. Freeze each used file,
  its SHA-256, file-level license and exact purpose in `inputs.json`; any other
  repository, revision or file is a scope change. Private evidence is limited to the
  already retained TEE identity and the named sanitized retained-ABI Markdown
  and JSON records below; no new private kernel/firmware corpus is admitted.
  Trace policy-field numbering through the actual protection registers,
  bus-domain/master attribution, and any region-overlap priority logic.
  Distinguish macro labels, caller intent, secure-handler behavior and hardware
  routing; do not infer AP, CONSYS or WLAN from the existing numeric policy
  words alone. Classify rights for every used source. Do not copy proprietary
  excerpts, strings, source, firmware bytes, disassembly, private absolute paths
  or unit identifiers into Git; cite private facts only through sanitized
  artifact/window hashes. Do not edit the Wi-Fi contract,
  hardware facts, roadmap, patch series or workflow ledger; `/root` owns shared
  integration after review.
- **Model route:** Astra Medium because domain routing and protection priority
  are a named hard hardware-ownership uncertainty with potentially conflicting
  source layers. Sol Medium performs the integration review.
- **Stop/escalation:** use exactly two branches: `domain-routing` and
  `overlap-priority`. An attempt is one predeclared corpus, query/objective,
  UTC start/stop and complete hit/no-hit inventory recorded in the result. Each
  branch gets at most two attempts. Caller intent or a no-hit remains
  inconclusive and permits the next predeclared discriminator; after two
  non-discriminating attempts, stop and return the evidence, attempts,
  unresolved question and one next check. Source-identity failure, contradictory
  labels, unavailable required private input, unclear acceptance or needed
  scope expansion is immediate escalation rather than silent inference.
- **Parent:** repository commit
  `82405bb9eafb3af37cafb331e1bc0eaeb2518f3f`; relevant frozen records:
  `EMI_ABI.md` SHA-256
  `60bd8c436b22495719512b8a1cd9dae0bffb062511811d67cff436d94a0f0c71`,
  `RETAINED_EMI_SECURE_ABI.md`
  `8c4963c1d9e63b98bb7dcdad8ed41e442f1f6171e8c599869758f4984e7a7f06`,
  `SHARED_OWNER_IMPLEMENTATION.md`
  `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`,
  and `experiments/2026-09-05-mt6797-wifi-contract/results/retained-emi-secure-abi.json`
  `fc1f249aa50b975298d559f8446dce7de24068a3aa88fab3b81ad83f1f3bcfe2`.
  Three existing sanitized records are admitted only as locator inputs for the
  retained private artifact, not as fresh domain or priority evidence:
  `experiments/2026-09-05-mt6797-wifi-contract/results/whole-image-emi-sources.json`
  SHA-256 `f69382b0ddaa09f9dd1f5eebf76d55f4b2e41734f1e9cd199e9fe2346b20d9ef`,
  `experiments/2026-07-22-a72-firmware-power-contract/results/live-tee-identity-20260723.txt`
  `3f2753800637a9650ce210b57f2d531f62b62daeef095262deff86c4a1f25b55`,
  and `experiments/2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt`
  `d7b3b7848dc6e0df9e11845193a3e77e72d2fd64034454b194c9f9e340ccd5a2`.
  This exact locator-only admission was recorded after the first review found
  that the investigation had consulted them; it does not expand the six-file
  public search corpus or authorize new private interpretation.
  The private retained TEE identity remains
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
- **Dependencies:** existing public source, private retained evidence and the RE
  VM only. No current device state, firmware redistribution or kernel build is
  required. If hardware documentation is not redistributable, record only
  independently derived facts and source identities.
- **Validation:** emit machine-checkable `resolved`, `contradicted` or
  `unresolved` verdicts separately for `ap`, `consys`, `wlan`, and
  `overlap_priority`, with evidence class and cited identity. AP, CONSYS and
  WLAN routing resolves only with a trace from master/bus identity through a
  hardware domain selector to the packed field; macro names and caller policy
  alone are inconclusive. Overlap priority resolves only with an authoritative
  priority rule and its applicability to every enabled overlapping region at
  the WLAN-loading epoch. A default initializer, caller attempt or no-hit must
  not be reported as active hardware state or absence of overlap. Record
  complete search inventories and SHA-256 identities;
  make every conclusion cite a concrete source path, symbol/register field and
  revision; independently reproduce arithmetic/bit-field decoding where
  applicable; require field vectors `0xb6da2d -> [5,5,0,5,5,5,5,5]` and
  `0xb6da28 -> [0,5,0,5,5,5,5,5]` for fields 0 through 7. Inventory every
  potentially overlapping region with its number, inclusive range,
  enable/lock/policy, writer/init path, lifecycle epoch and source-observed vs
  runtime-unknown status, or state exactly why it cannot be determined. No
  policy may be selected unless all three routing verdicts and overlap priority
  resolve. A reviewer must be able to classify each claim as observed source
  fact, cross-source inference, contradiction or unresolved.
- **Hardware:** none. No Gemini SSH, MMIO, SMC, radio, power, firmware execution,
  boot candidate or partition action. The RE VM is analysis-only and is not a
  kernel-build backend.
- **Upstream:** this is an evidence decision, not submission code. If resolved,
  it constrains the future MediaTek CONSYS/EMI provider policy; if unresolved,
  it must block policy selection rather than install vendor values by default.
- **Owner-away work:** the complete bounded investigation and review can finish
  offline. It must not select or prepare a device session unless the final
  result separately proposes a future read-only discriminator for later review.
- **Device readiness:** not applicable; no runtime candidate exists.
- **Handoff:** sanitized report, exact source/analysis identities, search
  inventory, reproduced policy decode, positive/negative evidence,
  contradictions, limitations, and one next discriminating check for each
  unresolved question.
- **State:** accepted unresolved evidence decision. Investigation began at
  `2026-09-06T04:57:48Z`, the first handoff was ready at
  `2026-09-06T05:03:55Z`, the escalated repair was ready at
  `2026-09-06T05:20:46Z`, and final Sol Medium review accepted it at
  `2026-09-06T05:21:50Z`. Three rework cycles closed structured-record,
  exact-boundary, and mutation-refusal gaps; the third followed the required
  two-repair escalation to Astra Medium. No hardware action or policy selection
  occurred.
- **Efficiency loop:** if accepted as an offline evidence decision, append one
  item to the active workflow-improvement ledger with actual routing, timing,
  review/rework, escalation and measured credits or explicit unavailability.
