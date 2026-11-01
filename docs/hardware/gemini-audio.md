# Gemini audio input and output

Scope: the Gemini's local analog audio paths and the digital transports that
feed them. This is the durable summary of the vendor source and the
[Gemini audio RE](../../experiments/2026-10-04-gemini-audio-re/README.md); the
experiment owns the full line-by-line citations, hypotheses and negative
results.

Confidence is split deliberately:

- **verified** means the vendor source, the stock DTB/HAL or the mainline
  source states it directly;
- **unresolved** means the public source and retained evidence do not settle
  which part is populated or which path the stock HAL selects.

## 1. Digital topology

```text
MT6797 AFE (audio@11220000, SPI 151)
  ├─ ADDA DAI ── five pads ── MT6351 codec
  ├─ PCM 1/2 ─── modem voice
  ├─ BTCVSD ──── Bluetooth SCO
  ├─ I2S0 ────── possible MAX98926 smart amplifier (not enabled)
  └─ hostless / memory interfaces

MT6351 codec
  ├─ DACL/DACR -> HPL/HPR, RCV, LOL
  ├─ AIN0/AIN1/AIN2 -> PGA L/R -> ADC L/R
  ├─ MICBIAS0/1/2
  └─ ACCDET (jack, headset mic, buttons)
```

The AFE is `mediatek,mt6797-audio` at `0x11220000`, 64 KiB, SPI 151
level-low. The vendor exposes 30 audio clocks; the current mainline binding
names eight, including `mtkaif_26m_clk`, which the ADDA DAPM graph acquires by
name. The mainline AFE driver limits register access to `AFE_MAX_REGISTER =
0x84c`, well inside the vendor aperture.

The codec digital interface uses five dedicated pads:

| Pad | GPIO | Direction |
| --- | ---: | --- |
| `AUD_CLK_MOSI` | 146 | codec clock |
| `AUD_DAT_MISO` | 147 | capture |
| `AUD_DAT_MOSI` | 148 | playback |
| `VOW_CLK_MISO` | 149 | voice-wake clock |
| `ANC_DAT_MOSI` | 150 | active-noise data |

The vendor knows these pads, but the Gemini board DTS leaves every
`aud_clk_mosi`/`aud_dat_mosi`/`aud_dat_miso` pinmux entry commented out, and
`AudDrv_GPIO_Request()` is only called for the VOW path, which the Gemini
build does not use. The board DWS sets these five pads to mode 1
(`AUD_CLK_MOSI`, `AUD_DAT_MISO`, `AUD_DAT_MOSI`, `VOW_CLK_MISO`,
`ANC_DAT_MOSI`) and the preloader applies that default, which is why the
commented-out states still work. The ADDA codec link is internal to the
SoC/PMIC, so these five pads are **not** part of the Gemini audio path and
mainline should leave them at the boot state.

The only audio pads that need mainline pinctrl are the two amplifier mode
lines (GPIO243/244), because the MT6797 pin controller does not switch a pad
to GPIO mode when the GPIO is requested. Proposal `0401` adds one default
pinmux state per amplifier. GPIO234/235 need no state: GPIO234 is only driven
by the unused DCC capture path and GPIO235 is only a manual debug knob.

### 1.1 Clocking and high-rate audio

The vendor `top_mux_audio` parent is `clk26m` for rates up to 48 kHz and
`top_sys_pll3_d4` once the downlink rate reaches 96 kHz
(`AudDrv_AUD_Sel(1)` in `SetDLSrc2`). The APLLs are a separate path:
APLL1 (180.6336 MHz) and APLL2 (196.608 MHz) feed `aud_mux1/2`, giving
22.5792/24.576 MHz, and `EnableALLbySampleRate()` enables them from
`EnableAfe()` only while `mtk_soc_always_hd` is set. The live Gemian boot
shows `EnableApll1/2` only around HDMI open/close, not on the ADDA path, so
the Gemini codec card does not need the APLLs. 48 kHz from `clk26m` is the
correct first-card configuration.

High-rate capture additionally uses the ADC hires format and the
`AUDIO_TOP_CON1` PDN_ADC_HIRES/PDN_ADC_HIRES_TML gates (`0x10000` and
`0x20000` in `mt6797-reg.h`). Mainline has the format code but a later
unconditional write put `AFE_ADDA_NEWIF_CFG2` back on the 260 kHz ANC
divider, and it never powers the hires gate. Proposals `0403` and `0404`
fix the clobber, select `top_sys_pll3_d4` at >= 96 kHz, and power the hires
gate for high-rate capture.

The vendor card is `mt-snd-card` with 31 links. Mainline has the AFE, MT6351
codec and `mt6797-mt6351` machine drivers, but no Gemini card node, board DAPM
routes, amplifier, jack or microphone wiring. The MT6351 MFD child is also
local-patch-only in the current package.

## 2. Outputs

| Output | Codec path | Board path | Stock control |
| --- | --- | --- | --- |
| Earpiece | `DACL -> RCV Mux -> RCV Buffer` | MT6351 HS driver | `Voice_Amp_Switch` |
| Headphones | `DACL/DACR -> HPL/HPR Mux -> HPL/HPR` | cap-less HP jack | `Audio_Amp_L/R_Switch` |
| Speaker | `DACL/DACR -> HPL/HPR Mux -> HPL/HPR` | HP outputs into a board amplifier, GPIO243/244 enable | `Audio_Amp_L/R_Switch` + `Ext_Speaker_Amp_Switch` |
| LOL / `speaker_output` | `DACL -> LOL Mux -> LOL Buffer` | line-out buffer | `Speaker_Amp_Switch` |
| Headphone as loudspeaker | HP outputs re-used | headset speaker mode | `Headset_Speaker_Amp_Switch` |
| Bluetooth SCO/A2DP | BTCVSD / host PCM | BT transport | separate |
| FM / HDMI / dock | digital or hostless | separate transport | separate |

The MT6351 has **no on-PMIC class-D speaker amplifier**. The stock HAL's
speaker path is now resolved by disassembly: `OpenSpeakerPath` and
`OpenHeadphoneSpeakerPath` are aliases at the same address, and the body
applies `headphone_output` followed by `ext_speaker_output`. `CloseSpeakerPath`
reverses that order. It never applies `speaker_output` / `Speaker_Amp_Switch`
and never touches the I2C MAX98926 node.

So the internal speaker is driven from **HPL/HPR into a board amplifier**,
enabled by `Ext_Speaker_Amp_Switch` → `AudDrv_GPIO_EXTAMP_Select()` /
`EXTAMP2_Select()`. Those helpers emit a three-pulse sequence on **GPIO243**
and **GPIO244** and wait 25 ms.

The amplifier identity is now resolved from the code and the public
datasheet: it is an **AW8736FCR** (AWINIC, FC-16 package), not a generic
AW87xx. The vendor `AW8736_MODE*` definitions match the AW8736 mode table
exactly:

| Mode | Pulses | NCN output |
| --- | ---: | --- |
| `AW8736_MODE1` | 1 | 1.2 W |
| `AW8736_MODE2` | 2 | 1.0 W |
| `AW8736_MODE3` | 3 | 0.8 W |
| `AW8736_MODE4` | 4 | NCN off, 1.65 W at THD 1% |

The code selects **mode 3**, the 0.8 W NCN setting, on both control lines.
AWINIC's own selector lists `AW8736FCR` as the FC-16 orderable variant; the
mode table and package match the vendor code.

### 2.3 Speaker, earpiece and microphone population

Public Planet Computers documentation resolves the functional population:

- the product specification lists **stereo speakers**, **handset speakers**
  and **integrated ambient microphones**;
- the Gemini PDA user guide says the device has "a microphone and speaker at
  both ends of the Gemini case" and that calls work in either orientation;
- the Wikipedia entry lists "stereo speakers" and "dual microphones".

Two independent AW8736 mode lines (GPIO243/244), both pulsed in mode 3 for a
stereo HPL/HPR feed, are consistent with two mono amplifiers — one per
speaker — rather than one stereo part. A direct BOM or schematic line item
has not been captured, so the exact orderable count remains a visual check,
but the functional reading is two amplifiers.

The user guide's handset speaker plus the stock `receiver_output` /
`Voice_Amp_Switch` path means the MT6351 RCV/HS driver has a physical load.
This is an earpiece/handset transducer, not an unused codec port.

The dual-microphone specification matches the AIN0 main and AIN2 reference
paths. The stock policy does not attach `Built-In Back Mic` by default, so the
second capsule is wired as a reference/secondary mic rather than a selectable
primary device.

The pulse timing matches the datasheet (`TH`/`TL` 0.75-10 µs; the code uses
2 µs). The vendor then waits 25 ms before audio, while the AW8736 datasheet
lists a 40 ms start-up time; mainline should use at least the datasheet value
or measure the actual turn-on.

The MT6351 LOL path remains a codec capability and the `speaker_output` HAL
path exists, but the stock speaker alias does not select it. It may be unused
on this board or reserved for another route.

The RCV/earpiece driver exists in the codec and the stock HAL exposes an
Earpiece port; the user guide's handset speaker confirms a load on it.

Headphone output is cap-less and uses PMIC efuse offset trim. The vendor reads
the trim; mainline `mt6351.c` does not. Headphone gain defaults to −40 dB and
the vendor de-pop flow is disabled (`use_hp_depop_flow = <0>`).

The stock HAL exposes these mixer paths:

```text
headphone_output       Audio_Amp_L/R_Switch
receiver_output        Voice_Amp_Switch
speaker_output         Speaker_Amp_Switch          (not used by OpenSpeakerPath)
two_in_one_speaker     Speaker_Amp_Switch + class AB
ext_speaker_output     Ext_Speaker_Amp_Switch      (selected by OpenSpeakerPath)
headphoneSpeaker       Headset_Speaker_Amp_Switch
```

`OpenSpeakerPath` = `OpenHeadphoneSpeakerPath` = `headphone_output` +
`ext_speaker_output`. The earlier ambiguity between LOL, the GPIO amplifier and
the I2C smart amplifier is therefore closed for the stock HAL: it uses the
headphone DAC path and the GPIO243/244 amplifier.

### 2.1 The I2C smart-amplifier alternative

The live Gemini DTB has an I2C0 `0x31` node named `speaker_amp` with
compatible `mediatek,speaker_amp`. The vendor source matches that compatible
to a MediaTek-adapted **MAX98926** driver (`max98926L`); its Kconfig symbol is
unset in the stock build, and the machine driver looks for a different
compatible (`maxim,max98926L`). The live client is therefore unbound, and the
retained Gemian boot log records `max98926L is not find`.

If that part is populated, it needs an I2S0 feed and board pins that the
public DTS comments out. Mainline has the MAX98926 driver but no MT6797 I2S
DAI and no board wiring, so the smart-amplifier path is a larger prerequisite
than the GPIO-enabled headphone-output speaker path.

The retained Gemian boot also records `Audio_Hpl_Offset_Get` and
`GetAudioTrimOffset channels = 1`, confirming that the stock path applies the
headphone offset trim. Mainline has no equivalent.

### 2.2 Headphone offset trim

The vendor `Auddrv_Read_Efuse_HPOffset()` reads the PMIC efuse rows
`0xe`–`0x10` through the efuse engine (`0x0C00`, `0x0C10`, `0x0C18`,
`0x0C1A`) and derives two coarse and two fine fields:

```text
HPL coarse = (word0 >> 10) & 0xf
HPR coarse = ((word0 >> 14) & 0x3) | ((word1 & 0x3) << 2)
HPL fine   = (word1 >> 3) & 0x3
HPR fine   = (word1 >> 5) & 0x3
```

It writes them into `AUDDEC_ANA_CON2` (`0x0CF6`):

```text
bit 11      trim circuit enable
bits 6:3    HPL coarse
bits 10:7   HPR coarse
bits 13:12  HPL fine
bits 15:14  HPR fine
```

The live Gemian boot calls `Auddrv_Read_Efuse_HPOffset` and later uses the
trim buffer, so this is the active stock path.

Mainline `mt6351.c` already knows `MT6351_AUDDEC_ANA_CON2` but never reads or
writes these fields. Closing this gap requires a reviewed PMIC efuse read
sequence: it is not safe to guess the efuse row/engine registers or to write
them without a bounded capture. The codec-side write is known; the PMIC-side
read is the remaining dependency.

## 3. Inputs

| Input | Codec path | Bias | HAL path |
| --- | --- | --- | --- |
| Main/built-in mic | `AIN0 -> L PGA -> L ADC` | `MICBIAS0`, 1.9 V | `builtin_Mic_Mic1` |
| Headset mic | `AIN1 -> L PGA` | `MICBIAS1`, high power | `headset_mic_input` |
| Back/reference mic | `AIN2 -> R PGA -> R ADC` | `MICBIAS2`, 1.9 V | `builtin_Mic_Mic2` / `BackMic` |
| DMIC | voice-wake code only | — | not a normal capture path |

The vendor `TurnOnADcPowerACC()` routes the analog inputs with ACC coupling and
a default PGA gain of 18 dB:

```text
main:    MICBIAS0 1.9 V, AIN0 -> L PGA -> L ADC
headset: MICBIAS1 high power, AIN1 -> L PGA
ref:     MICBIAS2 1.9 V, AIN2 -> R PGA -> R ADC
```

The stock HAL selects the capture source with `Audio_MicSource1_Setting`
(`ADC1`, `ADC2`, `ADC3`) and `Audio_Preamp1/2_Switch`
(`IN_ADC1`, `IN_ADC2`, `IN_ADC3`). Its named paths are:

```text
builtin_Mic_Mic1        ADC1, both ADCs, preamps IN_ADC1
builtin_Mic_Mic2        ADC1, preamps IN_ADC3
builtin_Mic_BackMic     ADC1, preamps IN_ADC3
builtin_Mic_SingleMic   ADC1, preamp1 IN_ADC1
builtin_Mic_DualMic     ADC1, preamp1 IN_ADC1, preamp2 IN_ADC3
headset_mic_input       ADC2, preamps IN_ADC2
```

The policy configuration also exposes `Built-In Back Mic`, `Wired Headset
Mic`, `BT SCO Headset Mic`, `AUX Digital In`, `FM Tuner In` and `Voice Call
In`. The last four are separate transports, not MT6351 analog inputs.

The mainline `mt6351.c` has the same mux topology (`PGA L` AIN0/1/2, `PGA R`
AIN0/3/2, ADC L/R muxes, Mic Bias 0/1/2) and programs Mic Bias 0/2 VREF code
2 and Mic Bias 1 VREF code 7. It has no board route or Gemini capture DAPM
path.

The back/reference microphone is supported by Planet's **dual-microphone /
integrated ambient microphone** specification and by the user guide's
"microphone at both ends" statement. The vendor HAL enables ADC2 and the
codec configures AIN2, which matches. A direct BOM line item is still not
captured, and the stock policy does not attach `Built-In Back Mic` as a
primary capture device.

## 4. Headset jack, mic and buttons

Jack detection is entirely inside the **MT6351 ACCDET** block. The AP GPIO
path is compiled out (`CONFIG_ACCDET_EINT_IRQ=y`), so GPIO92/EINT15 is not the
jack line in this build. ACCDET uses:

- MT6351 interrupts 12 (`ACCDET`) and 13 (`ACCDET_EINT`);
- `MICBIAS1` for the headset microphone;
- AUXADC channel 5 for the three headset buttons;
- a `switch` class device, not an ALSA jack.

The vendor debounces plug-in at 256 ms and plug-out at 1 ms, leaves MICBIAS1
on for 6 s after an event, and maps button thresholds at 0/80/220/400 mV to
`KEY_PLAYPAUSE`, `KEY_VOLUMEUP` and `KEY_VOLUMEDOWN`. The live Gemian `dmesg`
confirms the configured values (`mid-Key=80`, `up=220`, `down=400`,
`pwm_width=500`, `pwm_thresh=500`, efuse `0xffffff80`, offset `-2`); these are
configured values, not an acoustic calibration. The live PMIC interrupt
snapshot showed ACCDET sources 12-14 at count 0, so no live jack event was
captured.

Two board GPIOs remain associated with the headset path:

- **GPIO234 `headphone_en`**: driven high with the DCC-mode microphone ADC
  path, not with playback.
- **GPIO235 `headphone_cs`**: a world-writable `/proc/headphone_cs` manual
  knob; no HAL or kernel audio path uses it.

GPIO234's DCC-mic function is confirmed. GPIO235's electrical target is not,
but it has no audio-path consumer, so mainline can leave it unclaimed.
GPIO234/235 are also SPI1 alternate pads, so SPI1 and this use are mutually
exclusive. The codec style differs from the surrounding MediaTek code, so
they are board-vendor additions.

## 5. Mainline status

Present in current mainline:

- MT6797 AFE platform, memif and DAI drivers;
- MT6351 codec driver with the analog output/input DAPM topology;
- `mt6797-mt6351` machine driver with playback/capture, hostless and `PCM
  1`/`PCM 2` links;
- MAX98926 codec driver;
- AW8736 one-wire pulse sequencing, reusing `aw8738.c` with an
  `awinic,aw8736` compatible (proposal `0395`): `awinic,mode = <3>` gives
  three pulses and the driver waits the datasheet's 40 ms start-up;
- minimal Gemini card preparation (proposals `0396`-`0401`): MT6351 regmap
  fallback through the PWRAP grandparent, `mt6351-sound` MFD child, AFE
  enable, the `mediatek,mt6797-mt6351-sound` card node, headphone/main
  mic/headset mic/back mic DAPM routes, two AW8736FCR speaker amplifiers
  with HPL/HPR → amp → speaker routes, and default GPIO pinmux states for
  the two amplifier mode lines;
- high-rate ADDA preparation (proposals `0403`/`0404`): keep the hires
  `NEWIF_CFG2` divider, switch `top_mux_audio` to `top_sys_pll3_d4` at
  96 kHz and above, and power the ADC hires gate.

Missing or board-specific:

- MT6351 MFD parent/cell in current upstream; local patches 0008/0010 add it;
- a BOM line item for the two AW8736FCR amplifiers (by ear, each channel reaches its own speaker);
- headset classification and buttons on the MT6351 ACCDET (plug detection is done); see the
  [MT6351 ACCDET contract and driver plan](mt6351-accdet.md);
- headphone offset trim;
- MT6797 I2S DAI for a MAX98926 path;
- pinctrl for the unused AUD/VOW/ANC pads, GPIO234 and GPIO235, which the
  Gemini path does not need (left at the boot state).

The first safe mainline card is the AFE + MT6351 codec +
`mt6797-mt6351` machine link with **headphone output, microphone capture and
the two-amplifier speaker path**, all PGA gains at minimum. Proposals
`0396`-`0401` prepare that card; `0403`/`0404` prepare the high-rate path.
The build profile `mt6797-a53-audio-card-compile` compiled the series and the
composed DTB contains the card, codec child, both amplifiers and the 243/244
pinmux states (commit `9cf7001f`). It has not been booted or probed. The first
validation target is 48 kHz; headset-jack and physical amplifier confirmation
remain.

That candidate could not bind its card and cannot run on the station. Proposals
`0407`-`0409` bind the amplifiers and give the station an AUDIO domain, and the
station carries the audio stack as unloaded modules. See
[first audio on the station](../../experiments/2026-11-01-gemini-audio-station/README.md).
With `0411` as well, a 48 kHz tone is heard in both headphone ears and from the
matching left and right speakers, and capture from AIN0 and AIN2 follows a tone
and speech. With `0415`-`0417`, the `Headphone Jack` control follows plug and
unplug. Microphone placement, headset classification, the buttons and trim remain open.

## 6. Offline review results

| Open point | Offline result |
| --- | --- |
| Speaker amplifier family | Resolved to **AW8736FCR** (FC-16): the vendor `AW8736_MODE*` table matches the AW8736 datasheet and the code selects mode 3, 0.8 W NCN. Planet lists stereo speakers and the code drives two independent mode lines, consistent with two mono parts; an exact BOM line item remains a visual check. |
| MAX98926 node | The stock machine driver logs `max98926L is not find`; `OpenSpeakerPath` never selects the I2C node. The node is not part of the stock path. |
| Earpiece / two-in-one | `OpenReceiverPath` checks `persist.af.feature.2in1spk`; no Gemini config sets it, so the stock path is `receiver_output`, not the two-in-one speaker route. Planet's user guide says there is a handset speaker at each end, so the RCV/HS path has a physical load. |
| Back/reference mic | Planet's specification lists dual/integrated ambient microphones and the user guide puts a mic at both ends. The HAL has a `Built-In Back Mic` port and `builtin_Mic_BackMic` route, but the policy's `attachedDevices` does not attach it as a primary device. |
| GPIO234 `headphone_en` | Confirmed DCC microphone-path enable; not a playback control. |
| GPIO235 `headphone_cs` | Only exposed as a world-writable `/proc/headphone_cs` manual knob; no HAL or kernel audio path uses it. Leave it unclaimed in mainline. |
| ACCDET thresholds | Live Gemian `dmesg` confirms `mid-Key=80`, `up=220`, `down=400`, `pwm_width=500`, `pwm_thresh=500`, `efusevalue=0xffffff80`, offset `-2`. These are configured values, not an acoustic calibration. |
| Headphone trim | Live Gemian `dmesg` records `Audio_Hpl_Offset_Get` and `GetAudioTrimOffset channels = 1`; the stock path applies trim, mainline does not. |
| Audio pinctrl | Only GPIO243/244 need a mainline pinmux: they are the vendor "hpdepop" pads and the AW8736 mode lines. The Gemini DTS comments out every AUD/VOW/ANC pinmux and the stock only requests them for VOW. GPIO234 is DCC-only, GPIO235 a debug knob. |
| High-rate clocking | The ADDA path uses `clk26m` up to 48 kHz and `top_sys_pll3_d4` at >= 96 kHz; the APLLs serve HDMI/I2S only. Mainline clobbered the hires `NEWIF_CFG2` divider and never powered the ADC hires gate; `0403`/`0404` correct both. |

## 7. Still open

1. Is each speaker behind its own AW8736FCR? On station 29 the left channel
   reaches only the left speaker and the right only the right, with GPIO243/244
   switching together. Two parts is the consistent reading; the BOM line item
   is still a visual check.
2. Is the MAX98926-compatible I2C0 `0x31` node populated at all? It is not
   used by the stock speaker path.
3. Which transducer is on the MT6351 RCV/HS driver, and is it one of the two
   stereo speakers or a separate handset speaker? Public specs confirm a
   handset speaker at each end; the wiring split is a schematic question.
4. Which physical microphone is AIN2 (reference/back) and which end is AIN0?
   Public specs confirm dual microphones; the mapping is a schematic question.
5. Is the headphone efuse offset trim needed for acceptable DC offset on
   mainline, or only for the stock path?
6. Does the live DTB's audio section differ from the public board DTS beyond
   the `speaker_amp@31` node?
7. Are the configured ACCDET thresholds and debounce correct for the actual
   Gemini headset, beyond matching the live dmesg values?

The ordered first-boot checks for all of these are in the
[audio RE runtime sequence](../../experiments/2026-10-04-gemini-audio-re/README.md#first-runtime-sequence).

## 8. Evidence

- [Gemini audio RE](../../experiments/2026-10-04-gemini-audio-re/README.md) —
  full vendor line citations, F1-F16, and the ranked hypotheses.
- [Audio AFE recovery](../../experiments/2026-07-12-audio-afe-recovery/README.md)
  and [runtime summary](../../experiments/2026-07-12-audio-afe-recovery/results/runtime-summary.txt)
  — live card, 31 PCM devices and AFE identity.
- [MT6797 audio upstream architecture](../../experiments/2026-09-07-mt6797-audio-upstream-architecture/README.md)
  — AFE binding, clock and dependency map.
- Vendor `mt_soc_codec_63xx.c`, `mt_soc_machine.c`, `AudDrv_Gpio.c`,
  `accdet.c`, `max98926.c`; HAL `audio_device.xml`,
  `audio_policy_configuration.xml` and `audio.primary.mt6797.so`
  (`OpenSpeakerPath` disassembly); retained Gemian `dmesg` for
  `max98926L is not find` and `Audio_Hpl_Offset_Get`.
- [AWINIC AW8736FCR product page](https://www.awinic.com/en/productDetail/AW8736FCR)
  and the AW8736 datasheet mode table (1.2/1.0/0.8 W NCN, mode 4 NCN off).
- Proposal `0395` (`sound/soc/codecs/aw8738.c`, binding and Kconfig).
- Proposals `0396` (`mt6351.c` regmap fallback), `0397` (minimal Gemini
  audio card and AFE enable), `0398` (headphone/microphone card routes) and
  `0399` (two AW8736FCR speaker amplifiers and routes).
- Mainline `mt6797-afe-pcm.c`, `mt6351.c`, `mt6797-mt6351.c`,
  `max98926.c`.
