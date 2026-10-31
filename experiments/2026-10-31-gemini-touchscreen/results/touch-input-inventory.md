# Touchscreen input inventory

Scope: the vendor touch stack, board wiring, firmware contract and mainline
coverage for the named Gemini PDA. Vendor paths are relative to commit
`8cfe6596`; mainline paths to the pinned Linux 7.1.3 tree.

## 1. Board wiring and identity

- Controller: Novatek NT36xxx family at **I2C4 address `0x62`**
  (`novatek-nt36xxx-i2c.dtsi`, node `cap_touch@62`, compatible
  `mediatek,cap_touch`).
- Interrupt: **GPIO85 muxed to EINT8** (`ctp_pins_eint_as_int`,
  `aeon6797_6m_n.dts:603-611`); the driver selects the pinctrl state through
  `tpd_gpio_as_int(1)`.
- Reset: **GPIO68** (`ctp_pins_rst_output0/1`, `aeon6797_6m_n.dts:624-639`);
  the driver drives it through `tpd_gpio_output(0, level)`.
- An alternate Solomon node sits at I2C4 `0x53` (`ssd2092_touch.dtsi`,
  compatible `mediatek,solomon_touch`); the live baseline records it as
  **unbound**.
- Live identification: the Gemian baseline records `NVT-ts` bound at 4/`0x62`
  with EINT8 active, and trim bytes `00 00 03 72 66 03` selecting the
  NT36772 memory map (event buffer `0x11E00`).
- Board `&touch` node: `tpd-resolution = <1440 2560>`,
  `tpd-max-touch-num = <5>`, filter enabled with pixel density 192
  (`aeon6797_6m_n.dts:579-597`). The active panel is 1080x2160, so the public
  node's resolution does not match the panel; the live DTB may differ, as with
  the charger node.

## 2. Vendor driver stack

- `drivers/input/touchscreen/mediatek/` provides the MTK TPD wrapper
  (`mtk_tpd.c`, `tpd_*.c`): it owns the platform device, pinctrl states,
  resolution/key/filter DTS parsing, the input device and the suspend/resume
  path.
- The chip driver is `aeon_nt36xxx/` (`nt36xxx.c`, `nt36xxx_fw_update.c`,
  `nt36xxx_ext_proc.c`, `nt36xxx_mp_ctrlram.c`), bound by
  `compatible = "mediatek,cap_touch"` (`nt36xxx.c:1646`).
- Reporting: `MT_PROTOCOL_B` (`nt36xxx.h:62`), per-slot
  `input_mt_slot`/`input_mt_report_slot_state`, `ABS_MT_POSITION_X/Y`,
  `ABS_MT_TOUCH_MAJOR`, `ABS_MT_PRESSURE`, up to `TOUCH_MAX_FINGER_NUM`
  (10) in the protocol; the board's `tpd-max-touch-num` is 5.
- Wake gestures: the gesture table exists (`nt36xxx.c:207-221`, all mapped to
  `KEY_POWER`) but `WAKEUP_GESTURE` is **0** (`nt36xxx.h:63`), so gestures are
  not compiled in this build.
- Firmware update: `nt36xxx_fw_update.c` requests
  `BOOT_UPDATE_FIRMWARE_NAME = "novatek_ts_fw.bin"` (`nt36xxx.h:69`) at probe,
  compares the IC firmware version from `EVENT_MAP_FWINFO` with the binary's
  version at offset `0x1A000`, and updates only when the checksum or version
  indicates it should. The IC and bootloader I2C addresses are both `0x01`
  (`nt36xxx.h:36-37`).

## 3. Chip variant and firmware contract

- The trim table maps ID byte patterns to memory maps
  (`nt36xxx.c:174-260`). The Gemini's live bytes `… 0x72, 0x66, 0x03` are
  table entry 8, which selects the **NT36772** map: event buffer `0x11E00`,
  flash checksum at `0x14000`, raw/diff pipes at `0x10000`/`0x12000`
  (`nt36xxx.c:62-88`).
- The retained `novatek_ts_fw.bin` is 118,784 bytes with a structured header
  (first words `0x30 0x0 0xa038 0xe060 0x17700 0x188 0x1000 0x2fff`), and its
  firmware version at offset `0x1A000` is **0x05** with the complement
  **0xFA** (sum 0xFF, the driver's validity rule).
- The firmware is proprietary; only the version/checksum contract and the
  absence of a redistribution grant are recorded here.

## 4. Mainline coverage

- Upstream `drivers/input/touchscreen/novatek-nvt-ts.c` supports
  `novatek,nt11205-ts` (chip id `0x05`) and `novatek,nt36672a-ts`
  (chip id `0x08`). Binding requirements: compatible, reg, interrupts, and
  optional reset-gpios, vcc/iovcc supplies, `touchscreen-size-x/y`
  (`Documentation/devicetree/bindings/input/touchscreen/novatek,nvt-ts.yaml`).
- Its interface is different: it reads a parameter block at `0x78` and a
  fixed 6-byte-per-slot touch record block at `0x00`
  (`novatek-nvt-ts.c:23-60, 96-140`). The vendor Gemini driver instead uses
  the NT36772 SRAM event-buffer protocol at `0x11E00`.
- The upstream driver has **no firmware update** and no NT36772 compatible, so
  it cannot be selected by the board's `mediatek,cap_touch` node. Whether the
  Gemini controller also answers the upstream `0x78`/`0x00` interface is
  untested.
- Mainline therefore needs either a new compatible plus protocol support for
  the NT36772 event buffer, or a vendor-style driver; the existing upstream
  driver alone is not sufficient.

## 5. Limits

- Static reading only; no touch event was generated or read.
- The public board node's 1440x2560 resolution and 5-touch limit differ from
  the panel and from the driver's 10-slot protocol; the live DTB was not
  re-read in this study.
- Regulator rails for the controller are not described in the TPD node and
  were not traced.
- The firmware blob was not executed; only its header and version contract
  were read.
