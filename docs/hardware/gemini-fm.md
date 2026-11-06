# Gemini FM receiver

The MT6797 CONSYS reaches an MT6631 FM receiver through its firmware. This
document is the protocol and sequence contract a mainline driver needs. It
comes from the public downstream tree and a static look at the retained
firmware files. On this device only the power-up to the identity check, the
identity read and the power-down have run (F1, 2026-11-05): `0x62` read
`0x6631` three times, and all 25 commands got their events. Everything past
that, including the DSP, tuning and audio, is still vendor behaviour, not an
observation of this board. The
chronology, the observations and the first device test are in the
[FM record](../../experiments/2026-11-05-gemini-fm-radio/README.md).

Source: [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18)
at `8cfe6596`, `drivers/misc/mediatek/connectivity/fmradio/` (`core/`,
`inc/`, `mt6631/`) and `sound/soc/mediatek/mt_soc_audio_6797/mt_soc_pcm_fm_i2s*.c`.
It is read as evidence; no code is reused.

## Ownership and transport

| Item | Value |
| --- | --- |
| Function switch | WMT function type 1 (`WMTDRV_TYPE_FM`); Bluetooth is 0, GPS 2 |
| Data channel | STP task 1 (`FM_TASK_INDX`) on the shared CONSYS link |
| Rails | covered by the common CONSYS power-on; the FM-only VCN28 step needs co-clock mode, which Gemini's `WMT_SOC.cfg` disables |
| AP resources | none: no FM register window, interrupt or pin on the AP |
| Executor | every FM command is executed by the CONSYS firmware. The two retained `ROMv3` patches mention FM only in a WMT default-parameter message and a coexistence task-status message, so the FM handler is inferred to sit in the CONSYS ROM |

## Packets

All little-endian.

```text
command  01 OP LEN_LO LEN_HI payload[LEN]
event    04 OP LEN_LO LEN_HI payload[LEN]
```

| Opcode | Name | Command payload | Event payload |
| --- | --- | --- | --- |
| `0x03` | FM register read | `ADDR` | value, 2 bytes |
| `0x04` | FM register write | `ADDR VAL_LO VAL_HI` | status |
| `0x07` | enable (batch) | batch ops | status |
| `0x09` | tune (batch) | batch ops | empty acknowledgment, then `01` when the tune is done |
| `0x0d` | RDS data, unsolicited | | up to 12 raw RDS groups |
| `0x0e` | ramp down (batch) | batch ops | status |
| `0x12` | DSP patch segment | `SEG_NUM SEG_ID data` | status |
| `0x13` | coefficient segment | `SEG_NUM SEG_ID data` | status |
| `0x17` | soft-mute tune (CQI) | `01 FREQ_LO FREQ_HI` | channel quality record |
| `0x18` | CONSYS MCU register read | `ADDR` (4 bytes) | value, 4 bytes |
| `0x19` | CONSYS MCU register write | `ADDR VAL` (4 + 4 bytes) | status |
| `0x20` | common SPI write | `04 ADDR_LO ADDR_HI VAL` (4 bytes) | status |
| `0x21` | common SPI read | `04 ADDR_LO ADDR_HI` | value, 4 bytes |

The `04` in the common SPI packets selects the RF chip's top block (`02` would
select FM). Segments are at most 512 bytes. `SEG_NUM` is `len / 512 + 1`,
so a length that is an exact multiple of 512 would send an empty last
segment; neither retained file has such a length.

A batch is a list of operations the firmware runs in order, each
`OP SIZE args`:

| Op | Name | Args |
| --- | --- | --- |
| `0x80` | write | `ADDR VAL16` |
| `0x81` | delay | microseconds, 32 bit |
| `0x82` | read until | `ADDR MASK16 VALUE16` |
| `0x83` | modify | `ADDR AND16 OR16` |
| `0x84` | sleep | milliseconds, 32 bit |
| `0x85` | top write | `04 ADDR16 VAL32` |
| `0x86` | top read until | `04 ADDR16 MASK32 VALUE32` |
| `0x87` | top modify | `04 ADDR16 AND32 OR32` |

The vendor waits 3 s for most replies, 6 s for a soft-mute tune and 15 s for a
seek or scan.

## Registers

FM registers are 16 bit, addressed by one byte.

| Register | Name | Use |
| --- | --- | --- |
| `0x60` | `MAIN_CG1_CTRL` | clocks; `0x07` host controls RF, `0x0f` DSP controls RF |
| `0x61` | `MAIN_CG2_CTRL` | D0 ASIP power-down, D1 ASIP reset release, D4 short antenna, D7 I2S instead of line out, D12 75 µs de-emphasis, D15 ROM version request |
| `0x62` | `MAIN_HWVER` | reads `0x6631`; the vendor's identity check |
| `0x63` | `MAIN_CTRL` | D0 tune, D1 seek, D2 scan, D4 RDS, D5 mute, D8 ramp down |
| `0x64` | | D4:0 = 2 when the digital init is complete |
| `0x65` | `CHANNEL_SET` | D9:0 channel, D15:12 channel parameter |
| `0x69` | `MAIN_INTR` | D0 tune/seek done, D5 RDS; write 1 to clear |
| `0x6a`, `0x6b` | interrupt masks | `0x0021` (done and RDS) |
| `0x6c` | `RSSI_IND` | D9:0 RSSI, D12 stereo |
| `0x75` | | D3 forced mono |
| `0x7d` | | volume |
| `0x80`-`0x87`, `0xf0` | RDS | configuration, FIFO status, data and pointer |
| `0x83`, `0x84` | | during the ROM query: D15:8 ROM version, and `0x0001` when ready |
| `0x90`-`0x92` | DSP patch control | reset to `0x0040` then `0` after the downloads |
| `0x9b` | | `0xf9ab` sets the I2S transmit mode; power-down clears D2:0 |
| `0x9c` | | D1:0 = `11` mutes |

Conversions:

- Channel: `CHANNEL_SET[9:0] = (f_kHz / 10 - 6400) * 2 / 10`, that is,
  50 kHz steps above 64 MHz. 87.5 MHz is 470, 108.0 MHz is 880.
- RSSI: `RSSI_IND[9:0]` is signed 10 bit, and `dBm = value * 6 / 16`
  (0.375 dB per step). Gemian's threshold of `-296` is -111 dBm.
- Volume: `0x7d` takes one of 16 values, `0x0000` (silent) to `0x7fff`.
  Seek and scan use the hardware mute, not volume.

## Power-up

In order, from `mt6631_PowerUp()`:

1. WMT FM function on.
2. MCU write `0x8102600c = 0x0000800f` (common SPI parameters).
3. MCU `0x81024030` set D1 (a-die clock enable), `0x81021234` set D7 (26 MHz
   crystal stays awake).
4. Top `0x0c0` set D28:27 (bandgap LDO).
5. Enable batch: top `0xa10 = 0xffffffff`; top `0x060` through
   `0x30, 0x35, 10 µs, 0x15, 0x05, 10 µs, 0x45` (FM power domain on); FM
   `0x7f = 0x800f`; `0x60 = 1`, 3 ms, `0x60 = 3`, `0x60 = 7`; `0x70 = 0x0040`;
   `0x61` D12 from the de-emphasis setting.
6. Read `0x62`; anything but `0x6631` aborts. This board reads `0x6631`.
7. ROM query: set `0x61` D15, D1, clear D0; poll `0x84` every 1 ms for `1`;
   ROM version is `0x83[15:8]`; then clear D15 and set `0x61[1:0] = 01`.
8. Patch download (`0x12`) and coefficient download (`0x13`), then `0x92 = 0`,
   `0x90 = 0x40`, `0x90 = 0`.
9. Digital init batch: RF and ADPLL dividers (`0x21 = 0xe000`,
   `0xd8`-`0xdb`, `0x23 = 0x4000`), masks `0x6a = 0x6b = 0x21`, `0x60 = 0x0f`,
   release ASIP (`0x61` D1 set, D0 clear), 100 ms, wait for `0x64[4:0] = 2`.
10. Fine-tune batch: `0x60 = 7`, seven RF trim writes (`0x01`, `0x03`,
    `0x15`-`0x17`, `0x34`, `0x35`), `0x60 = 0x0f`.
11. Audio out: `0x9b = 0xf9ab`; MCU `0x81024064 = 0x14`,
    `0x81024058 = 0x888100c3`, `0x81024054 = 0x100`.

The ROM version picks `mt6631_fm_vN_*` with N = version + 1. Only v1 is
installed; an unknown version falls back to the newest file present, which
is still v1.

## Tune, search and quality

- **Tune:** ramp-down first; `0x60 = 7`; ADPLL gain `0x0f`; cell mode in
  `0x30` D3:2 (`10` TDD for 90.4-91.1, 97.9-99.4 and 106.9-108.0 MHz, else `00`
  FDD); `0x60 = 0x0f`; write `CHANNEL_SET`, with a channel parameter in D15:12
  for 18 channels; tune batch (`0x63` D0, then 100 ms). The tune gets two
  events: an empty acknowledgment, then one with payload `1` when done; the
  vendor waits for both. Nine channels (90.9-91.2, 103.8-104.2 MHz) also
  switch the common SPI clock to 64 MHz first (CONSYS MCU `0x81021138`,
  `0x80026000`, `0x8002110c`, `0x81026004`). All three lists are fixed tables
  in the MT6631 library; the [FM record](../../experiments/2026-11-05-gemini-fm-radio/README.md#why-f2-refused-the-owners-first-station-r9)
  has them reduced to the FM band.
- **Search:** the chip's own seek is compiled out on MT6631. The vendor steps
  through channels with soft-mute tune (`0x17`), which returns RSSI, PAMD, MR,
  ATDC, PRX, ATDEV and soft-mute gain for one frequency. A channel is valid when
  every value passes Gemian's thresholds (RSSI ≥ -296, PAMD ≤ -12,
  ATDC ≤ 3496, MR ≥ -67, PRX ≥ 64, ATDEV ≥ ATDC, gain ≥ 16421). A V4L2
  hardware seek is therefore a driver loop, not a chip command.
- **Mono and stereo:** stereo is `RSSI_IND` D12; forced mono is `0x75` D3,
  written between top `0x050 = 7` and `0x050 = 0x0f`.
- **RDS:** enable reads `0x80`, writes `0x80 = 6` (FIFO start threshold) and
  sets `0x63` D4. The firmware then pushes the groups itself as unsolicited
  `0x0d` events: two 16-bit words (`sin`, `cos`), then up to 12 groups of six
  16-bit words each, blocks A to D, the corrected-bit count and the per-block
  CRC flags. The host decodes the groups; the register-FIFO read path in the
  MT6631 library is compiled out. Disable clears `0x63` D4.

## Power-down

From `mt6631_PowerDown()`: MCU `0x81024064 = 4`, `0x81024058 = 0x88800000`,
`0x81024054 = 0x180`; common SPI clock back to 26 MHz; release 64 MHz;
crystal sleep allowed again; enable batch clearing `0x9b` D2:0, `0x60 = 0x330f`,
ASIP reset, four core resets on `0x6e`, `0x60 = 0`, `0x60 = 0x4000`, `0x60 = 0`,
top `0x060` through `0x05, 0x15, 0x35, 0x30`, wait for D3 and D1 clear; then MCU
`0x80101030` clear D1; WMT function off.

It is not the reverse of power-up: power-up sets D1 of `0x81024030` but
power-down clears D1 of `0x80101030`, and the bandgap LDO bits are never
cleared. Whether that matters is open; a first test should follow the vendor
as written and check Wi-Fi afterwards.

## Audio

The MT6631 sends FM samples to CONSYS on a two-wire digital link, and CONSYS
drives an internal I2S as master: 32 kHz, 16 bit, I2S format, on the CONSYS pad
(`FM_I2S_PAD_CONN`). Gemian prints exactly this configuration at boot.

The AFE takes it on its second I2S input in slave mode, with the pad select set
to CONSYS, then:

- ASRC from 32 kHz to 44.1 or 48 kHz;
- hardware gain 1;
- interconnect `I00/I01` to `O13/O14`, the DAC path to the MT6351, for
  playback without a buffer, and `I10/I11` to `O03/O04` and `O28/O29`;
- the AWB variant records the same input to memory.

No MT6351 analog input and no board audio pin is involved. Mainline has no
MT6797 I2S DAI yet ([audio](gemini-audio.md)), so this input is new AFE work.

## Firmware files

| File | Bytes | Content | Sent as |
| --- | --- | --- | --- |
| `mt6631_fm_v1_patch.bin` | 1028 | 16-bit DSP words, no header or strings | `0x12`, segments 512, 512, 4 |
| `mt6631_fm_v1_coeff.bin` | 1092 | coefficient table; the vendor reads bytes 38-39 as the patch version (`0x0000` here) and clears bytes 4-5 when the ROM is unknown (already zero here) | `0x13`, segments 512, 512, 68 |
| `fm_cust.cfg` | 304 | text: RSSI thresholds, 50 µs de-emphasis, 26 MHz oscillator | parsed by the host; mainline uses driver defaults |

Digests are in the [WMT recovery runtime summary](../../experiments/2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt).
Redistribution rights are unknown, so the files are not committed. Gemian's
`libfmcust.so` only maps the WMT chip ID to an FM chip (`0x6797` to MT6631);
it holds no band or region data.

## Mainline mapping

| Vendor | Mainline |
| --- | --- |
| `/dev/fm` and its ioctls | V4L2 radio receiver, `/dev/radio0` |
| `fm_link` over `mtk_wcn_stp_*` | CONSYS STP task-1 attach and send, as for GNSS and Bluetooth |
| `mtk_wcn_wmt_func_on(FM)` | a CONSYS FM function control |
| hardware seek | `VIDIOC_S_HW_FREQ_SEEK` driven by soft-mute tunes |
| volume, mute, mono | V4L2 audio controls |
| de-emphasis | `V4L2_CID_TUNE_DEEMPHASIS`, default from the region |
| antenna type | a driver default until the antenna is identified |
| `mt_soc_pcm_fm_i2s` | an AFE I2S-input DAI with ASRC and a card link |
