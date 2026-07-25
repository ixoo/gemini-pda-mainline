# MT6797 DVFSP-gated childless I2C6 Candidate AP

| Field | Value |
|---|---|
| Date | 2026-07-24 |
| Status | `hardware FAIL, safely recovered` — AP booted once from `boot2`; its exact live FDT passed, but the provider faulted closed because AP_DMA never regated after the guarded I2C6 clock hold; native reboot returned to changed-ID Gemian and a read-only full `boot2` checksum remained exact |
| Candidate | `AP` |
| Device | Planet Computers Gemini PDA, owner-named development unit |
| Required and observed predecessor | exact hardware-passed Candidate AO on logical `boot2`, preserved in a private full backup before AP installation |
| Installed candidate | exact Candidate AP padded SHA-256 `602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9` on live-resolved logical `boot2`; the same full hash passed after the completed AP/Gemian cycle |
| Main profile | `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer` |
| PM compile-audit profile | main profile plus `-pm-audit`; non-installed and never assembled |

## Question

After Candidate AO has reached its terminal `ready` state and passed the
45-second late check, can Linux initialize the otherwise childless MT6797 I2C6
controller exactly once without issuing a bus transaction, starting DMA,
observing a nonzero controller START, or handling an I2C interrupt?

Candidate AP is not a DA9214 experiment. It adds no I2C client, regulator, or
Cortex-A72 resource and performs no I2C command. The upstream I2C controller
probe is nevertheless an active hardware operation: after authorization it
opens the controller clocks, resets/configures the controller and DMA state,
then closes the clocks. A compile result alone is not evidence that this is
safe or functional on the device.

## Hypothesis and attributable evidence

The installed AP candidate has one hypothesis:

> an explicit access-controller dependency prevents the first I2C6 probe until
> the exact AO handoff owner is terminally ready; one guarded controller
> initialization then leaves the controller quiet and the inherited board
> services intact.

The exact hardware run rejected that hypothesis under the predeclared oracle.
The provider reached `ready` and granted one access, but AP_DMA remained
ungated through every one of the 32 cleanup samples. The provider changed to
`faulted`, denied further access, and I2C6 failed probe with `-EIO` before
binding an adapter or issuing a transfer.

The unique observation path is:

1. exact AO logs its terminal `ready` state after the late check;
2. the handoff provider publishes one successful access-controller bind;
3. the provider records one full held sample with I2C_APPM and AP_DMA both
   ungated, then 32 compact cleanup samples after disable; all 32 keep
   I2C_APPM gated and valid, every AP_DMA read is valid, and at least one has
   AP_DMA gated;
4. the full `consumer-post` sample exactly cross-links the first DMA-gated
   compact sample, and the provider records zero cleanup PCM/main failures;
5. I2C6 publishes one guarded-init record with one probe, one hardware init,
   one success, and zero transfer, DMA-start, nonzero-START and IRQ counters;
6. two read-only samples at least five seconds apart report the same counters,
   zero I2C children/clients/regulators, and zero suspend/resume counters.

The runtime collector never requests a power-state transition. System-sleep
callbacks are compiled and linked only in the separate PM-audit package, which
must never be assembled into an Android boot image, installed, or booted.

### Context-only shared-DMA baseline

A sanitized, read-only known-good Gemian 3.18 observation is preserved in
[`results/gemian-infra1-pdn-baseline-20260724.txt`](results/gemian-infra1-pdn-baseline-20260724.txt).
`INFRA1_PDN_STA` at `0x10001094` read `0x0246c872` once, then `0x0246c876`
for 20 active-SSH samples. Relevant `INFRA_AP_DMA` bit 18 remained set
(`gated`) throughout; unrelated bit 2 varied. This is context for AP's
post-disable cleanup oracle, not an expected value for AP's held sample, not
proof about AP, and not permission to touch hardware.

## Exact scope

### Installed AP

The main profile explicitly retains `CONFIG_SUSPEND=n`. Its AP fragment carries
the complete inherited forced command line plus `fw_devlink=rpm` and pins the
sleep policy closed. Linux 7.1.3 already defaults to the `rpm` policy; pinning
it makes managed supplier blocking attributable while preserving runtime-PM
coupling.

The final AP DT is derived from the exact hardware-passed AO final DT, SHA-256
`de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`.
Its complete semantic delta is:

- add `#access-controller-cells = <0>` and phandle `0x2c` to
  `/dvfsp-handoff@11015000`;
- add `access-controllers = <&dvfsp_handoff>` to `/i2c@1100e000`;
- change only I2C6 `status` from `disabled` to `okay`.

There are no added nodes. I2C6 remains childless and lacks
`clock-frequency`, `mediatek,use-push-pull`, `pinctrl-names`, and `pinctrl-0`.
There is no DA9214, regulator, legacy DVFSP, observer, or A72-power node.

### Non-installed PM compile audit

[`configs/gemini-dvfsp-i2c6-consumer-pm-audit.fragment`](../../configs/gemini-dvfsp-i2c6-consumer-pm-audit.fragment)
enables `CONFIG_SUSPEND`, `CONFIG_PM_SLEEP`, and `CONFIG_SUSPEND_FREEZER`, while
leaving hibernation and both autosleep policies disabled. The PM-audit package
exists only to prove the provider/consumer protected late/early callbacks
compile and link, the inherited I2C noirq callbacks bypass the protected
adapter, and device-link ordering remains auditable. The artifact builder
rejects that profile.

No suspend/resume hardware claim may be made from this experiment. A later
power-state experiment requires a separate authorization, oracle, artifact,
and recovery plan.

### AP_DMA ownership clue

AP_DMA was already valid and ungated in all three initial provider samples,
before the I2C6 consumer hold, and remained ungated afterward. The exact AP DT
also gives the same AP_DMA clock to enabled UART0 and I2C5; UART0 became the
active `ttyS0` console before AP completed. Those facts make an inherited or
shared owner a concrete next hypothesis, but this run does not identify which
consumer owns the surviving CCF reference. Gemian's gated read-only sample is
context from a different kernel and cannot override AP's exact baseline.

## Inputs

Candidate AP uses exact Candidate AO lineage:

- artifact directory:
  `candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a`;
- artifact manifest SHA-256:
  `6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85`;
- raw boot SHA-256:
  `44fc1e6a74744ce546f86f47cfdc7a25f23b134ac59da902f8ac302033875c66`;
- full padded/readback SHA-256:
  `3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb`;
- final DT SHA-256:
  `de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`;
- initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`;
- keymap SHA-256:
  `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`;
- guarded installer SHA-256:
  `cbb6b8da36ec7f6a48726b9e5304667068719bd406e9df642376b98c0e6bd730`.

New logical patches:

- [`0099`](../../patches/v7.1.3/0099-dt-bindings-mediatek-gate-MT6797-I2C-with-DVFSP-handoff.patch)
  adds the access-controller binding contract;
- [`0100`](../../patches/v7.1.3/0100-soc-mediatek-require-ready-MT6797-DVFSP-handoff-supplier.patch)
  adds the supplier API, terminal bind gate, consumer clock validation and
  compile-only PM callbacks;
- [`0101`](../../patches/v7.1.3/0101-i2c-mediatek-require-MT6797-DVFSP-handoff.patch)
  places the readiness check before I2C resources/MMIO initialization and adds
  durable quietness counters;
- [`0102`](../../patches/v7.1.3/0102-arm64-dts-mediatek-enable-childless-Gemini-I2C6-after-handoff.patch)
  removes active I2C6 policy/children and adds the access-controller link.

The selected series is
[`patches/series-dvfsp-handoff-owner-i2c6-consumer`](../../patches/series-dvfsp-handoff-owner-i2c6-consumer).
It is exact AO plus 0099–0102 and excludes active A72 patch 0093 and legacy
DA9214 patch 0096.

The frozen R3 source identities are:

- 0099: `11c6f09cdc02bfcf82a20946af40ef05e935f8679a34a01e6145728e8420115f`;
- 0100: `c3b1f67ef13a8b694af2d7e99b57bea68928b1e25f94898b4137cc1a629a7313`;
- 0101: `f2427527f16b75c9abd4578d1a235278e7ac1ac7311ed9e68803e5ac395487aa`;
- 0102: `b18ed3111ca3035180b4ce5b45556618c0a8295a471c0c5b11caf114be677094`;
- selected series:
  `f345600c8e7880b2eb8835f816aa99b963f9f28497467f5585cfb8877b6ddf6a`;
- path-sensitive patchset:
  `0b0dd6b642eaa2c648b7746bfc6531977a203a73a8b2e7dbdb8c57fd17cbe8f2`;
- compiled dependency auditor:
  `86518f5fb39615124df05ae46598ff70c1a855fab73612dbeda6147bfdfc6351`.

## Decision table declared before a device boot

| Observation | Result | Next action |
|---|---|---|
| Exact AO-ready chronology; one supplier grant; held I2C_APPM/AP_DMA both ungated; exact 32-sample cleanup with all main gates valid/gated and at least one valid DMA-gated sample; selected full post sample cross-links the first DMA-gated compact sample; one I2C6 init; two quiet samples; all transfer/START/DMA/IRQ/PM and cleanup-failure counters zero; no child/client/regulator/A72; inherited CPU0–7, console, keyboard, USB and reboot gates pass | `PASS` for the named childless-controller question only | Preserve evidence and review a separately scoped next consumer experiment |
| Provider binds in the exact initial-gate-already-gated terminal state; access grant is denied; no I2C6 bind, adapter, or hardware mutation occurs | structured `INCONCLUSIVE` | Do not retry an identical artifact; add a decision-changing observation or change the hypothesis |
| Provider reaches any `faulted` terminal state, supplier grant is absent/duplicated after `ready`, I2C6 probes before readiness, or init count is not exactly one | structured `FAIL` | Return to the known-good OS and inspect ordering/source evidence |
| Any transfer, DMA-start, nonzero-START, IRQ, suspend/resume, child/client/regulator, DA9214 or A72 counter is nonzero | `FAIL` | Return to known-good OS; do not promote the candidate |
| Console, keyboard, USB, eight-A53, or reboot regression; panic/hang/reboot | `FAIL` | Recover exact evidence; no unchanged repeat |
| Evidence is incomplete, malformed, from another boot, or samples are under five seconds apart | validation `FAIL` (not the structured terminal outcome) | Improve the independent observation path before another boot |

## Reproducible workflow

1. Run the local static checks. They perform no device access:

   ```sh
   python3 scripts/test-dtb-validator.py --ao-dtb /exact/AO/final.dtb
   python3 scripts/test-package-validators.py
   python3 scripts/test-runtime-validator.py
   python3 scripts/test-live-fdt-delta.py
   python3 scripts/test-live-fdt-capture.py
   python3 scripts/test-native-reboot-validator.py
   bash scripts/test-request-native-reboot.sh
   bash scripts/test-verify-post-return-boot2.sh
   python3 scripts/test-installer-derivation.py
   ```

2. In recovery VM `gemini-pda-build-recovery-20260717`, build the main AP
   profile twice with `KERNEL_JOBS=8`. Use six distinct, preflight-absent live
   roots:

   ```text
   /home/julien.guest/src/candidate-ap-kernel-build1-exact-20260724
   /home/julien.guest/build/candidate-ap-kernel-build1-exact-20260724
   /home/julien.guest/artifacts/candidate-ap-kernel-build1-exact-20260724
   /home/julien.guest/src/candidate-ap-kernel-build2-exact-20260724
   /home/julien.guest/build/candidate-ap-kernel-build2-exact-20260724
   /home/julien.guest/artifacts/candidate-ap-kernel-build2-exact-20260724
   ```

   Invoke only `./scripts/dev-vm build-kernel` with the exact main profile.
   Validate each explicit package path with
   [`scripts/validate-package.py`](scripts/validate-package.py), then compare
   them and their surviving roots with
   [`scripts/validate-package-reproduction.py`](scripts/validate-package-reproduction.py).
   Never select a package by timestamp.

3. Build the PM-audit profile once into separate explicit roots and validate it
   with [`scripts/validate-pm-audit-package.py`](scripts/validate-pm-audit-package.py).
   Do not pass it to the artifact builder. The builder independently rejects
   the PM-audit profile.

4. Assemble two AP artifacts, one from each reproduced main package, with
   [`scripts/build-candidate-ap.sh`](scripts/build-candidate-ap.sh), always
   passing the exact AO artifact. Compare their complete byte/mode inventories
   with
   [`scripts/validate-artifact-reproduction.py`](scripts/validate-artifact-reproduction.py).
   Pin output identities in [`scripts/candidate_ap.py`](scripts/candidate_ap.py)
   only after both comparisons pass.

5. Only after every pin is resolved, derive the AP installer from the exact AO
   installer with [`scripts/derive-installer.py`](scripts/derive-installer.py).
   The installer must resolve logical `boot2` from the live GPT, require exact
   AO as the inactive/unmounted predecessor, preserve a private mode-0600 full
   backup, pad to 16 MiB, write only `boot2`, flush, and require matching
   full-partition remote and independent local readbacks. It never reboots.

6. Before booting, restate the hypothesis, unique chronology/counter evidence,
   and decision table above. After the owner boots logical `boot2`, acquire the
   raw `/sys/firmware/fdt` exactly once with
   [`scripts/collect-live-fdt.sh`](scripts/collect-live-fdt.sh). The source-pinned
   decoder requires an exact direct-USB route, stable boot ID, exact AP
   configuration, matching pre/post/decoded hash and size, and a new ignored
   mode-0700 private directory with mode-0600 evidence.

7. Pin that private hash and size together, then validate the raw FDT with
   [`scripts/validate-live-fdt-delta.py`](scripts/validate-live-fdt-delta.py).
   It reuses the source-pinned LK allowlist, requires the AP access-controller
   properties to survive unchanged, validates dynamic/private values only in
   memory, and does not emit them.

8. Collect two read-only runtime samples with
   [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh), binding them to
   the same live-FDT transfer boot ID. The collector performs no partition
   read, I2C transaction, CPU hotplug, regulator operation, watchdog action,
   reboot, or power-state transition.

9. An exact terminal runtime `PASS` may authorize normal recovery, and an
   exact terminal `FAIL` may authorize outcome-bound recovery with
   `--expected-runtime-outcome FAIL` through
   [`scripts/request-native-reboot.sh`](scripts/request-native-reboot.sh). Its
   source-pinned preflight binds AP, the runtime capture and boot ID, the final
   live-FDT identity, and the inherited `/bin/reboot` hash before any device
   probe. It issues exactly one `/bin/reboot` and requires connection closure
   plus two stable exact-USB-MAC absence observations. The calibrated checked-in
   pins make the requester fail before any device probe if a dependency or
   capture changes. `INCONCLUSIVE` never authorizes this action.

10. After the changed-ID Gemian 3.18 root returns, calibrate and run
    [`scripts/verify-post-return-boot2.sh`](scripts/verify-post-return-boot2.sh).
    It revalidates the exact runtime/native evidence, live-resolves logical
    `boot2`, excludes root/mount/swap/holder use, performs one full read-only
    checksum, and proves the Gemian boot ID stayed stable. Its calibrated
    evidence and return-boot pins likewise refuse before SSH on any mismatch.

## Pinned build and artifact identities

The two main packages were built from six distinct preflight-absent live roots.
Their substantive bytes, modes, normalized provenance, exact output linkage,
and 119-DTB inventories reproduced. The only package differences were the
permitted generation timestamp and its manifest entry.

- package manifests:
  `8161dcecbe597ee1c09b28424a61b66d071bde1d9e2e156c3398705a49aa56be`
  and
  `f9acaacd1a8e87f8255035082c06b153d0004a3833d960fe5a8b4550b87be52e`;
- normalized source-build:
  `06f8aedc7b0f058d01dad6fff843a9a7b284e6c70bffbef72f702a0020cc2fae`;
- resolved config:
  `af4e641b24915e64b6cc045b207e8f665c55cd6314d29e37be8784c9d2f513c0`;
- Image.gz:
  `1dca59ec6cf75523387985a73b362709976ae484be3769f2d0a754accf894f2a`;
- System.map:
  `23c0c6a5505a341c6e37ebe5b112f5f315ec971c7a5f17c820ce81501e40b2bc`;
- final AP DT:
  `8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768`;
- raw Android-v0 boot image: 7,391,232 bytes,
  `127e511711bc06a91fcfc3c716aaad2084cc42ffc6452046a582bd53f54b2924`;
- artifact manifest:
  `dae6d5b891dfccdfc7831cea18fff2b4f43de345333f07e50303619dadd07f7a`;
- derived 16 MiB padded image:
  `602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9`;
- guarded installer:
  `3504a5b591ad4b952c577b5ecb08eaedac5027c97431152023a2d28afef7b937`.

All nine build-derived values are source-pinned in
[`scripts/candidate_ap.py`](scripts/candidate_ap.py); no build/artifact
`TO_PIN_*` value remains. The private live-FDT identity is now pinned as
52,655 bytes with SHA-256
`7b00d5eee94307d9f78e48ea0d3aeaf7081e54ffae98e89168596f6ee4e4d6a7`.

## Results

Build, compile-audit, assembly, and installation evidence is preserved in
[`results/candidate-ap-build-install-20260724.txt`](results/candidate-ap-build-install-20260724.txt).
The sanitized terminal hardware result is
[`results/candidate-ap-hardware-20260724.txt`](results/candidate-ap-hardware-20260724.txt).

- Two main kernel packages and two independently assembled 18-member artifacts
  reproduced byte-for-byte and mode-for-mode.
- The separate 242-member PM package compiled and linked the ordered
  provider/consumer sleep callbacks. It was never assembled, installed, or
  booted; an actual builder invocation rejected it with exit status 2 and left
  its output directory empty.
- All focused local suites passed: 27 DT mutations, 16 package/source tests,
  32 runtime tests, 13 live-FDT semantic tests, 20 live-FDT acquisition tests,
  40 native-reboot mutations, one mocked exact native-reboot workflow, one
  mocked post-return workflow with six negative return/readback cases, and 6
  installer tests.
- The guarded installer resolved live GPT logical `boot2` to the inactive,
  unmounted 16 MiB partition, required exact AO predecessor
  `3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb`,
  preserved a private mode-0600 full backup, wrote only `boot2`, synced and
  flushed, and matched full remote and independent local readbacks to the
  pinned AP padded identity.
- The installer did not reboot. Gemian was then shut down cleanly for the
  owner-controlled physical `boot2` selection.
- The 52,655-byte private post-LK FDT passed the exact 37-entry LK allowlist:
  10 nodes added, 2 removed, 23 properties added to existing nodes, and 2
  changed. Header reservations and boot CPU were unchanged; the handoff node,
  access-controller link, and childless I2C6 enable survived exactly, with no
  DA9214, A72-power, observer, or legacy-DVFSP node.
- Runtime reached the 45-second handoff check, one `ready` supplier grant, and
  one held sample with I2C_APPM and AP_DMA ungated. I2C_APPM then regated in
  all 32 cleanup samples, while AP_DMA was valid but ungated in all 32. The
  provider faulted with `consumer-cleanup-validation-failed`; I2C6 returned
  `-EIO`, remained unbound, and published no adapter, client, or regulator.
  Transfer, DMA-start, nonzero-START, IRQ, suspend/resume, DA9214, regulator,
  and A72 counters remained zero.
- CPU0–7 stayed online and advanced, CPU8/9 remained offline, and the inherited
  framebuffer, keyboard driver/keymap path, USB service, and native reboot path
  passed. No physical key was exercised in this run.
  The owner reported that the visible console came live only after a long,
  roughly 20-second delay. The instrumented timeline is more precise:
  simplefb registered at 1.437 seconds, the provider reached its late sample
  at 48.130 seconds, `/init` started at 48.143 seconds, and tty1/keymap became
  ready at 48.266 seconds. The provider's asynchronous probe waits for the
  45-second terminal check, so kernel pre-init asynchronous synchronization
  delayed userspace; the owner's estimate is not treated as a stopwatch value.
- One exact-runtime-bound native `/bin/reboot` request closed the USB
  connection and produced two stable exact-MAC absence observations. Gemian
  returned with a changed, stable boot ID. Live GPT again resolved inactive,
  unmounted logical `boot2`, whose one full read-only checksum still matched
  exact AP. No recovery write was required.

Candidate AP is a structured `FAIL`, not I2C6 support. The fail-closed
dependency prevented a transaction and preserved recovery, but AP's requirement
that shared AP_DMA become gated after the I2C6 clock hold is not satisfied.
Do not repeat this exact artifact. First identify the existing AP_DMA owner and
replace the absolute-gated cleanup assumption with an independently reviewable,
baseline-preserving ownership oracle.

## Reversibility

The experiment preserves exact AO as the required predecessor and a private
full `boot2` backup before the AP install. Native reboot returned the unit to
known-good Gemian without a restore; a changed boot ID and one full read-only
post-return checksum verified that exact AP remains on inactive logical
`boot2`. No tooling in this directory targets primary `boot`, `boot3`,
preloader, NVRAM, GPT, or a whole device.
