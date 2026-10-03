# Experiment: first MT6797 WMT default query

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-default-query` |
| Status | `in-progress` (compile preparation; no device admission) |
| Subsystem | CONSYS / BTIF / WMT |
| Device | Project Gemini PDA |
| Investigator | Codex, under owner standing authorization |
| Tracking issue | [#25](https://github.com/ixoo/gemini-pda-mainline/issues/25) |

## Question and boundary

Can the freshly powered CONSYS MCU answer the fixed default WMT option query
through BTIF mandatory STP, before WLAN HIF or common initialization?
The [startup review](../2026-10-03-mt6797-wifi-audit/BTIF_MANDATORY.md) owns the
source identities, register conflicts and host fault fixtures. This experiment
owns integration, build and any later exact candidate/runtime receipt.

## Selected compile inputs

Profile `mt6797-a53-wmt-default-query-compile` uses the existing WMT-before-start
foundation through proposal 0052, followed by proposals 0086–0091. It does not
select the later receive-sampling stack or parked proposal 0085. The executor
and wire helper are byte-identical to the host-tested drafts. The binding and
CONSYS owner acquire exact BTIF/channel resources and existing upstream clocks.
A source-fingerprinted level-low SPI 130 must inherit the MT6797 sysirq provider;
actual IRQ mapping occurs only after admitted CONSYS reset release.

The isolated board disables the WLAN child. Probe enables no transport clocks
and performs no query. After private region-19 preservation and its existing
one-shot preparation, the root-only `wmt_default_query` attribute replaces the
WLAN trigger. It reuses the existing prepower admission and power/reset sequence,
then stops after the query, with all four HIF/EMI-copy/WLAN-start arguments false.
The inherited diagnostic DT flags describe the foundation; the query-only
property overrides their runtime continuation. No Wi-Fi PA rail, calibration,
full-mode negotiation, ROM patch or WLAN firmware transfer belongs to this test.

## Validation and remaining admission

Run the existing sanitizer host fixtures and strict patch style checks. Synthetic
archive patches deliberately carry no invented DCO; checkpatch excludes only
`MISSING_SIGN_OFF` and the new-file MAINTAINERS reminder. Check exact replay,
canonical profile order, staged privacy/license/link checks and repository gates.
Compile only from a clean pushed checkout:

```sh
KERNEL_PROFILE=mt6797-a53-wmt-default-query-compile ./scripts/build-kernel --backend buildbox
```

Exact five-file replay, byte equality with both host-tested helpers,
sanitizer-backed host fixtures, strict patch style and repository checks pass.
The [first Buildbox attempt](results/build-1.json) failed DT compilation on
two clock references to an absent `infracfg` label. Proposal 0091 uses the
existing `infrasys` label. No validated package was produced. The complete
private log is retained by digest; DT/schema validation remains incomplete.
Proposal 0090 also fixes a reviewed deadline-underflow race by sampling
`jiffies` once, with a deadline-drift fixture that rejects the older executor.
Before any boot candidate, review the finite MMIO/IRQ effects, FIFO alias writes,
the initial DMA_EN timeout acknowledgment, shared AP-DMA clock-enable effects,
channel exclusion and power-retaining failure/recovery lifetime. Host fixtures
do not model real MMIO or IRQ concurrency. Do not use this record as a hardware
admission or installation instruction. No device has been contacted.

A later admitted test will consume one exact query lifetime: a matched response
establishes transport liveness; timeout or malformed/extra data stops without
retry and keeps the transport question open. Neither outcome establishes RF
calibration, reception, association or working Wi-Fi.
