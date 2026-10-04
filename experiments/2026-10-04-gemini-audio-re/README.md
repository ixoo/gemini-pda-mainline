# Experiment: Gemini audio path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-audio-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | MT6797 AFE, MT6351 audio codec, speaker amplifier, headphone jack and ACCDET, microphones, vendor ASoC machine card |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, MT6351 E2) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do to play and record audio on the
Gemini, which board parts sit between the MT6351 codec and the speakers,
headphone jack and microphones, and what does that imply for a mainline
description? The roadmap's
[audio step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps) listed
two unknowns: the speaker amplifier at I2C0 `0x31` and the jack-detection
wiring. This record answers what the public vendor source can answer, separates
verified facts from hypotheses, and ranks the hypotheses by how they should be
tested. It changes no patch, profile, candidate or device state.

Earlier records own the live observations this builds on: the
[audio AFE recovery](../2026-07-12-audio-afe-recovery/README.md) (live card
and PCM inventory, AFE node, mainline reuse boundary), the
[audio architecture refresh](../2026-09-07-mt6797-audio-upstream-architecture/README.md)
(AFE binding topic), the [PMIC recovery](../2026-07-11-mt6351-pmic-recovery/README.md)
(MT6351 E2, EINT176, interrupt snapshot) and the
[Gemian baseline](../../docs/hardware/gemini-gemian-baseline.md) (live I2C
inventory). PMIC basics (MFD, IRQ domain, regulators) are being handled in
another investigation and are only referenced here.

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the
[charging record](../2026-10-04-gemini-charging-re/README.md) used. Every
mainline citation is Linux `7.1.3` as pinned in `kernel/manifest.json`. Exact
URLs, sizes and SHA-256 values are in [`source-inputs.json`](source-inputs.json).
Line numbers refer to those exact revisions. No vendor source, firmware or
private capture is copied into this repository; register addresses, bit
values, GPIO numbers and configuration values are cited as facts.

The same caveat as the charging record applies: the public board DTS
(`aeon6797_6m_n.dts`) does not describe the live Gemian DTB in at least the
I2C0 speaker-amplifier node (F7). Where the public DTS and the live capture
disagree, the live capture wins.

## Part 1: verified facts

### Build selection and the vendor card

- **F1. The stock kernel builds the "old architecture" MT6797 ASoC stack with
  no PMIC speaker amplifier and no smart amplifier driver.**
  `CONFIG_SND_SOC=y`, `CONFIG_MT_SND_SOC_6797=y`, `CONFIG_MTK_BTCVSD_ALSA=y`,
  `# CONFIG_SND_SOC_MAX98926 is not set`, and no
  `CONFIG_MTK_SND_SOC_NEW_ARCH`, `CONFIG_MT_SND_SOC_CODEC` or
  `CONFIG_MTK_SPEAKER`
  ([`aeon6797_6m_n_defconfig` lines 399–419](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L399-L419)).
  Without `MTK_SND_SOC_NEW_ARCH` the top-level Makefile takes the old branch
  and builds only `mt_soc_audio_6797/`
  ([`sound/soc/mediatek/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/Makefile)),
  whose object list carries the AFE, clock, GPIO, PCM, machine and
  `mt_soc_codec_63xx.o` objects and gates `mt_soc_codec_speaker_63xx.o` on
  the unset `MTK_SPEAKER`
  ([`mt_soc_audio_6797/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/Makefile)).
  The codec in use is therefore
  `mt_soc_audio_6797/mt_soc_codec_63xx.c` (compatible
  `mediatek,mt_soc_codec_63xx`, [lines 5635–5636](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c#L5635-L5636)),
  not the newer `codec/mt6351/` tree that the July record hashed. The MT6351
  register header contains no `SPK_CON`/`SPK_ANA_CON` block at all, so the
  "class D / class AB" speaker controls in the codec source are dead code on
  this PMIC.
- **F2. The live card is the vendor's 31-link `mt-snd-card`, and the live
  kernel did not add the external-speaker links.** `mt_soc_dai_common[]` has
  exactly 31 DAI links
  ([`mt_soc_machine.c` lines 1001–1256](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_machine.c#L1001-L1256))
  and the card is named `mt-snd-card` (line 1332). The 2026-07-12 live
  capture saw 31 PCM device numbers on `mt-snd-card`
  ([runtime summary](../2026-07-12-audio-afe-recovery/results/runtime-summary.txt)).
  Two more links, `ext_Speaker_Multimedia` (codec DAI `max98926-aif1`, codec
  `MAX98926_MT`) and `I2S1_AWB_CAPTURE`, are appended only when a node with
  compatible `maxim,max98926L` exists
  ([lines 1257–1276, 1352–1360](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_machine.c#L1352-L1360)).
  31 observed links means that lookup failed on the live board; see F7.

### AFE, clocks and codec pads

- **F3. Vendor AFE and clock contract (unchanged from the July record,
  restated with line anchors).** `audiosys: audio@11220000` is
  `mediatek,audio`, 64 KiB, SPI 151 level-low, one-cell clock provider; the
  DL1 child lists 30 clocks and the driver table names 30
  ([`mt6797.dtsi` lines 2712–2784](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2712-L2784),
  [`AudDrv_Clk.c` lines 110–184](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/AudDrv_Clk.c#L110-L184)).
  The vendor reparents `top_mux_audio` between `syspll3_d4` and `clk26m`
  (lines 382–413) and `top_mux_audio_int` between `syspll1_d4` and `clk26m`
  (lines 310–341); APLL1/APLL2, their tuners and the hi-res ADC clocks exist
  only for I2S and >48 kHz paths. Mainline `mt6797-afe-clk.c` requests seven
  clocks and pins `top_mux_audio` to `clk26m`
  ([lines 24–31, 83–84](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-afe-clk.c#L24-L31)),
  and the ADDA DAI adds the `mtkaif_26m_clk` DAPM supply
  ([`mt6797-dai-adda.c` lines 104–115, 142–147](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-dai-adda.c#L104-L115)).
  The vendor codec node carries two board knobs, `use_hp_depop_flow = <0>`
  and `use_ul_260k = <1>`
  ([`mt6797.dtsi` lines 2877–2881](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2877-L2881)).
- **F4. The codec digital interface uses five dedicated MT6797 pads, switched
  per direction.** `AUD_CLK_MOSI` (GPIO146, pin state commented out),
  `AUD_DAT_MISO` GPIO147, `AUD_DAT_MOSI` GPIO148, `VOW_CLK_MISO` GPIO149 and
  `ANC_DAT_MOSI` GPIO150
  ([`aeon6797_6m_n.dts` lines 843–1008](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L843-L1008)).
  `AudDrv_GPIO_Request()` switches MOSI for downlink and MISO for uplink
  between GPIO and audio function on every stream open/close
  ([`AudDrv_Gpio.c` lines 304–328](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/AudDrv_Gpio.c#L304-L328)),
  called from the AFE ADDA enable paths
  ([`mt_soc_afe_control.c` lines 1757, 2300](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_afe_control.c#L1757)).
  Mainline's MT6797 pinctrl data has the same functions (`AUD_CLK_MOSI`,
  `AUD_DAT_MISO`, `AUD_DAT_MOSI`, `VOW_CLK_MISO`, `ANC_DAT_MOSI` at
  [`pinctrl-mtk-mt6797.h` lines 1422–1453](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h#L1422-L1453)),
  but neither the mainline AFE nor the codec driver touches pinctrl: a
  mainline board DT must hold these pads in their audio function statically.
  Whether the retained loader leaves them there is not recorded.

### Codec outputs (what the PMIC can drive)

- **F5. The vendor codec drives four analog outputs from the MT6351 and
  nothing else is built: headphone L/R, the "HS" voice (earpiece) driver, the
  LOL line-out buffer used as the "Speaker" path, and headphone-as-loudspeaker.**
  - Headphone: `Audio_Amp_Change()` enables cap-less LDO and NV regulator
    (`AUDDEC_ANA_CON9` `0xA000`, `CON10` bit 8), IBIST, sets HP gain to −40 dB
    (`ZCD_CON2 0x0F9F`), de-OSC/STBENH (`CON1`), enables DAC and switches the
    HP mux to the DAC (`AUDDEC_ANA_CON0 0xE09F → 0xF4FF`)
    ([`mt_soc_codec_63xx.c` lines 1710–1852](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c#L1710-L1852)).
    HP offset trim comes from PMIC efuse words read at `0x0C18`
    (`Auddrv_Read_Efuse_HPOffset`, lines 610–690).
  - Earpiece: `Voice_Amp_Change()` enables the HS driver (`AUDDEC_ANA_CON0`
    `0xE089 → 0xE119`, `ZCD_CON3` gain), lines 1947–2030.
  - Speaker: `Speaker_Amp_Change()` enables **LOL**, the line-out left buffer
    (`AUDDEC_ANA_CON3 0x4228 → 0x4230 → 0x4234`, `ZCD_CON1` gain), lines
    2036–2105. With `MTK_SPEAKER` unset `Apply_Speaker_Gain()` only writes
    `ZCD_CON1` (lines 702–709). The "Speaker" kcontrols therefore mean
    "mono line-out to an external amplifier", not a PMIC amplifier.
  - Headphone as loudspeaker: `Headset_Speaker_Amp_Change()`, line 2388.
  - Kcontrols: `Audio_Amp_R/L_Switch`, `Voice_Amp_Switch`,
    `Speaker_Amp_Switch`, `Headset_Speaker_Amp_Switch`, the PGA gains,
    `Ext_Speaker_Amp_Switch`, `Receiver_Speaker_Switch`, `Audio HP Impedance`
    ([lines 3046–3079](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c#L3046-L3079)).
    DAPM is vestigial: three bare `EARPIECE`/`HEADSET`/`SPEAKER` outputs and
    one route (lines 5398–5413).
  - Register addresses used above (MT6351 header, `upmu_hw.h`):
    `AUDDEC_ANA_CON0 0x0CF2`, `CON3 0x0CF8`, `CON6 0x0CFE`, `CON9 0x0D04`,
    `CON10 0x0D06`, `AUDENC_ANA_CON0 0x0D08`, `CON1 0x0D0A`, `CON3 0x0D0E`,
    `CON9 0x0D1A`, `CON10 0x0D1C`, `CON11 0x0D1E`, `ZCD_CON1 0x0802`,
    `ZCD_CON2 0x0804`, `DRV_CON2 0x0230`, `TOP_CKPDN_CON2 0x0246`
    ([lines 70–81, 408–409, 760–782](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/upmu_hw.h#L760-L782)).

  Mainline `sound/soc/codecs/mt6351.c` exposes the same four analog ends as
  DAPM outputs `Receiver`, `Headphone L`, `Headphone R`, `LINEOUT L`
  ([lines 1187–1190](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/codecs/mt6351.c#L1187-L1190)),
  routes `DACL/DACR → HPL/HPR Mux → HPL/HPR Power`, `DACL → LOL Mux → LOL
  Buffer`, `DACL → RCV Mux → RCV Buffer` (lines 1383–1405) and offers the
  `LoudSPK Playback` HP mux setting (lines 423, 1389–1390). Its HP power-up
  sequence mirrors the vendor's register order (lines 725–780). It has no
  efuse trim read and no external-amplifier or jack widget.

### Speaker amplifier

- **F6. In the public source the external speaker amplifier is switched by a
  pulse-coded GPIO, not by I2C.** `Ext_Speaker_Amp_Switch` →
  `Ext_Speaker_Amp_Change()` calls `AudDrv_GPIO_EXTAMP_Select(true, 3)` and
  `AudDrv_GPIO_EXTAMP2_Select(true, 3)`, then waits 25 ms
  ([lines 2154–2215](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c#L2154-L2215)).
  Both helpers emit `mode` (default 3) low/high pulses of 2 µs each on the
  pinctrl states named `hpdepop-pullhigh`/`hpdepop-pulllow` and
  `hpdepop-pullhigh_e2`/`hpdepop-pulllow_e2`
  ([`AudDrv_Gpio.c` lines 442–528](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/AudDrv_Gpio.c#L442-L528));
  the dedicated `audextamp_*` and `audcvspk_*` states are commented out
  (lines 81–88, 127–134) and `AudDrv_GPIO_RCVSPK_Select()` is `#if 0`
  (lines 530–553). The board DTS maps those states to **GPIO243** and
  **GPIO244** as push-pull outputs
  ([`aeon6797_6m_n.dts` lines 924–954](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L924-L954)).
  Because `use_hp_depop_flow = <0>` (F3), `hasHpDepopHw()` is false and the
  same two GPIOs are never used for headphone de-pop
  (`HP_Switch_to_Ground/Release`, lines 919–933). A pulse-count enable with a
  three-pulse default is the mode-select protocol of the AW87xx/AW8736
  analog amplifier family; the source names that family in its own
  `MT6755_AW8736_REWORK` conditional (lines 85–88, 2161). Nothing in the public tree
  records which part is populated.
- **F7. The live Gemini DTB additionally declares an I2C0 `0x31` device named
  `speaker_amp`, which the public DTS lacks and no live driver binds.** The
  live client list shows `0-0031:speaker_amp/unbound`
  ([I2C reuse audit](../2026-07-14-upstream-mt6797-coverage-audit/results/i2c-mt6797-controller-reuse-20260714.txt),
  [baseline table](../../docs/hardware/gemini-gemian-baseline.md#live-i2c-inventory)),
  while the public `i2c0@11007000` holds only `bq24261@6b` and `mt6306@64`
  ([`aeon6797_6m_n.dts` lines 46–53](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L46-L53)).
  An OF-instantiated I2C client is named from the compatible's suffix, so
  the live compatible is `mediatek,speaker_amp`. Exactly one vendor driver
  matches that string: a MediaTek-adapted Maxim **MAX98926** driver,
  `sound/soc/codecs/max98926.c` (`of_match` `mediatek,speaker_amp`, I2C id
  `max98926L`, commented board info `max98926L` at `0x31`, DT properties
  `vmon-slot-no`/`imon-slot-no`;
  [lines 956–1061](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/codecs/max98926.c#L956-L1061)).
  Its Kconfig symbol `SND_SOC_MAX98926`
  ([`sound/soc/codecs/Kconfig` lines 820–824](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/codecs/Kconfig#L820-L824))
  is unset (F1), which is why the live client is unbound, and the machine
  driver looks for a different compatible (`maxim,max98926L`, F2), so even a
  built driver would not have been linked into the card. Consequence: the
  stock kernel never programs a MAX98926. Either the part is absent and the
  node is a reference-board leftover, or it is present and driven by
  something other than this kernel; H1/H2 decide.
- **F8. A MAX98926 would need an I2S feed that mainline MT6797 cannot
  provide today.** The vendor's digital-amplifier path is the `I2S0DL1OUTPUT`
  link (DL1 to I2S0 and the internal DAC at once;
  [`mt_soc_machine.c` lines 1068–1074](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_machine.c#L1068-L1074),
  `mt_soc_pcm_dl1_i2s0Dl1.c`). The public DTS comments out every smart-PA
  pin state (GPIO69/70/72/73 as `I2S0_LRCK/BCK/DI` and `I2S3_DO`, GPIO135/
  136/138 as TDM;
  [lines 855–922](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L855-L922)),
  and nothing in the 6797 audio directory calls `AudDrv_GPIO_SMARTPA_Select()`
  (only `AudDrv_GPIO_Request()` is used, F4). Mainline's MT6797 AFE
  registers only ADDA, PCM, hostless and memory-interface DAIs
  ([`mt6797-afe-pcm.c` lines 728–732](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-afe-pcm.c#L728-L732),
  [Makefile lines 4–9](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/Makefile#L4-L9));
  the I2S control registers are defined (`AFE_I2S_CON..CON3`,
  [`mt6797-reg.h` lines 17–30](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-reg.h#L17-L30))
  but no I2S DAI uses them. Mainline does have the Maxim driver
  (`maxim,max98926`, [`max98926.c` line 575](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/codecs/max98926.c#L575))
  and its binding ([`maxim,max98925.yaml` lines 13–45](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/sound/maxim,max98925.yaml#L13-L45)),
  and the MT8183 I2S DAI is the nearest template
  (`sound/soc/mediatek/mt8183/mt8183-dai-i2s.c`).

### Headphone jack and ACCDET

- **F9. Jack detection runs entirely inside the MT6351 ACCDET block with the
  PMIC's own EINT comparator; the AP GPIO path is compiled out.**
  `CONFIG_MTK_ACCDET=y` and `CONFIG_ACCDET_EINT_IRQ=y` (defconfig lines
  260–261); `ACCDET_EINT` (AP GPIO), pin swap, pin recognition, four-key and
  TS3A225E options are unset. The driver registers PMIC interrupt callbacks
  12 (`accdet_int_handler`) and 13 (`accdet_eint_int_handler`)
  ([`accdet.c` lines 1638–1639](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accdet/mt6797/accdet.c#L1638-L1639)),
  which are `MT6351_IRQ_ACCDET` and `MT6351_IRQ_ACCDET_EINT` (indices 12 and
  13, `MT6351_IRQ_ACCDET_NEGV` 14) in the local
  [patch 0010](../../patches/v7.1.3/0010-mfd-mt6397-add-MT6351-core-and-interrupt-support.patch)
  enumeration. The AP-EINT setup (`accdet_setup_eint`, lines 579–633) and the
  DTS state `accdet_pins_eint_as_int` on **GPIO92/EINT15**
  ([`aeon6797_6m_n.dts` lines 719–726](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L719-L726))
  are behind `#ifndef CONFIG_ACCDET_EINT_IRQ` (line 578), so GPIO92 is not a
  jack line in this build. The live PMIC interrupt snapshot showed sources
  12–14 at count 0
  ([PMIC recovery](../2026-07-11-mt6351-pmic-recovery/README.md)).
- **F10. ACCDET register map and sequence (MT6351).** `ACCDET_CON0..CON24`
  at `0x0F46..`, with `CTRL = CON1 (0x0F48)`, `IRQ_STS = CON12 (0x0F5E)`,
  `EINT_CTL = CON15 (0x0F64)`; clock gate `TOP_CKPDN_CON2` bit 9, reset
  `TOP_RST_CON0` bit 4; interrupt enables in `INT_CON0` bits 12/13/14
  ([`reg_accdet.h` lines 19–58, 84–128](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accdet/mt6797/reg_accdet.h#L19-L58),
  [`upmu_hw.h` lines 956–971](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/upmu_hw.h#L956-L971)).
  `accdet_init()` ungates and resets the block, programs PWM width/threshold,
  `STATE_SWCTRL = 0x07`, rise/fall delay, debounce 0/1/3/4, EINT polarity
  (default level-low, line 42), enables IRQ 12 and 13, then sets the analog
  side: `AUDENC_ANA_CON11 |= 0xF`, `AUDENC_ANA_CON10 |= (mic-vol << 4) | 0x80`
  (MICBIAS1 reference and enable), `ACCDET_CON0 = 0x0010`, and the
  internal ACCDET–EINT connection bit 11 of `AUDENC_ANA_CON11`
  ([lines 1204–1310](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accdet/mt6797/accdet.c#L1204-L1310)).
  Plug-in/out debounce is retuned on each EINT edge (256 ms in, 1 ms out;
  lines 518–577) and MICBIAS1 is left on for 6 s after an event
  (`MICBIAS_DISABLE_TIMER`, line 89). Headset mic bias is therefore
  **MICBIAS1** on the MT6351 (`ACCDET_MICBIAS_REG = AUDENC_ANA_CON10`).
- **F11. Button detection reads PMIC AUXADC channel 5 and reports three keys
  through an input device.** `Accdet_PMIC_IMM_GetOneChannelValue()` requests
  `AUXADC_RQST0` bit 5, polls `AUXADC_ADC5` (`0x0E0A`) for bit 15, takes the
  12-bit value at 1.8 V full scale and subtracts an efuse offset from OTP
  word 3 bits 5–12
  ([lines 238–250, 1194–1201](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accdet/mt6797/accdet.c#L238-L250)).
  Thresholds map to `KEY_PLAYPAUSE` (< mid), `KEY_VOLUMEUP`, `KEY_VOLUMEDOWN`
  (lines 646–701); the input device also declares `KEY_VOICECOMMAND`
  (lines 1611–1614). Jack state goes to a `switch` class device (Android
  `h2w` style), not to an ALSA jack.
- **F12. Board ACCDET parameters (public DTS, F7 caveat):** `accdet-mic-vol
  = 7`, `headset-mode-setting = <0x500 0x500 1 0x1F0 0x800 0x800 0x20>`
  (pwm width, pwm threshold, fall delay, rise delay, debounce0, debounce1,
  debounce3), `accdet-plugout-debounce = 1`, `accdet-mic-mode = 1` (ACC),
  `headset-three-key-threshold = <0 80 220 400>` mV, four-key values
  present but unused
  ([`aeon6797_6m_n.dts` lines 702–717](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L702-L717),
  struct at [`accdet.h` lines 123–150](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accdet/mt6797/accdet.h#L123-L150)).
  These are MediaTek reference defaults, not Gemini measurements.
- **F13. Two further board GPIOs are tied to the headphone path by non-MediaTek
  code: GPIO234 `headphone_en` and GPIO235 `headphone_cs`.** Both are
  push-pull outputs with high/low states
  ([`aeon6797_6m_n.dts` lines 1010–1039](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1010-L1039);
  helpers at [`AudDrv_Gpio.c` lines 571–596](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/AudDrv_Gpio.c#L571-L596)).
  `headphone_en` is driven high when the DCC-mode ADC path powers on and low
  when it powers off
  ([`mt_soc_codec_63xx.c` lines 3493, 3762](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c#L3493)),
  that is, together with the **microphone**, not with playback.
  `headphone_cs` is only reachable from userspace through a world-writable
  `/proc/headphone_cs` (lines 5570–5617). The code style differs from the
  surrounding MediaTek code, so these are board-vendor additions. GPIO234–237
  are also the `SPI1_*_B` pads recorded in the
  [resource map](../../docs/hardware/mt6797-live-resource-map.md), so SPI1
  and this use are mutually exclusive on the Gemini. Their electrical target
  (an analog switch, a mic-line switch, a jack-side amplifier enable) is not
  recorded anywhere public.

### Microphones

- **F14. The vendor records from two analog inputs with ACC coupling: the
  "main mic" on AIN0 with MICBIAS0, the "headset mic" on AIN1 with MICBIAS1,
  and a "ref mic" on AIN2 with MICBIAS2.** `TurnOnADcPowerACC()` sets
  MICBIAS0 to 1.9 V (`AUDENC_ANA_CON9 0x0021` / mask `0x00f1`, VREF code 2),
  routes `AIN0 → L PGA → L ADC` (`AUDENC_ANA_CON0 0x0311`, `0x5311`), or for
  the headset powers MICBIAS1 in high-power mode (`AUDENC_ANA_CON10 0x0001`)
  and routes `AIN1 → L PGA` (`0x0221`, `0x5221`); the reference mic uses
  MICBIAS2 1.9 V (`AUDENC_ANA_CON9 0x2100`) and `AIN2 → R PGA → R ADC`
  (`AUDENC_ANA_CON1 0x0331`, `0x5331`); PGA default 18 dB
  ([lines 3140–3260](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c#L3140-L3260)).
  Mic modes default to ACC (lines 130–132); DMIC code exists only for the
  voice-wakeup path and the DTS has no DMIC pins. Whether the Gemini
  populates a second (reference) microphone is not recorded; the ADC2 path
  is enabled by the HAL, not by DT.
  Mainline `mt6351.c` has the identical mux topology (`PGA L Mux` AIN0/1/2,
  `PGA R Mux` AIN0/3/2, `ADC L/R Mux`, Mic Bias 0/1/2 supplies;
  [lines 1301–1334](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/codecs/mt6351.c#L1301-L1334))
  and programs Mic Bias 0/2 VREF code 2 and Mic Bias 1 VREF code 7
  (lines 982–1058), the latter equal to the ACCDET `accdet-mic-vol` (F12).

### Mainline 7.1.3 and this repository

- **F15. Mainline has the silicon drivers but none of the board pieces.**
  `mt6797-mt6351.c` needs `mediatek,platform` and `mediatek,audio-codec`
  phandles (lines 193–206) and creates Playback_1–3, Capture_1–3,
  Capture_Mono_1, two hostless links, `Primary Codec` (`ADDA` ↔
  `mt6351-snd-codec-aif1`) and `PCM 1`/`PCM 2`
  ([lines 13–171](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-mt6351.c#L13-L171));
  it declares no board DAPM widgets, routes, jack or amplifier. `mt6351.c`
  takes its regmap from the MFD parent (line 1465) and matches
  `mediatek,mt6351-sound` (line 1485). The only MediaTek jack driver is
  `mt6359-accdet.c`, which reads an `accdet` child of the PMIC node, takes
  three IRQs from the parent and uses MT6359 register names
  ([lines 556–666, 925–994](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/codecs/mt6359-accdet.c#L556-L666));
  there is no MT6351 ACCDET driver. Upstream `mediatek,mt6397.yaml` lists
  only `mt6358/mt6359/mt6397/mt6366` audio-codec children
  ([lines 110–126](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/mfd/mediatek,mt6397.yaml#L110-L126));
  local [patch 0008](../../patches/v7.1.3/0008-dt-bindings-mfd-mediatek-add-MT6351-PMIC.patch)
  adds `mediatek,mt6351-sound` there and
  [patch 0010](../../patches/v7.1.3/0010-mfd-mt6397-add-MT6351-core-and-interrupt-support.patch)
  adds the `mt6351-sound` MFD cell.
- **F16. The current Gemini build carries the modules but no graph.**
  `configs/gemini.fragment` selects `CONFIG_SND_SOC_MT6797=m` and
  `CONFIG_SND_SOC_MT6797_MT6351=m` (lines 74–77); patch 0045 adds the
  disabled `audio-controller@11220000`; the PMIC node from patch 0007 has no
  sound or accdet child; no I2C0 amplifier, no GPIO243/244/234/235 consumer,
  no audio pinctrl state and no sound card node exist in the Gemini DTS.

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.
Any playback test must start with every PGA at its minimum and the amplifier
off.

1. **H1. The Gemini speakers are driven by analog amplifier(s) fed from the
   MT6351 LOL line-out, enabled by pulse-coded GPIO243 and GPIO244, and the
   I2C0 `0x31` MAX98926 node is an unpopulated reference-board leftover
   (F5, F6, F7).** Two enable GPIOs with one mono source fit a stereo pair of
   AW87xx-class amplifiers. Test, in order: (a) Gemian read of
   `/sys/kernel/debug/gpio` or the pinctrl debug files for GPIO243/244
   direction and level while idle and while a short low-volume tone plays
   through the stock stack (one attended play; this is the single
   decision-changing measurement); (b) Gemian read `i2cdetect -y -r 0`
   restricted to address `0x31` (a quick-write probe is bounded and
   non-destructive for an unpowered or absent part; an ACK proves a device
   exists, no ACK with VIO on proves absence or a shut-down part); (c) only if
   (a) shows no GPIO activity, treat H2 as primary. Confidence: medium-high
   for the GPIO pulse path, medium for which part.
2. **H2. A MAX98926 is populated at I2C0 `0x31` and the stock Gemian speaker
   path is dead or userspace-driven (F7, F8).** If `i2cdetect` ACKs `0x31`,
   a Gemian read of register `0xFF` (MAX98926 revision ID; a one-byte read)
   through the vendor interface identifies the part. If so, stock Gemian
   would need an I2S0 feed and pins the public DTS does not route, and
   mainline would need an MT6797 I2S DAI (F8) before any speaker output;
   that is a larger project than H1. Confidence: low-medium.
3. **H3. A first mainline card can be built with only the parts that exist:
   AFE + MT6351 codec + `mt6797-mt6351` machine card, with the DAC routed to
   `Headphone L/R` for a bounded headphone test and `LINEOUT L` left muted
   (F5, F15, F16).** Prerequisites: the MT6351 MFD child `mediatek,mt6351-sound`
   (owned by the PMIC step), the five audio pads held in their audio function
   (F4), the AFE node enabled, and the fragment modules. Test: a mainline boot
   that probes the card, lists controls, and plays a −40 dB tone to
   headphones only with the amplifier GPIOs left as the loader left them;
   measure `/proc/asound` state and the PMIC `AUDDEC_ANA_CON0` readback.
   Confidence: high that the card registers; medium that the pads and clock
   parents are in a usable state without the vendor's APLL handling.
4. **H4. Microphone capture works on `AIN0` with Mic Bias 0 on mainline
   without board data (F14).** Test: in the H3 boot, select `PGA L Mux =
   AIN0`, `ADC L Mux = Left Preamplifier`, record 2 s at 48 kHz and check for
   non-silence; repeat with `AIN2`/Mic Bias 2 to learn whether a second mic is
   populated. Confidence: high for AIN0, unknown for AIN2.
5. **H5. The jack can be detected on mainline by a small MT6351 ACCDET driver
   using the existing MFD IRQ domain, modelled on `mt6359-accdet.c` with the
   MT6351 register map from F10 and the parameters from F12 (F9–F12).**
   Cheapest decision-changing test first: a Gemian read of
   `/proc/interrupts` counts for the ACCDET sources across one attended
   headset plug/unplug (sources 12/13 should increment), plus the resulting
   `switch` state and key events from `getevent`. That confirms the EINT
   polarity and that no AP GPIO is involved before any driver is written.
   Confidence: high for the mechanism, medium for the parameters (F7 caveat).
6. **H6. GPIO234 (`headphone_en`) and GPIO235 (`headphone_cs`) gate an analog
   switch on the headset microphone/line, not a headphone amplifier (F13).**
   The only kernel user drives GPIO234 with the ADC, and `headphone_cs` is a
   manual userspace knob. Test: in the H1 Gemian read, capture GPIO234/235
   levels while idle, while recording from the headset mic, and while playing
   to headphones; a level that follows capture confirms the hypothesis. If
   both stay constant, they can be left alone on mainline. Confidence: medium.
7. **H7. The live Gemian DTB's audio section differs from the public DTS
   beyond the `0x31` node, most likely in the smart-PA and ACCDET nodes
   (F7, F8, F12).** Test: one Gemian read of `/proc/device-tree` for
   `i2c0@11007000/speaker_amp@31` properties, the `audgpio` pinctrl names and
   the `accdet` node, under the usual identity checks. Settles which numbers
   in Part 1 carry the F7 caveat. Confidence: high that it differs.
8. **H8. Headphone offset trim from efuse is needed for acceptable DC offset
   on mainline (F5).** Mainline `mt6351.c` has no trim read. Test: measure
   the headphone DC offset in the H3 boot with a meter; defer until a headset
   test is admitted. Confidence: low priority.
9. **H9. Bluetooth voice (`BTCVSD`) and modem PCM paths are separate
   transports and stay out of the first card.** No test now; the mainline
   `PCM 1`/`PCM 2` DAIs exist for the modem link but have no consumer.

## Consequences for the roadmap (no changes applied here)

- The roadmap's two audio unknowns resolve as: the `0x31` device is, by the
  vendor's own driver and node name, a Maxim MAX98926 smart amplifier node
  that the stock kernel never binds or links, while the stock speaker path
  is the MT6351 LOL line-out plus a pulse-enabled GPIO243/GPIO244 amplifier
  pair; one attended Gemian read (H1) decides which is real. Jack detection
  is MT6351 ACCDET with the PMIC's internal EINT on `MT6351_IRQ_ACCDET`
  / `MT6351_IRQ_ACCDET_EINT`; no AP EINT is used.
- Audio depends on the PMIC step twice: the `mt6351-sound` child and regmap
  for the codec, and the MFD IRQ domain for ACCDET. Nothing here changes the
  After-Wi-Fi order.
- The first mainline sound card should be headphone-only with the amplifier
  GPIOs untouched; an external-amplifier widget (GPIO-enabled, as
  `simple-amplifier` or a card-level `SND_SOC_DAPM_SPK` with a GPIO event) or
  a MAX98926 node is added only after H1/H2.
- If H2 wins, the MT6797 I2S DAI becomes a prerequisite and should be scoped
  as its own upstream topic next to the AFE schema conversion.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks apply;
no kernel build, DT check or device action was performed. Line numbers were
taken from the exact fetched files recorded in `source-inputs.json`.
