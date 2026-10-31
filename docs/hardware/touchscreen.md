# Gemini touchscreen

Scope: the capacitive touch controller, its wiring, the vendor input stack, the
firmware contract and the mainline gap on the named Gemini PDA. This is a
static source, firmware-header and document study; no touch event has been
exercised here.

Evidence chronology is in the
[2026-10-31 touchscreen experiment](../../experiments/2026-10-31-gemini-touchscreen/README.md);
the live identity and binding are in the
[Gemian hardware baseline](gemini-gemian-baseline.md).

## 1. Identity and wiring

| Item | Value |
| --- | --- |
| Controller | Novatek NT36xxx family, I2C4 address `0x62` |
| Vendor binding | `mediatek,cap_touch` (`cap_touch@62` in the board DTS) |
| Interrupt | GPIO85 muxed to **EINT8** |
| Reset | GPIO68 |
| Alternate node | Solomon `solomon_touch@53` on I2C4, unbound on the live unit |
| Panel | NT36672, 1080x2160 (display) |
| Live driver name | `NVT-ts`, EINT8 active, trim bytes `…0x72,0x66,0x03` |

The public board node declares `tpd-resolution = <1440 2560>` and
`tpd-max-touch-num = <5>`, which do not match the 1080x2160 panel or the
protocol's ten slots. As with the charger node, the shipped DTB differs from
the public tree; the live values must be read before writing a mainline node.

## 2. Vendor input stack

- The MTK TPD wrapper (`drivers/input/touchscreen/mediatek/`) owns the platform
  device, pinctrl states, DTS parsing (resolution, keys, filter), the input
  device and suspend/resume.
- The chip driver is `aeon_nt36xxx/`, bound by `mediatek,cap_touch`. It uses
  **`MT_PROTOCOL_B`** slot reporting (up to ten slots in the protocol), with
  `ABS_MT_POSITION_X/Y`, `ABS_MT_TOUCH_MAJOR` and pressure.
- Wake gestures exist in the source but **`WAKEUP_GESTURE` is 0**, so they are
  not compiled in this build.
- The driver points the controller at the SRAM event buffer with a three-byte
  command and reads a fixed record block per interrupt; this is the NT36xxx
  SRAM protocol, not a simple register window.

## 3. Chip variant and firmware

- The trim table maps ID bytes to memory maps. The live Gemini bytes select
  **NT36772**: event buffer `0x11E00`, flash checksum `0x14000`, raw/diff pipes
  at `0x10000`/`0x12000`.
- `novatek_ts_fw.bin` (118,784 bytes) is requested at probe only when the IC's
  checksum or firmware version says an update is needed. Its header starts with
  `0x30 0x0 0xa038 0xe060 0x17700 0x188 0x1000 0x2fff`, and its firmware
  version at offset `0x1A000` is **0x05** with complement **0xFA** (sum 0xFF).
- The blob is proprietary and has no redistribution grant; the vendor driver
  is the only path that flashes it.

## 4. Mainline position

Upstream `novatek-nvt-ts` supports `novatek,nt11205-ts` and
`novatek,nt36672a-ts`, using a **`0x78` parameter block** and **`0x00`
six-byte-per-slot touch records**, with optional reset GPIO and vcc/iovcc
supplies. It has no firmware update and no NT36772 compatible.

The Gemini controller uses the NT36772 SRAM/event-buffer interface instead, so
the upstream driver cannot be selected by the board's `mediatek,cap_touch`
node. Two paths are possible:

1. extend upstream with NT36772 map/protocol support and a new compatible; or
2. add a board-specific driver over the vendor protocol.

Either way, the firmware question stays open: the upstream driver does not
flash firmware, and the retained blob is not redistributable.

## 5. Open questions

1. Does the Gemini controller also answer the upstream `0x78`/`0x00` interface
   (which would make a compatible-only mainline path possible)?
2. What are the live resolution, touch count and filter settings?
3. Which rails power the controller, and are they always on?
4. Does the existing firmware version (5) match the controller's flashed
   version, i.e. does the vendor update path ever run on this unit?

## 6. Evidence index

- Vendor kernel commit `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `drivers/input/touchscreen/mediatek/`, `aeon_nt36xxx/`, board DTS touch and
  pinctrl nodes.
- Mainline Linux 7.1.3: `novatek-nvt-ts.c` and
  `Documentation/devicetree/bindings/input/touchscreen/novatek,nvt-ts.yaml`.
- Retained `novatek_ts_fw.bin` (size, header words and version bytes only).
- [Gemian hardware baseline](gemini-gemian-baseline.md),
  [input recovery experiment](../../experiments/2026-07-12-input-backlight-recovery/README.md),
  [touchscreen experiment](../../experiments/2026-10-31-gemini-touchscreen/README.md).
