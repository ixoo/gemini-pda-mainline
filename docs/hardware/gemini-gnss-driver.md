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
not fully settled; the first second of a trace fits a host-side engine in `libmnl`, which
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

`MNL.bin` was not found in the retained 2019 vendor firmware set, the device
userspace extraction, the private Gemian dump or the mainline artifact set, and
the project owner states that it does not exist. The stock kernel also leaves
`CONFIG_MTK_GPS_EMI` unset, so its load path was not built for this unit. The
public stock Gemini Android 8.1 base also has no `MNL.bin`: its `system.img`
contains `libmnl.so`, `mnld` and `gps.conf`, but not the engine image. So this
specification cannot be demonstrated on this Gemini, and the work is parked. If
the engine is indeed absent, stock must use the host-side engine in `libmnl`,
which is userspace and not a kernel driver. A
[stock trace](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md) saw that path's DSP boot and no
GFNS frame. With assistance off and `mnld`'s start timer raised, 20 minutes of steady once-a-second DSP packets followed, including
per-channel records, and one satellite's live navigation subframes. Outdoors for 5 minutes it tracked up to 10 satellites, with no fix in that time. Stationary under open sky for 30 minutes it got a first fix at 158 s, GPS only and mostly intermittent.

## What `libmnl` does, mapped to the kernel

`libmnl` is the host-side reference implementation. The kernel driver replaces
it, not the firmware.

| `libmnl` role | Function (RE address) | Kernel replacement |
| --- | --- | --- |
| GFNS frame builder | `FUN_0001ab4c` / splitter `FUN_0001ac8c` | frame builder in the driver |
| GFNS sender | `FUN_0001ad80`, generic send `FUN_0001b8ae` | `mt6797_consys_stp_send()` |
| RX scan and dispatch | `FUN_0001a89e`, `FUN_0001a944`, `FUN_0001b26c` | STP receive callback |
| Keep-alive builder | `FUN_0001b018`, sender `FUN_0001b0bc` | work item, driven by bytes sent |
| 49-byte config sender | `FUN_0001b846` | start sequence |
| Start/stop user logic | `mtk_gps_ofl_mode_update` at `0x2dd48` | open/close state machine |
| UTC time sender | `FUN_0001b95c` | start sequence |
| NV download open | `FUN_0001bd34` | optional NVRAM mapping |
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
- Type `0x35` is the firmware's 28-byte acknowledgement of host traffic; the
  host reads it and does not answer it. Type `0x36` resets the host counters and
  enables the host's ACKs.
- The host ACKs with type `0x7e`, 28 bytes: received bytes as two `u32`s (low
  16 bits, then the rest), processed bytes, dropped bytes, a zero `rdrop`, packets,
  and a window of `0x10`. It sends one right after `0x36` and after every `0x800`
  received bytes. This is read from the decompile and has not run on the device.
- Type `0x76` is the 11-byte keep-alive, carrying the count of bytes the host has
  sent. It has no timer: the host sends it once more than `0x400` further bytes
  have gone out. Also read from the decompile, and not run on the device.

STP tasks 5 and 6 are separate from GFNS types. They carry firmware asserts and
logs in their own framing, and the CONSYS link engine parses and logs them, so
the driver's callback never sees them.

## Start sequence

This note uses the vendor sender's names. The firmware's own handler names appear
to be `MNL_INIT_API` for `0x13` and `MNL_INIT` for `0x14`; that mapping rests partly
on the vendor sender. The vendor `mtk_gps_ofl_mode_update` sends, in order:

1. `0x13` `MNL_INIT`, zero length.
2. `0x14` `MNL_INIT_CFG`, 49 bytes. The vendor passes the global config; the
   zero-length form is only the NULL-config fallback and is not the normal
   vendor path.
3. `0x44` `DEL_NV_DATA`, 4-byte bitmap. The current mainline driver sends an
   all-zero bitmap, which deletes nothing; that is conservative but is not the
   vendor's stored bitmap.
4. `0x83` `MNL_UTC_INIT`, 12 bytes, from the host clock.
5. `0x77` `NV_DOWN_OPEN`, 8 bytes. The vendor skips it when it has no stored NVRAM
   data, and patch 0439 leaves it out.
6. `0x40` `HOST_START_GNSS`, zero length, once per added GNSS user.
7. `0x41` `HOST_STOP_GNSS` on the last stop.

`0x13` is the first frame and reaches the engine-image call. The `0x14`
configuration is sent afterwards, so a correct configuration cannot prevent a
fault caused by a missing or invalid engine image. The configuration still
matters for a valid start, and the empty fallback is not equivalent to the
vendor's 49 bytes.

The 49-byte configuration field names are recorded in the
[GNSS document](gemini-gnss.md): `if_type`, `pps_mode`, `datum`, `dgps_mode`,
`tcxo_mode`, `pps_duty`, `pps_port`, `u1ClockType`, `hw_Clock_Drift`,
`hw_Clock_Freq`, `if_link_spd`, `fix_interval`, `Int_LNA_Config`, two reserved
words, `GNSSOPMode`, `C0`, `C1`, `initU` and `lastU`. Patch 0439 sends the values `mnld`
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
set EMI protection region 20 over that 1 MiB
map 1 MiB at gGpsEmiPhyBase
memset the mapping
request /vendor/firmware/MNL.bin
copy the image into the mapping
```

`mnld` starts this through an ioctl on `/dev/gps_emi`; the device also defines
NVRAM ioctls beside it. On the stock kernel `CONFIG_MTK_GPS_EMI` is unset, so this
describes the vendor's design, not something observed on this unit.

The connectivity patch then expects a header at the start of the image. The
faulting call loads a function pointer from a header word and passes two pointers
to firmware RAM structures. The patch also reads an engine version and a partition
table from that header, so the engine is a structured firmware image, not a protocol
message, and a flat copy is not proven to be enough. The exact patch load and image
addresses are kept in the private analysis record rather than this document.

Mainline's EMI regions 18 and 19 cover only the first 1 MiB of the 2 MiB reservation.
The firmware may not be able to read an image in the second without the equivalent of
region 20, so that policy has to be part of any load.

For mainline this means one of:

- the CONSYS owner or the GNSS driver requests `MNL.bin`, sets the protection, maps the
  1 MiB window and copies the image before the first GFNS start; or
- the image is integrated into the existing WMT/ROM-patch download path; or
- the image is not available and the offload driver is not usable.

When the load has to happen relative to WMT GPS function-on is not established.

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
3. **RX callback** runs in hard interrupt context. It validates the GFNS frame,
   dispatches `0x0a` payloads to `gnss_insert_raw()`, updates the counters and never
   parses NMEA. It cannot send, because `mt6797_consys_stp_send()` can sleep.
4. **A work item** sends the `0x7e` ACK and the `0x76` keep-alive when the byte
   counts above call for them.
5. **Close** cancels the work item, sends `0x41`, switches the function off and
   detaches the link.
6. **Failure** is handled by the link: it logs the assert, stops transmitting and keeps
   draining until the last detach. Later opens return `-EIO` and nothing recovers by
   itself. Recovery is a manual CONSYS reload, and `gnss-mt6797` has to be unloaded
   first because it holds `mt6797-consys`. There is no retry inside one firmware
   lifetime.

The owner remains responsible for common initialization, the ROM patches, the
calibration exchange, the rails and the AFE GPS words. The driver must not
duplicate those.

## DSP packets on the host path

Read from `libmnl` and checked against the [stock trace](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md): all 10717 captured
DSP frames pass the checksum. This is the `AA F0` path, not the GFNS offload path.

Frame: `AA F0`, a little-endian u16 whose low 12 bits are payload length plus 4 and high 4 bits a sequence number, a little-endian u16 ID, the
payload, a little-endian u16 sum of those four header bytes and the payload bytes, then `AA 0F`. Inside a frame, `DE DF` stands for `AA` and
`DE E0` for `DE`.

DSP measurement payload bytes are scrambled, and the checksum covers the scrambled bytes: descramble with a rotate right by 3, then XOR `0x59`. Host-to-DSP frames and the boot
acknowledgements `0xFE31` and `0xFE32` are not scrambled.

| ID | Payload | Content |
| --- | --- | --- |
| `0xFE28` | 8 bytes | Epoch header, first of each second |
| `0xFE29` | 57 bytes | One channel: byte 0 channel, 1 satellite, 2 constellation code (1 is GPS), 3 signal level (inferred C/N0 in dB-Hz), 5 inferred bandwidth, 6 state; `0x40` is required by the measurement API. The rest is not mapped |
| `0xFE2A` | 10 bytes | Header for a batch of `0xFE2B` frames |
| `0xFE2B` | 46 bytes | One navigation subframe: bytes 2 and 3 satellite, 4 subframe ID, and from byte 6 ten 4-byte words. Within a word, bytes 0, 3 and 2 hold the 24 data bits, most significant first, and byte 1 the parity |
| `0xFE2C` | 44 bytes | Closes the epoch |
| `0xFE30`, `0xFE37` | 57, 61 bytes | Once a second, not mapped; `0xFE30` carries one channel per epoch |
| `0xFE3A` | 5 bytes | Header for a batch of `0xFE3B` frames: byte 0 frame count, bytes 1 to 4 a millisecond counter in the layout below |
| `0xFE3B` | 14 bytes | One GLONASS string: byte 0 channel plus 8, bytes 2 and 3 string number, bytes 4 to 13 the 80 bits after the string number, with each byte pair swapped, then in standard GLONASS order |
| `0xFE4A`, `0xFE4B` | 10, 47 bytes | Same shape as `0xFE2A` and `0xFE2B`, probably BeiDou navigation data; not decoded |

Fields of `0xFE29`, from [step 5](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md#step-5-30-minutes-stationary-under-open-sky-radio-action-owner-approved). A 32-bit value at offset `o` is `r[o+1]<<24 | r[o]<<16 | r[o+3]<<8 | r[o+2]`.

| Offset | Content | Check |
| --- | --- | --- |
| 1 | Satellite. For GLONASS, the frequency channel plus 8, not the slot; a channel can be reused by another satellite, so take the slot from string 4 | Slot field and Doppler, 4 satellites |
| 2 | Constellation code: 1 GPS, 16 GLONASS, 32 BeiDou, 2 probably SBAS | GPS, GLONASS and BeiDou 11 by range; SBAS inferred |
| 21 | Whole transmit time: 1.5 s units for GPS; seconds of the day in Moscow time for GLONASS; BeiDou seconds of the week | Position solution for GPS; range fit for the others |
| 25 | Transmit time within that unit, in whole chips, 1534500 per 1.5 s for GPS, 511000 per second for GLONASS, 2046000 per second for BeiDou | As above |
| 29 | Fraction of a chip, u16 over 65536 | Residuals fall from tens of metres to a few |
| 31 | Doppler in Hz including the common clock drift: the signed 32-bit value over 65536 | 9 GPS satellites within about 25 Hz of a common offset over the run |
| 35 | Accumulated carrier phase, whole cycles; steps follow range rate | GPS slope 5.243 per m/s; quality not assessed |

With `T` the common receive time, the GPS pseudorange is `c * (T - (1.5 * r21 + (r25 + r29 / 65536) / 1023000))`. In [offline tests](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md#offline-analysis-2026-11-01), these fields alone gave a position in 1620 of 1641 seconds, using orbit data decoded from the same stream, and RTKLIB agreed. This ran on a stored capture from stock Gemian, not on a device, and nothing has run on mainline.

Byte 1 of each `0xFE2B` word holds the 6 parity bits, computed from the previous word's last 2 parity bits in the standard GPS way. Check them: 39% of frames failed in the capture.

Those GLONASS bits matched broadcast position and velocity exactly on 3 satellites.

## Booting and running the DSP on the host path

From the [step 5 capture](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md) and `libmnl`. Step 1's trace adds the stop. All 72737 frames in step 5 pass the checksum. This is what stock does, on stock Gemian: none of it has been reproduced by other code.

1. **Open.** Open `/dev/stpgps`, then ioctls 11 (co-clock flag), 10 (RTC flag), 7 and 8 (chip versions) in that order. The terminal ioctls `mnld` then tries fail with `EFAULT` and do not stop it.
2. **Boot header.** Send `0xFE08` with a 106-byte header, which `libmnl` fills with the image's size and addresses and with chip-dependent settings. The DSP answers `0xFE31`.
3. **Image.** Send the image as `0xFE0C` fragments: a little-endian u16 sequence number from 1, then up to 1400 bytes. Wait for `0xFE32` carrying that sequence number before the next one. On a failed try `libmnl` retries up to 5 times. Step 5 sent 44 fragments, 61440 bytes in all, in about 0.5 s. The whole image is embedded in `libmnl.so`: no separate `MNL.bin` was used.
4. **Started.** `0xFE2C` arrives first, about 7 ms after the last fragment.
5. **Setup.** Send `0xFE05` commands, each a little-endian u16 command then arguments. Step 5's order was 0x32, 0x0A, 0x32, 0x36, 0x2A, 0x34, 0x0F, 0x15.
6. **Every second,** in this order:

| ID | Payload | Content |
| --- | --- | --- |
| `0xFE00` | 4 bytes | A millisecond counter in bytes 2 and 3, +1000 a second, wrapping |
| `0xFE01` | 17 bytes | Host status, with the time of week in 1.5 s units at bytes 11 to 14, high half first, or all ones when unknown |
| `0xFE02` | 20 bytes, one per aided channel | Satellite, constellation, then predicted code phase and Doppler in Hz, and flags. The Doppler matched the following measurement within about 2 Hz. Mapped only in part |
| `0xFE03` | Lists of 2-byte pairs | Satellite and constellation, one list for tracking and one for search |
| `0xFE08` | 10 bytes | A setting, nearly constant, not mapped |
| `0xFE1C` | Empty | Ends the commands for the second |
| `0xFE05` | 2 bytes | Command 0x29 |

Less often: `0xFE04` (28-byte masks, all ones at start, 10 later), `0xFE07` (3 bytes, per satellite), `0xFE09` (45 bytes, per satellite, not mapped), `0xFE0A` (16 bytes, time-like), and `0xFE05` commands 0x0C and 0x1C. Host traffic is about 350 bytes a second and DSP traffic about 1200.

**Stop:** `0xFE05` with command 4. On a boot failure, `libmnl` sends it three times.

**Acquisition does not depend on `0xFE02`.** Most satellites first became valid before their first `0xFE02`, and none was sent until 38 s: satellite 7 was valid at 3 s. The search list alone seems to be enough to start. This run had saved state and host time, which may help. Whether the DSP keeps tracking without `0xFE02`, or runs at all without the other per-second frames, is not known. Their timeouts are not known either.

A free host would need: this transport, an image (vendor firmware, whose redistribution rights are unresolved), the frames above, and the [position solution](#dsp-packets-on-the-host-path) from the measurements.

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
| `MNL.bin` | not found in the retained sets, the private Gemian dump or the public stock Gemini Android base, and the owner states it does not exist; the offload path is unavailable |
| Image load | EMI protection, load timing and whether a flat copy is enough are unproven |
| Real 49-byte `MNL_INIT_CFG` values | `mnld` defaults are in patch 0439; a real `mnl.prop`/calibration record was not retained |
| NVRAM tolerance and the correct `0x44` bitmap | unknown |
| `0x7e`/`0x35` layout and ACK cadence | read from the decompile; not run on the device |
| Keep-alive rule and counter | read from the decompile; not run on the device, and whether the firmware needs it at low traffic is unknown |
| NMEA channel mapping | `byte1 >> 5`; per-channel behavior unproven |
| GPIO 69 / LNA population | board pin exists; physical LNA not established |
| Coexistence de-sense packet | not implemented; may matter with Wi-Fi/BT active |
| Stock Gemini path | the stock Android system has `libmnl.so`, `mnld` and `gps.conf` but no `MNL.bin`; the host-side path is the likely stock path; no stock trace yet; the Gemian DSP boot and 20 minutes of packets after it were [traced](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md) and partly decoded; up to 10 satellites tracked outdoors, no fix in 5 minutes |

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
- [Stock Gemini Android 8.1 base](https://github.com/Wenri/planet-pda-archive/releases/tag/firmware-2020):
  `gemini_x25_x27_base.zip`, SHA-256 `dd04e310459e6cbd9043ae0165e17261c27543f3707a221237c1bcb7aba354b1`.
  Its `system.img` contains `libmnl.so`, `mnld` and `gps.conf`, and no
  `MNL.bin`.
