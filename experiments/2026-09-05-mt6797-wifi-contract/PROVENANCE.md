# Retained WIFI storage and producer contract

This offline slice follows `ca4e114d697b03e5b7b846d3f1365050f1620c3c` and
the [512-byte consumer contract](CALIBRATION.md). It identifies the retained
filesystem file, its storage envelope and a producer implementation family.
**The actual restoration history and board/firmware applicability remain
unproved.** There is no active radio candidate or new hardware support claim.

Only independently written interface facts, a pure inspector and a bounded
sanitized receipt are published. Record contents, identifiers, calibration,
private record/image/library hashes, compiled defaults and binary listings
remain private. No proprietary implementation is imported or executed.

## Evidence and attribution boundaries

The device scope is the named project's Gemini described in the
[experiment record](README.md#record). Three inputs have different identities:

| Input | Verification and use | Limit |
| --- | --- | --- |
| Existing [partition backup](../2026-07-14-mmc-partition-backup/README.md), capture `20260715T020041Z` | Private manifest integrity, successful capture status, full image hashes, exact sizes and restricted host permissions checked for the five calibration-related images and the Linux image | Non-atomic capture; file presence is historical, not necessarily current or coherent |
| Retained `gemian-2019` userspace corpus | Selected ELF files verified against its 696-entry private manifest; static analysis through the [read-only RE environment](../../docs/DEV_VM.md#reverse-engineering) | This is the earlier corpus documented there, not the later 621-entry July extraction; no equality with the installed July producer is claimed |
| Pinned public Gemini/Gemian configuration and selected Planet gen3 source | Public configuration files re-fetched and hashed; consumer identity remains the pin in [CALIBRATION.md](CALIBRATION.md) | Public source selection is not proof of the installed configuration or loaded driver/firmware pair |

Host and VM free space were checked before image inspection. No source tree,
image copy, mount, extraction directory or retained record export was made.
Read-only filesystem tools returned selected bytes into process memory.
No vendor library, daemon, emulator, device or radio operation was invoked.

## Filesystem identity

Read-only `debugfs` inspection of the verified `nvdata` image found the regular
file `/APCFG/APRDEB/WIFI`, with 514 bytes. The separate `WIFI_CUSTOM` file has
six bytes; it is not the selected driver's WIFI input or this inspector's
accepted format. These observations identify files inside a captured
filesystem, not a direct parser for the raw `nvram` partition.

The pinned Gemini init configuration maps `/data/nvram` to `/nvdata` and
declares `/vendor/bin/nvram_daemon`; its fstab mounts the named `nvdata`
partition there. The pinned Gemian LXC fstab independently uses that mount.
Thus the retained relative path agrees with the selected driver's
`/data/nvram/APCFG/APRDEB/WIFI` path **if that configuration was installed and
active**. This is a source-supported mapping, not an observed runtime mount.
[Gemini init](https://github.com/lineage-geminipda/android_device_planet_geminipda/blob/8f7cd432feb3252497497a5259c7e4e326407a4f/rootdir/init.mt6797.rc#L85),
[Gemini fstab](https://github.com/lineage-geminipda/android_device_planet_geminipda/blob/8f7cd432feb3252497497a5259c7e4e326407a4f/rootdir/fstab.mt6797#L11),
[Gemian fstab](https://github.com/gemian/lxc-android/blob/dc9d10409a9bf04d3353969f170bc8aa10d8bdbd/var/lib/lxc/android/fstab.mt6797#L16).

The retained Linux image matched its full backup hash, but `debugfs` 1.47.0
refused to open its filesystem because of a metadata checksum error. The
process returned zero despite this failure; stderr and absence of filesystem
output exposed it. Installed init/fstab queries are therefore **inconclusive**,
not evidence that those files are absent. Checksum verification was not
disabled, and no repair or journal replay was attempted. This slice does not
diagnose whether capture consistency or another cause explains the failure.

## Producer family and storage envelope

The retained `libcustom_nvram.so` registrations associate the WIFI pathname
with one 512-byte logical record and a separate four-byte WIFI_CUSTOM record.
Both ARM32 and AArch64 libraries were inspected. These registration facts
agree with the selected consumer's record size; they do not attribute which
producer wrote the captured file.

Static inspection of `libnvram.so` establishes the following narrow envelope
contract. Trailer calculation, writing and checking matched in both ABIs;
the size classification below was inspected in the AArch64 library. Symbol
names provide the analysis landmarks; no instruction listing or vendor code
is included.

| Boundary | Independent interpretation |
| --- | --- |
| `NVM_CheckFileSize` | Distinguishes a registered payload from a payload with two additional bytes for this single-record type |
| `NVM_ComputeCheckNo` | Starts an eight-bit check at zero; adds payload bytes at even indexes and XORs bytes at odd indexes, retaining the low eight bits; protected-file checking excludes the final two bytes |
| `NVM_SetCheckNo` | Stores marker `0xaa` followed by the check, by appending or replacing the trailer according to its mode |
| `NVM_CheckFile` | Compares both final bytes against that marker/check contract |

This is a userspace **storage envelope**, separate from the 512-byte kernel
record. It does not contradict the earlier finding that the audited kernel
load path defines no record checksum check. WIFI_CUSTOM's different payload
size does not make it interchangeable with WIFI.

The retained daemon is ARM32. Its static calls include NVRAM initialization
and recovery; the corresponding 32-bit library paths include restoration,
default reset, protection and version handling. A read-sounding function
such as `NVM_GetFileDesc` has paths to mutating helpers. These are possible
producer/restoration paths, not proof of the branch taken for this record.
No such API was executed to inspect private inputs.

## Pure inspector and observed result

[`wifi_nvram_storage.py`](scripts/wifi_nvram_storage.py) accepts only an
independently isolated immutable 514-byte WIFI file. It checks the trailer
before passing exactly the first 512 bytes and independent version context
to the existing record inspector. It neither repairs nor returns a payload,
opens a file, accesses hardware, nor authorizes loading or transmission.
The old 512-byte inspector and its historical receipts remain unchanged.

The [sanitized receipt](results/storage-inspection.json) records a matching
envelope and a passing selected-source record-version predicate. Driver
context is the independently pinned `0x0200`/`0` pair, not values inferred
from the file. Firmware context was not supplied. No actual record version,
MAC, country, power value or private digest is emitted in this receipt.

The check is weak: distinct payloads can produce identical results. The
synthetic collision test deliberately demonstrates this. A passing envelope
cannot authenticate a file, distinguish a restored default from factory
calibration, prove RF values suitable for a board, or establish firmware
acceptance. The record's origin is not established by its structure.

| Question | Result |
| --- | --- |
| Is the exact logical WIFI file present in retained storage? | Yes, in the verified `nvdata` image |
| Is there a matching producer implementation and public path mapping? | Yes, as separately attributed static/source evidence |
| Is the captured file structurally compatible with this envelope and the selected host version predicate? | Yes, for these narrow checks |
| Which installed service/version and restoration branch produced it? | Unproved; installed configuration recovery was inconclusive |
| Is it authentic factory calibration for the exact RF board and loaded firmware? | Unproved |
| Does the firmware apply it successfully and enforce valid radio limits? | Unobserved |

The remaining dependency is an attributable record-production history and
exact board/firmware application contract. This result supplies no device
action budget and no permission to initialize the radio. Shared ownership
and recovery requirements remain in [OWNERSHIP.md](OWNERSHIP.md); ordering
remains solely with [the roadmap](../../docs/ROADMAP.md).

## Reproduction and review

Run the 26 new synthetic tests and the unchanged 23 record tests:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_nvram_storage.py
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_nvram.py
```

For authorized private reproduction, verify retained inputs against their
own private manifests before use. Inspect the named filesystem file with a
read-only tool that checks errors as well as exit status. Keep file bytes in
memory and give the pure helper independently known driver context. Emit
only the receipt's fixed allowlist; never attach raw output or private hashes.
Public fixtures do not contain private records or compiled RF defaults.

Independent code review found no actionable defects. Tests cover all
truncated lengths, incorrect trailer bytes, single-byte changes throughout
the payload, parity and overflow, checksum collision, context and delegation
boundaries, privacy, and preservation of the earlier record semantics.
[Validation and scope](results/storage-validation.txt) records the executed
checks and remaining CI-only check. No kernel input changed, so no kernel
build, checkpatch or DT-schema run was required.

Public-source SHA-256 identities (no private input hashes):

| Pinned file above | SHA-256 |
| --- | --- |
| Gemini `rootdir/init.mt6797.rc` | `c9e637be263538b656dd3e1a4abd6f026054db2cb4edbe1ff70f2f047b65533d` |
| Gemini `rootdir/fstab.mt6797` | `6bee3124347fea36cd1d933921b1cfaea0682aa6486d459103b9bcfd7c369127` |
| Gemian `var/lib/lxc/android/fstab.mt6797` | `7a83b99eb01fd8548c72705344888fefa127c84a6d39bceebfbfcb74c1d225e2` |
