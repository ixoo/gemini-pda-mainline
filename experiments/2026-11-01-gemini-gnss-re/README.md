# Experiment: Gemini GNSS userspace, firmware and protocol reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-re` |
| Status | `completed` (offline binary and firmware review; no build, boot or device access) |
| Subsystem | MT6797 CONSYS GNSS: vendor `mnld`/`libmnl`, Android GPS HAL, SUPL/EPO/FLP/MPE userspace, GFNS protocol, ROMv3 patches |
| Device variant | Planet Computers Gemini PDA, MT6797X, CONSYS `0x0279`, Gemian `3.18.41+` |
| Date(s) | 2026-11-01 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | M6 connectivity documentation; no implementation |

> **Follow-up, 2026-11-01.** The first device start contradicts this record's
> planning conclusions. See the
> [link record](../2026-11-01-gemini-gnss-link/README.md#t3-result-the-start-sequence-asserts-the-firmware-2026-11-01):
> offload is inferred to need `MNL.bin`, so F7's ROM inference, F2's serial fallback and
> "What this changes" are in doubt. The frame format itself did work: the firmware
> acknowledged the frames at link level and reached the handler.

## Question

The [2026-10-04 GNSS source review](../2026-10-04-gemini-gps-re/README.md)
mapped the kernel boundary and the WMT/STP path but could not see the
proprietary daemon, the firmware internals or the payload format. It concluded
that positions were only reachable through MediaTek's proprietary MNL library
and ranked a Gemian-side trace as the decisive next measurement. That trace was
never taken, and the daemon binaries were subsequently found in the retained
extraction.

This study asks, from the binaries and firmware alone:

1. Which process owns the receiver, and which device does it open?
2. What exactly is on `/dev/stpgps` — binary navigation data or text?
3. What initialization, keep-alive and flow control does the firmware expect?
4. What do SUPL, EPO, FLP and the sensor engine add, and are they required?
5. What would a standards-shaped mainline GNSS interface have to implement?

No code, patch, profile, candidate or device state is changed.

## Provenance

All binary work was static and read-only in the project RE VM against the
private payload from the 2026-07-12 userspace extraction
(`artifacts/device-userspace/gemian-2019/`). Nothing was executed.

| Binary (`system/vendor/`) | Bytes | SHA-256 | Role |
| --- | --- | --- | --- |
| `bin/mnld` | 171,228 | `ecae74f8a03094dc95a91878b13e924215b9e21c9173aa3153735c55641f2d71` | GNSS daemon: state machine, sockets, NVRAM, EPO, AGPS, FLP, MPE |
| `lib/libmnl.so` | 2,411,928 | `a2e3fe692215352f4d27646e72aa1c439ba60d60883c26d8bcc3227fdb5d330f` | GFNS transport, framing, ACK, NMEA parse/generate, assist agents |
| `lib/hw/gps.mt6797.so` | 46,936 | `e6aeed49842a8c4b32a46b4cd7716e9b9de0d321151c87c9a523a328012039cf` | Android GNSS HAL 1.0/1.1, socket shim |
| `lib64/hw/gps.mt6797.so` | 51,832 | `a461bbe5ab075565435299a067a7c82eee75fb559569b6f6dd8e245f761fb5b3` | Same HAL, AArch64 |
| `bin/mtk_agpsd` | 1,494,624 | `1ab44c91859ed105f3a4b4d8e4e5e51b07197972b55c6e410e2d5c9430c9477f` | OMA SUPL 2.0 client, RIL, TLS |
| `bin/wifi2agps` | 18,624 | `7029ad4d8b88b502b8b70b3d2fcb8e6869ee6037fab4b7c35940a246cb2e87f3` | Wi-Fi scan/RTT location aiding |
| `bin/MPED` | 30,388 | `44f04443612dd7e86f2a4e7405ca6fd7313eed7b6ba31183a5f0f2cbed5e9faf` | MTK Positioning Engine daemon |
| `lib/libDR.so` | 22,220 | `cad69beb4f1f53d4f8bb463fdc7964d0742aac98e890d355c49b9f7a0ff1ef01` | Dead-reckoning / PDR algorithms |
| `lib/libmpe.driver.so` | 42,788 | `a4e93f64419cf1547685c133a8da7e472d2341403a5fcb9b753dbc0c6b14ad1d` | MPE driver glue and sensor listener bridge |
| `lib/libmpe.sensorlistener.so` | 26,272 | `190e1fbeeefb0ed7744f99adc081cb8e327ced229a2ff99b6086f8eebcde65a9` | Android `SensorManager` listener |
| `lib/libviagpsrpc.so` | 143,648 | `615b0125ee14224bcaa3b1a214d4d16716a707dd9e5fc2b0fdf13c02803535b3` | VIA CDMA GPS RPC (not this platform) |

Firmware, from the retained 2019 vendor set:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `ROMv3_patch_1_0_hdr.bin` | 210,904 | `450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630` |
| `ROMv3_patch_1_1_hdr.bin` | 46,472 | `5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e` |
| `WMT_SOC.cfg` | 80 | `f4a59b622a4e0c1470e475ce33f3edae43b27f1fbdeba54dc7cf07503d132880` |

Vendor kernel source, public, commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`:

| File | SHA-256 |
| --- | --- |
| `drivers/misc/mediatek/connectivity/gps/gps.c` | `e8cff970f66f86c41318db448ac3f3c9e82d02fc9cbe637926e66278813e49b4` |
| `drivers/misc/mediatek/connectivity/gps/stp_chrdev_gps.c` | `0cd498a248dce5dd0a0809ab884229c3d034a4e8f0299caea78ba34abcbb8fb7` |
| `drivers/misc/mediatek/connectivity/gps/gps_emi.c` | `1809b36948cdb333a3a2fa291a9addb589f5f65382ceaa96ae6b20c6ff5aa530` |
| `drivers/misc/mediatek/connectivity/common/common_main/include/stp_exp.h` | `9c1daca8fa5e30468865d42fb778bf070ac09e0adebf6735852631d5dc89ec42` |
| `drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c` | `79d03346c95e2d233f2a384fa4490d3b89acdfd1c1d6b9c2026709358dbcbf65` |
| `drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c` | `c57079b29491338fa635dd36f550f3be53b4a2cee343b1dce1c9e4d365b4589d` |
| `arch/arm64/configs/aeon6797_6m_n_defconfig` | `83f33ed07c17abe8dceaee64afd26de0cc970c0bae93681b68906636e21e883f` |
| `arch/arm64/boot/dts/mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |

No binary, firmware or configuration content is copied into this repository.
Command bytes, frame layouts, opcodes and path names are cited as facts.

## Method

- `readelf -sW`/`-SW`/`-lW`, `strings`, and section extraction to separate
  `.rodata`/`.data` from code; function-to-string association by decompilation
  rather than by hand-guessing.
- Ghidra 12.1.2 headless (`-processor ARM:LE:32:v7`) decompiled all 2,029
  functions of `libmnl.so` and all 321 functions of `mnld`, then the call sites
  of the packet builder/sender helpers were enumerated and correlated with the
  firmware's own log strings.
- radare2 5.5.0 cross-checked symbol and string virtual addresses.
- Firmware was searched with `strings` for protocol names, and patch images
  were compared structurally (header, entropy, string sets). Firmware code was
  not disassembled; the protocol numbers below come from the host side, which
  is the side that must be reimplemented.
- Every cell marked "inferred" below is labelled; everything else was read
  from code, a string, a call site or a source file.

## Findings

### Architecture

- **F1. GNSS is a function of CONSYS, not a separate device.** There is no GNSS
  UART, chip or register node. All resources belong to `consys@18070000` and
  BTIF. The kernel consumes only STP task 2 and one board GPIO.
- **F2. `mnld` is the owner process, and it is offload-capable.** It detects the
  chip from `persist.mtk.wcn.combo.chipid` and opens `/dev/stpgps`
  unconditionally. Only `0x6797`/`0x6632` are listed as offload-capable, and
  `mtk_gps_ofl_set_option(1)` is called **only** when the byte set by
  `FUN_0001d770` is non-zero. The two observed writers of that byte are both in
  the FLP socket handler (`flp2mnl_hdlr`) and follow a fused-location-provider
  `flp_mnl_mode` value; its initial `.data` byte is zero. Stock Android is
  expected to run such a client, but it was not in the retained extraction, so
  that is unproven; whether a reduced Gemian session does is not established. Without it `mnld` selects the legacy
  serial path (`/dev/ttygserial`, MT3332 handshake and firmware boot), which has
  no hardware on this board. This is the cheapest thing to verify in any stock
  Gemian GNSS observation, and it would explain the absence of any recorded fix.
- **F3. The Android HAL is a socket shim.** `gps.mt6797.so` imports
  `socket`/`sendto`/`recvfrom`, uses the local datagram sockets
  `mtk_hal2mnl`/`mtk_mnl2hal`, and opens no device node. Its exported command strings are exactly the
  Android GNSS HAL calls; the 32- and 64-bit builds are equivalent.
- **F4. The position engine runs on the CONSYS microcontroller.** The firmware
  patch contains the BORA porting layer (`BORA_MnlPorting_L1_tcm.c`,
  `mtk_gps_init_api_bora`, `BORA_MNL_EVENT_INIT/RUN/DEINIT`), the GNSS status
  machine (`GFNS_GNSS_STOPPED/STARTING/WORKING/STOPPING/ERR_STATUS`) and a
  DMA output path from the GNSS core (`gps_dma_output`, `md32_recv`). The host
  library only transports, acknowledges, parses NMEA, and manages assistance.

### Firmware

- **F5. GNSS code ships inside the common ROM patch, with no GNSS-specific
  file.** `ROMv3_patch_1_0_hdr.bin` contains the GFNS task scheduler
  (`g_gfns_task_info`, `GFNS_TASK_ST_WORKING`, `GFNS_TASKID_CNT`, rbuf), and
  `ROMv3_patch_1_1_hdr.bin` contains the GNSS/geofence application. Both are
  applied during WMT power-on before any function-on.
- **F6. The second patch is the GNSS application layer.** It announces
  `GFNS_CONN_VER3.0_2017.01.03-01` and contains the request/response handler
  names (`GFNS_REQ_MNL_INIT`, `_INIT_API`, `_MNL_UTC_INIT`,
  `_MNL_PMTK_INPUT`, `_MNL_AGPS_PMTK_SEND`, `_HOST_START_GNSS`,
  `_HOST_STOP_GNSS`, `_NV_*`, `_MCU_*`), the user/state machine and the NVRAM
  store (`g_nvram`).
- **F7. The patches contain no NMEA sentence formatters.** Neither image
  contains `$GPGGA`, `$GPRMC`, `$GPGSV` or equivalents; the only NMEA strings
  are two `$PMTK` status replies. The sentences observed on the wire must be
  produced by the ROM-resident GNSS engine that the patch extends.

### Transport and protocol

- **F8. `/dev/stpgps` is an opaque byte pipe to STP task 2.** `GPS_write` calls
  `mtk_wcn_stp_send_data(..., GPS_TASK_INDX)` and `GPS_read` calls
  `mtk_wcn_stp_receive_data(..., GPS_TASK_INDX)`; the kernel adds STP framing
  only. `GPS_TASK_INDX` is 2, so the STP task nibble is `0x2`.
- **F9. Open/close is the power switch.** Open calls
  `mtk_wcn_wmt_func_on(WMTDRV_TYPE_GPS)`, registers a reset callback, requires
  STP ready, registers the task-2 event callback and takes the `gpswakelock`
  wakeup source. Close calls `mtk_wcn_wmt_func_off(WMTDRV_TYPE_GPS)`.
- **F10. The GFNS frame is `A5 00 TYPE LEN_HI LEN_LO SUM payload A3`.** The TX
  builder (`libmnl` `FUN_0001ab4c` at `0x1ab4c`) writes the six header bytes and
  `SUM = (0x00 + TYPE + LEN_HI + LEN_LO) & 0xff`; the sender
  (`FUN_0001ad80` at `0x1ad80`) writes `0xA3` as the final byte. The RX scanner
  (`FUN_0001a89e`/`FUN_0001a944`) validates the checksum, derives
  `LEN = CONCAT11(HI,LO) + 1`, and requires the trailing `A3`
  (`FUN_0001a928`/`FUN_0001a9ec`). User data is split into chunks of at most
  `0x1ff` bytes (`FUN_0001ac8c`).
- **F11. A keep-alive frame uses type `0x76`.** `FUN_0001b018` builds an
  11-byte `A5 00 76 00 04 7A <counter32> A3`; `FUN_0001b0bc` sends it when the
  progress counter advances past 1024.
- **F12. Frame dispatch uses the numeric type.** `FUN_0001b26c` dispatches on
  the type byte and logs the protocol names, giving exact numbers for the
  MCU→host set: `0x0a` NMEA block, `0x0b` NMEA/debug text, `0x22` NMEA plus
  fix-ready, `0x24` FLP, `0x30`/`0x31`/`0x32` AGPS parameter/dispatch,
  `0x34` agent message, `0x35` downlink ACK (28 bytes), `0x36` uplink reset,
  `0x40`–`0x47` and `0x49` NVRAM.
- **F13. The host→MCU set is identified by call site.** `0x13` MNL_INIT (zero
  length), `0x14` MNL_INIT_CFG (49 bytes), `0x21` FLP data, `0x40` start GNSS,
  `0x41` stop GNSS, `0x44` NVRAM-delete bitmap (payload from
  `mtk_gps_delete_nv_data()`), `0x70` MNL message (`u16 id`, `u16 len`, data),
  `0x71` raw AGPS data, `0x76` keep-alive, `0x77`/`0x78`/`0x7a`/`0x7b`/`0x7d`/
  `0x7e`/`0x7f` NVRAM and ACK, `0x83` UTC time (12 bytes built from the host
  clock). `0x79` (NV down close) and `0x7c` (NV up close) are inferred from the
  firmware names and the 28-byte ACK pairing; they were not observed being sent.
- **F14. Flow control is a 28-byte counter packet in both directions.** The
  host logs `recv`, `proc`, `pkt`, `pdrop`, `rdrop`, `window` and replies with
  `GFNS_REQ_MCU_ACK_UP_PKT_STA` (`0x7e`). Missing ACKs produce a traffic-timeout
  log and a CONSYS assert. The precise field layout beyond the logged counters
  is not named.
- **F15. The GNSS payload is NMEA text, not a binary fix.** `FUN_00019bf8`
  reassembles lines, requires `$`, and matches `GGA`, `GSA`, `RMC`, `GSV`,
  `VTG` and `ACC` at offset 3. A closing `ACCURACY` sentence flushes the block
  and raises `MTK_GPS_MSG_FIX_READY`, after which `mnld` calls
  `mtk_gps_get_position()` and sends the HAL location.
- **F16. The second header byte is a channel field on MCU→host frames.** The
  dispatcher uses `byte1 >> 5` as an index into eight 512-byte NMEA assemblers;
  host→MCU frames set it to zero.
- **F17. NVRAM is a block protocol with session identifiers.** The host opens a
  download (`0x77`) and sends 256-byte blocks (`0x78`) as the MCU requests them
  (`0x41`); the MCU closes the session (`0x42`). The host then queries which
  blocks the MCU holds (`0x7f`, acked by `0x49`). Uploads run the other way
  (`0x43`/`0x44`/`0x45`/`0x46`, acked by `0x7b`). Deleting data is requested by
  `0x47` and acknowledged with `0x7d` after the host removes
  `/data/misc/gps/mtkgps.dat`.

### Userspace behaviour

- **F18. `mnld` writes sysfs state that this kernel only logs.** It writes
  `pwrctl`, `state`, `suspend` and `pwrsave` under
  `/sys/class/gpsdrv/gps/`; `gps.c` has null power hooks, so no hardware
  action results. `/dev/gps` itself is never opened by the observed stack.
- **F19. The TCXO calibration is a 16-byte NVRAM record.** `mnld` reads
  `/data/nvram/md/NVRAM/CALIBRAT/ML4A_000` and prints `co`, `c1`, `initU`,
  `lastU`; without it the defaults are 26 MHz and 2000 ppb. It then queries the
  co-clock flag with ioctl 11 and sets the `gps.clock.type` property.
- **F20. The GNSS trigger is an `ACCURACY` sentence, not a binary event.** This
  is why `mnld` can report a location without any GNSS-specific kernel ioctl.
- **F21. EPO is a direct HTTP download, not SUPL.** `mnld` builds a URL for
  `EPO_GPS_3_n.DAT`/`EPO_GR_3_n.DAT` (and `QG_R_n.DAT` for QEPO), encodes the
  request with an embedded RSA public key, downloads with libcurl, fetches the
  companion `.MD5` file and updates `EPO.DAT`/`QEPO.DAT`.
- **F22. SUPL is a separate daemon.** `mtk_agpsd` implements OMA SUPL 2.0 ULP,
  reads profiles from `agps_profiles_conf2.xml` (data, `/etc` or `/vendor/etc`),
  maps PLMN to SLP, uses the RIL for cell identity and network state, and
  exchanges AGPS messages with `mnld` over `/data/agps_supl/`.
- **F23. Cell/NLP/Wi-Fi aiding all enter through the HAL or the AGPS socket.**
  `hal_gps_inject_location` (network location), `set_ref_location` (cell),
  `update_network_state`, and `wifi2agps` (Wi-Fi RTT/AP records) all converge
  on `libmnl`'s AGPS agent and leave as `0x71`/`0x70` frames.
- **F24. Sensor fusion is a separate MTK engine.** `MPED` links `libDR.so`,
  `libmpe.driver.so` and `libmpe.sensorlistener.so`, reads
  accelerometer/gyroscope/magnetometer through Android `SensorManager`, and
  injects dead-reckoned deltas into `mnld` over `/data/mpe_mnl/`. `libDR.so`
  exports `mpe_get_pdr_heading`, `mpe_get_pdr_pose` and `mpe_update_pdr`.
- **F25. FLP/geofence is offloaded to the same firmware.** FLP messages travel
  as type `0x21`/`0x24`, with host sockets `/data/gps_mnl/{mnld2flp,flp2mnld}`.
- **F26. `libviagpsrpc.so` is not part of this path.** It is a CDMA GPS RPC
  client (`gps_rpc_api_clnt`) retained for a non-MTK modem path.

### Kernel and configuration

- **F27. The vendor defconfig enables both GNSS drivers by select.**
  `CONFIG_MTK_GPS_SUPPORT=y` selects `CONFIG_MTK_GPS`, so `gps.c` (the mailbox
  and sysfs) is built; `CONFIG_MTK_COMBO_GPS=y` builds `stp_chrdev_gps.c`.
  `CONFIG_MTK_GPS_EMI` is not set, which is why `/dev/gps_emi` and `MNL.bin`
  are absent. The "MNL in EMI" feature is unrelated to the used
  "MNL on the CONSYS MCU" offload.
- **F28. The initialisation configuration is a 49-byte record.** The firmware
  dump names its fields in order: `if_type`, `pps_mode`, `datum`, `dgps_mode`,
  `tcxo_mode`, `pps_duty`, `pps_port`, `u1ClockType`, `hw_Clock_Drift`,
  `hw_Clock_Freq`, `if_link_spd`, `fix_interval`, `Int_LNA_Config`, two
  reserved words, `GNSSOPMode`, `initU`, `lastU`. Values are assembled from
  `mnl.prop`, the chip capability table and the NVRAM calibration. The exact
  per-field values used on a Gemini were not recovered.
- **F29. Mainline is missing three things, not one.** Common CONSYS
  initialization (unchanged Wi-Fi blocker), a GFNS endpoint (new, now
  specified), and NVRAM/clock inputs (new, partially specified). The `gnss`
  core itself is sufficient once those exist.

## Hypotheses and open questions

Each states what would confirm it and the cheapest measurement. None is
admitted by this record. Device work requires a reviewed experiment with its
own candidate and stop conditions.

0. **H0. A stock Gemian session never enables offload, so GNSS cannot start at
   all.** Prediction from F2: unless an FLP client sends `flp_mnl_mode = 1`,
   `mnld` chooses the serial path and fails on a device with no GNSS UART. This
   would explain why no fix was ever recorded on this device under either
   kernel. Test: a bounded read-only Gemian check for the FLP process/socket
   and for `set option, cfg = %d` in the GNSS log during one HAL start. It costs
   one session and decides whether the rest of this record describes a path
   that Gemian has never exercised. Confidence: medium.
1. **H1. A minimal GFNS client is enough for a first NMEA byte.** Prediction:
   after common CONSYS init, GPS function-on, GPIO 69 high, `MNL_INIT`,
   `MNL_INIT_CFG`, `MNL_UTC_INIT`, `HOST_START_GNSS` and keep-alives, type
   `0x0a` frames carrying `$G...` text appear. Refuted if the engine stays
   silent until an NVRAM download completes. Test: a mainline boot that logs
   frame type and the first 64 payload bytes only. Confidence: medium-high;
   the protocol shape is exact, the firmware's tolerance of empty NVRAM is not.
2. **H2. The NVRAM exchange is required before the first fix, not before the
   first frame.** Prediction: frames arrive immediately, positions stay coarse
   until `mtkgps.dat` is supplied. Test: same boot, two sessions with and
   without a pre-seeded NVRAM file. Confidence: medium.
3. **H3. The 49-byte configuration can be reconstructed from defaults.**
   Prediction: the firmware accepts `MNL_INIT_CFG` with `fix_interval = 1000`,
   TCXO type/drift from `ML4A_000`, and `GNSSOPMode` from the 0x6797 capability
   mask, and runs. Test: offline reconstruction plus one mainline boot that
   logs the firmware's own "use AP cfg" versus "use default cfg" choice.
   Confidence: medium.
4. **H4. The keep-alive is required for continuous output.** Prediction:
   omitting `0x76` makes the MCU stop or the host time out. Test: A/B in the
   same boot. Confidence: medium.
5. **H5. Bluetooth/Wi-Fi coexistence needs the de-sense exchange.** The vendor
   sends a de-sense command to the WMT launcher whenever GNSS and BT/Wi-Fi
   overlap. Prediction: GNSS throughput or fix quality degrades when another
   radio starts, unless the de-sense packet is supplied. Test: two-radio run
   after H1 succeeds. Confidence: medium.
6. **H6. A physical LNA exists and GPIO 69 matters for quality, not for
   frames.** Test: compare carrier-to-noise values with GPIO 69 low and high
   once a decoder exists. Confidence: medium.
7. **H7. The 28-byte ACK fields are mirrored counters plus a window.** The
   logged names and the symmetric `0x35`/`0x7e` pair support this; the exact
   offsets are unproven. Test: one instrumented session logging both packets
   while varying traffic. Confidence: high on semantics, low on layout.

## What this changes

- The earlier record's F16 ("the payload is MediaTek's binary protocol, not
  NMEA") and its H5 risk are **superseded**: the payload is NMEA text inside
  GFNS frames, and the binary part is only the envelope and the handshake.
- Mainline GNSS no longer ends at "raw frames or nothing". A small GFNS
  endpoint plus the existing `gnss` core and `gpsd` is a plausible path, without
  `mnld`, `libmnl` or the Android HAL.
- The cost moves from "reverse-engineer a position engine" to "implement a
  ~20-message handshake and keep the firmware happy". That is comparable to the
  Bluetooth work already in progress and shares its WMT/STP owner.
- The assistance stack (SUPL, EPO, FLP, MPE) is now bounded and optional; it
  should not block a first fix.
- A stock Gemian session may never enable the offload path at all (F2/H0).
  That one read-only check should precede any hardware GNSS work, because it
  decides whether the vendor path is even active in Gemian and would explain
  the absence of any recorded fix.
- The roadmap's "GNSS after Bluetooth" ordering still holds, because the
  common initialization is still the prerequisite, but the estimate after that
  point improves.

## Limitations

This review is static. No GNSS session was captured, so the following remain
unproven: whether any FLP client runs in the Gemian container (the offload
switch); that the engine runs with an empty or default NVRAM; the actual
`MNL_INIT_CFG` bytes a Gemini sends; the keep-alive period in milliseconds; the
exact 28-byte ACK layout; whether any additional undocumented frame is needed
before the first sentence; and whether the de-sense exchange is required for a
usable fix with another radio active. Firmware code was not disassembled; the
BORA/ROM split is inferred from strings and from the host-side behaviour. The
NMEA formatters are assumed to be ROM-resident because they are absent from
both patches.
