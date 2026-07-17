# Experiment: write the LK framebuffer-console candidate to boot3

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-15-display-console-write` |
| Status | `inconclusive` for runtime; synchronized write/readback completed, then an owner-reported boot loop with no display |
| Subsystem | Boot image handoff |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-15 |

## Question or hypothesis

Can the validated LK framebuffer-console candidate be written completely and
reversibly to the explicitly authorized non-primary `boot3` partition?

## Provenance and safety

- Target device node: `/dev/mmcblk0p31`
- GPT logical name: `boot3`
- Target size: 16,777,216 bytes (16 MiB; 32,768 sectors)
- Candidate package: `linux-7.1.3-gemini-b885d52ffc58`
- Candidate experiment: [LK framebuffer console recovery](../2026-07-15-display-console-recovery/README.md)
- Original partition backup:
  `artifacts/device-partitions/20260715T020041Z/mmcblk0p31-boot3.img`
- Original backup SHA-256:
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`

Only `boot3` was targeted. The preloader, RPMB, NVRAM, GPT, primary boot
partitions, and all other MMC partitions were not touched. The write used
`sudo dd` with `bs=4M,conv=fsync`, followed by `sync`; temporary transfer files
were removed after verification. The device was not rebooted.

## Procedure and observations

The unpadded candidate was 15,724,544 bytes and had SHA-256
`a70e8967b69e187e6643a4c2c43f7d9071a3dea441ccd99171c346ac26f2e4f8`. It was
zero-extended to the exact partition size before the final write. The padded
write image SHA-256 was:

```text
0e168671b31b0c754d560f9c4437870fd72399ef92c9913b7fd466104b09a220
```

The full raw readback of `/dev/mmcblk0p31` produced the same digest and the
same 16 MiB size. An earlier payload-only write was immediately superseded by
the explicit full-size write; no reboot occurred between them.

An independent read through MediaTek preloader/DA using mtkclient 2.1.4 also
returned exactly 16 MiB with the same digest and an `ANDROID!` boot-image
header. See [the sanitized mtkclient result](results/mtkclient-readback-boot3-20260715.txt).

Afterward, the owner reported an attempt to select the candidate that produced
a boot loop with no visible display, and later noted that it is uncertain
whether the intended slot was selected or the candidate reached LK or Linux
because even the loader splash was absent. No UART or framebuffer log was
available, so the exact reset point is unknown.
The sanitized runtime observation is recorded in
[runtime-boot-loop-20260715.txt](results/runtime-boot-loop-20260715.txt).

The owner then restored the original image on the primary `boot` partition and
reported both the initial loader splash and the subsequent Gemian splash. This
confirms the stock primary display/boot path is healthy. It does not prove that
a candidate written only to `boot2` or `boot3` was selected by the normal boot
flow; see [stock-boot-splash-recovery-20260715.txt](results/stock-boot-splash-recovery-20260715.txt).

An offline check found no standard AVB footer, vbmeta partition, or nonzero
legacy Android boot-image id/hash field in either the original image or the
candidate. However, both captured LK binaries contain MediaTek image-auth and
verified-boot signature code, and the live vendor handoff reports green verified
boot with verity enforcing. This leaves authentication as an unresolved
possibility, not the demonstrated cause; see
[the authentication check](results/boot-authentication-check-20260715.txt).
The later arm64-header analysis found
a concrete independent defect: this modern Image used legacy
`kernel_addr=0x40080000` instead of the 2 MiB-aligned modern placement at
`0x40200000`; see the
[updated boot contract](../2026-07-12-boot-contract-recovery/README.md).

## Analysis and conclusion

The write is **confirmed** for this device and target: the complete partition
readback matches the padded candidate byte-for-byte. Runtime support is
**inconclusive/failed for this candidate**: a boot loop with no display was
reported, but the selected slot and execution stage were not established. The
candidate's now-known arm64 placement error is sufficient to retire it, while
the observation alone cannot distinguish non-selection, authentication, LK
parser failure, early kernel failure, watchdog reset, or initramfs handoff.

## Follow-up

Restore the saved boot3 backup before further candidate changes. Do not reuse
this artifact. The next candidate should retain the Android-v0
gzip+appended-DTB format, use `kernel_addr=0x40200000` for the current
`text_offset=0` Image, validate the pre-jump LK DT contract, and keep the
framebuffer handoff optional. Add an early diagnostic marker and a minimal
recovery path so a no-UART failure can be distinguished from a display failure.
