# Experiment: the idle headphone noise after the first playback

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-hp-idle-noise` |
| Status | `running`: `0447` falsified on a fresh boot; a switchable restore test is next |
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

It is falsified if the noise continues after a tone once that register reads `0x4600`. It was, on
station 35, and `0447` is withdrawn.

Second hypothesis: the noise comes from one of the other registers the tone changes. Putting all of them
back after a tone stops it, and putting back groups singles it out. It is falsified if the noise
continues with all of them back; then the cause is not in a writable register these reads cover.

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

Station 35 removes `0x2096` and also `0x2026`, which stayed `0000` there. This is a ranking, not a
mechanism. Nothing here explains how a charge pump setting with the pump's
enable bit clear would couple noise. Stock's own quiet listen also came with nothing played, so stock
after playback is untested, and its idle state differs in other ways.

## Build

Buildbox-3, commit `4da5aa369ce4b2df8b1dad9db19ee029a5e7b2f1`, job `4da5aa36…-mt6797-a53-station-a72-m1`,
inventory `617668a7…`, `Image.gz` `3e637a85…`, `snd-soc-mt6351.ko` `f0988b91…`, release
`7.1.3-gemini-a53-station`. Compiled, checksums pass. Device action: none.

## Safety assessment

`0447` writes one more MT6351 audio register, to the value it read before the first power-up, after
the pump's enable bit is clear. No NVRAM, calibration, radio or eMMC writes. A kernel image change uses
the reviewed boot2 path. Swapping the codec module needs none. Stop on an oops, a hang or a loud pop.

## Associated code

- `0447`, withdrawn; in Git history. It was built at `4da5aa36`.
- [`0449`](../../patches/proposals/0449-ASoC-mt6351-test-which-idle-registers-bring-the-head.patch): test only. Default 0 changes nothing. Remove it when
  this experiment ends.
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

`0447` ran on a fresh boot instead of with the swap above; see the observations.

Second test. `idle_restore` applies when a stream ends, so it is set before the tone, and it needs no
kernel change beyond the module:

1. On a boot with no tone yet, Wi-Fi up, notices firing, owner reporting no noise: swap
   `snd-soc-mt6351.ko` for the package's and set `idle_restore=15`.
2. Tone, read, and listen for 2 minutes. Expect the read to match the values from before the tone,
   except the read-back `0x080A`.
3. If quiet, set `idle_restore=0`, tone, listen 2 minutes for the noise to come back.
4. If it does: `idle_restore` of 1, 2, 4 and 8 in turn, each with a tone, a read and 2 minutes, with a
   `0` tone between them if the noise is gone.

| Observation | Next |
| --- | --- |
| 15 quiet, 0 noisy, one group quiet | Make that restore the real power-down; remove the parameter |
| 15 quiet, 0 stays quiet | The first tone's state is not reproduced later; retest each group from a fresh boot |
| 15 noisy, registers as expected | Not these registers; hold the output on while headphones are in, or compare stock after playback |

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

**Station 35 (boot `04cc38ee`, boot2 `38116570`, package `932520bc`, `snd-soc-mt6351.ko` `f0988b91…` with
`0447`), run by the custodian, headphones in at power-on, joined at 28.65 s, associated throughout, no
restarts, CPUs 0-7:**

- Notices from 390.05 s at 30 s spacing. The owner, at about 760 s: "No noise, play".
- Tone ended 763.24 s, rc 0: "Heard, no pop". Then "ok the noise is back 1s every 30s". Key presses at
  809.41 and 839.40 s. The owner then unplugged to try another plug.
- `0x2096` read `4600` at 763.25 s and 947.34 s. The other registers of the table changed as on
  station 34, except `0x2026`, which stayed `0000`.

A second tone was not played. The notice schedule past about 840 s is extrapolated (print limit).

## Analysis

The first-playback trigger repeats: stations 33, 34 and 35 show the same order of events, on two CPU
profiles.

`0447` did not help. With the charge pump configuration at its original value, the noise still came
back, so comparing with stock's close path did not find the cause. Stock leaves the other candidates
set too, so it gives no ranking among them, and stock after playback is still untested. Registers do change with the tone, so the SoC-side branch of the reload
experiment does not apply first.

## Conclusion

`0447` is `refuted` for the named Gemini on one fresh boot. The cause is not established.

## Follow-up

- [Audio reload](../2026-11-01-gemini-audio-reload/README.md)
- If no register explains it, holding the output on while headphones are in should work around the
  noise, as the silent stream did, at a battery cost not yet measured.
