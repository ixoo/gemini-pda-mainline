# Experiment: Gemini boot-graphics recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-boot-graphics-recovery` |
| Status | `completed; read-only format and asset-map recovery; no replacement built or flashed` |
| Subsystem | retained LK logo partition and Gemian initramfs splash |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | none |

## Question or hypothesis

Can the early Planet/Tux graphics and the later Debian startup logo be located
and decoded from the retained Gemini software without guessing their geometry,
and does either format contain a checksum or authentication field that would
prevent a future owner-supplied replacement?

The format and location questions are tested here. Acceptance of a modified
image is not: this experiment performs no repack, partition write, or device
boot.

## Provenance and environment

- Private read-only input: the project-wide 8 MiB capture of logical `logo`,
  retained below the ignored `artifacts/device-partitions/` tree. Its sanitized
  identity is recorded in
  [`results/logo-container-analysis-20260831.txt`](results/logo-container-analysis-20260831.txt).
- Gemian inputs: the same private capture set's logical `linux` ext4 image and
  Android-v0 logical `boot` image. No root-filesystem or boot-image content is
  committed.
- Public LK source: Planet Gemini Android 8 LK commit
  [`f4988d74bb70a0a15d7f362f412afba7e7fcda46`](https://github.com/dguidipc/gemini-lk-android8/tree/f4988d74bb70a0a15d7f362f412afba7e7fcda46).
  The Gemini target selects `BOOT_LOGO := fhd`, Pump Express graphics, and a
  270-degree physical rotation in
  [`k97v1_64_bsp.mk`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/project/k97v1_64_bsp.mk).
  The exact resource order comes from
  [`lk/dev/logo/rules.mk`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/dev/logo/rules.mk).
  MediaTek's outer-header field names and sizes are defined in the same pinned
  tree's
  [`partition.h`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/partition.h#L43-L73).
- Earlier authentication evidence:
  [`boot-authentication-check-20260715.txt`](../2026-07-15-display-console-write/results/boot-authentication-check-20260715.txt).
- Forum search boundary: all OESF Gemini sections were searched for `boot
  logo`, `custom logo`, `logo.bin`, `logo partition`, `boot animation`, and
  `splash screen`. The closest public discussions were the unanswered
  [`lk`, `lk2`, and `logo` partition question](https://www.oesf.org/forum/index.php?topic=35797.0),
  a [firmware listing containing `logo_s.bin`](https://www.oesf.org/forum/index.php?topic=35572.0),
  and a [reported distinction between early static and later animated graphics](https://www.oesf.org/forum/index.php?topic=35065.0).
  No Gemini-specific successful replacement recipe was found.
- Host tools: Python 3.14.6 standard library and FFmpeg 8.1.2 for private
  visual checks. VM tools: Binwalk 2.3.4, `initramfs-tools-core` 0.142ubuntu25.8,
  GNU cpio 2.15, and gzip 1.12.
- Kernel, compiler, patch series, and configuration: not applicable. This is an
  offline firmware/userspace investigation.

## Safety assessment

The procedure was read-only. The retained partition captures were not changed.
The Gemian root filesystem was mounted with `ro,noload`, which suppresses ext4
journal replay, and was unmounted after inspection. The Android boot ramdisk
was extracted only below a managed temporary directory and removed afterward.

No device was contacted, no image was assembled, and no partition was written.
In particular, the standing authorization for logical `boot2` does not cover
the primary `logo` or `boot` partitions. Any future write to either remains
outside this experiment and requires its own explicit safety and recovery
review.

## Associated code

- [`scripts/inspect-logo-container.py`](scripts/inspect-logo-container.py) is a
  read-only parser. It validates the outer MediaTek header, the complete
  57-entry offset table, every zlib boundary and Adler-32, the corrected
  BGRA8888 geometry, and the zero-padded partition tail. It deliberately does
  not extract or reproduce artwork.
- [`results/logo-container-analysis-20260831.txt`](results/logo-container-analysis-20260831.txt)
  is the sanitized parser result for the retained logical `logo` capture.
- [`results/gemian-initramfs-logo-analysis-20260831.txt`](results/gemian-initramfs-logo-analysis-20260831.txt)
  records the source and embedded locations of the later Debian logo.
- Private decoded PNGs and contact sheets were used only for visual validation;
  they are not repository artifacts and are not redistribution evidence.

The logo-container check is reproducible from a private capture with:

```sh
python3 experiments/2026-08-31-boot-graphics-recovery/scripts/inspect-logo-container.py \
  artifacts/device-partitions/PRIVATE-CAPTURE/mmcblk0p23-logo.img
```

No privileges or hardware access are required.

## Procedure

1. Search the Gemini forum for an existing successful customization procedure
   and record positive and negative results.
2. Parse the retained `logo` partition's outer MediaTek header and locate the
   inner table at the declared 512-byte payload offset.
3. Inflate each table-bounded zlib stream, initially without assuming image
   dimensions or pixel ordering.
4. Compare plausible 32-bit channel orders visually, then reconcile the
   stream order and raw byte counts with the exact public Gemini LK resource
   list and target configuration.
5. Render all 57 entries privately using the reconciled dimensions. Check the
   suspect slots independently rather than relying on a generic factorization
   of their byte counts.
6. Inspect the outer and inner container boundaries, zlib trailers, captured LK
   authentication call, and pinned public LK security policies.
7. Mount the captured Gemian `linux` filesystem read-only with journal replay
   disabled. Identify the boot UI program, initramfs hook, source artwork, and
   boot script.
8. Parse the captured Android-v0 `boot` image, extract its gzip ramdisk to a
   temporary directory, and compare the embedded artwork with the rootfs
   source by SHA-256.
9. Remove all temporary raw, extracted, and VM-exported inputs. Retain only
   sanitized text metadata and the read-only parser.

## Observations

### MediaTek container

- The captured partition is 8,388,608 bytes. Its complete non-padding image is
  5,447,562 bytes: a 512-byte outer header plus a 5,447,050-byte declared
  payload. The remaining 2,941,046 bytes are zero.
- The outer header begins with magic `0x58881688`, names the image `logo`, and
  carries extended magic `0x58891689`, header size 512, version 1, and
  alignment 16.
- The inner payload starts with count `0x39` (57), a total equal to the outer
  payload size, and 57 increasing offsets. The first stream begins at offset
  236, immediately after the two inner header words and 57 offsets.
- Every entry is one exact zlib stream. All 57 inflate successfully and each
  zlib Adler-32 is valid. The decoded pixels are tightly packed BGRA8888 with
  no row padding.
- Neither the outer header nor the inner table contains width or height.
  Geometry must come from the selected LK resource set and decoded byte count;
  factorizing the byte count alone is ambiguous.

### Corrected complete slot map

| Slots | LK resource identity | Correct geometry | Stride |
| --- | --- | ---: | ---: |
| 0 | first-stage `uboot` splash | 2160x1080 | 8,640 bytes |
| 1 | battery screen | 1920x1080 | 7,680 bytes |
| 2 | low-battery screen | 2160x1080 | 8,640 bytes |
| 3 | charger-overvoltage screen | 2160x1080 | 8,640 bytes |
| 4--13 | normal digits 0--9 | 84x121 | 336 bytes |
| 14 | normal percent sign | 108x121 | 432 bytes |
| 15--24 | battery animation 01--10 | 304x52 | 1,216 bytes |
| 25--34 | ten-percent animation 01--10 | 2160x1080 | 8,640 bytes |
| 35 | battery background | 2160x1080 | 8,640 bytes |
| 36 | battery fill image | 16x19 | 64 bytes |
| 37 | full-battery screen | 2160x1080 | 8,640 bytes |
| 38 | `kernel` splash | 2160x1080 | 8,640 bytes |
| 39 | fast-charging full screen | 2160x1080 | 8,640 bytes |
| 40--45 | fast-charging animation 01--06 | 2160x1080 | 8,640 bytes |
| 46--55 | fast-charging digits 0--9 | 108x192 | 432 bytes |
| 56 | fast-charging percent sign | 108x192 | 432 bytes |

Slot 0 is the owner-recognized Planet/Tux startup image. Slot 38 is a
near-identical follow-on image and is named `kernel` by the public LK resource
order. The private visual inventory shows charging, warning, percentage, and
animation content in every other slot consistent with the table above.

### Rejected interpretations

- The first render treated slot 0 as 1080x2160 portrait. This was rejected when
  the owner recognized the content but reported the wrong ratio; 2160x1080
  landscape uses the same byte count and matches the source BMP header.
- Slots 46--56 were initially factorized as 144x144. That square and the
  correct 108x192 rectangle both contain 20,736 pixels, but only 108x192
  reconstructs the fast-charging glyphs without scrambling.
- Generic reshapes of slots 4--14 as 242-pixel-wide strips were rejected.
  Their repeated byte counts and LK order establish 84x121 digits and a
  108x121 percent sign.
- Slot 36 can be factorized as a 304x1 strip, but the source asset and visual
  check establish the intended 16x19 battery fill.
- An early reading described 16 embedded entries. The value 16 belongs to the
  outer alignment field; the inner table at offset 512 explicitly records 57.

### Integrity and authentication boundary

- No whole-container CRC, digest, or appended signature was observed inside
  the stock image. Each zlib stream's Adler-32 is ordinary corruption
  detection and is regenerated by a normal zlib compressor; see
  [RFC 1950 section 2.2](https://www.rfc-editor.org/rfc/rfc1950.html#section-2.2).
- A future repack must nevertheless regenerate every changed stream, all
  following offsets, the inner total, and the outer payload size, while fitting
  before the 8 MiB partition boundary.
- The retained LK contains a real conditional image-authentication path. The
  pinned source calls the security library only when the selected policy says
  verification is required:
  [`img_auth_stor.c`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/img_auth_stor.c#L46-L85).
  In the public policy tables, logo verification is skipped for SBC-disabled
  locked and unlocked states and for SBC-enabled unlocked state; SBC-enabled
  plus locked requires it. See
  [`config1`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/sec_policy_config1.h#L58-L65),
  [`config2`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/sec_policy_config2.h#L58-L65),
  [`config3`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/sec_policy_config3.h#L58-L65),
  and
  [`config4`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/sec_policy_config4.h#L58-L65).
- The earlier MediaTek download session reported SBC disabled, and the stock
  logo has no appended authentication trailer. This supports, but does not
  prove at runtime, the inference that this named device would not require an
  OEM signature for a structurally valid replacement. No modified logo was
  boot-tested.

### Separate Gemian initramfs logo

- The later Debian swirl is not read from `logo_s.bin` and is not an active
  Plymouth theme. Generic `desktop-base` Plymouth artwork is installed, but no
  Plymouth package, active-theme alternative, or Plymouth configuration was
  present in the captured rootfs.
- Its rootfs source is
  `/usr/share/initramfs-tools/res/images/debian.png`: a 205x256, 8-bit RGB,
  non-interlaced PNG.
- `/usr/share/initramfs-tools/hooks/halium` copies that source to
  `/res/images/debian.png` in the initramfs and copies `/usr/bin/yamui` to
  `/bin`. `/usr/share/initramfs-tools/conf.d/halium` selects
  `BOOT=geminipda`.
- `/usr/share/initramfs-tools/scripts/geminipda` invokes `yamui` with asset name
  `debian` while checking and mounting the Gemian root. Yamui's installed
  documentation describes it as a minimal framebuffer UI for initrd/early boot
  and requires non-interlaced PNG files below `/res/images/`.
- The captured primary Android-v0 `boot` ramdisk contains `/bin/yamui`,
  `/scripts/geminipda`, and `/res/images/debian.png`. The embedded and rootfs
  source PNGs have identical SHA-256
  `729259cc68674786c81c34a0289df11736f094b5a1cb137c923c20dd0bfc5723`.
- Therefore changing only the rootfs source would not alter an already packed
  boot image. A future replacement would require a rebuilt initramfs and a
  correctly repacked Android-v0 boot container, including updated ramdisk size,
  layout, and image ID.

## Analysis

The early graphics and the Gemian startup graphic are two independent layers:

```text
retained LK
  -> 57-entry MediaTek logo partition (`uboot`, `kernel`, charging UI)
  -> Linux and gzip initramfs from Android-v0 boot image
  -> `yamui` renders `/res/images/debian.png` while mounting Gemian
  -> normal userspace
```

The recognizable-but-scrambled images were not damaged streams. In every case
the compressed data and Adler-32 were valid; only an underdetermined geometry
had been selected. The pinned LK resource order plus exact raw byte counts
resolves all 57 entries without adding dimensions to the vendor format.

There is no format-level CRC or embedded digest that prevents reconstruction.
Authentication is a separate LK policy question. Source and observed SBC state
make unsigned acceptance plausible on the named device, but that remains an
inference until a separately authorized, recovery-backed runtime test exists.

## Conclusion

`confirmed` for the named Gemini x27 capture:

- the retained `logo` image is a 57-stream MediaTek container with the complete
  corrected BGRA8888 slot map above;
- slots 0 and 38 are the first-stage and `kernel` Planet/Tux splash resources;
- there is no whole-file CRC or signature inside the captured container;
- zlib Adler-32 values are not an authentication barrier; and
- the later Debian swirl is a separate Yamui asset embedded in the Gemian
  initramfs.

`inferred`, not runtime-confirmed: an unsigned, structurally valid replacement
should be accepted under the named device's reported SBC-disabled state. No
modified logo, initramfs, boot image, or device partition was produced or used.

## Follow-up

Durable conclusions are summarized in
[`../../docs/hardware/boot-graphics.md`](../../docs/hardware/boot-graphics.md).
The owner has deliberately deferred graphical redesign, repacking, and all
device writes. This record does not add an implementation step to the roadmap
and does not authorize work on `logo`, primary `boot`, or any other protected
partition.
