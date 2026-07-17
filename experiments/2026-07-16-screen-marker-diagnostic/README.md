# Experiment: deterministic LK framebuffer marker

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-screen-marker-diagnostic` |
| Status | Runtime attempted once; black screen, marker absent, cause unresolved |
| Subsystem | Retained LK display handoff, simplefb, early userspace |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Does the exact kernel that produced candidate D retain LK's scanout long enough
for external initramfs `/init` to paint a deterministic visible frame through
Linux `simplefb`?

Candidate D provided strong indirect evidence that `/init` executed, but UART
is unavailable and its USB gadget did not enumerate. This experiment preserves
that exact `Image.gz` and the existing LK/USB DT deltas, adds only the known LK
framebuffer description, and replaces the reset timer with one bounded
`/dev/fb0` write. Seeing eight horizontal white/dark-gray bands would directly
confirm the kernel, simplefb probe, devtmpfs, and `/init` path.

## Provenance and environment

The exact runtime-tested baseline is candidate D:

```text
boot image sha256: 61fb961a8de48a7e0a9acf83447b90cc7012b741a10b0707cb7e73d33e8081c8
initramfs sha256: 8a63939caf76473ad8d688e923155d2b9800bf25cd2017c36acafb08a11bb71b
DTB sha256:       5717a8c2f3f4f02533fae4dad8c9f9137f0f78cb0986fd6908a74309722e7db4
```

The display contract is independently present in the live Gemian capture:

- framebuffer physical/MVA base `0x7dfb0000`;
- LK reservation `0x1f90000` bytes;
- 1080 by 2160 pixels, 4352-byte stride, 32-bit RGBA/ARGB-compatible layout;
- OVL0 layer 0 scanning from the same base.

The visible frame is exactly `4352 * 2160 = 9,400,320` (`0x8f7000`) bytes,
well below the reservation. See
[`results/display-path-selection-20260716.txt`](results/display-path-selection-20260716.txt)
and the private raw capture named there.

The earlier simplefb test is not a negative result for this method. Its
initramfs redirected the first devtmpfs mount to `/dev/null` before that device
existed, so it could not create `/dev/fb0` or console nodes. It also relied on
fbcon text and never performed a deterministic pixel write. Candidate D's DTB,
despite containing `CONFIG_FB_SIMPLE=y` in the kernel, had no
`simple-framebuffer` node and therefore could not bind simplefb.

## Safety assessment

All associated build and validation tools are file-only. They have no SSH,
block-device, partition, adb, fastboot, MediaTek, or flashing interface.
Candidate generation does not authorize a device write or boot.

At runtime, `/init` refuses to write unless `/dev/fb0` exists, its reported
name is exactly `simple`, its virtual size is exactly `1080,2160`, its depth is
exactly 32 bits, its stride is exactly 4352, and the marker is exactly
9,400,320 bytes. It then writes one visible frame. It does not write the
remainder of LK's reservation, display
registers, panel controls, PMIC, I2C, storage, or firmware, and it makes no
reboot request. The kernel and DT retain candidate D's already-tested USB
probe, but USB userspace is dormant in this initramfs.

Any future test remains an attended non-primary `boot2` experiment requiring a
separate explicit instruction, a current backup/read-back procedure, and the
known-good primary/recovery path. Stop after unexpected heat, charging changes,
or changed recovery behavior. Primary `boot`, preloader, NVRAM, and GPT remain
protected.

## Associated code

- `initramfs/init`: mounts devtmpfs first, validates the exact fbdev contract,
  writes one frame, then idles.
- `scripts/generate-screen-marker.py`: generates and validates eight opaque,
  channel-order-independent horizontal bands.
- `scripts/build-initramfs.sh`: creates a deterministic static-BusyBox archive.
- `scripts/validate-initramfs-delta.sh`: permits only the tracked `/init`, raw
  marker, and BusyBox `dd`/`wc` links relative to candidate D.
- `scripts/build-screen-marker-dtb.sh`: applies the already-validated LK and
  USB overlays plus the isolated simplefb overlay, then invokes the exact DT
  allow-delta validator.
- `scripts/validate-boot-delta.py`: proves both Android images use the same
  `Image.gz`, explicit appended DTBs/initramfs files, addresses, name, command
  line, padding policy, and canonical Android-v0 IDs.
- `scripts/build-screen-marker-candidate.sh`: reconstructs and hash-pins exact
  candidate D before deriving this non-flashing image.

## Procedure

1. In the development VM, run the builder with the exact validated usbdiag
   package, source-date epoch `0`, and a new explicit output directory.
2. Require the LK parser, combined DT allowlist, initramfs delta, Android-v0
   delta, and `SHA256SUMS` checks to pass.
3. Build into a second new directory and require byte-identical outputs.
4. Stop. A later `boot2` write or boot requires a separate explicit instruction.
   The owner explicitly authorized the `boot2` write on 2026-07-16; the write,
   flush, and full readback are recorded below. Booting remains a separate,
   attended action.
5. During an authorized attended boot, watch from power-on. The positive marker
   is eight broad bands alternating opaque white and dark gray. The panel's
   physical orientation is rotated 90 degrees, so the row bands may appear
   vertical. A
   dark screen, splash only, or backlight change without those bands is not a
   positive result. Record whether the pattern appeared, approximate latency,
   duration, backlight state, power state, and recovery outcome.

## Observations

The build produced a 6,533,120-byte Android v0 image:

```text
boot image sha256: 08845b5c3985a8bcba569d3009889bbfe210f942d1cef23b798f5fff5c2cb253
initramfs sha256:  1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
DTB sha256:        cd41adc3f38b2f94b69ca69a27f61ab2b3ff5dcbcf7094de2f250a341c726389
marker sha256:     096b4f7a4737ea20e6d03c73b9955e70979f1a5db09e78d4d87610411c7cabe2
```

The builder reconstructed exact candidate D before each derivation. Two
independent output directories matched recursively. Both complete checksum
manifests passed. The combined DT validator found no delta outside the named
LK, USB, and simplefb properties; the semantic checks proved the 4352-byte
stride covers the visible width, the `0x8f7000` frame fits inside the
`0x1f90000` reservation, and the reservation ends at `0x7ff40000` immediately
before the fixed ATF log region. The initramfs validator proved that only the
tracked `/init`, exact marker, and BusyBox `dd`/`wc` links differ from candidate
D. The Android validator proved `Image.gz` is byte-identical and independently
validated both appended DTBs, ramdisks, header deltas, padding, and canonical
IDs. The LK parser passed.

The verified output was exported with mode `0600` below the Git-ignored host
path:

```text
artifacts/vm-export/boot-candidates/
  gemini-screen-marker-20260716-E-3d92a7e9-fdf1d345/
```

The full static record is
[`results/screen-marker-candidate-20260716.txt`](results/screen-marker-candidate-20260716.txt).
At `2026-07-16T23:37:15Z`, the owner explicitly directed this candidate to be
copied to logical `boot2`. Live preflight resolved `boot2` to the unmounted
16 MiB `/dev/mmcblk0p30`, while the running Gemian root remained
`/dev/mmcblk0p29`. A fresh full backup matched the expected prior candidate-D
partition. The screen-marker image was zero-extended to the exact partition
size, written with `fsync`, followed by `sync` and a block-device buffer flush.
Both the device-side and locally retained full-partition readbacks matched the
staged image byte-for-byte at SHA-256
`34d183cd5f79e1784177445ece2d3b5b36ecbd809b4d920ea579f35f076ed2d7`.
The write procedure left the device running Gemian; no boot was attempted as
part of that procedure.
See
[`results/boot2-write-20260716.txt`](results/boot2-write-20260716.txt).

On 2026-07-16, after the owner established a standing `boot2` synchronization
policy, a fresh live check again resolved the unmounted logical `boot2` to
`/dev/mmcblk0p30` while Gemian ran from `/dev/mmcblk0p29`. Candidate E remained
the newest validated boot candidate. The live full-partition SHA-256 was still
`34d183cd5f79e1784177445ece2d3b5b36ecbd809b4d920ea579f35f076ed2d7`,
matching the retained exact-size candidate, so no redundant write was made.
See the
[`boot2` synchronization check](results/boot2-latest-sync-check-20260716.txt).

The owner subsequently selected `boot2` and reported a black screen. None of
the expected white/dark bands appeared. Backlight state, elapsed time, final
power state, and recovery action have not yet been reported. This fails the
positive marker criterion, but it does not distinguish kernel entry failure,
missing simplefb, a refused framebuffer contract, a failed framebuffer write,
or loss of loader-initialized scanout state before or after the write. See
[`results/runtime-screen-marker-attempt-20260716.txt`](results/runtime-screen-marker-attempt-20260716.txt).

## Analysis

This is a smaller stateful probe than native DRM/panel bring-up. It reuses
loader-initialized display state and changes only reserved framebuffer RAM.
It cannot establish correct display clock, regulator, panel, DSI, or DRM
ownership. A visible pattern would prove only that the retained path remained
active and that Linux userspace reached the bounded write.

The principal negative-test ambiguity is clock handoff. A focused audit of
bsg100's later native-fbcon milestone reports that unused-clock cleanup gated
`CLK_INFRA_DISP_PWM` and its `pwm_sel` parent, extinguishing LK's retained
backlight. Linux simplefb can retain clocks named in its node, while Candidate
E names none. That hardware-tested history makes
`clocks = <&infrasys CLK_INFRA_DISP_PWM>;` the next one-variable DT-only
discriminator; it is no longer a guessed clock. See the
[exact-commit comparison](../2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md).

## Conclusion

The candidate is reproducible, passes its static safety and container gates,
and was fully verified on the non-primary `boot2` partition. Its positive
runtime criterion was not observed. The black result is inconclusive because
every fail-closed `/init` branch is visually black and the experiment has no
independent signal proving kernel entry, simplefb probe, the framebuffer write,
or retained LK scanout.

## Follow-up

The [Candidate F follow-up](../2026-07-16-screen-clock-retention-diagnostic/README.md)
now preserves Candidate E's exact Image, initramfs, simplefb geometry and
marker while adding only the `CLK_INFRA_DISP_PWM` reference above. Its builder
derives the existing phandle from `/syscon@10001000`, and the semantic
validator proves that sole delta. Two builds are byte-identical, all static
gates pass, and the image has been synchronized and fully read back from
logical `boot2`. Its first attended boot showed sideways console text for about
one second before black, strongly supporting kernel entry plus simplefb/fbcon
output and targeted clock retention. The unread text does not independently
prove `/init`, and no expected marker bands were recognized.

The [Candidate G follow-up](../2026-07-16-fbcon-text-diagnostic/README.md)
keeps F's exact kernel and DTB while replacing only initramfs, removing the raw
marker and all framebuffer-device access, and holding a distinctive tty0
banner. Its attended boot reproduced sideways scrolling for 1–2 seconds before
black with the backlight apparently off. Candidate H preserved G's exact
kernel/initramfs and appended only the MM-root simplefb clock reference. Two
attempts visibly progressed farther and approximately exposed its
initramfs-only marker before the screen and backlight went off; later attempts
did not reproduce the progress. Candidate I kept H's exact kernel/DTB and
changed only `/init` to emit a one-second counter through `T+60` before a
silent hold, but the reported intended selection went directly to black with
no I marker or counter. Its timing hypothesis therefore remains untested.
Candidate J rebuilds that kernel with `clk_ignore_unused` in forced
`CONFIG_CMDLINE`, retains exact I's DTB/initramfs/header command line, and has
been synchronized and fully read back from logical `boot2`; runtime is pending.
It is a broad diagnostic control, not a proposed fix.
Native DRM, DSI, PWM, panel, regulators and display-domain consumers remain
disabled.
