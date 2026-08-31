# Gemini boot graphics

## Scope

This document records the durable ownership and format boundary for visible
startup graphics on the named Gemini PDA x27. It covers the retained Planet LK
`logo` partition and the stock Gemian initramfs splash. It does not claim that a
modified image has been accepted by hardware.

The detailed read-only investigation, rejected dimension interpretations, and
sanitized metadata are in the
[`2026-08-31-boot-graphics-recovery`](../../experiments/2026-08-31-boot-graphics-recovery/README.md)
experiment.

## Boot-stage ownership

| Stage | Graphic owner | Durable location | Confidence |
| --- | --- | --- | --- |
| Retained LK startup | MediaTek 57-entry logo container | logical `logo`; slots 0 (`uboot`) and 38 (`kernel`) | `confirmed` format and identities; exact on-screen transition timing not instrumented |
| LK charging and warning UI | Same logo container | logical `logo`; slots 1--37 and 39--56 | `confirmed` |
| Gemian early userspace | Yamui in the gzip initramfs | source `/usr/share/initramfs-tools/res/images/debian.png`; embedded `/res/images/debian.png` | `confirmed` |
| Plymouth | Not active in the captured Gemian boot path | generic theme assets exist only as `desktop-base` data | `observed` |

These are independent layers. Replacing an LK splash cannot change the later
Debian swirl, and changing the rootfs PNG alone cannot change the copy already
embedded in an existing initramfs.

## Retained LK logo format

- The captured `logo` partition is 8 MiB. The active image occupies 5,447,562
  bytes and the rest is zero padding.
- A 512-byte MediaTek header (`0x58881688`, image name `logo`, extended magic
  `0x58891689`) precedes an inner 57-entry table.
- The table stores a count, total size, and stream offsets. It stores no width,
  height, stride, or pixel-format metadata.
- Every entry is a separate zlib stream containing tightly packed BGRA8888
  pixels. Each row stride is `width * 4`; there is no row padding.
- The zlib Adler-32 trailers validate all captured streams. The container has
  no observed whole-file CRC, digest, or appended signature.

The exact public-source resource order is pinned to Planet Gemini Android 8 LK
commit
[`f4988d74bb70a0a15d7f362f412afba7e7fcda46`](https://github.com/dguidipc/gemini-lk-android8/tree/f4988d74bb70a0a15d7f362f412afba7e7fcda46),
whose Gemini target selects the `fhd` assets and Pump Express additions.

## Complete geometry map

| Slots | Content | Geometry |
| --- | --- | ---: |
| 0 | first-stage Planet/Tux (`uboot`) | 2160x1080 |
| 1 | battery screen | 1920x1080 |
| 2--3 | low-battery and charger-overvoltage screens | 2160x1080 |
| 4--13 | normal digits 0--9 | 84x121 |
| 14 | normal percent sign | 108x121 |
| 15--24 | battery animation 01--10 | 304x52 |
| 25--34 | ten-percent animation 01--10 | 2160x1080 |
| 35 | battery background | 2160x1080 |
| 36 | battery fill | 16x19 |
| 37 | full-battery screen | 2160x1080 |
| 38 | Planet/Tux `kernel` splash | 2160x1080 |
| 39 | fast-charging full screen | 2160x1080 |
| 40--45 | fast-charging animation 01--06 | 2160x1080 |
| 46--55 | fast-charging digits 0--9 | 108x192 |
| 56 | fast-charging percent sign | 108x192 |

The format's missing dimensions create genuine ambiguities: 2160x1080 and
1080x2160 have the same byte count, as do 108x192 and 144x144. Geometry must
therefore remain tied to the source asset identity, not inferred from size
alone.

## Integrity and authentication

Adler-32 is part of each zlib stream and is regenerated during compression; it
is corruption detection, not a signing requirement. A structurally valid
container still has to update all affected offsets, both size fields, and the
partition padding boundary.

The retained LK has a conditional security-library call for the `logo`
partition. Its public policy tables require logo verification only when secure
boot is enabled and the bootloader is locked. The named device's earlier
download session reported SBC disabled, and the stock image has no appended
authentication trailer. Unsigned replacement acceptance is therefore
`inferred`, not `confirmed`: no changed logo has been boot-tested.

## Gemian Yamui logo

The Debian swirl shown after Linux starts is a 205x256, non-interlaced RGB PNG:

```text
rootfs source:  /usr/share/initramfs-tools/res/images/debian.png
initramfs copy: /res/images/debian.png
renderer:       /bin/yamui
boot script:    /scripts/geminipda
```

The Halium initramfs hook copies the PNG and Yamui into the ramdisk. The
`geminipda` script displays asset name `debian` while checking and mounting the
Gemian root filesystem. The source and captured-boot copies were byte-identical
in the 2026-08-31 investigation.

This is not the generic Plymouth artwork also present under
`/usr/share/plymouth/themes/`; Plymouth was not installed or selected in the
captured boot path.

## Safety and modification boundary

No ordinary project authorization covers writes to logical `logo` or primary
`boot`. Both remain outside the standing `boot2` deployment path. The raw
partition, decoded proprietary artwork, and root/boot captures remain private
below ignored storage and must not be committed.

Any future owner-directed artifact must preserve the slot order, corrected
geometry, BGRA8888 packing, exact zlib boundaries, rebuilt offset/size fields,
and 8 MiB capacity. A Gemian-logo change additionally requires rebuilding the
initramfs and Android-v0 boot container; editing only the rootfs source is
insufficient. These are format constraints, not authorization to build or
flash an image.

## Unresolved questions

- No modified `logo` container has completed an offline no-op reproduction or
  a recovery-backed hardware acceptance test.
- LK's source names slots 0 and 38 `uboot` and `kernel`; their exact visible
  transition timing has not been instrumented.
- Android boot animations or later desktop/login graphics were not part of
  this investigation.

## Evidence index

- [Boot-graphics recovery experiment](../../experiments/2026-08-31-boot-graphics-recovery/README.md)
- [Earlier offline boot-authentication surface check](../../experiments/2026-07-15-display-console-write/results/boot-authentication-check-20260715.txt)
- [Pinned Gemini LK resource order](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/dev/logo/rules.mk)
- [Pinned Gemini LK target configuration](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/project/k97v1_64_bsp.mk)
