# Experiment: boot the proven Cortex-A53 set with SMP

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-21-smp8-boot-diagnostic` |
| Status | `passed` |
| Subsystem | ARM64 SMP, PSCI, GICv3, architectural timer |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-21 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Will replacing only Candidate AC's forced `maxcpus=1` token with
`maxcpus=8` bring all eight already hardware-proven Cortex-A53 CPUs online
during Linux SMP initialization while preserving AC's working USB shell,
local console, keyboard, and kernel-native reboot?

Candidate AD deliberately does not request CPU8 or CPU9. Those are the two
Cortex-A72 CPUs. Independent bsg100 Linux 6.6 evidence records a non-returning
CPU8 `CPU_ON`, while this unit has run only CPU0--7 concurrently. An uncapped
boot could therefore hang before initramfs, USB, the watchdog driver, or
ramoops becomes usable. CPU8 and CPU9 require separate watchdog-backed hotplug
experiments before an uncapped boot.

## Provenance and environment

- Kernel: pinned Linux `7.1.3`; exact 88-patch series through patch 0087.
- Parent kernel profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot`.
- Candidate profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8`.
- Configuration-input SHA-256:
  `37223bd4a7e2e3ed0852b9dfe3ea4f5e4268b4e7db69d9cf40eafabf75441a67`.
- Resolved configuration SHA-256:
  `32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`.
- Candidate AD `Image.gz` SHA-256:
  `1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b`.
- Sole requested resolved-config delta: `maxcpus=1` to `maxcpus=8` in
  `CONFIG_CMDLINE`; `CONFIG_CMDLINE_FORCE=y` remains exact.
- Container parent: exact hardware-passed Candidate AC
  `candidate-AC-usb-gadget-ethernet-final-3491c119`.
- AC boot SHA-256: `3491c119d19b7b0af2ac2342659648227182ead0e32bb4c39a66fa22cadfb39d`.
- AC padded boot2 SHA-256:
  `318f418a5e67042ecdd1c98a8767c104c8cfc68c3d56cd7c0d13cb3c5fad8a84`.
- Exact inherited AC initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
- Exact inherited final DTB SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`.
- Final Candidate AD boot SHA-256:
  `a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b`.
- Final Candidate AD zero-padded boot2 SHA-256:
  `371fda65cf9c21406d6b08e52ffb46690426a7d356ba67aa9ffe1410e7d1e495`.
- Build VM: `gemini-pda-build-recovery-20260717`, Linux AArch64.
- Boot path: Android boot image v0 through retained Planet LK, manually
  selected logical `boot2`.

The inherited AC initramfs contains a historical
`cpu_policy=maxcpus-1` text record. It remains byte-exact so the experiment has
one boot-critical variable. That string is lineage metadata and is not an AD
oracle. Only the installed full-partition hash, exact live `/proc/cmdline`,
and live CPU masks attribute and decide this experiment.

## Safety assessment

The storage-disabled kernel, DTB, initramfs, USB network, keymap, console, and
reboot implementation remain exact AC. CPU frequency scaling, CPU idle, and
thermal support are disabled, so AD is an attended, idle, bounded test. Stop
on unexpected heat, power or charging behavior, an automatic reset, a fault
log, loss of USB, or any CPU mask other than the exact expected masks.

Installation started only after native reboot returned from AC to known-good
Gemian. The guarded installer resolved logical `boot2` from the live GPT,
proved it inactive and unmounted, required exact padded AC as predecessor,
preserved a mode-0600 full backup, wrote only `boot2`, flushed, and verified the
full-partition readback. It did not select a slot or reboot.

## Associated code

- `configs/gemini-smp8.fragment`: final-wins command-line override.
- `kernel/manifest.json`: isolated Candidate AD profile.
- `scripts/validate-package-delta.py`: exact one-line configuration,
  provenance, DTB-lineage, package-integrity, and two-build reproduction gates.
- `scripts/build-candidate-ad.sh`: deterministic Android-v0 assembly using the
  new kernel and byte-exact AC runtime payloads.
- `scripts/validate-boot.py`: canonical container and AC-lineage validation.
- `scripts/collect-runtime.sh`: bounded read-only validation over AC's direct
  USB `nc` service.

## Procedure

1. Build the isolated kernel profile twice in independent guest build roots.
   Validate each package and require all files other than generated timestamps
   to reproduce.
2. Require the resolved configuration to differ from exact Candidate AB in
   exactly one line and token: `maxcpus=1` becomes `maxcpus=8`.
3. Assemble Candidate AD independently from both reproduced packages. Require
   byte-identical boot images, exact AC initramfs/final-DTB/keymap/helper bytes,
   canonical Android-v0 headers, and all 32 LK analyzer gates.
4. Return from active AC to known-good Gemian. Run the calibrated guarded
   installer against exact logical `boot2`; do not reboot automatically.
5. Manually select `boot2`, wait no more than 90 seconds for USB, then collect
   the ordered runtime gates below. Keep the unit idle and physically attended.
6. After at least 45 seconds of stable idle, test local keyboard/console and
   issue bare `reboot` through the direct USB shell with owner authorization.
   Confirm a changed known-good boot ID and collect pstore without deleting it.

Runtime success requires all of the following:

- `/proc/cmdline` contains `maxcpus=8` exactly once, no `maxcpus=1`, and is
  otherwise exact AC policy.
- `possible=0-9`, `present=0-9`, `online=0-7`, `offline=8-9`, and `nproc=8`.
- CPU1--7 booted as the expected Cortex-A53 MPIDRs; CPU8/9 did not boot.
- two `/proc/stat` samples five seconds apart contain CPU0--7, and each CPU's
  accounting advances; no CPU8/9 accounting line appears.
- no PSCI error, failed CPU, Oops, BUG, SError, RCU stall, or hung task.
- USB ping, shell, reconnect, local console, keymap, 45-second idle, and native
  reboot all work.

## Observations

Two independent builds used separate guest build roots. Both generic package
validators passed. The AD validator found exactly one resolved-configuration
line difference from Candidate AB: the forced command line changes only
`maxcpus=1` to `maxcpus=8`. Both builds produced byte-identical `Image`,
`Image.gz`, `System.map`, configuration, all 119 MediaTek DTBs, patch and
fragment provenance, and identical modes. After removing only
`generated_utc`, their build provenance is identical. See the
[kernel result](results/kernel-reproduction-ad-20260721.txt).

Independent container assembly from each reproduced package produced the same
16-file tree with identical bytes and modes. Raw boot SHA-256 is
`a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b`
at 7,378,944 bytes. The new kernel is paired with exact AC initramfs and final
DTB bytes; the Android-v0 validator and all 32 LK analyzer gates passed. See
the [container result](results/container-validation-ad-20260721.txt).

The guarded installer was deterministically derived twice from exact AC inner
installer SHA-256
`b1a71fc2bb6d2e3b374b16dcfdeec4ec334acf7596556c7d9631930997664dd7`.
It pins raw AD, padded AD, and exact padded AC predecessor identities, retains
one bounded 16 MiB target write and all inherited live-GPT and readback gates,
contains no reboot or slot selection, passes `bash -n` and ShellCheck, and has
SHA-256
`41f8a20b04f0bed34ce7b3a77662ee31ecae778b2372afb5275c436914d944c3`.
Its only foundation-contract extension samples both Gemian `ac/online` and
`usb/online`, requires two identical samples at each gate, at least one online
external source, and the same present, `Full`, 100%, `Good` battery state.
See the [installer result](results/installer-validation-ad-20260721.txt).

The first install invocation retained the inherited AC-only power predicate and
stopped before device backup or write because Gemian reported AC offline. A
separate read proved USB online. After the explicit power-contract extension,
all probe, immediate pre-write, and post-write samples were exact
`0|1|1|Full|100|Good` in the documented
AC/USB/battery-present/status/capacity/health order. Live GPT resolved `boot2`
as `/dev/mmcblk0p30` while root was `/dev/mmcblk0p29`. The complete backup
matched exact padded AC SHA-256
`318f418a5e67042ecdd1c98a8767c104c8cfc68c3d56cd7c0d13cb3c5fad8a84`;
the post-flush remote checksum and full 16 MiB byte-for-byte readback matched
exact padded AD SHA-256
`371fda65cf9c21406d6b08e52ffb46690426a7d356ba67aa9ffe1410e7d1e495`.
No reboot or slot selection occurred. See the
[write result](results/boot2-write-candidate-ad-20260721.txt).

The owner then selected `boot2` and reported a successful boot with eight CPUs
visible manually. The exact installed hash and live forced command line
attribute the run to AD. USB collection found `possible=present=0-9`,
`online=0-7`, `offline=8-9`, and `nproc=8`. CPU1--7 booted with the expected
Cortex-A53 MIDRs and MPIDRs, every CPU0--7 accounting sum advanced over a
five-second sample, all expected GICv3 redistributor lines are present, and
CPU8/9 did not boot. The bounded fault scan found no panic, Oops, BUG, SError,
RCU stall, hung task, CPU boot failure, or PSCI failure. A fresh USB shell
connection succeeded at 363.20 seconds uptime with the masks unchanged,
proving service respawn and more than the required 45 seconds without an
automatic reset. See the
[runtime result](results/runtime-candidate-ad-attempt-1-20260721.txt).

The untouched raw capture initially exposed two validator defects rather than
runtime failures: the known USB shell prompt prefixed one-line identity output,
and case-insensitive `SError` matched the benign `fserror_init` initcall. The
validator now strips only the exact known prompt prefix and requires word
boundaries around `SError`; exact CPU-mask and injected real-SError mutations
still fail. The owner separately confirmed that the local console and keyboard
remained usable and manually observed eight CPUs.

After 1,140 seconds of stable uptime, an authorized bare `reboot` was issued
through the direct USB shell. The shell reached Candidate AB's retained forced
BusyBox reboot wrapper, USB disconnected, and known-good Gemian returned with
changed boot ID `385cc5d1-c6a8-48f7-8f75-fcc7a00d4346`. The private pstore
copy records the request at 1140.407944 seconds, an orderly shutdown, and
`reboot: Restarting system` at 1140.433403 seconds: 25.459 ms from request to
the final kernel restart line. Its `console-ramoops` SHA-256 is
`55b4e6c22ff6de305c92b1ac7c5a5cf58ba4bdec763a5f98f4023133c1cbe45f`.
No remote pstore record was removed. The complete runtime and native-reboot
evidence is in the
[runtime result](results/runtime-candidate-ad-attempt-1-20260721.txt).

## Analysis

The build and container observations support a clean one-variable experiment:
the boot-critical payload differs from AC only in the rebuilt kernel carrying
the exact `maxcpus=8` forced command line. The runtime observations establish
one normal-boot pass for the complete already-proven Cortex-A53 set, not merely
compile-time SMP support. The stale inherited AC `cpu_policy=maxcpus-1` record
remains explicitly excluded from interpretation. This run does not validate
the two Cortex-A72 CPUs, repeatability, load, DVFS, thermal management, or
suspend.

## Conclusion

`passed` once for boot-time Cortex-A53 SMP on the named unit: exact Candidate AD
booted CPUs 0--7, kept CPU8/9 offline, showed advancing per-CPU accounting, and
remained reachable past six minutes without a fault signature or automatic
reset. The local console and keyboard remained usable, and an authorized bare
reboot completed through the native restart path and returned to changed-boot-ID
Gemian with an orderly pstore record.

## Follow-up

Test CPU8 alone through standard hotplug behind the proven 31-second watchdog
and pstore boundary, then CPU9 separately. Remove the cap only after both
Cortex-A72 paths pass. Keep scheduler topology and capacity policy out of those
CPU_ON experiments so each result remains attributable.
