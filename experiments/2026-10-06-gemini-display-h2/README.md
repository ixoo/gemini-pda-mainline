# Experiment: display H2, simple framebuffer holds the MM domain

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-display-h2` |
| Status | Built and package-verified; protocol draft for review; no candidate; not booted |
| Profile | `mt6797-a53-display-h2-compile` |
| Date | 2026-10-06 |
| Device action | None |

## Purpose

Roadmap step 5 starts with display adoption: the loader-initialised panel
stays on the simple framebuffer, which should hold the MM power domain and its
root clocks, so that `clk_ignore_unused` can later go
([display record, H2](../2026-10-04-gemini-display-re/README.md#part-3-what-mainline-needs-beyond-the-retained-simplefb)).
This experiment is the first half: attach the MM domain with no power
transition. Removing `clk_ignore_unused` is a later, separate step.

## Finding that shaped the design

Mainline's legacy `mtk-scpsys` already supports MT6797, and the parent DT
already has the SCPSYS node (four named clocks and `infracfg`). But its probe
powers every domain on, then lets genpd switch unused ones off at late init
and at provider `sync_state`. On MT6797 that sequences all twelve domains,
including the four GPU cores and MJC. `pd_ignore_unused` would not stop the
`sync_state` power-off. Simply enabling SCPSYS is therefore an unreviewed
power-sequencing effect.

## Change

[display/0001](../../patches/v7.1.3/display/0001-pmdomain-mediatek-scpsys-optionally-adopt-the-boot-loader-domain-state.patch)
adds the default-off `CONFIG_MTK_SCPSYS_ADOPT_BOOT_STATE`. Each domain is
registered in the state found:

- **On.** It takes its regulator and clock references and stays on for the
  whole boot. Provider `sync_state` is disabled, so `stay_on` is never
  cleared.
- **Off.** It stays off.
- **Disagreeing status bits.** It is kept on and reported.

No power-control register is written at probe. Each domain logs
`adopt: <name> on|off`.

## Profile and candidate DT

- `mt6797-a53-display-h2-compile`: the 107 board-services patches plus
  display/0001. The fragment keeps the board-services RTC scope and adds
  `MTK_SCPSYS` with adopt mode. It also turns on `MTK_INFRACFG`, which
  `MTK_SCPSYS` selects and the handoff fragment disables. That is a helper
  library: its only init code targets MT8192, and its bus-protection helpers
  run only on SCPSYS power on and off, which adopt mode never calls at probe.
  The cmdline is unchanged and keeps `clk_ignore_unused`.
- [display-h2-dt.sh](display-h2-dt.sh) runs the board-services DT derivation
  on the exact C1-5 parent, then adds one property:
  `/chosen/framebuffer@7dfb0000 power-domains = <&scpsys 3>` (MM). It checks
  that the provider is the legacy MT6797 SCPSYS and that the decompiled
  difference is exactly that line. The output is reproducible: SHA-256
  `679a336900541244b912305dbf663c05db8e9888e7693c929f32562e16444b77`.
- **Schema.** No new diagnostic relative to the board-services derived DT,
  against the 107-patch tree schema `e067ef24…`. The display patch changes no
  binding.

## Protocol draft (for the custodian's review)

Hypothesis: with adopt mode, SCPSYS reports the MM domain on, the framebuffer
attaches to it, and nothing powers on or off.

Effects admitted: SCPSYS probe reads the status registers and enables the
clock gates of domains already on, which are loader-enabled and kept under
`clk_ignore_unused`. The framebuffer's genpd attach finds MM already on. No
power-control, bus-protection or SRAM register is written. Everything else is
as board-services.

Observations, before recovery:

1. All twelve `adopt:` lines, and that MM is reported on.
2. simplefb probe success and the console still visible on the panel.
3. No SCPSYS warning, timeout or `WARN`.
4. Board-services serviceability: USB SSH, keyboard, eMMC, watchdog, and the
   CPU masks as the laptop pinned them for board-services.

Decision branches:

- **MM on, simplefb attached, panel lit.** H2a holds. Next is a separate step
  to remove `clk_ignore_unused`, which needs the missing clock gates
  identified first.
- **MM reported off.** Contradicts the loader-lit panel. Stop, and keep the
  log for the status-bit question.
- **Disagreeing bits or any SCPSYS warning.** Stop; no further display step.
- **simplefb fails to attach.** Inspect the genpd error; no retry in the same
  boot.

## Validation

- Local `W=1` compile of `mtk-scpsys.o` with the board-services config plus
  the two options: no warnings. checkpatch `--strict`: clean.
- The 108-patch series reproduces the author tree. ShellCheck passes on the
  script, which also refuses an existing output.

## Build

The first submission at `a9b2d086` stopped at the build's config check:
`MTK_SCPSYS` selects `MTK_INFRACFG`, which the handoff fragment requests off.
`98e2cdc4` enables it explicitly (see Profile).

| Item | Value |
| --- | --- |
| Input commit | `98e2cdc4072e691ecd472c25296474d5ac6ffa1e` |
| Job | `98e2cdc4…-mt6797-a53-display-h2-compile-m0`, buildbox-1, 32 jobs |
| Package inventory | `92b8731ec5ac9b6e4c0c237362d2b26d4adf9b594f27e773839a6b4ca4745f84` |
| Release | `7.1.3-gemini-a53-display-h2-compile` |

Compilation, remote validation, fetch and local checksums pass, with no
compiler warning. The resolved config has `MTK_SCPSYS`,
`MTK_SCPSYS_ADOPT_BOOT_STATE` and `MTK_INFRACFG`; the cmdline still carries
`clk_ignore_unused`. The packaged DT is not the candidate DT.

## H8 follow-on: PWM backlight under the simple framebuffer

H8 needs no new kernel: the H2 package already has `PWM_MTK_DISP` and
`BACKLIGHT_PWM` built in. [display-h8-dt.sh](display-h8-dt.sh) runs the H2
derivation, then:

- **`/pwm@1100f000`.** Status okay, with a newly allocated phandle.
  `assigned-clocks = <&topckgen CLK_TOP_MUX_PWM>` and
  `assigned-clock-parents = <&clk26m>`. That reparenting is needed: mainline
  has no ULPOSC root rate, so a ULPOSC parent reads 0 Hz and would program a
  zero duty
  ([display record, H8 preflight](../2026-10-04-gemini-display-re/README.md#h8-preflight-finding-2026-10-06)).
- **`/backlight`.** `pwm-backlight` on that PWM, with a 39385 ns period
  (1024 cycles at 26 MHz, about 25 kHz), levels 0 to 1023 interpolated, and
  default 512.
- **Checks.** The decompiled difference must be exactly these edits. The
  output is reproducible: SHA-256
  `cc89c643d6842df5ae6a03176de2b60c7a4d05d650d3de982f3d0b14549f49b3`. There is
  no new schema diagnostic relative to H2.

Protocol draft, to run only after an H2 pass:

- **Admitted effects beyond H2.** One `pwm_sel` mux write to `clk26m` at PWM
  probe; PWM enable, divider, period, high-width and commit writes from the
  first backlight apply; the brightness change to level 512. There is no
  ULPOSC, sleep-controller or panel access.
- **Observations.**
  - `pwm-backlight` and `disp_pwm` bound.
  - `/sys/class/backlight/backlight/brightness` and `actual_brightness` read
    512.
  - The panel stays lit; the owner checks the screen at level 512, then 100,
    then 900 (three writes), and judges flicker.
- **Branches.**
  - Lit and tracking: H8 holds.
  - Dark after probe: record the brightness values, restore by reading the
    log over USB SSH, and go to recovery. A fixed-rate or calibrated ULPOSC
    description is then needed.
  - Probe failure: the loader's backlight setting is untouched; record the
    error.
