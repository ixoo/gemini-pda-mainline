# Experiment: the idle headphone noise after the first playback

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-hp-idle-noise` |
| Status | `planned`: first candidate `0447` built for test; not run on the device |
| Subsystem | audio: MT6351 headphone path |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | audio session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

The [reload experiment](../2026-11-01-gemini-audio-reload/README.md) found a burst in the headphones
every 30 s that is absent before the first playback, starts after it, stops while a stream drives the
output, and stays with the modules removed.

Hypothesis: the charge pump configuration that the first stream leaves behind opens that path.
Restoring `AFE_NCP_CFG0` to `0x4600` at power-down, as the vendor driver does, removes the noise.

It is falsified if the noise continues after a tone once that register reads `0x4600`.

## Why this candidate first

[Stock's close path](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_codec_63xx.c)
and the mainline driver both write these registers at power-up. Comparing what each leaves afterwards,
from reading the code, for the registers the tone changed on station 34:

| Register | Before tone | After tone | Stock's close path |
| --- | --- | --- | --- |
| `0x2096` `AFE_NCP_CFG0` | `4600` | `8c00` | writes `0x4600`: the one that differs |
| `0x0CF4` `AUDDEC_ANA_CON1` | `0000` | `2000` | no write, as mainline |
| `0x201C` `AFUNC_AUD_CON0` | `d021` | `c3a1` | no write, as mainline |
| `0x2020` `AFUNC_AUD_CON2` | `0000` | `000b` | no write, as mainline |
| `0x2008` `AFE_DL_SDM_CON1` | `003a` | `001e` | not compared |
| `0x2002` `AFE_DL_SRC2_CON0_H` | `0300` | `8300` | not compared |
| `0x2038` `AFE_PMIC_NEWIF_CFG0` | `9330` | `8330` | not compared |
| `0x0806` `ZCD_CON3` | `0012` | `001f` | not compared |
| `0x080A` `ZCD_CON5`, `0x2026` `AFUNC_AUD_MON0` | `3f3f`, `0000` | `3232`, `ffff` | mainline never writes them; read-back |

This is a ranking, not a mechanism. Nothing here explains how a charge pump setting with the pump's
enable bit clear would couple noise. Stock's own quiet listen also came with nothing played, so stock
after playback is untested, and its idle state differs in other ways.

## Build

Pending; see the request to the custodian.

## Safety assessment

`0447` writes one more MT6351 audio register, to the value it read before the first power-up, after
the pump's enable bit is clear. No NVRAM, calibration, radio or eMMC writes. A kernel image change uses
the reviewed boot2 path. Swapping the codec module needs none. Stop on an oops, a hang or a loud pop.

## Associated code

- [`0447`](../../patches/proposals/0447-ASoC-mt6351-restore-the-charge-pump-configuration-at.patch)
- [`pmic-audio-read.sh`](../2026-11-01-gemini-audio-reload/pmic-audio-read.sh)

## Procedure

Run by the custodian on any station boot of the same release, owner listening with the headphones in:

1. With the codec module the boot loaded, play one tone and confirm the noise with key presses. Read.
2. Remove the audio modules, load `snd-soc-mt6351.ko` from the package and the others as before.
3. Play one tone, read, and have the owner listen for 3 minutes, which is six bursts.
4. Play a second tone to check that the next power-up works. Ask about pops.

| Observation | Next |
| --- | --- |
| `2096` reads `4600`, noise stops, tone heard | Confirm once from a fresh boot of the package's image; keep `0447` |
| `2096` reads `4600`, noise continues | Not shown yet: repeat from a fresh boot, in case the state does not clear. If it stays, drop `0447` and test `CON1`, then `AFUNC`, and a Gemian listen after playback |
| `2096` reads `8c00` | The new module did not run; check what was loaded |
| Second tone silent | Revert `0447`; the pump needs its configuration another way |

## Observations

**Station 34 (boot `e1706072`, boot2 `01280137`, package `db7b42af`, A72 profile), run by the custodian,
headphones plugged in at 115.94 s, Wi-Fi joined at 67.46 s:**

- `BSS timeout ignored` first at 428.80 s, then 458.82 s. With those firing, before any tone, the owner:
  "No noise, play tone".
- Tone ended 495.32 s, rc 0. The owner: "I heard the tone, but no noise so far", then "noise now".
- Key presses at 519.97 s, near the next expected notice at about 518.8 s (extrapolated).
- Register reads at 493.08 s, 495.33 s and 525.57 s. The table above gives the differences between the
  first two. The last two match, so nothing further changes as the noise starts.
- Plugging the headphones in changed only ACCDET registers (`0x0F5E`, `0x0F64`) and raised no noise.

The values after the tone match station 33's noisy reads for `0x0CF4`, `0x201C` and `0x2020`.

## Analysis

The first-playback trigger repeats, on a second boot and a second CPU profile. That makes two boots with
the same order of events. Registers do change with the tone, so the SoC-side branch of the reload
experiment does not apply first.

## Conclusion

`inconclusive`: the candidate has not been tested.

## Follow-up

- [Audio reload](../2026-11-01-gemini-audio-reload/README.md)
- If no register explains it, holding the output on while headphones are in should work around the
  noise, as the silent stream did, at a battery cost not yet measured.
