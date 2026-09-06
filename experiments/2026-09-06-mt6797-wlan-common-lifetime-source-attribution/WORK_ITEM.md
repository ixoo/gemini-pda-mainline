# MT6797 WLAN-to-common lifetime source-attribution work item

- **Outcome:** resolve, contradict or preserve as unresolved the exact selected
  public-source chain connecting WLAN registration/probe and firmware download
  to the WMT/common Wi-Fi callback, common power/resource retention and cleanup.
  The useful result is a bounded evidence decision, not a driver or ownership
  policy.
- **Owner and reviewer:** Astra Medium owns the hard callback/state-machine
  attribution; Orchestrator owns scope/integration; Sol Medium independently
  reviews the frozen handoff.
- **Scope:** Planet public source at
  `c5b0be85017ad0c599725e8273842efdbecdd88a`; start from the prior pinned
  `wlan_lib`, `gl_init`, `gl_kal`, `wifi_chrdev`, `wmt_exp`, `wmt_func`,
  `wmt_core`, `wmt_ctrl`, `wmt_lib`, `wmt_dev` and relevant headers recorded by
  `experiments/2026-09-06-mt6797-consys-owner-source-attribution/inputs.json`.
  Follow only edges needed to join callback assignment, function-on request,
  platform-driver probe, `wlanAdapterStart`, WMT state/resource retention,
  function-off/failure and unregister cleanup. No unrelated CONSYS, firmware
  format, transport, EMI, reset or radio behavior.
- **Model route:** Astra Medium because directionality, asynchronous callback
  registration and split WMT/WLAN lifetime evidence previously conflicted with
  the requested reverse-ownership inference. Sol Medium reviews ordinary
  cross-file correctness after the specialist handoff.
- **Stop/escalation:** at most three declared search/fetch batches, sixteen new
  regular source files and two contextual rereads of already selected functions.
  Freeze each batch before semantic reads and count failed/no-hit requests.
  Stop with separate unresolved edges when the budget expires; do not broaden
  into a repository traversal. A source contradiction, ambiguous build
  selection or required private/runtime evidence is a handoff, not permission
  to infer or access the device.
- **Parent:** repository commit
  `a770a606ef28244d143fe270f76264ea6d0391d0`; predecessor attribution
  `experiments/2026-09-06-mt6797-consys-owner-source-attribution/` with frozen
  Planet pin and exact source identities.
- **Acceptance predicates:** independently classify these edges:
  1. the exact callback object/API, assignment site and direction;
  2. the exact function-on caller through callback invocation to WLAN probe and
     `wlanAdapterStart`/firmware-buffer lifetime;
  3. whether common power/resource state is held before, throughout and after
     that callback on success;
  4. failure propagation and which state/reference is retained or released;
  5. function-off, module/unregister and consumer probe-failure cleanup order.
  Each is `resolved`, `contradicted` or `unresolved` with citations, boundary,
  missing edge and next discriminator. Do not collapse source behavior into a
  Linux ownership or safe-reuse claim.
- **Dependencies:** public source only. The earlier audit supplies partial edges
  but explicitly did not join their lifetimes. Running Gemian equivalence,
  Linux ownership, rail/reset safety and provider recovery remain independent.
- **Worktree:** current small repository checkout and branch; fetch individual
  public files in memory only. Store no checkout, archive or source body.
- **Validation:** pin raw URL, whole-file SHA-256, Git blob identity, size and
  line count; keep request inventory and evidence citations complete; add a
  deterministic offline verifier and mutations that reject omitted edges,
  reversed callback direction, success-state promotion on callback failure,
  invented lifetime retention and any runtime/reuse/ownership authority. Repeat
  under normal and optimized Python, then run repository publication checks.
- **Hardware:** none. The Gemini remains powered down with the prepared boot2
  candidate; no SSH, boot, reset, radio, VM or Buildbox action is allowed.
- **Upstream:** evidence may constrain a future shared MediaTek CONSYS/WLAN
  owner, but no implementation, authorship, DCO or submission claim is in scope.
- **Owner-away work:** all bounded public-source attribution, validation and
  review can finish without physical selection. It does not alter the prepared
  boot2 candidate or device queue.
- **Device readiness:** not applicable; evidence-only and never a candidate.
- **Handoff:** source/request inventory, per-edge verdicts, exact callback and
  state chronology where proved, explicit unjoined edges, refusal results,
  rights/storage statement and checks actually run.
- **State:** complete and accepted after one bounded publication-integrity
  repair. The five semantic verdicts and strict budget accounting passed Sol
  review; all 17 source tuples and 42 citation anchors are independently frozen.
- **Efficiency loop:** if accepted, append one sanitized offline-item
  measurement to the active workflow ledger; credits are recorded only when
  measured, otherwise unavailable.
