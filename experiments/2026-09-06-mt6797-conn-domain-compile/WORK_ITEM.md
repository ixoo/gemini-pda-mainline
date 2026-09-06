# MT6797 CONN power-domain compile proposal work item

- **Outcome:** decide whether a compile-only MT6797 CONN domain-data and
  appended binding-ID proposal can be made reviewably inert, then implement it
  only if the safety contract is satisfied.
- **Owner and reviewer:** Orchestrator integrates; Astra Medium owns the initial
  safety/architecture decision. A Luna High implementer may own exact proposal,
  fixture and experiment files only after that decision permits implementation;
  Sol Medium performs cross-file integration review.
- **Scope:** an experiment-local typed descriptor compiled against the actual
  definitions in `drivers/pmdomain/mediatek/mtk-scpsys.c`, with the proposed
  ID and fields recorded below; this experiment's fixtures and receipts. No
  kernel patch, public binding edit, provider data edit, isolated series or
  profile change is in scope. No DT consumer, Wi-Fi consumer, outer
  rail/reset sequence, runtime enable path, canonical full series, device
  candidate or support claim.
- **Model route:** Astra Medium is required for the named hard uncertainty:
  whether publishing an otherwise incomplete generic callback behind an unused
  ID is an acceptable compile-only artifact. If allowed, bounded implementation
  routes to Luna High and integration review to Sol Medium.
- **Stop/escalation:** stop before implementation if registration has a hardware
  effect beyond the already-reviewed coherent OFF-status reads/resource lookup,
  an in-tree DT consumer can reach the new ID, existing domain ABI changes, or
  the generic callbacks make the artifact misleading or unsafe even under the
  isolated-profile/no-deployment boundary. Two failed repairs, contradictory
  source evidence or a required scope expansion returns to Orchestrator.
- **Parent:** repository commit
  `57956d050f743465740d93efd14b6a1b42c9410f`; upstream Linux
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; provider proposal
  `patches/proposals/0001-pmdomain-mediatek-defer-initial-activation.patch`;
  current isolated provider series `patches/series-mt6797-provider-compile`.
- **Frozen facts:** future ID must append after 0--11; data candidate is name
  `conn`, status mask `BIT(1)`, control offset `0x32c`, zero SRAM request/ACK,
  protection mask `0x60000`, no parent or preclock, and
  `MTK_SCPD_KEEP_DEFAULT_OFF`. Outer VCN rails, CONMCU reset, SPM-key ownership,
  order equivalence and partial-transition recovery remain unresolved.
- **Dependencies:** the deferred-registration proposal supplies passive initial
  registration and NULL-slot refusal. Runtime consumption remains blocked on
  provider-owned outer preparation and recovery. No hardware, build or private
  evidence dependency is admitted for the decision.
- **Worktree:** current small repository checkout and topic branch; no Linux tree
  is stored here.
- **Validation:** prove the local proposed ID and exact data fields against the
  actual provider type, no provider/public-binding/DT references, no initial
  power callback, normal-domain non-regression and refusal mutations. The
  focused fixture applies the already-reviewed deferred-registration proposal
  only in managed temporary state and invokes its existing actual-C runner.
  Checkpatch and Buildbox are **not applicable**: Astra rejected a kernel
  patch/public-binding implementation for this item, so no kernel patch is
  generated and no provider/profile integration or build is authorized.
- **Hardware:** none. The Gemini remains powered down with the independently
  prepared TOPRGU boot2 candidate; no device action or deployment follows from
  this item.
- **Upstream:** MediaTek legacy SCPSYS and MT6797 power binding. Any patch remains
  experiment-only, synthetic/non-certifying and without a DCO sign-off. Remove
  it when maintainers choose a different owner architecture or an accepted
  upstream implementation supersedes it.
- **Owner-away work:** source decision, local descriptor construction, host
  validation and review may finish. Kernel patch generation, Checkpatch,
  Buildbox compilation, physical selection and runtime testing do not apply.
- **Device readiness:** not applicable; compile-only and never a device
  candidate.
- **Handoff:** exact revision, changed files, field and reachability proof,
  executed checks, rejected mutations, unresolved runtime prerequisites and the
  disposition (allowed proposal or rejected direction).
- **Safety decision:** Astra review rejected adding the descriptor to
  `scp_domain_data_mt6797` or the public binding header. Passive initial
  registration would still publish incomplete runtime callbacks. The approved
  implementation is an experiment-local typed descriptor with local proposed
  ID 12, compiled against the pinned provider's actual definitions and proven
  unreachable from registration, match data, subdomains and onecell lookup.
- **State:** complete and accepted after one bounded review repair. The final
  Sol review and full repository gate passed. Checkpatch and Buildbox are not
  applicable after the Astra rejection of kernel patch/public binding changes.
- **Efficiency loop:** if accepted as an offline item, append the measured route,
  timings and evidence to the active workflow ledger; otherwise record the
  considered exclusion.
