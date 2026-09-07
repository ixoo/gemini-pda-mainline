# Work item: audit retained MT6797 Wi-Fi lifetime evidence

- **State:** accepted bounded no-evidence stop at
  `2026-09-07T19:32:12Z` after independent Sol Medium review.
- **Outcome:** determine whether already retained project/private evidence
  contains one attributable successful MT6797 WLAN firmware-load and shutdown
  cycle that proves any of the exact lifetime predicates required by the
  accepted HIF architecture review. Return a predicate-by-predicate evidence
  matrix and the smallest remaining discriminator. Do not create a new observer
  or treat source sequencing as runtime execution.
- **Parent:** published repository commit
  `2af9532b3b1c1850cfa071a0f279154127a04db1` on `origin/main`.
- **Owner and reviewer:** Astra Medium owns this named retained-evidence and
  shared-hardware uncertainty. Sol Medium independently reviews the handoff;
  `/root` integrates shared records. The owner is not alone in the repository,
  owns only this experiment directory and must not edit or revert concurrent
  files.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium; later review is
  `gemini_reasoner`, `gpt-5.6-sol`, medium. No implementation route is selected.
- **Frozen project inputs:** accepted HIF architecture README SHA-256
  `39f15d2630184e5e918d53d53b00f1d4221b982292304efda32c2c4707c7baaf`
  and source receipt
  `1738744324d0a5cd1afc3beb598a401f1f9db1147a9d866cfd8790d61f608cb9`;
  observer-feasibility README
  `aa9fb9c1cfd2db26ffcce1f80b74808fa81aaeceea10f62af7713e9da5f7e6a6`;
  HIF DMA contract
  `a29d7b34aaa3b8942c3fb751c24f0493c74f2ff245cf9d3ca1353b157b4e7dfc`;
  SPM order and retained attribution
  `730731f169dac016b8146b0d4cd05783cb7b63ced45658eb4454f8192f227f6e`
  and `9b7dca863dec9d979cf38827d5a3a196327e563e066f669b23e9aaf2c316075e`;
  WLAN common-lifetime README
  `d3a1955019680e3884d5a69ff89da6a9aa9f3e2fbcf344d65a8f68a241e8f470`.
- **Predicate matrix:** assess separately (1) DMA API address joined to the
  programmed source/destination and `ADDR2` values; (2) HIF endpoint
  translation joined to `EN`/`INT_FLAG` progression; (3) positive channel-idle
  witness before unmap/release; (4) attributable firmware-stop completion; and
  (5) coherent CONSYS OFF order/effects. A cycle identity and success predicate
  must join every accepted fact. Partial predicates remain partial.
- **Repository phase:** exhaust the relevant committed experiment records and
  hardware documents first. Pin exact paths and hashes. Distinguish live/runtime
  observations from source/static facts, fixtures, proposals and negative
  results. Do not promote a source-derived register value to an observation.
- **Private phase:** only if repository evidence is insufficient, use the
  approved `./scripts/dev-vm re-shell` path for read-only analysis of the sole
  retained immutable Gemini vendor evidence workspace. Begin with a bounded
  filename/type/size inventory. Exclude credentials, keys, calibration/NVRAM,
  firmware image contents, partition dumps, raw block data, personal data and
  analysis databases. Inspect at most 30 plausible existing text/log records
  totaling at most 10 MiB. Read no binary body and create no analysis database.
  Record only hashes, sizes, sanitized relative evidence classes, bounded term
  counts and independently worded conclusions; publish no raw excerpts,
  private paths, addresses tied to personal identifiers or proprietary bytes.
- **Search boundary:** relevant terms may include the exact public register and
  lifecycle names already recorded in the frozen inputs (`ADDR2`, AP-DMA source
  and destination, `EN`, `INT_FLAG`, HIF endpoint, WLAN init/exit, firmware
  ready/stop, CONSYS power-off). A term hit is not evidence until its producer,
  cycle, ordering and success semantics are attributable. Stop rather than
  expanding into whole-binary disassembly, decompilation, database import,
  vendor debug ABI execution or an unbounded source tree audit.
- **Acceptance:** exact input verification; bounded inventory and selection
  receipt; a five-row observation/source/missing matrix; cycle-identity and
  ordering assessment; explicit contradictions and negative results; exact
  statement of what existing evidence can and cannot transfer; one next
  discriminator. A well-supported no-existing-evidence stop is acceptable.
- **Mandatory exclusions:** no live device/SSH, radio/firmware action, trace or
  debug ioctl, register read/write, module/interface transition, retained
  instruction observer/checker repair, private binary decoding, network lookup,
  kernel/build/VM mutation, patch/config/manifest/series edit, upstream contact,
  support claim, authorship or DCO action.
- **Validation:** create only `README.md`, `inputs.json`, `inventory.json`,
  `evidence-matrix.json`, `FREEZE.md`, an assert-free verifier and
  `VALIDATION.md` under this experiment. Normal and optimized verifier runs must
  reject mutations covering every input, bound, evidence class, predicate,
  cycle join, limitation and effects flag. Record actual checks and review-ready
  UTC. Raw private output, if any, remains mode-0600 in one fresh mode-0700 guest
  child and is not exported.
- **Stop/escalation:** stop on identity drift, unclear private ownership,
  sensitive-data risk, cap overflow, binary-only evidence, need for a new
  observer, conflicting cycle attribution or any attempt to infer through a
  missing runtime join. Return exact evidence, unresolved question and the next
  discriminating check; do not repair by adding a second access method.
- **Handoff:** exact parent/input hashes, repository/private inventory counts,
  selected-record hashes, five predicate verdicts, cycle/ordering status,
  privacy/effect postconditions, verifier mutation counts, limits and
  review-ready UTC.
- **Efficiency loop:** if independently accepted, append one sanitized accepted
  offline item to the active workflow cohort with actual timestamps/routes,
  review outcome and measured credits or explicit unavailability.
