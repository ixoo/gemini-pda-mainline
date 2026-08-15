# Experiment: current-mainline module-policy serviceability control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mainline-module-policy-control` |
| Status | static input validated; Buildbox pending |
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

## Analysis

The unchanged pstore map, initcall order, ramdisk, and LK layout do not isolate
an obvious container or ramoops-address defect. Module policy is earlier and
broader than the provider: disabling module support converts unrelated module
selections into built-ins, changes link/initcall inventory, and materially
inflates the image. Restoring it is a smaller and more informative discriminator
than immediately adding new checkpoint code.

## Conclusion

Static input is accepted for one Buildbox-only matched build. No boot candidate
or runtime claim exists yet.

## Follow-up

Follow the ordered action in [`docs/ROADMAP.md`](../../docs/ROADMAP.md): build
and independently compare this profile. Only an exact validated container may
advance to one device boot.
