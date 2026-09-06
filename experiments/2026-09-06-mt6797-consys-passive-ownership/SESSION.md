# Passive Gemian ownership session

## Identity and ownership

- Experiment and custodian: this experiment; `/root` is the sole custodian.
- Preparation/device state: complete / known-good Gemian remained running.
- Frozen repository revision: `99831dc50f93577c4535ae96d56adfc774985a3f`.
- Current authenticated preflight: release `3.18.41+`, boot ID
  `ce741f2c-462f-424e-aa90-49bada3a116f`, model `MT6797X`.
- Transport: known-host `gemini` SSH alias with its dedicated key.

## Question and dependencies

- Hypothesis: passive kernel metadata identifies the CONSYS reservation and
  bound WLAN/CONSYS resource owners sufficiently to narrow a manager binding.
- Pass: one stable identity plus coherent reservation classification/range and
  named platform owners. Inconclusive: missing/unreadable metadata. Failure:
  conflicting ranges/owners or identity change.
- No result permits register access, resource activation or firmware loading.

## Offline completion

- Script syntax, ShellCheck and all nine collector refusal fixtures must pass
  before collection.
- A hardware-ownership safety review must accept the exact allowlist and the
  `collect.py` enforcement wrapper.
- Output parser is manual and fixed to public hardware metadata fields; no
  private record, calibration or firmware content is requested.

## Session contract

- Exact candidate: the already-running known-good Gemian system; no deployment.
- Budget: one SSH process, one collector execution, ten remote seconds, a
  15-second host deadline, and at most 64 KiB combined stdout/stderr. The host
  wrapper kills the process group on deadline or excess output. Failure consumes
  the attempt.
- Allowed: reads from identity files, `/proc/device-tree`,
  `/sys/bus/platform` and `/proc/iomem`, plus `readlink`, `od`, `sed`, `awk`,
  `tr`, `wc` and shell builtins over those reads. DT context includes root and
  reserved-memory `#address-cells`, `#size-cells`, `ranges`, matching node `reg`,
  `no-map` and `reusable` presence.
- Excluded: all writes, sudo, mounts, device nodes, debugfs, register reads,
  radio/network configuration, firmware/calibration files and service control.
- Stop: identity mismatch/change, timeout, excessive output or wider privilege/
  interface requirement. Safe interruption is process termination.
- Evidence: sanitized committed result only; no raw private device data.
- Recovery: none required because no state changes are admitted.

## Owner session card

No physical action is needed. The device stays on Gemian. If authenticated SSH
or identity fails, collection stops and offline work continues.

## Result handoff

The one permitted attempt was consumed and completed in 0.7 seconds with stable
identity. The live DT confirmed a dynamic no-map `consys-reserve-memory` node
without `reg`; `/proc/iomem` was unreadable, so the allocation base and extent
remain unresolved. `18070000.consys` was bound to `mtk_wmt`, and the WLAN
cross-check `180f0000.wifi` was bound to `mt-wifi`. No state-changing interface
was used and the device remains on Gemian. See `results/observation.json` for
the complete sanitized result and exact executed-script hashes. No repeat is
authorized by this contract.
