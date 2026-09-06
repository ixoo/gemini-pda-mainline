# Work item: attribute public-source MT6797 CONSYS resource ownership

- **Outcome:** produce one bounded, independently reviewable attribution from
  the pinned public Planet kernel source of the components that (1) declare or initialize the dynamic
  `consys-reserve-memory` allocation, (2) own the CONSYS power/reset/handoff
  transition used by WLAN download, and (3) write or request the shared remap
  and EMI region-18 policy. Resolve only identities and call/data boundaries
  supported by an exact pinned path; otherwise preserve separate unresolved
  predicates and name the smallest next discriminator. This is source evidence,
  not a proposal to reuse vendor code.
- **Owner and reviewer:** Astra Medium specialist owns this hard hardware-
  ownership attribution and files only in this experiment directory. Sol Medium
  reviews source identity, inference boundaries and whether the result actually
  narrows a real Linux provider. `/root` owns integration, workflow measurement
  and publication. The worker is not alone in the repository and must preserve
  unrelated or concurrent edits.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium for the named
  uncertainty spanning reserved memory, common connectivity ownership and
  secure EMI effects; `gemini_reasoner`, `gpt-5.6-sol`, medium for review.
- **Frozen parent and inputs:** repository commit
  `d56c4d8763d2b11f0521b945e890a9a108dbe16e`. Shared-owner contract
  `experiments/2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md`
  SHA-256 `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`;
  passive ownership result
  `experiments/2026-09-06-mt6797-consys-passive-ownership/results/observation.json`
  SHA-256 `46d4b23d96af1cb3c060955088d0c76cf4139f83048c3c198ecfcb7ba38b214b`;
  dynamic declaration result
  `experiments/2026-09-06-mt6797-consys-dynamic-declaration/results/observation.json`
  SHA-256 `43a6aa8629e2b549fe95d8facc323c22029093caa3c2209ed15d8f0d41fdedf1`.
  Source selection is the public GPL-2.0 Planet/Gemini kernel repository
  `https://github.com/lineage-geminipda/android_kernel_planet_mt6797` at exact
  commit `c5b0be85017ad0c599725e8273842efdbecdd88a`, already authenticated by the
  source links and raw-file hashes in
  `experiments/2026-09-05-mt6797-wifi-contract/OWNERSHIP.md` and
  `experiments/2026-09-05-mt6797-wifi-contract/results/conn-power-domain-contract.json`,
  SHA-256 `5a7044e62fc5688ef7c14f53f536dbf6a18a7e64719dd0236ead39ab540d3435`
  and `8a075cd2680561407a8873ad1780587dc394a4f79fe6e71f92a13d8269cbad15`
  respectively.
  Record the immutable repository/commit and the exact API/raw response hashes
  used in `inputs.json`; a branch or moving tag is not an eligible substitute.
- **Scope and method:** use only immutable public primary-source tree metadata
  and raw files at that exact commit. At most four predeclared semantic search
  batches and 120 distinct regular files may be inspected. A mechanical remote
  tree/path inventory is exempt from the semantic-file count because it reads no
  file bodies, but its request, response identity and selected paths must be
  recorded. Before semantic search, derive and freeze a relative-path allowlist
  of at most 120 regular files from that inventory. Every raw file opened or
  searched counts once in the union even when it has no hit; repeated reads of
  the same exact content count once. All body searches and reads are restricted
  to the frozen allowlist, and the verifier rejects any batch whose cumulative
  union exceeds 120. Batch
  A targets the exact reserved-memory compatible/node label, early reservation
  callbacks and allocation consumers. Batch B targets the live `mtk_wmt` owner,
  its platform probe and CONSYS power/reset/handoff calls. Batch C targets the
  live `mt-wifi` owner and the path from firmware request/MTKE handling into
  common ownership. Batch D targets exact shared-remap `0x10001340`, region 18,
  and secure-call adapters reached from A-C. Record every query family before
  executing it, exact relative file identities, whole-file SHA-256, size,
  relevant symbol/line locators, hit/no-hit disposition and UTC boundaries.
  Follow at most two direct call/data-reference levels from a discovered anchor;
  do not broaden into an unbounded tree-wide architecture reconstruction.
- **Acceptance predicates:** report `resolved`, `contradicted` or `unresolved`
  separately for `dynamic_reservation_producer`, `consys_power_reset_owner`,
  `wlan_to_common_handoff`, `shared_remap_writer`, and `emi_region18_requester`.
  Each predicate has a distinct minimum positive chain:

  - `dynamic_reservation_producer` must connect the exact declaration/early
    callback through the initialized reservation/allocation effect and both its
    base and size inputs; a node or later consumer alone is insufficient.
  - `consys_power_reset_owner` must connect the common driver's public caller or
    lifecycle entry through the actual MT6797 transition authority and
    power/reset effect, including its success/failure return boundary.
  - `wlan_to_common_handoff` must connect an exact WLAN firmware-download caller
    edge to the common owner and show what lifetime is retained and what failure
    is returned; parallel bindings or nearby calls are insufficient.
  - `shared_remap_writer` must connect a caller to the actual masked/write effect
    on `0x10001340`, including which bits are changed and preserved; a literal or
    helper definition without a caller is insufficient.
  - `emi_region18_requester` must carry the literal or derived region value 18
    from the requester through the secure adapter and its returned raw/status
    boundary; adapter presence or region declarations alone are insufficient.

  For one predicate, `contradicted` requires an exact complete chain that
  positively falsifies its claimed actor/effect or value. Two incompatible exact
  chains are a stop/escalation, not a convenient contradicted verdict. Any
  incomplete chain remains `unresolved`. Keep Linux ownership inference separate from vendor behavior:
  the audit may identify responsibilities that a new common provider must
  assume, but may not claim that a vendor routine or ABI is reusable upstream.
- **Evidence and rights:** create concise `README.md`, machine-readable
  `inputs.json`, `search-attempts.json` and `verdicts.json`, plus a deterministic
  offline verifier and in-memory refusal fixtures. Commit only independently
  written sanitized facts, opaque whole-file identities, relative source paths,
  symbol names and short necessary identifiers. Do not copy source excerpts,
  decompiler output, raw binaries, credentials, calibration, personal data,
  proprietary documents or private absolute paths. GPL inspection permits
  source study but does not authorize copying an implementation into this
  independently written patch layer.
- **Validation:** verifier freezes the parent/input identities, finite batch and
  file inventories, per-predicate verdicts, citations, rights boundary and all
  false authority flags: `linux_owner_established`, `vendor_code_reusable`,
  `vendor_api_reusable`, `policy_selected`, `runtime_authority`,
  `device_action_allowed`, and `hardware_support_claim` must all remain false.
  Refusal fixtures cover co-mutated identities,
  fabricated searches, cap expansion, predicate promotion from a string or
  constant hit, source-copy permission, device authority and hardware-support
  promotion. Run normal and optimized Python, in-memory syntax compilation,
  Markdown-link, whitespace, sensitive-data and experiment-local rights checks.
- **Stop/escalation:** stop on immutable source identity mismatch, binary-only
  evidence requiring disassembly, conflicting exact ownership
  chains, missing redistribution boundary, need for live device/MMIO/SMC/radio
  action, need for a local checkout/archive/mirror, or exhaustion of four batches/120
  files. After two failed repair attempts or unclear acceptance/scope change,
  return evidence, attempts, unresolved question and next discriminating check.
- **Hardware and builds:** none. No Gemini SSH, boot, firmware execution, MMIO,
  SMC, radio, partition, power, deployment, kernel build or Buildbox action.
  No VM, local source checkout, archive, mirror or analysis database is created.
- **Upstream:** the pinned public vendor kernel is behavioral evidence only. This item
  supplies no author identity, DCO certification, reusable source, ABI approval,
  DT binding or hardware-support claim.
- **Owner-away work:** the complete source audit, refusal fixtures and review can
  finish offline. It does not alter the prepared boot2 candidate or select a
  device session.
- **Device readiness:** not applicable. Static ownership attribution does not
  admit a passive or active runtime probe.
- **Handoff:** exact public corpus/attempt inventory, five independent
  verdicts, observed vendor boundaries versus Linux inference, contradictions,
  next discriminators, verifier/refusal output and storage/rights status. No
  kernel, manifest, series, configuration, roadmap or support-matrix edits.
- **State:** contract drafted at `2026-09-06T15:08:33Z`; repair 1 replaced the
  ambiguous private-corpus premise with the exact public Planet commit, made the
  semantic-file cap mechanically enforceable and separated all five predicates.
  Sol Medium accepted the repaired contract at `2026-09-06T15:12:18Z`;
  specialist implementation began at `2026-09-06T15:13:28Z`, reached its
  review-ready handoff at `2026-09-06T15:29:11Z`, and passed first final Sol
  review at `2026-09-06T15:33:32Z`. State: complete and accepted for
  integration; no device, build or runtime claim.
- **Efficiency loop:** if accepted, append one sanitized offline-item
  measurement to the active workflow ledger using observed timestamps and
  actual routes; measured credits remain unavailable unless directly reported.
