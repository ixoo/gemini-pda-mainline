# Experiment: Gemini touchscreen input

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-touchscreen` |
| Status | `completed` for the static source, firmware-header and mainline-comparison study; no hardware behaviour is claimed |
| Subsystem | Novatek NT36xxx touch controller, MTK TPD wrapper, touch firmware, mainline NVT driver |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | M4 local interaction (calibrated multitouch) |

## Question or hypothesis

What controller and wiring does the Gemini touchscreen use, how does the vendor
stack read it, what does the retained firmware contain, and can the upstream
`novatek-nvt-ts` driver serve it?

The hypothesis was that the controller is an NT36xxx variant whose vendor
driver uses a different protocol from the upstream NVT driver, and that the
upstream compatible list does not cover it.

## Provenance and environment

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `drivers/input/touchscreen/mediatek/` (TPD wrapper),
  `.../aeon_nt36xxx/`, and the board DTS touch/pinctrl nodes.
- Mainline Linux 7.1.3: `drivers/input/touchscreen/novatek-nvt-ts.c` and its
  binding.
- Retained `novatek_ts_fw.bin` (118,784 bytes, private archive).
- Live baseline: [Gemian hardware baseline](../../docs/hardware/gemini-gemian-baseline.md)
  (NVT-ts at 4/`0x62`, EINT8, trim bytes, event map).
- Prior record: [input and backlight recovery](../2026-07-12-input-backlight-recovery/README.md),
  including its live NVT identity and firmware-request capture
  ([`nvt-live-trim-identity-20260714.txt`](../2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt)).

## Safety assessment

Read-only. No device access, no I2C/GPIO write, no firmware flash. The firmware
blob stayed private; only its size, header words and version bytes are recorded.

## Procedure

1. Read the board touch node and pinctrl states (bus, address, INT, reset).
2. Read the TPD wrapper and `aeon_nt36xxx` driver: probe, trim/chip selection,
   protocol, gestures, firmware update.
3. Read the retained firmware header and version/checksum contract.
4. Read the upstream NVT driver and binding; compare interfaces and compatibles.
5. Reconcile with the live baseline.

## Observations

- [Touch input inventory](results/touch-input-inventory.md) — wiring, vendor
  stack, chip-variant selection, firmware contract, mainline comparison.

Decisive observations:

1. Wiring is I2C4 `0x62`, INT on **GPIO85/EINT8**, reset on **GPIO68**; an
   alternate Solomon node at `0x53` is unbound.
2. The vendor stack is the MTK TPD wrapper plus `aeon_nt36xxx`, bound by
   `mediatek,cap_touch`, with `MT_PROTOCOL_B` slot reporting; the board caps
   reported touches at 5 while the protocol supports 10. Gestures are compiled
   out (`WAKEUP_GESTURE 0`).
3. The chip's trim bytes `…0x72,0x66,0x03` select the **NT36772** memory map
   (event buffer `0x11E00`, checksum `0x14000`), matching the live baseline.
4. The retained firmware is 118,784 bytes with version **0x05** at offset
   `0x1A000` and complement `0xFA`. It is requested 14 s after every probe and
   flashed only if the checksum or version check requires it; the 2026-07-14
   Gemian capture showed `firmware checksum match` and no update.
5. The upstream `novatek-nvt-ts` driver supports only NT11205/NT36672A via a
   `0x78` parameter block and `0x00` touch records, has no firmware update and
   no NT36772 compatible — a different interface from the vendor event-buffer
   protocol.
6. The public board node declares 1440x2560 while the active panel is
   1080x2160, so the live DTB (or the driver's scaling) must differ.

## Analysis

The Gemini touch input is a conventional NT36xxx SRAM/event-buffer design with
a vendor wrapper, not the register-window design the upstream driver models.
That makes the upstream driver insufficient even though the silicon family is
related: a mainline path needs NT36772 map support (or a board-specific
protocol implementation) and a new compatible, plus a decision about firmware
(the upstream driver cannot update it, and the vendor blob has no
redistribution grant).

The public DT's resolution and touch-count values are not usable as-is. They
also reinforce the pattern seen with the charger: the shipped DTB differs from
the public tree, and the live values must be read before a mainline node is
written.

## Conclusion

`confirmed`, scoped to the vendor tree, mainline tree, retained firmware header
and live baseline: the wiring, vendor stack and protocol, chip-variant
selection, firmware version contract, and the interface mismatch with the
upstream driver.

Not established: whether the controller also answers the upstream `0x78`/`0x00`
interface, the effective live resolution/touch count, the controller's
regulator rails, and any multitouch behaviour on hardware.

## Follow-up

- Durable summary: [Gemini touchscreen](../../docs/hardware/touchscreen.md).
- Next discriminating step: read the controller's `0x78` parameter block and
  chip-ID byte through the TPD debug interface, then a single-finger event
  capture, before choosing between extending the upstream driver and writing a
  board-specific one.
