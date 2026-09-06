# MT6797 passive CONSYS/WLAN boot slice work item

- **Outcome:** implement one bootable, effect-free Linux 7.1.3 diagnostic slice
  that discovers the existing Gemini `mediatek,consys-reserve-memory`
  description, validates its no-map/dynamic-allocation contract, creates one
  opaque nonzero provider generation, binds one passive WLAN client to that
  handle, and emits one bounded machine-readable boot record. The record must
  show provider/client state and zero calls in each forbidden effect class:
  power, reset, remap, protection, firmware, radio and DMA. This is a passive
  interface/lifetime implementation and boot observation, not Wi-Fi runtime
  support.
- **Owner and reviewer:** Luna High owns bounded implementation in this
  experiment, its proposal patch/config/series and focused fixtures. Sol Medium
  reviews Linux integration and `/root` alone integrates shared
  `patches/series`, manifest, workflow, queue, candidate and device records.
  Astra review is required only if implementation introduces a new resource
  owner, mapping, write, device action or ambiguous lifetime beyond this frozen
  passive contract.
- **Scope:** the implementation owner may add files only below this experiment,
  one logical `patches/v7.1.3/0544-*.patch`, one
  `patches/series-mt6797-consys-passive-boot`, and one
  `configs/gemini-mt6797-consys-passive.fragment`. The patch may add a
  built-in diagnostic below `drivers/soc/mediatek/` plus the minimum Kconfig and
  Makefile wiring. It must reuse the existing Gemini reserved-memory compatible
  and may read OF/reserved-memory metadata only. No DTS/binding change, MMIO or
  reserved-memory mapping, resource request, clock/regulator/genpd/reset/DMA
  acquisition, firmware request, rfkill/cfg80211/netdev action, or radio
  operation is in scope.
- **Model route:** implementation uses `gemini_implementer`, Luna High, because
  patch context and refusal fixtures are bounded. Integration review uses Sol
  Medium. The frozen accepted design already received Astra Medium ownership
  review.
- **Stop/escalation:** stop immediately if the existing reserved-memory node
  cannot support a read-only metadata observer, if useful attribution requires
  logging a physical address/pointer, if an effect API or DT change becomes
  necessary, if an opaque client lifetime cannot be represented without a new
  public ABI, or if the parent profile is not a canonical foundation. After two
  repair attempts, return evidence, attempts, the unresolved question and the
  next discriminating check without widening scope.
- **Parent:** repository commit
  `5ff87b372419e506a92a052db22da0dcfa13cb8b`; Linux 7.1.3 source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`;
  parent profile `mt6797-toprgu-minimal-restart`; parent series
  `patches/series-mt6797-toprgu-minimal-restart`. The accepted interface design
  canonical hashes are inputs `a82211e6...d80b`, decisions
  `f3a51551...696f`, state model `a05217ea...dd19`, and proposal map
  `2ab26995...f3a8` as recorded in its `FREEZE.md`.
- **Dependencies:** the existing patch-0020 Gemini DTS node remains a dynamic,
  no-map 2 MiB reservation aligned to 2 MiB in the admitted allocation range.
  The implementation may inspect only the exact managed Linux 7.1.3 Kconfig,
  Makefile and OF/reserved-memory interfaces needed to construct/apply the
  patch. It must not treat a physical base as a client-visible value. The
  TOPRGU parent candidate already booted to authenticated USB serviceability;
  its consumed restart experiment is not repeated and no restart action belongs
  to this session.
- **Implementation contract:** keep provider internals private; give the WLAN
  side only an opaque handle/generation binding with balanced acquire/release.
  Validate unique compatible, `no-map`, exact `size`, `alignment` and
  `alloc-ranges` cell values before publication. Mark the observer failed and
  publish no handle on absence, ambiguity or malformed metadata. Use immutable
  compile-time-zero effect counters with no increment path and a build-time or
  fixture proof that forbidden effect APIs/symbols are absent. The one success
  log must contain a stable prefix, `state=BOUND`, a nonzero generation token,
  `client=wlan-passive`, and all seven zero counters; it must contain no base,
  pointer, device identifier or raw firmware/calibration value. Removal is not
  needed for built-in boot observation, but fixture lifetime tests must prove a
  never-active client releases only passive references.
- **Validation:** require patch metadata and exact preimages, application to the
  parent series, focused host fixtures in normal and optimized modes, Kconfig
  closure, compilation with warnings treated as errors, Checkpatch, JSON/link/
  whitespace/privacy scans, canonical series/profile audit and full repository
  gate. Refusals must cover absent/duplicate compatible, missing no-map,
  malformed/wrapped/wrong size/alignment/range, zero generation, publication
  before validation, raw address/pointer export or log, each forbidden effect
  class, automatic retry/radio action, unbalanced passive release, wrong profile
  parent and support-claim inflation.
- **Hardware/candidate:** `/root` is the sole device custodian. After accepted
  offline review, commit and push a clean exact integration, build only with
  `./scripts/build-kernel --backend buildbox` and profile
  `mt6797-consys-passive-boot`, fetch only its validated package, and construct
  one exact LK-compatible candidate using the already reviewed serviceability
  initramfs/recovery path. Before deployment freeze exact kernel/DT/config/
  initramfs/checksums and a collector that proves the bounded success record and
  rejects any nonzero/missing effect counter. The session spends one physical
  boot2 selection; no automatic reboot. On a missing/malformed record, identity
  mismatch, serviceability failure or any nonzero counter, classify
  inconclusive, preserve logs and recover only; do not retry.
- **Device readiness:** starts `preparing`. It becomes `ready` only after exact
  Buildbox package/candidate validation, recovery and logging identities,
  finite budgets, queue selection and independent packet review. Any patch,
  profile, package, DT, config, initramfs, collector or guard change invalidates
  readiness. Standing boot2 installation may then resolve the live logical
  partition, verify it is inactive/unmounted/non-swap, write and read back the
  full padded image, and shut down cleanly. The owner alone physically selects
  boot2.
- **Upstream:** this experiment patch uses a clearly synthetic,
  non-certifying author identity without `Signed-off-by` and is not
  submission-ready. A final platform/provider split, binding and actual
  authorship remain separate upstream review gates.
- **Handoff:** exact changed paths, patch identity/preimages, state/log schema,
  normal/optimized refusal count, checks actually run, known limits and
  review-ready UTC. No commit, push, build, candidate construction, queue
  selection or device access by the implementation owner.
- **Efficiency loop:** if accepted offline, append one sanitized item to the
  active workflow cohort. Builds and device sessions are not accepted offline
  items.
- **State:** active; bounded passive implementation authorized.
