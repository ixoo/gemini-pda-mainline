# Gemini GNSS kernel driver specification

This note turns the vendor `libmnl`/`mnld` GNSS stack into a contract a
mainline kernel driver can implement. It is a design record, not a claim of
working GNSS support: the receiver has produced no fix on mainline.

The protocol itself is described in the [GNSS hardware
document](gemini-gnss.md); the decompilation, function addresses and
confidence marks are in the
[GNSS reverse-engineering record](../../experiments/2026-11-01-gemini-gnss-re/README.md)
and the [link record](../../experiments/2026-11-01-gemini-gnss-link/README.md).
This note adds the part those records do not own: the driver state machine and
the firmware-image boundary.

## Scope and the current blocker

The mainline driver path is the CONSYS offload path: the position engine runs
on the connectivity microcontroller, the application processor sends GFNS
frames on STP task 2 and receives NMEA text in return. The stock Gemian path is
not settled; the latest inference is a host-side engine in `libmnl`, which
would still use the CONSYS transport and is not a kernel driver.

The engine is not in either retained `ROMv3` patch. The patch contains the
BORA porting layer and the GFNS protocol; it calls a separate image. The
vendor `gps_emi.c` maps that image at `gConEmiPhyBase + SZ_1M`, zeroes the
window and fills it from `/vendor/firmware/MNL.bin`. The patch's start path
loads a function pointer from a header word of that image and calls it.

The observed mainline start faulted at exactly that call. The inference is
that the engine image was absent, so the header word was not a valid function
pointer. The vendor source shows the load path and the file name; the retained
firmware set does not contain the file; the call site is the fault address.
That is strong evidence, not proof.

`MNL.bin` is not in the retained 2019 vendor firmware set, the device
userspace extraction, the private reference archive or the mainline artifact
set. The private Gemian dump is the complete vendor filesystem for this unit,
so the image is absent from the unit, not merely from a partial subset. A
driver can be written and built for a unit or image set that has the engine,
but the offload path cannot be demonstrated on this Gemini running Gemian.
The only remaining stock path is the host-side engine in `libmnl`, which is
userspace and not a kernel driver.

## What `libmnl` does, mapped to the kernel

`libmnl` is the host-side reference implementation. The kernel driver replaces
it, not the firmware.

| `libmnl` role | Function (RE address) | Kernel replacement |
| --- | --- | --- |
| GFNS frame builder | `FUN_0001ab4c` / splitter `FUN_0001ac8c` | frame builder in the driver |
| GFNS sender | `FUN_0001ad80`, generic send `FUN_0001b8ae` | `mt6797_consys_stp_send()` |
| RX scan and dispatch | `FUN_0001a89e`, `FUN_0001a944`, `FUN_0001b26c` | STP receive callback |
| Keep-alive builder | `FUN_0001b018`, sender `FUN_0001b0bc` | timer in the driver |
| 49-byte config sender | `FUN_0001b846` | start sequence |
| Start/stop user logic | `mtk_gps_ofl_mode_update` at `0x2dd48` | open/close state machine |
| NVRAM helpers | `FUN_0001b95c`, `FUN_0001bd34` | optional NVRAM mapping |
| NMEA reassembly | `FUN_00019bf8` | userspace (`gpsd`) |

The offload path is selected in the vendor daemon by
`mtk_gps_ofl_set_option(1)`; `mnld` only calls it for the 0x6797/0x6632 chips
and only when the FLP client has set the offload option. A kernel driver does
not need `mnld`, `libmnl`, the Android HAL or the position daemon.

## Wire contract

The full frame layout, checksum, type tables and channel rules are in the
[GNSS document](gemini-gnss.md). The driver needs these facts:

- Frame: `A5 00 TYPE LEN_HI LEN_LO SUM payload A3`; `SUM` is the low byte of
  the sum of header bytes 1 to 4.
- Host-to-MCU frames use channel byte 0. MCU-to-host frames put the NMEA
  output channel in the top three bits of byte 1.
- Type `0x0a` carries NMEA text. The driver streams the payload; it does not
  parse sentences.
- Type `0x35` is the firmware's 28-byte receive-status packet; type `0x36`
  resets the host counters. The host ACKs the firmware with type `0x7e`.
- Type `0x76` is the 11-byte keep-alive with a 32-bit counter.
- Types `5` and `6` are firmware assert and log messages. They use the
  vendor's own framing and must be logged, not treated as GFNS.

## Start sequence

The vendor `mtk_gps_ofl_mode_update` sends, in order:

1. `0x13` `MNL_INIT`, zero length.
2. `0x14` `MNL_INIT_CFG`, 49 bytes. The vendor passes the global config; the
   zero-length form is only the NULL-config fallback and is not the normal
   vendor path.
3. `0x44` `DEL_NV_DATA`, 4-byte bitmap. The current mainline driver sends an
   all-zero bitmap, which deletes nothing; that is conservative but is not the
   vendor's stored bitmap.
4. The NVRAM/init helpers.
5. `0x40` `HOST_START_GNSS`, zero length, once per added GNSS user.
6. `0x41` `HOST_STOP_GNSS` on the last stop.

`0x13` is the first frame and reaches the engine-image call. The `0x14`
configuration is sent afterwards, so a correct configuration cannot prevent a
fault caused by a missing or invalid engine image. The configuration still
matters for a valid start, and the empty fallback is not equivalent to the
vendor's 49 bytes.

The 49-byte configuration field names are recorded in the
[GNSS document](gemini-gnss.md): `if_type`, `pps_mode`, `datum`, `dgps_mode`,
`tcxo_mode`, `pps_duty`, `pps_port`, `u1ClockType`, `hw_Clock_Drift`,
`hw_Clock_Freq`, `if_link_spd`, `fix_interval`, `Int_LNA_Config`, two reserved
words, `GNSSOPMode`, `initU` and `lastU`. Patch 0439 sends the values `mnld`
builds for chip 0x6797 when no `mnl.prop` and no clock calibration record are
present: interface 1, DGPS mode 2, PPS duty 100, TCXO, 2000 ppb, 26 MHz,
115200 baud, a 1000 ms fix interval, the chip words `0x800000f0` and
`0xffff6797`, GNSS mode 2, and zero calibration words. A real device may use
different values from its own `mnl.prop` and NVRAM record; those inputs were
not retained.

## Firmware-image contract

The vendor `gps_emi.c` path is the model for the driver's optional engine load:

```text
gGpsEmiPhyBase = gConEmiPhyBase + SZ_1M
map 1 MiB at gGpsEmiPhyBase
memset the mapping
request /vendor/firmware/MNL.bin
copy the image into the mapping
```

The connectivity patch then expects a header at the start of the image; the
faulting call loads a function pointer from `+0x8` and passes two ROM strings.
In other words, the engine is a firmware image with a function table, not a
protocol message. The exact patch load and image addresses are kept in the
private analysis record rather than this document.

For mainline this means one of:

- the CONSYS owner or the GNSS driver requests `MNL.bin`, maps the 1 MiB
  window and copies the image before the first GFNS start; or
- the image is integrated into the existing WMT/ROM-patch download path; or
- the image is not available and the offload driver is not usable.

The driver must not silently start the firmware without the image. The
current safe behavior is what patch `0435` does: opening `/dev/gnss0` only
checks the link, and the start is opt-in.

## Driver state machine

The kernel side can be a `drivers/gnss` client over the existing CONSYS owner.
The interface already exists in the link series:

- `mt6797_consys_stp_attach(task, callback, context)`
- `mt6797_consys_stp_send(task, data, length)`
- `mt6797_consys_stp_detach(task)`
- the owner's WMT GPS function-on/off control
- `gnss_allocate_device()`, `gdev->type = GNSS_TYPE_NMEA`,
  `gnss_insert_raw()`

A minimal driver:

1. **Probe** allocates and registers the `gnss` device. It does not power or
   start anything.
2. **Open** attaches STP task 2, runs the link check, verifies that the engine
   image is available and loaded, switches the WMT GPS function on, optionally
   raises GPIO 69, and sends the start sequence.
3. **RX callback** validates the GFNS frame, dispatches `0x0a` payloads to
   `gnss_insert_raw()`, ACKs `0x35`/`0x36`, logs `5`/`6`, and never parses
   NMEA.
4. **Timers** send `0x76` keep-alives and the `0x7e` ACK when the flow-control
   window requires it.
5. **Close** sends `0x41`, switches the function off, detaches the link and
   stops the timers.
6. **Failure** logs the assert, stops transmitting, keeps draining the link,
   and lets the owner recover the CONSYS state. It does not retry inside the
   same firmware lifetime.

The owner remains responsible for common initialization, the ROM patches, the
calibration exchange, the rails and the AFE GPS words. The driver must not
duplicate those.

## Safety and privacy

- The start is a radio action and a firmware action. It stays opt-in until the
  engine image and the correct config are available.
- The GNSS firmware shares one microcontroller with Wi-Fi. A firmware assert
  can take the WLAN command path down even though the host link looks alive.
  Recovery is a CONSYS reload; the driver must not assume Wi-Fi is unaffected.
- Kernel logs carry frame types and counters, never sentence text or
  coordinates. Sentence text and any location-capable capture stay in private
  artifacts.
- The ROM patch and `MNL.bin` are vendor firmware. Their redistribution rights
  are unresolved; a mainline driver may support a user-supplied image, but the
  repository must not carry the image.

## Open items before implementation

| Item | Status |
| --- | --- |
| `MNL.bin` on this unit | absent from the private Gemian dump; the offload path is unavailable |
| Real 49-byte `MNL_INIT_CFG` values | `mnld` defaults are in patch 0439; a real `mnl.prop`/calibration record was not retained |
| NVRAM tolerance and the correct `0x44` bitmap | unknown |
| `0x7e`/`0x35` field layout and ACK cadence | types and 28-byte size known; fields unproven |
| Keep-alive period and the counter source | type and 11-byte shape known; cadence unproven |
| NMEA channel mapping | `byte1 >> 5`; per-channel behavior unproven |
| GPIO 69 / LNA population | board pin exists; physical LNA not established |
| Coexistence de-sense packet | not implemented; may matter with Wi-Fi/BT active |
| Stock Gemian path | inferred AP-side `libmnl`; needs a stock trace |

## Evidence

- [GNSS hardware document](gemini-gnss.md): protocol, ownership, firmware and
  userspace.
- [GNSS reverse-engineering record](../../experiments/2026-11-01-gemini-gnss-re/README.md):
  the `libmnl`/`mnld` decompilation, frame and type evidence.
- [GNSS link record](../../experiments/2026-11-01-gemini-gnss-link/README.md):
  T1 link pass, the T3 firmware assert, the `MNL.bin` inference and the
  current parked state.
- Vendor kernel `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `gps_emi.c`, `stp_chrdev_gps.c`, `stp_core.c`.
- Retained `ROMv3_patch_1_1_hdr.bin` and its load address; the patch
  call-through was cross-checked with Ghidra NDS32 in the private RE VM.
