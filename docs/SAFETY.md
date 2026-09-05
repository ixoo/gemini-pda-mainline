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

### Device identity before a boot2 write

New and active installers must use the read-only
[`boot2-device-guard.sh`](../scripts/boot2-device-guard.sh) in their remote
deployment shell after resolving `boot2` from the live GPT, and again
immediately before writing. Historical closed experiment installers remain
immutable evidence and must not be reused without this integration.

Source the reviewed library or embed the bytes between its explicit library
markers, pinning the complete source digest in the candidate's installer
validation. Call `boot2_device_guard "$target" "$major_minor"` with the exact
GPT-selected device and its independently obtained, validated live device
number. The guard verifies the block node against sysfs and rejects target
mounts by kernel major:minor, regardless of `/dev/root`, UUID aliases, or bind
mount source text. It derives the actual root from the unique `/` mountinfo
entry and verifies its live sysfs/device-node identity; no root partition number
is assumed. An absent, pseudo-device, malformed, or unresolved root is a refusal.
It verifies that the target is a partition and also rejects use of its whole
parent disk. Holders, target or parent swap aliases, unsupported swap identities,
and a caller outside the init mount namespace are refusals. Missing observations
never count as an inactive device.

The successful output records `target_device`, `target_major_minor`,
`root_device`, and `root_major_minor`. Preserve these in deployment evidence;
pass the observed root number as the optional third argument when pinning the
root across deployment stages. Refuse an empty or duplicate evidence field.
The guard has no write action and requires explicit `--check` when run directly.
Its hardware-free tests are in
[`boot2-device-guard-test.py`](../scripts/boot2-device-guard-test.py).

This metadata check supplements the existing exact target, GPT label, parent,
size, writable-state, power, candidate, checksum, and recovery gates. It does
not lock mounts, inspect other mount namespaces, authorize a write, or replace
full readback. Deployment requires a quiescent known-good OS and the complete
guarded installer; a standalone passing check is not an installation receipt.
The fixture tests do not establish behavior on the named hardware.

## Standing retained-RAM diagnostic authorization

The device owner gives standing authorization for isolated, default-off early
boot diagnostics to write short attributable records only within an existing,
DT-reserved persistent-RAM range when all of the following are true:

- the exact physical range, record bytes, maximum write count, and recovery
  reader are documented and validated before build;
- any pre-DT access has an exact physical fingerprint, proves the required
  exception level and MMU/cache state, preserves the boot ABI, and refuses on
  every mismatch before its first write;
- every writer owns one bounded slot, commits data before metadata, performs a
  full ordered readback, and never clears, repairs, retries, or overwrites a
  nonempty slot;
- the diagnostic performs no storage, firmware, I2C, regulator, clock, CPU
  admission, timer, watchdog, reset, or power operation at runtime; and
- Buildbox provenance, guarded live-GPT `boot2` deployment, full-partition
  readback, one physical selection, known-good recovery, and clean shutdown
  remain mandatory.

This standing authorization removes a repeated approval prompt; it does not
relax any gate above and does not cover a new physical range or effect class.
Primary `boot`, `boot3`, preloader, NVRAM, GPT, firmware, and whole-device
writes remain outside it and require separate review.

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
- personal absolute host paths that expose usernames; use repository-relative
  paths or neutral role placeholders in published commands.

State what was redacted so another contributor does not mistake missing fields for device behavior.

## Stop conditions

Stop testing and return to a known-good boot path after unexpected heat, battery swelling, charging anomalies, repeated filesystem errors, memory corruption, watchdog loops, or any change in recovery behavior. Open a safety-labeled issue with non-sensitive evidence before repeating the test.
