# Experiment: Gemini CPU, PSCI, and architectural-timer recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-cpu-psci-timer-recovery` |
| Status | `inconclusive` for mainline runtime; generic source contract confirmed |
| Subsystem | ARM64 CPU topology, PSCI, GIC PPIs, clocksource, clockevents, and idle states |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-13 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Does the MT6797 Gemini expose the standard ARM64 PSCI and architectural-timer
contracts expected by Linux 7.1.x, or does it require a new CPU/timer driver?
The working hypothesis is that the CPU topology, PSCI transport, GIC PPIs, and
architectural counter can use generic Linux support; vendor deep-idle states
must remain disabled until their firmware semantics are proven.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Private raw capture: `artifacts/device-inventory/20260713-live/cpu-psci-timer.txt`
  (Git-ignored, mode 0600).
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: prepared Linux `7.1.3` tree in the development VM.
- Sanitized source result:
  [`results/mainline-cpu-psci-timer-validation.txt`](results/mainline-cpu-psci-timer-validation.txt).
- Historical package contract audit:
  [`results/mainline-cpu-psci-timer-current-package-20260714.txt`](results/mainline-cpu-psci-timer-current-package-20260714.txt).
- Current 72-patch package contract audit:
  [`results/mainline-cpu-psci-timer-current-72-package-20260714.txt`](results/mainline-cpu-psci-timer-current-72-package-20260714.txt)
  (audit SHA-256 `d6d84d6efa3314cbf43918556d812b56c18e9904550209a2cea0e7fbe7a368c7`).
- Current 76-patch Image/DTB package contract audit:
  [`results/mainline-cpu-psci-timer-current-76-package-20260714.txt`](results/mainline-cpu-psci-timer-current-76-package-20260714.txt).
- CPU frequency metadata audit:
  [`results/cpu-frequency-hint-audit-20260713.txt`](results/cpu-frequency-hint-audit-20260713.txt).
- Independent hardware-tested comparison: the bsg100 Linux 6.6 CPU/PSCI
  logs are normalized by [`audit-bsg100-cpu-crosscheck.sh`](scripts/audit-bsg100-cpu-crosscheck.sh)
  into [`results/bsg100-cpu-psci-crosscheck-20260714.txt`](results/bsg100-cpu-psci-crosscheck-20260714.txt).

## Safety assessment

Both the device collector and source analyzer are read-only. The collector reads
CPU/sysfs state, `/proc/cpuinfo`, `/proc/interrupts`, `/sys/power` metadata, and
flattened-DT properties. It does not online/offline a CPU, enter idle or
suspend, invoke PSCI, write a release address, read dmesg, or alter firmware.
The raw capture must remain private because it describes the device's complete
CPU/resource layout.

## Associated code

From the repository root:

```sh
mkdir -p artifacts/device-inventory/20260713-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-13-cpu-psci-timer-recovery/scripts/collect-live-cpu-psci-timer.sh \
  > artifacts/device-inventory/20260713-live/cpu-psci-timer.txt
chmod 700 artifacts/device-inventory/20260713-live
chmod 600 artifacts/device-inventory/20260713-live/cpu-psci-timer.txt
./scripts/dev-vm run \
  experiments/2026-07-13-cpu-psci-timer-recovery/scripts/analyze-cpu-psci-timer-contract.sh
```

The analyzer reads only immutable vendor Git objects and the prepared Linux
tree. It emits source hashes, bounded DT/source excerpts, and the reuse
decision; it does not copy vendor code.

## Procedure

1. Run the key-only collector once without changing CPU online state or power
   policy.
2. Repeat only bounded consistency reads if the downstream sysfs masks change;
   do not “fix” an offline CPU as part of this experiment.
3. Compare the live DT properties and interrupt names with the vendor MT6797
   DT/source and Linux 7.1.3 PSCI/timer bindings and implementations.
4. Leave mainline runtime status unchanged until a non-primary boot validates
   CPU bring-up, timer interrupts, and recovery from a failed CPU-on attempt.

## Observations

- The flattened DT contains ten CPU nodes: Cortex-A53 MPIDRs `0x000`–`0x003`
  and `0x100`–`0x103`, plus Cortex-A72 MPIDs `0x200` and `0x201`. Every node
  uses `enable-method = "psci"` and the same firmware release mailbox address
  `0x40000200`. The vendor DT's `clock-frequency` values decode to 1.391 GHz,
  1.950 GHz, and 2.288 GHz for the three populated groups; these are
  descriptive boot values, not a safe OPP table.
- PSCI is `arm,psci-0.2` over `smc`. The live function IDs are the standard
  SMCCC values `0x84000001` (CPU_SUSPEND), `0x84000002` (CPU_OFF),
  `0x84000003` (CPU_ON), and `0x84000004` (AFFINITY_INFO).
- The timer node is `arm,armv8-timer` with PPIs 13, 14, 11, and 10 and a
  `clock-frequency` of `0x00c65d40` = 13,000,000 Hz. The live clocksource is
  `arch_sys_counter`; clockevent slots 0 and 1 select `arch_sys_timer`.
  The vendor-only MT6797 CPU GPT interrupts are separate resources and are not
  a reason to replace the ARM architectural timer.
- The downstream cpuidle DT has `cpu-sleep-0-0` with PSCI state `0x00010000`
  and `cluster-sleep-0` with `0x01010000`. The live sysfs state names are
  vendor `dpidle`, `SODI3`, `SODI`, `MCDI`, `slidle`, and `rgidle/WFI`; only WFI
  has non-zero usage in the capture. These states depend on vendor SPM/PCM and
  must not be enabled in mainline by copying their names or parameters.
- CPU online reporting is not stable in the downstream kernel. The capture's
  global mask read `online=0` and `/proc/cpuinfo` listed processor 0, while the
  same capture's per-CPU files marked CPU0 and CPU1 online; separate immediate
  reads returned global `0-1` and `/proc/stat` counters for CPU0 and CPU1.
  Earlier baseline evidence also saw CPU0/CPU1 online and CPU2–CPU9 offline.
  This is recorded as a vendor sysfs/reporting contradiction, not evidence that
  all ten CPUs are currently usable.
- The vendor MT6797 DT/source and Linux 7.1.3 both use the same PSCI and
  `arm,armv8-timer` bindings. Linux's generic `drivers/firmware/psci/psci.c`
  accepts this PSCI 0.2 node, and `drivers/clocksource/arm_arch_timer.c`
  consumes the exact timer compatible and frequency property.
- The generated Linux 7.1.3 Gemini DTB was inspected independently of the
  vendor capture. It contains ten CPU nodes with the expected MPIDRs and
  `enable-method = "psci"`, a minimal `arm,psci-0.2`/`smc` node, and the
  four architectural-timer PPIs. It intentionally omits the vendor
  `cpu-release-addr`, `cpu-idle-states`, per-CPU `clock-frequency`, PSCI
  function-ID properties, and timer `clock-frequency`: Linux PSCI 0.2 uses
  the standard IDs, the CPU binding rejects the per-CPU frequency property,
  and the architectural timer prefers firmware-configured `CNTFRQ` unless a
  broken firmware workaround is proven necessary.
- The authoritative current 72-patch package was audited separately from the
  older source result: it contains ten `enable-method = "psci"` CPU nodes, one
  `arm,psci-0.2` SMC node, one architectural timer with PPIs 13/14/11/10, and
  zero CPU OPP, idle-state, `cpu-release-addr`, or per-CPU
  `clock-frequency` properties. `CONFIG_ARM_PSCI_FW`, `CONFIG_ARM_PSCI_CPUIDLE`,
  `CONFIG_ARM_ARCH_TIMER`, and `CONFIG_ARM_GIC_V3` are built in; the generic
  cpufreq/SVS modules are package-only and have no Gemini consumer. See the
  [current-package audit](results/mainline-cpu-psci-timer-current-72-package-20260714.txt).
- The prepared configuration enables `CONFIG_ARM_PSCI_FW`,
  `CONFIG_ARM_ARCH_TIMER`, `CONFIG_ARM_GIC_V3`, and generic CPU idle support.
  The PSCI binding check, architectural-timer binding check, focused CPU
  binding check, and full-schema validation of `mt6797-gemini-pda.dtb` all exit
  successfully after removing the vendor-only per-CPU frequency metadata. This
  validates the static handoff contract; it does not validate the retained
  firmware's CPU-on or timer behavior under a mainline kernel.
- The independent bsg100 Linux 6.6 sequence confirms the generic PSCI path is
  usable for CPU1 and CPUs1–7, but records a separate CPU8/A72-cluster
  `CPU_ON` failure; `maxcpus=8` was used as a hardware-tested A53-only
  workaround. This is not copied into the current 7.1.3 command line: the
  current board retains all ten generic CPU nodes and no `maxcpus` token so the
  first boot can identify whether the same boundary exists after the newer
  kernel's clock/power changes. See the [cross-check result](results/bsg100-cpu-psci-crosscheck-20260714.txt).
- The fresh 2026-07-14 vendor handoff refresh adds loader-policy evidence:
  LK injects `maxcpus=5`, `console=ttyMT0,921600n1`, and
  `printk.disable_uart=1`, while only CPUs 0–1 are online in that snapshot.
  This does not contradict the ten-node topology; it means the effective
  post-LK command line and CPU_ON results must be captured during a mainline
  boot. See the [handoff refresh](../2026-07-13-memory-carveout-recovery/results/live-handoff-refresh-20260714.txt)
  and the [current 76-patch audit](results/mainline-cpu-psci-timer-current-76-package-20260714.txt).

## Analysis

The observed identity and resource contracts match Linux's generic ARM64 CPU,
PSCI, GIC, and architectural-timer implementations. A new driver is not
justified by the MT6797 name alone. The MT6797-specific vendor timer/GPT and SPM
code are separate facilities: they do not replace the architectural counter or
prove that the vendor PSCI suspend-state encodings are safe for mainline.

Linux 7.1.3's CPU binding has no `clock-frequency` property and sets
`unevaluatedProperties: false`; a focused validation of the pre-audit DTB
rejected all ten vendor frequency entries. The local board patch therefore
keeps those values only in this evidence record and carries no per-CPU
frequency metadata. The generic SoC DTS supplies the CPU nodes, PSCI node, and
architectural timer. It intentionally does not carry the vendor idle-state
nodes. A future change may add a new platform-specific idle/firmware driver if
experiments recover a different contract, but it must not silently repurpose
generic PSCI around an unverified chipset ABI.

## Conclusion

`confirmed` as a source-level reuse decision for generic ARM64 topology, PSCI,
GIC PPIs, and `arm,armv8-timer`; `inconclusive` for actual Linux 7.1.x runtime.
No mainline image was booted and no CPU hotplug, PSCI suspend, or timer test was
attempted.

## Follow-up

- Boot a non-primary mainline candidate and capture early PSCI/timer messages,
  all CPU bring-up results, and clockevent registration.
- Capture LK's final `/chosen/bootargs` before interpreting the candidate header
  `console=ttyS0` or deciding whether a diagnostic `maxcpus` cap is needed.
- If CPU8/9 reproduces the bsg100 failure, first use a diagnostic-only
  `maxcpus=8` candidate to separate the A53 boot path from the A72 power-domain
  problem; do not make that workaround part of the default patch layer until
  the failure is reproduced on Linux 7.1.3.
- Test one reversible CPU-on/off cycle at a time with an external recovery path;
  never begin with deep idle or system suspend.
- Determine why the vendor global CPU masks, `/proc/cpuinfo`, and per-CPU flags
  can disagree before treating online CPU count as a board invariant.
- Only after that evidence, evaluate whether any MT6797-specific idle or GPT
  support is needed in addition to the generic drivers.
