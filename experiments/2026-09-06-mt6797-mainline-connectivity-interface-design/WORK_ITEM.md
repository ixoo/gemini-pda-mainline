# MT6797 mainline connectivity interface and lifecycle design work item

- **Outcome:** produce a reviewable, implementation-facing Linux design that
  replaces the retained `wmt_loader`/`wmtdetect` ioctl lifecycle with standard
  in-kernel ownership, firmware, cfg80211 and error interfaces. Define probe,
  activation, failure containment, remove/shutdown and recovery contracts for
  the shared MT6797 CONSYS owner and its WLAN client without claiming that
  existing proposal code or hardware support already implements them.
- **Parent and frozen inputs:** repository commit
  `7daaf3811a95e7187bd378e0ce345bf4b536630c`. Required accepted inputs are:
  `docs/ARCHITECTURE.md`, `docs/SAFETY.md`, `docs/hardware/mt6797-wifi.md`,
  `experiments/2026-09-05-mt6797-wifi-contract/{OWNERSHIP.md,SHARED_OWNER_IMPLEMENTATION.md,WHOLE_IMAGE_PLANNER.md,WHOLE_IMAGE_EMI.md,INIT_SESSION.md,CONFIG_PHASE.md,WIFI_START.md}`,
  `experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/`,
  `experiments/2026-09-06-mt6797-wmt-loader-ioctl-static-attribution-v3/`,
  and the proposal series `patches/proposals/0001` through `0012`. Compare only
  against the manifest-pinned Linux release and repository-retained evidence.
- **Owner/reviewer:** Sol Medium owns cross-file architecture reasoning;
  `/root` integrates; Astra Medium independently reviews novel shared-resource
  ownership and teardown risk. The owner may edit only this new experiment
  directory, must not edit this contract, and must preserve other work.
- **Research boundary:** local repository and the already prepared manifest-
  matching Linux source/docs only. At most six precisely named Linux interface
  files or documentation pages may be inspected if an API statement cannot be
  established from frozen inputs; predeclare each and record its exact release
  identity/path. No broad search, new source tree, archive, device/private
  input, network retrieval or build. Historical/vendor material is behavior
  evidence only, never code or ABI to copy.
- **Required decisions:** classify each with inputs, rationale, rejected
  alternatives, exact responsibility and unresolved prerequisite:
  1. whether any new userspace lifecycle ABI is needed; default hypothesis is
     no—normal platform/firmware/cfg80211 interfaces should suffice;
  2. the single CONSYS provider and WLAN consumer boundary, including power,
     reset, remap/protection, reserved EMI and AP-DMA ownership;
  3. probe/bind ordering and the exact point at which firmware loading may
     begin, without mapping vendor module-init aggregation onto probe success;
  4. typed error propagation and state transitions for common owner, ordinary
     HIF, EMI, START/readiness and WLAN registration failures;
  5. remove/shutdown/unbind ordering derived from acquired resources and
     observable quiescence, not by reversing vendor init or assuming a missing
     gen3-exit caller;
  6. suspend/resume and recovery authority, including which failures poison an
     epoch and which operation, if any, may retry;
  7. which existing proposal components can remain compile-only helpers, which
     need API changes, and the smallest next implementation slice with explicit
     acceptance tests; and
  8. upstream-facing structure: likely subsystem/location and how DT bindings,
     firmware names, cfg80211 registration and devlink/health or equivalent
     diagnostics remain standard and reviewable.
- **State/error model:** give a compact state machine or transition table with
  entry preconditions, held resources, allowed calls, success evidence,
  failure state, cleanup obligations and retry policy. Preserve separate
  distinctions for submitted vs completed I/O, firmware START submitted vs
  readiness observed, and runtime support vs compilation. No Boolean may stand
  in for ownership, EMI sealing, firmware quiescence or successful teardown.
- **Mainline constraints:** no WMT-compatible ioctl/character device, retained
  loader execution, arithmetic errno aggregation, synthetic success flag,
  raw physical mapping by the WLAN client, duplicated power/reset owner,
  unconstrained firmware/calibration access, automatic radio action or hidden
  best-effort cleanup. Do not expose private calibration or manufacturing ABI.
- **Acceptance:** deliver README/design, machine-checkable decision/state JSON,
  independent canonical freezes and an offline verifier with normal/-O refusal
  fixtures. Refusals must cover copied vendor ABI, dual ownership, WLAN-side
  raw EMI/remap writes, aggregate errno, init-result discard, START/readiness
  conflation, unproven reverse-order teardown, release before quiescence,
  automatic retry/radio action, compile/runtime promotion, missing state edge,
  proposal-status inflation and scope/input drift. Run JSON, in-memory compile,
  whitespace, links, privacy/source-rights, `git diff --check` and repository
  gate. No kernel build is required because kernel inputs do not change.
- **Effects/stop:** no shared-file edit, kernel/DT/config/patch edit, device,
  SSH, private capture, VM build, Buildbox, network, candidate, boot2, staging,
  commit or push. Stop on conflicting ownership evidence, API uncertainty that
  exceeds the six-file budget, or a design choice requiring new authority.
- **Handoff:** exact decisions, state model, rejected alternatives, mapping of
  all twelve proposal patches, unresolved risks and one smallest ordered next
  implementation slice. Record observed start/review-ready UTC and measured
  credits only; otherwise unavailable.
- **Efficiency loop:** if accepted, append one sanitized pilot-03 item.
- **State:** contract frozen; bounded standard-interface design authorized.
