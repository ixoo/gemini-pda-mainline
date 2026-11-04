# Experiment: Esc and the side key on the MT6351 PMIC

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-03-gemini-pmic-keys` |
| Status | `running`: patches written and compile-checked in the VM, no Buildbox build or boot yet |
| Subsystem | input: `mtk-pmic-keys` on the MT6351 |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-03 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

The owner found two keys that do nothing on the station: the outside side key,
and Esc, which doesn't wake a blanked console. Boot `64622312` captured no
events from the side key on any of the three input devices, and no interrupt
moved for it.

Hypothesis: both are MT6351 PMIC keys. Esc is the power key and the side key is
the home key. The station has no PMIC keys node, so neither reaches Linux.

## Evidence so far

Read from retained images and public source. None of this is a live measurement
of the side key.

- **LK.** Its key routine at `0x46004904` handles code `0x11` by calling
  `0x4600d378`, whose log string names `pmic_detect_homekey`. It reads PMIC
  `0x0220` bit 2, and a clear bit means pressed. Code 8 reads bit 1 the same way.
  Other codes read the SoC keypad. LK selects boot2 from code `0x11`
  ([audit](../2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt)).
- **Vendor device tree.** `mediatek,kpd-hw-rstkey` is 17 and
  `mediatek,kpd-sw-rstkey` is 231, `KEY_SEND`. The public default is 115.
- **Gemian driver.** The power key is reported as `KEY_ESC`, the home key as the
  device-tree keycode.
- **Earlier mainline test.** C1 had a power-key child and a press reached
  userspace as `KEY_POWER`
  ([record](../2026-10-04-gemini-c1-preparation/README.md#c1-follow-up-boot-2026-10-06)).
- **Matrix.** The [key map](../2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt)
  has no Esc entry.

**Owner statement:** the outside side key is the button held to select boot2
("Yes, same button"). With the LK code above, that places the key on the PMIC home
line. No reading of that register during a press exists yet, so the alternatives
stay open until the test: GPIO93/EINT16, which the vendor calls anti-tamper, and
the SoC keypad.

## Change

- [0530](../../patches/proposals/0530-arm64-dts-mediatek-gemini-station-add-the-PMIC-keys.patch)
  adds the station's `mediatek,mt6351-keys` node: `KEY_ESC` for the power key and
  `KEY_SEND` for the home key.
- `patches/series-a53-station` gains keys patches 0001, 0002, 0006 and 0007, as C1
  had. Without 0007 the driver writes the seconds value into the selector field,
  so `power-off-time-sec = <11>` would select 5 s.

The driver rewrites the long-press policy at probe, and an absent mode disables
the reset. The node sets one-key reset at 11 s, from Gemian's configuration.
Holding Esc for 11 s is therefore expected to reset the device, so the test
below doesn't hold it that long.

**Checked:** the full station series applies with `git apply --unidiff-zero`.
`mtk-pmic-keys.o`, `mt6397-core.o` and both station DTBs build with `W=1`, the
binding check passes, and `CHECK_DTBS` reports nothing against the keys binding.
**Not checked:** no Buildbox build, no boot.

## Test (predeclared)

Before the new image, if convenient, on the running station: sample `0x0220`
through the PMIC regmap while the owner holds the side key, then taps Esc.

On the first boot with 0530:

1. A new `mtk-pmic-keys` input device binds. Read `0x02b6`: expect bit 9 set, bit 8
   clear and bits 13:12 equal to 1.
2. Esc: `KEY_ESC` press and release, the blanked console wakes, and the console
   receives Esc. Keep the press short.
3. Side key: `KEY_SEND` press and release, with the lid open and with it closed.
4. With the lid closed the matrix stays inhibited, so its keys report nothing.

**Decisions.**

- If 2 fails to report, the node or IRQ path is wrong: read `0x0220` during a press.
- If Esc wakes the console but types nothing, add keycode 1 to the station console
  keymap.
- If the side key reports nothing and `0x0220` bit 2 doesn't move, the hypothesis
  is wrong for that key. Drop `home-key`, then sample GPIO93 during a press.

## Observations

None yet.
