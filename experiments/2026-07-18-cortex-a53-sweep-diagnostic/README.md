# Candidate O: Cortex-A53 sweep diagnostic

## Status

Build validation: **complete**. Two clean-tree VM outputs are recursively
byte-identical. Logical `boot2` synchronization: **complete**, including full
backup, flush, and byte-identical full readback. Runtime decision oracle:
**passed once on the current Gemini PDA unit**.

| Field | Value |
| --- | --- |
| Experiment | `2026-07-18-cortex-a53-sweep-diagnostic` |
| Candidate | O |
| Baseline | exact Candidate N artifact `candidate-N-cpu1-online-7cdb4b99` |
| Marker | `GEMINI_A53_SWEEP_20260718_O` |
| Device write target | logical `boot2` only, through the repository safety procedure |

## Question

With Candidate N's exact kernel, configuration, DTB, LK container contract,
framebuffer console, ramoops, and no-IRQ watchdog recovery held constant, can
each remaining Cortex-A53 CPU (CPU2 through CPU7) be brought online and execute
work after the already-proven CPU1?

Candidate O tests the complete Cortex-A53 set in one bounded pass. CPU1 through
CPU7 are requested sequentially. The Cortex-A72 CPUs, CPU8 and CPU9, are
explicitly validated as offline and are never written. This larger step is
intentional now that Candidate N proved one secondary CPU and a durable
watchdog-recovery observation path. The per-CPU checkpoints preserve a useful
bisect boundary if a later CPU fails.

## Exact baseline

The builder accepts only Candidate N with these pinned properties:

- boot image SHA-256:
  `43aea71224f6261001ff00904b30dae29063334172a2f6b0163b424a84c0e3aa`
- initramfs SHA-256:
  `3351422e594c59e5785e12cac6ffbefa2644bd6c85932ac6825a9b9c5edd6290`
- `Image.gz` SHA-256:
  `0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3`
- appended DTB SHA-256:
  `c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379`
- embedded config SHA-256:
  `5a0c442c67b64cbabd4d030c93d50837bfc93e34d8878b413805457bfcd8e7cd`

The only payload change is `/init` in the initramfs. Kernel bytes, appended DTB,
embedded configuration, Android-v0 addresses, LK-compatible layout, header
name, and header command line are byte-identical to Candidate N.

## CPU contract

The build-time validator requires this exact logical topology from the pinned
DTB:

| Logical CPU | DT node | Core | Candidate O action |
| --- | --- | --- | --- |
| 0 | `cpu@0` | Cortex-A53 | boot CPU; already online |
| 1 | `cpu@1` | Cortex-A53 | request online; repeat the N checkpoint |
| 2 | `cpu@2` | Cortex-A53 | request online |
| 3 | `cpu@3` | Cortex-A53 | request online |
| 4 | `cpu@100` | Cortex-A53 | request online |
| 5 | `cpu@101` | Cortex-A53 | request online |
| 6 | `cpu@102` | Cortex-A53 | request online |
| 7 | `cpu@103` | Cortex-A53 | request online |
| 8 | `cpu@200` | Cortex-A72 | validate offline; never write |
| 9 | `cpu@201` | Cortex-A72 | validate offline; never write |

All CPU nodes must use PSCI, and `/psci` must use the SMC method. The initramfs
revalidates the live DT links and begins only when `possible=0-9`,
`present=0-9`, `online=0`, and `offline=1-9` are exact.

## Runtime oracle

The MediaTek watchdog is opened before the first CPU request, receives one
ownership-handoff ping, and receives no further pings. Its timeout remains 31
seconds. A request is not started after 23 seconds from that ping; a two-second
accounting sample is not started after 25 seconds.

For each CPU, the initramfs records:

1. the expected cumulative online mask before the request;
2. a single write of `1` to that CPU's standard `online` control;
3. the write result and resulting cumulative mask;
4. the target CPU's kernel boot line plus bounded GIC and I-cache context;
5. two `/proc/stat` samples proving the target CPU accumulated work; and
6. a durable `checkpoint=PASS` marker.

The sweep stops at the first failed gate and waits for watchdog recovery. A
complete pass requires `online=0-7`, `offline=8-9`, CPU8 and CPU9 still reading
`0`, and the unique marker:

```text
GEMINI_A53_SWEEP_20260718_O sweep_result=online-0-7 SUCCESS cpu8=offline cpu9=offline
```

The reset and subsequent return to the known-good OS are part of the oracle.
After that cycle, recover ramoops with `scripts/collect-device-pstore`; do not
infer success from display text alone.

## Decision table

| Last durable evidence | Conclusion | Next action |
| --- | --- | --- |
| complete success marker and watchdog recovery | CPU1-7 each booted and accumulated work | preserve O as the SMP checkpoint; begin the rotation-only candidate |
| `checkpoint=PASS` through CPU *n*, then CPU *n+1* stop | CPU1-*n* passed; failure is bounded to the next request or its validation | make a focused derivative for CPU *n+1* using O's exact bytes |
| inventory, DT, or watchdog gate fails | experiment did not reach a valid CPU request | fix that observation/contract path; do not blame SMP |
| no O marker in changed-cycle pstore | Candidate O execution was not established | verify the selected slot and `boot2` full-partition checksum before changing kernel code |
| no watchdog recovery after an O marker | recovery oracle failed | restore the last proven recovery path before another SMP expansion |

## Runtime result

Candidate O passed its first attributable run. A cycle-aware collector started
from known-good Gemian, observed the device disconnect, then observed Gemian
return with a changed boot ID. The recovered `console-ramoops` has SHA-256
`f6e568e7ec4f5b8d3133bb8883664953fa04e587fa79a5b399c86d9494b31688`
and contains the exact O marker stream.

The live topology mapped logical CPUs 1–7 to `cpu@1`, `cpu@2`, `cpu@3`,
`cpu@100`, `cpu@101`, `cpu@102`, and `cpu@103`, all
`arm,cortex-a53`; CPUs 8–9 mapped to the deferred `cpu@200` and `cpu@201`
`arm,cortex-a72` nodes. Each single CPU1–7 online request returned success with
no write error. For every core, the retained record contains its GICv3
redistributor initialization, MPIDR boot line with MIDR `0x410fd034`, two
advancing `/proc/stat` samples, the expected cumulative online mask, and
`checkpoint=PASS`. It then emitted:

```text
GEMINI_A53_SWEEP_20260718_O sweep_result=online-0-7 SUCCESS cpu8=offline cpu9=offline
```

The mask remained `0-7` through the last retained 10-second wait marker. The
log ends in the expected interval before the unserviced 31-second watchdog
expiry; the changed-cycle Gemian boot reports `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`. This
completes the recovery-backed oracle without relying on display text.

This is one hotplug run with forced `maxcpus=1`, not proof of repeatability,
boot-time SMP, stress or coherency, DVFS, idle, thermal behavior, or either
Cortex-A72 `CPU_ON` path. Unchanged O repetition is closed. Candidate P may now
change only the kernel configuration and forced command line needed for
landscape fbcon rotation while retaining O's exact tested hardware baseline.
The complete sanitized record is the
[Candidate O runtime result](results/runtime-candidate-o-attempt-1-20260718.txt).

## Build and validation

Run in the existing AArch64 Linux development VM from a clean repository:

```sh
DEV_VM_NAME=gemini-pda-build-recovery-20260717 ./scripts/dev-vm run \
  /mnt/gemini-pda-mainline/experiments/2026-07-18-cortex-a53-sweep-diagnostic/scripts/build-cortex-a53-sweep-candidate.sh \
  --baseline /home/julien.guest/artifacts/boot-candidates/candidate-N-cpu1-online-7cdb4b99
```

The builder rejects any unpinned baseline, unexpected baseline file, dirty
repository, nonzero source epoch, non-AArch64 guest, unexpected kernel/DT/config
foundation, noncanonical initramfs, or boot-container delta outside the
initramfs. Build twice into different directories and require a recursive
byte-for-byte comparison before selecting the artifact for a device test.

Pinned Candidate O payload values are:

- tracked `/init` SHA-256:
  `0393b9fba88bf7dc8d1ba5217f7a422066ca4f427130f3fed5eb6e064aed8d52`
- initramfs SHA-256:
  `3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8`
- boot image SHA-256:
  `4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146`
- boot image size: `6526976` bytes

These are build facts, not hardware results.

The exact two-build comparison and validated host export are recorded in the
[final build reproduction](results/final-build-reproduction-20260718.txt).
The standing-authorized logical-`boot2` operation is recorded separately in the
[full write/readback result](results/boot2-write-candidate-o-20260718.txt).

## Scope and safety

Candidate O contains no storage, framebuffer, raw-memory, I2C, network, shell,
generic reset, or power-management action in `/init`. Its only sysfs writes are
the seven standard CPU online controls. The build scripts have no device or
flashing interface.

Installing the validated artifact is a separate operation governed by
`docs/SAFETY.md` and `AGENTS.md`: resolve logical `boot2` from the live GPT,
verify it is inactive and unmounted, preserve its full backup, pad to the exact
partition size, write and flush, then require a matching full-partition
readback checksum. Never substitute `boot`, `boot3`, or a remembered partition
number. Do not reboot automatically.

Console rotation, keyboard support, an interactive initramfs shell, eMMC
diagnostic storage, and USB gadget Ethernet are deliberately not mixed into O.
They are staged in `docs/ROADMAP.md` so each changes one attributable layer and
keeps O available as the runtime baseline.
