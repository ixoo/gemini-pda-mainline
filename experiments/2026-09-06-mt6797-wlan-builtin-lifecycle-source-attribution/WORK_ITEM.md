# MT6797 WLAN built-in lifecycle source-attribution work item

- **Outcome:** resolve, contradict or preserve as unresolved the exact selected
  build/init/exit chain for the Planet MT6797 gen3 WLAN/WMT path, including the
  `CFG_FUNC_WIFI_SUPPORT` guard, built-in initialization caller and `__exit_p`
  treatment of the platform remove callback. This closes only source
  reachability; it is not runtime equivalence or safe ownership.
- **Owner and reviewer:** Astra Medium owns the hard cross-build/state-machine
  attribution; Orchestrator integrates; Sol Medium independently reviews the
  frozen result.
- **Scope:** Planet commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`. Begin with the exact predecessor
  identities in `experiments/2026-09-06-mt6797-wlan-common-lifetime-source-attribution/`
  for WLAN/WMT makefiles, defconfig, gen3 config, `gl_init.c`, AHB HIF,
  `wmt_exp.c`, `wmt_func.c`, `wmt_core.c` and callback headers. Follow only the
  definitions/callers needed to determine compilation of the Wi-Fi function
  table, invocation of `initWlan`/`exitWlan`, module-vs-built-in selection,
  `__exit_p(HifAhbPltmRemove)` expansion and driver-core remove reachability.
  Do not enter queue synchronization, power effects, firmware protocol, EMI,
  radio or unrelated module initialization.
- **Model route:** Astra Medium because the prior accepted audit identified a
  source counterexample whose actual selected reachability depends on split
  vendor make/config and kernel init/exit semantics. Sol Medium reviews the
  joined conditional chain and negative boundaries.
- **Stop/escalation:** at most three predeclared fetch batches, twelve new
  regular files and two contextual rereads of previously selected functions.
  Count every success/failure/no-hit request and freeze each batch before
  semantic reads. Stop separately at unresolved edges when exhausted; do not
  traverse the whole tree or silently substitute a different product config.
- **Parent:** repository commit
  `05e3e04afd0f00a6a2ed1fdb9a263af8c0fd1d0d`; predecessor lifetime verdicts,
  source identities, request accounting and independent freeze are direct
  inputs.
- **Acceptance predicates:** classify independently:
  1. selected definition/value and compilation reachability of
     `CFG_FUNC_WIFI_SUPPORT` and the WMT Wi-Fi operations table;
  2. exact selected producer/caller of built-in `initWlan` and whether its
     registration return is observed;
  3. exact selected producer/caller of `exitWlan`, or a bounded unresolved
     result if no caller is established;
  4. `__exit_p` expansion for this built-in configuration and the resulting
     platform-driver `.remove` value;
  5. whether `platform_driver_unregister` can reach callback clearing in the
     selected source configuration, distinguished from whether the exit path is
     ever invoked.
  Every verdict needs exact citations, conditions, missing edge and next
  discriminator. Do not infer concurrency, actual hardware state or running
  Gemian binary equivalence.
- **Dependencies:** public source only. Reuse predecessor identities and
  semantic boundaries; do not rewrite its accepted normal/late lifetime or
  cleanup verdicts. Queue timeout synchronization and resource balancing remain
  separate future work even if build selection is resolved.
- **Worktree:** current small repository checkout; fetch individual public files
  in memory only. Store no source body, archive, mirror, checkout or binary.
- **Validation:** pin full source identity and request receipts; independently
  freeze the final source tuples/citation anchors; add normal and optimized
  offline validation plus refusals for guard inversion, invented init/exit
  caller, wrong built-in/module mode, wrong `__exit_p` result, conflated remove
  reachability/invocation and any ownership/runtime/device authority. Require
  co-mutation-resistant evidence pins before acceptance.
- **Hardware:** none. Gemini remains powered down with prepared boot2; no SSH,
  boot, reset, radio, VM or Buildbox operation.
- **Upstream:** source evidence may constrain a future common-owner design but
  adds no kernel implementation, API reuse approval, author identity, DCO or
  submission claim.
- **Owner-away work:** all source attribution, validation and review can finish
  offline without altering the prepared boot2 candidate or device queue.
- **Device readiness:** not applicable; evidence-only and never a candidate.
- **Handoff:** identities/requests, per-predicate verdicts, exact conditional
  build/init/exit chain, explicit unjoined invocation or synchronization edges,
  independent evidence freeze, refusal results and checks actually run.
- **State:** bounded source audit complete; three conditional source predicates
  resolved, two outer-caller predicates unresolved; awaiting independent review.
- **Efficiency loop:** if accepted, append one sanitized offline measurement to
  the active workflow ledger; record credits only if measured.
