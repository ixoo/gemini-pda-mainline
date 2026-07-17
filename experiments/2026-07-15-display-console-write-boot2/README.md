# Experiment: write the LK framebuffer-console candidate to boot2

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-15-display-console-write-boot2` |
| Status | `completed` for synchronized write and full readback; runtime boot not attempted |
| Subsystem | Boot image handoff |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-15 |

## Target and safety

- Target device node: `/dev/mmcblk0p30`
- GPT logical name: `boot2`
- Target size: 16,777,216 bytes (16 MiB; 32,768 sectors)
- Candidate package: `linux-7.1.3-gemini-b885d52ffc58`
- Candidate experiment: [LK framebuffer console recovery](../2026-07-15-display-console-recovery/README.md)
- Saved boot2 backup: `artifacts/device-partitions/20260715T020041Z/mmcblk0p30-boot2.img`
- Saved backup SHA-256: `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`

Only `boot2` was targeted. The preloader, RPMB, NVRAM, GPT, primary boot
partitions, and all other MMC partitions were not touched. The write used
`sudo dd` with `bs=4M,conv=fsync`, followed by `sync`; the temporary transfer
file was removed after verification. The device was not rebooted.

## Candidate and verification

The unpadded candidate was 15,724,544 bytes with SHA-256
`a70e8967b69e187e6643a4c2c43f7d9071a3dea441ccd99171c346ac26f2e4f8`. It was
zero-extended to the exact 16 MiB target size. The padded write image and the
complete raw readback of `/dev/mmcblk0p30` both have SHA-256:

```text
0e168671b31b0c754d560f9c4437870fd72399ef92c9913b7fd466104b09a220
```

## Conclusion and limits

The boot2 write is **confirmed** byte-for-byte. This proves only that the
partition contains the requested candidate; LK acceptance, display handoff,
Linux boot, and recovery behavior remain untested. Keep the saved boot2 image
available for restoration before any runtime test.
