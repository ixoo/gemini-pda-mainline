# Candidate P: framebuffer-console rotation diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-18-fbcon-rotation-diagnostic` |
| Candidate | P |
| Status | Planned; configuration/profile scaffold only, with no P package, boot artifact, device write, or runtime result yet |
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
Before a P derivative is assembled, the future builder must require the exact
O artifact inventory and verify its `SHA256SUMS` file, whose SHA-256 is:

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

The dedicated P builder and validators are not part of this initial scaffold.
Before any device selection they must establish all of the following:

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

The configuration and documentation changes are build-only and do not access
hardware. The future candidate builder must likewise have no device or
flashing interface.

Installing a validated P artifact is a separate operation governed by
`docs/SAFETY.md` and `AGENTS.md`: resolve logical `boot2` from the live GPT,
verify it is inactive and unmounted, preserve a full private backup, pad to the
exact partition size, write and flush, and require a matching full-partition
readback checksum. Never substitute `boot`, `boot3`, or a remembered partition
number, and never reboot automatically.

At runtime, retain stable power and the proven watchdog recovery path. Stop
for unexpected heat, charging anomalies, filesystem errors, repeated recovery
failure, or any changed recovery behavior.

## Observations and conclusion

No Candidate P package or boot image has been built, written, or selected at
the time of this scaffold. The hypothesis remains untested; no hardware
support claim follows from the manifest or fragment changes.

If P passes, keyboard event capture is the next separate kernel/DT gate, and a
supervised local initramfs shell follows only after keyboard input is proven.
eMMC diagnostics and USB gadget networking remain later independent layers.
