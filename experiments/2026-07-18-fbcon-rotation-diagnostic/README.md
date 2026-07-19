# Candidate P: framebuffer-console rotation diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-18-fbcon-rotation-diagnostic` |
| Candidate | P |
| Status | Reproducibly built and validated; exported and synchronized to logical `boot2` with a matching full readback; runtime not tested |
| Subsystem | simplefb/fbcon console orientation |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date | 2026-07-18 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question

With Candidate O's hardware-tested DTB, external initramfs, Android-v0/LK
container, watchdog policy, and runtime sequence held exact, does compiling in
fbcon rotation and forcing `fbcon=rotate:3` make the existing console output
readable in the Gemini's normal landscape orientation without regressing the
watchdog/pstore recovery oracle?

Candidate P is a rotation-only configuration gate. It does not test a new
font, native DRM, panel or backlight control, keyboard input, a shell, eMMC, or
USB networking.

## Exact hardware-tested baseline

The baseline is the exported Candidate O artifact
`candidate-O-a53-sweep-e35dc9a`, whose one attributable hardware run completed
the Cortex-A53 CPU1--7 sweep and returned automatically through the watchdog.
The P builder requires the exact O artifact inventory and verifies its
`SHA256SUMS` file, whose SHA-256 is:

```text
d57319532822ee89bd435114e3119a7ebf4cb009553dab4b1682f88c3534be2e
```

The preserved payload and container inputs are:

| Input | Candidate O value |
| --- | --- |
| Boot image SHA-256 | `4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146` |
| External initramfs SHA-256 | `3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8` |
| Appended DTB SHA-256 | `c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379` |
| Baseline `Image.gz` SHA-256 | `0c0d0e22c78b5b0d89b7a7363be55850b3f3474d3b4e7f922946747efbe164d3` |
| Baseline embedded-config SHA-256 | `5a0c442c67b64cbabd4d030c93d50837bfc93e34d8878b413805457bfcd8e7cd` |
| Android header name | `gemini-obs-L` |
| Android header command line | `bootopt=64S3,32N2,64N2` |
| Kernel address | `0x40200000` |
| Ramdisk address | `0x45000000` |
| Second address | `0x40f00000` |
| Tags address | `0x44000000` |
| Page size | `2048` |

The kernel must be recompiled, so P's `Image`, `Image.gz`, kernel field size,
and canonical Android image ID are expected to change. The O initramfs and DTB
must remain byte-identical, and every Android-v0 field other than a
payload-derived kernel size and canonical ID must remain exact O.

## Controlled configuration delta

The `observability-fbcon-rotation` profile applies the exact `observability`
fragment chain and then `configs/gemini-fbcon-rotation.fragment`. Against the
exact Candidate O configuration, the resolved configuration may change only
these two lines:

```diff
-# CONFIG_FRAMEBUFFER_CONSOLE_ROTATION is not set
+CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y
-CONFIG_CMDLINE="... clk_ignore_unused"
+CONFIG_CMDLINE="... clk_ignore_unused fbcon=rotate:3"
```

`CONFIG_CMDLINE_FORCE=y`, `CONFIG_FRAMEBUFFER_CONSOLE=y`,
`CONFIG_FONT_8x16=y`, `# CONFIG_FONT_TER16x32 is not set`, and
`CONFIG_LOCALVERSION="-gemini-observability-L"` must remain unchanged. The
rotation token belongs in the compiled command line: an Android-header-only
addition would be discarded by `CONFIG_CMDLINE_FORCE=y` and would therefore be
a runtime no-op.

The profile is selected explicitly:

```sh
KERNEL_PROFILE=observability-fbcon-rotation ./scripts/dev-vm build-kernel
```

A successful compile or package validation is not a hardware result.

## Marker and attribution boundary

P deliberately preserves Candidate O's exact initramfs. Its visible and
pstore marker therefore remains:

```text
GEMINI_A53_SWEEP_20260718_O
```

Seeing that unchanged O marker in the correct landscape orientation is the
visual behavior oracle: it proves execution of the inherited O initramfs while
exercising the new rotation setting. It does **not** identify Candidate P by
itself. P attribution additionally requires the validated P boot-image hash,
the matching full logical-`boot2` readback hash, an intended `boot2` selection,
and the changed-cycle recovery record. Adding a P-only runtime string would
change the initramfs and invalidate this two-config-line gate.

The inherited O initramfs also emits:

```text
kernel_dtb_config=exact-candidate-N
```

That text is a historical label from the N-to-O initramfs lineage. O reused
Candidate N's exact kernel, DTB, and configuration, so the label was accurate
for O. P intentionally rebuilds the kernel with a changed resolved
configuration. The inherited label proves only that the exact O `/init` bytes
ran; it is not evidence for P's resolved configuration and must not be cited as
such. P's configuration identity must instead come from the validated package,
embedded configuration, artifact provenance, and exact target readback.

## Required artifact validation

The dedicated P builder and validators establish all of the following before
any device selection:

1. Source tarball, patch series, architecture, compiler, linker, base config,
   existing fragment inputs, and `modules_built=false` match Candidate O's
   source package.
2. The resolved configuration has exactly the two changes listed above and no
   font, local-version, probe, driver, or policy delta.
3. The complete packaged DTB tree is byte-identical to the O source package,
   and the assembled candidate uses O's exact final appended DTB.
4. The external initramfs is byte-identical to O, including its O marker and
   inherited `kernel_dtb_config` text.
5. P's kernel field is exactly its newly compiled `Image.gz` followed by O's
   exact DTB; the ramdisk is O's exact initramfs.
6. Header name, header command line, addresses, page size, layout, zero
   padding, empty second payload, and LK/arm64 placement gates remain exact O.
   Only the kernel payload, corresponding kernel size, and canonical image ID
   may differ.
7. Two clean VM builds produce identical resolved config, `Image`, `Image.gz`,
   DTBs, boot image, and other non-timestamp content before final hashes are
   pinned.

Negative mutation tests must reject an omitted or wrong rotation value, a
header-only rotation token, any extra configuration change, a font change, an
altered initramfs or DTB, and any non-derived LK-container change.

Both focused regressions pass against the exact O/P inputs:
`scripts/test-package-validator-mutations.sh` rejects omitted or wrong
rotation configuration, omitted or wrong `fbcon=rotate`, extra configuration,
font/local-version, packaged-fragment, and DTB mutations;
`scripts/test-validator-mutations.sh` rejects changed O pins, initramfs, DTB,
header identity/addressing, canonical ID, padding, and an unchanged kernel.
Their temporary mutations never access a device.

## Build, export, and `boot2` synchronization result

Candidate P was built from clean repository revision
`170a6403ef41438e01a512d65eb9ad9c223118b0` using package:

```text
linux-7.1.3-gemini-observability-fbcon-rotation-e1d4f6f3-03ac37f8
```

Its source tarball SHA-256 is
`be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`,
and its 82-patch series SHA-256 is
`e1d4f6f36b49c5f6064bd7344e31c69b05903ef2f37fa8d9af736035faf47a8a`.
Two independent VM packages generated at `2026-07-19T00:35:56Z` and
`2026-07-19T00:49:55Z` have the same 214-file inventory, including 119 DTBs,
and every file not carrying the generated timestamp is byte-identical. The
two `build.json` files and checksum manifests become byte-identical after
normalizing only `generated_utc` and its dependent digest. The complete DTB
trees match, and the resolved configuration has only the two permitted line
changes. A second final candidate-artifact directory is recursively identical
to the selected one.

The selected validated output is:

| Output | Value |
| --- | --- |
| `Image` SHA-256 | `695eff12f7fb3b210b2d9814cc1cf0ea2250d1e8277bb552fb695c87782a1a4b` |
| `Image.gz` SHA-256 | `7f9421e41eca296cc757c18c7cce0203fb53bbe9b5afa9eb890314a5ce1dea69` |
| Resolved configuration SHA-256 | `0759fdb25abf25008ecf967736316a2d16d227c80c6835dad5875e8a612ef424` |
| `System.map` SHA-256 | `098c703d382b13386b6fa40c6130f8b77d8b8905c39de8e80445d753b297ea07` |
| Raw Android-v0 image | `gemini-fbcon-rotation.boot.img` |
| Raw image size | `6531072` bytes |
| Raw image SHA-256 | `d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341` |
| Candidate `SHA256SUMS` SHA-256 | `e063bf5ddeb576deaec8aea3fa050f23a890027c7cf58b0133e3672f1ad07835` |
| Exact inherited O DTB SHA-256 | `c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379` |
| Exact inherited O initramfs SHA-256 | `3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8` |

The Android-v0 delta validator found only the payload-derived kernel size and
canonical ID fields changed. Header name and command line, addresses, layout,
zero padding, appended O DTB, and O initramfs remain exact. The LK parser and
arm64 placement/decompression gates pass. The exact host export is:

```text
artifacts/vm-export/boot-candidates/candidate-P-fbcon-rotation-170a640
```

The raw image was then zero-padded to the exact 16 MiB target size and
synchronized only to live-resolved logical `boot2`. Before the write, the full
partition matched exact padded Candidate O SHA-256
`5efda7d18ebb99d0152d872d6dd23e7e6345c56920a77fb1129c350e8e02102d`.
A fresh private backup was preserved. The Candidate P padded image, flushed
target, and separate full local readback all match SHA-256
`cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc`.
No reboot, shutdown, or boot selection was performed. See the
[final build reproduction](results/final-build-reproduction-20260718.txt) and
[full write/readback result](results/boot2-write-candidate-p-20260718.txt).

These results establish software and partition identity only. They do not
establish that P boots, that `fbcon=rotate:3` takes effect, that the console is
readable, or that the inherited watchdog/pstore recovery still works.

## Runtime oracle and decision table

One owner-attended intended `boot2` selection is sufficient for this changed
gate when the exact artifact and full-partition readback are already verified.
The standard cycle-aware collector must observe disconnect, reconnect, and a
changed boot ID before recovering pstore.

| Observation | Conclusion | Next action |
| --- | --- | --- |
| Exact O marker is readable in normal landscape orientation and the O CPU/watchdog checkpoints plus automatic recovery remain intact | Rotation gate passes on this exact P revision | Preserve P as the readable-console baseline and proceed to keyboard events as a separate candidate |
| Exact O marker remains sideways, with otherwise valid O recovery evidence | P ran, but `rotate:3` did not produce the expected orientation | Inspect the embedded config, effective command line, fbcon rotation parsing, and simplefb geometry before changing other inputs |
| Output is rotated but wrong by 90 or 180 degrees | Rotation support ran with the wrong orientation assumption | Make a new rotation-value-only derivative; do not add font or display-driver work |
| No attributable P record or unchanged-cycle pstore only | P execution was not established | Reverify exact `boot2` target/readback and intended slot selection; do not infer a display regression |
| O CPU or watchdog checkpoint regresses | The new kernel build regressed the proven baseline or the run is incomplete | Stop the quality-of-life sequence and bisect against exact O before adding keyboard or shell layers |

## Safety

The configuration, builder, and validators have no device or flashing
interface. The completed build and export did not access hardware.

The completed installation was a separate operation governed by
`docs/SAFETY.md` and `AGENTS.md`: logical `boot2` was resolved from the live
GPT, verified inactive and unmounted, fully backed up, written only after exact
padding, synchronized and flushed, and checked through a matching full local
readback. Never substitute `boot`, `boot3`, or a remembered partition number,
and never reboot automatically.

At runtime, retain stable power and the proven watchdog recovery path. Stop
for unexpected heat, charging anomalies, filesystem errors, repeated recovery
failure, or any changed recovery behavior.

## Observations and conclusion

Candidate P has been reproducibly built, validated, exported, synchronized,
flushed, and fully read back from logical `boot2`. It has not been selected or
runtime-tested. The rotation hypothesis therefore remains untested, and no
hardware-support claim follows from the successful build or partition write.

If P passes, keyboard event capture is the next separate kernel/DT gate, and a
supervised local initramfs shell follows only after keyboard input is proven.
eMMC diagnostics and USB gadget networking remain later independent layers.
