# Work item: resolve MT6797 EMI routing and overlap from primary sources

- **Outcome:** perform one bounded public-primary-source sweep for the exact
  hardware facts still blocking a real MT6797 CONSYS/EMI owner: the effective
  AP and CONSYS/WLAN EMI domain assignment and the arbitration rule for
  overlapping MPU regions. Resolve a predicate only from an exact MT6797
  register/transaction chain; otherwise preserve an explicit, stronger
  unresolved result and identify the smallest remaining discriminator.
- **Owner and reviewer:** Astra Medium owns the hard-uncertainty source
  investigation and only this experiment directory. Sol Medium reviews source
  identity, inference boundaries and whether any predicate is actually
  resolved. `/root` owns integration, workflow measurement and publication.
  The owner is not alone in the repository and must preserve concurrent and
  unrelated edits.
- **Model route:** specialist `gemini_specialist`, `gpt-6-astra`, medium for
  conflicting hardware attribution; reviewer `gemini_reasoner`,
  `gpt-5.6-sol`, medium.
- **Frozen parent:** repository commit
  `cf10a2f4a062c13b92b3a5a21e6a818db927d1b8`. Frozen unresolved verdicts are
  `experiments/2026-09-06-mt6797-emi-domain-attribution/results/verdicts.json`
  SHA-256
  `458bbd8b15b59dc40663315c8c305829fc1ca9df4d144a2b61166726daf8a63f`.
  The retained secure-ABI record is
  `experiments/2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md`
  SHA-256
  `8c4963c1d9e63b98bb7dcdad8ed41e442f1f6171e8c599869758f4984e7a7f06`;
  the shared-owner contract is
  `experiments/2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md`
  SHA-256
  `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`.
- **Attempt accounting:** an attempt is one predeclared request batch for one
  branch. Before its first request, record the branch, objective, exact query
  strings or source locators, allowed source class, maximum four discovery/API/
  page-open requests and UTC start. Record every request in order, including
  search-result discovery pages, redirects, failures and cache misses, with
  UTC completion, result identity and a complete hit/no-hit disposition. Then
  record the attempt's stop UTC and conclusion. A follow-up request is part of
  the same attempt only when it was predeclared in that batch; otherwise it
  consumes the branch's next attempt. Attempts cannot be grouped or renamed
  retrospectively. Each branch has at most two attempts and eight requests;
  the item has at most four attempts and sixteen requests total. The offline
  verifier freezes these exact counts, ordering and inventories.
- **Branch A — routing assignment:** use at most two attempts across public
  primary sources. Attempt 1 targets exact MT6797 vendor kernel,
  bootloader, trusted-firmware or register-definition sources for EMI master
  domain assignment, CONSYS/peripheral bridge domain/security override and
  AP-domain configuration. Attempt 2 may follow exact symbol/register leads
  from attempt 1 into another immutable revision or first-party register
  description. Resolve AP routing only by joining an identified AP transaction
  or master through its assignment register and any bridge/security override to
  an effective EMI policy field. Resolve CONSYS routing only by the equivalent
  complete chain for the source-identified CONSYS master. Resolve WLAN-routing
  applicability only with the CONSYS chain **and** an attributable WLAN
  firmware fetch/data transaction joined to that exact master and domain; a
  generic CONSYS assignment, host AP-DMA or SPI-related traffic is insufficient.
  The verifier must reject a record that promotes WLAN after proving only
  CONSYS-to-D2 routing. Domain names, default permission rows, port numbers and
  violation decoders alone remain insufficient for every predicate.
- **Branch B — overlap arbitration:** use at most two attempts across
  public primary sources for the MT6797 EMI MPU multiple-region match rule.
  A valid resolution must state the exact winning-region rule, applicability
  conditions and source locator. A nearby MediaTek generation may be a search
  lead but cannot resolve MT6797 without an explicit compatible contract.
  Software call order, region numbering and successful setter return values do
  not establish arbitration. Record `priority_rule_established` separately
  from `active_region_applicability_established`. This public-only item cannot
  establish which regions are enabled and applicable at the WLAN-loading epoch,
  so the latter remains false and the composite overlap verdict remains
  unresolved even if an exact arbitration rule is found.
- **Corpus and evidence bound:** inspect at most twelve newly fetched regular
  files or primary documents total. Record every query family, immutable URL or
  repository commit/path, whole-file SHA-256, license/rights classification,
  byte count and exact locator used. Search-result pages are discovery only but
  every request and disposition remains in the attempt ledger; cite the
  underlying primary source. Do not mirror a repository, download an
  archive, create a Ghidra project, or retain fetched source bytes in Git. Small
  streamed or temporary files must be removed after hashing/inspection.
- **Acceptance:** create a concise `README.md`, machine-readable `inputs.json`,
  `search-attempts.json` and `verdicts.json`, plus a deterministic offline
  verifier and in-memory refusal fixtures. Records must distinguish observed
  source text from inference; carry `resolved`, `contradicted` or `unresolved`
  separately for AP routing, CONSYS routing and WLAN-routing applicability.
  The overlap record must retain distinct `priority_rule_established` and
  `active_region_applicability_established` predicates and an unresolved
  composite verdict. `policy_selection_allowed` is unconditionally false in
  this public-only item because active-region applicability cannot be resolved.
  A well-supported bounded unresolved result is acceptable. The verifier must
  freeze file identities, predeclared request batches, every request and
  hit/no-hit disposition, attempt/cardinality caps, citations, predicates and
  no-policy/no-device claims without network access. Refusal fixtures must
  reject co-mutated path/hash substitutions, missing/extra corpus items,
  predicate promotion, rights expansion and fabricated attempts.
- **Stop/escalation:** stop after two attempts per branch or twelve new source
  files, whichever occurs first. Stop immediately on conflicting exact MT6797
  semantics, encrypted/proprietary material without inspection rights, a need
  for live fault generation/status clearing, or a need for new reverse-
  engineering tooling. Return the evidence, attempts, unresolved question and
  next discriminating check; do not broaden into another traversal framework.
- **Hardware and private evidence:** none. No Gemini SSH, MMIO, SMC, violation
  trigger, status clear, firmware execution, VM, boot, partition or radio
  action. Existing private records may be cited by hash but private bytes,
  paths, symbols or disassembly are not reopened in this item.
- **Rights and publication:** public source is inspection evidence, not code to
  copy. Record license notices and URLs; commit only independently written
  metadata/verifier text and short necessary identifiers. No proprietary
  document or fetched source body enters the repository.
- **Handoff:** exact corpus and attempts, per-predicate verdicts and false
  inference guards, verifier/refusal output, rights inventory, stop reason and
  next discriminator. No kernel, manifest, series, configuration, roadmap or
  support-matrix edits.
- **State:** contract drafted at `2026-09-06T07:43:13Z`. Sol Medium review at
  `2026-09-06T07:45:03Z` required exact predeclared request/attempt accounting
  and preservation of the separate active-region-applicability predicate;
  repair 1 applies those constraints. Repeat review at
  `2026-09-06T07:46:59Z` required independent AP, CONSYS and WLAN resolution
  predicates so a generic CONSYS-to-D2 chain cannot promote WLAN applicability;
  repair 2 applies that final constraint. Final Sol pre-dispatch review passed
  at `2026-09-06T07:47:31Z`; implementation began at
  `2026-09-06T07:47:42Z`.
- **Integration repair 1:** first complete review-ready handoff used the
  observed completion time `2026-09-06T07:58:39Z`. Sol review at
  `2026-09-06T08:03:11Z` requested the missing MIT SPDX header and refusal
  fixtures that exercise semantic guards independently of whole-record digest
  rejection. Repair adds the header, separates the outer freeze gate, preserves
  independent corpus/retained identity checks, checks all routing boolean types
  and unresolved shapes, and checks the conditional WLAN prerequisites before
  frozen-result promotion guards. By `2026-09-06T08:06:10Z`, normal and optimized
  Python both passed 33 semantic refusals and a positive generic CONSYS-to-D2
  structural control. The targeted WLAN promotion is refused specifically for
  its missing WLAN prerequisite. All three evidence JSON records remain
  byte-identical; no new source requests or hardware actions were performed.
  Repeat Sol Medium integration review passed at
  `2026-09-06T08:08:15Z`; the bounded inconclusive result is accepted.
- **Efficiency loop:** if accepted, append one sanitized offline-item
  measurement to the active workflow ledger with actual routes and observed
  timestamps. Credits remain null unless directly measured.
