# MT6797 WLAN drv-init lifecycle source-attribution work item

- **Outcome:** close or sharply bound the selected built-in caller chain for
  `mtk_wcn_wlan_gen3_init()` and `mtk_wcn_wlan_gen3_exit()` at Planet commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`, beginning with the exact
  `common_detect/drv_init/Makefile` required by the accepted predecessor. This
  is source reachability only; it is not runtime equivalence, resource
  ownership, firmware success or safe radio enablement.
- **Parent:** repository commit
  `30d414811724c25ebd4183c00f06cd8d27aebb0b`; direct predecessor is
  `experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/`
  with its immutable source, citation and request-evidence freezes.
- **Owner and reviewer:** Astra Medium owns this named hard source-selection
  uncertainty; `/root` integrates; Sol Medium independently reviews the
  complete frozen result. The owner is not alone in the worktree and must not
  revert or edit concurrent work.
- **Frozen first input:** fetch the complete regular file
  `drivers/misc/mediatek/connectivity/common/common_detect/drv_init/Makefile`
  first. Only after its exact object selection is frozen may the owner fetch
  the demonstrated lifecycle producer/caller sources. Directory filenames or
  predecessor inventory metadata alone are not selection evidence.
- **Scope:** trace only the build-selected init/exit definitions and direct
  calls needed to join the already established gen3 exports. Include exact
  init registration mechanism, order where explicit, return propagation or
  loss, teardown registration/invocation mechanism, and any directly selected
  common/connection wrapper required by those edges. Do not traverse WLAN data
  paths, WMT queues, power/reset, EMI, AP-DMA, firmware commands, radio state,
  userspace ABI or unrelated Bluetooth/FM/GPS/ANT bodies.
- **Bounded fetch:** at most two predeclared request batches, eight new regular
  files total (including the Makefile), one immediate-directory inventory only
  if the Makefile names a missing include/generated input, and two exact
  contextual rereads from predecessor files. Count and freeze every success,
  failure and no-hit before semantic verification. Stop with an explicit
  unresolved edge when the budget is exhausted; never use a whole-tree search,
  archive, checkout, mirror or retained source body.
- **Acceptance predicates:** classify independently with exact source/line/
  symbol citations, conditions, missing edge and next discriminator:
  1. the Makefile-selected drv-init objects for the pinned product build;
  2. the exact selected producer/caller of `mtk_wcn_wlan_gen3_init()`;
  3. whether its integer registration result is returned, accumulated,
     discarded or converted by every established caller in scope;
  4. the exact selected producer/caller of `mtk_wcn_wlan_gen3_exit()` and the
     mechanism that can invoke it, or a bounded unresolved result;
  5. any explicit cross-component init/exit ordering established by the
     selected corpus, without inferring resource lifetime or runtime execution.
- **Evidence discipline:** record full source identity tuples and complete
  request receipts; declare independent canonical freezes for source tuples,
  citation anchors and immutable request evidence before writing the verifier.
  Expected digests must be literal independent constants, never generated from
  mutable records at verifier startup. Inherited evidence must match the
  predecessor field-for-field.
- **Validation:** normal and optimized verification must reject co-mutation of
  source/request/citation evidence; wrong object selection; invented callers;
  hidden return-value loss; false exit invocation; init/exit order inversion;
  conflated built-in/module lifecycles; runtime, resource, firmware, radio,
  reuse or device authority; missing/no-hit request deletion; and budget drift.
  Run JSON, in-memory Python compile, newline/whitespace, local-link, license,
  sensitive-data, `git diff --check` and the common repository gate.
- **Source rights:** use the public vendor-derived source only as evidence. Do
  not store source bodies or excerpts, copy implementation, or claim host-code
  reuse rights. Record facts and independently expressed conclusions only.
- **Hardware/build effects:** none. No device, SSH, private capture, VM,
  Buildbox, kernel build, candidate, boot2 selection, radio action, staging,
  commit or push. Stop if the source evidence would require a live observation
  or another repository-wide search.
- **Handoff:** README, inputs/request receipts, per-predicate verdicts, freeze,
  normal/optimized verifier with refusal count, validation record, exact
  unresolved boundaries and the next discriminator. One experiment owner may
  edit only this directory; shared roadmap, queue, hardware, workflow, manifest
  and series files remain for integration.
- **Efficiency loop:** if accepted, append one sanitized offline-item
  measurement to the active cohort. This should become accepted item 10 and
  close the ten-item pilot only after independent review; credits are recorded
  only if measured.
- **State:** contract frozen; source retrieval and audit authorized.
