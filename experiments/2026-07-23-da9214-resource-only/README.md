# Experiment: add only the Gemini I2C6/DA9214 resource path

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-23-da9214-resource-only` |
| Status | `attempt 1 FAIL; root cause isolated: legacy DA9214 has no normal I2C DEVICE_ID 0x201` |
| Subsystem | MT6797 I2C6, DA9214 regulator registration, Cortex-A72 prerequisite isolation |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-23 |
| Investigator(s) | Project maintainers |
| Candidate | `AL` |

## Question or hypothesis

Can the exact hardware-passed Candidate AH kernel, configuration, userspace,
console, USB, keyboard, pstore, eight-Cortex-A53, and reboot payload survive
when the **only final-DT semantic delta** is patch 0089's I2C6/DA9214
description?

Candidate AL is deliberately resource-only. It must register the MT6797 I2C6
controller, one `dlg,da9214` client at address `0x68`, and both upstream
DA9211-family regulator children without requesting CPU8 or CPU9 and without
registering the MT6797 A72 observer. The first active CPU8 candidate is renamed
Candidate AM.

This label replaces the earlier working-plan use of “AL” for an active A72
sequence. That earlier sequence remains on hold pending the exact Gemian
owner-local transaction capture and will not be hidden in this experiment.

## Provenance and environment

- Kernel release: exact Candidate AH Linux `7.1.3`.
- Exact AH raw Android-v0 image SHA-256:
  `e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197`.
- Exact AH `Image.gz` SHA-256:
  `b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912`.
- Exact AH `System.map` SHA-256:
  `a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d`.
- Exact AH resolved configuration SHA-256:
  `bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63`.
- Exact AH initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
- Exact AH final DT SHA-256:
  `27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845`.
- Exact 0089 evidence patch SHA-256:
  `5626670d4d4b39e8b8e9b1e803bcb9a847068690046531a7132a4dda6936248b`.
- Two independent AL trees reproduce byte-for-byte and mode-for-mode. Exact
  raw Android-v0 SHA-256:
  `a19877ad5f2c5a8515b6f3b64aec9b5bf036820ef35452e3e7009803fa3848da`;
  raw size: `7,387,136` bytes.
- Exact AL final-DT SHA-256:
  `ea80e7a835fee94c7eb985165aaca7d074ab99f0878f9f07f2ef67b0954afea1`.
- Exact AL artifact-manifest SHA-256:
  `591bc166f1992b5b1152ba87703b61ca5b8cb3f35b5f087af12c27cb47a5e5ba`.
- Exact 16 MiB padded AL SHA-256:
  `5f022a8b4d6ed19a248d21b8cebdbfa2190e86675714eab49adfc57de9a7f794`.
- Exact pre-install Candidate AK padded SHA-256, used **only** as the guarded
  installer predecessor:
  `66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e`.
- Build and validation environment: repository AArch64 recovery VM
  `gemini-pda-build-recovery-20260717`. Generated artifacts stay outside Git.
- Boot path: Android boot image v0 through retained LK, manually selected
  logical `boot2`.

AL keeps AH's `maxcpus=8`, `regulator_ignore_unused`, and exact
`initcall_blacklist=mt6797_a72_power_driver_init` command line. Patches 0090
and 0091 remain compiled into the byte-exact AH kernel, but 0090 has no AL
consumer and 0091's initcall remains blacklisted. The AL final DT contains no
`a72-power` node. CPU8 and CPU9 retain the rejecting
`mediatek,mt6797-psci` method and are neither boot-time nor runtime requested.

The exact final-DT allowlist is:

```text
/pinctrl@10005000/i2c6-pins/phandle = 0x2c
/i2c@1100e000/status = "okay"
/i2c@1100e000/clock-frequency = 3400000
/i2c@1100e000/mediatek,use-push-pull
/i2c@1100e000/pinctrl-names = "default"
/i2c@1100e000/pinctrl-0 = <0x2c>
/i2c@1100e000/regulator@68/compatible = "dlg,da9214"
/i2c@1100e000/regulator@68/reg = <0x68>
/i2c@1100e000/regulator@68/regulators/BUCKA/regulator-name = "da9214-bucka"
/i2c@1100e000/regulator@68/regulators/BUCKB/regulator-name = "vproc-big"
```

The new phandle is the first unused value after exact AH's contiguous
`0x01`--`0x2b` map. Keeping all existing AH phandles fixed makes the binary-DT
derivation attributable and avoids recompiling or substituting a raw package
DT.

## Safety assessment

The build and validation phase is file-only. It performs no device, VM-host
storage, watchdog, CPU-online, regulator, reset, SMC, or reboot operation.

The runtime candidate does not add a regulator consumer and does not call
enable, disable, or set-voltage. Normal DA9211 probe is not side-effect-free:
its paged regmap can write the page-selector register, and normal platform
initialization can change controller/clock state. Those inherited probe effects
are the exact experimental variable. `regulator_ignore_unused` prevents the
regulator core from disabling the newly registered rails as unused.

The runtime collector reads regulator class `state` and `microvolts` through
the driver/regmap-serialized sysfs path. Those values may be satisfied from
regcache. They are **not a physical voltage measurement**, not an independent
DA9214 readback, and not evidence that either output is electrically enabled.
“Read-only collector” describes its userspace/kernel API: a paged-regmap read
may still update the chip's page-selector register on the physical bus.
The oracle therefore requires only readable, stable, driver-valid values:
`enabled` or `disabled`, and 300000--1570000 microvolts on the 10000-uV grid.
It records `physical_readback_claim=none`.

Exact AH has no `i2cN` aliases. Enabling a second controller can therefore
renumber both Linux I2C adapters. The runtime oracle never assumes that I2C6 is
adapter 6 or that the inherited AW9523 remains on adapter 0: it correlates
I2C6 and its `0x68` client through their live `of_node` links, and requires the
inherited AW9523 marker to match its separately observed live client identity.

A later install is allowed only after two independent AL assemblies reproduce
all bytes and modes and the raw, manifest, DT, and exact-16-MiB padded hashes
are source-pinned. The derived installer must:

- reconstruct the exact validated AK installer foundation;
- require exact AK as the live full-partition predecessor;
- resolve logical `boot2` from the live GPT;
- prove it is inactive, unmounted, writable, exactly 16 MiB, and not in use;
- require stable external power and a present/full/healthy 100% battery;
- preserve a private mode-0600 full backup and checksum;
- write once, sync and flush, and require matching full remote and local
  readback hashes;
- never select a slot and never reboot.

Before the one AL boot, arm the exact-MAC USB collector and the independent
wait-for-cycle pstore collector. Stop on any fault, I2C transfer error,
unexpected reset, CPU8/9 request, CPU-mask change, regulator inventory change,
heat/power anomaly, or identity mismatch. Do not repeat an identical AL
artifact unless a new independent observation can change the decision.

## Associated code

- `scripts/candidate_al.py`: exact AH/AK lineage and source-pinned AL
  identities.
- `scripts/validate-lineage.py`: validates exact AH functional input and exact
  AK storage-predecessor input without merging their roles.
- `scripts/build-al-dtb.sh`: deterministic binary-DT implementation of the
  exact 0089 semantic delta.
- `scripts/validate-dtb-delta.py`: whole-tree semantic, FDT header,
  reservation-map, boot-CPU, phandle, board-contract, and forbidden-node
  validator against exact AH.
- `scripts/build-candidate-al.sh`: two-pass DT and Android-v0 assembly using
  byte-exact AH payload members.
- `scripts/validate-boot.py`: exact component, canonical Android-v0 header,
  address, padding, capacity, command-line marker, and final-DT validation.
- `scripts/validate-artifact-reproduction.py`: two-independent-tree byte/mode
  reproduction and raw/DT/manifest/padded calibration.
- `scripts/derive-installer.py`: fail-closed exact-AK installer derivation. It
  cannot publish while any AL calibration placeholder remains.
- `scripts/collect-runtime.sh` and `scripts/validate-runtime.py`: bounded,
  read-only 45+5-second exact-USB runtime capture and honest regcache-limited
  resource oracle.
- `scripts/collect-cycle.sh`: exact-MAC one-shot watcher that creates one
  private evidence directory and invokes the runtime collector once.
- `scripts/request-native-reboot.sh`: validates the AL capture, exact USB
  interface, live boot ID, and inherited reboot helper before issuing one
  native reboot. It cannot run until AL artifact pins are final.
- `scripts/test-static.py`: storage-inert syntax, identity, runtime-oracle, and
  fail-closed placeholder tests.

The serializer and LK analyzer are reused from
`2026-07-12-boot-contract-recovery`. The runtime resource inventory is derived
from Candidate AF, while the complete board/runtime contract comes from
hardware-passed AH. The guarded storage lineage is derived from AK. None of
those historical final DTs is silently substituted for AL.

## Procedure

1. In the recovery VM, validate the exact AH and AK artifact roots with
   `validate-lineage.py`.
2. Run `build-candidate-al.sh` twice into independent output parents. Each run
   derives AL from the exact AH final DT twice, requires identical results,
   assembles Android-v0 twice, and validates the complete final image.
   **Completed** in the recovery VM.
3. Run `validate-artifact-reproduction.py` over the two output trees. Record
   its raw image, raw size, final-DT, artifact-manifest, and exact-16-MiB
   padded hashes. Pin those values in `candidate_al.py`, rerun the validator,
   and run all static/ShellCheck tests. **Completed**; the host-exported trees
   were independently revalidated.
4. Derive and independently test the guarded installer. Install only while
   exact AK is the verified inactive `boot2` predecessor. Preserve the full
   backup and matching full readback; do not reboot. **Completed** on the named
   unit: exact AK was backed up, one exact 16 MiB AL write was synced/flushed,
   and remote plus local full readbacks matched. The installer did not reboot.
5. State the boot hypothesis, the exact installed padded hash, and this
   decision oracle. Arm the one-shot USB and pstore collectors before the
   owner selects `boot2`. **Completed** for attempt 1. The original exact-MAC
   watcher could not configure the host address without host authorization and
   made no device connection. Once the exact interface had configured itself,
   a fresh one-shot rearm made exactly one collector connection.
6. A pass requires one AL boot ID through 45+5 seconds; the exact AH
   kernel/config/initramfs and complete AH board contract; exact AL DT;
   I2C6 bound at the described 3.4-MHz push-pull pinctrl contract; one bound
   DA9214 client at address `0x68`, dynamically correlated to the adapter whose
   `of_node` is exact I2C6; exactly one BUCKA and one BUCKB regulator linked to
   that same client; stable, valid driver/regmap-serialized but potentially
   cached sysfs values; advancing CPU0--7;
   CPU8/9 offline and unrequested; one observer-blacklist line; no observer
   device/driver/sysfs, watchdog owner, fault, I2C error, or automatic reboot.
7. Preserve the runtime evidence. Only then use the guarded native reboot
   helper and recover pstore/post-return `boot2` integrity as separate gates.
   Do not request CPU8/9 during AL. **Completed** with a clean native restart
   and changed-identity Gemian return. The original wait-for-cycle collector
   reached its deadline after observing disconnect, so the retained pstore is
   explicitly an unpaired post-return capture.

The predeclared decision oracle is:

| Result | Decision |
| --- | --- |
| Exact AL satisfies every resource, 45+5-second stability, console/USB/keyboard, CPU, no-error, native-reboot, changed-Gemian-return, and post-return `boot2` gate | `PASS`: mainline I2C6 plus DA9214 registration is an attributable hardware-passed prerequisite. Keep the AL artifact; combine it with the separately captured Gemian transaction contract only in later Candidate AM. |
| AL reaches exact USB/pstore identity but I2C6 transfers fail, DA9214 or either descriptor fails to bind, state is unstable/invalid, or a fault/reset occurs | `FAIL`: stop. Isolate controller timing/pinctrl or DA9211 paged-regmap behavior without requesting an A72. |
| Kernel/config/initramfs/final-DT/installed hash differs, observer registers, CPU8/9 is requested, or exact AK was not the install predecessor | `INVALID`: correct lineage or policy; do not interpret hardware behavior. |
| No exact AL USB or durable kernel identity is recovered | `INCONCLUSIVE`: add an earlier independent observation path; do not repeat unchanged AL and do not proceed to AM. |

## Observations

Two independent Candidate AL assemblies reproduced all 18 files and modes.
The raw, final-DT, artifact-manifest, and padded identities above are
source-pinned, and the two private host exports passed the same independent
validator.

On the named Gemini, live GPT resolution selected logical `boot2` as
`/dev/mmcblk0p30`; active root was `/dev/mmcblk0p29`. The target was inactive,
unmounted, writable, exactly 16 MiB, and contained exact AK. USB power was
online and the battery reported full, 100%, and good. The guarded installer
preserved an exact mode-0600 full AK backup, wrote once, synced/flushed, and
required matching remote and local full-partition AL readbacks. It neither
rebooted nor selected a slot. See
[`artifact-reproduction-20260723.txt`](results/artifact-reproduction-20260723.txt),
[`installer-derivation-20260723.txt`](results/installer-derivation-20260723.txt),
and [`boot2-write-20260723.txt`](results/boot2-write-20260723.txt).

The owner manually selected `boot2`, and Candidate AL reached its exact USB
runtime identity. The 132,724-byte private capture has SHA-256
`1ec303026a8570e9948c3c30cad9bdc1de4a7b560694d2b92f58aab316869140`.
At both samples, the exact AH configuration and forced command line were
present, CPU0--7 were online with advancing accounting, CPU8/9 were offline
and unrequested, the observer was blacklisted and absent, and the inherited
keyboard, keymap, USB, framebuffer, and no-watchdog contracts remained
present.

The exact AL DT appeared at runtime. `1100e000.i2c` bound to
`i2c-mt65xx`; its dynamically assigned adapter was `0`; and exact client
`0-0068` was correlated to I2C6 through its live `of_node`. The client did not
bind. Its probe logged:

```text
da9211 0-0068: Unsupported device id = 0x0.
probe of 0-0068 returned 19 after 1444 usecs
```

Consequently neither `da9214-bucka` nor `vproc-big` registered. The focused
evidence contains no I2C timeout, NACK, panic, BUG, or automatic-reset
signature. This is a resource-oracle failure, not an A72 result and not a
physical rail measurement.

The identity-gated native reboot was requested at about 208.747 seconds; the
retained console records `reboot: Restarting system` at about 208.773 seconds
after the complete shutdown path. Gemian returned with a changed hashed boot
identity and Linux `3.18.41+`. A full read-only post-return checksum of
`boot2` still matched exact padded AL. The wait-for-cycle pstore collector had
already exhausted its deadline after seeing disconnect, so the later
checksum-clean pstore collection is deliberately labeled unpaired
post-return evidence. See
[`runtime-candidate-al-attempt-1-20260723.txt`](results/runtime-candidate-al-attempt-1-20260723.txt).

## Analysis

The I2C6 controller resource, pinctrl selection, and DT-client creation are
supported by this one attributable run. The upstream DA9211-family probe did
communicate far enough to return an ID value, but `0x0` is not an accepted
DA9211-family identity. At the end of the runtime attempt alone, that result
did not distinguish page/register protocol, timing, reset/prerequisite, or
driver-family alternatives. It did prove that requesting an A72 then would
have combined unresolved variables.

A subsequent datasheet cross-check resolves the leading alternative. The
owner-supplied document is the newer automotive `DA9213-A/DA9214-A/DA9215-A`
datasheet, not the legacy `DA9213/DA9214/DA9215` datasheet. The A-family
document exposes I2C page `10x` as `0x200`--`0x27f` and defines `DEVICE_ID` at
`0x201`. Renesas's current legacy-family document exposes only I2C page
`00x` as `0x000`--`0x0ff` and `01x` as `0x100`--`0x17f`; higher page values
are reserved for production/test, and reads of nonexistent 2-WIRE registers
return zero. Linux 7.1's DA9211-family probe unconditionally reads `0x201`.
Candidate AL's successful transfer returning `0x00` is therefore the
documented legacy behavior, not evidence of a missing I2C client.

The operational ABI still matches the existing driver. The legacy datasheet,
the pinned public Gemian driver, and two live Gemian captures agree on the
BUCKA/B controls, selectors, voltage encoding, and page-2 interface registers.
Gemian identifies the part through `0x105[7:4] == 0xd` and never reads
`0x201`; the live signature repeated as `0x105=d9`, `0x106=d0`,
`0x147=c0`. This makes a separate regulator driver unjustified. The required
change is a narrow legacy/non-A DA9214 variant in `da9211-regulator`, gated by
the exact compatible and documented page-2 interface signature. It must never
accept ID zero globally or access a legacy page reserved for production/test.

There is also a page-state hazard to fix as part of that variant. Live Gemian
observed `PAGE_CON=0x80`, with `REVERT` asserted, while the generic regmap
selector is cacheable. Hardware can return to page 0 after an access while
regmap still believes another page is selected. Legacy signature reads must
therefore force a selector for every page-2 access or use the documented
alternate page address, and must finish in a verified documented page state.

One additional controller-ownership difference remains relevant. A fresh
read-only check of the running Gemian DT confirms `mediatek,appm_used` on
I2C6, and the active kernel logs running CPUHVFS/DVFSP transitions. The pinned
vendor I2C driver pauses DVFSP with `SEMA_I2C_DRV` around every I2C6 hardware
transfer. Candidate AL used the generic mainline controller path, which has no
equivalent pause. This does not rescue the `0x201` probe—the register is still
outside the legacy application map—but it means AL cannot establish safe
shared ownership for later regulator writes. The next resource-only run must
also capture the mainline DVFSP/I2C6 handoff state. Any active competing owner
blocks rail changes until the matching arbitration contract is implemented
and validated.

See
[`da9214-datasheet-crosscheck-20260723.txt`](results/da9214-datasheet-crosscheck-20260723.txt).

## Conclusion

`fail, root cause isolated`: Candidate AL preserves the inherited eight-A53,
console, keyboard, USB, and native-reboot path, and I2C6 plus the exact `0x68`
client enumerate. The regulator prerequisite fails because the upstream
DA9211-family driver assumes the A-family `0x201` identity page for Gemini's
legacy/non-A-compatible DA9214. The legacy device predictably returns zero,
so the driver leaves the client unbound and registers neither regulator. Do
not repeat unchanged AL and do not proceed to an A72 request.

## Follow-up

Add a fail-closed legacy DA9214 variant to the existing DA9211-family driver;
do not create a standalone driver. The next candidate remains resource-only:
no CPU8/9 request, no regulator consumer, and no enable, disable, or voltage
change. It must attributeably prove the documented page-2 signature, safe
page-state handling, mainline DVFSP/I2C6 ownership state, driver binding, and
both regulator registrations. Any signature, transfer, ownership, page-state,
or registration mismatch must leave the driver unbound. No active regulator
write is authorized unless the competing firmware is proven quiescent or the
I2C6 arbitration contract is first implemented and validated.

In parallel, complete and review the Gemian owner-local online and
last-A72-offline transaction capture. The March 29 image is not an exact
`59e00a` build; `59e00a` is only the selected public equivalent for the
verified hook blobs. Candidate AM remains the first possible one-way CPU8
provider, with no OPP, cpuidle, thermal transition, or unproven hotplug-off
policy, and stays on hold until both prerequisites are resolved.
