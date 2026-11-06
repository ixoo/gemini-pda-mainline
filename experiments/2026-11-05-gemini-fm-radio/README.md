# Experiment: FM radio on the mainline station, facts and first test

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-fm-radio` |
| Status | `running`: the receiver works on mainline as a V4L2 radio, `/dev/radio0`, with tuning, seek and RDS (F1 to F3), and the headset cable is its antenna. The stereo flag never sets (F4: not forced mono). FM audio (0591-0594) written; in F5 both streams started cleanly but the owner did not hear the station; F5b, a read-only snapshot during the stream, admitted on 2026-11-05, not yet run |
| Subsystem | MT6631 FM receiver behind CONSYS, STP task 1, AFE second I2S input |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-05 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | M6 peripherals (FM), follow-up gate 3 of the [WMT recovery record](../2026-07-12-connectivity-wmt-recovery/README.md#follow-up-gates) |

## Question or hypothesis

Is the FM receiver present and reachable on this Gemini, and if so, what does a
mainline driver talk to?

Hypothesis for the first device test (F1): with the WMT FM function on and the
vendor's FM clock-on sequence applied, FM register `0x62` reads `0x6631` over
STP task 1.

Nothing before F1 shows that FM was ever powered on this board, on Gemian or on
mainline. The `0x6631` Gemian prints at boot is not that read (O4, S1).

## Provenance and environment

- Kernel: Linux 7.1.3 with the local series, tag `v1` (`5c263c74`) as the base
  station. No FM code exists in the series.
- Vendor reference: the public downstream tree
  [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18)
  at `8cfe6596a503612e3332d9c26e292a19525a7f07`, read only as evidence. The
  paths below are relative to `drivers/misc/mediatek/connectivity/` unless they
  start with `sound/`.
- Gemian evidence: the running configuration and boot image under ignored
  `artifacts/vendor-kernel/gemian-2019/`, the userspace extraction under ignored
  `artifacts/device-userspace/gemian-2019/`, the published
  [WMT recovery results](../2026-07-12-connectivity-wmt-recovery/results/) and a
  retained private Gemian boot log. No device access was used for this record.

## What is observed

| # | Observation | Source |
| --- | --- | --- |
| O1 | Gemian's running kernel sets `CONFIG_MTK_COMBO_CHIP_CONSYS_6797=y`, `CONFIG_MTK_FMRADIO=y` and `CONFIG_MTK_FM_CHIP="MT6631_FM"`. `CONFIG_MTK_FM_50KHZ_SUPPORT` is unset | running config |
| O2 | Gemian installs `fm_cust.cfg` (304 bytes), `mt6631_fm_v1_coeff.bin` (1092) and `mt6631_fm_v1_patch.bin` (1028); digests in the [runtime summary](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt) | WMT recovery record |
| O3 | `/dev/fm` exists on Gemian | same |
| O4 | At about 9.5 s Gemian's FM module loads, prints `chipid:0x6631, chip type:1`, its default configuration, then the same values after loading `fm_cust.cfg`, including `aud path[1]I2S state[1]mode[0]rate[0]pad[0]`. No FM power-up, patch download or tune line follows in that boot | private boot log |
| O5 | The same boot probes the AFE `mt-soc-fm-i2s-pcm` and `mt-soc-fm-i2s-awb-pcm` platforms; the audio service opens and closes the FM-I2S PCM once at about 22 s with rate 0 | private boot log |
| O6 | `fm_cust.cfg` sets RSSI thresholds (long and short antenna both `-296`), de-emphasis `0` (50 µs) and oscillator `0` (26 MHz). It carries no antenna or audio-route key | userspace extraction |
| O7 | Gemian's userspace has `libfmcust.so` and no FM application, JNI library or service found by name | userspace extraction |
| O8 | The vendor device tree carries only the generic AFE nodes `mediatek,mt_soc_pcm_fm_i2s`, `mediatek,mt_soc_pcm_fm_i2s_awb` and `mediatek,mt_soc_pcm_fmtx`. It has no FM board node, FM interrupt, antenna switch or FM pin group | boot image DTB, decompiled |

## What the vendor source says

These are statements of the public source, not observations of this device.

| # | Statement | Where |
| --- | --- | --- |
| S1 | The `0x6631` in O4 is a constant: `mt6631_get_chipid()` returns `0x6631` without touching hardware. The real identity check is in `mt6631_PowerUp()`: after the clock-on sequence it reads FM register `0x62` and fails with `fm sys error` unless it is `0x6631` | `fmradio/mt6631/pub/mt6631_fm_lib.c` |
| S2 | FM control rides the shared STP link as task 1 (`FM_TASK_INDX`), and the function is switched by WMT with type 1 (`WMTDRV_TYPE_FM`), the same mechanism Bluetooth (task 0, type 0) and GNSS (task 2, type 2) already use on mainline | `common/common_main/include/stp_exp.h`, `wmt_exp.h`, `fmradio/core/fm_link.c` |
| S3 | FM packets are `01 OPCODE LEN_LO LEN_HI payload`; events start with `04`. A register read is `01 03 01 00 ADDR`. Opcodes `0x18`/`0x19` read and write connectivity-MCU registers and `0x20`/`0x21` the common SPI to the RF chip, all executed by the firmware: the AP maps no FM register | `fmradio/inc/fm_link.h`, `fmradio/core/fm_cmd.c` |
| S4 | Power-up order: common SPI parameter, a-die clock enable, 26 MHz crystal sleep off, bandgap LDO on, clock-on batch (opcode `0x07`), read `0x62`, DSP patch and coefficient download, digital init, RF fine tune, then FM register `0x9b = 0xf9ab` (I2S transmit mode) and three MCU writes that enable the FM audio trigger. Power-down has its own sequence and is not the exact reverse | `mt6631_fm_lib.c` |
| S5 | For an SoC CONSYS chip (type 1) the audio default is `FM_AUD_I2S`, CONSYS is I2S master at 32 kHz on the CONSYS pad (`FM_I2S_PAD_CONN`); that matches O4. The source comments the enable step "connsys FM 2 wire RX": the RF chip passes FM samples digitally to CONSYS, which drives the I2S | `fmradio/core/fm_config.c`, `fmradio/inc/fm_interface.h`, `mt6631_fm_lib.c` |
| S6 | The MT6797 AFE takes that I2S on its second I2S input, slave, 16 bit, I2S format, pad select "from CONNSYS", runs the ASRC from 32 kHz to 44.1 or 48 kHz, applies hardware gain 1 and connects `I00/I01` to `O13/O14` (the DAC path to the MT6351) for hostless playback. The AWB variant captures the same input to memory. FM never uses an MT6351 analog input | `sound/soc/mediatek/mt_soc_audio_6797/mt_soc_pcm_fm_i2s.c`, `..._awb.c` |
| S7 | The driver supports a long antenna (in the headset cable) and a short one, chosen by a bit in `FM_MAIN_CG2_CTRL`. Nothing in O6 or O8 selects one | `mt6631_fm_lib.c` |
| S8 | The FM-specific VCN28 step exists only in co-clock mode; Gemini's `WMT_SOC.cfg` has `co_clock_flag = 0`, so the common CONSYS power-on already covers the rail ([GNSS document](../../docs/hardware/gemini-gnss.md)) | WMT recovery source summary |
| S9 | The MT6631 library has a receive power-up only; the TX fields in the shared configuration are generic. FM itself transmits nothing | `mt6631_fm_lib.c` |

## Offline reverse engineering (2026-11-05)

A second pass read the rest of the MT6631 library and looked at the firmware
statically in the project RE VM against the 2026-07-12 userspace extraction.
Nothing was executed. The full contract is in the
[FM document](../../docs/hardware/gemini-fm.md); what is new:

| # | Finding | Source |
| --- | --- | --- |
| R1 | Command packets, the eight batch operations, and register, MCU and common-SPI access are fully specified, with the vendor's 3, 6 and 15 s reply timeouts | `fmradio/core/fm_cmd.c`, `fmradio/inc/fm_cmd.h`, `fm_link.h` |
| R2 | The tuner's register map: identity `0x62`, channel `0x65` in 50 kHz steps above 64 MHz, RSSI `0x6c` at 0.375 dB per step with stereo in D12, volume `0x7d`, mute `0x9c`, antenna, de-emphasis and ROM query bits in `0x61` | `mt6631/inc/mt6631_fm_reg.h`, `mt6631_fm_lib.c` |
| R3 | The chip's own seek is compiled out; the vendor searches by stepping soft-mute tunes (`0x17`), each returning a channel quality record judged against the `fm_cust.cfg` thresholds | `mt6631_fm_lib.c` |
| R4 | Power-down is not the reverse of power-up: up sets D1 of MCU `0x81024030`, down clears D1 of `0x80101030`, and the bandgap LDO bits are never cleared | `mt6631_fm_lib.c` |
| R5 | `mt6631_fm_v1_patch.bin` is 16-bit DSP words with no header or strings, sent as three segments (512, 512, 4). `mt6631_fm_v1_coeff.bin` is a coefficient table sent as 512, 512, 68; its bytes 38-39 (the vendor's patch version) are `0x0000` and bytes 4-5 are already zero. The file is chosen by the DSP ROM version read during power-up; only v1 is installed | RE VM, files with the published digests |
| R6 | The two `ROMv3` CONSYS patches name FM only in a WMT default-parameter message and a coexistence task-status message; they carry no FM command handler, so the handler is inferred to be in the CONSYS ROM | RE VM, `strings` |
| R7 | `libfmcust.so` (SHA-256 `80a9ea1a…f79d0`) exports only `CUST_get_cfg`, which maps the WMT chip-ID property to an FM chip, `0x6797` to MT6631. It has no band, region or antenna data | RE VM, `objdump` |
| R8 | RDS needs no polling: after enable (`0x80 = 6`, `0x63` D4) the firmware pushes raw groups as unsolicited `0x0d` events, up to 12 per event, each with blocks A-D, a corrected-bit count and CRC flags. The register-FIFO read path in the MT6631 library is compiled out (`#if 0`). The host decodes PI, PS, RT, PTY, CT and AF | `mt6631/pub/mt6631_fm_rds.c`, `fmradio/inc/fm_rds.h`, `fmradio/core/fm_link.c` |
| R10 | Stereo, checked after F3: the vendor's only stereo controls are reading `RSSI_IND` D12 (`GetMonoStereo`) and forcing mono with `0x75` D3, written between top `0x050 = 7` and `0x050 = 0xf` (`SetMonoStereo`). The vendor interface has no blend or pilot threshold setting, the power-up and tune never write `0x75`, and `fm_cust.cfg` has no stereo key. The MT6627, MT6630 and MT6632 libraries in the same tree read the same bit. Gemian's userspace has no FM application, so nothing ever set stereo there. The coefficient file starts with a table of DSP addresses 13 words apart (`0x4010` to `0x4078`) followed by constants, and the patch is 231 words of DSP code; without a description of the DSP neither can be read for a stereo threshold | `mt6631_fm_lib.c`, `mt6630`/`mt6632`/`mt6627` libraries, `fm_ioctl.h`; RE VM |

## What is inferred

- **Population.** The FM receiver sits on the same RF companion as Wi-Fi,
  Bluetooth and GNSS, reached through the same CONSYS common SPI (S3), and
  those three work on this board. So the FM silicon is very likely present.
  This is not proof: a block can be unbonded, the FM antenna input can be left
  unmatched, and Gemian never powered FM (O4, O7).
- **Audio is digital.** FM audio goes RF chip to CONSYS to the AFE second I2S
  input, all inside the SoC package path (S5, S6). There are no board audio pins
  to describe, and the MT6351 analog inputs are not involved.
- **Antenna is unknown.** If the board follows the reference design, the
  headset cable is the antenna. F2 below separates long from short.

## What is open

1. ~~Does register `0x62` read `0x6631` on this board?~~ Yes (F1).
2. ~~Which antenna is wired?~~ The headset cable: plugging a headset in raised RSSI by about 23 dB (F2c).
3. The redistribution rights of the two MT6631 FM files are unknown, as for the
   other CONSYS files; they would come from the owner's own Gemian as for the
   v1 release ([firmware](../../docs/hardware/firmware.md)).
4. Whether the vendor's power-down leaves CONSYS fit for Wi-Fi without a reload.
   F1 suggests yes: three pings passed before the reload. One run, no stress.
5. The mainline AFE has no I2S DAI at all ([audio document](../../docs/hardware/gemini-audio.md)),
   so FM audio needs a new second-I2S-input DAI with the ASRC. Its register
   layout has not been checked against the mainline `mt6797-reg.h`.
6. Whether Planet's Android image ever offered FM on this hardware (owner
   knowledge, not a blocker).
7. The DSP ROM version, which picks the patch file (F2 reads it).
8. ~~What signals RDS data on CONSYS?~~ The firmware pushes it as `0x0d` events (R8), observed in F3.
9. Why the stereo flag (`RSSI_IND` D12) never sets, on two stations at about -72 and -81 dBm (F2c, F3). R10 rules out a missing vendor setting, F4 rules out forced mono; a strong, known-stereo station is still to be tried.

## Mainline shape

| Part | Interface | Notes |
| --- | --- | --- |
| CONSYS owner | export task 1 attach and a WMT FM function control | as [0421](../../patches/proposals/0421-soc-mediatek-mt6797-consys-let-a-client-send-and-swi.patch) and [0511](../../patches/proposals/0511-soc-mediatek-mt6797-consys-let-Bluetooth-share-the-S.patch) did for GNSS and Bluetooth; register a child device |
| Tuner | V4L2 radio receiver, `/dev/radio0`, under `drivers/media/radio/`, `=m` | frequency, hardware seek, signal strength, mute, de-emphasis control; RDS later through `read()`. The TI `wl128x` driver is the closest precedent (FM on a shared combo transport). No `/dev/fm` ABI |
| Audio | ASoC capture DAI for the AFE second I2S input from CONSYS, plus a hostless route to the ADDA playback path; an FM link in the Gemini card | new AFE work, separate series from the tuner |
| Firmware | `request_firmware()` of the patch and coefficient files | not redistributed; `fm_cust.cfg` values become driver defaults |
| Region | band 87.5 to 108 MHz and 75 µs de-emphasis for the station's US country; 50 µs and the wider band selectable through V4L2 | Gemian's 50 µs default (O6) is a China setting |

The station config already has `CONFIG_VIDEO_DEV=m`; the tuner adds
`CONFIG_MEDIA_RADIO_SUPPORT` and `CONFIG_RADIO_ADAPTERS` in a station fragment.

## Safety assessment

F1 is a radio-subsystem action, not read-only: it switches a CONSYS function and
writes FM power and clock registers through the firmware, as the vendor does
before every FM use. It tunes nothing, enables no audio path, loads no FM patch
or coefficient file and selects no antenna. FM has no transmitter (S9), so F1
emits nothing; the shared risk is CONSYS coexistence with Wi-Fi and Bluetooth,
as in [GNSS T2](../2026-11-01-gemini-gnss-link/README.md#t2-first-receiver-start-radio-action-admitted).
No calibration, NVRAM, partition or boot write. Modules only, no boot. The
station's Wi-Fi country (US) stays set; F1 needs no band. A timed-out WMT or STP
exchange stops the link for that power lifetime, which the existing CONSYS
reload recovers.

## Test F1: FM identity read (admitted)

The owner admitted F1 on 2026-11-05. This covers exactly the effects below, once;
anything else, including a retry, needs asking again.

**Code:**
[0581](../../patches/proposals/0581-soc-mediatek-mt6797-consys-let-the-FM-receiver-use-t.patch)
lets task 1 attach and send, exports a WMT FM function control and registers an
`mt6797-fm` child device.
[0582](../../patches/proposals/0582-media-radio-add-a-first-MT6797-CONSYS-FM-receiver-dr.patch)
adds `radio-mt6797`, whose probe runs only the steps below and registers
nothing. Its event parser keeps state across link frames and never refuses one.
Each command waits 3 s for the event with the same opcode, as the vendor does.
[`gemini-a53-station-fm.fragment`](../../configs/gemini-a53-station-fm.fragment)
builds it as a module in profile `mt6797-a53-station-a72`; it also lets the TV
tuner core autoselect a dozen I2C tuner modules that nothing loads.

**Checks so far:** both files build with `W=1` and no warning in the dev VM
against the station series with the fragment, and `checkpatch --strict` is
clean apart from the missing sign-off. 0580 to 0582 apply to the station tree
with the build's `git apply --unidiff-zero`. Nothing has run on hardware.

**Buildbox build:** `b23c2346`, profile `mt6797-a53-station-a72`,
`BUILD_MODULES=1`, 754 patches, package `557f9d68…`, patchset `cdd70a16…`,
config `8739e8ca…`, `Image.gz` `da0c8a3a…`; validation passed. Modules:
`radio-mt6797.ko` `d7686524…`, `mt6797-consys.ko` `1797e440…`. Built, not
booted.

**Effects, once, on module load:**

1. Attach STP task 1 (the CONSYS driver repeats its link check if this is the
   first client).
2. WMT FM function-on: `01 06 02 00 01 01` by analogy with GNSS
   (`... 02 01`) and Bluetooth; expect `02 06 01 00 00`.
3. Vendor power-up steps before the patch download (S4): MCU
   `0x8102600c = 0x800f`, set D1 of `0x81024030`, set D7 of `0x81021234`, set
   D28:27 of top `0x0c0`, then the clock-on batch with de-emphasis left at
   Gemian's 50 µs (nothing is tuned).
4. Read FM register `0x62` three times (`01 03 01 00 62`, reply
   `04 03 02 00 VAL_LO VAL_HI`); log the values.
5. Vendor power-down sequence as written (see R4), WMT function-off, detach.
   If any FM command got no answer, the power-down is skipped and only
   function-off and detach run.

**Not done:** no patch or coefficient download, no tune, seek or RDS, no
antenna select, no I2S or AFE change, no retry.

**Needs** a boot of a `mt6797-a53-station-a72` image with `BUILD_MODULES=1`
from the commit that adds 0582 or later, with the modules from the same package:
0581 changes the CONSYS module, so a module from another package must not be
mixed in. Batch it with the next station boot; it needs no boot of its own.

**Procedure,** one load, no retry:

1. Wi-Fi up and associated; one gateway ping through `wlan0`. Note
   `dmesg | wc -l` and the taint.
2. `insmod radio-mt6797.ko`; note the exit code.
3. New `dmesg` lines matching `STP link|WMT FM|mt6797-fm|radio`. The driver
   prints one `identity ... power-up ... power-down` line and one `link:` line.
4. `rmmod radio-mt6797`, three gateway pings, then the usual CONSYS and `mac`
   reload and three more pings. Note the taint again.

| Observation | Meaning | Next |
| --- | --- | --- |
| `0x62` = `0x6631` three times | FM block present and reachable | write the tuner in stages; F2 |
| function-on answers, `0x62` reads another stable value | reachable, unexpected identity | stop; compare offline with the vendor read path |
| function-on answers, read times out | FM block not responding | stop; record as likely absent or gated; no blind retry |
| a power-up command times out before the read | the firmware does not run FM commands, or a step is wrong | stop; compare the failing opcode offline |
| any kernel warning or Oops | driver fault | stop; preserve `dmesg`; CONSYS reload |
| function-on refused or times out | firmware or board does not offer FM | stop; function-off; CONSYS reload |
| Wi-Fi ping fails after unload | FM power-down disturbs CONSYS | record; CONSYS reload; F2 must reload CONSYS after FM |

## F1 result (2026-11-05): the receiver answers

Run by the custodian session with the owner's admission. Raw outputs are
private under `artifacts/station-work-57/boot-1/`.

- **Identity:** image `f0f66d1b…`, composed from package `557f9d68…`
  (`b23c2346`, `mt6797-a53-station-a72`), boot `0b3c33aa-0b2c-4d17-b876-87461b11f72e`;
  `radio-mt6797.ko` `d7686524…`, `mt6797-consys.ko` `1797e440…` from the same
  package.
- **Before:** Wi-Fi associated on 5200 MHz with a lease, gateway ping 1 of 1,
  taint 0.
- **Load:** `insmod` rc 0; probe returned 0 after 14,093 µs.
- **Log, in order, all within 14 ms:**

  ```text
  STP link running: tx-seq=2 rx-seq=2 peer-ack=1 local-ack=1
  STP link check: result=0 reply=10 bytes 02 04 06 00 00 04 df 0e 68 01
  WMT FM function on: result=0 reply=5 bytes 02 06 01 00 00
  WMT FM function off: result=0 reply=5 bytes 02 06 01 00 00
  mt6797-fm mt6797-fm: identity 6631 6631 6631 (3 of 3 match), power-up 0, power-down 0
  STP link halted: failed=0 busy=0 rx=28 discarded=0 dup=0 tx=28 acks=28 timeouts=0 resent=0 wmt-unsolicited=0 first=0 bytes
  STP link firmware messages: assert=0 log=0; after failure 0 bytes
  mt6797-fm mt6797-fm: link: bytes=138 events=25 unexpected=0 junk=0
  ```

  No `command xx:` error line, no warning or Oops.
- **After:** `rmmod` rc 0, gateway pings 3 of 3, taint 0. Then the usual
  CONSYS and `mac` reload: both rc 0, CONSYS kept its earlier WMT setup,
  Wi-Fi associated again on 5200 MHz with a lease, pings 3 of 3, taint 0. The
  station stays on this image.

**Analysis.** The driver sends 25 FM commands (8 for power-up, 3 reads, 14 for
power-down) and got exactly 25 events with matching opcodes, none unexpected
and no stray bytes, so the packet framing in R1 is right in both directions.
The firmware runs FM commands, including the batches, the MCU accesses and the
RF top-block accesses. The identity register gives `0x6631` every time after
the clock-on batch, which is the vendor's own check that the FM block is there
and clocked. Wi-Fi kept working after the vendor power-down and before the
CONSYS reload, so R4's asymmetry did not disturb it in this run.

**Conclusion:** `confirmed` for this unit and image: the MT6631 FM block is
present and reachable over STP task 1, and the vendor power-up to the identity
check and the vendor power-down run without error. This says nothing yet
about the DSP, the antenna, reception or audio.

Following the decision table, the tuner is written in stages, starting with F2.

## Test F2: first tune and antenna check (admitted)

The owner admitted F2 on 2026-11-05. This covers exactly the effects below,
once; anything else, including a retry, needs asking again.

**Hypothesis:** with the rest of the vendor power-up, the DSP accepts the v1
patch and coefficient files, a tune to a strong local station completes, and
the signal strength there is well above the noise. A headset plugged into the
jack raises it clearly if the long antenna (the headset cable) is the one
wired, as the reference design does.

**Code:**
[0583](../../patches/proposals/0583-media-radio-mt6797-tune-and-log-the-signal-strength-.patch)
adds two module parameters to `radio-mt6797`. Without `freq_khz` the module
does exactly F1. With it, after the three identity reads probe runs:

1. The DSP ROM version query (R2): `0x61` D15, D1, D0; poll `0x84` for `1`
   every 1 ms, at most 100 times; read `0x83[15:8]`; then put `0x61` back.
2. The patch (`0x12`) and coefficient (`0x13`) downloads from
   `/lib/firmware/mediatek/mt6797/mt6631_fm_v1_patch.bin` and
   `mt6631_fm_v1_coeff.bin`, each refused unless its SHA-256 is the retained
   Gemian file's (O2). Version 0 selects these files; any other version stops
   here, before the download.
3. `0x92 = 0`, `0x90 = 0x40`, `0x90 = 0`, then the digital init and RF fine
   tune batches (power-up steps 8 to 10 of the [FM document](../../docs/hardware/gemini-fm.md#power-up)).
   Step 11, the I2S output and the CONSYS audio trigger, is left out: no audio
   leaves the receiver.
4. The vendor tune: its ramp-down first, then the channel register and the
   tune batch, whose event must report `1`.
5. Every second for `seconds` (default 60, at most 300): read `0x6c` and log
   the raw value, dBm (raw × 6 / 16) and the stereo flag.
6. The F1 power-down, function off, detach.

Only plain channels are accepted: 87.5 to 108 MHz in 100 kHz steps, minus 53
channels for which the vendor tune also sets a channel parameter, the TDD cell
mode or a 64 MHz common SPI clock (`fm_special_channels` in the driver; for
example 90.5 to 91.1, 97.9 to 99.4 and 103.7 to 104.2 MHz). A refused value
does nothing at all.

**Checks so far:** `W=1` and `checkpatch --strict` clean in the dev VM; 0583
applies to the station tree. The two digests in the driver match the
published ones. Buildbox build `4f87f6b8`, profile `mt6797-a53-station-a72`,
`BUILD_MODULES=1`, 755 patches, package `e1b8b58a…`; validation passed.
Its `Image.gz` (`da0c8a3a…`), config (`8739e8ca…`) and `mt6797-consys.ko`
(`1797e440…`) are byte-identical to the F1 package's, and only
`radio-mt6797.ko` differs (`aafa0671…`, same `vermagic`). Not run.

**Safety:** receive only, as F1; the FM block has no transmitter. New effects
are the DSP firmware download into the FM block, which is volatile and goes
with the power-down, and the tune. No antenna select (the vendor default,
long, stays), no audio path, no AFE or codec change, no calibration, NVRAM or
partition write. Two files are copied onto the station's root file system
from the owner's own Gemian copy; they are not published. The frequency the
owner picks is kept private, since a local station hints at a location.

**Needs:** the running F1 image (`f0f66d1b…`) with `radio-mt6797.ko`
`aafa0671…` from package `e1b8b58a…`; no boot, since the kernel and every
other module are identical to the F1 package's; `mt6631_fm_v1_patch.bin` and `mt6631_fm_v1_coeff.bin` in
`/lib/firmware/mediatek/mt6797/`; the owner, about 3 minutes, a wired headset,
and a strong local station that is not refused.

**Procedure,** one load, no retry:

1. Wi-Fi associated, gateway ping, taint, `dmesg | wc -l`. No headset plugged.
2. `insmod radio-mt6797.ko freq_khz=<station> seconds=120`. It returns after
   about 125 s.
3. At the `t=60` log line, the owner plugs the headset in and leaves it.
4. New `dmesg` lines from `mt6797-fm` and the `STP link` and `WMT FM` lines.
5. `rmmod radio-mt6797`, three pings, CONSYS and `mac` reload, three pings,
   taint.

| Observation | Meaning | Next |
| --- | --- | --- |
| Downloads and tune succeed; median RSSI with the headset at least 6 dB above without it | long antenna wired through the headset; the receiver works | V4L2 tuner; F3 audio once the AFE input exists |
| Both halves similar and above -90 dBm | receives without a headset: a short antenna or another path | try the short-antenna bit in F3; then the tuner |
| Both halves similar and near -110 dBm | nothing received | check the frequency, then the short-antenna bit; no blind retry |
| DSP ROM version other than 0 | a different DSP ROM than the files expect; the driver stops before the download | compare offline |
| A download or the tune times out or fails | firmware refused or sequence wrong | stop; compare the failing opcode offline |
| Wi-Fi fails after unload | FM DSP activity disturbs CONSYS | record; CONSYS reload |

The stereo flag is logged as a hint of signal quality, not a pass criterion.

## F2 result (2026-11-05): stopped at the tune, a driver fault

Run by the custodian session with the owner's admission, on the running F1
image (`f0f66d1b…`, boot `0b3c33aa`), `radio-mt6797.ko` `aafa0671…` with the
matching vermagic; the package's `Image.gz` and `mt6797-consys.ko` are
identical to the running ones. Both FM files were copied to the station's
`/lib/firmware/mediatek/mt6797/` (RAM root file system) and matched their
digests. Raw `dmesg`, with the frequency redacted, is private under
`artifacts/station-work-57/boot-1/`.

- **First load:** the owner's first station is one of the refused special
  channels: `refused: -95`, no STP or WMT line, nothing reached the radio.
  `rmmod` rc 0. As the request allowed, the owner picked another station.
- **Second load,** the one that reached the radio, 0.25 s in all:

  ```text
  STP link running: tx-seq=2 rx-seq=2 peer-ack=1 local-ack=1
  STP link check: result=0 reply=10 bytes 02 04 06 00 00 04 df 0e 68 01
  WMT FM function on: result=0 reply=5 bytes 02 06 01 00 00
  mt6797-fm: DSP ROM version 0: 0
  mt6797-fm: mediatek/mt6797/mt6631_fm_v1_patch.bin: 1028 bytes: 0
  mt6797-fm: mediatek/mt6797/mt6631_fm_v1_coeff.bin: 1092 bytes: 0
  mt6797-fm: command 09: -71
  mt6797-fm: power-up and tune to <redacted> kHz: -71; logging for 120 s
  WMT FM function off: result=0 reply=5 bytes 02 06 01 00 00
  mt6797-fm: identity 6631 6631 6631 (3 of 3 match), listen -71, result -71, power-down 0
  STP link halted: failed=0 busy=0 rx=71 discarded=0 dup=0 tx=71 acks=71 timeouts=0 resent=0 wmt-unsolicited=0 first=0 bytes
  mt6797-fm: link: bytes=326 events=68 unexpected=0 junk=0
  ```

  No signal-strength line followed, so the headset step never came.
- **After:** `rmmod` rc 0, pings 3 of 3, CONSYS and `mac` reload, Wi-Fi back on
  5200 MHz with a lease, pings 3 of 3, taint 0, no warning or Oops.

**Analysis.** Everything up to the tune worked: DSP ROM version 0, the one the
v1 files are for, both downloads, the digital init (whose batch waits for the
DSP's init-complete state) and the RF fine tune. The tune command's event
arrived but carried no `1`, which the driver reads as `-EPROTO`.

The vendor explains it. Its event parser turns an event with no payload into
the opcode's own flag and the payload `1` on opcode `0x09` into a separate
"tune done" flag, and its tune waits for both
(`fmradio/core/fm_link.c`, `fmradio/inc/fm_utils.h`: the wait needs every
bit of the mask). So the tune gets two events: an empty acknowledgement, then
"done" when the DSP finishes. The driver took the acknowledgement as the
whole answer, and powered the block down at once, before any "done" could
come. The count agrees: the commands sent, with one ROM-ready poll, are 67
plus 1, exactly the 68 events, none unexpected, so no "done" arrived during the
power-down either.

**Conclusion:** `inconclusive` for reception. Newly shown on this board: the
DSP ROM is version 0, the v1 patch and coefficients are accepted, and the DSP
finishes its digital init. The tune fault is the driver's.

The fix and a repeat are F2b below, which also tunes the channels F2 refused (R9). A repeat needs a new admission.

## Why F2 refused the owner's first station (R9)

F2 refused 53 channels for which the vendor tune does more than its plain
sequence. The owner's first station is a valid broadcast frequency; it is
refused only because the vendor tables mark it. They hold three kinds of
per-channel extras, all fixed in the MT6631 library (`mt6631_fm_lib.c`:
`mt6631_TDD_list`, `mt6631_chan_para_map`, `mt6631_SPI_hopping_list`), not
board data. Reduced to 87.5-108 MHz on the 100 kHz grid:

| Extra | Channels | What the vendor tune does |
| --- | --- | --- |
| TDD cell mode | 90.4-91.1, 97.9-99.4, 106.9-108.0 MHz | register `0x30` D3:2 = `10` ("TDD solution") instead of `00` ("FDD", the default) |
| channel parameter | 18 channels, among them 88.3, 92.1-92.3, 95.5, 96.0, 98.3, 104.0, 107.5 and 107.6 MHz | the value (1, 2, 3 or 8) in `CHANNEL_SET` D15:12 |
| 64 MHz common SPI clock | 90.9-91.2, 103.8-104.2 MHz | before the tune, keep the 64 MHz clock awake and switch the common SPI clock to it (MCU `0x81021138`, `0x80026000`, polling `0x8002110c` D27, `0x81026004`); the ramp-down switches it back |

The vendor names the first two only "cell mode" and "HiLo side / FA / ATJ";
what they change inside the receiver is not documented. Several of the listed
channels sit at multiples of 26 MHz (78, 104 MHz) or near them, which fits
spur avoidance, but that is inference.

The first two need one more register value each, so refusing them was a
simplification of this driver, not a hardware limit.
[0587](../../patches/proposals/0587-media-radio-mt6797-tune-channels-with-the-TDD-mode-o.patch)
now follows the vendor for both; only the nine 64 MHz clock channels are still
refused.

## Test F2b: the F2 test with both fixes (admitted)

The owner admitted F2b on 2026-11-05: one load, the effects of F2 plus the
two changes below; anything else needs asking again.

The same test as F2, procedure, safety and decision table unchanged, with two
more patches:

- [0586](../../patches/proposals/0586-media-radio-mt6797-wait-for-both-tune-events.patch):
  the tune waits up to 3 s for both events, the empty acknowledgment and
  "done" with `1`, in either order, and logs the acknowledgment's length and
  the "done" payload. Anything else still fails the tune.
- [0587](../../patches/proposals/0587-media-radio-mt6797-tune-channels-with-the-TDD-mode-o.patch):
  the TDD cell mode and channel parameters above; the tune line names the mode
  and parameter. The owner's first station becomes tunable, so it can be used.

Checks: each patch builds with `W=1` and passes `checkpatch --strict` in the
dev VM, and both apply to the station tree. Buildbox build `f7c4f645`, profile
`mt6797-a53-station-a72`, `BUILD_MODULES=1`, 758 patches, package `4f2e3383…`,
config `6b86c0b3…`, `Image.gz` `5229086f…`; validation passed, and the copy
here checks against its `SHA256SUMS`. `radio-mt6797.ko` `9f5f93e8…`,
`mt6797-consys.ko` `1797e440…` (unchanged since F1). Not run.

**Needs a boot,** unlike F2: the vibrator's 0585 changed the station config and
`Image.gz` after F2. That image is the vibrator V1 one (its package `445e8b8d…`
has the same `Image.gz`, config and `mt6797-consys.ko`), so F2b rides that
boot with `radio-mt6797.ko` from `4f2e3383…`, or from a composition of
`4f2e3383…`, which carries both. The two FM files must be copied again after
the boot, since the station's root file system is in RAM.

## F2b result (2026-11-05): tune acknowledged, no "done"

Run by the custodian session with the owner's admission, in the vibrator V1
boot `a22a4ca8`, image `02e045fa…` from package `8f569751…` (built from
`c546644d`): `Image.gz` `5229086f…`, `radio-mt6797.ko` `9f5f93e8…` with the
matching vermagic, `mt6797-consys.ko` `1797e440…`, the same hashes as
`4f2e3383…`. Both FM files copied again and matched. The owner's first F2
station, which 0587 makes tunable. Raw `dmesg`, frequency redacted, is
private under `artifacts/station-work-58/boot-1/`.

```text
290.343 STP link running: tx-seq=2 rx-seq=2 peer-ack=1 local-ack=1
290.343 STP link check: result=0 reply=10 bytes 02 04 06 00 00 04 df 0e 68 01
290.345 WMT FM function on: result=0 reply=5 bytes 02 06 01 00 00
290.353 mt6797-fm: DSP ROM version 0: 0
290.359 mt6797-fm: mediatek/mt6797/mt6631_fm_v1_patch.bin: 1028 bytes: 0
290.365 mt6797-fm: mediatek/mt6797/mt6631_fm_v1_coeff.bin: 1092 bytes: 0
293.600 mt6797-fm: tune: TDD mode, parameter 0, acknowledgment length 0, done 0: -110
293.600 mt6797-fm: power-up and tune to <redacted> kHz: -110; logging for 120 s
293.602 WMT FM function off: result=0 reply=5 bytes 02 06 01 00 00
293.602 mt6797-fm: identity 6631 6631 6631 (3 of 3 match), listen -110, result -110, power-down -125
293.602 STP link halted: failed=0 busy=0 rx=57 discarded=0 dup=0 tx=57 acks=57 timeouts=0 resent=0 wmt-unsolicited=0 first=0 bytes
        mt6797-fm: link: bytes=250 events=54 unexpected=0 junk=0
```

No `command xx:` line. `insmod` rc 0; probe 3.26 s. Afterwards `rmmod` rc
0, pings 3 of 3, CONSYS and `mac` reload, Wi-Fi back with a lease, pings 3 of
3, taint 0, no warning or Oops. No signal-strength line, so no headset step.

**Analysis.** The tune command itself was answered: no `command 09` error,
and the 54 events are the 53 commands up to the tune batch (with one ROM-ready
poll) plus its empty acknowledgment, none unexpected. Then nothing came for
3 s: no "done" event and no other event. The F2 run fits the same pattern; it
only failed earlier. `-125` is the planned skip of the power-down after a
timeout; function-off and the CONSYS reload then powered the block off.

The vendor's FM interrupt hooks are empty on this platform
(`fmradio/core/fm_eint.c`: only an STP receive callback), and its own tune
fails on a missing "done" (`fm_link.c`), so a working stock tune must get
the event. The one vendor step the driver leaves out is the last of power-up:
`0x9b = 0xf9ab` (I2S transmit mode), MCU `0x81024064 = 0x14` ("enable
aon_osc_clk_cg"), `0x81024058 = 0x888100c3` ("enable FMAUD trigger") and
`0x81024054 = 0x100` ("release fmsys memory power down"). An always-on clock
gate and a memory power-down are plausible prerequisites for the DSP's
tune-done path. This is inference.

**Conclusion:** `inconclusive` for reception. The tune is accepted; its
completion is not reported without the full vendor power-up.

## Test F2c: F2b with the full vendor power-up (admitted)

The owner admitted F2c on 2026-11-05: one load, the F2b effects plus the
three changes below; anything else needs asking again.

The F2 procedure, safety and decision table, with
[0588](../../patches/proposals/0588-media-radio-mt6797-finish-the-vendor-power-up-before.patch):

- **Last power-up step:** after the fine tune, the vendor's step 11 above. It
  turns the DSP's I2S output on into CONSYS. The AFE is not set up to take it,
  so nothing reaches the codec and nothing is heard.
- **Diagnostics:** if "done" is still missing after an answered tune command,
  the driver reads `0x63`, `0x64`, `0x69` and `0x6c` once and logs them. If the
  interrupt status `0x69` D0 shows tune-done, the tune is taken as finished
  and the signal-strength log goes ahead.
- **Power-down:** it is skipped only when a command gets no answer at all, so
  a missing "done" now ends with the vendor power-down.

| Added observation | Meaning | Next |
| --- | --- | --- |
| "done" arrives, signal-strength lines follow | step 11 is needed for the tune to report | the F2 decision table |
| no "done", `0x69` D0 set | the tune finished; only the event is missing | the logged signal strength decides; then why no event |
| no "done", `0x69` D0 clear | the DSP never finished the tune | compare `0x63` and `0x64` with the vendor offline; no blind retry |

Checks: `W=1` and `checkpatch --strict` clean in the dev VM, applies to the
station tree. Not built on Buildbox yet, not run.

## F2c result (2026-11-05): it tunes, and the headset is the antenna

Run by the custodian session with the owner's admission, in the same boot as
F2b (`a22a4ca8`, image `02e045fa…`), as a module-only load. Package
`f996a919…`, built by the custodian from `74eab043`: `Image.gz`
`5229086f…` and `mt6797-consys.ko` `1797e440…` identical to the running
ones, `radio-mt6797.ko` `85d85c5b…` with the matching vermagic. Both FM files
still in RAM with the right digests. The owner's first station, in TDD mode,
channel parameter 0. Raw `dmesg`, frequency redacted, is private under
`artifacts/station-work-58/boot-1/`.

```text
950.205 STP link running: tx-seq=2 rx-seq=2 peer-ack=1 local-ack=1
950.207 WMT FM function on: result=0 reply=5 bytes 02 06 01 00 00
950.216 mt6797-fm: DSP ROM version 0: 0
        mt6797-fm: mediatek/mt6797/mt6631_fm_v1_patch.bin: 1028 bytes: 0
        mt6797-fm: mediatek/mt6797/mt6631_fm_v1_coeff.bin: 1092 bytes: 0
950.448 mt6797-fm: tune: TDD mode, parameter 0, acknowledgment length 0, done 1: 0
950.449 mt6797-fm: power-up and tune to <redacted> kHz: 0; logging for 120 s
1073.319 WMT FM function off: result=0 reply=5 bytes 02 06 01 00 00
         mt6797-fm: identity 6631 6631 6631 (3 of 3 match), listen 0, result 0, power-down 0
         STP link halted: failed=0 busy=0 rx=270 discarded=0 dup=0 tx=197 acks=270 timeouts=0 resent=0 wmt-unsolicited=0 first=0 bytes
         mt6797-fm: link: bytes=6835 events=267 unexpected=72 junk=0
```

Signal strength, one line a second:

| Time | Headset | RSSI |
| --- | --- | --- |
| t=1 to 81 | out | -97 to -98 dBm (raw about -261), one line at -92 |
| t=82 | plugged in during this second (`mt6351-sound: jack in`) | -95 dBm |
| t=83, 84 | in | -79, -74 dBm |
| t=85 to 120 | in | -72 to -75 dBm |

The stereo flag was 0 on all 120 lines. `insmod` rc 0, probe 123.1 s, no
`command xx:` line. Afterwards `rmmod` rc 0, pings 3 of 3, CONSYS and `mac`
reload, Wi-Fi back with a lease, pings 3 of 3, taint 0, no warning or Oops.
Two unrelated `one-shot WLAN BSS timeout ignored` lines from CONSYS fell in
the window.

**Analysis.**

- **The tune works with the full vendor power-up.** The only change from F2b
  is step 11, and the "done" event now arrives with `1` 0.23 s after power-up
  began. So the tune-done report depends on that step (oscillator clock gate,
  FM audio trigger or FM memory), though which part is not separated.
- **The headset cable is the antenna.** Plugging the headset in raised RSSI
  from about -97.5 to about -73.5 dBm, some 24 dB, within two seconds of the
  jack event, and it stayed there. This confirms the long-antenna path through
  the headset, the vendor default. Without a headset the receiver still sees
  the station at about -97 dBm, 14 dB above the vendor's -111 dBm search
  threshold, so there is some pickup without a headset, possibly the PCB or the
  cable-less jack; no short antenna was selected.
- **Stereo flag never set.** At -74 dBm a stereo broadcast would normally
  decode in stereo. Either the station is mono, the flag needs the audio path,
  or `RSSI_IND` D12 is not the live stereo indicator. Open.
- **72 unexpected events.** F2b had none. About 6.6 kB arrived in 72 events
  that matched no waiting command, roughly 90 bytes each, over 120 s. The
  vendor's ramp-down sets `0x63` D4, which the register map names the RDS
  mask, and the interrupt masks enable RDS, so these are probably the
  unsolicited RDS events of R8 (an RDS event with 7 groups would be 92 bytes).
  The driver did not log opcodes, so this is inference.

**Conclusion:** `confirmed` for this unit: the MT6631 FM receiver tunes a
broadcast station on mainline with the vendor sequence, and the headset cable
is the antenna. Not shown: audio, stereo, RDS, seek, or any channel other than
this one TDD channel.

## Test F3: the V4L2 radio device (admitted)

The owner admitted F3 on 2026-11-05: one load and one `fm-check` run with
the effects below; anything else needs asking again.

**Question:** does the receiver work through a standard radio device:
tune, signal strength, controls, RDS blocks, and a seek built from the
firmware's channel-quality reports?

**Code:**
[0589](../../patches/proposals/0589-media-radio-mt6797-make-it-a-V4L2-radio-receiver.patch)
turns `radio-mt6797` into a V4L2 radio receiver, `/dev/radioN`:

- **Power:** the first open runs the whole F2c sequence: attach, function on,
  power-up with the identity check, ROM query, both downloads, digital init, fine
  tune, the vendor's last step, RDS buffer threshold `0x80 = 6`, the controls,
  the tune. The last close runs the vendor power-down, function off and
  detach. Probe touches nothing, and the bring-up parameters are gone.
- **Tuner:** 87.5 to 108 MHz on the 100 kHz grid; signal strength maps RSSI
  -111 to -51 dBm onto 0 to 65535; stereo from `RSSI_IND` D12; forced mono
  through `0x75` D3 (`audmode`). The nine 64 MHz SPI-clock channels are
  still refused.
- **Controls:** mute (`0x9c`), volume (`0x7d`, 16 steps) and de-emphasis, 50
  or 75 µs, 75 by default (`0x61` D12).
- **Seek:** the vendor never uses the chip's own seek. The driver steps through
  the band, asks the firmware for each channel's quality report (`0x17`, R3)
  and applies the `fm_cust.cfg` thresholds, then tunes the first good channel.
  If none passes, or a signal interrupts it, it returns to the old channel.
- **RDS:** the unsolicited `0x0d` events (R8) become `v4l2_rds_data` blocks for
  `read()`, with the error flag from each block's CRC result and C' for version
  B groups.

[`fm-check.c`](fm-check.c) exercises it with V4L2 calls only. Public lines go
to stdout: capabilities, control results, one line a second with signal
strength, stereo and RDS block counts, and the seek's result and time. The
frequency, the station a seek finds and the decoded RDS PI and programme name
go only to a private file.

**Checks:** 0589 builds with `W=1` and passes `checkpatch --strict` in the dev
VM and applies to the station tree. `fm-check` builds static for aarch64 with
`-Wall -Wextra` and no warning (`3fced782…`, GCC 13.3, binary kept under ignored
`artifacts/fm/`). Buildbox build `5bc16e1b`, profile `mt6797-a53-station-a72`,
`BUILD_MODULES=1`, 760 patches, package `c9aa2298…`; validation passed.
`Image.gz` (`5229086f…`), config (`6b86c0b3…`), `mt6797-consys.ko`
(`1797e440…`) and `videodev.ko` (`838c4fe4…`) are identical to the running
vibrator V1 image's, so F3 is a module-only load of `radio-mt6797.ko`
(`ede6bf4e…`), which now depends on `videodev` and `mc`. Not run.

**Safety:** receive only, as F2c, with the same effects plus the RDS buffer
threshold, the control writes (mute, volume, de-emphasis, forced mono off)
and, for the seek, one quality report per channel tried, at most 205. No
antenna select, no AFE or codec change, nothing heard, no calibration, NVRAM
or partition write. The frequency, the station a seek finds and the RDS
identity stay private.

**Needs:** a package with 0589 from the same build as the running kernel (a
module-only load if `Image.gz` and `mt6797-consys.ko` match); the two FM
files in `/lib/firmware/mediatek/mt6797/`; `fm-check`; the owner's station
and the headset plugged in from the start. The owner is not needed beyond
that.

**Procedure,** one load and one run, no retry:

1. Wi-Fi associated, gateway ping, taint, `dmesg | wc -l`.
2. `insmod radio-mt6797.ko`; note the `registered /dev/radioN` line.
3. `fm-check /dev/radioN <station kHz> 60 <private file> seek`.
4. New `dmesg` lines from `mt6797-fm`, `STP link` and `WMT FM`.
5. `rmmod radio-mt6797`, three pings, CONSYS and `mac` reload, three pings,
   taint.

| Observation | Meaning | Next |
| --- | --- | --- |
| open ok, signal above 0, RDS good blocks counted, seek finds a station | the radio device works | upstream review of the tuner; the AFE input for audio |
| everything but RDS | RDS events not as R8 says, or the station sends none | log the `0x0d` events' sizes offline; check the station on another receiver |
| seek returns `ENODATA` or hits the time limit | the quality report or thresholds are not as read | decode a report offline from a `dev_dbg` run |
| stereo still 0 with strong signal | the indicator bit or a mono station | compare with another receiver |
| open fails | regression from F2c | compare its log with F2c |
| Wi-Fi fails after unload | FM power-down or RDS traffic disturbs CONSYS | record; CONSYS reload |

## F3 result (2026-11-05): the radio device works

Run by the custodian session with the owner's admission, in boot `a22a4ca8`
(image `02e045fa…`), module-only: package `c9aa2298…` checked against its
`SHA256SUMS`, `Image.gz` and `mt6797-consys.ko` identical to the running ones;
`mc.ko` `c596bcbb…` and `videodev.ko` `838c4fe4…` from the package, identical
to the running package's copies; `radio-mt6797.ko` `ede6bf4e…`;
`fm-check` `3fced782…`. Firmware still in RAM. Headset plugged in, the
owner's station. The private file (frequency, the station the seek found,
RDS PI and programme name) is kept under `artifacts/station-work-58/boot-1/`
and is not quoted here.

`insmod` of `mc`, `videodev` and `radio-mt6797`: rc 0, `registered radio0`.
`fm-check` output, apart from the per-second lines:

```text
open: ok after 0.24 s
cap: driver=radio-mt6797 card=MT6797 CONSYS FM receiver caps=01250500
tuner: FM cap=0000059d range=87500-108000 kHz audmode=1
ctrl mute=1: ok
ctrl mute=0: ok
ctrl volume=15: ok
ctrl deemphasis=2: ok
s_frequency: ok after 0.11 s
rds totals: good A=678 B=678 C=678 D=678 C'=0, bad A=0 B=0 C=0 D=0 C'=0, PI seen 678 times
seek up: ok after 0.49 s
after seek: signal=32767 stereo=0
close after 0.01 s
```

The 60 per-second lines: signal 40,413 to 43,690, mostly 42,597 (about -72
dBm); `stereo=0` and `rds=1` on every line; 48 good blocks a second, 24 in
seven of the seconds; no bad block. `dmesg`: link running and checked,
function on, `on: identity 6631: 0`, function off, `STP link halted: failed=0
... timeouts=0 resent=0`, `off: power-down 0, events=333 unexpected=0 junk=0`.
Afterwards `rmmod` rc 0, pings 3 of 3, CONSYS and `mac` reload, Wi-Fi back with
a lease, pings 3 of 3, taint 0, no warning or Oops.

**Analysis.**

- **The device works through the standard interface.** Open runs the whole
  power-up in 0.24 s, a tune takes 0.11 s, close powers down in 0.01 s with the
  vendor power-down returning 0, and all controls are accepted.
- **RDS works and R8 is confirmed.** 678 groups in 60 s is 11.3 groups a
  second, the RDS rate of 1187.5 bit/s (11.4 groups/s), with all four blocks
  of every group present and none flagged bad. The 72 "unexpected" events of F2c
  are now consumed as RDS: `unexpected=0`. That no block was bad at -72 dBm
  is plausible but also fits a firmware that drops bad groups before sending;
  which one is not separated. The seconds with 24 blocks are the 2 s event
  batches straddling a read.
- **Seek works.** It found the next station upward in 0.49 s, at about -81 dBm,
  so the quality report and the vendor thresholds are read correctly. One seek,
  upward only.
- **Stereo flag still 0**, now on two stations, both with clean RDS. A stereo
  pilot at these levels should be detected, so `RSSI_IND` D12 is probably not
  the live pilot indicator on MT6631, or it needs the audio path running. Open
  item 9.

**Conclusion:** `confirmed` for this unit: the MT6631 FM receiver works on
mainline as a V4L2 radio receiver with tuning, signal strength, controls,
hardware seek and RDS. Not shown: audio, stereo, downward seek, the nine
64 MHz SPI-clock channels, suspend.

## Test F4: why the stereo flag stays 0 (admitted)

The owner admitted F4 on 2026-11-05: one load and one `fm-check` run with
the effects below; anything else needs asking again.

**Question:** does the receiver see a stereo pilot at all, and does forced
mono or the signal level explain the flag (open item 9, R10)?

**Hypotheses:** (a) `0x75` D3 reads 1, so the receiver is forced to mono
despite the driver's write; (b) the stations are received too weakly for
stereo, so the indicator follows the vendor's blend and comes on with a
stronger signal; (c) the indicator needs something the driver does not do.

**Code:**
[0590](../../patches/proposals/0590-media-radio-mt6797-log-the-stereo-registers-and-chan.patch)
implements `VIDIOC_LOG_STATUS`: it logs `0x6c`, `0x75`, `0x61`, `0x63` and
`0x64`, then the firmware's full quality report for the tuned channel (RSSI,
PAMD, PR, FPAMD, MR, ATDC, PRX, ATDEV, soft-mute gain, delta RSSI). The
channel is not logged, only whether the report's channel field matches the
tuned one. [`fm-check`](fm-check.c) now calls it at t=5, after the last second
and after the seek (`52196287…`).

The quality report is a soft-mute tune of the same channel, as the seek does
for every channel it tries; it may interrupt RDS for a moment.

**Build:** `1c0140e1`, profile `mt6797-a53-station-a72`, `BUILD_MODULES=1`, 761
patches, package `c8213ba7…`; validation passed. `Image.gz` `5229086f…`,
config `6b86c0b3…`, `mt6797-consys.ko`, `videodev.ko` and `mc.ko` identical to
F3's, so module-only on the running image; `radio-mt6797.ko` `61a2c041…`.
Not run.

**Safety:** as F3, plus five register reads and one quality report per call,
three calls. Receive only.

**Procedure:** as F3, one load and one run, headset plugged in. If the owner
can, the device near a window and a station the owner knows is in stereo on
another receiver. The owner says which (no frequency needed): whether the
station is known to be in stereo, and where the device was.

| Observation | Meaning | Next |
| --- | --- | --- |
| `0x75` D3 = 1 | forced mono despite the write | find what sets it; fix the write order |
| `0x75` D3 = 0, stereo comes on with the stronger signal | blend by level, (b) | the indicator works; nothing to fix |
| `0x75` D3 = 0, strong signal, known stereo station, flag still 0 | (c); PR and FPAMD show what the DSP sees | compare with the audio path once it exists |

## F4 result (2026-11-05): not forced mono; signal too weak to say more

Run by the custodian session with the owner's admission, in boot `a22a4ca8`,
module-only: package `c8213ba7…` checked against its `SHA256SUMS`,
`radio-mt6797.ko` `61a2c041…`, `fm-check` `52196287…`. The owner's F3
station, headset plugged in. The owner did not say where the device was or
whether the station is in stereo. Raw output and the private file are under
`artifacts/station-work-58/boot-1/`.

`fm-check`: open 0.24 s, all controls ok, tune 0.11 s, then 60 lines with
signal 26,214 to 31,675 (about -87 dBm; F3 had 40,413 to 43,690, about
-72 dBm), `stereo=0`, `rds=0` and no RDS block at all; seek ok in 0.49 s to a
station at signal 20,752, still `stereo=0`; close 0.01 s. `dmesg`: power-up,
identity, function on and off, power-down all 0, `events=241 unexpected=0
junk=0`, link halted with no failure. Afterwards pings, CONSYS reload, Wi-Fi
and taint as in F3.

The diagnostic lines (controls in each block: not muted, volume 15, 75 µs):

| When | `0x6c` | `0x75` | `0x61` | `0x63` | `0x64` | Quality report |
| --- | --- | --- | --- | --- | --- | --- |
| t=5 | `0318` | `0000` | `1002` | `0011` | `000a` | ch matches, rssi -232, pamd -20, pr `00b6`, fpamd `0f5b`, mr 54, atdc 474, prx 92, atdev 3320, smg 3677, drssi `0013` |
| end | `0323` | `0000` | `1002` | `0011` | `000a` | ch matches, rssi -222, pamd -26, pr `0060`, fpamd `0f2b`, mr 65, atdc 1689, prx 103, atdev 4411, smg 32767, drssi `0016` |
| after seek | `030a` | `0000` | `1002` | `0011` | `000a` | ch matches, rssi -244, pamd -27, pr `0029`, fpamd `0f23`, mr 60, atdc 171, prx 109, atdev 1890, smg 32767, drssi `000d` |

**Analysis.**

- **Not forced mono, (a) rejected.** `0x75` is `0000` throughout, so D3 is
  clear, and `0x6c` D12 is 0: its low ten bits are the RSSI (`0x318` = -232,
  the same as the report).
- **The registers are as the driver set them.** `0x61` D12 = 75 µs and D1 =
  ASIP running; `0x63` D0 tune and D4 RDS on; the report's channel always
  matches the tuned one.
- **The signal was weak.** -222 to -244 raw is about -83 to -92 dBm, some 15
  dB below F3 on the same station; RDS, which decoded cleanly at -72 dBm in
  F3, got no block at all. The soft-mute gain was low at t=5 (3677, under the
  vendor's 16421) and at its maximum later. The owner says the device was in
  the same place as for F3, about 13 minutes earlier in the same boot with the
  jack in throughout. The module difference does not explain it: 0590 changes
  only the quality-report parsing, the seek's use of it and `LOG_STATUS`, not
  the power-up or tune, and the signal was already weak at t=1, before the
  first `LOG_STATUS`. Both the tuned station and the one the seek found were
  some 11 to 15 dB below F3, which points at the antenna rather than one
  station. The owner then confirmed they had moved the headset wire between
  F3 and F4: the antenna's position cost about 15 dB, and RDS with it.
- **(b) or (c) not settled.** At this level a receiver blends to mono, so the
  flag being 0 says nothing new. `pr` and `fpamd` change with the signal, but
  their meaning is not documented, so they cannot be read as pilot strength.

**Conclusion:** `confirmed` that forced mono is not the cause, and that the
headset wire's position alone moves reception by about 15 dB; `inconclusive`
on stereo. A run on a strong station, at F3's level or better and known to be
in stereo, is still needed.

## FM audio: design (2026-11-05, desk only)

The receiver's audio already leaves the DSP: power-up step 11 puts it on
CONSYS's I2S as master, 32 kHz, 16 bit (S5). The AFE has to take it in and
route it to the codec. Mainline has headphone and speaker playback through the
ADDA path ([audio record](../2026-11-01-gemini-audio-station/README.md)), and
every AFE register the vendor uses for FM is already defined in mainline
`mt6797-reg.h`; only the DAIs and routes are missing.

What the vendor programs (`sound/soc/mediatek/mt_soc_audio_6797/`:
`mt_soc_pcm_fm_i2s.c`, `mt_soc_afe_control.c`, `AudDrv_Clk.c`,
`mt_soc_afe_connection.c`):

| Step | Vendor | Mainline name |
| --- | --- | --- |
| I2S input clock | `AUDIO_TOP_CON0` D6 cleared ("I2S In clock, needed in slave mode") | `PDN_I2S` |
| Second I2S input | `AFE_I2S_CON`: slave (D2), I2S format (D3), 16 bit (D1), no LRCK inversion (D5), pad select D28 = 0 (CONSYS); enable D0 | `AFE_I2S_CON`; inputs `I_I2S0_CH1/2` (I00/I01) |
| ASRC 32 to 44.1/48 kHz | `AFE_CONN4` D30 = 0 (use ASRC); `AFE_ASRC_CON14` = `0x1b9000` (44.1) or `0x1e0000` (48); `CON15` = `0x140000`; `CON16` = `0xff5987`, `CON17` = `0x7ef4`, `CON16` = `0xff5986` then `0xff5987`; `CON13` D16 = 0 (stereo); `CON20` = `0x36000`, `CON21` = `0x2fc00`; enable `AFE_ASRC_CON0` D6 and D0; the AFE rate of the I2S block set to the output rate | `AFE_ASRC_CON0`-`CON21`, `AFE_CONN4` |
| Hardware gain 1 | `AFE_GAIN1_CON0` rate and 64 samples per step, D0 enable; `AFE_GAIN1_CUR` = 0 to ramp up; `AFE_GAIN1_CON1` = gain | `AFE_GAIN1_*` |
| Routing | I00 to O13 and I01 to O14 (`AFE_CONN13` D0, `AFE_CONN14` D1, into gain 1); I10/I11 (gain 1 out) to O03/O04 (`AFE_CONN3` D10, `AFE_CONN4` D11, ADDA downlink) and to O28/O29 (I2S DAC out) | `I_GAIN1_OUT_CH1/2`; ADDA DL mixers |
| Codec side | the I2S DAC-out path `AFE_I2S_CON1` at the output rate, 32 bit | not needed for the headphones: mainline drives the MT6351 through ADDA |
| AFE on | `AFE_DAC_CON0` D0 | already handled by the AFE driver |

MT8186's mainline `CONNSYS_I2S` DAI writes the same ASRC constants
(`0x1b9000`, `0x1e0000`, `0x140000`, `0x36000`, `0x2fc00`, `0x7ef4`,
`0xff5986`) to its own ASRC block, and MT8186 and MT8365 route
`CONNSYS_I2S` through hardware gain 1 to the downlink for a "Hostless FM"
front end. So the MT6797 work is a port of an existing mainline pattern:

1. a `CONNSYS_I2S` back-end DAI on the second I2S input with the ASRC above,
   capture only, 44.1 or 48 kHz, and the `PDN_I2S` clock as a DAPM supply;
2. a hardware gain 1 DAI with `HW_GAIN1_IN_CH1/2` mixers fed from
   `I_I2S0_CH1/2` at `AFE_CONN13`/`AFE_CONN14`;
3. a "Hostless FM" front end next to the existing hostless DAIs;
4. `GAIN1_OUT_CH1/2` inputs on the `ADDA_DL_CH1/2` mixers;
5. the DAIs registered in `mt6797-afe-pcm.c`, and an FM link in the
   `mt6797-mt6351` card.

The AFE, the card and the codec are modules on the station
(`CONFIG_SND_SOC_MT6797=m`, `_MT6351=m`), so a first audio test needs no
boot. The audio session confirmed nothing was in flight in these files and
left them to this work until the FM audio patches land.

The first audio test would open the hostless FM front end with the radio
tuned and listen on the headphones, which are the antenna as well. That makes
it the first FM test that needs the owner's ears, and also the first that can
answer the stereo question.

## FM audio: implementation (2026-11-05)

Four patches, compile-checked only:

- [0591](../../patches/proposals/0591-ASoC-mediatek-return-no-position-for-a-hostless-fron.patch):
  the shared `mtk_afe_pcm_pointer()` indexed the memory-interface array by the
  CPU DAI id, which for a hostless front end lies past its end, so a status
  query or a write on any hostless stream read out of bounds. It now returns
  position 0 for such an id.
- [0592](../../patches/proposals/0592-ASoC-mediatek-mt6797-add-the-CONSYS-I2S-input.patch):
  a `CONNSYS_I2S` capture DAI on the second I2S input, with the vendor's
  register sequence from the design table: 16-bit I2S slave from the CONSYS
  pad, the I2S block at the output rate, the ASRC settings and enable, and
  the `PDN_I2S` clock as a supply. Stop bypasses the ASRC again.
- [0593](../../patches/proposals/0593-ASoC-mediatek-mt6797-add-a-hostless-FM-path-to-the-d.patch):
  a "Hostless FM" front end and `I2S0_CH1`/`I2S0_CH2` switches on the
  `ADDA_DL_CH1`/`CH2` mixers (`AFE_CONN3` D0, `AFE_CONN4` D1). This skips the
  vendor's hardware gain 1, which only ramps the level; the receiver's volume
  control sets it instead. Smallest path first; the gain can follow if needed.
- [0594](../../patches/proposals/0594-ASoC-mediatek-mt6797-mt6351-link-the-hostless-FM-pat.patch):
  the `Hostless_FM` front end and the `CONNSYS_I2S` back end in the
  `mt6797-mt6351` card, after the existing links; the Primary Codec link and
  its jack setup are untouched, as the audio session asked.

Checks: every changed object builds with `W=1` and no warning in the dev VM,
and `checkpatch --strict` reports only the MAINTAINERS note and an alignment
that matches the file's existing link definitions. The patches apply after
0590 to the station tree.

Starting the path needs the front end in both directions with no data moved,
which `aplay` cannot do: it would wait for periods that never come.
[`fm-listen.c`](fm-listen.c) opens the radio, sets its volume and tunes, then
sets up and starts the `Hostless_FM` capture and playback streams with raw
ALSA ioctls (48 kHz, 16 bit, stereo, stop threshold above the boundary so
playback starts without data), prints the tuner's signal and stereo flag
every 5 s, then stops both and closes. Static aarch64 build `d0b66f4e…`,
kept under ignored `artifacts/fm/`.

## Test F5: first FM sound on the headphones (admitted)

The owner admitted F5 on 2026-11-05: one run with the effects below;
anything else needs asking again.

**Question:** does FM audio reach the headphones through the new path, and
in stereo?

**Effects:** reload of the audio modules (`mt6797-mt6351`,
`snd-soc-mt6797-afe`, `snd-soc-mtk-common`) from the same package; two new
mixer switches on; the radio opened and tuned as in F3; the AFE's second I2S
input and ASRC on, the ADDA downlink and the headphone output powered by the
codec as for any playback. Speakers stay off (`Speaker Switch` off), the
headphone gain stays at its minimum, -10 dB, and the receiver's volume
starts at 8 of 15, about -14 dB. Receive only; no calibration, NVRAM or
partition write.

**Hearing safety:** FM is full-scale programme audio, much louder than the
-40 dBFS tone of the audio record. The owner holds the earbuds near, not
in, the ears when it starts, and the run stops at once if it is loud or
harsh.

**Procedure,** one run, no retry:

1. Radio module loaded and the FM files in place, as in F3; headset plugged in.
2. Unload the card, AFE and common modules, then load the new ones in the
   same order as `audio-start`; set `audio-start`'s mixer list again.
3. `amixer cset name='ADDA_DL_CH1 I2S0_CH1' on` and
   `name='ADDA_DL_CH2 I2S0_CH2' on`.
4. `fm-listen /dev/radio0 <station kHz> 8 60 <private file>`.
5. The owner says what they hear: nothing, noise, the station; distorted or
   clean; mono or stereo; too loud or too quiet.
6. Switches off again, the usual unload, CONSYS and `mac` reload, pings, taint.

| Observation | Meaning | Next |
| --- | --- | --- |
| The station, clean | the FM audio path works | stereo by ear; then levels and defaults |
| Silence, both streams started | no I2S data, or the ASRC or route wrong | plan a register read of `AFE_I2S_CON`, `AFE_ASRC_CON0`, `AFE_CONN3`/`4` as its own test; no blind retry |
| Noise or wrong pitch | rate or format mismatch | check the ASRC rate and the I2S word length |
| A stream fails to start | front-end or back-end setup | `dmesg` decides |
| Warning or Oops | driver fault | stop; preserve `dmesg`; reload |

## F5 result (2026-11-05): no station heard

Run by the custodian session with the owner's admission, in boot `a22a4ca8`
(image `02e045fa…`), module-only: package `5f9d037a…` built by the custodian
from `2a628ce6`, `Image.gz` `5229086f…` matching the running image. Changed
modules `snd-soc-mtk-common` `89133c3d…`, `snd-soc-mt6797-afe` `f1d96068…`,
`mt6797-mt6351` `ab9caefb…`; `radio-mt6797` `61a2c041…`; `fm-listen`
`d0b66f4e…`. The owner's F3 station, headset in. Raw output and the private
file are under `artifacts/station-work-58/boot-1/`.

- **Module swap:** the three audio modules unloaded and loaded with rc 0; the
  AFE combined 15 DAIs (13 before), the card probed, the headphone jack input
  came back and reported the jack in. The `audio-start` mixer list applied
  without a failure; `ADDA_DL_CH1 I2S0_CH1` and `ADDA_DL_CH2 I2S0_CH2` on;
  speakers off; `Headphone Volume` 0, -10 dB.
- **`fm-listen`:** radio volume 8 and tune ok; `Hostless_FM` is card 0
  device 9; capture and playback both started; signal 19,660 to 43,690 over
  60 s, mostly about 40,000 (around -74 dBm), `stereo=0` throughout; both
  streams stopped, radio closed, rc 0.
- **`dmesg`:** the radio's usual lines (link, function on, identity, function
  off, power-down 0, `events=218 unexpected=0`), a console unblank from a
  key press, and **no line at all from the AFE, the card or the codec**
  during the stream.
- **Owner:** did not hear the station: "complete silence", no hiss and no
  noise, with the earbuds held near the ears at -10 dB. Very faint output is
  not ruled out, but the lack of even the usual power-up hiss suggests the
  headphone output may not have been powered or routed at all.
- **After:** switches off, radio unloaded, pings, CONSYS and `mac` reload,
  pings, taint 0, no warning or Oops. The new audio modules stay loaded.

**Analysis.** Both front-end directions started without an error, and the
receiver ran as in F3, so the fault is in the audio path between the
receiver's I2S and the headphones, and it is silent. Every candidate fits
the log: the receiver not driving its I2S, the AFE input or ASRC not
running, the downlink not connected, or the codec not powered. Nothing in
F5 separates them. A register and DAPM-state read during the stream does.

**Conclusion:** `inconclusive`: the path starts without an error but carries
no audible station.

## After F5: desk check of the path

Everything the driver programs matches the vendor and the AFE register
descriptions (privately held, not quoted here), so the silence is not a
misread field:

- `AFE_I2S_CON`: D0 enable, D1 word length (0 = 16 bit), D2 slave (1), D3
  I2S format (1), D5 LRCK inversion (0), D6 SRC bypass (0, use the SRC),
  D28 pad select (0 = from CONSYS, "for FM receive"). 0592 writes exactly
  this.
- `AFE_CONN3` and `AFE_CONN4` implement every input bit, I00 to O03 and I01
  to O04 included, so skipping hardware gain 1 is not the fault.
- The per-I2S engine clock gates in `AUDIO_TOP_CON1` reset to 0 (not gated);
  the vendor's only write there belongs to a different, 4-pin I2S mode.
- The receiver's I2S output: on MT6630 and MT6632 the vendor enables it with
  `0x9b` D1:0; on MT6631 its last power-up step writes `0x9b = 0xf9ab`, which
  has D1:0 set, and the driver does the same.

The ASRC has a frequency calibrator that measures the incoming I2S. The
vendor's `AFE_ASRC_CON16 = 0xff5987` turns "calibrator 2" on with
auto-restart, and its results are read-only: the period in `AFE_ASRC_CON18`
(`0x564`) and the frequency in `AFE_ASRC_CON19` (`0x568`). They tell
directly whether an I2S clock reaches the AFE from CONSYS.

## Test F5b: what the path does during the stream (admitted)

The owner admitted F5b on 2026-11-05: one run with the effects below;
anything else needs asking again.

**Question:** where does the FM audio stop: at CONSYS, at the AFE input, or
on the way to the codec?

**Code:** none new; the F5 modules stay loaded.
[`fm-afe-read.sh`](fm-afe-read.sh) reads, through debugfs only, the AFE
registers of the I2S input, its ASRC with the calibrator results, the routes
and the ADDA downlink, then lists every powered DAPM widget of the card and
the full state of the FM path's widgets.

**Effects:** as F5, once; plus debugfs reads. Earbuds out of the ears; the
owner does not need to listen, but may.

**Procedure,** one run:

1. As F5 steps 1 to 3 (modules already loaded; switches on).
2. `sh fm-afe-read.sh > before.txt` with no stream.
3. `fm-listen /dev/radio0 <station kHz> 8 60 <private file> &`; after 20 s,
   `sh fm-afe-read.sh > during.txt`; wait for `fm-listen` to end.
4. As F5 step 6.

| During the stream | Meaning | Next |
| --- | --- | --- |
| `ADDA Playback` and the codec's headphone widgets off | the playback back end never joined, which fits F5's complete silence | DPCM: the front-end playback path |
| `AFE_I2S_CON` D0 = 0, or `AFE_ASRC_CON0` D0 = 0 | the CONNSYS_I2S back end never started | DPCM: the front-end capture path |
| D0 set, `0x564` and `0x568` stay 0 | no I2S clock reaches the AFE | the CONSYS side: its I2S output or the FM audio trigger |
| D0 set, calibrator nonzero, `ADDA_DL_CH1`/`2` or `ADDA Playback` off | the downlink is not connected | the playback route |
| all on and measuring | data reaches the downlink | the ASRC output or the codec level |

## Follow-up

- [Hardware support](../../docs/HARDWARE_SUPPORT.md) row "GNSS and FM"
  links here; the [firmware](../../docs/hardware/firmware.md) FM row is unchanged
  until F1.
