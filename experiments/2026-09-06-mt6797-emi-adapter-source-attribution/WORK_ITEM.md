# Work item: attribute the MT6797 EMI secure adapter

- **Outcome:** resolve, from the exact pinned public Planet kernel, the smallest
  source chain missing from the accepted CONSYS audit: the definition selected
  for `mt_emi_mpu_set_region_protection`, its direct secure-call mapping, and
  its return/raw-status semantics. Report whether literal region 18 can be
  carried end to end from the already cited WLAN requester through that adapter.
  A bounded unresolved or contradicted result is acceptable; no ABI or policy is
  selected from a function name or wrapper success.
- **Owner and reviewer:** Astra Medium specialist owns source inspection and
  files only in this experiment directory. Sol Medium performs final source and
  inference review. `/root` owns integration, workflow measurement and
  publication. The worker is not alone in the repository and must preserve all
  unrelated edits.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium because secure-call
  status propagation conflicts with the observed unconditional outer success;
  `gemini_reasoner`, `gpt-5.6-sol`, medium for review.
- **Frozen parent and inputs:** repository commit
  `cb035d7f8b9f782b1b8b1139352621fe2a38c025`; source repository
  `https://github.com/lineage-geminipda/android_kernel_planet_mt6797` at exact
  commit `c5b0be85017ad0c599725e8273842efdbecdd88a`. Accepted predecessor verdicts,
  inputs and attempts have SHA-256
  `beaa116bf405d8143353b98bb458143eb2ff1ad07020f72fb8006a0df3750af9`,
  `157c990f2f3a04099723ce7098e61840ec3756842381397e787b8ed5956e9496`
  and `408963b5f149130f507570448a868861d681096cca69be477105caee4ab73113`.
  Retained ABI constraints `RETAINED_EMI_SECURE_ABI.md` and `EMI_ABI.md` have
  SHA-256 `8c4963c1d9e63b98bb7dcdad8ed41e442f1f6171e8c599869758f4984e7a7f06`
  and `60bd8c436b22495719512b8a1cd9dae0bffb062511811d67cff436d94a0f0c71`.
- **Scope and accounting:** use only immutable GitHub tree metadata and raw
  regular files at the frozen commit. Before any source-body read, predeclare
  at most two query batches and freeze an allowlist of at most 16 paths selected
  from a body-free tree inventory. Count every attempted raw-file open and every
  opened file, including failures/no-hits; repeat reads of identical content
  count once in the distinct-file union but every request remains recorded.
  Batch A locates the unique definition/build selection for
  `mt_emi_mpu_set_region_protection` and follows at most two direct references.
  Batch B joins only the directly identified secure-call wrapper/macro/function
  and return conversion, again with at most two direct references. Record exact
  requests, response/blob/SHA-256 identities, sizes, line/symbol locators and
  hit/no-hit dispositions. No checkout, archive, mirror, broad code-search
  service, binary analysis or adjacent EMI architecture sweep.
- **Acceptance predicates:** emit independent `resolved`, `contradicted` or
  `unresolved` verdicts for:

  - `adapter_definition`: resolved only by an exact definition plus build or
    compile-selection evidence tying it to MT6797; a declaration is insufficient.
  - `secure_call_mapping`: resolved only when adapter arguments are joined to a
    concrete secure-call identifier/function and argument positions.
  - `adapter_return_semantics`: resolved only when the raw lower result and the
    adapter's returned status/conversion are both explicit; outer wrapper zero
    cannot substitute for the lower return.
  - `region18_end_to_end`: resolved only when literal/derived 18 flows from the
    frozen predecessor requester through the selected adapter and secure-call
    mapping with its status boundary. It does not establish successful execution.

  `contradicted` requires a complete exact chain that positively falsifies the
  predicate. Incompatible complete chains trigger stop/escalation; incomplete
  evidence remains unresolved. Observed source facts remain distinct from any
  inference about deployed secure firmware or live configuration.
- **Evidence and rights:** create `README.md`, `inputs.json`,
  `search-attempts.json`, `verdicts.json`, an offline verifier and in-memory
  refusal fixtures. Store only independently written facts, hashes, public
  relative paths, line ranges, symbol names and short necessary identifiers.
  Do not copy source excerpts, binaries, firmware, proprietary documents,
  credentials, calibration, personal data or private absolute paths. GPL source
  study is not permission to import vendor implementation into this patch layer.
- **Validation:** freeze every input and evidence record, request/file/batch/hop
  caps, four verdicts and exact citation keys. Refuse co-mutated identities,
  fabricated requests, cap expansion, declaration-only adapter promotion,
  macro-only secure-call promotion, outer-zero return promotion, region-number-
  only end-to-end promotion, source-copy permission, independent
  `vendor_api_reusable`/`linux_owner_established` promotion and runtime/support
  claims.
  The verifier must pin false: `deployed_adapter_established`,
  `secure_firmware_compatibility_established`, `policy_selected`,
  `vendor_code_reusable`, `vendor_api_reusable`, `linux_owner_established`,
  `runtime_authority`, `device_action_allowed`, and `hardware_support_claim`.
  Run normal and optimized Python, in-memory syntax,
  JSON, link, whitespace, sensitive-data and repository checks.
- **Stop/escalation:** stop on source identity mismatch, multiple selected
  definitions, conflicting secure-call IDs/argument layouts, any need to inspect
  secure firmware or binary-only code, any scope beyond two batches/16 files/two
  references, or any device/MMIO/SMC action. After two repair failures or unclear
  acceptance, return the evidence, attempts, unresolved question and next
  discriminator; do not broaden the audit.
- **Hardware and builds:** none. No Gemini SSH, MMIO, SMC, firmware execution,
  radio, boot, partition, power, kernel build, Buildbox, VM or deployment action.
- **Upstream:** source attribution only; no reusable implementation, truthful
  authorship/DCO identity, ABI approval, binding, support claim or submission.
- **Owner-away work:** the complete bounded audit and review can finish offline
  without altering or selecting the prepared boot2 candidate.
- **Device readiness:** not applicable; static attribution admits no runtime test.
- **Handoff:** exact request/corpus inventory, four verdicts, source versus
  deployment boundaries, contradictions/next discriminators, verifier/refusal
  output and rights status. No kernel, manifest, series, config, roadmap or
  support-matrix edits.
- **State:** contract drafted at `2026-09-06T15:37:54Z`; repair 1 added explicit
  API-reuse and Linux-owner false-authority gates. Sol Medium accepted the
  repaired contract at `2026-09-06T15:40:46Z`. Specialist inspection began at
  `2026-09-06T15:41:55.774253Z`, reached review-ready state at
  `2026-09-06T15:50:46Z`, and passed first final Sol review at
  `2026-09-06T15:53:58Z`. State: complete and accepted for integration; no
  runtime, build or device claim.
- **Efficiency loop:** if accepted, append one sanitized measurement to the
  active workflow ledger using observed timestamps/routes; credits remain
  unavailable unless directly measured.
