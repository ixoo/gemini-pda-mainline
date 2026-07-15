# Experiment: Gemian hardware-userspace inventory

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-gemian-hardware-userspace-inventory` |
| Status | `completed` |
| Subsystem | Vendor userspace and Linux/Android compatibility boundary |
| Device image | Planet `Gemini-7.1-Planet-08102018-V1` |
| Date | 2026-07-11 |
| Method | Read-only SSH filesystem, ELF, package, process, and service inspection |

## Question

Which installed executables, shared libraries, HALs, and native Gemian packages
are hardware-specific, and what role do they play in the working vendor stack?

## Safety and licensing

The investigation read file metadata, SHA-256 hashes, ELF dynamic dependency
tables, selected non-unique build properties, package metadata, service files,
and process names. It did not execute vendor diagnostic tools, attach a debugger,
change services, read NVRAM, or copy binaries/libraries from the device.

The files have unknown or proprietary redistribution terms. Only independently
written analysis and cryptographic identifiers are stored in Git.

## Associated code

[`scripts/inventory.sh`](scripts/inventory.sh) reproduces the sanitized read-only
inventory. Run it on the device or over SSH stdin. It intentionally limits
properties and process output to avoid unique identifiers and user command
lines.

The repository-level
[`scripts/extract-device-userspace`](../../scripts/extract-device-userspace)
uses [`scripts/list-extract-files.sh`](scripts/list-extract-files.sh) to create a
private, checksummed copy beneath Git-ignored `artifacts/`. Extraction is
explicit because the payload has unknown or proprietary redistribution terms.

## Observations

- Android identifies the image as Planet Gemini 4G, Android 7.1.1, MT6797 S01.
- 29 MT6797 HAL paths were present across 32-bit and 64-bit ABIs; two Vulkan
  paths point to the Mali GLES libraries.
- Hardware domains covered audio, camera, GNSS, graphics, lights, memtrack,
  power, sensors, sound-trigger, thermal, consumer IR, and Vulkan.
- The graphics path combines proprietary Mali/Android HALs with libhybris,
  drihybris, and an Xorg hwcomposer driver.
- Audio uses PulseAudio droid modules; telephony uses oFono/RIL bridges; Wi-Fi
  policy includes a WMT-specific ConnMan plugin.
- MediaTek modem, WMT, AGPS, NVRAM, factory, logger, and AT-command programs are
  installed. Their presence is not evidence that they are required for a
  maintainable mainline system.
- The broad `gemian-modular-kernel` module tree is generic; Gemini platform
  drivers appear predominantly built into the vendor kernel.

Exact regular-file HAL hashes are in
[`results/hal-manifest.sha256`](results/hal-manifest.sha256). Vulkan symlinks are
documented separately because their contents are the Mali library targets.

The owner-authorized vendor-only extraction was rerun on 2026-07-14 after SSH
reconnect. Its 621-entry private corpus, manifest verification, and bounded
transfer behavior are recorded in
[`results/vendor-only-extraction-20260714.txt`](results/vendor-only-extraction-20260714.txt).
The corpus remains below the Git-ignored `artifacts/` tree.

## Conclusion

`confirmed` that Gemian depends on a substantial Android vendor compatibility
stack, not just firmware plus standard Linux interfaces. The durable subsystem
map and migration implications are in
[Gemian hardware-specific userspace](../../docs/hardware/vendor-userspace.md).
No support-matrix runtime state changes because this describes the historical
vendor environment, not current mainline.
