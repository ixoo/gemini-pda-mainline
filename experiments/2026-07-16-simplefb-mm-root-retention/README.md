# Experiment: retain LK's MM root clock through simplefb

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-simplefb-mm-root-retention` |
| Status | Candidate H attempted in one owner-attended series; two attempts visibly progressed farther than G and ended black with the backlight off, while later attempts did not reproduce that progress |
| Subsystem | LK display handoff, MT6797 CCF, simplefb, framebuffer console |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Does retaining LK's active multimedia clock root prevent the 1–2 second
fbcon/backlight loss observed with Candidate G?

Candidate H is an exact-G DT-only derivative. It preserves Candidate G's
`Image.gz`, initramfs, framebuffer geometry, forced command line and Android-v0
container. Its only semantic change appends `CLK_TOP_MUX_MM` to the existing
simplefb `clocks` property:

```dts
clocks = <&infrasys CLK_INFRA_DISP_PWM>,
         <&topckgen CLK_TOP_MUX_MM>;
```

The first clock retains the display-PWM/backlight path and its `pwm_sel`
parent. The second asks simplefb to prepare and enable `mm_sel`, recursively
retaining the parent that LK selected for the display/MM tree. This is a
diagnostic ownership bridge, not the final native display binding.

## Evidence and boundary

Candidate G reproduced sideways fbcon for 1–2 seconds and then went black with
the backlight apparently off, despite having no raw framebuffer access. That
rejects Candidate F's raw marker overwrite as the cause. Candidate G retains
only `CLK_INFRA_DISP_PWM`; it does not retain `mm_sel` or its selected PLL.

The bsg100 effort's later native-DRM success gives every display engine, SMI,
DSI, PWM and panel resource a real Linux consumer and removes
`clk_ignore_unused`. Separately, the named device's Gemian
[`clock capture`](../2026-07-12-mt6797-clock-power-reset-recovery/results/runtime-summary.txt)
records `mm_sel` at 325 MHz as the active display/MM tree. This experiment uses
those observations as evidence for one bounded clock-retention test, not as
proof that the two kernels have identical clock state. See also the local
[`035d4b0 comparison`](../2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md).

Linux performs unused-clock disable and unprepare work during late init. A
clock with no Linux owner may therefore remain usable long enough for early
fbcon output and disappear before `/init`. Candidate H directly tests one
specific unowned root. It does not enable MMSYS gates, program a PLL, change a
rate or parent, touch panel registers, add DRM, rotate fbcon, access `/dev/fb0`,
or use broad `clk_ignore_unused`.

## Associated code and validation

- `scripts/build-mm-root-dtb.sh` resolves both clock-provider phandles from
  exact Candidate G by validated DT paths and appends the MM specifier.
- `scripts/validate-simplefb-mm-root-delta.py` parses both DTBs and rejects
  every node/property/reservation change except the allowlisted clock cells.
- `scripts/build-mm-root-candidate.sh` reconstructs exact G, preserves its
  kernel and initramfs, rebuilds the Android-v0 image, and runs the LK parser,
  canonical-ID, padding, address, placement and size gates.

The semantic clock cells are:

```text
Candidate G: 3 45
Candidate H: 3 45 6 6
```

The phandles `3` and `6` are observed values in the pinned DTB; builders resolve
them by path rather than assuming those numbers. Clock IDs 45 and 6 are the
Linux 7.1.3 binding values for `CLK_INFRA_DISP_PWM` and `CLK_TOP_MUX_MM`.

## Build result

Two independent builds from the exact source package were recursively
byte-identical. Both checksum manifests and every semantic/container gate
passed:

```text
boot image size:       6520832
boot image SHA-256:    594a83d4b48ad33688abb3e0c5ffd1914d6027c680d7799322f9379bef8f4b09
unchanged initramfs:   8dc85151bececf297f99b6f22c87316a54d0fa062e29c2c64ad00334b7ad0956
Candidate H DTB:       2054f0affec1ed5edff6b6a7de2a5d97102145c35fd335b4c0fd834571918a34
```

The laptop export is Git-ignored at
`artifacts/vm-export/boot-candidates/gemini-mm-root-H-final1/`. See
[`results/candidate-h-build-20260716.txt`](results/candidate-h-build-20260716.txt).

## Boot2 synchronization

The live GPT resolved logical `boot2` to unmounted, writable 16 MiB
`/dev/mmcblk0p30`; Gemian was running from `/dev/mmcblk0p29`, there were no
holders, AC was online, and the battery was 100%, Full and Good. A new private
full backup matched Candidate G. Candidate H was zero-padded to the exact
partition size, checksum-verified on the device, written with `fsync`, followed
by `sync` and a block-device flush. The complete post-write device checksum and
laptop readback matched:

```text
full boot2 SHA-256: a878bfce9d7335965cb60c3016f2dfac9f12d51550a17ba46e82af35183c68b0
```

No reboot occurred and no other partition was touched. See
[`results/boot2-write-candidate-h-20260716.txt`](results/boot2-write-candidate-h-20260716.txt).

## Runtime result and interpretation

In one owner-attended series of logical-`boot2` attempts, Candidate H visibly
progressed somewhat farther than Candidate G twice. On both of those attempts,
the backlight remained on while text was visible and then went off when the
screen became black. The exact visible duration was not reported. Later
attempts did not reproduce the same visible progress; their count and
backlight behavior were not reported, and there is no independent visual proof
that every no-output attempt reached the same boot stage.

The owner recalls a line approximately as `GEMINI FBCON TEST`. This is not an
exact transcription or photograph, but it is consistent with H's unchanged,
tracked initramfs marker `GEMINI_FBCON_TEXT_20260716_G`. No other tracked H path
emits a `GEMINI_FBCON` string. The content attribution therefore strongly
supports `/init` execution on at least one visible attempt, while the
approximate recollection does not establish which exact marker characters were
rendered. No heartbeat was reported as recognized. The kernel's final runtime
and power state after black remain unknown. See the sanitized
[`Candidate H runtime record`](results/runtime-candidate-h-20260716.txt).

The unreported duration does not establish whether either attempt reached the
30-second observation threshold. The eventual black screen and failed
reproduction do establish that appending only `CLK_TOP_MUX_MM` is insufficient
to produce a stable visible console. The intermittent result is compatible
with timing-sensitive retained bootloader state, but it does not identify a
particular clock or distinguish display-clock cleanup from an earlier,
variably reached boot stage. Because external `/init` runs after the synchronous
late-initcall unused-clock sweep, the content-attributed marker also makes a
broad `clk_ignore_unused` candidate a lower-value next step: the sweep had
already completed before the marker was drawn. Candidate I therefore keeps H's
kernel and DTB byte-identical and changes only `/init` to emit one timestamped
fbcon line per second before a silent hold. That test can place the
black/backlight-off transition relative to active console writes without adding
another guessed clock consumer. Rotation and broad clock retention remain
separate follow-ups until the timing boundary is measured.
