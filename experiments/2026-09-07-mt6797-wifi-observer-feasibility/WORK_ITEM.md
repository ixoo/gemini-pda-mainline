# Work item: test the known-good Gemian HIF observer boundary

- **Status:** bounded read-only preflight accepted at
  `2026-09-07T19:11:51Z`; no observer or radio action admitted.
- **Outcome:** determine whether the already running known-good Gemian kernel
  exposes a standard read-only/dynamic-tracing path capable of attributing the
  Wi-Fi HIF load/shutdown lifetime evidence required by the accepted
  [upstream architecture review](../2026-09-07-mt6797-hif-upstream-architecture/README.md).
  Return a precise feasibility stop if the required observer is absent.
- **Parent:** repository commit
  `0593a6b9ed6b72fb9578ee8da2f38d14e86a7b23` on `origin/main`.
- **Custodian and route:** `/root` was the sole live-device custodian. This was
  a direct Sol Medium integration preflight, not delegated work or an
  implementation item. Independent Astra Medium review accepted the bounded
  stop after one evidence-scope wording repair.
- **Chronology:** the direct preflight began before this record was written.
  This file documents the completed bounded scope and does not retroactively
  expand it. Exact invocation chronology and the accepted coherent snapshot
  are in [the result](results/observer-feasibility.json).
- **Frozen target:** the usual authenticated private-LAN Gemini endpoint, the
  existing mode-0600 ignored identity, known-good Gemian release `3.18.41+`,
  AArch64 and root `/dev/mmcblk0p29`. Refuse a different OS or changed boot
  identity within the coherent snapshot.
- **Owned scope:** authenticated reads of OS/boot identity, `wlan0` presence,
  operational state and driver link, debugfs/tracing interface presence,
  `/proc/config.gz` booleans and noninteractive privilege availability. Publish
  no MAC address, network credentials, private key material, calibration,
  firmware bytes, serial/IMEI or private paths.
- **Hypothesis:** if the live kernel supplies kprobe events or function tracing,
  a later separately reviewed protocol might observe exact retained WLAN
  entry/exit and HIF lifetime edges without rebuilding the vendor kernel. If it
  supplies only static event tracing or `nop`, this check must stop and must not
  infer the missing DMA/register/idle/firmware-stop facts.
- **Acceptance:** one coherent changed-ID-safe snapshot must establish exact
  OS/root identity, stable boot ID, live WLAN driver state, available tracer,
  relevant configuration booleans and probe/filter interface presence. A
  negative capability result is accepted when it names the absent mechanism
  and the next discriminator.
- **Mandatory exclusions:** no trace enablement, probe creation, event buffer
  read, interface transition, association change, firmware reload, module
  unload, ioctl, register access, debug command, suspend, shutdown, reboot,
  boot2 action, partition access or persistent device write. Do not resume the
  owner-closed retained-instruction observer/checker line.
- **Stop condition:** stop after the coherent capability snapshot, or earlier
  on identity drift, authentication failure, unexpected mutation need or a
  missing safe standard interface. Do not repair an absent observer on-device.
- **Validation and effects:** compare boot identity before and after the final
  snapshot; preserve invocation/refusal chronology; run repository JSON/link
  checks after integration. No build, VM, private-capture read, firmware/radio
  action, upstream contact or hardware-support claim.
- **Workflow measurement:** this live-device preflight is not an accepted
  offline item. Record it as an excluded considered item in the active routing
  cohort if the result is accepted.
- **Handoff:** exact capability verdict, coherent sanitized snapshot, failed
  preliminary query disclosure, limits, next discriminating evidence and
  review-ready UTC.
