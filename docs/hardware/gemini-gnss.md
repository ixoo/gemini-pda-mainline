# Gemini GNSS and navigation

This document records how the stock Gemian system turns the Gemini's GNSS
receiver on, moves its data, computes and reports a position, and what else on
the device participates in navigation. It is a description of the working
vendor stack, not a Linux implementation.

> **Correction, 2026-11-01.** The first GFNS start caused a firmware exception. The
> [link record](../../experiments/2026-11-01-gemini-gnss-link/README.md#t3-result-the-start-sequence-causes-a-firmware-exception-2026-11-01)
> infers the first cause is an `MNL.bin` image this device lacks. If so, a GFNS client alone
> is no path to a fix, and "What is *not* required" and the claims that `mnld` falls back to
> a serial port and that sentences come from ROM are wrong. A
> [stock trace](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md) then saw stock start with
> `libmnl`'s DSP boot and `AA F0` frames over STP task 2, with no GFNS frame, then, with assistance off, 20 minutes of DSP packets, including one GPS satellite's live navigation subframes, so the RF path works on stock. Stationary under open sky, stock later got an intermittent GPS-only fix after 158 s. Offline, that capture's raw measurements alone gave a position on almost every second. A later minimal host, with `mnld` stopped, booted the DSP and tracked up to 13 satellites on the stock kernel.

The evidence is a static review of the retained 2019 vendor binaries and the two
CONSYS ROM patch images in the private artifact set, plus the pinned GPL vendor
kernel and the repository's Wi-Fi/connectivity records. See the
[GNSS reverse-engineering experiment](../../experiments/2026-11-01-gemini-gnss-re/README.md)
for exact inputs, methods and confidence marks. No GNSS fix has been produced on
mainline; this document does not change that.

## Summary

The Gemini has no discrete GNSS chip and no GNSS serial port. The receiver is
part of the MediaTek MT6797 CONSYS block, and the position engine runs on the
CONSYS microcontroller (MediaTek calls the GNSS core "BORA"). The application
processor never touches GNSS registers directly.

The stock path is:

```text
Android location API
      |  Binder
gps.mt6797.so (HAL, socket shim)
      |  local datagram socket mtk_hal2mnl / mtk_mnl2hal
mnld  (daemon: state machine, NVRAM, EPO, AGPS, FLP, MPE)
      |  libmnl.so (GFNS protocol, framing, ACK, NMEA parse, assist)
      |  /dev/stpgps  (vendor char device, STP task 2)
vendor mtk_stp_GPS_chrdev  ->  WMT / STP over BTIF
      |
CONSYS MD32: ROM + ROMv3 patch 1_1 (BORA porting, GFNS, FLP, NVRAM)
      |
BORA GNSS engine -> NMEA 0183 sentences
```

Three consequences matter for mainline work:

1. **The wire protocol is a framed binary transport that carries NMEA text.**
   The microcontroller emits ordinary NMEA sentences (`GGA`, `GSA`, `GSV`,
   `RMC`, `VTG` and an MTK accuracy sentence) inside the binary frames. A
   standards-shaped `gnss` device is therefore reachable without the vendor
   position daemon, contrary to the earlier assumption that positions required
   MediaTek's proprietary MNL library.
2. **Turning GNSS on is small; keeping it fed is not.** Function-on is one WMT
   command plus one GPIO. The firmware also expects an initialization
   configuration, a keep-alive and flow-control acknowledgements before it
   produces sentences; clock calibration and stored almanac/ephemeris determine
   accuracy and time-to-first-fix.
3. **Assistance is separate.** SUPL, EPO and sensor dead reckoning are optional
   userspace services above the same transport. They improve time-to-first-fix
   but are not needed to receive a fix.

The description below is the vendor Android stack. The offload path is only
selected when a fused-location-provider client declares `flp_mnl_mode = 1`
(see [Userspace](#userspace)); whether a reduced Gemian session does that is
not established, and if it does not, the daemon would fall back to a serial
path that does not exist on this board.

## Hardware and ownership

The receiver has no device-tree node of its own with registers, interrupts,
clocks or supplies. `mt6797.dtsi` describes it with two property-less
pseudo-nodes, `gps { compatible = "mediatek,gps"; }` and
`gps_emi { compatible = "mediatek,gps_emi-v1"; }`. Every hardware resource
belongs to `consys@18070000` and to the BTIF block:

| Resource | Owner | GNSS role |
| --- | --- | --- |
| CONSYS power, clocks, reset, protection | `consys` / WMT | Whole subsystem, including GNSS |
| VCN18, VCN28, VCN33 | CONSYS power-on sequence | VCN28 is the "FM/GPS" analog rail, 2.8 V |
| AFE window `0x180b6000` (0x100 bytes) | CONSYS power-on | GPS receive words `WBG_GPS_01/02` at `+0x50`/`+0x54` are written before firmware starts |
| BTIF + STP | WMT / STP | Single multiplexed link shared by Bluetooth, FM, GNSS and WMT |
| GPIO 69 | Board pinctrl | GPS LNA control: low at init, high while GNSS is on |
| TCXO / co-clock | `WMT_SOC.cfg` `co_clock_flag = 0` | GNSS uses its own TCXO, not a shared crystal |

The board DTS defines four pinctrl states for GPIO 69 (`gps_lna_state_init`,
`_ol`, `_oh` and deinit). The vendor GNSS "on" selects the high state, "off"
returns to init. Whether a physical LNA is populated is still not established;
the software contract is only "GPIO 69 high while GNSS is on".

The vendor kernel also defines a "GPS PA LDO" (VCN28) branch, but it is dead on
this device: it needs a non-zero co-clock flag, and the retained `WMT_SOC.cfg`
sets `co_clock_flag = 0`. VCN28 is therefore enabled by the common CONSYS
power-on, not by GNSS-on.

## Kernel boundary

Two vendor character devices exist; only one carries GNSS data.

### `/dev/stpgps` — the data path

`stp_chrdev_gps.c` registers a character device with static major 191 and a
single task. Its entire content is "bytes for STP task 2":

- `write()` → `mtk_wcn_stp_send_data(buf, len, GPS_TASK_INDX)`, at most 16 KiB
  per call, returns `-ENOSPC` when the STP window is exhausted.
- `read()` → `mtk_wcn_stp_receive_data(buf, len, GPS_TASK_INDX)`; on an empty
  queue it sleeps on a wait queue woken by the STP event callback.
- No framing, parsing or protocol knowledge exists in the kernel. The payload
  is opaque, including the GFNS header and the NMEA text inside it.
- `GPS_TASK_INDX` is 2. The per-task receive ring is 16 KiB
  (`MTKSTP_BUFFER_SIZE`).
- Open calls `mtk_wcn_wmt_func_on(WMTDRV_TYPE_GPS)`, registers a reset
  callback, requires `mtk_wcn_stp_is_ready()`, registers the task-2 event
  callback and takes a wakeup source named `gpswakelock`. Close reverses this
  with `mtk_wcn_wmt_func_off(WMTDRV_TYPE_GPS)`.
- Ioctls expose only chip hardware/firmware version, the co-clock flag, a
  firmware-assert trigger and wakelock take/give. None configures the receiver.

The first WMT function to open runs the whole common CONSYS initialization:
power, BTIF/STP setup, mode negotiation, ROM patch download, calibration and
coexistence setup. GNSS gets no shortcut; it must share that owner. The chip is
powered down only when BT, GPS, FM, Wi-Fi, LPBK, ANT and COREDUMP are all off.

STP full-mode frames are built in `stp_core.c` as:

| Byte | Value |
| --- | --- |
| 0 | `0x80 \| (txseq << 3) \| txack` |
| 1 | `(task << 4) \| (len >> 8)` |
| 2 | `len & 0xff` |
| 3 | sum of bytes 0..2 |
| 4.. | payload |
| last 2 | CRC-16 over the payload |

A GPS frame therefore carries `0x2n` in byte 1. When the GNSS receive ring is
full the STP core discards the GNSS queue instead of back-pressuring the peer
(`mtk_wcn_stp_flush_rx_queue(GPS_TASK_INDX)`); no other task is treated this way.

### `/dev/gps` — an unused mailbox

`gps.c` (enabled because `CONFIG_MTK_GPS_SUPPORT` selects `CONFIG_MTK_GPS`)
creates `/dev/gps`, a 4 KiB userspace-to-userspace mailbox, and the sysfs
directory `/sys/class/gpsdrv/gps/`. Its hardware hooks are null, so `pwrctl`
only logs. `mnld` writes `pwrctl`, `status`, `state`, `suspend` and `pwrsave`
there to record its own state machine, and the device node itself is never
opened by the observed stack. It is a leftover of the serial MT3326 design.

`gps_emi.c` would map a 1 MiB region and copy `MNL.bin` into it for the
"MNL in EMI" variant. `CONFIG_MTK_GPS_EMI` is not set, the image is not in the
firmware inventory, and `/dev/gps_emi` is absent. The separate, *used* kind of
offload is different: it runs MNL/BORA on the CONSYS microcontroller, not in
application-processor EMI.

### Why the kernel cannot simply be `gnss-mtk`

The mainline `drivers/gnss` core is a raw byte pipe with open/close hooks and a
kfifo for `read()`. That shape fits, but the existing `gnss-mtk` driver is a
serdev consumer for `globaltop,pa6h` with `vcc`/`vbackup` supplies. It neither
matches this transport nor knows the GFNS handshake.

## Firmware

GNSS code arrives with the common connectivity firmware, not with a
GNSS-specific download. Two images are involved, both loaded by WMT power-on:

| Image | Bytes | Content relevant to GNSS |
| --- | --- | --- |
| `ROMv3_patch_1_0_hdr.bin` | 210,904 | WMT/STP, GFNS task scheduler/buffers (`g_gfns_task_info`, `GFNS_TASK_ST_WORKING`, `GFNS_TASKID_CNT`), Wi-Fi/BT |
| `ROMv3_patch_1_1_hdr.bin` | 46,472 | BORA porting layer, GFNS request/response handlers, FLP/geofence, GNSS NVRAM, user/state machine |

`ROMv3_patch_1_1` identifies itself as `GFNS_CONN_VER3.0_2017.01.03-01` and is
built from paths such as `patch/geofence/BORA_MnlPorting_L1_tcm.c`,
`patch/geofence/gfns_mgmt.c`, `patch/gfns/gfns_if.c`,
`patch/gfns/gfns_if_conn.c`, `patch/gfns/gfns_rbuf.c`,
`patch/gfns/gfns_scp.c` and `patch/geofence/flp_offload_msg.c`.

Its strings expose the microcontroller side of the protocol and state machine,
including `GFNS_REQ_MNL_INIT`, `GFNS_REQ_MNL_INIT_API`,
`GFNS_REQ_MNL_UTC_INIT`, `GFNS_REQ_MNL_PMTK_INPUT`,
`GFNS_REQ_MNL_AGPS_PMTK_SEND`, `GFNS_REQ_HOST_START_GNSS`,
`GFNS_REQ_HOST_STOP_GNSS`, the `GFNS_REQ_NV_*` family, the `GFNS_REQ_MCU_*`
debug/memory family and `GFNS_RSP_MCU_ACK_DN_PKT_STA`. It also contains the
GNSS user bitmask logic (`mnl_chk_user`, `GFNS_GNSS_STOPPED` … `GFNS_GNSS_ERR_STATUS`)
and the NVRAM store (`g_nvram`).

Neither patch contains NMEA sentence formatters (no `$GPGGA`, `$GPRMC` and so
on). The sentence text observed on the wire must therefore come from the
ROM-resident GNSS engine that the patch extends. The patch provides the porting
layer and the host protocol, not the position solution itself.

## The GFNS wire protocol

Everything the application processor exchanges with the GNSS microcontroller is
carried in GFNS frames inside STP task 2. GFNS is also the geofence/FLP
transport; the same frames carry locations, NVRAM and debug traffic.

### Frame format

```text
A5 00 TYPE LEN_HI LEN_LO SUM  <LEN bytes of payload>  A3
```

- `SUM` is the low byte of the sum of header bytes 1 to 4. The vendor receiver
  checks exactly that, so on MCU→host frames the channel byte counts; on
  host→MCU frames that byte is zero, giving `(TYPE + LEN_HI + LEN_LO) & 0xff`.
- `LEN` is the payload length; the sender splits user data into chunks of at
  most `0x1ff` bytes.
- Total frame size is `6 + LEN + 1`.
- The receiver scans for `A5`, validates the checksum, computes the length,
  requires the trailing `A3`, then dispatches on `TYPE`.
- The second header byte is zero on host→MCU frames. On MCU→host frames its
  top three bits select one of eight output channels used by the NMEA/log
  assembler.

There is also an 11-byte keep-alive frame, type `0x76`, with a 32-bit counter
payload; the host sends it when its progress counter advances. It is used for
link liveness and timeout detection.

### Host→MCU message types (REQ)

Confidence is exact for the frame and for types observed against their string
counterpart; the two "inferred" rows follow from the protocol symmetry only.

| Type | Length | Meaning | Basis |
| --- | --- | --- | --- |
| `0x01` | variable | alternate request channel used by a client pipe | decompiled sender, unresolved |
| `0x03` | variable | NMEA/PMTK text input from a client socket | decompiled sender, unresolved |
| `0x13` | 0 | `MNL_INIT` — start the MNL/BORA layer with defaults | call site + firmware name |
| `0x14` | 49 | `MNL_INIT_CFG` — full initialization configuration | call site + firmware name |
| `0x21` | variable | `FLP_AP2CONN` — FLP request/data to the geofence engine | call site + firmware name |
| `0x40` | 0 | `HOST_START_GNSS` — add a GNSS user, start the engine | call site + firmware name |
| `0x41` | 0 | `HOST_STOP_GNSS` — remove a user, stop when the last leaves | call site + firmware name |
| `0x44` | 4 | `DEL_NV_DATA` — bitmap of NVRAM records to erase | payload is `mtk_gps_delete_nv_data()` bitmap |
| `0x70` | variable | `MNL_PMTK_INPUT` — host MNL message: `u16 id`, `u16 len`, data | decompiled sender |
| `0x71` | variable | `MNL_AGPS_PMTK_SEND` — raw assistance data | decompiled sender |
| `0x76` | 4 | keep-alive with 32-bit counter | decompiled builder |
| `0x77` | 8 | `NV_DOWN_OPEN` | log string |
| `0x78` | 6 + n | `NV_DOWN_DATA` (256-byte blocks) | log string |
| `0x79` | — | `NV_DOWN_CLOSE` (inferred, not observed) | protocol symmetry |
| `0x7a` | 8 | `NV_UP_OPEN` | log string |
| `0x7b` | 6 | `NV_UP_DATA_ACK` | decompiled sender |
| `0x7c` | — | `NV_UP_CLOSE` (inferred, not observed) | protocol symmetry |
| `0x7d` | 0 | `NV_DEL_DONE` | log string |
| `0x7e` | 28 | `MCU_ACK_UP_PKT_STA` — host receive counters/window | log string |
| `0x7f` | 20 | `NV_DOWN_MASKQRY` — which NVRAM blocks the host has | log string |
| `0x83` | 12 | `MNL_UTC_INIT` — UTC broken-down time from the host clock | decompiled builder |

`MTK_GPS_INIT_CFG` is 49 bytes. The firmware's own parameter dump names its
fields in order: `if_type`, `pps_mode`, `datum`, `dgps_mode`, `tcxo_mode`,
`pps_duty`, `pps_port`, `u1ClockType`, `hw_Clock_Drift`, `hw_Clock_Freq`,
`if_link_spd`, `fix_interval`, `Int_LNA_Config`, two reserved words,
`GNSSOPMode`, `initU`, `lastU`. The vendor's packer also carries `C0` and `C1`
before `initU`. The values come from `mnl.prop`, the chip capability table and the NVRAM calibration.

### MCU→host message types (RSP)

| Type | Meaning |
| --- | --- |
| `0x0a` | NMEA text block, channel in header byte 1 |
| `0x0b` | NMEA/debug text (second channel) |
| `0x22` | fix-ready event plus a payload passed to the NMEA-output callback |
| `0x24` | FLP data |
| other `< 0x34` | unassigned "to app" payloads (mostly debug/log) |
| `0x30` | `GFNS_RSP_AGPS_SET_PARAM` |
| `0x31` | `GFNS_RSP_AGPS_GET_PARAM` |
| `0x32` | `GFNS_RSP_AGPS_SET_DISPATCH_CB` (PMTK string plus length) |
| `0x34` | `GFNS_RSP_AGT_MSG_SEND` (assistance message from agent) |
| `0x35` | `GFNS_RSP_MCU_ACK_DN_PKT_STA` (28-byte downlink status) |
| `0x36` | `GFNS_RSP_MCU_RST_UP_PKT_STA` (uplink counters reset) |
| `0x40` | `GFNS_RSP_NV_DOWN_START` |
| `0x41` | `GFNS_RSP_NV_DOWN_DATA_REQ` |
| `0x42` | `GFNS_RSP_NV_DOWN_END` |
| `0x43` | `GFNS_RSP_NV_UP_REQ` |
| `0x44` | `GFNS_RSP_NV_UP_START` |
| `0x45` | `GFNS_RSP_NV_UP_DATA` |
| `0x46` | `GFNS_RSP_NV_UP_END` |
| `0x47` | `GFNS_RSP_NV_DEL_REQ` |
| `0x49` | `GFNS_RSP_NV_DOWN_MASKACK` |

The request and response number spaces overlap; direction and the surrounding
exchange disambiguate them (for example `0x40` is "start GNSS" from host to
MCU and "NV download start" from MCU to host).

### Flow control

Both directions carry a 28-byte status packet: total received, processed,
packet count, protocol drops, ring drops and the current window. The receiver
acknowledges with type `0x7e`, the sender with `0x35`. If the host's traffic is
not acknowledged in time it treats the link as wedged, logs a timeout and
triggers a CONSYS assert, which forces `mnld` to restart the GNSS session.

### How a fix is reported

The microcontroller sends a block of NMEA text as type `0x0a`. `libmnl`
reassembles lines in a 4 KiB staging buffer, forwards them to registered
consumers (log, NMEA group), and recognizes `GGA`, `GSA`, `RMC`, `GSV`, `VTG`
and the MediaTek `ACCURACY` sentence. When an `ACCURACY` sentence closes a
block, the host raises `MTK_GPS_MSG_FIX_READY`, `mnld` calls
`mtk_gps_get_position()` and sends the location to the HAL socket.

In other words: the GNSS engine computes the fix, the transport carries NMEA,
and the only binary framing is the GFNS envelope. This is the single most
important fact for mainline planning.

## Userspace

### `gps.mt6797.so` (HAL)

A thin socket shim for the Android GNSS HAL 1.0/1.1 interface (32- and 64-bit
variants differ only in ABI). It opens no device node. It uses the local
datagram sockets `mtk_hal2mnl` and `mtk_mnl2hal`, sends commands such as
`gps_init`, `gps_start`, `gps_stop`,
`gps_cleanup`, `inject_time`, `inject_location`, `delete_aiding_data`,
`set_position_mode`, `data_conn_*`, `set_server`, `set_ref_location`, `set_id`,
`ni_message`, `ni_respond`, `update_network_state`,
`update_network_availability`, `set_gps_measurement` and
`set_gps_navigation`, and receives `location`, `status`, `sv`, `nmea`,
`capabilities`, `measurements`, `navigation`, wakelock, UTC, data-connection,
NI, set-id and reference-location requests back on `mtk_mnl2hal`.

### `mnld` and `libmnl.so`

`mnld` is the daemon. It owns a small state machine (`IDLE`, `STARTING`,
`STARTED`, `STOPPING`), the user bitmask behind start/stop, the HAL/AGPS/FLP/
MPE/AT sockets, the sysfs writes, the GNSS NVRAM calibration read and the EPO
download. The GNSS protocol, framing, ACK handling, NMEA parsing and assistance
agents live in `libmnl.so`.

`libmnl` is also the whole non-offload implementation (serial MT3332 boot,
navigation engine, NMEA generation). Those paths are dormant when offload is
selected: `mnld` calls `mtk_gps_ofl_set_option(1)` after the FLP client selects
it, and the same binary is otherwise unchanged, which is why it still contains
serial boot code and `$GPGGA` formatters.

Startup sequence inside `mnld`:

1. Read `/data/misc/gps/gps.conf` and `mnl.prop` (or `/sbin/mnl.prop`).
2. Detect the chip from `persist.mtk.wcn.combo.chipid`; `0x6797` is one of the
   two chips that support the offload path, and its capability mask is
   GPS + GLONASS + BeiDou.
   The offload path is only enabled when a fused-location-provider client has
   declared `flp_mnl_mode = 1` on `/data/gps_mnl/flp2mnld`; that flag is the
   only observed writer that selects `mtk_gps_ofl_set_option(1)` on this
   board. Stock Android is expected to run such a client, but it was not in the
   retained extraction, so that is unproven; whether a reduced Gemian session
   starts one is also **not established**. Without it `mnld` falls back to the
   legacy serial path, which has no hardware here. This is the first thing to
   check in any stock-Gemian GNSS observation.
3. Read the 16-byte TCXO/co-clock calibration from
   `/data/nvram/md/NVRAM/CALIBRAT/ML4A_000` (`co`, `c1`, `initU`, `lastU`).
   Defaults are 26 MHz and 2000 ppb when absent.
4. Open `/dev/stpgps` and query the co-clock flag with ioctl 11, then set the
   `gps.clock.type` property.
5. Write the `pwrctl`/`state`/`suspend`/`pwrsave` sysfs attributes.
6. Assemble the 49-byte init configuration and call `mtk_gps_mnl_run()`.

The offload engine then runs three threads: an output thread that sends the
keep-alive, a main thread that reads `/dev/stpgps` into a 4 KiB ring buffer and
parses GFNS frames, and a debug thread that consumes the log pipe and parses
NMEA into the position state.

### Configuration and state files

| Path | Role |
| --- | --- |
| `/data/misc/gps/gps.conf`, `mnl.prop`, `/sbin/mnl.prop` | timeouts, EPO/BEE/SUPL enables, `OFFLOAD_enabled`, debug flags |
| `/data/misc/gps/mtkgps.dat` | host-side GNSS NVRAM store (almanac, ephemeris, calibration) |
| `/data/misc/gps/cache.dat`, `AAT.cfg` | cache and factory test data |
| `/data/misc/gps/EPO.DAT`, `EPOHAL.DAT` | extended prediction orbit data |
| `/data/misc/gps/QEPO.DAT`, `QEPOHAL.DAT` | quarter EPO data |
| `/nvcfg/almanac.dat` | almanac input used to estimate fix age |
| `/data/nvram/md/NVRAM/CALIBRAT/ML4A_000` | TCXO/co-clock calibration |
| `/sys/class/gpsdrv/gps/{pwrctl,status,state,suspend,pwrsave}` | state recording only on this kernel |

### Assistance services

| Service | Function |
| --- | --- |
| `mtk_agpsd` | OMA SUPL 2.0 client (ULP, TLS/OpenSSL, libcurl, RIL); profiles in `/data/agps_supl/agps_profiles_conf2.xml`, `/etc/` or `/vendor/etc/`, PLMN-to-SLP table, OMA CP provisioning; talks to `mnld` on `/data/agps_supl/{agps_to_mnl,mnl_to_agps}` and exposes `/dev/socket/agpsd2`/`agpsd3` for test/settings tools |
| `mnld` EPO | Downloads `EPO_GPS_3_1..10.DAT`/`MD5` and `EPO_GR_3_1..10.DAT`/`MD5` from `https://mgepodownload.mediatek.com/` or `https://mepodownload.mediatek.com/`, RSA-encrypts the request with an embedded public key, resumes pieces, and updates `EPO.DAT` |
| `mnld` QEPO | Same scheme for `QG_R_1..5.DAT`, plus `QEPOHAL.DAT` |
| `mnld` BEE | MediaTek broadcast ephemeris exchange over the NMEA/PMTK agent path |
| `wifi2agps` | Turns Wi-Fi scan/RTT results into AP location-aiding records for the AGPS agent; disabled in the Gemian init rules |

### Navigation-adjacent services

| Component | Role |
| --- | --- |
| `MPED`, `libmpe.driver.so`, `libmpe.sensorlistener.so`, `libDR.so` | MediaTek Positioning Engine: sensor fusion and pedestrian dead reckoning (`mpe_get_pdr_heading`, `mpe_get_pdr_pose`, `mpe_update_pdr`) using accelerometer/gyroscope/magnetometer through Android `SensorManager`; talks to `mnld` on `/data/mpe_mnl/{mnl2mpe,mpe2mnl}` and injects ADR into the GNSS engine |
| `magd`, `geomagneticd`, `msensord`, `sensors.mt6797.so` | Magnetometer calibration and virtual orientation sensors; heading source for mapping applications and for MPE |
| FLP (inside `mnld`/`libmnl` and the firmware) | Fused location provider and geofence offload; `/data/gps_mnl/{mnld2flp,flp2mnld}` |
| `libviagpsrpc.so` | CDMA GPS RPC client (`gps_rpc_api_clnt`) retained for a non-MTK modem path; not part of the MT6797 stack |

## End-to-end sequences

**Cold start.** The Android location service loads the HAL, which sends
`gps_init`/`gps_start` to `mnld`. `mnld` opens `/dev/stpgps`, which powers
CONSYS through WMT. It sends `MNL_INIT`, the 49-byte configuration, the NVRAM
delete bitmap, the UTC time and an NVRAM download open, then offers its stored
NVRAM in blocks as the firmware requests them, and finally queries which blocks
the firmware now holds. When configuration is accepted, the host adds a GNSS
user (`0x40`).

**Fix.** The engine acquires satellites and emits an NMEA block. The host raises
`FIX_READY`, reads the position and forwards it to the HAL. Ephemeris and
almanac are mirrored back into NVRAM at stop or on demand.

**Assistance.** When the engine asks for assistance, `libmnl` raises an AGPS
dispatcher event; `mnld` forwards it to `mtk_agpsd`, which runs SUPL over the
network and returns data that `mnld` sends back as type `0x71` (or as PMTK
messages through `0x70`). EPO works the same way without a network session.

**Stop.** The HAL sends `gps_stop`; when the last user leaves, the host sends
`HOST_STOP_GNSS` and closes `/dev/stpgps`, which releases the wake lock and
calls WMT function-off. CONSYS stays powered if any other radio is on.

**Failure.** A missed acknowledgement or a firmware fault makes the host log a
timeout and trigger a CONSYS assert; `mnld` restarts the GNSS session. A whole
chip reset also invalidates the open STP state, so the userspace daemon must
reopen the device.

## Mainline translation

The transport and protocol are known, and common CONSYS initialization with ROM
patch loading and calibration now runs on the station for Wi-Fi. What remained
below the protocol was a receive path that stays on: the start chain's STP
exchanges are one-shot. The
[GNSS link record](../../experiments/2026-11-01-gemini-gnss-link/README.md) adds
that link and a silent `gnss` device; one boot passed with Wi-Fi running. The
receiver has not been started.

A first standards-shaped GNSS implementation needs, in order:

1. The shared CONSYS/WMT owner (done for Wi-Fi) and a persistent STP link
   (passed one boot).
2. GPS function-on (`01 06 02 00 02 01`), the GPIO 69 LNA state, and the VCN28
   and AFE prerequisites provided by that owner.
3. A GFNS endpoint that sends `MNL_INIT`, `MNL_INIT_CFG`, `MNL_UTC_INIT`,
   the keep-alive and `HOST_START_GNSS`; answers the downlink ACK; keeps the
   uplink ACK window; and exposes type `0x0a` payloads as a stream.
4. A standard `gnss` device (`GNSS_TYPE_NMEA` semantics) over that stream, so
   `gpsd` can consume it. Parsing in the kernel is not needed.
5. NVRAM up/down mapping to a host file, and the TCXO calibration values, to
   get repeatable accuracy. Without them the engine runs with defaults.
6. Optional, later: EPO/SUPL assistance, FLP/geofence, and coexistence
   de-sense with Bluetooth/Wi-Fi.

What is *not* required for a first fix: `mnld`, `libmnl`, the Android HAL,
`mtk_agpsd`, `MPED`, EPO, or any NMEA-to-serial daemon. That is a material
change from the earlier plan, which assumed positions were only reachable
through MediaTek's proprietary MNL library.

Risks and unknowns are recorded in the experiment record: exact init
configuration values, whether the firmware tolerates a minimal NVRAM exchange,
the keep-alive cadence, and the de-sense protocol that Bluetooth/Wi-Fi
coexistence may require.

## Evidence and limits

Facts here come from static analysis of the retained 2019 userspace payload and
the two ROM patch images, decompiled with Ghidra 12.1.2 and cross-checked with
radare2 5.5.0, plus the pinned vendor kernel at
`8cfe6596a503612e3332d9c26e292a19525a7f07`. No device was accessed for this
record and no fix was observed.

Not established: whether an FLP client runs in the Gemian container, which is
what selects the offload path in the vendor daemon; whether a physical LNA is
populated; the exact meaning of every GFNS type in the `0x25`–`0x33` range; the
exact counter behind the keep-alive; and the properties of a mainline GNSS
session. See the
[experiment](../../experiments/2026-11-01-gemini-gnss-re/README.md) for the
per-fact confidence and the proposed measurements that would close them. The
[link record](../../experiments/2026-11-01-gemini-gnss-link/README.md) has the
`0x14`, `0x83`, `0x7e` and keep-alive details read for the first start.
