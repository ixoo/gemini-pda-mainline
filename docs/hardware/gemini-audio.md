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

The vendor `AudDrv_GPIO_Request()` switches MOSI/MISO between GPIO and audio
function on each stream open/close. Mainline has the same pinctrl functions
but neither the AFE nor the MT6351 codec driver touches pinctrl, so a board DT
must hold these pads in their audio function statically.

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
and **GPIO244** and wait 25 ms. The pulse-count protocol matches the
AW87xx/AW8736 analog amplifier family, but no public source records which part
is populated.

The MT6351 LOL path remains a codec capability and the `speaker_output` HAL
path exists, but the stock speaker alias does not select it. It may be unused
on this board or reserved for another route.

The RCV/earpiece driver exists in the codec and the stock HAL exposes an
Earpiece port. Whether the Gemini physically fits an earpiece speaker, rather
than routing that port only for voice calls, is not separately recorded.

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

Whether the back/reference microphone is populated is **unresolved**. The
vendor HAL enables ADC2 and the vendor codec configures AIN2, but no retained
board measurement proves a second microphone is fitted.

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
`KEY_PLAYPAUSE`, `KEY_VOLUMEUP` and `KEY_VOLUMEDOWN`. Those are MediaTek
reference defaults, not Gemini measurements. The live PMIC interrupt snapshot
showed ACCDET sources 12-14 at count 0, so no live jack event was captured.

Two board GPIOs remain associated with the headset path:

- **GPIO234 `headphone_en`**: driven high with the DCC-mode microphone ADC
  path, not with playback.
- **GPIO235 `headphone_cs`**: a world-writable `/proc/headphone_cs` knob.

Their electrical target is not recorded. GPIO234/235 are also SPI1 alternate
pads, so SPI1 and this use are mutually exclusive. The codec style differs
from the surrounding MediaTek code, so they are board-vendor additions.

## 5. Mainline status

Present in current mainline:

- MT6797 AFE platform, memif and DAI drivers;
- MT6351 codec driver with the analog output/input DAPM topology;
- `mt6797-mt6351` machine driver with playback/capture, hostless and `PCM
  1`/`PCM 2` links;
- MAX98926 codec driver.

Missing or board-specific:

- MT6351 MFD parent/cell in current upstream; local patches 0008/0010 add it;
- Gemini sound-card node and DAPM routes;
- speaker amplifier node and enable sequence;
- MT6351 ACCDET driver (only MT6359 ACCDET exists);
- headphone offset trim;
- MT6797 I2S DAI for a MAX98926 path;
- any Gemini microphone, jack or amplifier pinctrl state.

The first safe mainline card is therefore the AFE + MT6351 codec +
`mt6797-mt6351` machine link with **headphone output only**, all PGA gains at
minimum and the amplifier GPIOs left as the loader left them. Speaker,
headset-mic and jack work need board evidence first.

## 6. Unresolved questions

1. Which AW87xx/AW8736-class part sits behind GPIO243/244, and is the
   MAX98926-compatible I2C0 `0x31` node populated but unused?
2. Is the earpiece/RCV driver physically populated?
3. Is the back/reference microphone populated?
4. What is GPIO235's electrical target? GPIO234 is confirmed as the DCC
   microphone-path enable, not a playback control.
5. What are the measured ACCDET button thresholds and plug debounce on the
   Gemini, rather than the MediaTek reference values?
6. Does the live DTB's audio section differ from the public board DTS beyond
   the `speaker_amp@31` node?
7. Is the headphone efuse offset trim needed for acceptable DC offset on
   mainline?

## 7. Evidence

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
- Mainline `mt6797-afe-pcm.c`, `mt6351.c`, `mt6797-mt6351.c`,
  `max98926.c`.
