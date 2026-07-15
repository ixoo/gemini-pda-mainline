# MT6797 audio mainline design

Status: `inconclusive` for runtime audio; the AFE, codec, and machine-card
contracts are source-audited and the live ALSA topology is captured. No PCM
stream, mixer write, PMIC codec register, jack event, or speaker/amplifier
test was performed.

## Reproducible evidence

Run the source-only analyzer in the development VM:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-audio-afe-recovery/scripts/analyze-mt6797-audio-contract.sh
```

The analyzer reads vendor files from Git objects, prints source hashes and
selected DT/driver anchors, and never opens ALSA or writes hardware.

Vendor evidence is Planet's MT6797 tree at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. Linux evidence is the prepared
`7.1.3` source in the VM.

| Source | SHA-256 |
| --- | --- |
| Vendor `mt_soc_audio_6797/AudDrv_Afe.c` | `21d64fd62250a6778f583886fad30f757be495b2335f2894e716f1658095dc08` |
| Vendor `mt_soc_audio_6797/mt_soc_afe_control.c` | `d550c28bb71a5024953e4ef42af4a0b0646e2512fbbec341f5cbf12d5192b94e` |
| Vendor `mt_soc_audio_6797/mt_soc_afe_connection.c` | `1c63ab9e969028d5cce761d931ca7c2337df01f40dec63e10e919056f74271cd` |
| Vendor `codec/mt6351/mt_soc_codec_6351.c` | `40817e56e34a2a1aed5d722b353b32830e4ba061ee34412f70a65d40b721edd7` |
| Vendor `codec/mt6351/mt_soc_codec_speaker_6351.c` | `8556e788f06a9b1f7451b7259045e618349a321b97cc652cd5a47511eb4bfa41` |
| Vendor `mt_soc_audio_6797/mt_soc_codec_63xx.c` | `5006c9ba0f93b5e712c30bf8ebb6394f2db0ff75e9dccfe78696496d5329205a` |
| Vendor `arch/arm64/boot/dts/mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |
| Vendor `arch/arm64/boot/dts/aeon6797_6m_n.dts` | `d1bd9d83941dffb44615f69e9113c7b79d87b3e9e87057619c70370f56456f5a` |
| Linux `mt6797-afe-pcm.c` | `ed52674d150c7d49bcaace00b6742390ba37de89a96a1720bf2df62674169f84` |
| Linux `mt6797-afe-clk.c` | `0d1ec1ae44312c6eab43d7c0835307f6f3e9d622abe9ab79e1bb074b775438a0` |
| Linux `mt6797-mt6351.c` | `61e3007631fdc0904d6725718e7afe71932de5bc697bdbc71583d8083f9bd179` |
| Linux `sound/soc/codecs/mt6351.c` | `b6e3dd7764e0b405fe8293993ffb2a5ac8cbe3f75010ed08eec31add0b797d32` |
| Linux `drivers/mfd/mt6397-core.c` | `a2c9d6ac7f5c884b7d47c5be69e485d12c2e730f050974223c3b1be9601a07d3` |
| Linux `mt6797-afe-pcm.txt` | `3ee4a94768158f942bd1faadc3a260cafb252f9a7a8d1010951df9614bcef062` |
| Linux `mt6797-mt6351.txt` | `2a4a8fcb3449d5701119ad203ffccf414b48b1a12d4fc05ab50aac06586719ad` |
| Linux `mt6351.txt` | `2da9f61e8b293b822804555fd97f7878ef1ace6ecbf85930b0c33c050d67c57f` |

The live device exposes one vendor `mt-snd-card` with 31 PCM endpoints. That
list includes ordinary multimedia playback/capture, but also modem/Bluetooth
voice, FM I2S, TDM debug, headphone impedance, ANC, hostless, and routing
paths. Endpoint enumeration does not prove that any Gemini analog endpoint is
wired or safe.

## Vendor contract

The vendor DT has two distinct audio layers:

| Layer | Contract |
| --- | --- |
| `audiosys: audio@11220000` | `mediatek,audio`, `0x11220000 + 0x10000`, SPI 151, 28-clock provider |
| `audgpio: mt_soc_dl1_pcm@11220000` | vendor DL1 child, `0x11220000 + 0x1000`, SPI 151, 28 named clocks |
| codec pseudo-nodes | `mt_soc_codec_63xx`, dummy, routing, voice, FM, ANC, and hostless vendor components |

The vendor AFE source directly manipulates MT6797 AFE registers and clock/power
gates; its codec source combines MT6351 PMIC register access with vendor DAPM,
speaker, depop, headphone, and analog-routing policy. The vendor tree does not
provide a modern `mt6797-mt6351-sound` machine-card phandle graph for the
Gemini board.

The 28 vendor child clocks include AFE/DAC/ADC gates, APLL tuners, SCP audio
power, infrastructure 26 MHz/ANC clocks, audio muxes, PLL dividers, and APLL1/
APLL2 sources. They are a vendor component graph, not a reason to copy every
legacy child node into a mainline DT.

## Linux reuse boundary

Linux 7.1.3 already has the matching silicon drivers:

- `mt6797-afe-pcm.c` matches `mediatek,mt6797-audio`, maps the resource with
  `devm_platform_ioremap_resource()`, requests SPI 151, uses runtime PM, and
  registers the MT6797 memory-interface, PCM, ADDA, and hostless DAIs;
- `mt6797-afe-clk.c` requests seven named clocks and sets the audio mux parent
  to the 26 MHz clock during runtime resume;
- `mt6351.c` obtains the parent PMIC regmap and exposes the standard MT6351
  codec DAI/DAPM component; and
- `mt6797-mt6351.c` only needs `mediatek,platform` and
  `mediatek,audio-codec` phandles to create the machine card.

This is a strong silicon identity and register-protocol match. A new AFE or
codec silicon driver is not justified by the vendor pseudo-node differences.
The correct mainline work is board integration and, if needed, small fixes to
the existing clock/binding contract.

## Resource discrepancies to preserve explicitly

1. The vendor AFE parent maps `0x10000` bytes, while the Linux binding example
   and current disabled Gemini node map `0x1000`. Linux's regmap caps access at
   `AFE_MAX_REGISTER = 0x84c`, so the smaller resource covers the current
   driver. Keep the 64 KiB vendor aperture as documented evidence; do not
   enlarge an enabled node without a register-access reason.
2. The Linux binding requires eight clock names, including
   `mtkaif_26m_clk`. The MT6797 platform clock helper requests seven clocks for
   its runtime-resume sequence, while the ADDA DAPM graph declares
   `mtkaif_26m_clk` as a clock-supply widget and ASoC obtains it by widget name.
   The disabled node retains all eight; this platform/DAPM split is intentional
   and must remain explicit if the binding is converted to YAML.
3. The MT6351 MFD core's `mt6351_devs` table includes an `mt6351-sound` cell
   and calls `devm_mfd_add_devices()` for the matched PMIC. In the current
   Linux MFD core, an exact matching child with `status = "disabled"` suppresses
   that cell; an absent child still leaves a name-matched `mt6351-sound`
   platform device. Treat codec config and MFD child side effects as part of
   the enablement review, and keep the board graph disabled until they are
   understood.

## Mainline implementation order

1. Keep the existing disabled AFE resource node and preserve the eight-clock
   binding: seven platform-resume clocks plus the ADDA DAPM clock supply.
2. Confirm the MT6351 MFD/regmap and PMIC IRQ behavior under the mainline
   Gemini DT without enabling the audio codec driver.
3. Recover board-level analog wiring: speaker/earpiece, microphones, headset
   detect, external amplifier, GPIOs, and regulator supplies. The live vendor
   endpoint list is not enough.
4. Add a disabled-only `mt6797-mt6351-sound` graph only when both phandles and
   the codec probe side effects are understood. Keep modem, Bluetooth, FM,
   ANC, and hostless routes out of the first board card.
5. Run a bounded low-volume playback test and a separate capture test with an
   external recovery path. Do not test modem/Bluetooth voice through the
   ordinary card.

The evidence supports reuse of Linux AFE/codec/machine drivers, not a new
audio silicon driver. The local patch series therefore retains only the
disabled AFE boundary and does not claim working audio.
