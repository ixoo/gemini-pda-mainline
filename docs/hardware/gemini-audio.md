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
mode table and package match the vendor code. The populated BOM still needs
physical confirmation.

The pulse timing matches the datasheet (`TH`/`TL` 0.75-10 µs; the code uses
2 µs). The vendor then waits 25 ms before audio, while the AW8736 datasheet
lists a 40 ms start-up time; mainline should use at least the datasheet value
or measure the actual turn-on.

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
- minimal Gemini card preparation (proposals `0396`/`0398`): MT6351 regmap
  fallback through the PWRAP grandparent, `mt6351-sound` MFD child, AFE
  enable, the `mediatek,mt6797-mt6351-sound` card node, and headphone/main
  mic/headset mic/back mic DAPM widgets and routes.

Missing or board-specific:

- MT6351 MFD parent/cell in current upstream; local patches 0008/0010 add it;
- speaker amplifier DT node and its card route;
- MT6351 ACCDET driver (only MT6359 ACCDET exists);
- headphone offset trim;
- MT6797 I2S DAI for a MAX98926 path;
- any Gemini microphone, jack or amplifier pinctrl state.

The first safe mainline card is the AFE + MT6351 codec +
`mt6797-mt6351` machine link with **headphone output and microphone capture**,
all PGA gains at minimum and the amplifier GPIOs left as the loader left
them. Proposals `0396`-`0398` prepare that card; they have not been built or
run. Speaker, headset-jack and amplifier work still need board routes and
evidence.

## 6. Offline review results

| Open point | Offline result |
| --- | --- |
| Speaker amplifier family | Resolved to **AW8736FCR** (FC-16): the vendor `AW8736_MODE*` table matches the AW8736 datasheet and the code selects mode 3, 0.8 W NCN. Physical BOM confirmation remains. |
| MAX98926 node | The stock machine driver logs `max98926L is not find`; `OpenSpeakerPath` never selects the I2C node. The node is not part of the stock path. |
| Earpiece / two-in-one | `OpenReceiverPath` checks `persist.af.feature.2in1spk`; no Gemini config sets it, so the stock path is `receiver_output`, not the two-in-one speaker route. Physical earpiece population is still not proven. |
| Back/reference mic | The HAL has a `Built-In Back Mic` port and `builtin_Mic_BackMic` route, but the policy's `attachedDevices` does not include it and no board evidence proves a second capsule. |
| GPIO234 `headphone_en` | Confirmed DCC microphone-path enable; not a playback control. |
| GPIO235 `headphone_cs` | Only exposed as a world-writable `/proc/headphone_cs` manual knob; no HAL or kernel audio path uses it. Leave it unclaimed in mainline. |
| ACCDET thresholds | Live Gemian `dmesg` confirms `mid-Key=80`, `up=220`, `down=400`, `pwm_width=500`, `pwm_thresh=500`, `efusevalue=0xffffff80`, offset `-2`. These are configured values, not an acoustic calibration. |
| Headphone trim | Live Gemian `dmesg` records `Audio_Hpl_Offset_Get` and `GetAudioTrimOffset channels = 1`; the stock path applies trim, mainline does not. |

## 7. Still open

1. Does the Gemini BOM actually populate one or two AW8736FCR amplifiers
   behind GPIO243/244? The code and datasheet identify the part; physical
   population is still unconfirmed.
2. Is the MAX98926-compatible I2C0 `0x31` node populated at all? It is not
   used by the stock speaker path.
3. Is the earpiece/RCV driver physically populated?
4. Is the back/reference microphone populated?
5. Is the headphone efuse offset trim needed for acceptable DC offset on
   mainline, or only for the stock path?
6. Does the live DTB's audio section differ from the public board DTS beyond
   the `speaker_amp@31` node?
7. Are the configured ACCDET thresholds and debounce correct for the actual
   Gemini headset, beyond matching the live dmesg values?

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
  audio card and AFE enable) and `0398` (headphone/microphone card routes).
- Mainline `mt6797-afe-pcm.c`, `mt6351.c`, `mt6797-mt6351.c`,
  `max98926.c`.
