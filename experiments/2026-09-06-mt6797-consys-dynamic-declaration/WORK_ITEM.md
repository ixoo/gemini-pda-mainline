# Work item: passive Gemian dynamic CONSYS declaration

- **Outcome:** determine whether the running known-good Gemian DT supplies the
  `size`, `alignment` and `alloc-ranges` inputs needed to validate the exact
  reg-less CONSYS reservation declaration.
- **Owner and reviewer:** `/root` is sole device custodian and execution owner;
  Astra Medium reviews the frozen protocol before its one live collection;
  Sol Medium integrates the sanitized result.
- **Scope:** this experiment only. Read identity plus the named
  `/proc/device-tree/reserved-memory` context and
  `consys-reserve-memory/{reg,size,alignment,alloc-ranges,no-map,reusable}`.
- **Model route:** Sol Medium coordination; Astra Medium safety/ownership review
  because the result constrains shared CONSYS memory ownership.
- **Stop/escalation:** refuse on identity drift, missing exact node, more than
  one execution, privilege or broader-interface need, timeout, output overflow
  or a request for allocation/register/calibration/radio state.
- **Parent:** `aa94cd163701d6542249700693b2aeb153460d13`; preflight observed
  Gemian `3.18.41+`, boot ID `ce741f2c-462f-424e-aa90-49bada3a116f`, model
  `MT6797X`.
- **Dependencies:** consumed passive-ownership result and accepted dynamic
  reserved-memory parser. This is a new property set, not a repeat of that
  collector and not evidence of successful allocation.
- **Validation:** Bash syntax, ShellCheck, host refusal fixtures, exact allowlist
  review, one 10-second SSH collection capped at 16 KiB, stable boundary
  identity, sanitized fixed-key result and repository publication gate.
- **Hardware:** one read-only SSH process; no boot, sudo, mount, device node,
  debugfs, `/proc/iomem`, MMIO, DMA, power, reset, firmware, calibration or radio
  operation. Custodian `/root`.
- **Upstream:** informs the passive reserved-memory binding only; no submission
  or hardware-support claim.
- **Owner-away work:** standing Gemian read-only inspection permits this session;
  no physical interaction is required.
- **Device readiness:** ready only after specialist review; no deployment.
- **Handoff:** exact property shape, parser implication, unresolved allocation
  facts, consumed budget and next implementation decision.
- **State:** complete. The one live attempt passed with stable identity and was
  consumed; the declaration is parser-compatible while current allocation
  identity remains unresolved.
- **Efficiency loop:** device sessions are excluded from accepted offline items.
