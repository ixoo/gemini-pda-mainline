# MT6797 retained WLAN final-linkage and teardown attribution

- **Outcome:** use one exact retained active Gemian kernel ELF to determine the
  final linked strength/identity of `do_wlan_drv_init`, prove or reject the
  direct `do_connectivity_driver_init` → WLAN → gen3 init call chain in that
  binary, and identify an actual linked caller/reference path for
  `mtk_wcn_wlan_gen3_exit` or return a precisely bounded unresolved result.
  This closes a linkage/lifecycle evidence gap only; it is not runtime
  execution, safe teardown, resource ownership, firmware success or radio
  admission.
- **Parent:** repository commit
  `1092104ac1aa06c7ef9d0144ad9429feefe53b23`.
  Direct evidence dependencies are the accepted
  `2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution` and
  `2026-09-06-mt6797-connectivity-producer-source-attribution` experiments.
  The public Planet source remains pinned at
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- **Frozen private input:** the already reconstructed active-kernel ELF at the
  existing RE-VM work path, expected SHA-256
  `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`.
  Its identity chain is the accepted
  `experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt`
  record, SHA-256
  `b8e1ba26fad5338cc32b29ffe5cd9a1a9dece6e069dc88cc0acc12a7dc05b7f0`.
  The lifecycle predecessor inputs/verdicts/freeze are pinned as
  `3e2b5c20...`, `618af79a...`, `1c9ee0bd...`; the producer predecessor trio as
  `9893687d...`, `955ccc16...`, `e1a6f37c...`. Record all six full hashes in
  `inputs.json` before analysis. Verify the exact ELF hash, AArch64 identity and embedded
  `Linux version 3.18.41+` family before analysis. Never copy the ELF, raw
  disassembly or analysis database out of the RE VM.
- **Owner and reviewer:** Astra Medium owns this named final-link/xref
  uncertainty. Sol Medium independently reviews the complete frozen result;
  `/root` integrates. The owner is not alone in the repository and must not
  revert or edit concurrent work.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium for the binary
  linkage uncertainty; `gemini_reasoner`, `gpt-5.6-sol`, medium for integration
  review. Return ordinary execution to Luna only if the uncertainty resolves
  into a settled implementation task.
- **Owned scope:** create only this experiment's `README.md`, `inputs.json`,
  `analysis.json`, `FREEZE.md`, assert-free normal/optimized verifier,
  `VALIDATION.md` and sanitized result metadata. Raw tool output and databases
  remain under a private ignored RE-VM work directory. Do not edit the source
  experiments, hardware facts, roadmap, queue, workflow ledger, manifest,
  series, configs or patches.
- **Analysis contract:** run only through `./scripts/dev-vm re-shell`, with
  debuginfod/network lookup disabled. Record exact tool versions and commands.
  Require unique symbol-table entries, binding/type/address/size and containing
  executable section for `do_connectivity_driver_init`, `do_wlan_drv_init`,
  `mtk_wcn_wlan_gen3_init` and `mtk_wcn_wlan_gen3_exit`. Inspect only those
  exact symbol ranges plus directly identified caller functions. Prove direct
  calls from decoded AArch64 branch targets, not name proximity. Independently
  enumerate all direct `BL` targets to the gen3-exit address across executable
  sections and record the count and containing symbols. Check symbol/data/code
  xrefs for address-taking or indirect dispatch; distinguish a direct call,
  address reference, callback registration and no reference.
- **Bound:** one ELF, no network/source fetch, no whole-tree checkout and no
  device. Up to eight named function bodies may be inspected: the four required
  symbols plus at most four functions selected solely by direct call/xref edges.
  One whole-executable direct-branch target enumeration and one whole-ELF
  code/data xref analysis are admitted because they are the discriminator.
  Record every selected function and why. Stop unresolved rather than expanding
  past the function budget or guessing through an indirect target.
- **Acceptance predicates:** independently classify with exact address/symbol
  evidence, conditions, missing edge and next discriminator:
  1. whether the final `do_wlan_drv_init` definition is strong, weak or absent;
  2. whether the retained final binary directly joins connectivity → WLAN →
     gen3 init and how the integer result propagates at those calls;
  3. every direct call to `mtk_wcn_wlan_gen3_exit` in executable sections;
  4. any address-taken/callback registration edge for gen3 exit and the exact
     selected caller/owner mechanism within budget;
  5. the strongest supported teardown conclusion, explicitly separating final
     linkage from observed runtime execution and safe owner quiescence.
- **Refusal and validation:** reject wrong ELF/repository/source identities,
  duplicate/missing symbols, wrong section/type/binding, out-of-range or
  non-`BL` call claims, invented xrefs/callers, count drift, function-budget
  expansion, omitted no-hit results, runtime/resource/firmware/radio authority,
  private paths/bytes and mutable expected digests. Freeze source tuples,
  symbols, function selection and raw-evidence hashes before building the
  verifier. The normal and optimized verifier must use active checks rather
  than Python `assert`, and mutations must cover each predicate class.
- **Rights and privacy:** the retained ELF is private evidence. Commit only
  sanitized identities, symbol addresses/sizes, counts, hashes of private raw
  logs, independently worded conclusions and verifier code. No proprietary
  bytes, long disassembly, credentials, serial/IMEI/calibration data or personal
  host paths. Existing GPL source facts remain study evidence, not code to copy.
- **Hardware/build effects:** none. No SSH, device, boot2, recovery, network,
  Buildbox, VM kernel build, firmware/radio action, patch integration, commit or
  push by the owner. The installed passive candidate and its waiting-owner-boot
  state remain untouched.
- **Stop/escalation:** stop immediately on binary identity mismatch, ambiguous
  symbol reconstruction, tool auto-download, required scope beyond one ELF or
  eight functions, or evidence that conflicts with the accepted source audits.
  Return the evidence, attempts, unresolved question and next discriminating
  check. Do not repair a source/binary contradiction by inference.
- **Handoff:** exact parent/input/tool identities, selected function inventory,
  symbol/call/xref counts, sanitized raw-log hashes, per-predicate verdicts,
  normal/optimized mutation counts, limitations and review-ready UTC. State
  whether the teardown join is resolved, partially resolved or still missing.
- **Efficiency loop:** if independently accepted, append one sanitized item to
  the active workflow cohort with actual routes/timestamps, first-review result,
  rework/escalation and measured credits or explicit unavailability.
- **State:** frozen for offline specialist dispatch; no device action.
