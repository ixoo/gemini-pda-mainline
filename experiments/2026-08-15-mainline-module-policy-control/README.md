# Experiment: current-mainline module-policy serviceability control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mainline-module-policy-control` |
| Status | exact candidate validated offline; deployment pending |
| Subsystem | kernel configuration, boot serviceability, DA921x read-only provider |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-15 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline pre-transport localization |

## Question or hypothesis

Did omission of the historically serviceable `CONFIG_MODULES=y` policy turn
unrelated defconfig modules into built-in drivers and cause the current
provider-only image to fail before USB and retained pstore?

The control restores only the top-level module policy plus a unique release.
The DA921x driver and provider remain built in and read-only. The external
serviceability initramfs contains no modules or loader path.

## Provenance and environment

- Failed parent profile: `da921x-resource-only-provider` at exact Buildbox
  commit `1ab09cd9ef39a9c99c82e639dcbc15cb6040c74c`.
- Last serviceable mainline comparison: Stage 27
  `7.1.3-gemini-da921x-life27`, exact source commit
  `e0fc95ff0686e6989fe7a38ef40d01c34f50f463`, 136 patches.
- Current parent: Linux 7.1.3, 267 patches, observer disabled.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

This is configuration-only. `CONFIG_MODULES=y` preserves defconfig `m`
selections as modules instead of promoting them to built-in. The retained
2,073,441-byte initramfs is module-free and cannot load them. The DA921x
provider remains built in with no setter or register-data write helper. No DT,
ramdisk, LK address, command line, regulator operation, transition owner, or
CPU8/CPU9 admission change is introduced.

## Associated code

- [`../../configs/gemini-da921x-provider-modules-control.fragment`](../../configs/gemini-da921x-provider-modules-control.fragment):
  exact two-setting control delta.
- [`scripts/validate.py`](scripts/validate.py): exact parent-extension and
  safety validation.
- [`scripts/test-validate.py`](scripts/test-validate.py): six negative
  mutations.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): source-pinned,
  deterministic Android-v0/LK builder.
- [`scripts/test-candidate.py`](scripts/test-candidate.py): independent
  container parser and structural-mutation validator.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): exact live-GPT boot2
  installer with full readback and shutdown.
- [`scripts/remote-runtime-probe.sh`](scripts/remote-runtime-probe.sh),
  [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh), and
  [`scripts/validate-runtime.py`](scripts/validate-runtime.py): bounded
  read-only USB/netcat observation and frozen classifier.
- [`results/baseline-localization-20260815.txt`](results/baseline-localization-20260815.txt):
  offline Stage-27/current comparison.

## Procedure

1. Compare the exact failed current control with the last serviceable mainline
   Stage-27 container and configuration.
2. Confirm the initramfs, LK addresses/command line, pstore configuration,
   ramoops DT region, and ramoops-before-provider initcall order.
3. Add one profile that exactly extends the failed provider-only profile with
   the two-setting control fragment.
4. Validate all manifest series, the exact profile delta, syntax, and negative
   mutations; commit and push with a clean worktree.
5. Build only with `./scripts/build-kernel --backend buildbox` and fetch only
   its validated package.
6. Compare the resolved control configuration and container before deciding
   whether one boot is justified.
7. Freeze the exact candidate, hypothesis, decision map, guarded installer,
   and one-hour collector; commit and push before device action.
8. Install only to live-GPT logical boot2, require a full readback, shut Gemian
   down, and arm the collector before one owner-selected boot.

## Observations

The failed current control and serviceable Stage 27 use the exact same
serviceability ramdisk and Android-v0/LK addresses, page size, and command line.
Both enable printk, pstore, pstore console, and the same ramoops initcall before
the DA921x driver initcall. Their decompiled ramoops node is exact at
`0x44410000` with the same `0xe0000` extent and zone sizes.

The first broad configuration boundary is module policy. Stage 27 explicitly
restored `CONFIG_MODULES=y`; the failed current parent inherits
`# CONFIG_MODULES is not set`. The full resolved configs have 302 changed
addition/removal lines, including many defconfig drivers changing from `m` to
`y`. The current compressed kernel is 892,923 bytes larger and its decompressed
Image is 1,816,576 bytes larger. The exact comparison is recorded in the
[baseline localization receipt](results/baseline-localization-20260815.txt).

The new profile is the exact failed parent plus one final fragment. That
fragment selects `CONFIG_MODULES=y` and the attributable local version
`-gemini-da921x-modctl`; it does not reuse the historical fragment's command
line or DA921x module setting. Static validation and all six mutations pass.

Buildbox completed exact pushed commit
`09ba93dbe1aa462795f1a1f4f0e82e31f5392989`. The fetched package passes its
complete manifest. The Gemini DTB and 267-patch series are unchanged from the
failed provider-only parent; the provider remains built in and the observer
remains disabled. The build produced no external module package, matching the
module-free initramfs. The compressed Image is 881,288 bytes smaller than the
failed parent, the decompressed Image is 1,818,624 bytes smaller, and its
12,517,376-byte arm64 effective size is exact to serviceable Stage 27. The
compressed image is only 11,635 bytes larger than Stage 27 and the decompressed
Image is 2,048 bytes smaller. See the
[Buildbox receipt](results/buildbox-20260815.txt).

Independent assemblies produced the exact 6,881,280-byte raw container
`782850c4854e9454fc5c0ac22243b25233f7b4e6ebb5cecdf4d2872fd45ae040`
and exact 16 MiB boot2 image
`044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff`.
Both assembly paths are byte-identical, all 32 LK gates pass, and the
independent parser rejects all six structural mutations. Runtime tools pass
positive and six negative classifications, static no-write checks, syntax,
ShellCheck, the guarded no-backup/full-readback/shutdown contract, and a
one-hour collector window. See the
[offline review](results/offline-validation-20260815.txt).

## Analysis

The unchanged pstore map, initcall order, ramdisk, and LK layout do not isolate
an obvious container or ramoops-address defect. Module policy is earlier and
broader than the provider: disabling module support converts unrelated module
selections into built-ins, changes link/initcall inventory, and materially
inflates the image. Restoring it is a smaller and more informative discriminator
than immediately adding new checkpoint code.

The resulting image-size collapse is the predicted mechanical effect and
makes one boot decision-changing. It does not prove that built-in expansion
caused the pre-transport failures; only exact runtime identity or retained
candidate evidence can do that. The unchanged DTB, ramdisk, LK layout,
provider/observer policy, and CPU gate make serviceability the single runtime
discriminator.

## Conclusion

The exact candidate is accepted for one boot2 deployment and one runtime boot.
No hardware-support or provider-runtime claim exists yet. Register writes,
transition ownership, and CPU8/CPU9 admission remain closed.

## Follow-up

Follow the ordered action in [`docs/ROADMAP.md`](../../docs/ROADMAP.md): commit
and push the frozen candidate/tooling record, install the exact image to
live-GPT logical boot2, shut Gemian down, arm the collector, and observe one
owner-selected boot. Do not repeat the candidate unchanged.
