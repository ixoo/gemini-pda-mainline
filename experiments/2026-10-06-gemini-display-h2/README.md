# Experiment: display H2, simple framebuffer holds the MM domain

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-display-h2` |
| Status | Driver option, profile and DT derivation; protocol draft for review; not booted |
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
  `MTK_SCPSYS` with adopt mode. The cmdline is unchanged and keeps
  `clk_ignore_unused`.
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
