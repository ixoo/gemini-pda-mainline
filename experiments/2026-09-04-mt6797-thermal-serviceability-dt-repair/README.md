# Experiment: MT6797 thermal serviceability DT repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-serviceability-dt-repair` |
| Status | exact offline candidate selected; device attempt pending |
| Subsystem | MT6797 thermal observation and preserved USB serviceability |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Tracking goal | restore attributable thermal observation before longer CPU8/CPU9 load |

## Question or hypothesis

Does the exact thermal-stage-ledger kernel reach a read-only USB/netcat runtime
when its appended DT is derived from the exact runtime-proven PWRAP candidate
and changes only the root model, thermal reset/controller enablement, and one
policy-free thermal zone?

This repairs the observation-channel error in the preceding base-DT control.
That control used the package base DT, which explicitly disabled the USB
controller, its PHY, and the keyboard and lacked the proven simple framebuffer.
Its absence of USB was therefore built into the control and could not
distinguish a kernel failure from an unavailable observation path.

## Provenance and environment

- Published Buildbox commit:
  `b66b03c722cd67584fb8fb15de493ebb084954b4`.
- Release: `7.1.3-gemini-mt6797-thermal-stage-ledger`.
- `Image.gz`:
  `3e1ebb8de1aeb9ff1c6c6cbe655f18d1affd751959967bfd85507d280dedd2a2`.
- Configuration:
  `f0a135b24055229447d56ae6bda16e1ada683ebe4612af3ba0b96ec7febd375a`.
- Runtime-proven PWRAP DT:
  `e1e4eca289320533bad5c879e78055eaa86a295080b1154c13debe29ddd8ee4a`.
- Repaired thermal DT:
  `f131a06474ad5665dd957d7290f7b1240ca9603028046c93f4a5527ba3aa1366`.
- Runtime-proven initramfs:
  `344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b`.
- Selected raw Android-v0 image:
  `dd7a6ec45389dc87b658c7eb22ee7022230cb9f435439875b981903770c21bf0`,
  7,555,072 bytes.
- Selected exact 16 MiB `boot2` payload:
  `ca3c25889b92673aa341fa97fc347c3469bc3b532d81045659a3afa1f563636a`.

No kernel build is needed. The experiment reuses the fetched and validated
Buildbox package and the exact serviceability DT/initramfs that previously
proved USB, console, PWRAP/MT6351, and eMMC runtime. No native VM build is
permitted or used.

## Safety assessment

The runtime frame is read-only. It samples three temperatures one second apart
but issues no CPU request, load, cpufreq/OPP, hotplug, idle, suspend, reboot,
retained-RAM read, NVMEM-content read, sysfs write, or storage operation. CPU8
and CPU9 must remain offline.

Deployment is limited to the standing-authorized live-GPT-resolved inactive
logical `boot2`. The installer rejects active, mounted, held, wrong-size,
read-only, underpowered, unpublished, dirty, or wrong-checksum state. It skips
an already matching partition; otherwise it writes once, flushes, requires a
matching full-partition readback, and requests clean shutdown. Shutdown is
confirmed only after three consecutive closed TCP/22 samples. The verified
project-start backup remains the recovery source; no fresh backup is created.

## Associated code

- `thermal-serviceability.dtso` defines the isolated DT delta.
- `scripts/build_dtb.sh` and `scripts/validate_dtb.py` require the exact
  seven-property/two-node semantic delta and preserved serviceability nodes.
- `scripts/build_candidate.sh` and `scripts/validate_candidate.py` perform two
  deterministic transforms/container builds, LK validation, and exact padding.
- `scripts/remote_observe.sh`, `scripts/classify_observation.py`, and
  `scripts/collect_runtime.sh` source-pin and validate one bounded live frame.
- `scripts/install_boot2.sh` enforces the inactive-`boot2`, readback, no-new-
  backup, and confirmed-shutdown gates.
- `scripts/test_runtime_tools.py` exercises the positive classifier and thirteen
  rejecting mutations, then statically audits observation and install safety.

## Procedure

1. Validate the exact Buildbox package and runtime-proven source candidate.
2. Apply the overlay twice and require byte-identical repaired DTs; require the
   exact semantic delta and collision-free thermal phandle `0x2e`.
3. Assemble the Android-v0 candidate twice, require byte identity, independently
   validate every container member, and reproduce exact zero padding.
4. Publish the experiment before device use.
5. Install only the exact padded payload to guarded inactive `boot2`, require a
   matching full readback, and shut the Gemini down.
6. Pre-arm the observer and select `boot2` once. A pass requires the exact
   release/DT/reset identities, USB/netcat, console, CPU0--7, PWRAP/MT6351,
   eMMC, calibration provider, thermal bind, one zone, and three plausible
   nonzero temperatures with no targeted error or action.

## Observations

Offline construction and validation pass. Relative to the exact runtime-proven
PWRAP DT, the output adds only `/thermal-zones` and its `soc-thermal` child and
changes exactly seven properties: root model, thermal phandle, thermal reset,
thermal status, two polling values, and the zone sensor reference. The output
preserves enabled T-PHY, USB PHY/controller, keyboard, eMMC, PWRAP reset
`<3 1>`, and simple framebuffer. Standalone AUXADC remains disabled.

Two DT transformations and two container assemblies are byte-identical. The
complete package and LK validators pass, and the exact raw and padded hashes
reproduce. The runtime positive fixture passes; thirteen identity, reset, USB,
thermal, CPU, console, eMMC, temperature, action, and boot-ID mutations reject.
Shell syntax, ShellCheck, source pins, single live-GPT write, no-new-backup,
full-readback, and closed-TCP shutdown requirements pass offline.

## Analysis

This is the smallest attributable recovery from the invalid base-DT control:
the observation path comes from a previously live-proven DT, while the thermal
delta remains explicit and independently validated. A live passing frame would
close the temperature-observability prerequisite for the next bounded A72
load. A changed-ID Gemian return without USB would now be a real regression
against the exact preserved observation-path baseline, although an empty
retained record would still not prove which early stage executed.

## Conclusion

The exact candidate is confirmed offline and selected for one device attempt.
No runtime thermal-support claim is made yet.

## Follow-up

The ordered next action and the condition for resuming CPU8/CPU9 load work are
owned by [`docs/ROADMAP.md`](../../docs/ROADMAP.md).
