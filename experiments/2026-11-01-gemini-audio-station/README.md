# Experiment: first audio on the development station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-audio-station` |
| Status | `running`: card binds and AUDIO powers on (station 29); no tone played yet |
| Subsystem | audio: MT6797 AFE, MT6351 codec, AW8736 amplifiers |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | audio session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

This is the next step of the
[audio runtime sequence](../2026-10-04-gemini-audio-re/README.md#first-runtime-sequence).
With `0407`-`0409` on the station kernel and the audio modules loaded over SSH,
the card binds, a −40 dBFS 48 kHz tone is audible in the headphones at −10 dB
headphone gain, and a 2 s capture from AIN0 and AIN2 is not silent.

It is falsified if the card does not bind or the tone is not heard. The
speakers are a separate opt-in step after the headphones pass.

## Why the audio-card candidate was not booted

The `9cf7001f` package (`mt6797-a53-audio-card-compile`) compiled and its DTB
was correct. Source review before any boot showed it could not have answered
the question:

1. **The card could not bind.** `0399` routes through the amplifier widgets, but
   nothing added the amplifiers to the card. `snd_soc_dapm_add_routes()` returns
   `-ENODEV` and `snd_soc_bind_card()` gives up, so there is no card at all,
   headphones included. `0407` fixes this.
2. **The station has no AUDIO domain.** The station registers only the CONN domain
   through `mtk-pm-domains`, with `MTK_SCPSYS` off, so the AFE would defer forever.
   `0408` adds the domain and `0409` uses it.
3. **No tools.** The RAM root has only busybox, and a live Gemian check recorded no
   `amixer`. [`build-alsa-tools.sh`](build-alsa-tools.sh) builds static tools.
4. **The mixer path was closed.** The draft test script set none of
   `ADDA_DL_CH* DL1_CH*`, `HPL/HPR Mux` or `UL1_CH* ADDA_UL_CH*`, so no route
   reached the codec. [`audio-test.sh`](audio-test.sh) sets them.

`0397` also changed. Its `mt6797.dtsi` hunk did not apply on the station tree,
and a fuzzy `patch` silently put the codec node inside a pinctrl group. The node
now goes before `rtc`, whose context both trees share.

## Provenance and environment

- Kernel: Linux 7.1.3, profile `mt6797-a53-station`, audio as modules
  ([fragment](../../configs/gemini-a53-station.fragment)).
- Tools: alsa-lib and alsa-utils 1.2.12, static, not in Git.
- AUDIO domain values: the `mtk-scpsys` entry for the same domain.

## Build

| Item | Value |
| --- | --- |
| Input commit | `70d0a621810665291b79f3e9a1716ef2d343567b` |
| Buildbox job | `70d0a621…-mt6797-a53-station-m1` on Buildbox-3 |
| Package inventory | `f4dec3d3…`, 126 DTBs, checksums pass |
| `Image.gz` | `8ef83b55…` |
| Config | `b4a26966…`; `SND`, `SND_SOC`, the AFE, card, codec and `AW8738` are all `m`; `MTK_SCPSYS` stays off |
| Device action | None |

The composed `mt6797-gemini-pda.dtb` decompiles to `power-domain@4`, the AFE on
that domain with `status = "okay"`, `audio-aux-devs` with two phandles, both
`awinic,aw8736` nodes and the `mt6351-sound` child.

The ALSA tools built on Buildbox-2 from checksummed alsa-lib and alsa-utils
1.2.12: `amixer` `15b00b10…` and `aplay` `6fa19355…`, both statically linked and
checked with `file` and `readelf`, never yet run. `audio-test.sh` has not run
anywhere. The bundle is not in Git.

`modules/load-order` follows `modules.dep`: `snd`, `snd-timer`, `snd-pcm`,
`snd-pcm-dmaengine`, `snd-soc-core`, `snd-soc-mtk-common`, `snd-soc-mt6351`,
`snd-soc-aw8738`, `snd-soc-mt6797-afe`, `mt6797-mt6351`.

## Safety assessment

The modules are not loaded at boot. The station boots as before, except that
`power-domain@4` is registered with no power-control write (`KEEP_DEFAULT_OFF`).

Loading the modules admits:

- the first AUDIO power sequence by `mtk-pm-domains`, not yet run by mainline;
- AFE and MT6351 register writes through DAPM;
- GPIO243/244 driven low at amplifier probe, pulsed only with `Speaker Switch` on.

`Headphone Volume` 0 is −10 dB (register `0x12`, inverted control). The codec
sets 0 dB briefly before ramping to it, and the tone is −40 dBFS. There are no
calibration, NVRAM, radio or eMMC writes. Stop on an oops, a bus hang or a domain
error, and return only through the reviewed recovery path.

## Associated code

- [`audio-test.sh`](audio-test.sh): device test, root. It stops on a wrong release,
  a refused control or a missing card, and closes the path on exit.
- [`build-alsa-tools.sh`](build-alsa-tools.sh): Buildbox only.
- `0395`-`0399`, `0401`, `0403`, `0404`, `0407`-`0409`.

## Procedure

Run by the custodian, in one boot:

1. Boot the station package and copy the bundle to `/tmp/audio`.
2. Run `audio-test.sh` with headphones attached; the owner listens for the tone.
3. Only if that passes, run `TEST_SPEAKER=1 audio-test.sh` with the device on a surface.

| Observation | Next |
| --- | --- |
| Card, tone and capture | Record; speaker; then jack and trim |
| Exit 2, a module load failed | Read the error; fix offline |
| Exit 3, no card | `dmesg` names the failed route, clock or domain |
| Card but silent | Compare DAPM and PWR_STATUS; do not raise the gain |
| Bus hang at load | The domain sequence is wrong; stop and recover |

## Observations

No audio boot yet. One read-only SPM read on station 27 (boot `778ff91c`), with no
audio in that kernel:

| Register | Value |
| --- | --- |
| `PWR_STATUS` `0x10006180` | `0x2A00005E` |
| `PWR_STATUS_2ND` `0x10006184` | `0x2A00004E` |
| AUDIO `PWR_CON` `0x10006314` | `0x3330FF12` |

The same read found no `amixer`, `aplay` or Python in the RAM root.

**Run 1, station 29 (boot `feb2831c`, package `70d0a621`, `Image.gz` `8ef83b55…`),
run by the custodian:**

- Wi-Fi before audio load matched station 28: join, ping 10/10, reconnects 10/10.
- All 10 modules loaded. Card 0 is `mt6797mt6351`, playback device 0, capture device 3.
  Both amplifiers, the codec and the AFE probed. No hang, oops or warning.
- AUDIO powered on: `0x10006180` `0x2A00005E` to `0x2B00005E`, `0x10006184`
  `0x2A00004E` to `0x2B00004E`, `0x10006314` `0x3330FF12` to `0x3330000D`.
- `audio-test.sh` stopped at its first mixer call (exit 1), so **no tone played** and
  no capture ran. The owner heard nothing, as expected.

Two script bugs, both fixed since:

- `amixer sset` takes simple names (`Speaker`), not `Speaker Switch`. It now uses
  `cset name=` with the exact control names, which run 1 listed.
- The exit trap ran `cat run.log >&2` with stderr on that same file, and busybox
  `cat` does not refuse. The log filled the 1 GiB RAM root until the custodian
  truncated it. The trap now writes one line to the original stderr.

**Run 2, same boot, script `3809057f`:** every mixer setting was accepted, then
`aplay` hit a NULL dereference at offset 0x10 in `mtk_memif_set_rate_substream()`
during `HW_PARAMS`. Nothing was played. The kernel was tainted, `aplay` stuck and
reading the PCM status appeared to hang. Wi-Fi stayed associated.

## Analysis

Run 1 confirms that the card binds with `0407` and that `0408`/`0409` power AUDIO
through `mtk-pm-domains` without a hang. It says nothing about sound yet.

Run 2 is a machine driver bug, not a hardware result. `COMP_DUMMY()` leaves a front
end's codec array empty, but the probe writes the codec node through it anyway. In
the built module `playback_2_codecs` and `playback_1_platforms` have the same address
(`0x1b8`, from `nm`), so Playback_1 bound the MT6351 as its platform and the lookup of
`mtk-afe-pcm` returned NULL. `0411` skips links with no codec entries.

Before load, bit 24 is clear in both status registers, so the loader leaves AUDIO off.
`KEEP_DEFAULT_OFF` therefore matches the hardware, and loading the modules is a
real off-to-on transition, not an adoption. Inference: the low bits of `PWR_CON`
read as isolated, in reset and clock-disabled, with bits 8-15 set. That fits the
SRAM power-down and acknowledge masks in `0408`, but it does not prove the
sequence works.

## Conclusion

`inconclusive`: nothing here establishes hardware behavior.

## Follow-up

- [Gemini audio](../../docs/hardware/gemini-audio.md)
