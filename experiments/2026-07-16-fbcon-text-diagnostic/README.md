# Experiment: retain readable fbcon text without a raw framebuffer overwrite

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-fbcon-text-diagnostic` |
| Status | Candidate G built reproducibly and synchronized to `boot2`; runtime not attempted |
| Subsystem | LK display handoff, simplefb, framebuffer console, initramfs |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Will Candidate F's transient sideways framebuffer-console output remain visible
when its raw screen-marker file and `/dev/fb0` write are removed?

Candidate G is an initramfs-only derivative of exact Candidate F. It retains
the same `Image.gz`, DTB, `CLK_INFRA_DISP_PWM` simplefb reference, Android-v0
header contract and forced kernel command line. It replaces the marker-writing
`/init` with a short distinctive tty0/UART banner and a carriage-return
heartbeat every 30 seconds. It never opens a framebuffer device.

## Motivation and prior observation

On one owner-attended Candidate F boot, the owner reported sideways text moving
right-to-left for about one second, followed by a black display. The text was
not transcribed or photographed and the later backlight and power state were
not reported. This is the first positive visual runtime signal from the current
Linux 7.1.3 handoff and strongly supports simplefb/fbcon output, but it is not
content-attributed proof of `/init`. Candidate F emits text and then attempts
its full raw framebuffer fill, so removing that fill is the smallest direct
A/B. See the exact sanitized
[`Candidate F runtime record`](../2026-07-16-screen-clock-retention-diagnostic/results/runtime-candidate-f-20260716.txt).

## Rotation boundary

The exact Candidate F kernel has `CONFIG_FRAMEBUFFER_CONSOLE=y`, but
`CONFIG_FRAMEBUFFER_CONSOLE_ROTATION` and `CONFIG_FONT_TER16x32` are not set.
Linux still creates fbcon rotation sysfs attributes in that configuration, but
their handlers call compiled no-op stubs. Candidate G therefore does not write
those attributes or claim rotation; sideways text is expected. A later
Candidate H can isolate the kernel change by enabling rotation and adding
`fbcon=rotate:3` to the forced built-in command line. Font enlargement should
remain separately attributable.

## Provenance and safety

The builder reconstructs Candidate F and refuses to continue unless these
exact hashes match:

```text
boot image: 14c1fe4116cd04331fa347502929ef9e60aed08cbc859b99621a5010e263df57
initramfs:  1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
DTB:        edcc5da98996cf594661c5c6da08996a6b2bf59f1e46bcbf6b89e9e9aac56abb
Image.gz:   3c001a8950939fdf4e15fb5d94f4c8761e461a2e274f103777c4db97da483a3e
```

The initramfs validator permits only tracked `/init` bytes plus removal of
`screen-marker.raw`, `bin/dd` and `bin/wc`; every other path, mode, symlink and
regular-file byte must match exact Candidate F. It rejects framebuffer-device,
storage, raw-memory, reboot, poweroff and halt access. Procfs and sysfs remain
read-only. The runtime writes only console characters and volatile shell state.

The build tools are file-only and have no partition or flashing interface.
Hardware synchronization is a separate action under the owner's standing
logical-`boot2` authorization. No boot or reboot is authorized.

## Associated code

- `initramfs/init` mounts devtmpfs first, emits the distinctive banner, reads
  optional simplefb sysfs metadata, and holds with a 30-second heartbeat.
- `scripts/build-initramfs.sh` derives the deterministic archive from exact F.
- `scripts/validate-initramfs-delta.sh` enforces the archive and safety delta.
- `scripts/validate-boot-delta.py` requires an identical kernel segment and
  Android header differences only for ramdisk size and canonical ID.
- `scripts/build-fbcon-text-candidate.sh` reconstructs F, builds G, runs every
  validator and writes a complete checksum manifest.

## Procedure and positive criterion

1. Build Candidate G twice from the exact Candidate F source package with
   source-date epoch zero.
2. Require both manifests to pass and both output trees to be byte-identical.
3. Export one exact directory to Git-ignored host artifacts.
4. Synchronize it only to live logical `boot2` after the standing-policy
   preflight, backup, full write, flush and full readback gates pass.
5. On an owner-attended `boot2` selection, record the visible text, orientation,
   approximate duration, heartbeat changes, backlight state, final power state
   and recovery action. A legible `GEMINI_FBCON_TEXT_20260716_G` or
   `LINUX INITRAMFS REACHED` line directly confirms `/init`.

Persistent sideways console output supports the raw overwrite as Candidate F's
black-transition cause. A black transition despite no raw access rejects that
leading explanation. Native DRM, DSI, panel, backlight programming and full
display clock ownership remain untested in either case.

## Build and deployment result

Two independent builds were recursively byte-identical. Both checksum
manifests, the exact initramfs tree-delta gate, Android-v0 delta validator,
canonical IDs and LK parser passed. The exported files are:

```text
boot image size:       6520832
boot image SHA-256:    85f91ee7138e91cd98b0116da9b40e3fba286836feaea268e232cec79ef16c09
initramfs SHA-256:     8dc85151bececf297f99b6f22c87316a54d0fa062e29c2c64ad00334b7ad0956
unchanged DTB SHA-256: edcc5da98996cf594661c5c6da08996a6b2bf59f1e46bcbf6b89e9e9aac56abb
```

See [`results/candidate-g-build-20260716.txt`](results/candidate-g-build-20260716.txt).

The live preflight resolved `boot2` to unmounted, writable 16 MiB
`/dev/mmcblk0p30` while Gemian ran from `/dev/mmcblk0p29`; no holders existed,
AC was online, and the battery reported 100%, Full and Good. A fresh private
full backup matched Candidate F. Candidate G was padded to the exact target,
staged and checksum-verified, then written with `fsync`, followed by `sync` and
a block-device flush. The device checksum and complete private laptop readback
both matched:

```text
full boot2 SHA-256: 9380cba612f4512922564b79062403b2b8bc143c422bfea7fa84dec1c1ba6d29
```

No boot, reboot or shutdown occurred and no other partition was touched. See
[`results/boot2-write-candidate-g-20260716.txt`](results/boot2-write-candidate-g-20260716.txt).

## Next observation

Candidate G is ready for an owner-attended silver-button `boot2` selection.
The expected result is console text that remains visible sideways, followed by
an in-place heartbeat-number update every 30 seconds. Rotation is intentionally
deferred until this initramfs-only A/B has a recorded result.
