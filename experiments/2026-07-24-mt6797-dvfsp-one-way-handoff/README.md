# Experiment: normalize the stopped MT6797 DVFSP clock handoff

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-24-mt6797-dvfsp-one-way-handoff` |
| Status | `passed` — exact Candidate AO booted from logical `boot2` and the predeclared one-way handoff oracle passed |
| Runtime validation | `completed`; named-unit/exact-revision clock normalization confirmed while I2C6 remained disabled |
| Candidate | `AO` |
| Subsystem | MT6797 DVFSP/CSPM and the shared I2C_APPM clock |
| Device variant | Current named Gemini PDA development unit |
| Date(s) | 2026-07-24 |
| Investigator(s) | Codex and device owner |
| Tracking issue | None; the support-matrix state is not promoted without one |

## Question or hypothesis

Can Linux convert Candidate AN's observed stopped-PCM/ungated-clock handoff
into an attributable CCF-owned gated state without changing the retained
firmware state?

The falsifiable Candidate AO hypothesis is:

1. three initial samples match Candidate AN's exact stopped CSPM signature and
   show a valid, physically ungated I2C_APPM clock;
2. exactly one successful `clk_prepare_enable()` followed by exactly one
   `clk_disable_unprepare()` keeps the PCM byte-for-byte stable, observes the
   clock ungated while the temporary reference is held, and leaves it
   physically gated after the reference is balanced; and
3. one automatic, read-only sample after 45 seconds still shows that same
   exact stopped CSPM signature and the clock gated.

The predeclared decision oracle is:

| Observation | Classification | Decision |
| --- | --- | --- |
| Exact Candidate AN stopped signature; initial gate ungated; one balanced CCF transition; post-transition and 45-second samples retain that signature and show the gate closed | `PASS` / driver `ready` | The narrow clock-accounting normalization worked for this boot. Keep I2C6 disabled; review a separate consumer-dependency experiment next. |
| Exact Candidate AN stopped signature; all three initial samples show the gate already closed; transition, enable, disable, and late-check counters remain zero | `INCONCLUSIVE` / driver `inconclusive` | No attributable transition occurred. Keep I2C6 disabled and do not treat the boot as handoff proof. |
| Any active, changing, malformed, or unrecognized PCM/gate state; CCF failure; an unbalanced reference; the gate not open while held; the gate not closed afterward; or any immediate/late PCM change | `FAIL` / sticky driver `faulted` | Perform no I2C6, DA9214, regulator, or A72 operation. Return through the independent recovery path and explain the mismatch before another test. |

For this first mutating experiment, the stopped signature is deliberately
exact: timer before/after `0`, `PCM_CON1=0x00006c00`, zero `PCM_PWR_IO_EN` and
R15, FSM `0x00048490`, and `SW_RSV0..6=0xbabebabe`. The newly observed
`PCM_CON0` must have its PCM/IM kick and software-reset bits clear and remain
bit-for-bit stable across all samples. Only infracfg gate bit 1 is interpreted.
Any other stable-looking signature faults before a CCF transition.

This is deliberately a narrow, state-changing clock-gate experiment. It is not
an I2C transfer, a DA9214 identification, a regulator operation, DVFSP firmware
control, or Cortex-A72 authorization.

## Provenance and environment

The predecessor evidence is:

- [Candidate AN](../2026-07-24-mt6797-dvfsp-handoff-observer/README.md)
  booted successfully from full-readback-verified logical `boot2`. Its exact
  accepted runtime observed a stable reset-like PCM, no modeled firmware
  motion, and I2C_APPM physically ungated. I2C6 remained disabled and had no
  platform device, adapter, client, or regulator. The accepted capture SHA-256
  is
  `6278c99ffe80e2f79541a1313195e58907255ee93f909cb903a7b430c41f8adb`.
- The
  [DVFSP/I2C6 arbitration recovery](../2026-07-24-mt6797-dvfsp-i2c6-arbitration/README.md)
  establishes from the exact active Gemian ELF that vendor stop is reversible,
  that `SEMA_I2C_DRV` is a per-transaction pause source rather than a hardware
  semaphore, and that stopped state has no synthesized persistent DVFSP clock
  reference. The retained external-firmware audit found no positive direct PCM
  restart writer, but ATF CSPM/semaphore activity and an SCP-local alias remain
  explicit uncertainty. Candidate AO therefore validates at the receiver and
  faults closed rather than claiming global firmware exclusivity.

The Candidate AO inputs are:

- Upstream Linux `7.1.3`, released 2026-07-04, from
  `https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz`, SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Kernel profile
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-`
  `a72-observer-initcall-blacklist-dvfsp-handoff-owner`, pinned in
  [`kernel/manifest.json`](../../kernel/manifest.json).
- [`patches/series-dvfsp-handoff-owner`](../../patches/series-dvfsp-handoff-owner):
  exactly 100 lines comprising three comments and 97 selected patch entries.
  The entries are `0001` through `0092`, including separately numbered
  `0057a`, followed by `0094`, `0095`, `0097`, and `0098`. Unsafe active-power
  draft `0093` and draft legacy-DA9214 patch `0096` are absent.
- Selected-series SHA-256
  `00b79dc273943b52f7353b9e8252ab7a2963c0f45b5aea0077885af7f9fb28af`;
  path-sensitive patchset SHA-256
  `98b2058c6c7127bcb441d734090025581dc1ebdfc50537123ea6ad3b1d9aec32`;
  and ordered configuration-input SHA-256
  `0a6d7cedaf2b1b7bd4f6dd896d307ccd7696eecf88fafb30ee01e15ae92fdb54`.
- Owner binding patch
  [`0097`](../../patches/v7.1.3/0097-dt-bindings-soc-mediatek-add-MT6797-DVFSP-handoff-owner.patch),
  SHA-256
  `11b5fb7c0cf8ef034fa3e1db706d05e3bab7f5aeade0d7592a2213ed7e3ac910`,
  and owner implementation patch
  [`0098`](../../patches/v7.1.3/0098-soc-mediatek-add-MT6797-DVFSP-one-way-handoff.patch),
  SHA-256
  `260f84c885d9f25524162ab097f1377137b55b5461af2b429d4508f1cfe58748`.
  The series also pins corrected A72 rejection patch `0092` and predecessor
  observer patches `0094`/`0095` at the hashes enforced by
  `scripts/validate-package.py`; `0097`/`0098` replace the observer contract and
  implementation.
- [`configs/gemini-dvfsp-handoff-owner.fragment`](../../configs/gemini-dvfsp-handoff-owner.fragment)
  selects built-in `CONFIG_MTK_MT6797_DVFSP_HANDOFF=y`. The complete profile
  keeps `maxcpus=8`, blacklists the inherited A72-power initcall, and resolves
  `CONFIG_SUSPEND=n`, so Candidate AO makes no suspend/resume claim.
- The expected package build identity is kernel release
  `7.1.3-gemini-observability-L`, GCC
  `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`, and GNU ld
  `2.42`.
- The source mirror
  [`src/mt6797-dvfsp-handoff.c`](src/mt6797-dvfsp-handoff.c) has SHA-256
  `7967d921f3b6dd43b9f88c44fc0752d624ef4a2504c3d9b4882dc6b34f7e2f2d`.
  Patch `0098`, not this convenience mirror, is the build input.
- The source-pinned semantic FDT parser, compiled fail-closed A72-gate auditor,
  and compiled handoff auditor have SHA-256 values
  `444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66`,
  `90aa983f66261e18f192b14a535ccf9520b6e9079d45a8ce9234e30de8e90bde`,
  and
  `e008e4011c3a3cb1a6e3a4877e12955117cd7046ea2f1f37e87a8599b30808be`,
  respectively.

The final boot-artifact DT starts from the exact hardware-passed Candidate AH
DT, SHA-256
`27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845`,
and adds only `/dvfsp-handoff@11015000`. Its source-pinned SHA-256 is
`de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`.
The added node maps the CSPM validation window, references exact AH
I2C6's `main` clock `<0x3 0x36>`, and uses existing infracfg phandle `0x3`.
The whole-tree validator requires every existing AH node, property,
reservation, string block, and phandle to remain unchanged. In this final DT:

- I2C6 is byte-exact Candidate AH, `status = "disabled"`, and childless;
- no DA9214 node is present;
- no A72-power node is present; and
- no legacy DVFSP or Candidate AN observer node is present.

Two clean kernel builds used six distinct, surviving source/build/artifact
roots. Their 236-member packages have byte-identical substantive content and
119 byte-identical DTBs; only `generated_utc` and its derived manifest entry
differ. Both have normalized source-build SHA-256
`0a414ce1e25414e6001fbc81046ff799bcb88d259fd224634a136768a15dd5ce`,
resolved configuration SHA-256
`4aab63bad14a689a450395de0c33636ee2946df79a9df3b7993f5db4da5b8318`,
`Image` SHA-256
`22445b6319347e8ce5a9a132d76d5d466ed1b46678c31155efbaa943c7d80d26`,
`Image.gz` SHA-256
`f077c0196cdf0678671f5672beb41bef698626d9c9b6be9720d7f1a56e9ffc05`,
and `System.map` SHA-256
`6f34cb0c656569777932e45aae9c895234c4b8acf5f7fd2a425bd7aae9badadf`.

Two complete 18-member Android-v0 artifact trees are byte- and mode-identical.
The source-pinned artifact has final-DT SHA-256
`de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`,
manifest SHA-256
`6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85`,
raw boot-image SHA-256
`44fc1e6a74744ce546f86f47cfdc7a25f23b134ac59da902f8ac302033875c66`
at 7,387,136 bytes, and exact 16 MiB padded SHA-256
`3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb`.

The source-pinned guarded installer, SHA-256
`cbb6b8da36ec7f6a48726b9e5304667068719bd406e9df642376b98c0e6bd730`,
ran from known-good Gemian. The live GPT resolved logical `boot2` as the
inactive 16 MiB `/dev/mmcblk0p30` while root remained `/dev/mmcblk0p29`.
It verified exact Candidate AN predecessor SHA-256
`1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb`,
preserved a private full backup, wrote only `boot2`, flushed it, and obtained
matching remote and independent local full-partition readbacks of
`3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb`.
It did not reboot or select a slot. The owner subsequently selected logical
`boot2`, and the exact installed image passed the runtime oracle and private
post-LK whole-FDT gate recorded below.

## Safety assessment

Candidate AO is not read-only: on the qualifying initially-ungated path, it
changes the physical I2C_APPM clock gate through exactly one balanced common
clock framework reference. The balance returns Linux's logical reference count
to its starting value; the intended hardware result is a closed gate. The
driver directly reads CSPM and infracfg status, but it performs no direct MMIO
write and no `regmap_write()` or `regmap_update_bits()`. Any underlying gate
write belongs to the existing CCF clock provider.

The driver does not start, stop, pause, reset, kick, or load DVFSP firmware. It
does not map CSRAM, request a DVFSP interrupt, issue an I2C transaction, touch a
regulator, change voltage, request CPU8/CPU9, expose a restart/unpause control,
or provide writable sysfs state. It is built in, suppresses bind/unbind
attributes, has no remove path, permits at most one transition attempt, and
makes every observed mismatch sticky-faulted until reboot.

The final experiment DT, not merely runtime policy, keeps I2C6
disabled/childless and omits DA9214 and A72-power consumers. The inherited
eight Cortex-A53 CPUs, USB development endpoint, keyboard, loader-retained
console, and native reboot path remain regression gates, not new Candidate AO
features.

Build, validation, and artifact assembly have no device access. If and only if
all exact package and artifact gates pass, the separately derived installer
must use known-good Gemian to live-resolve logical `boot2`, prove that it is
inactive, unmounted, writable, and exactly 16 MiB, require the exact
readback-verified Candidate AN predecessor and stable power, preserve a private
mode-0600 full backup, write only the padded Candidate AO image, sync and
flush, and require matching remote and independent local full-partition
readbacks. It must never substitute another partition, write primary `boot`,
`boot3`, preloader, NVRAM, GPT, or a whole device, select a boot target, or
reboot.

The owner must select `boot2` manually. The runtime collector is observation
only: it reads the already-published state and inherited runtime contracts over
the direct USB development link. It performs no partition read, I2C/regulator/
CPU-hotplug operation, watchdog action, or reboot. Recovery is a reboot or
power-cycle into independently bootable Gemian; the test does not attempt an
inverse firmware or clock sequence.

Stop after any unexpected heat, battery or charging anomaly, storage error,
watchdog loop, changed recovery behavior, kernel fault, spontaneous reboot,
I2C6/DA9214/A72 activity, or owner/validator fault. Do not repeat an identical
failed or inconclusive image unless a new measurement can change the decision.

## Associated code

Candidate AO preparation is intentionally split into exact, storage-inert
stages:

- [`kernel/manifest.json`](../../kernel/manifest.json),
  [`patches/series-dvfsp-handoff-owner`](../../patches/series-dvfsp-handoff-owner),
  [`configs/gemini-dvfsp-handoff-owner.fragment`](../../configs/gemini-dvfsp-handoff-owner.fragment),
  patches [`0097`](../../patches/v7.1.3/0097-dt-bindings-soc-mediatek-add-MT6797-DVFSP-handoff-owner.patch)
  and [`0098`](../../patches/v7.1.3/0098-soc-mediatek-add-MT6797-DVFSP-one-way-handoff.patch),
  and [`src/mt6797-dvfsp-handoff.c`](src/mt6797-dvfsp-handoff.c) define the
  selected source boundary.
- [`results/build-install-candidate-ao-20260724.txt`](results/build-install-candidate-ao-20260724.txt)
  records the clean-root preflights, all six live roots, package and artifact
  identities, focused test counts, guarded installer, live-GPT resolution,
  private-backup identity, and both matching full-partition readbacks.
- [`scripts/validate-package.py`](scripts/validate-package.py),
  [`scripts/audit-compiled-handoff.py`](scripts/audit-compiled-handoff.py),
  [`scripts/normalize-build-json.py`](scripts/normalize-build-json.py),
  [`scripts/validate-package-reproduction.py`](scripts/validate-package-reproduction.py),
  and [`scripts/test-package-validators.py`](scripts/test-package-validators.py)
  check exact inputs, resolved config, embedded config, image markers,
  symbols, compiled call/control boundaries, package DT, provenance,
  independent live source/build/artifact roots, exact live-output and DTB
  linkage, and focused mutations. Distinct live roots do not reconstruct their
  historical pre-build absence; retain the command's clean-root preflight in
  the experiment result.
- [`scripts/build-ao-dtb.sh`](scripts/build-ao-dtb.sh),
  [`scripts/validate-dtb-delta.py`](scripts/validate-dtb-delta.py), and
  [`scripts/test-dtb-validator.py`](scripts/test-dtb-validator.py) derive and
  verify exact AH plus only the one handoff node.
- [`scripts/candidate_ao.py`](scripts/candidate_ao.py),
  [`scripts/build-candidate-ao.sh`](scripts/build-candidate-ao.sh),
  [`scripts/validate-boot.py`](scripts/validate-boot.py), and
  [`scripts/validate-artifact-reproduction.py`](scripts/validate-artifact-reproduction.py)
  define source-pinned output identities, assemble the storage-inert
  Android-v0 image,
  enforce the LK/container and final-DT boundaries, tie each artifact back to
  one fully validated package, recheck embedded IKCONFIG and both compiled
  audits, and compare two complete artifact trees.
- [`scripts/derive-installer.py`](scripts/derive-installer.py) and
  [`scripts/test-installer-derivation.py`](scripts/test-installer-derivation.py)
  derive the exact-target guarded `boot2` installer only after all Candidate
  AO artifact identities are calibrated.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh),
  [`scripts/validate-runtime.py`](scripts/validate-runtime.py), and
  [`scripts/test-runtime-validator.py`](scripts/test-runtime-validator.py)
  implement the bounded, no-reboot USB capture, independent raw-snapshot
  classification, inherited service checks, and mutation tests.
- [`scripts/validate-live-fdt-delta.py`](scripts/validate-live-fdt-delta.py)
  and [`scripts/test-live-fdt-delta.py`](scripts/test-live-fdt-delta.py)
  validate the exact private post-LK tree without emitting device-unique or
  command-line values.
- [`results/runtime-candidate-ao-validated-20260724.txt`](results/runtime-candidate-ao-validated-20260724.txt)
  and
  [`results/live-fdt-candidate-ao-validated-20260724.txt`](results/live-fdt-candidate-ao-validated-20260724.txt)
  are the sanitized runtime and live-FDT results.
- Artifact assembly also pins the existing Android-v0 serializer and LK
  analyzer in
  `experiments/2026-07-12-boot-contract-recovery/scripts/` at SHA-256
  `569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4`
  and
  `aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95`.
  It reuses exact Candidate AH initramfs SHA-256
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`
  and keymap SHA-256
  `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.

All build/package/artifact tools ran in the approved ARM64 recovery VM. The
completed installation used the existing mode-0600 Gemini credential and the
exact target enforced by the derived installer. The one runtime collection
used the direct Gemini USB interface and caller-supplied, previously verified
installed full-partition, resolved-config, and live-FDT identities.

## Procedure

1. Reconfirm the source, series, patchset, config-input, patch, auditor, parser,
   serializer, analyzer, AH DT, initramfs, and keymap hashes above. Require
   exactly 100 series lines and 97 selected entries, with `0093` and `0096`
   absent.
2. Build Candidate AO twice from clean guest-owned source/output trees with:

   ```sh
   KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner \
     ./scripts/dev-vm build-kernel
   ```

3. Run `scripts/validate-package.py` on each explicit package and then
   `scripts/validate-package-reproduction.py` across them, supplying the
   actual live source directory, build directory, and artifact-root directory
   used by each invocation:

   ```sh
   python3 scripts/validate-package-reproduction.py \
     --repository /mnt/gemini-pda-mainline \
     --first "$PACKAGE1" --second "$PACKAGE2" \
     --first-source-dir "$SOURCE_DIR1" \
     --first-build-dir "$BUILD_DIR1" \
     --first-artifact-root "$ARTIFACT_ROOT1" \
     --second-source-dir "$SOURCE_DIR2" \
     --second-build-dir "$BUILD_DIR2" \
     --second-artifact-root "$ARTIFACT_ROOT2"
   ```

   Here `SOURCE_DIRn` and `BUILD_DIRn` are the final profile-specific
   directories below the `GEMINI_SOURCE_ROOT` and `GEMINI_BUILD_ROOT` values,
   while `ARTIFACT_ROOTn` is the exact `GEMINI_ARTIFACT_ROOT`. Require six
   distinct live roots, exact source/build state markers, an exact package
   child of each artifact root, exact `Image`, `Image.gz`, `.config`,
   `System.map`, and complete MediaTek DTB inventory/bytes from the
   corresponding live build. Also require exact package manifests, 97 selected
   patches, resolved/embedded configuration, package DT, fail-closed CPU gate,
   and compiled handoff audit. Do not select a package merely by timestamp.
   The validator proves the surviving roots are distinct and linked; the
   clean-root preflight remains separate historical evidence and must be
   recorded.
4. Derive the final DT twice from exact Candidate AH with
   `scripts/build-ao-dtb.sh`. Require byte equality, SHA-256
   `de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`,
   one added six-property handoff node, byte-exact disabled/childless I2C6, and
   absent DA9214, A72-power, legacy-DVFSP, and observer nodes.
5. Assemble two complete Candidate AO Android-v0 artifacts from the independent
   packages and exact AH artifact inputs with
   `scripts/build-candidate-ao.sh`. Validate each with
   `scripts/validate-boot.py`, compare the trees with
   `scripts/validate-artifact-reproduction.py`, passing both source packages:

   ```sh
   python3 scripts/validate-artifact-reproduction.py \
     --repository /mnt/gemini-pda-mainline \
     --first-package "$PACKAGE1" --second-package "$PACKAGE2" \
     --first-source-dir "$SOURCE_DIR1" \
     --first-build-dir "$BUILD_DIR1" \
     --first-artifact-root "$ARTIFACT_ROOT1" \
     --second-source-dir "$SOURCE_DIR2" \
     --second-build-dir "$BUILD_DIR2" \
     --second-artifact-root "$ARTIFACT_ROOT2" \
     --first "$ARTIFACT1" --second "$ARTIFACT2" \
     --ah-artifact "$AH_ARTIFACT"
   ```

   Require both full package validators, all six distinct live-root state,
   output, and DTB checks, and the package reproduction comparison to pass
   again inside the artifact-calibration command. Each artifact's `Image.gz`,
   `System.map`, `kernel.config`, and normalized source-build must match its
   package exactly; its decompressed Image and embedded IKCONFIG must match;
   its normalized package-validation report must have the exact canonical
   inventory and values; and fresh compiled A72 rejection and handoff audit
   reports must equal the corresponding package audit hashes. Then require
   artifact byte/mode identity. Only then pin the resolved config, `Image.gz`,
   `System.map`, normalized source-build, raw image/size, artifact-manifest,
   and padded-image hashes.
6. Derive the exact Candidate AO installer from the source-pinned Candidate AN
   installer and run its focused tests. In known-good Gemian, execute it only
   after all source and artifact pins are complete. Require the live GPT,
   inactive/unmounted exact logical `boot2`, exact Candidate AN predecessor,
   stable power, private full backup, bounded write, flush, and matching full
   readbacks. The installer must not reboot or select a slot.

   **Completed.** The exact identities and write/readback evidence are in
   `results/build-install-candidate-ao-20260724.txt`.
7. Before the boot, record the exact hypothesis, unique evidence, and decision
   boundary in this file. The exact installed full-partition SHA-256 is
   `3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb`.
   Relative to Candidate AN, its attributable changes are the source-pinned AO
   kernel owner and exact final-DT handoff node; it retains the exact AH
   initramfs and inherited console, keyboard, USB, and reboot contract. The
   expected result is the predeclared initially-ungated, one-balanced-CCF-
   transition, immediately-gated, 45-second-still-gated `PASS` path above.
   Initially gated remains `INCONCLUSIVE`; any other state is sticky `FAIL`
   with no I2C6, DA9214, regulator, or A72 operation. At this pre-boot
   declaration point Candidate AO had not yet booted. The owner manually
   selected `boot2`; no software substituted another boot path.
8. Allow one Candidate AO boot. Do not touch I2C6, DA9214, a regulator,
   CPU8/CPU9, or a watchdog. Wait through the driver's 45-second late check.
   Run `scripts/collect-runtime.sh` once over the exact direct USB interface.
   It captures the final publication twice at least five seconds apart and
   does not reboot the device.

   **Completed once.** The owner reported a successful `boot2` selection; the
   bounded collector performed no reboot or prohibited operation.
9. Run `scripts/validate-runtime.py` with the already pinned installed
   full-partition, resolved-config, and expected post-LK live-FDT identities.
   Require stable repeated publication, independent raw-snapshot
   classification, advancing CPU0-CPU7 accounting, offline/unrequested
   CPU8/CPU9, and no I2C6/DA9214/A72, fault, watchdog-owner, or spontaneous
   reboot activity.

   **Completed.** The private capture has SHA-256
   `1e7e5377116a887c530b1da3925b8fe21383d915819d06ac2a68eb0762c64097`;
   its sanitized result is linked above, and 24/24 focused runtime mutations
   pass.
10. Record exactly one of `PASS`, `INCONCLUSIVE`, or `FAIL` from the
    predeclared oracle. Do not promote compile-only evidence to hardware
    support and do not repeat an unchanged candidate solely to seek a preferred
    result.

    **Recorded: `PASS`.**

## Observations

- Two clean kernel builds used distinct preflight-absent source, build, and
  artifact roots. Their substantive package bytes, live outputs, complete
  MediaTek DTB inventory, resolved and embedded config, and compiled audits
  match. Two complete AO artifact trees are byte- and mode-identical. The
  focused package, DT, pre-boot runtime, and installer suites passed 16/16,
  41/41, 22/22, and 4/4 mutations respectively. Post-capture hardening raised
  the runtime suite to 24/24 and added a 12/12 private live-FDT suite.
- The deterministic final-DT transformation has source-pinned SHA-256
  `de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`.
  Its semantic contract is exact Candidate AH plus one handoff node; final-DT
  I2C6 remains disabled/childless and DA9214/A72-power remain absent.
- From known-good Gemian, the guarded installer resolved exact logical `boot2`
  as inactive `/dev/mmcblk0p30`, verified stable external power and the exact
  Candidate AN predecessor, preserved a private full backup, and wrote only
  the exact 16 MiB AO image. Its remote post-flush and independent local
  full-partition readbacks both equal
  `3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb`.
  It neither rebooted nor changed boot selection.
- Candidate AO booted from logical `boot2` as kernel
  `7.1.3-gemini-observability-L`, resolved config
  `4aab63bad14a689a450395de0c33636ee2946df79a9df3b7993f5db4da5b8318`,
  and boot ID `bf77e5ab-7969-40fd-88e5-17d791324b8a`. Two final publications
  were stable through uptime 1,211 seconds.
- All six independently parsed snapshots retained timer `0`,
  `PCM_CON0=0x00000004`, `PCM_CON1=0x00006c00`, zero `PCM_PWR_IO_EN` and R15,
  FSM `0x00048490`, and `SW_RSV0..6=0xbabebabe`. Gate bit 1 was clear in
  `pre0`, `pre1`, `pre2`, and `enabled`, then set in `post` and the 45-second
  `late` sample. Driver counters were exactly one attempt, one successful
  enable, one disable, one passed late check, and zero faults.
- CPU0–7 remained online and all advanced; CPU8/9 remained offline and
  unrequested. I2C6 remained disabled/childless with no platform device,
  adapter, client, or regulator; no DA9214 or A72-power activity appeared.
  The inherited framebuffer, console, exact keymap readback, USB service, and
  reboot-dispatch contract passed. The collector did not execute reboot and
  no userspace watchdog owner existed.
- The 52,567-byte post-LK FDT has SHA-256
  `7529b57dbc810419ba06f220408676305314cb4c6dc133d61d3daec6cf3af197`.
  The private whole-tree gate accepted exactly 37 LK changes, kept the AO
  handoff node byte-exact, uniquely resolved clock `<0x3 0x36>` to the exact
  infracfg node, and found no unexpected semantic delta.
- The collector initially returned validation exit 2 for
  `keymap_verify_output_hex`. The immutable capture twice contained the
  established `K_ALLOCATED` verifier result with return code zero; the new
  validator literal had omitted one `L`. After replacing the opaque typo with
  a readable exact string and adding an independent literal assertion, the
  same capture passed. No second runtime-collector invocation occurred.

## Analysis

Candidate AN supplies the discriminating initial condition but not ownership:
its retained PCM was stable/reset-like while I2C_APPM was physically ungated.
Because `clk_ignore_unused` intentionally preserves inherited clocks, Linux
could have a hardware-on/logical-count-zero state. Candidate AO tests the
narrow hypothesis that acquiring and balancing one normal CCF reference
reconciles that state and closes the gate.

The enabled snapshot distinguishes a real CCF reference from an already-closed
or misidentified gate. The immediate post-balance sample attributes the
ungated-to-gated transition to the one attempted balance. The 45-second sample
detects a delayed firmware or external owner reopening the clock or changing
the PCM. An initially gated result contains no transition and is therefore
inconclusive rather than retroactively accepted.

Candidate AO took the discriminating path. The enabled sample proves that the
shared gate was still open while Linux held its one temporary CCF reference;
the immediate post-balance sample attributes the gate closure to balancing
that reference. The identical 45-second sample and zero-fault publication
exclude delayed reopening or measured PCM drift in this boot window. The
kernel counters and independent snapshot classifier agree.

Even a `PASS` is bounded to this named unit, exact boot, and observed time
window. It does not implement the vendor per-transfer pause map, lock, CSRAM
mirrors, retry/unwind behavior, or persistent running-DVFSP/A72 iDVFS
references. It does not prove the absence of every secure or SCP computed
writer. It cannot authorize I2C6, legacy DA9214 identification, voltage
changes, or an A72 request by itself. `CONFIG_SUSPEND=n` also means the result
says nothing about resume.

## Conclusion

Candidate AO is `confirmed` for its narrow, predeclared claim on this named
unit and exact revision. One balanced CCF reference converted the exact
Candidate AN stopped/ungated state to a stable gated state without changing
the measured PCM signature, and the 45-second validation passed with zero
faults. This is a successful clock-accounting normalization for this boot, not
general DVFSP ownership or permission to use I2C6.

## Follow-up

- Keep I2C6 disabled in Candidate AO. Review a separate candidate that makes
  the validated handoff an explicit prerequisite of the I2C6 consumer path.
- Legacy DA9214 identification remains a distinct, resource-only step; any
  voltage operation and any Cortex-A72 request require later independent
  review.
- Add resume validation before making any suspend/resume claim; AO has
  `CONFIG_SUSPEND=n`.
- Keep Candidate AM and both Cortex-A72 CPUs on hold until the I2C6/DA9214 and
  owner-synchronized power-state prerequisites are independently satisfied.
