# Checked pre-negotiation identity measurement

Status: consumed by the [successful runtime measurement](results/runtime-1.json).
The protocol below records the single admitted attempt; it does not authorize
repetition.

Hypothesis: the measured chip framing also carries HW and ROM register replies
with the Gemian-reported 0x8a00 values. The unique observation is the attributable
chip/HW/ROM tuple, not another raw chip capture.

Select only the validated package built from 720269885122a88e0d9b175783c26199f7956e05,
profile mt6797-a53-wmt-versions-compile. Candidate pins are in [the receipt](results/candidate.json). Its manifest digest
is d6a22f27246ea98632fb11f057249fc6ff254f3e5a0f4a08d09e76b390b93b53. The unchanged
identity selector keeps WLAN disabled; the kernel exposes wmt_versions.

Use the existing guarded boot2 installer and reviewed capture/session tools with
only reviewed candidate, release, private output path and trigger substitutions.
Resolve logical boot2 from Gemian GPT, verify inactive/unmounted/non-root state,
size, writability and stable power. Record the installed predecessor, require
full-partition matching readback, then shut down. The owner selects boot2.

On mainline, require changed boot identity, exact kernel release, direct USB SSH,
active ttyS0 console and positive AP-DMA clock votes. Before WMT setup, preserve
two equal region-19 preimages. Require exact existing setup records, clear-prefix
readback and unchanged suffix before one wmt_versions trigger. Restore sysfs
read-only after the attempt and retain stdout/stderr and process completion.
Never treat printf status as firmware acceptance.

The shared kernel owner consumes one attempt. Checked chip, HW and ROM reads
run in order, each only after preceding success, with persistent records and
first-error stopping. Whole budget 1500 ms, per-read maximum 500 ms, maximum
combined 78 THR bytes, 66 RBR bytes, 192 services and three sequential exclusive
IRQ registrations. Existing reviewed setup runs once. No negotiation, patch,
DLM/MCU-clock write, PA/calibration, WLAN START or radio action follows.
Power/clocks remain held after success or failure.

Seal the complete log, independently validate exact commands/replies and
terminal counters, and run the existing A53 serviceability regression. Return
through the reviewed native recovery only after preservation and exact boot and
recovery-tool checks. Confirm changed-boot Gemian. Unknown replies remain private.

Decision branches:
- All three exact checked replies: measured tuple 0279/8a00/8a00; reconcile ROM
  applicability, then implement the current plan's re-triggerable common-init
  executor. The tuple alone does not admit writes or prove Wi-Fi support.
- Different or partial reply, timeout or prerequisite failure: retain raw bytes,
  first failure and completed steps; stop without later reads or retry. Diagnose
  the exact difference offline before another decision-changing candidate.
- Unexpected heat, power/charging or recovery behavior: follow SAFETY stop rules.
