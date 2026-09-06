# Work item: attribute the retained firmware NVRAM call target

- **Outcome:** produce a bounded, independently reviewable decision on whether
  the already retained computed-call target can be attributed to an NVRAM
  record handler/application path and whether any reachable branch establishes
  precedence among the submitted WIFI record, compiled defaults and on-chip
  EFUSE. An unresolved result is acceptable and must preserve the exact next
  discriminator.
- **Owner and reviewer:** an Astra Medium specialist owns this hard private
  firmware/control-flow uncertainty and files only under this experiment;
  `/root` integrates; Sol Medium reviews the evidence and source-rights boundary.
- **Scope:** reuse only the existing access-restricted Ghidra 12.1.2 NDS32
  project and scripts for retained firmware SHA-256
  `a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd`,
  411,632 bytes, plus the exact sanitized records below. Re-hash the whole
  artifact and verify the existing section/window identities before analysis.
  The frozen private starting identity is the SHA-256 of the C-locale,
  relative-path-sorted stream of `sha256sum` records for every regular file in
  the retained analysis directory:
  `140f2ab852c841774511861baaff543875da352060d5c44e0a1b3e52790b821b`
  (21 files, 1,619,222 aggregate bytes). It covers the project database,
  stored program/options (including the private entry, anchor and call-target
  candidate), logs and scripts. The independently frozen import-log SHA-256 is
  `ef4dde5d97b8b70a43a118fa1b9809d605560dd2675954b6ef14882278eaadbe`;
  it identifies the existing Ghidra 12.1.2 import and
  `NDS32:LE:32:default:default` language/compiler selection. The aggregate
  SHA-256 of the five permitted script content digests, in the fixed order
  ArgumentProbe, BoundaryProbe, ReachProbe, TargetCheck, TargetProbe, is
  `201a8e8241a5af6ed2555beb22c00bc1f75d38c83d40e3253c4f8c8533421ad9`.
  The public MTKE receipt and executable-mapping record below freeze the
  section/window identities. Before either branch, all identities and the
  private stored-option presence booleans must match; record only booleans and
  opaque digests publicly. Any mismatch is a global stop. Do not create a
  replacement identity, script, firmware copy, source extraction or analysis
  database.
  Inspect only plaintext MTKE section 2 and only the already retained caller,
  NVRAM reference and computed target candidates. Do not change anchors after
  an unfavorable result. Two branches are allowed: `target-contract` and
  `incoming-reachability`, with at most two timestamped, predeclared attempts
  per branch. Target attempt 1 may reconstruct the target's bounded
  intraprocedural CFG up to 4,096 decoded instruction boundaries; attempt 2 may
  classify at most 64 direct calls/data references one level from those visited
  nodes, without traversing callees. Incoming attempt 1 may enumerate direct
  references/call targets to the retained caller and target across established
  plaintext-section instruction boundaries; attempt 2 may perform one bounded
  predecessor/constant-propagation search capped at 16,384 nodes for a concrete
  computed dispatch into the caller. Unknown transfers and encrypted sections
  remain unknown. No decryption, emulation, firmware execution, device access,
  radio action or dynamic instrumentation. No private addresses, instruction
  listings, strings, raw bytes, calibration values, MAC/country data, private
  paths, artifact names or analysis databases may enter Git.
  Traversal is deterministic: instruction boundaries and initial roots are
  sorted by unsigned address; a FIFO work queue is used; each node's unique
  successors or predecessors are enqueued in unsigned-address order; and a
  node is counted when first dequeued. A node that reaches the cap is recorded
  but not expanded. References are deduplicated by
  `(source,target,reference-kind)` and processed in unsigned source, unsigned
  target, then reference-kind order. Constant propagation uses the same queue
  and order, joins only identical concrete values, and turns differing or
  unsupported values into unknown without guessing. Each attempt records roots,
  dequeued nodes, unique edges/references, unknown transfers, cap exhaustion
  and queue exhaustion. A cap hit is never an exhaustive no-hit.
- **Model route:** Astra Medium because this is a named hard uncertainty in
  proprietary NDS32 control-flow and calibration ownership. Sol Medium performs
  final integration review.
- **Stop/escalation:** each branch has its own attempt count and stop state; a
  branch-local cap, ambiguity, result or exhausted two-attempt budget stops only
  that branch, and the independent branch may continue. Stop both branches on
  source identity mismatch, anchor mismatch, required scope expansion, or any
  need to interpret encrypted code. Decoder ambiguity stops each branch it
  affects. Do not
  label a target from keyword proximity, a size constant, an ABI guess, caller
  intent or a plausible default/EFUSE branch. Conflicting evidence or unclear
  acceptance is immediate escalation. Return the evidence, attempts, unresolved
  question and next discriminating check.
- **Parent:** repository commit
  `f43a702c107e3685c92c4d275dc3547acf7302ce`. Exact frozen records and SHA-256:
  `results/firmware-mtke.json`
  `801a45dce0596675faaa67a693ca535b2256f687f4f9c7d25db9626ce681db0e`,
  `FIRMWARE_EXECUTABLE_MAPPING.md`
  `f5689c16a79aa5d512da40b7f8309aa5b4941ecccc40494071e09d2435d609a8`,
  `FIRMWARE_NVRAM_PATH.md`
  `0ae5a47e5f5b728a0f350dacfa7aacc21a34ae1762815d72d79fd41e64320b6e`,
  `FIRMWARE_NVRAM_CALL_TARGET.md`
  `1fa29b99340880c925a4c837ea10864c09ed936143a56247cc7ae491d03db40e`,
  `FIRMWARE_CALIBRATION_BOUNDARY.md`
  `13c7ae780a6fef9c17d05c1ec0f70d0127c76fb48c2063cd1b46801cfd3eae29`,
  `CALIBRATION_APPLICABILITY.md`
  `fe99c510f2291616257a33dbe3ace90ed3ba010bec2fb60a104d1ee853802c03`,
  `PROVENANCE.md`
  `cc7fb7cbc162d9f3f3d6b8982faedd8557bfbfddc614ffede7090e9b39a842e1`,
  and `NORMAL_COMMAND.md`
  `7cec7a6b00c8a499d32f6c16df4bbe1489a7a572035281c611424eaa27ceebf9`.
- **Dependencies:** the retained private artifact/project and existing RE VM
  only. The default little-endian data ABI, big-endian instruction decoding,
  local caller entry and selected conditional path remain explicit hypotheses,
  not facts to hide. Public host framing does not prove firmware pairing.
- **Rights boundary:** the firmware and Ghidra project remain private retained
  evidence used under the owner's standing analysis authorization; that is not
  redistribution permission. The five permitted scripts are locally retained
  analysis tooling, are not vendor source, and remain private because their
  embedded anchors and redistribution review are outside this work item.
  Ghidra is an already installed analysis dependency. Commit only independently
  written verifier/report material and sanitized behavioral facts; do not copy
  firmware bytes, decompiler output, instruction listings, private scripts or
  database content.
- **Validation:** emit machine-checkable `resolved`, `contradicted` or
  `unresolved` verdicts separately for `target_contract`,
  `incoming_reachability`, `record_application` and `calibration_precedence`.
  `target_contract=resolved` requires a decoded target entry plus a coherent,
  completely traversed bounded data/control slice demonstrating input shape and
  at least one consumer/effect; `contradicted` requires a completely traversed
  slice with positive incompatible semantics (for example a proven different
  input object and effect). `incoming_reachability=resolved` requires an exact
  concrete transfer chain into the retained caller or target;
  `contradicted` requires positive, exhaustive concrete dispatch evidence that
  all values for the same admitted predecessor state go elsewhere. A missing
  reference or no-hit is unresolved. `record_application=resolved` requires
  both relevant resolved foundations and a def-use trace from the host-submitted
  payload to a consumer/effect on the selected path; `contradicted` requires a
  complete selected-path trace positively proving rejection or discard before
  every effect. `calibration_precedence=resolved` requires a concrete
  branch/data-flow ordering among record, compiled-default and EFUSE sources;
  `contradicted` requires two concrete paths under the same admitted predicates
  that establish incompatible orderings. Absence of a source/path, one-branch
  evidence, a cap, an unknown join or an unexamined encrypted transfer is
  unresolved. Each
  claim must cite a sanitized source identity, branch/attempt and counted
  method, and classify observation versus inference. Record exact attempt
  UTC boundaries, complete hit/no-hit/count inventories, caps and whether each
  cap was exhausted. Provide one next discriminator per unresolved verdict.
  Add an offline verifier that freezes the parent/input identities, four verdict
  enums and no-policy/no-runtime boundary without embedding private anchors.
  Run repository whitespace, link, rights and sensitive-data checks. A reviewer
  may inspect the sanitized result but must not access the private artifact.
- **Hardware:** none. No Gemini SSH, MMIO, SMC, firmware loading/execution,
  radio, boot candidate, partition or power action. The RE VM is analysis-only.
- **Upstream:** this is private-firmware behavioral evidence only. It may
  constrain the standard `request_firmware()`/normal-command input contract but
  supplies no redistributable firmware, vendor code, regulatory policy or DCO
  certification.
- **Owner-away work:** the bounded retained analysis and review can finish
  offline. It must not select or prepare a device session.
- **Device readiness:** not applicable. Static firmware attribution is not an
  application receipt or radio admission.
- **Handoff:** sanitized report, exact public record identities, private
  whole-file/section identity match booleans, branch attempt ledger, four
  verdicts, assumptions/contradictions, next discriminators, storage retention
  status and verifier output.
- **State:** global stop for required scope expansion. The contract was drafted
  at `2026-09-06T05:33:37Z`, passed Sol pre-dispatch review at
  `2026-09-06T05:40:37Z`, and the contract/analysis clock began at
  `2026-09-06T05:41:02Z`. Observed preflight began at
  `2026-09-06T05:41:33Z`. Both branches stopped before an attempt; private
  preservation and the stop were recorded at `2026-09-06T05:44:00Z`. The first
  final review at `2026-09-06T05:52:32Z` accepted the technical stop and
  required a chronology repair; final Sol acceptance was recorded at
  `2026-09-06T05:53:46Z`.
- **Efficiency loop:** if accepted as an offline evidence decision, append one
  sanitized measurement to the active workflow ledger with actual timing,
  routes, review/rework, escalation and credits or explicit unavailability.
