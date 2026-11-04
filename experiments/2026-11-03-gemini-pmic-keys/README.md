# Experiment: Esc and the side key on the MT6351 PMIC

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-03-gemini-pmic-keys` |
| Status | `running`: both keys report on boot `fcb98505`; whether Esc reaches the console is awaiting the owner |
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

**Boot `fcb98505`.** Built at `d5daaff4`: package `b024a5df`, image `3e429f70`.
Run by the device session with the owner. Raw files are retained privately with
its evidence. The kernel stayed untainted, with no Oops, call trace or warning.
`mtk-pmic-keys` bound as `event0`.

| Uptime (s) | Event |
| --- | --- |
| 124.66 | Console blanked, lid open |
| 136.68–136.84 | Esc: `event0` keycode 1 down, up |
| 137.68 | `lid-guard` logs `console unblanked`, on its 1 s poll, so this isn't the wake's real time |
| 141.87–142.25 | Side key, lid open: `event0` keycode 231 down, up |
| 145.58 | Lid closed: `SW_LID` 1, keyboard inhibited |
| 146.59 | Console blanked |
| 147.30–147.67 | Side key, lid closed: `event0` keycode 231 down, up. The console stayed blanked |
| 149.92 | Lid open: `SW_LID` 0; console unblanked at 149.93 |
| 151.89–152.03 | Letter key after opening: `event1` keycode 34 down, up |

The owner on the blanked console: "pressing esc during a blanking worked to wake
it up".

`0x02b6` read `0x1201`: bit 9 set, bit 8 clear and bits 13:12 equal to 1, as
predicted.

## Analysis

- **Hypothesis confirmed.** Esc is the PMIC power key and the side key is the home
  key: each reports on the PMIC keys device and on no other. The press test on
  `0x0220` wasn't needed.
- **Closed lid.** The side key reports with the lid closed, as the owner wanted.
  It didn't wake the console in that state. The cause wasn't investigated.
- **Long-press reset.** The register holds the intended policy. The 11 s reset
  itself was not exercised.

**Not tested:**

- Whether Esc reaches the console as a key. The capture shows the event and the
  wake only, and the device session has asked the owner.
- Whether the matrix stays silent with the lid closed. No matrix key was pressed
  in that window, so step 4 rests on reading `gemini-lid`.
- Suspend and wake from either key.

## Open before upstream

- **Long press.** The register holds the intended policy, but the action has never run,
  so reset versus power-off is open. In one-key mode it sits on Esc, an ordinary typing
  key, so a key held for 11 s acts on the whole device. Whether to keep that is an owner
  decision.
- **Keys 0001, 0002, 0006 and 0007.** All four carry a placeholder author, and 0001 and
  0002 also say "Unsigned experiment draft". They can't be submitted until the owner has
  reviewed them and certifies them truthfully.
