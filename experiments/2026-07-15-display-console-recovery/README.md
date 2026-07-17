# Experiment: LK framebuffer console recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-15-display-console-recovery` |
| Status | `inconclusive` for runtime; VM build/static validation completed, but the later boot attempt did not establish slot selection, LK acceptance, or Linux execution |
| Subsystem | LK framebuffer handoff and Linux fbcon |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-15 |

## Question or hypothesis

Can Linux display early userspace diagnostics by reusing the framebuffer that
the retained Gemini LK initializes, without enabling the unvalidated MT6797
DRM/DSI/panel pipeline or relying on UART?

## Provenance and environment

- Kernel input: Linux `7.1.3`, pinned by `kernel/manifest.json` (source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`).
- Historical patch series: `patches/series` then included prototype patch 0077;
  series SHA-256
  `010ac44b136666e391a54397887da9e8549e750fb1a909ce28924982c7fa48e4`.
- New patch SHA-256:
  `7cf8f0fcbf7841d6cef8c97bf136a7ffaa97dc0e2914665736072ac4535fb74a`.
- Built `.config` SHA-256:
  `52d0f91457f08dae13967dcb760dca7be8604307823a73b3b2cee810ead678b7`.
- VM toolchain: GNU Make 4.3 and `aarch64-linux-gnu-gcc` 13.3.0.
- Boot path: private LK Android-8 boot image candidate. It was subsequently
  written under explicit authorization to non-primary `boot3`, and later to
  non-primary `boot2`; both writes have complete checksum records.

## Evidence and safety

Sanitized Gemian capture reports 1080×2160, 32 bpp, stride 4352 bytes, and a
final LK framebuffer reservation at `0x7dfb0000` of `0x1f90000` bytes. Retained
LK source sets `disp_fb_bpp = 32` and labels the format ARGB8888. LK adds the
runtime reservation after loading the DTB, so the patch intentionally does not
duplicate a static `/reserved-memory` entry; this avoids the known LK mblock
overlap failure mode.

The build and packaging scripts are read-only with respect to hardware. They
build a guest-owned initramfs and boot image and never write the preloader,
NVRAM, GPT, or any MMC partition. The later owner-authorized `boot3` write is
recorded separately in [the write experiment](../2026-07-15-display-console-write/README.md).
The candidate remains outside Git under the VM artifact directory.

## Associated code

- [`fixtures/0077-arm64-dts-mediatek-gemini-expose-LK-simple-framebuffer.prototype.patch`](fixtures/0077-arm64-dts-mediatek-gemini-expose-LK-simple-framebuffer.prototype.patch)
  preserves the exact prototype patch with SHA-256
  `7cf8f0fcbf7841d6cef8c97bf136a7ffaa97dc0e2914665736072ac4535fb74a`.
  It added a `simple-framebuffer` child under `/chosen` and redirected
  `stdout-path` to it. It has been removed from the active patch series: this
  loader-specific instrumentation is not an upstream board-DT contract, and
  its placeholder authorship/sign-off is historical evidence only.
- The historical build selected `FB`, `FB_SIMPLE`, and
  `FRAMEBUFFER_CONSOLE`. Those options no longer belong to the general
  `configs/gemini.fragment`; a focused handoff profile must select them when
  producing a display-instrumented candidate.
- `scripts/build-display-initramfs.sh` creates a deterministic, static ARM64
  BusyBox initramfs from the local VM BusyBox.
- `scripts/build-display-lk-candidate.sh` validates the package, serializes the
  LK image, and records parser/provenance output. It refuses an existing output
  directory and has no flashing path.
- `initramfs/init` prints sanitized boot state, redirects a shell to
  `/dev/console`, and intentionally performs no storage probe.

Build inside the development VM:

```sh
./scripts/dev-vm build-kernel
./scripts/dev-vm run bash -lc \
  'experiments/2026-07-15-display-console-recovery/scripts/build-display-lk-candidate.sh \
     --package "$HOME/artifacts/gemini-pda/linux-7.1.3-gemini-<validated-id>" \
     --output "$HOME/artifacts/boot-candidates/<new-directory>"'
```

## Procedure

1. Apply the full pinned patch series and merge `configs/gemini.fragment` in
   the VM.
2. Build the kernel package with `./scripts/dev-vm build-kernel`.
3. Run the candidate builder against that exact package.
4. Inspect the parser output and decompile the packaged DTB. Do not flash as a
   side effect of any of these steps.

## Observations

The VM build and package validation completed successfully. The package was
`linux-7.1.3-gemini-b885d52ffc58`, and the decompiled DTB contains:

```text
chosen/framebuffer@7dfb0000
compatible = "simple-framebuffer"
reg = <0x00 0x7dfb0000 0x00 0x1f90000>
width = 1080, height = 2160, stride = 4352
format = "a8r8g8b8"
```

The candidate passed the LK parser, is 15,724,544 bytes (below the 16 MiB
`boot3` partition), and has these private artifact hashes:

```text
guest:~/artifacts/boot-candidates/20260715-display-console/linux-7.1.3-gemini-b885d52ffc58-display.boot.img
candidate_sha256: a70e8967b69e187e6643a4c2c43f7d9071a3dea441ccd99171c346ac26f2e4f8
initramfs_sha256: 153ac3cbc1e052f2863e362bc241ba84fbf23acd7c3843c439a4a639cb9f06f2
```

The `a8r8g8b8` value is source-backed evidence, but Linux scanout byte order
has not been observed. A blank or garbled display would therefore be an
inconclusive format/handoff result, not proof that the kernel failed. The
candidate was subsequently written to `boot3` and `boot2`, each with a
full-partition readback match. A later owner-reported boot attempt occurred,
but the key sequence and selected slot were not captured. No loader splash,
fbcon marker, Linux log, or initramfs marker attributable to this candidate
was observed.

The complete sanitized parser/configuration record is
[`results/display-console-candidate-20260715.txt`](results/display-console-candidate-20260715.txt).
The post-write boot attempt is recorded as an inconclusive live snapshot
in [`results/runtime-boot-attempt-20260715.txt`](results/runtime-boot-attempt-20260715.txt):
the device was later reachable in its vendor 3.18.41 system, and the exact
boot-button sequence was not captured. That observation does not establish
whether the prototype was selected, rejected before LK, entered and reset in
LK/Linux, or was never selected.

## Analysis and conclusion

The hypothesis is **supported statically and inconclusive at runtime**: the
historical kernel had a generic simplefb driver and built-in fbcon, and its DTB
described the framebuffer reported after LK. The attempted boot produced no
evidence that this DTB reached Linux. It therefore does not establish that the
panel remains powered after handoff, that the address is accessible with
Linux memory attributes, or that the chosen pixel format is correct. It is not
a claim of display hardware support.

## Follow-up

Do not reuse this prototype as the next candidate. Preserve it only as evidence
and build display instrumentation as an optional packaging-time DT overlay on
top of a separately validated LK-handoff candidate. Keep the DRM/DSI/panel,
backlight, touchscreen, and other display consumers disabled, preserve the
known-good boot path, and record the exact selection method plus an attributable
loader, fbcon, Linux, or initramfs marker before drawing a runtime conclusion.
