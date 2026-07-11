# Safety and recovery

Mainline bring-up can make a device unbootable and can cause data loss or hardware stress. This document sets project policy; it is not a guarantee that an experiment is safe.

## Before the first write

- Identify the exact Gemini hardware variant.
- Preserve the original firmware and matching scatter/partition description.
- Back up every readable device-specific partition using a method already proven on that variant.
- Verify that backups are non-empty, record checksums, and store them offline.
- Confirm an independently bootable stock or recovery path.
- Confirm UART access before relying on a kernel that has no display or USB.
- Disconnect or back up removable storage and user data.

Device-specific backups may contain IMEI, serial numbers, MAC addresses, keys, and calibration data. Keep them private and encrypted. Never attach them to an issue.

## Protected areas

Normal project procedures must never write:

- preloader or BootROM-adjacent firmware;
- NVRAM or calibration partitions;
- GPT/partition-table sectors;
- secure-world or modem firmware;
- the primary known-good Android/recovery boot slot;
- a whole-disk device when a named boot partition is intended.

Any future proposal to touch one of these areas requires a separate design and explicit maintainer review. It must not be hidden inside a build or flash helper.

## Development boot policy

- Use a non-primary boot choice reserved for development.
- Package only the kernel, DTB, and initramfs needed for the experiment.
- Print and confirm the resolved target before a write.
- Read back and checksum written data when the toolchain supports it.
- Keep power stable during writes.
- Change one boot-critical variable at a time.

## Clocks, regulators, and thermals

Incorrect values can corrupt memory, overheat components, or damage hardware.

- Begin with conservative, known-initialized settings.
- Do not enable DVFS until fixed-frequency boot is stable.
- Do not guess voltage tables or thermal limits.
- Treat vendor values as evidence requiring validation, not as permission to overclock.
- Keep an independent way to remove power during early regulator/thermal tests.

## Publishing logs

Before uploading, remove:

- IMEI and modem identifiers;
- serial numbers and MAC addresses;
- Wi-Fi credentials;
- filesystem UUIDs when they identify personal media;
- keys, tokens, crash dumps containing user memory, and partition contents.

State what was redacted so another contributor does not mistake missing fields for device behavior.

## Stop conditions

Stop testing and return to a known-good boot path after unexpected heat, battery swelling, charging anomalies, repeated filesystem errors, memory corruption, watchdog loops, or any change in recovery behavior. Open a safety-labeled issue with non-sensitive evidence before repeating the test.
