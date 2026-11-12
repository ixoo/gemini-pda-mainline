# Experiment: compressed-audio offload on the MT6797 and its battery value

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-12-mt6797-audio-offload-re` |
| Status | `completed`: offline source and firmware review; no build, boot or device access. Playback-current measurement M1 proposed |
| Subsystem | audio: MT6797 AFE, SCP (CM4) companion core, vendor audio HAL; power |
| Device variant | named Gemini PDA (MT6797X), Gemian `3.18.41+` and the mainline station |
| Date(s) | 2026-11-12 |
| Investigator(s) | audio-offload RE session (owner-requested) |
| Tracking issue | none |

## Question or hypothesis

The owner wants the most battery life on the move and asked whether the
hardware can decode compressed audio so the application processor (AP) can
sleep. The custodian's prior answer was an inference: the vendor stack seems to
have an "offload" mode, probably music decode on a coprocessor.

Questions:

1. What is the vendor offload path: which processor decodes, which codecs,
   which firmware, which kernel and HAL interfaces, and how does the AP sleep?
2. What may the AP do while it runs?
3. What would a mainline path cost, against software decode with large buffers?
4. What should we do, with a rough battery estimate?

Falsifiable core claim tested here: *the stock Gemini uses SCP offload for
music.* It is rejected if the shipped kernel or SCP firmware lacks the
offload path.

## Provenance and environment

- Vendor kernel: public GPL tree at Gemian commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the
  [audio RE](../2026-10-04-gemini-audio-re/README.md) cites. Links below use
  `V/` for
  `https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/`.
- Live Gemian configuration: the decompressed `/proc/config.gz` retained by the
  [A72 owner observer](../2026-07-23-gemian-a72-owner-observer/README.md),
  [`inputs/active-gemian.config`](../2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config),
  SHA-256 `231d8a2f…35c18f4`.
- SCP firmware: the unit's retained private `scp1` partition image, SHA-256
  `3c65097eeeb4e2d29dd125752cfb648c6da5e3651eabc9dad1da672b2558cd66`. `scp2` has
  the same hash ([thermal firmware scan](../2026-10-31-mt6797-thermal-management/results/firmware-thermal-scan.tsv)).
- Vendor HAL: the retained private `vendor/lib64/hw/audio.primary.mt6797.so`
  from the July userspace extraction, SHA-256
  `d086eab26f9dbfa824e8136336ac785aaf2ba6b8848b6633516d9d62945aec0e`. Only
  string-level observations are recorded; nothing is copied.
- Mainline: Linux `7.1.3` as pinned in `kernel/manifest.json`.
- LK: public MT6797 LK source at `f4988d74`, as the [LK record](../../docs/hardware/lk.md) cites.
- Tools: `git grep`, `strings`, a short Python header walk, all in the RE VM.

## Safety assessment

Read-only. Public source, retained private images and a retained config
were read in the RE VM. No device access, partition access, build or boot. No
vendor code, firmware or HAL bytes enter the repository.

## Associated code

None. The commands were `git grep`/`sed` over the vendor tree, `strings` over
the two retained binaries, and a header walk of the SCP image (magic
`0x58881688`, 512-byte headers, size at offset 4, name at offset 8).

## Observations

### O1. The offload design in the vendor source

- **Option.** `MTK_AUDIO_TUNNELING_SUPPORT` is "Audio playback through dsp …
  The decoding process is done in DSP"
  ([`V/sound/soc/mediatek/Kconfig#L202-L208`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/Kconfig#L202-L208)).
  It builds `mt_soc_offload_common.o`
  ([`V/sound/soc/mediatek/mt_soc_audio_6797/Makefile#L29-L38`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/Makefile#L29-L38))
  and the `audio_ipi` MP3 task
  ([`V/drivers/misc/mediatek/audio_ipi/common/tasks/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/audio_ipi/common/tasks/Makefile)).
  `mt_soc_offload_gdma.c` is in the 6797 directory but in no Makefile rule.
- **Decoder.** The SCP, MediaTek's "tinysys" Cortex-M4 companion
  (`MTK_TINYSYS_SCP_SUPPORT`: "SCP is a MediaTek in-house DSP"). Messages go
  out as `audio_send_ipi_msg(…, TASK_SCENE_PLAYBACK_MP3,
  AUDIO_IPI_LAYER_KERNEL_TO_SCP, …)` (`mt_soc_offload_common.c` L729).
- **Codecs.** `get_caps` advertises two: `SND_AUDIOCODEC_PCM` and
  `SND_AUDIOCODEC_MP3` (L625-L627). Every message is `MP3_*`: `MP3_INIT`,
  `MP3_SETPRAM`, `MP3_SETMEM`, `MP3_DRAIN`, `MP3_SETWRITEBLOCK`, `MP3_VOLUME`,
  and back from the SCP `MP3_NEEDDATA`, `MP3_PCMCONSUMED`, `MP3_DRAINDONE`
  (`AudDrv_OffloadCommon.h` L156-L163, receive handler L667-L690). No AAC.
- **Memory.** The bitstream ring is the SCP reserve block `MP3_MEM_ID`,
  4 MiB inside the 16 MiB `scp_share` reservation
  ([`V/drivers/misc/mediatek/scp/mt6797/scp_helper.c#L103-L107`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/scp/mt6797/scp_helper.c#L103-L107)).
  The last 32 KiB of it are kept as a DRAM fallback for PCM
  (`RESERVE_DRAMPLAYBACKSIZE`, `mt_soc_offload_common.c` L73-L75, L495-L513).
- **AFE side.** The SCP's PCM plays through memif **DL3** to the I2S/DAC path
  (L251-L326). Its buffer comes from AFE SRAM through `AllocateAudioSram()`.
  Only when SRAM is taken does it fall back to the DRAM block and call
  `AudDrv_Emi_Clk_On()` (L563-L576). AFE SRAM is 48 KiB at `0x11221000`
  (`AudDrv_Afe.h` L377-L379), and a DL buffer is at most 32 KiB
  (`mt_soc_pcm_common.h` L116-L125).
- **Interfaces.** Bitstream arrives through misc device `/dev/offloadservice`
  (`OFFLOAD_DEVNAME`, L1208, L1249). Parameters arrive in a
  `struct snd_compr_params` (L555-L595), but no ASoC compress platform is
  registered. The card's `OFFLOAD` DAI link uses the dummy CPU DAI and platform
  with codec DAI `mt-soc-codec-offload-dai`, stream `Offload_Playback`
  (`mt_soc_machine.c` L1221-L1228).
- **SCP clock.** The MP3 feature asks for 20 MHz of SCP clock. VOW asks for 80,
  sensors 84, OpenDSP 270 (`scp_helper.c` L134-L175). A total above 224 MHz
  raises the SCP to 354 MHz and pins VCORE at 1.0 V (L777-L787).

### O2. How the AP sleeps in that design

- The driver holds a wakelock only while it copies bitstream. It drops it when
  the 4 MiB ring is full (L799-L808), at drain (L443) and at stop/close
  (L961, L994). With a full ring, Android may suspend the whole system.
- `ConditionEnterSuspend()` returns false while offload is enabled
  (`mt_soc_afe_control.c` L343-L351). The audio suspend hook then leaves the
  analogue path and the AFE clocks on (`mt_soc_pcm_routing.c` L1074-L1089).
- The SCP wakes the AP with `MP3_NEEDDATA` when it wants more bitstream. SCP is
  wake source bit 10 of `SPM_WAKEUP_EVENT_MASK`
  ([SPM sleep §7](../../docs/hardware/mt6797-spm-sleep.md#7-wake-sources)).
  At 128 kbit/s a full 4 MiB ring is about 4 minutes of music.
- So the vendor's model is AP in **system suspend** while the SCP decodes into
  AFE SRAM and the AFE plays. Without offload, the best the vendor allows during
  playback is deep idle or SODI, and only with the PCM buffer in AFE SRAM:
  a DRAM-backed buffer calls `AudDrv_Emi_Clk_On()`, which runs
  `disable_dpidle_by_bit(MT_CG_ID_AUDIO_AFE)` and `disable_soidle_by_bit(…)`
  ([`V/…/mt_soc_audio_6797/AudDrv_Clk.c#L1868-L1882`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/AudDrv_Clk.c#L1868-L1882)).
  Normal DL1 playback uses the same SRAM-first rule
  (`mt_soc_pcm_dl1.c` L254-L268). A 32 KiB SRAM buffer holds about 170 ms of
  48 kHz stereo S16, so the AP wakes several times a second.
- The vendor source has no power figures for offload playback.

### O3. The Gemini never shipped it

- **Kernel.** The live Gemian config has
  `# CONFIG_MTK_AUDIO_TUNNELING_SUPPORT is not set` and
  `# CONFIG_MTK_AURISYS_PHONE_CALL_SUPPORT is not set`. It has
  `CONFIG_MTK_TINYSYS_SCP_SUPPORT=y`, `CONFIG_MTK_VOW_SUPPORT=y` and
  `CONFIG_SND_COMPRESS_OFFLOAD=y` (lines 1503-1504, 1628, 2482, 2564). The
  board defconfig agrees (lines 282, 321; no tunnelling line). So
  `/dev/offloadservice` and the MP3 IPI task are not in the kernel. Nothing in
  the build calls `SetOffloadEnableFlag()`, so `mOffloadEnable` stays false and
  the offload branch of `ConditionEnterSuspend()` is dead.
- **SCP firmware.** The `scp1` image holds two sections:
  `tinysys-loader-CM4_A` (1,024 bytes) and `tinysys-scp-CM4_A` (37,444 bytes).
  Data ends at offset `0x9a42` of the 1 MiB partition. Its 294 strings name
  FreeRTOS, the SCP IPI driver, `[DVFS-SCP]` clock, SPM and VCORE requests,
  PMIC-wrapper self-tests, EINT and two "Sensor-Timer" timers. The only IPI
  names are `IPI_DVFS_*`. No string mentions audio, AFE, MP3, VOW, a decoder,
  a sensor hub or a task besides these. This matches the thermal record's
  finding that the SCP is a DVFS service.
  LK loads `scp1` or `scp2`, whichever is marked active
  ([LK `mt_scp.c` L66-L134](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mt_scp.c#L66-L134)).
  Both copies are identical.
- **Firmware files.** `/system/vendor/firmware` holds no SCP or audio-DSP
  image. Its files are the nine SPM programs, the connectivity ROM patches, FM
  coefficients and modem log filters.
- **HAL.** The 64-bit `audio.primary.mt6797.so` still holds the generic MTK
  `AudioALSAPlaybackHandlerOffload`: strings for `/dev/offloadservice`, a
  compress device, `format mp3`, `OFFLOAD_GDMA_Playback` and the
  `OffloadAudio_Check_Support` parameter. Without the kernel device it cannot
  open.

### O4. Mainline today

- `mt6797-afe-pcm.c` allocates memif buffers in DRAM. It allows periods up to
  192 KiB and buffers up to 384 KiB, about 1 s and 2 s of 48 kHz stereo S16
  (L124-L137). It has no AFE-SRAM allocation, no DL3 user and no compress
  platform. No upstream MediaTek ASoC driver registers `snd_compr` ops.
- Upstream `mtk_scp` remoteproc and SOF cover later SoCs only (MT8183 to MT8195 SCPs,
  and MT8186/MT8195 HiFi DSPs). Neither has MT6797 data, and the MT6797 SCP is
  a different generation.
- Measured on the station
  ([R1b and P6](../2026-11-06-gemini-power-management/README.md#r1b-result-2026-11-06),
  [support row](../../docs/HARDWARE_SUPPORT.md)): awake and idle, blanked,
  CPU0 only: 96 mA. All eight A53s online: 111 mA. The AUDIO domain with no
  stream: under 5 mA. s2idle: 73.3 mA. `mem` through the SPM program: about
  42 mA. No playback current has been measured.

## Analysis

**Q1 answer.** The vendor offload path is MP3-only decode on the SCP Cortex-M4
under FreeRTOS. The AP writes MP3 bitstream into a 4 MiB DRAM ring through
`/dev/offloadservice` and speaks the `audio_ipi` protocol. The SCP writes PCM
into AFE SRAM, and AFE memif DL3 plays it. The AP may system-suspend between
`MP3_NEEDDATA` wakes. The Gemini build has none of it: the kernel option is
off, and the SCP image is a 37 KiB DVFS-only build. The core claim is
rejected. The "offload" branch in the audio suspend hook is dead code on this
device, and no Gemini firmware exists that could decode audio.

**Q2 answer.** In the vendor design the AP may fully suspend once the ring is
full. The audio suspend hook keeps the AFE clocks and analogue path up, the
SCP stays clocked (20 MHz requested), and AFE SRAM keeps DRAM out of the
playback path. In ordinary vendor playback the AP may enter deep idle or SODI
only when the PCM buffer is in AFE SRAM. A DRAM buffer forbids both. Which
PLLs and the 26 MHz request stay on during an offload suspend is not stated in
the source. That would be the SPM program's resource arbitration, inferred
only.

**Q3 and the cost of each path.**

| Path | What we would write | Gating dependency | Size (estimate) |
| --- | --- | --- | --- |
| SCP offload | A new CM4 firmware with an MP3 decoder, since none exists for this device. A permissively licensed decoder such as minimp3 could be ported. Also: a loader that replaces or coexists with the LK-loaded DVFS image (the SCP also drives DVFS and touches the PMIC wrapper and I2C6, see patch 0287), an IPI driver, AFE SRAM and DL3 support, and an ASoC compress platform with a userspace that speaks `snd_compr` | A working `mem` suspend that keeps AFE, APLL, 26 MHz and the SCP alive, which nobody has shown | Months. The highest risk is the SCP, which already shares I2C6 and VCORE with the A72 path |
| Large buffer, software decode | Configuration only: a bigger PipeWire quantum for music, native 44.1 kHz | None | Days |
| AFE SRAM playback plus SPM deep idle | A small AFE patch for the SRAM buffer, once deep idle exists | SPM deep idle (Route A S3 in the [cpuidle record](../2026-11-07-mt6797-cpuidle/README.md)) | Weeks after deep idle |

**Q4 battery estimate (inference).** Screen off, headphones, design capacity
4268 mAh ([fuel gauge record](../2026-11-11-mt6351-fuel-gauge/README.md)):

- **Today, software decode.** About 96 mA awake with CPU0 only, plus an
  unmeasured playback share P. MP3 decode on an A53 is usually well under 1 %
  of a core. The codec and headphone driver are a few mA. P is likely 5–15 mA,
  so roughly 100–110 mA, or 39–43 hours. M1 below measures P.
- **Large buffers.** These only cut wakeups. With the AP awake anyway at a 96 mA
  floor, they save at most a few mA of P.
- **Ideal SCP offload.** About 42 mA (`mem`) plus the AFE, codec and SCP while
  suspended. The vendor gives no figure; if 5–15 mA, the total is 47–57 mA, or
  75–90 hours. That would roughly double music runtime. It depends on `mem`
  suspend that keeps audio alive, and on firmware that does not exist.

The gap between awake (96 mA) and `mem` (42 mA) is real. The decode itself is
not where the energy goes; the always-on floor is. Any route that lowers the
floor during playback needs the SPM work first. The suspend and cpuidle
sessions already own that work, and it helps every use, not only music.

## Conclusion

**Rejected** for this unit and these revisions: the stock Gemini does not
offload audio. MediaTek's MP3-on-SCP design exists in the generic 6797 source.
The Gemini kernel compiles it out, and its SCP firmware has no audio code.

Recommendation:

1. **Do not start SCP offload now.** It means firmware written from scratch,
   SCP ownership conflicts and a `mem`-with-audio dependency. The gain is
   at most about 2× music runtime, and only after the SPM work.
2. **Measure playback cost first (M1).** If P is small, software decode stays
   the answer and the battery work stays on the idle floor.
3. **Keep software decode, tune it if M1 says so.** Use a large PipeWire
   quantum for background music and avoid 44.1→48 kHz resampling.
4. **Later, once SPM deep idle works:** put the playback buffer in AFE SRAM,
   as the vendor does, so playback no longer forbids deep idle.
5. Revisit offload only if `mem` suspend matures and a test shows the AFE can
   play from SRAM while the AP is in `mem`.

## Follow-up

- Durable facts: [Gemini audio §offload](../../docs/hardware/gemini-audio.md#25-compressed-audio-offload)
  and the audio row of the [vendor kernel ABI](../../docs/hardware/vendor-kernel-abi.md).
- **M1 (proposed, custodian).**
  - Hypothesis: MP3 playback adds under 10 mA to the 96 mA awake floor, and a
    larger PipeWire quantum recovers little of it.
  - Unique observation: mean `current_now` over 60 s windows, as in R1b.
    Unplugged, blanked, CPUs 1–7 offline, Wi-Fi unloaded, fixed volume on the
    headphone path. Windows:
    1. silent;
    2. `mpv --no-video` of a generated 128 kbit/s MP3 through PipeWire defaults;
    3. the same with `PIPEWIRE_LATENCY=8192/48000`.
  - Also record AFE and `arch_timer` interrupts, and the CPU time of `mpv` and
    `pipewire`.
  - Decision:
    - window 2 minus window 1 under 10 mA: no buffer work, and offload stays
      parked;
    - over 10 mA, and window 3 recovers more than half of it: the arch-root
      session ships a music-player latency setting;
    - over 10 mA and window 3 does not help: find the cost (resampling, the
      codec bias, the AFE's runtime PM) with the audio session.
- Dependencies: the gemini-audio session (AFE SRAM, buffer limits, AFE runtime
  PM); the cpuidle and SPM sessions (deep idle); the suspend session (`mem`
  with audio running).
