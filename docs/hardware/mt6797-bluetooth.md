# MT6797 Bluetooth and Bluetooth audio

This document records how Bluetooth works on the Gemini: the AP-side transport,
the controller bring-up contract, the two userspace stacks that use it, and the
out-of-band path that carries voice audio. It states what was read from source
and binaries, what was observed on the device, and what remains hypothesis.

The transport framing, register-level BTIF contract and WMT power sequence are
not repeated here. Their evidence lives in the
[Bluetooth path review](../../experiments/2026-10-04-gemini-bluetooth-re/README.md)
and the [full-STP](../../experiments/2026-10-03-mt6797-wifi-audit/FULL_STP.md)
and [BTIF](../../experiments/2026-10-03-mt6797-wifi-audit/BTIF_MANDATORY.md)
notes. The 2026-11-01 userspace, firmware and BT-audio source/binary study is
the [Bluetooth audio reverse-engineering record](../../experiments/2026-11-01-gemini-bluetooth-audio-re/README.md).

## Identity and ownership

Bluetooth is not a device on the application processor. It is function 0 of the
MT6797 CONSYS (WMT) subsystem, addressed over the shared BTIF transport as STP
task 0. There is no Bluetooth register block, reset line or GPIO on the AP side,
and the vendor `mt6797.dtsi` has no Bluetooth node.

| Item | Value | Evidence |
| --- | --- | --- |
| WMT function number | `WMTDRV_TYPE_BT = 0` | vendor `wmt_exp.h` |
| STP task | `BT_TASK_INDX = 0` (GPS 2, Wi-Fi 3, WMT 4) | vendor `stp_exp.h` |
| Transport | `btif@1100c000`, SPI 130 level-low, clock `INFRA_BTIF` | vendor DT, live capture |
| TX/RX DMA | `btif_tx@11000a00` (SPI 116), `btif_rx@11000a80` (SPI 117) | vendor DT |
| AP-side supply | MT6351 `VCN33_BT` at 3.3 V, separate from `VCN33_WIFI` on this board | vendor `mtk_wcn_consys_hw.c`, live regulators |
| Control path | WMT function-control on task 4, payload path on task 0 | vendor `wmt_func.c`, `stp_core.c` |
| Voice path | CONSYS shared SRAM (CVSD), not HCI SCO | vendor `mt_soc_pcm_btcvsd*`, HAL analysis |

The WMT common power-on (hardware power, BTIF open, mode negotiation, ROM patch
download, RF calibration, coexistence) is owned by the connectivity owner. On
Gemian that owner is the vendor Android `wmt_launcher` running in the LXC
container, not a native Debian service.

## Bring-up order

There are two nested "on" operations, and confusing them is the usual source of
misdiagnosis.

1. **WMT/common on** powers CONSYS, opens BTIF, negotiates full STP mode, and
   downloads the two `ROMv3_patch_*` images from `/vendor/firmware`. It ends
   with RF calibration and the coexistence table. On Gemian this has already
   happened before Bluetooth is touched: `hci_stp_open()` waits up to 60 s for
   `mtk_wcn_wmt_func_on(WMTDRV_TYPE_BT)` because of the race with
   `6620_launcher`.
2. **Bluetooth function on** is the five-byte WMT command
   `01 06 02 00 00 01` on task 4, answered by `02 06 01 00 00`, after the
   `VCN33_BT` rail is enabled.
3. **HCI device open** then runs the controller initialization script on task 0
   and lets BlueZ or Bluedroid own the HCI device.

One bounded mainline boot demonstrated that step 2 and plain HCI commands work
without the ROM patch or RF calibration: WMT Bluetooth on, `HCI Reset`,
`Read Local Version`, `Read BD_ADDR`, and Bluetooth off, all on the negotiated
full-mode link ([runtime 3](../../experiments/2026-10-05-mt6797-bt-h1/RUNTIME_3.md)).
That is a transport result, not radio operation, and the absence of the patch is
not a supported configuration.

The reverse order matters: shutting Bluetooth off sends the WMT function-control
off command and only then drops the rail. A whole-chip CONSYS reset is surfaced
to the host as a synthesized HCI Hardware Error event, and the transport must be
reopened.

Bluetooth does not own the 2.4 GHz air: it shares the medium with the co-located
Wi-Fi and LTE radios. That arbitration, and the one-time host configuration that
enables it, is described in
[MT6797 connectivity coexistence](mt6797-connectivity-coexistence.md).

## HCI over STP

The payload is ordinary H:4 HCI, unmodified:

- The first byte is the HCI packet indicator (`01` command, `02` ACL, `03` SCO,
  `04` event), and it is part of the STP payload.
- STP adds the full-mode header with the task in the type nibble (task 0 gives
  `0x0n` where WMT yields `0x4n`), the sequence/ACK bits, the length checksum,
  and the CRC-16 trailer.
- BTIF is the only AP-side transport. Its FIFO and interrupt contract, plus the
  mandatory-mode boundary, are in the linked BTIF note.
- The host drives chip sleep and wake. After 30 ms idle the WMT sleep command
  `01 03 01 00 01` is sent on task 4; a transmit while asleep is preceded by the
  BTIF `WAK` line pulse, not by a wake byte.

`btmtkuart`-style frames (prefix `0x80`, zero sequence/ACK and zero CRC) are
*not* what the vendor sends after negotiation. Whether the MT6797 ROM tolerates
them is an open question; the repository's full-STP codec already implements the
vendor framing.

## Controller initialization

Both userspace stacks run an initialization script on task 0 before exposing the
controller. The six core commands are the same; the sources of their parameters
differ.

| Order | Command | Opcode | Parameters (Gemian compiled defaults) |
| --- | --- | --- | --- |
| 1 | Read BD_ADDR | `0x1009` | none; only when the config file still holds the placeholder address |
| 2 | Set BD_ADDR | `0xFC1A` | 6 bytes, little-endian, from config or eFUSE |
| 3 | Set Radio | `0xFC79` | `06 80 00 06 03 06` |
| 4 | Set TX power offset | `0xFC93` | `FF FF FF` |
| 5 | Set Sleep timeout | `0xFC7A` | `03 40 1F 40 1F 00 04` |
| 6 | HCI Reset | `0x0C03` | none |

Gemian's in-kernel driver (`drivers/misc/mediatek/connectivity/drv_bt/`) has two
scripts compiled in. The active one is the six-command table above; a 23-command
table with link-key type, unit key, encryption, PCM codec, OSC/LPO, PTA,
de-sense and sleep-register writes is compiled out. The `Set Voice` (`0x0C26`)
and `Set Codec` (`0xFC72`) commands exist as byte arrays and are patched from
the config structure, but are not in the active table, so they are never sent.

The parameters in the table are the static arrays, which equal the driver's
local config initializer. If `/data/bluetooth/BT.cfg` can be created, the driver
instead loads `sDefaultCfg`, whose radio bytes are `07 80 00 06 05 07`; the
sleep and TX-power bytes are the same. So the radio bytes actually sent depend
on whether that Android path is writable, which is itself unverified on this
unit.

The Android vendor stack does the same six commands plus two conditional ones
(Set FW syslog `0xFCBE`, SSP debug `0x1804`) driven by persistent properties, and
takes its parameters from the NVRAM record `ap_nvram_btradio_struct` when that
record is present, otherwise from per-chip compiled defaults. Whether this
unit's nvram partition contains a valid BT radio record has not been inspected;
the earlier filesystem check only covered `/data`.

### BD address

The address is not stored in the filesystem on a stock Gemini, and the two
compiled constants are easy to confuse. Gemian's `hci_stp` starts from a local
config initializer whose address is `00:00:46:66:20:01`, while
`bt_conf.h`'s `sDefaultCfg` uses `00:00:46:02:79:01` as the file template and as
the "is this still a placeholder" comparison value.

The actual sequence is:

1. Try `/data/BT.cfg`, then `/data/bluetooth/BT.cfg`.
2. If the internal file cannot be read *and cannot be created* (for example
   because the Android `/data` paths do not exist on a Debian rootfs), keep the
   local default and **do not** read the controller. The address is then the
   fixed `00:00:46:66:20:01`.
3. If the internal file exists or can be created, it starts as `sDefaultCfg`;
   when the address still equals that placeholder the driver issues
   `Read BD_ADDR`, uses the controller's eFUSE value, and writes it back to
   `/data/bluetooth/BT.cfg` (or `/data/BT.cfg` is read first when present).

One read-only Gemian inspection found neither file
([H6](../../experiments/2026-10-04-gemini-bluetooth-re/README.md#h6-gemian-read-2026-10-05)).
That means either the directory was absent or unwritable and the fixed default
was used, or the directory was writable and the file would have been created.
The earlier record inferred a controller reply from "not the placeholder"; that
does not follow, because the fixed local default is not the placeholder either.
The observed address is kept private; the owner can compare it with the two
constants above without publishing it. Mainline must not assume a unique factory
address and should read the controller explicitly or accept a DT
`local-bd-address`.

### Gemian and Android stacks

| Aspect | Gemian (observed) | Android vendor (read from binaries) |
| --- | --- | --- |
| HCI host | in-kernel BlueZ `hci_stp` (`CONFIG_MTK_COMBO_BT_HCI`) | userspace Bluedroid over `/dev/stpbt` |
| Transport API | `mtk_wcn_stp_send_data()` on task 0, direct RX callback | `write()`/`read()` on the char device, raw H:4 |
| Kernel BT stack | `CONFIG_BT=y` | no `CONFIG_BT`; only the chrdev |
| Init parameters | compiled defaults in `bt_conf.h` | NVRAM `ap_nvram_btradio_struct`, else per-chip defaults |
| Address storage | config file, else fixed default; eFUSE only on the placeholder branch | eFUSE or NVRAM record |
| SCO configuration | none in the active table | postload SCO script is explicitly empty for 0x6797 |

Gemian's HCI device is registered as bus `HCI_UART` with
`HCI_QUIRK_RESET_ON_CLOSE`, open/close/flush/send callbacks only, and no
`set_bdaddr`. The device is brought up by `bluetoothd`; the 2026-09-26 reference
boot had `hci0 UP RUNNING` with matching `hci_stp_open`/`hci_stp_close` WMT
traces. Gemian's kernel also builds the vendor MT6797 audio machine driver
(`CONFIG_MT_SND_SOC_6797=y`) and the CVSD ALSA drivers
(`CONFIG_MTK_BTCVSD_ALSA=y`), so the PCMs described below exist in the same
kernel image.

The exact BlueZ and PulseAudio package versions on the unit have not been
re-read since the userspace inventory; the running Debian base is 9.13 and the
installed PulseAudio modules come from the Gemian `10.0+gemian2` package. A2DP
is ordinary BlueZ/L2CAP traffic and depends only on a working ACL link. HFP/HSP
signaling is expected to go through oFono, which is installed, but its audio
path is the subject of the next section.

## Bluetooth audio

Two mutually exclusive host interfaces exist in the vendor design:

1. **AFE BT PCM (DAIBT).** The SoC's audio front end drives a PCM/I2S port
   connected to a separate Bluetooth baseband, with a `bt-sco` codec and the
   `Voice_MD1_BT`, `Voice_MD2_BT` and `VOIP_CALL_BT_*` DAI links. This is the
   classic MediaTek design for chips with physical PCM pins.
2. **CVSD over CONSYS shared SRAM (`btcvsd`).** The AP and the connectivity
   subsystem exchange already-encoded SCO payloads through SRAM windows, and the
   AP does the CVSD (or mSBC) coding in userspace. No audio pin exists between
   the SoC and CONSYS.

The Gemini uses the second. The vendor audio HAL asks the Bluetooth library for
a per-chip 16-byte interface descriptor and receives
`{hw_if = 3, sample_rate = 0, sync_format = 0, bit_len = 0}` for `0x6797`. Its
`BTUseCVSDRemoval()` predicate is literally `hw_if == 3`, and that selects the
`AudioBTCVSDControl` path. The vendor Bluetooth library's own postload SCO
script is a null pointer for `0x6797`, so the stack does not even try to
configure an HCI/PCM SCO interface.

### CVSD hardware contract

The vendor driver is `sound/soc/mediatek/common/mt_soc_pcm_btcvsd.c` with its
RX/TX platform drivers. The node and windows are in the vendor `mt6797.dtsi`:

```text
btcvsd@10001000 {
        compatible = "mediatek,audio_bt_cvsd";
        offset = <0xf00 0x800 0xfd0 0xfd4 0xfd8>;
        reg = <0x10001000 0x1000>,   /* INFRA, INFRA_MISC at +0xf00 */
              <0x18000000 0x10000>,  /* CONSYS PKV */
              <0x18080000 0x8000>;   /* CONSYS SRAM bank 2 */
        interrupts = <GIC_SPI 286 IRQ_TYPE_LEVEL_LOW>;
};
```

| Element | Meaning |
| --- | --- |
| INFRA_MISC bit 11 (`0x800`) | CVSD interrupt/wake gate; set means disabled |
| PKV `+0xFD0` | read pointer: low 16 bits are an offset into SRAM bank 2, written by CONSYS |
| PKV `+0xFD4` | write pointer: same encoding, the AP's next output area |
| PKV `+0xFD8` | control/status: bit 31 interrupt, bits 20:18 packet-type index, bit 21 TX not-ready, bit 22 RX ready, bit 23 TX underflow, bit 24 RX overflow |
| IRQ | GIC SPI 286, level-low, shared by both streams within one handler |

Buffer geometry (vendor and mainline agree):

| Direction | Unit | Buffers | Notes |
| --- | --- | --- | --- |
| TX (playback) | 60 bytes per packet | 8 (vendor), 18 (mainline) | each IRQ consumes 3 packets = 180 bytes |
| RX (capture) | 30-byte payload + 2-byte validity | 16 (vendor), 64 (mainline) | each IRQ produces 6 packets = 180 bytes |

An interrupt reports a packet-type index 0-5 mapping to lengths
30/60/90/120/10/20 bytes, with the corresponding packet count for a 180- or
120-byte batch. The control word also carries a bitmap that marks which packets
in the batch were actually received; the driver stores one 16-bit validity word
after each 30-byte payload so userspace can conceal missing ones. Flow control
is a simple watermark: the driver refuses to read when fewer than the batch size
of slots remain and refuses to write when fewer than the batch size of packets
are prepared, and reports overflow/underflow through the status bits.

The unit is *encoded* audio, not PCM samples. A 30-byte packet is 240 bits, i.e.
240 CVSD samples (30 ms at 8 kHz); the userspace codec turns PCM into those bytes
and back. The ALSA layer therefore sees a packet stream: playback periods must be
a multiple of 60 bytes, capture is read in whole 32-byte records (the vendor
capture copy rounds its request down to 64 bytes), and the `pointer()` callbacks
count packets, not frames. This is easy to misread as a normal PCM device.

### Kernel interfaces

Vendor kernel (`CONFIG_MTK_BTCVSD_ALSA=y`):

- two platform drivers, `mt-soc-btcvsd-rx-pcm` and `mt-soc-btcvsd-tx-pcm`, each
  registering an ASoC platform with a custom `copy()`/`pointer()`;
- two DAI links on the `mt-snd-card` sound card, `BTCVSD_RX` (capture) and
  `BTCVSD_TX` (playback), both with the `snd-soc-dummy` codec and DAI;
- mixer controls `btcvsd_band` (`NB`/`WB`) and `BT_DIRECT_LOOPBACK`.

Mainline has the same block as `sound/soc/mediatek/common/mtk-btcvsd.c`:
compatible `mediatek,mtk-btcvsd-snd`, the same five offsets, the same packet
sizes and validity scheme, the same registers and IRQ handling, and mixer
controls `BTCVSD Band` and the loopback switch. The DT shape differs: mainline
takes only the two CONSYS windows as `reg` and takes INFRA through a
`mediatek,infracfg` phandle, because the vendor described INFRA as `reg` 0. It
registers a component with no DAIs, so a machine driver still has to provide the
`BTCVSD_RX`/`BTCVSD_TX` links over `snd-soc-dummy`. No Gemini node exists yet.

The AFE DAIBT links remain in the vendor machine driver but are not selected on
this board. They would only matter for a hypothetical PCM-connected baseband.

### Userspace codecs and the HAL

The vendor HAL (`audio.primary.mt6797.so`) does not encode audio itself. It
`dlopen()`s two proprietary codec libraries:

- `/vendor/lib64/libcvsd_mtk.so` for narrow-band CVSD (`encInit`, `encProcess`,
  `decInit`, `decProcess`, buffer-size queries) plus G.711 packet-loss
  concealment (`g711plc_*`);
- `/vendor/lib64/libmsbc_mtk.so` for wide-band mSBC.

`AudioBTCVSDControl` owns the two ALSA streams, runs the codec, maps the
validity words to concealment, and selects narrow or wide band through the
`btcvsd_band` mixer control. It also exposes a modem-side ring-buffer interface
(`BT_SCO_ExtMDReadDataFromRingBuf`, `EXTMD_BTSCO_DIRECTION`), so the same path
carries the Bluetooth leg of a call. The `BTSCO` classes in the HAL exist for
the PCM-interface variant and are not used when `hw_if == 3`.

This split is the important architectural fact: **the kernel moves opaque SCO
payloads; the codec is a userspace library**. A mainline implementation inherits
the same requirement unless the SCO-over-HCI path turns out to work.

### A2DP, HFP and Gemian

| Profile | Bearer | Dependency on this platform |
| --- | --- | --- |
| A2DP (media playback) | L2CAP/ACL over STP task 0 | ordinary HCI ACL; SBC encoding is host userspace |
| HFP/HSP (two-way voice) | SCO | vendor path is btcvsd over SRAM, not HCI SCO |

So A2DP is a pure HCI media problem, while HFP is the one that needs the CVSD
contract. Gemian has the in-kernel BlueZ stack and the btcvsd ALSA devices, but
no userspace component connects a BlueZ SCO stream to those PCMs: Debian's
BlueZ/PulseAudio/oFono stack expects the kernel SCO socket to carry audio. Unless
the MT6797 ROM accepts HCI SCO packets, HFP audio needs either

- evidence that the ROM routes HCI SCO to its baseband (then standard `sco.c`
  works and no CVSD work is needed), or
- a userspace bridge that implements HFP audio over the `btcvsd` PCMs, which
  also means reproducing CVSD/mSBC coding, or
- a kernel-side bridge that presents the btcvsd stream as an SCO transport.

No test has yet distinguished these. The vendor software never exercises the
first, which makes it the least likely.

## Current mainline state and gaps

| Piece | State |
| --- | --- |
| WMT transport, negotiation, function control | demonstrated (one-shot diagnostics) |
| Task-0 HCI, version/address reads | demonstrated in one bounded boot |
| Persistent link and `hci_dev` | demonstrated: `btmt6797` module on the station ([record](../../experiments/2026-11-02-gemini-bluetooth/README.md)) |
| Power saving, wake pulse, reset recovery | not implemented in mainline; a stopped link needs a CONSYS reload |
| Scan, pairing, A2DP source (SBC) with BlueZ and BlueALSA | demonstrated on one boot with one headset; owner heard audio |
| LE | hidden from the core; see [controller behaviour](#controller-behaviour-on-mainline) |
| SCO over HCI | eSCO connects, status 0, with CVSD air mode; 0 SCO packets received in 30 s, and the headset heard static for valid 16-bit PCM sent ([T3](../../experiments/2026-11-02-gemini-bluetooth/README.md#t3-result-the-link-connects-no-voice-over-hci-2026-11-03)). Does not carry voice as tried |
| btcvsd driver in tree | runs on the station as a module with its own card; loopback carried voice from microphone to earpiece, heard by the owner ([T4](../../experiments/2026-11-02-gemini-bluetooth/README.md#t4-result-the-owner-heard-their-own-voice-2026-11-03)). Through its PCM stream, a capture matched a known recording played at the microphone, with the same lag at both ends of 20 s ([T6](../../experiments/2026-11-02-gemini-bluetooth/README.md#t6-result-the-capture-is-the-microphones-signal-2026-11-03)), and matched as well with playback running; the earpiece has noise whatever is sent ([T7](../../experiments/2026-11-02-gemini-bluetooth/README.md#t7-result-silence-didnt-change-the-noise-2026-11-03)), and with a call signalled ([T8](../../experiments/2026-11-02-gemini-bluetooth/README.md#t8-result-the-headset-noticed-the-call-and-the-capture-didnt-change-2026-11-03)). With mSBC the owner's noise was gone, and both directions worked: the controller refuses Enhanced Setup `0x043d` for transparent air (`0x20`) but accepts Setup Synchronous Connection `0x0428` with voice `0x0063` ([T11](../../experiments/2026-11-02-gemini-bluetooth/README.md#t11-result-an-msbc-link-and-the-noise-went-away-2026-11-03)), which the driver now makes the core use ([T12](../../experiments/2026-11-02-gemini-bluetooth/README.md#t12-result-the-kernels-own-msbc-link-heard-clean-2026-11-03)) |
| Userspace CVSD/mSBC codec | proprietary, not in mainline |
| HFP audio bridge | none |

The durable design consequence is that Bluetooth audio is two separable
projects: A2DP follows from a working ACL transport, and HFP follows from the
CVSD contract plus a coding/bridging component. Neither is required for
Bluetooth keyboards, mice, serial profiles or A2DP.

## Controller behaviour on mainline

Observed on this unit with both ROM patches loaded, through the
[2026-11-02 record](../../experiments/2026-11-02-gemini-bluetooth/README.md):

| Fact | Detail |
| --- | --- |
| Identity | HCI and LMP version `0x08` (4.2), HCI revision `0x0010`, LMP subversion `0x0307`, manufacturer 70; ACL 1021 bytes, 6 packets; SCO 184 bytes, 1 packet |
| Address | Read BD_ADDR returns the placeholder `00:00:46:02:79:01`, so it is not unique. This answers the open point in [BD address](#bd-address) for this unit |
| LE | The LE feature bit is set, Supported Commands octets 25-28 are zero, and LE Set Event Mask `d0 07 00 00 00 00 00 00` is refused with `0x20`. Gemian's older core sends a mask with nothing above `0x20`, so a newer event bit is probably what's refused (inferred). The driver hides LE |
| MWS | Get MWS Transport Layer Configuration is listed but refused with `0x02`. Gemian's core has it under `#if 0`, blaming the chip. The driver sets the core's quirk |
| Inquiry | Inquiry Cancel is refused with `0x0c`, and no Inquiry Complete event was seen, so the core's `INQUIRY` flag stays set. Paging and pairing still work. Not understood |
| Completed packets | Number of Completed Packets events are 11 bytes long, with bytes the spec doesn't define. The core ignores them |
| Link | One stream stopped the link within 0.19 s on an ACK timeout, with the firmware repeating its last ACK, before the resend existed. The resend has since recovered one timeout (`timeouts=1 resent=7`). The cause of the losses is open |

The vendor's Set Radio and TX offset are not sent by default (`gemian_radio`), and A2DP
worked with the controller's own settings at a few metres. Their effect on output power
is not measured; Read Transmit Power reports 10 without them and 8 with Gemian's local
bytes. The owner hears SBC skip from about 4 yards and AAC not at twice that, without a
control yet ([T14](../../experiments/2026-11-02-gemini-bluetooth/README.md)). On a voice link they were accepted and left the earpiece noise about the same, by the owner's
ear on one run ([T9](../../experiments/2026-11-02-gemini-bluetooth/README.md#t9-result-gemians-radio-settings-left-the-noise-about-the-same-2026-11-03)).

## Open questions

- Why did the T2 stream stall? It happened once, late in a long CONSYS lifetime.
- What ended the inquiry, and when? See the table above.
- An eSCO link uses the CVSD SRAM path whatever the host's data path: the registers are zero
  before a link and its flags come up with it, and the upstream driver's loopback carried
  voice at about 45 interrupts a second
  ([T4](../../experiments/2026-11-02-gemini-bluetooth/README.md#t4-result-the-owner-heard-their-own-voice-2026-11-03)).
  Open: the quality of a host CVSD coder against it, and mSBC.
- Does the ROM's CVSD SRAM path require firmware-side enabling beyond the INFRA
  bit and the packet pointers? The vendor driver has no explicit "start" command.
- What does the ROM patch contribute to BT audio? It contains BT/Wi-Fi
  coexistence scheduling and a "BT HW IRQ handler" string, but nothing that
  identifies SCO or CVSD handling.
- Are the vendor NVRAM `Voice` and `Codec` fields used on this board at all?
  They are patched into command arrays that are not sent.

## Evidence

- Vendor and Gemian kernel 3.18 source at commit
  `59e00a9144d782e148332009a835b99c43382467`: `drv_bt/`,
  `sound/soc/mediatek/common/mt_soc_pcm_btcvsd*`,
  `sound/soc/mediatek/mt_soc_audio_6797/mt_soc_machine.c`,
  `arch/arm64/boot/dts/mt6797.dtsi`, `aeon6797_6m_n_hybris_defconfig`.
- Android vendor binaries from the retained 2026-07-12 extraction:
  `libbluetooth_mtk.so`, `libbluetooth_mtk_pure.so`, `libbluetoothem_mtk.so`,
  `libbluetooth_relayer.so`, `libbluetooth_hw_test.so`,
  `audio.primary.mt6797.so`. Hashes and function-level notes are in the
  [2026-11-01 record](../../experiments/2026-11-01-gemini-bluetooth-audio-re/README.md).
- Linux 7.1.3 `sound/soc/mediatek/common/mtk-btcvsd.c`.
- Retained firmware `ROMv3_patch_1_0_hdr.bin`, `ROMv3_patch_1_1_hdr.bin`,
  `WMT_SOC.cfg`.
