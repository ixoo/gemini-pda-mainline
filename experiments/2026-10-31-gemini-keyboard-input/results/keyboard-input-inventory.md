# Keyboard input inventory

Scope: vendor keyboard driver and DTS, the shared Planet keyboard
documentation, and the boot-chain key handling for the named Gemini PDA.
Vendor paths are relative to commit `8cfe6596`; LK paths to `f4988d74`.

## 1. Matrix and keymap

`drivers/misc/mediatek/aw9523/aw9523_key.c:130-205` holds the 56-position table
(8 rows on `P0`, 7 columns on `P1`, column-major order). 52 positions carry a
keycode; four carry `KEY_UNKNOWN`:

| Position | Row | Column |
| --- | --- | --- |
| `P0_7 / P1_3` | 7 | 3 |
| `P0_7 / P1_4` | 7 | 4 |
| `P0_7 / P1_5` | 7 | 5 |
| `P0_7 / P1_6` | 7 | 6 |

The shared Planet documentation (`planet-psion-kpd-driver/docs/key-matrix.md`)
independently gives the same map and states that those four positions are
unconnected, and that Gemini, Cosmo and Astro use the same keyboard PCB. That
resolves the earlier "four vendor-unknown contacts" as unpopulated positions,
although no electrical measurement confirms it.

The same table shows the modifier at `P0_4/P1_3` as `META-L` =
`KEY_LEFTMETA`. The Planet comparison document says Gemini and Cosmo report
`KEY_LEFTMETA` and only Astro reports `KEY_FN`; the earlier source/binary
discrepancy is therefore a device-family mix-up, not two snapshots of the same
board.

## 2. Scan, timing and ghosting

- Monitor mode arms the AW9523 port interrupts; the EINT handler disables the
  IRQ, schedules work after 1 ms, and the work disables the port interrupt,
  clears it, and schedules a fast rescan (`:566-577`, `:543-563`).
- Two rescan periods: `MATRIX_SCAN_NANO_SECONDS_FAST` 1 ms and
  `MATRIX_SCAN_NANO_SECONDS_SLOW` 10 ms (`:126-127`). Held keys rescan slowly;
  fresh changes rescan fast.
- The scan drives one `P1` column low at a time, reads all eight `P0` rows, and
  compares against the previous snapshot (`:391-406`).
- Ghosting: if two rows are pressed in one column, ambiguous positions are
  blocked until a modifier is released. The source comment gives
  Ctrl+LShift+N (which would also show M) as the example, and a dedicated
  branch masks z/x/c/v during Ctrl+Shift so shortcuts keep working
  (`:408-458`).
- Presses are reported before releases so a release that unblocks a key cannot
  drop a held modifier (`:488-501`).
- Columns 3 and 6 are swapped before event generation, with the comment "I'm
  not sure why these are swapped" (`:460-468`).
- Event device: `input_report_key` presses/releases only; no MSC scan codes,
  no LED registration.

## 3. Lid, screen and wake

- `CONFIG_AW9523_HALL` is defined; the driver registers a hall notifier
  (`:929-930`) and sets `is_device_closed` from `hall_fcover_lid_closed`.
- When the lid is reported closed, the interrupt work returns early and forces
  all keys released (`:371-380`, `:516-520`).
- The hall driver is built (`CONFIG_MTK_HALL=y`), its DTS node is enabled, and
  its pin is **GPIO66** (`mt6797.dtsi:4295-4316`, `drivers/input/hall/hall.c`).
  This is the same signal the project's lid work observed.
- `CONFIG_AW9523_FB` (screen-off suppression) is commented out, so screen state
  does not gate the matrix.
- No wakeup registration exists in the keyboard driver: no
  `device_init_wakeup`, no `enable_irq_wake`, no `input_dev` wakeup flag. The
  matrix is not a wake source. The PMIC power button is.
- The Planet comparison table lists "Hall-sensor key suppression" as absent on
  Gemini and present on Cosmo/Astro, which conflicts with this source; treat the
  source as the vendor behaviour and the table as unverified for Gemini.

## 4. Power key, boot chain and firmware

- The physical power button is a PMIC key, not an AW9523 position. On Android,
  bare power reports `KEY_ESC`; `Meta + Esc` is the power action. The Gemini HAL
  does not implement the interlock, so the combination is userspace policy
  (Planet `docs/device-comparison.md`).
- Preloader (retained image): detects the power key, logs
  `[PMIC_PRELOADER] pl pmic powerkey Press/Release`, sets KPD GPIO mode
  (`Enter mtk_kpd_gpio_set!`), and uses power-key state in RTC boot checks and
  USB enumeration skip decisions.
- LK (`platform/mt6797/mtk_key.c:46-100`, `mt_pmic.c:192`,
  `platform.c:714-715`): `set_kpd_pmic_mode()`, PMIC power-key detection, PMIC
  KPD clock enable/disable, and boot menus driven by PMIC volume keys
  (`mt_boot.c` strings: "Press the Volume UP/Down buttons…"). LK never touches
  the AW9523 matrix.

## 5. Backlight, LEDs and address

- Gemini has no keyboard backlight (Planet comparison: "Backlight: none").
  The AW9523 LED-mode (`0x12/0x13`) and `DIM0..15` (`0x20-0x2F`) registers are
  defined in the vendor header but never written by the keyboard driver.
- `aw9523_key.h:44-45` defines `IIC_ADDRESS_WRITE 0xB0` (7-bit 0x58), a stale
  value from an earlier reference design. The driver uses the I2C client
  address from the DT (`reg = <0x5b>`), which matches the live device. The
  shared Planet documentation calls the header value incorrect for production.

## 6. Independent documentation comparison

`planet-psion-kpd-driver/docs/device-comparison.md` for Gemini:

| Feature | Gemini | Matches this tree? |
| --- | --- | --- |
| AW9523B matrix | yes | yes |
| Backlight | none | yes (registers unused) |
| `P0_4/P1_3` | `KEY_LEFTMETA` | yes |
| Scan timing | 1 ms active / 10 ms idle | yes |
| MMIO style | `*(volatile u16 *)` | not checked here |
| Hall key suppression | no | **no** — source registers a notifier and suppresses |
| FM radio wakeup guard | yes | not present in this file |
| Meta+Power interlock | no (userspace) | yes |

The two "no" rows are the conflicts to resolve by observation, not by copying
either document.

## 7. Limits

- Static reading only; no key was pressed and no lid state was changed in this
  study.
- The lid suppression and wake conclusions are source-level.
- The unconnected positions are documented but not electrically measured here.
- Latency, debounce and rollover remain unmeasured; the ghosting workaround is
  a vendor policy, not proof of diode isolation.
