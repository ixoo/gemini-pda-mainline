# Experiment: split the AF kernel from the regressed AE/AF board DT

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-ad-contract-af-kernel-split` |
| Status | `built, reproduced, checksum-verified on boot2; attempt 1 inconclusive; exact attempt 2 runtime, console, and native-reboot PASS` |
| Subsystem | ARM64 SMP, LK-to-Linux board handoff, USB gadget, keyboard, MT6797 A72 safety gate |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 |
| Investigator(s) | Project maintainers |
| Candidate | `AH` |

## Question or hypothesis

Will Candidate AF's exact kernel, resolved configuration, `System.map`, and
initramfs reach the hardware-passed eight-Cortex-A53 runtime when paired with
Candidate AD's complete hardware-passed final DT contract, changing only the
two Cortex-A72 `enable-method` strings from generic `psci` to AF's rejecting
`mediatek,mt6797-psci` gate?

AG answered a narrower packaging question but was not a valid AD runtime
control. Its final DT restored AD's simple-framebuffer node while retaining
AF's raw package DT everywhere else. A whole-tree comparison now establishes
that this also left the proven AD USB gadget and keyboard paths disabled and
omitted other artifact-level board transforms. The absent USB nodes made AG's
predeclared remote pass oracle unreachable regardless of whether its kernel
continued. Its owner-confirmed grey/no-text state still does not identify a
Linux stage.

AH is the clean component split. It does not test the DA9214, I2C6, observer,
or active A72 power sequence. A pass establishes that AF's kernel/config
binary can retain AD's working console, USB, keyboard, pstore, eight A53s, and
native reboot while its new resource consumers remain absent. A failure with
an attributable AH kernel record moves the investigation into the AF kernel
delta; another grey state without an AH record requires an observation point
earlier than normal ramoops rather than another display derivative.

## Provenance and environment

- Kernel release: pinned Linux `7.1.3`.
- Exact AF `Image.gz` SHA-256:
  `b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912`.
- Exact AF resolved configuration SHA-256:
  `bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63`.
- Exact AF `System.map` SHA-256:
  `a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d`.
- Exact AF normalized source-build SHA-256:
  `57ea75dd81ac7389c6a34d47cf9dc6a7300476f7ad85b00d782190585e686094`.
- Exact AD final DTB SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`.
- Exact AD initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
- Exact AD keymap SHA-256:
  `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
- Exact AD helper SHA-256:
  `b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602`.
- AF profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist`.
- Forced AF policy retains `maxcpus=8`, `clk_ignore_unused`,
  `regulator_ignore_unused`, and
  `initcall_blacklist=mt6797_a72_power_driver_init`.
- Build and validation environment: repository recovery VM
  `gemini-pda-build-recovery-20260717`; generated artifacts remain in the VM
  until explicitly exported.
- Boot path for a later validated candidate: Android boot image v0 through
  retained LK, manually selected logical `boot2`.

Candidate AH's final DT must be semantically identical to the exact AD DT
above except:

```text
/cpus/cpu@200/enable-method: psci -> mediatek,mt6797-psci
/cpus/cpu@201/enable-method: psci -> mediatek,mt6797-psci
```

Phandle renumbering, node reordering as a semantic substitute, added
properties, and any other property/value change are invalid. In particular,
AH must retain AD's complete simplefb, USB, keyboard, ramoops, SCP, reserved
memory, and loader-handoff contracts; it must contain no A72-power node,
enabled I2C6/DA9214 client, or static copy of LK's dynamic framebuffer
reservation.

## Safety assessment

The artifact split adds no kernel patch, configuration fragment, manifest
profile, raw framebuffer write, storage access, watchdog owner, automatic
reboot, regulator operation, reset request, SMC, or CPU-online request. The
exact AF command line keeps `maxcpus=8`, so normal SMP initializes only the
already-passed Cortex-A53 CPUs 0--7. Both offline Cortex-A72 nodes select the
AF kernel's method that returns `-EAGAIN` before generic PSCI `CPU_ON`; AH's
runtime collection does not exercise even that rejecting path.

The AF kernel does retain patch 0090's MT6797 TOPRGU reset-controller
registration at watchdog probe. Exact AD DT supplies no reset-controller
consumer or A72-power node, so no new reset is requested, but AH is not a
mathematically 0092-only kernel. If AH fails with attributable kernel evidence,
the retained kernel-side 0088--0092 delta, including 0090 registration, must be
split in a newly pinned build rather than hidden by another artifact change.

Build and validation are file-only. A future install is a separate guarded
operation under the standing logical-`boot2` authorization. It must resolve
the live GPT label, prove the target inactive and unmounted, preserve a private
mode-0600 full backup, require exact AG as predecessor, pad AH to the exact
target size, perform one bounded write, sync and flush, and require matching
full-partition readback. The installer must not select a slot or reboot.

Before a boot, arm the exact-MAC USB watcher and independent wait-for-cycle
pstore collector. The runtime collector is read-only and requires one boot ID
to survive the 45+5-second interval. Stop on an unexpected reset, heat, power
change, CPU mask, fault, or missing identity. Do not repeat an identical AH
artifact unless a new measurement can change the decision.

## Associated code

- `scripts/validate-lineage.py`: exact AF, AG, and AD inventory, mode,
  manifest, payload, command-line, and symbol lineage.
- `scripts/build-ah-dtb.sh`: deterministic exact-AD two-property DT transform.
- `scripts/validate-dtb-delta.py`: whole-FDT semantic, header, reservation-map,
  boot-CPU, phandle, and board-contract allowlist.
- `scripts/test-dtb-validator.py`: positive fixture plus 22 focused DT
  mutations.
- `scripts/build-candidate-ah.sh`: two-pass DT and Android-v0 construction in
  the AArch64 recovery VM.
- `scripts/validate-boot.py`: exact component, canonical Android-v0, address,
  padding, header-ID, and capacity validation.
- `scripts/test-boot-validator.py`: positive fixture plus 12 coherent payload,
  DT, and Android-header mutations.
- `scripts/validate-artifact-reproduction.py`: byte-and-mode comparison for
  two independently constructed 18-member artifacts.
- `scripts/collect-runtime.sh` and `scripts/validate-runtime.py`: bounded,
  read-only exact-USB collection and the 45+5-second runtime oracle.
- `scripts/collect-cycle.sh`: once-only exact-MAC watcher; it never invokes the
  collector if the exact interface is absent or ambiguous.
- `scripts/test-runtime-validator.py` and
  `scripts/test-collect-cycle-no-interface.sh`: synthetic runtime mutation and
  watcher failure/signal tests.
- `scripts/derive-installer.py` and `scripts/test-installer-derivation.py`:
  fail-closed exact-AG-to-AH guarded-installer derivation and storage-safety
  tests; calibration and validation must complete before use.

No script in this experiment may contact a device except an explicitly named
runtime collector or a separately derived guarded installer. No installer is
part of the initial scaffold.

## Procedure

1. Validate the exact AF and AD artifact roots and every pinned file identity.
2. Derive the AH DT twice from exact AD, changing only the two A72 enable
   methods. Require a whole-FDT semantic validator to accept that transform and
   reject focused path, value, phandle, USB, keyboard, simplefb, ramoops,
   reservation, observer, and extra-property mutations.
3. Assemble Android-v0 twice from exact AF `Image.gz`, exact AD initramfs, and
   the reproduced AH DT. Require canonical header, address, alignment,
   component, command-line, capacity, and trailing-data validation.
4. Require both complete artifact trees to be byte- and mode-identical. Record
   raw and exact-16-MiB padded hashes before deriving any installer.
5. Validate the bounded runtime fixture and all focused negative mutations.
   Derive and test a source-pinned guarded installer only after every artifact
   identity is final.
6. Before the single device cycle, state the exact installed full-partition
   hash and arm both observation paths. Manually select `boot2`; do not request
   CPU8/9 online or touch regulator, reset, watchdog, memory, or storage
   interfaces.
7. A runtime pass requires the exact AH USB identity, exact installed-hash
   attestation, one boot ID past 45+5 seconds, exact AF command line and
   blacklist, exact live AH/AD board contract, advancing CPU0--7 accounting,
   offline CPU8/9 with both rejecting methods, absent observer/I2C6/DA9214
   consumers, and no fault, CPU request, or watchdog owner.
8. Preserve evidence before issuing the already-proven native `reboot`. A
   rejecting CPU8 sysfs-gate exercise, DA9214/I2C6 introduction, and active A72
   sequence are separate later state-changing steps, not hidden inside AH.

The predeclared decision oracle is:

| Result | Decision |
| --- | --- |
| Exact AH passes every 45+5-second runtime gate and native reboot | `PASS`: AF's kernel/config is viable with the full AD board contract. Introduce the AE/AF DT resource path in separately attributable, fail-closed steps. |
| Exact AH reaches ramoops or USB but faults, stalls, changes CPU masks, or resets | `FAIL`: split the AF kernel/config delta, including retained patch 0090 behavior; do not add DA9214, observer, or active A72 work. |
| The intended DT, command line, installed hash, or component identities are not exact | `INVALID`: correct artifact lineage; do not interpret hardware behavior. |
| Owner-selected AH again yields grey/no text and no exact kernel, pstore, or USB identity | `INCONCLUSIVE`: stop normal-console derivatives and add an earlier independent observer, preferably external LK UART or a separately validated reserved-DRAM stage ledger. |

## Observations

The owner-confirmed AG cycle produced a grey screen with no text and no exact
USB identity before an owner-forced return. A post-return full read confirms
that logical `boot2` still contains exact padded AG SHA-256
`63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14`.
The known-good Gemian root remains separate.

A subsequent whole-FDT audit established the broader board-contract split
summarized above. In exact AD, the T-PHY, USB PHY child, MTU3 wrapper, keyboard
I2C parent, AW9523, and matrix keypad are enabled. In exact AG all those paths
are disabled; AG contains only the separately restored simplefb part of AD's
artifact-level transform. AD also retains an SCP node, per-CPU clock-frequency
properties, and firmware-reservation compatibles that AG's raw-package lineage
omits. See the [AD/AG DT audit](results/ad-ag-dtb-lineage-audit-20260722.txt).

Two independent AArch64 recovery-VM constructions produced byte- and
mode-identical 18-member AH artifacts. The exact DT transform is SHA-256
`27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845`.
The 7,385,088-byte raw Android-v0 image is
`e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197`;
its exact 16 MiB zero-padded identity is
`f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`.
Both manifests are SHA-256
`04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997`
and verify after export. The whole-FDT fixture passed and all 22 focused
mutations failed; the Android-v0 fixture passed and all 12 coherent payload,
DT, and header mutations failed. See the
[build reproduction record](results/build-reproduction-ah-20260722.txt).

The calibrated installer was derived at SHA-256
`01768f0decaf621eebfcfbbf02eba64d15f3595207a1ce3c8ea1918f17656c91`
and mode 0700. It passed 64 inherited AF, 42 inherited AG, and 58 AH-specific
storage, identity, calibration, and publication mutations plus recovery-VM
ShellCheck. See the
[installer validation record](results/installer-validation-ah-20260722.txt).

The guarded install then resolved live-GPT logical `boot2` as inactive,
unmounted `/dev/mmcblk0p30` while known-good Gemian remained rooted on
`/dev/mmcblk0p29`. USB external power was online and the battery was present,
full, healthy, and 100%. The private full backup matched exact installed AG;
one bounded write was synced and flushed; the remote post-flush checksum and
complete 16 MiB local readback both matched exact padded AH
`f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`.
Remote staging was removed. The installer did not reboot or select a slot. See
the [boot2 write record](results/boot2-write-candidate-ah-20260722.txt).

One requested cycle followed with the exact AH image still verified on
`boot2`, but it did not cross an attributable candidate stage. The known-good
SSH connection disconnected at 15:01:50Z and returned on a changed Gemian boot
ID at 15:02:14Z, only 24 seconds later. The exact AH USB MAC never appeared,
the USB collector therefore ran zero times, and the investigator stopped the
watcher with Ctrl-C after the known-good return. Its preserved `status.env`
correctly records exit 130, phase `waiting-for-exact-mac`, zero collector
invocations, and `received-signal-INT`.

The changed-cycle pstore contains the preceding orderly Gemian shutdown, but no
AH identity, Linux 7.1.3 identity, initramfs marker, panic, fault, or watchdog
pretimeout. A post-cycle full read still matches exact padded AH on `boot2`.
The owner subsequently confirmed selecting `boot2`, observing a grey console
screen with no text, and forcing the return; no automatic candidate reboot was
observed. The grey scanout confirms the attended visual state after the LK
selection, but without an AH USB or pstore identity it still does not establish
kernel entry or initramfs execution. See the
[attempt-1 runtime record](results/runtime-candidate-ah-attempt-1-20260722.txt).

On a later owner-selected boot of the unchanged, exact AH image, the console
worked and the direct USB service became reachable. The exact runtime
validator passed at boot ID `a1329a48-084c-4d03-bf59-7dd39b81f6dc` and a final
uptime sample of 1,728 seconds. It confirmed the exact AF kernel configuration
and command line, exact live AD initramfs payload and board contract, one exact
USB shell session, the bound AW9523 matrix/keymap path, absent observer,
disabled and absent I2C6 platform device, absent DA9214 client and regulators,
possible/present CPUs 0--9, online CPUs 0--7, offline CPUs 8--9, advancing
CPU0--7 accounting, exact rejecting CPU8/9 enable methods, and no CPU8/9
request or rejection, userspace watchdog owner, automatic reboot through the
observation boundary, or fault signature. The owner did not separately
exercise or report physical key events during this attempt, so the live
driver/keymap validation is not a physical-keyboard claim.

After preserving an empty pre-reboot pstore inventory, one fresh boot-ID-gated
bare `reboot` request was sent over the direct USB shell. Retained pstore from
the resulting cycle contains the request at 1852.023901 seconds, watchdog
shutdown at 1852.040732 seconds, and `reboot: Restarting system` at 1852.050174
seconds. The 26.273 ms interval is retained-log timing from the request marker
to the final restart line, not an input-to-reset latency measurement. Gemian
returned as AArch64 kernel `3.18.41+`, root `/dev/mmcblk0p29`, under changed
boot ID `4dfa7e87-d7c7-416f-8c32-7271662d89bd`. A read-only live-GPT check
resolved unmounted logical `boot2` as `/dev/mmcblk0p30`, whose full hash still
matched exact padded AH
`f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`.
See the
[attempt-2 runtime record](results/runtime-candidate-ah-attempt-2-20260722.txt).

## Analysis

The component split is preferable to a raw framebuffer beacon. Grey scanout
already depends on LK state and display clocks, and absence of new pixels would
remain ambiguous. AH instead restores every proven AD observation dependency
and has an outcome that changes the next patch/DT branch. Ramoops remains the
earliest proven durable mainline observer on this unit, but it registers only
after early kernel execution; absence of an AH record cannot prove LK rejected
the image or that Linux never entered.

The complete-AD-DT comparison also corrects AG's overly narrow premise. AG's
simplefb restoration was exact, but simplefb alone could not make its disabled
USB and keyboard nodes satisfy the remote/runtime oracle. That is a packaging
failure, not evidence about A72 power sequencing.

Attempt 1 establishes an owner-selected `boot2` cycle, a grey/no-text visual
state, an owner-forced return, and that exact AH remained stored on `boot2`.
It does not establish that LK entered AH or that Linux reached any attributable
stage. The 24-second interval and ambiguous known-good watchdog-class
boot-reason token cannot substitute for an AH identity. It did not justify a
planned unchanged retry.

The later owner-selected boot did add the decision-changing observation that
attempt 1 lacked: exact AH was reachable through the USB service, survived the
predeclared runtime boundary with its full live contract, and left an exact
retained reboot record. This does not retroactively turn attempt 1 into a pass;
it is independent attributable evidence for attempt 2. The bare command was
routed through the inherited absolute BusyBox wrapper and then the native
kernel restart path. No userspace watchdog, automatic watchdog reboot, or
countdown owned the observed cycle.

## Conclusion

`PASS for the predeclared AH baseline on the current named unit`: attempt 2
established the exact AF kernel/config with the full AD board contract, a
working owner-observed console, exact USB runtime past the observation
boundary, CPUs 0--7 online and advancing, CPU8/9 still offline and unrequested,
and one orderly native reboot back to Gemian. Attempt 1 remains inconclusive.
This result does not establish physical keyboard events in attempt 2 or any
Cortex-A72 power/online support.

## Follow-up

AH has passed. Validate the corrected 0092-only fail-closed kernel as a
separately attributable baseline before any active CPU8 request. A later
candidate may make one bounded CPU8 rejecting request; the I2C6/DA9214
description, observer resources, and any active regulator/reset/SPM/SMC/DCM
sequence remain separate candidates with independent rollback, isolation,
watchdog, thermal, and scheduling gates.
