# Work item: passive Gemian CONSYS ownership snapshot

- **Outcome:** determine whether the known-good Gemian system exposes the exact
  connectivity reservation and OS-visible WLAN/CONSYS owners through passive
  documented interfaces, without reading live device registers.
- **Owner and reviewer:** `/root` is the sole device custodian and execution
  owner; a bounded Astra Medium safety/ownership review precedes collection;
  `/root` integrates the sanitized result.
- **Scope:** this experiment only. Read-only inputs are `/proc/device-tree`,
  `/sys/bus/platform`, `/proc/iomem`, kernel release, boot ID
  and model. No other workstream files change until the result is accepted.
- **Model route:** Astra Medium review for the novel shared-resource ownership
  boundary; Sol Medium coordination/integration. Device access is not delegated.
- **Stop/escalation:** stop on non-Gemian release/model, changed boot identity
  during collection, missing authenticated known-host access, unexpected command
  requirements, output beyond 64 KiB, or any need for privilege, register I/O,
  mounting, radio control, calibration reads or state changes.
- **Parent:** project commit
  `99831dc50f93577c4535ae96d56adfc774985a3f`; live preflight observed Gemian
  `3.18.41+`, boot ID `ce741f2c-462f-424e-aa90-49bada3a116f`, model `MT6797X`.
- **Dependencies:** known-good authenticated `gemini` SSH alias and current
  Wi-Fi ownership contracts. No kernel/profile/package dependency.
- **Validation:** shell syntax, ShellCheck and nine host refusal fixtures;
  review exact command allowlist and enforcement wrapper; one collector attempt;
  identity at both boundaries; fixed-key sanitized result; repository
  publication gate before commit.
- **Hardware:** one read-only Gemian collection, one SSH process, ten-second
  remote deadline and 64 KiB output limit. No boot, partition, firmware,
  calibration, radio, power, reset, MMIO or DMA operation. Custodian `/root`.
- **Upstream:** evidence informs the private CONSYS manager/resource binding;
  it creates no upstream patch or certification.
- **Owner-away work:** authorized by the standing Gemian inspection policy and
  the owner's current availability message; no physical interaction is needed.
- **Device readiness:** ready for this passive observation only; no deployment.
- **Handoff:** record exact observed paths/absence, interpretation limits,
  consumed budget and next implementation decision.
- **State:** complete. The first draft was refused before collection and
  repaired; Astra accepted the exact revised collector, and the sole live
  attempt was consumed successfully. The post-result SSH wrapper warning fix
  did not trigger a repeat.
- **Efficiency loop:** device sessions are excluded from accepted offline items.
