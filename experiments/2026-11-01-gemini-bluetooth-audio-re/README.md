# Experiment: Gemini Bluetooth userspace, firmware and audio reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-bluetooth-audio-re` |
| Status | `completed` (offline source and binary review; no build, boot or device access) |
| Subsystem | Android vendor Bluetooth libraries, Gemian BlueZ transport, CONSYS CVSD audio, firmware evidence |
| Device variant | Planet Computers Gemini PDA, MT6797X, CONSYS `0x0279` |
| Date(s) | 2026-11-01 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Connectivity/Bluetooth documentation; no implementation |

## Question

The 2026-10-04 review covered the kernel transport (WMT, STP task 0, BTIF,
Gemian `hci_stp`). It could not see what stock Android does in userspace, where
the voice samples go, or how Gemian differs at runtime. This study asks:

1. What exactly does the vendor Android Bluetooth stack do with `/dev/stpbt`,
   and which initialization does it perform?
2. Where does Bluetooth audio travel on this platform, and which side codes it?
3. What do the retained firmware and the Gemian kernel contribute to each?
4. Which parts are demonstrated, and which remain hypotheses?

No code, patch, candidate or device state is changed.

## Provenance and environment

All binary work was static and read-only in the RE VM against the private
payload from the 2026-07-12 userspace extraction. Nothing was executed.

| Binary (private extraction, `system/vendor/`) | Bytes | SHA-256 | Role |
| --- | --- | --- | --- |
| `lib64/libbluetooth_mtk.so` | 26,752 | `bc8b255bb2a396e500b6db46e32d336383fb250e0823879e9e3cf4701884a7cc` | Android BT wrapper: threads, init script, PSM/assert ioctls |
| `lib64/libbluetooth_mtk_pure.so` | 27,048 | `9e315f8b6cc5640576d7af0fe8f1c3f0998d63bc48c0d9fa609ab9840f66df62` | Transport over `/dev/stpbt`, HCI helpers, audio config |
| `lib64/libbluetoothem_mtk.so` | 10,296 | `2b67dc1c3a7b70010427fed85e7aca4015666fee5240c105195915b6b0b29b04` | Dynamic wrapper around `_pure` |
| `lib64/libbluetooth_relayer.so` | 14,392 | `f79a4864a4e1d454465e045742a15b2cb3ff152045f2d414197660ce24ce3b83` | UART/USB HCI relayer for factory use |
| `lib64/libbluetooth_hw_test.so` | 22,584 | `75866c6eb2ba5b0f1715d2d1704632e1b3c6dbdd32ff42608bce463d46f7930f` | Factory RF test commands |
| `lib64/hw/audio.primary.mt6797.so` | 1,332,968 | `d086eab26f9dbfa824e8136336ac785aaf2ba6b8848b6633516d9d62945aec0e` | Audio HAL: BT interface selection, CVSD/mSBC control |
| `bin/autobt` | 23,688 | `fa3af58e94fcfcf3916296561a69fc7d3d3a45e51c7c308aba5d97bc860042ad` | Vendor Bluetooth bring-up helper |

Source inputs, all public and read at pinned revisions:

| Tree | Revision |
| --- | --- |
| Gemian `gemini-linux-kernel-3.18` | `59e00a9144d782e148332009a835b99c43382467` |
| Linux `7.1.3` | pinned in `kernel/manifest.json` |

| File | SHA-256 |
| --- | --- |
| `drivers/misc/mediatek/connectivity/drv_bt/linux/hci_stp.c` | `659a38e7d7f21bc5777d9023650820f8f993608c8546b965bf8455424c50f5cd` |
| `drivers/misc/mediatek/connectivity/drv_bt/include/hci_stp.h` | `44e9a83347d84f0421ef539ed06dee8c000d5f28e01f2fb15e7c1c0d6b5ee543` |
| `drivers/misc/mediatek/connectivity/drv_bt/include/bt_conf.h` | `652da845929cb3922390911fdb53f0f2ed6c10409affb03c98954fd925844f3f` |
| `drivers/misc/mediatek/connectivity/bt/stp_chrdev_bt.c` | `55565ca1cafb1c9171965a06f5bae8b773c241c49cb2b2a3b770f17786eeb9d9` |
| `sound/soc/mediatek/common/mt_soc_pcm_btcvsd.c` | `b843ac6f6b70b376abbe08a41feb35b4f8d53953ced7d6f8df91b99e4058d356` |
| `sound/soc/mediatek/common/mt_soc_pcm_btcvsd.h` | `8f263b7f09b3c6169d15c77e7339a065408cf589125428995a875c80a87e35f4` |
| `sound/soc/mediatek/common/mt_soc_pcm_btcvsd_rx.c` | `ad01954f908baed2a5491737df887bbd284b2700648c49f799af0e2f6eeb927f` |
| `sound/soc/mediatek/common/mt_soc_pcm_btcvsd_tx.c` | `008351cce3a25ce4a0cabda0e8e1a72e4679e723bc5025570213949aeb9ada6a` |
| `sound/soc/mediatek/mt_soc_audio_6797/mt_soc_machine.c` | `f067eba71be95dec9972db9c6c775b923d7a1aa72bf3f97fce6c7d4b5cfe3cd0` |
| `sound/soc/mediatek/mt_soc_audio_6797/mt_soc_pcm_dl1_bt.c` | `6d427f93bd3581b20cdb6391907c471c7de9c8353802e3022f90d124949d208a` |
| `sound/soc/codecs/bt-sco.c` | `9c0530904e2072369419fd77542e8879da6084702828be443bfc107c40694c8f` |
| `arch/arm64/boot/dts/mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |
| `arch/arm64/configs/aeon6797_6m_n_defconfig` | `83f33ed07c17abe8dceaee64afd26de0cc970c0bae93681b68906636e21e883f` |
| `arch/arm64/configs/aeon6797_6m_n_hybris_defconfig` | `adcfc69fa6428231957edf46bb70c58e21899032e0569364f3207bcca3b73b2c` |
| Linux 7.1.3 `sound/soc/mediatek/common/mtk-btcvsd.c` | `935f11bfe1fdf003358a76fc22cada7210098279b4d0e99ed508d1d2c70e3612` |

Retained firmware strings were read from the private 2019 vendor set; no
firmware, binary or configuration content is copied here.

## Method

- `readelf -sW`/`-dW`/`-rW`, `strings`, `objdump -d` and `r2` disassembly and
  cross-reference work on stripped AArch64 ELF files, with relocation-derived
  pointer tables resolved by hand.
- The `daemon`/`HAL` split was established from the dynamic symbol tables, the
  `dlopen()`/`dlsym()` string sets, and the `.data` tables.
- Source facts were read directly at the pinned commits, not from the earlier
  summary.
- Firmware was searched for identifying strings only.

## Findings

### F1. The Android stack is two layers, and `/dev/stpbt` is a raw H:4 pipe

`libbluetooth_mtk_pure.so` exports `bt_init`, `bt_send_data`,
`bt_receive_data`, `bt_restore`, `BT_InitDevice`, `BT_DeinitDevice`,
`BT_SendHciCommand`, `BT_ReadExpectedEvent`, `GORM_Init` and `mtk_bt_op`. Its
`bt_send_data` is a `write()` loop over the caller's buffer with no framing or
header added; `bt_receive_data` reads a selected file descriptor. `bt_init`
opens `/dev/stpbt`. A factory-test library and the relay library reuse the same
symbols through `dlopen()`, so the raw byte stream is the de-facto vendor ABI.

The wrapper `libbluetooth_mtk.so` adds threads and callbacks: `BT_InitDevice`,
`BT_InitSCO`, `GORM_FW_Init_Thread`, `GORM_SCO_Init_Thread`, `mtk_fw_cfg`,
`mtk_sco_cfg`, `mtk_set_psm_control` (the `COMBO_IOCTL_BT_SET_PSM` ioctl),
`mtk_set_fw_assert`, `mtk_prepare_off`. It obtains command/event success through
a callback table (`bt_vnd_cbacks`), i.e. it is the Bluedroid vendor shim, not a
standalone stack.

`mtk_bt_op` implements a single operation. Its only accepted opcode is 0, and it
copies one 16-byte record from a chip-id-indexed table `audio_conf_map`
(20-byte entries: `{u32 chip id, u8 config[16]}`). For `0x6797` the record is
`03 00 00 00` followed by twelve zero bytes. The table gives all-zero records
for `0x6628/0x6630/0x6632` and `03 00 …` for the later chips.

### F2. The Android FW init script is eight commands fed by NVRAM

The preload table at `bt_init_preload_script_consys` resolves to eight
functions in `.text`:

| # | Function | Command | Parameters |
| --- | --- | --- | --- |
| 1 | Read BD_ADDR | `0x1009` | none |
| 2 | Set BD_ADDR | `0xFC1A` | 6 bytes from NVRAM or eFUSE, with two placeholder comparisons |
| 3 | Set Radio | `0xFC79` | 6 bytes from NVRAM `+0x10`, or 8 bytes with two extension bytes on `0x6632` |
| 4 | Set TX power offset | `0xFC93` | 3 bytes from `+0x1f`, or 6 with extensions |
| 5 | Set Sleep timeout | `0xFC7A` | 7 bytes from `+0x16` |
| 6 | HCI Reset | `0x0C03` | none |
| 7 | Set FW syslog | `0xFCBE` | `01 05`, gated by `persist.bt.syslog.enable` |
| 8 | Set SSP debug | `0x1804` | `01 01`, gated by `persist.bt.sspdebug.enable` |

The log strings confirm the NVRAM record is `ap_nvram_btradio_struct` and that
the library validates both the record count and the record size. The struct
fields observed by offset are: chip id at 0, BD address at 4, radio at 0x10,
sleep at 0x16, TX power offset at 0x1f, extension bytes at 0x28-0x2c, and two
6-byte default address constants later in the global (used to decide whether a
value is a real address or a placeholder).

The Gemian kernel's script is the same six core commands, with compiled defaults
in `bt_conf.h` and a `Set Voice`/`Set Codec` pair that is dead code because those
commands are not in the active table. With no config file and no writable
`/data/bluetooth`, the local initializer survives and Gemian sends `FC79 06 80
00 06 03 06`, `FC93 FF FF FF` and `FC7A 03 40 1F 40 1F 00 04`. If that path is
writable, the created file supplies `sDefaultCfg` and the radio bytes become
`07 80 00 06 05 07`.

### F3. The BD address path has two compiled values and a failed-write fallback

Gemian's `hci_stp_dev_init_work()` initializes its config structure with
`00:00:46:66:20:01`, while `bt_conf.h`'s `sDefaultCfg` uses
`00:00:46:02:79:01`. It tries `/data/BT.cfg`, then `/data/bluetooth/BT.cfg`.

- If the internal file cannot be read and cannot be created, the local
  initializer survives, `fgetEFUSE` stays false, `Read BD_ADDR` is skipped, and
  the fixed `00:00:46:66:20:01` is written to the controller.
- If the file exists or is created, its content is `sDefaultCfg`; when the
  address still equals that placeholder, the driver issues `Read BD_ADDR`, uses
  the reply, and writes it back.

The 2026-10-05 read-only check found neither file. It reported a non-placeholder
`hci0` address and the earlier record concluded that the address came from the
controller. That inference is not sound: the fixed fallback is not the
placeholder either. The observed value stays private, and the owner can compare
it with the two constants without publishing it. This does not change the
transport result, but it does change the mainline address decision: a first
driver should read the controller itself rather than trust Gemian's value.

The vendor library has the same two-tier precedence: NVRAM
`ap_nvram_btradio_struct` first, two compiled placeholders for validation, then
per-chip defaults, and the eFUSE read only on the placeholder branch.

### F4. MT6797 explicitly has no SCO initialization script

The SCO thread started by `mtk_sco_cfg`/`BT_InitSCO` walks the pointer stored in
`bt_init_postload_script_consys`. That object is zero in this build. The code
path compares the runtime chip id against `0x6797`, points the thread at that
empty table, then dereferences it, sees NULL and returns success without
sending anything. Other ids log "Unknown combo chip id" and fall through to the
same empty slot, so this library sends no SCO command on any chip.

In the same library the HCI `Set Voice Settings` (`0x0C26`) and vendor
`Set Codec` (`0xFC72`) byte arrays are present but the active init table does not
use them. On this platform the vendor stack therefore never configures an
HCI-SCO voice path.

### F5. The audio HAL selects the CVSD SRAM path, not PCM

`WCNChipController::InitAudioBTInfo()` `dlopen()`s
`/vendor/lib64/libbluetooth_mtk_pure.so`, `dlsym()`s `mtk_bt_op`, and calls it
with opcode 0 and a 16-byte stack buffer, retrying up to ten times with 100 ms
sleeps. It stores the result in a global and logs
`hw_if=%d, sample_rate=%d, sync_format=%d, bit_len=%d`. On failure it uses a
built-in default that is the same `03 00 00 00` record.

`BTChipHWInterface()` returns the first word, and `BTUseCVSDRemoval()` is
`return hw_if == 3;`. The HAL's `AudioBTCVSDControl` implements that mode; the
`AudioALSAPlaybackHandlerBTSCO`/`AudioALSACaptureDataProviderBTSCO` classes
implement the PCM interface mode and are not selected.

### F6. The HAL codes audio in user space with proprietary libraries

The HAL's strings and dynamic dependencies name
`/vendor/lib64/libcvsd_mtk.so` and `/vendor/lib64/libmsbc_mtk.so`, and it
`dlsym()`s `encInit`/`encProcess`/`encGetBufferSize`,
`decInit`/`decProcess`/`decGetBufferSize`, and `g711plc_*` concealment
functions. The ALSA devices therefore carry encoded SCO payloads; PCM and
codec handling live entirely in the proprietary libraries.

### F7. The kernel CVSD contract is shared between vendor and mainline

The vendor driver and Linux 7.1.3 `mtk-btcvsd.c` agree on the packet sizes
(60-byte TX, 30-byte RX plus 2 validity bytes), the packet-type table
(30/60/90/120/10/20), the register offsets (`0xfd0`, `0xfd4`, `0xfd8`), the
INFRA_MISC gate bit (`0x800`), the GIC SPI 286 level-low interrupt, and the
mixer controls for band and loopback. The mainline binding
`mediatek,mtk-btcvsd-snd` differs from the vendor node only in taking the two
CONSYS windows as `reg` and INFRA via a `mediatek,infracfg` phandle.

The vendor machine driver wires `BTCVSD_RX`/`BTCVSD_TX` with `snd-soc-dummy`;
mainline registers the component with no DAIs, so such links are still required
on Gemini.

### F8. Gemian builds in-kernel BlueZ plus the CVSD ALSA devices, but not the chrdev

`aeon6797_6m_n_hybris_defconfig` has `CONFIG_BT=y`,
`CONFIG_MTK_COMBO_BT_HCI=y`, `CONFIG_MT_SND_SOC_6797=y` and
`CONFIG_MTK_BTCVSD_ALSA=y`, and does not enable `CONFIG_MTK_COMBO_BT`. The
Android defconfig is the inverse: the chrdev is enabled and `CONFIG_BT` is
absent. This matches the observed `hci0 UP RUNNING` and `hci_stp_open`/
`hci_stp_close` traces on Gemian.

The exact installed BlueZ/PulseAudio file set was not re-read on this unit, so
the HFP backend (oFono vs BlueZ native) is an architectural expectation, not a
measured fact.

### F9. The retained firmware has no SCO/CVSD codec strings

`ROMv3_patch_1_0_hdr.bin` contains Wi-Fi/Bluetooth coexistence scheduling
strings (`bt_oper_freq_*`, `lte_op_freq`, `BT HW IRQ handler`). Neither patch
contains SCO, CVSD or PCM vocabulary. `WMT_SOC.cfg` contains only coexistence
and clock keys (antenna mode, GPS LNA pins, co-clock flag). This is consistent
with host-side coding and an SRAM transport rather than a firmware codec.

## Interpretation

The platform has exactly one demonstrated voice path, and it is not HCI SCO:
the AP sends encoded packets through CONSYS SRAM and a userspace library does
CVSD/mSBC and concealment. The alternative, standard HCI SCO over STP task 0,
is implemented in Gemian's transport (the H:4 state machine accepts type 3, and
`hci_stp_send_frame` would forward it) but has never been exercised and is not
used by any vendor component on this chip.

That leaves the HFP gap precise: A2DP needs only ACL, while HFP needs either
proof that the ROM consumes HCI SCO, or a bridge between a userspace SCO source
and the CVSD PCMs. The mainline tree already has the CVSD block; what it lacks
is a Gemini node, a machine link, and any codec/bridge.

## Limitations

- No device was contacted. The unit answered on its Wi-Fi address but had no
  listening SSH service, so the BlueZ/PulseAudio configuration, the enumerated
  sound card, and the live mixer state were not inspected.
- Binary analysis is static. No vendor code was executed, and no codec library
  (`libcvsd_mtk.so`, `libmsbc_mtk.so`) is present in the retained extraction, so
  their exact internal parameters are unknown.
- The HAL's `hw_if` enum has only the `3 == CVSD` relation proven; other values
  are inferred from the parallel PCM classes.
- Whether the ROM ignores, accepts or forwards HCI SCO is untested.
- The Android framework above Bluedroid is not in the extraction.
- One unit and one past runtime pass only.

## Consequences

- The durable reference is [MT6797 Bluetooth and Bluetooth audio](../../docs/hardware/mt6797-bluetooth.md).
- A2DP work can proceed on the ACL transport independently of audio code.
- HFP should start with a cheap discriminating test (HCI SCO) before any btcvsd
  implementation, because the answer changes the design.
- No repository patch, profile or device state is proposed by this record.
