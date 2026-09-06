# MT6797 `wmt_loader` ioctl static-attribution work item

- **Outcome:** statically resolve or sharply bound whether the exact retained
  `system/vendor/bin/wmt_loader` issues `COMBO_IOCTL_DO_MODULE_INIT` to
  `/dev/wmtdetect`, the value supplied as its third ioctl argument, the ordering
  around cleanup/autok commands, and how the returned aggregate is interpreted.
  Preserve binary reachability separately from runtime execution, successful
  initialization, firmware activity, radio safety and a future mainline ABI.
- **Parent and immutable inputs:** repository commit
  `65f1b43333b727f0d5bbddf900cd38486a896e4d`; direct source predecessor is
  `experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/`.
  The only retained binary admitted is logical path
  `system/vendor/bin/wmt_loader`, SHA-256
  `446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa`,
  already inventoried by the accepted connectivity experiment. Match its hash
  before analysis and stop on mismatch or absence.
- **Owner and reviewer:** Astra Medium owns the hard stripped-binary data-flow
  uncertainty; `/root` integrates; Sol Medium independently reviews. The owner
  may edit only this new experiment directory, must not edit this frozen
  contract, and must preserve concurrent work.
- **Analysis environment and boundary:** use `./scripts/dev-vm re-shell` and
  guest-owned analysis state only. Never execute, load or emulate the retained
  program and never invoke an ioctl. Start from the accepted bounded call-site
  metadata and the exact kernel command definitions/handler at the pinned
  predecessor. Analyze only `wmt_loader`; do not inventory or inspect adjacent
  binaries, filesystem content, live processes or device state.
- **Bounded analysis:** at most two predeclared analysis batches. Batch 1 may
  recover the minimal function/control-flow regions that open `/dev/wmtdetect`
  and reach its ioctl call sites. Batch 2 may follow only direct local data-flow
  edges needed to identify command construction, chip-value origin, branch
  ordering and return handling for module init/cleanup/autok. Count analyzed
  functions, call sites, blocks and tool invocations. Stop rather than broaden
  to whole-binary decompilation or unrelated property/configuration paths.
- **Acceptance predicates:** classify independently with exact binary address,
  semantic anchor, conditions, missing edge and next discriminator:
  1. exact binary identity, architecture and `/dev/wmtdetect` open-to-fd flow;
  2. exact numeric request matching `COMBO_IOCTL_DO_MODULE_INIT` and its direct
     call site, or a bounded unresolved result;
  3. third-argument value provenance, including whether `0x6797` is constant,
     property-derived, kernel-query-derived or otherwise conditional;
  4. ioctl return interpretation, conversion, retry, gating and process result;
  5. relative order and conditions for module init, cleanup and SDIO autok
     requests within the admitted control flow; and
  6. whether the result supports only a vendor compatibility observation or any
     proposed mainline userspace contract. The latter must remain unresolved
     absent an explicit standard-interface design.
- **Evidence discipline:** retain the exact input identity, tool/version and
  bounded request receipts, addresses, normalized instruction/data-flow
  semantics and independently authored prose/verifier code only. Retain no raw
  binary bytes, complete function dump, decompiler output, strings corpus,
  analysis database, credentials, identifiers or private paths. Declare literal
  independent canonical freezes for immutable metadata, semantic anchors,
  analysis receipts and verdicts before verifier construction. Expected hashes
  must not be generated from mutable evidence at startup.
- **Validation:** normal and optimized verification must reject binary-identity
  drift, invented ioctl numbers/call sites/value origins, pointer-versus-scalar
  conflation, command-order inversion, hidden return discard/retry/gating,
  runtime or mainline-ABI promotion, missing receipts and budget drift. Run
  JSON, in-memory compile, whitespace, local-link, retained-suffix,
  privacy/source-rights, `git diff --check` and the common repository gate.
- **Effects and stop conditions:** no device, SSH, live process, network,
  Buildbox, kernel build, candidate, boot2, radio action, binary execution,
  shared-file edit, staging, commit or push. Stop after two batches, on an input
  mismatch, conflicting data flow, unsupported tool output, or when another
  binary/runtime trace would be required.
- **Handoff:** README, complete sanitized input/analysis receipts, verdicts,
  independent freeze, normal/optimized verifier and validation record. Report
  exact resolved/unresolved predicates, budgets, checks and next discriminator.
- **Efficiency loop:** if accepted, record one sanitized item in active pilot
  03; credits remain unavailable unless actually measured.
- **State:** contract frozen; bounded private static analysis authorized under
  the repository's standing retained-evidence policy.
