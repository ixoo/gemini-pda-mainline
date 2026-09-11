# Native export container

The [constructor](build-export-container.py) packages the verified 46-patch
kernel and [compact export filesystem](STARTUP_ASSEMBLY.md#compact-export-filesystem)
using the native Android-v0 contract. The [receipt](results/export-container.json)
records completed offline checks. No deployment or physical session is selected.

## Preserve the native header

The native kernel uses load address `0x40080000`, ARM64 text offset `0x80000`
and flags zero. These match the pinned
[native assembler](../2026-08-02-gemian-a72-bounded-observer-boot/scripts/assemble.py)
used by the earlier [recovery-only result](../2026-08-02-a72-recovery-only-discriminator/README.md).
The generic mainline constructor's different address and flags requirements do
not apply to this native kernel. No kernel header bytes are patched to satisfy
that different contract.

The constructor first uses the pinned native assembler to verify the retained
reference image, original ramdisk, addresses, layout and selected kernel. It
then substitutes the new filesystem, its size, startup command line and Android
payload ID. It preserves the native addresses and one appended DTB. Required
arguments are `rdinit=/init`, `panic=0`, `cpuidle.off=1`,
`ramoops.pmsg_capture=1` and the exact session's `wifi_cycle` UUID, after the
existing boot-selection and log-buffer arguments.

Run in the RE VM with independently verified private filesystem/session hashes:

```sh
python3 build-export-container.py --active-boot RETAINED_REFERENCE \
  --kernel-field VERIFIED_KERNEL --filesystem VERIFIED_FILESYSTEM \
  --filesystem-sha256 EXPECTED_FILESYSTEM_SHA256 --session VERIFIED_SESSION \
  --session-sha256 EXPECTED_SESSION_SHA256 --output NEW_PRIVATE_DIRECTORY
```

The filesystem's embedded session must match exactly. The session must select
export, pin the current startup sources, compact runtime and selected kernel
inputs. This composition check supplements the filesystem assembly validation;
it is not a general verifier for arbitrary initramfs contents. Output is private
and exclusive; an incomplete directory from an I/O failure is not a certified
package. The checksum inventory covers both images and their private receipt.

## Observed checks and remaining admission

The raw container is 16,295,936 bytes and its zero-padded form is 16,777,216 bytes.
Repeated construction produced identical images. An independent parse verified
the native fields, exact payloads, Android SHA-1 ID, permitted header changes
and all inter-payload/final padding. Seventeen serialized-image mutations were
rejected; six construction refusals covered changed reference/kernel, cycle
action, mismatched embedded session, changed kernel inputs and an oversized
filesystem. The appended DTB contains the exact split capture reservations and
empty PMSG `no-map` property. Package checksums passed after private export.

The first constructor attempt used a `./` prefix absent from this archive's
member names and refused before creating output. The corrected exact member
lookup passed. No device action occurred during construction or validation.

Startup parks after export or refusal and provides no recovery command channel.
The [physical-key prerequisite](EXPORT_RECOVERY.md) now specifies the next
owner-confirmed check on known-good Gemian.
The [single export session](EXPORT_SESSION.md) defines the host attribution,
request budget and result boundary once that prerequisite passes.
Resolve the recovery path for both cases before guarded deployment, including
owner confirmation before any restart. The effective loader arguments and DT,
native PID1 mounts, actual USB enumeration/transfer and changed-boot recovery
still require the admitted physical session. This container supplies no radio,
watchdog-takeover or clearing approval.
