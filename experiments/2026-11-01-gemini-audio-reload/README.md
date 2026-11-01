# Experiment: audio survives a module reload

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-audio-reload` |
| Status | `running`: reload confirmed on station 33; the 30 s noise starts at the first playback and stops during a stream; fresh-boot baseline pending |
| Subsystem | audio; MT6797 AUDIO power domain |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | audio session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

On station 31, [removing the audio modules left the domain on with its SRAM powered down, and
after a reload `aplay` succeeded in silence](../2026-11-01-gemini-audio-boot/README.md). The
inference there was that the SRAM power-down acknowledge needs the audio clocks, which the AFE
had already stopped, so the power-off timed out.

Hypothesis: with the audio clocks on `power-domain@4`, removing the modules turns AUDIO
fully off (bit 24 of `0x10006180` clear, `0x10006314` back to its off value), and after a reload
the tone is heard.

## Design

The domain gets the same three clocks `mt8183` and `mt8192` give their audio domains: the audio
bus and the two infra audio gates. `mtk-pm-domains` holds them across its power-on and power-off
sequences. That is the only change, in the device tree.

The domain still stays on while the card is loaded, because the AFE probe holds it. Letting it
idle would need a register cache as well, and is not part of this.

## Build

Buildbox-3, commit `32280cd99e6ccd88fb579d6c6867fa8a961ab004`, job `32280cd9…-mt6797-a53-station-m1`,
inventory `24857504…`, `Image.gz` `933a7d70…`, the same image as station 31. The composed station DTB
has the three clocks on `power-domain@4`. An offline compose gives a 15,175,680-byte boot image.
Device action: none.

## Safety assessment

Module removal runs the first complete AUDIO power-off by mainline, and a reload its first
power-on from that state. A stuck poll times out and reports through the existing path; a
hang is possible, so keep the console, preserve evidence and reboot. The boot image changes
through the reviewed boot2 path. At boot this adds three clock references for the
domain and should otherwise behave as station 31. No NVRAM, calibration, radio or eMMC writes.

## Associated code

- The device-tree patch in the [series](../../patches/series-a53-station).

## Procedure

Run by the custodian with the owner present and the headphones in, on a fresh boot:

1. Confirm `audio=ready` and hear a tone: no regression at boot.
2. Remove all ten modules and read `0x10006180` and `0x10006314`.
3. `/bin/audio-start`, then play a tone; the owner listens.
4. Repeat steps 2 and 3 once.
5. Separately, the noise lead: reconnect Wi-Fi and have the owner note how long after the join
   the noise is first heard. The firmware notice that repeats on this period starts about 6
   minutes after a join, so noise well before that rules it out.
6. The noise mechanism, on a fresh boot before any reload. The owner suspects the undriven output
   picks up the noise. With the headphones in, Wi-Fi up and the noise present, compare 60 s idle, a
   silent stream for 90 s, and 60 s idle again. If it stops only during the stream, the idle output
   state is the mechanism and the fix is in audio, whatever the source is.
7. The closest mainline gets to the stock idle state: with all ten modules removed and bit 24 of
   `0x10006180` clear, Wi-Fi up and the headphones in, listen for 90 s. The output is still undriven.
   If the noise goes, our loaded idle state matters; if it stays, the undriven line or Wi-Fi does.

| Observation | Next |
| --- | --- |
| Bit 24 clear after removal, tone heard after reload, twice | Record; reload is safe for development |
| Domain fully off, reload silent | The cause is elsewhere; read what differs |
| Same half-off state | These clocks are not the acknowledge clock; find which is |
| Hang at removal or reload | Stop, preserve evidence, revert the patch |

Added after the first results on station 33, to find what the first playback leaves behind, using
the read-only [`pmic-audio-read.sh`](pmic-audio-read.sh):

8. On the current boot, with the noise present: read with the modules out, then read again after
   the reload and after its tone.
9. Now that the noise is present, run step 6 on the reloaded card.
10. On the next fresh boot, with the headphones in: listen for 60 s and read, play one tone and read,
    then read again 30 s later while the owner says when the noise starts.

| Observation | Next |
| --- | --- |
| Bits differ after the tone and match the noisy read | Clear those in the driver's power-down, one candidate at a time |
| Nothing differs, noise follows the tone again | Look on the SoC side: pins and clocks to the PMIC |
| No noise after the tone on the fresh boot | The tone is not the trigger; station 33 was a coincidence |

## Observations

**Interim, station 33 (boot `a4984df3`, boot2 `857a19ae`, package `24857504`), run by the custodian,
owner listening with the headphones in from power-on:**

- Idle from boot to about 790 s: no noise. That includes 14 `BSS timeout ignored` lines at 30 s
  spacing from 388 s to 783 s, and a replug (`jack out` 703.64 s, `jack in` 705.86 s) followed by a
  90 s listen. All four bias levels off, `HPL Power` and `HPR Power` off, `0x10006180` =
  `0x2B00005E`, `0x10006314` = `0x3330000D`.
- Tone at 799.67 s, `aplay` rc 0, heard. Those two registers were unchanged afterwards.
- The owner, asked after the removal: the noise is back, it started "Right after the tone", and it
  is the same 1 s every 30 s.
- Removal at 815.40 s: no `rmmod` failed, `0x10006180` = `0x2A00005E` (bit 24 clear), `0x10006314`
  = `0x3330FF12`, the off value. No hang, not tainted, Wi-Fi associated.
- With all modules removed and AUDIO off, the owner still hears the noise.

Reload, same boot, Wi-Fi associated on channel 40 throughout, not tainted at any read, no hang, no
`rmmod` failure:

| Time (s) | Step | `0x10006180` | `0x10006314` | Owner |
| --- | --- | --- | --- | --- |
| 815.40 | Removal 1 | `0x2A00005E` | `0x3330FF12` | |
| 931.31 | Reload 1, `audio-start` `ready`, jack in at 931.617 | `0x2B00005E` | `0x3330000D` | |
| 935.52 | Tone, rc 0 | unchanged | unchanged | "Heard it" |
| 957.66 | Removal 2 | `0x2A00005E` | `0x3330FF12` | |
| 982.36 | Reload 2, `audio-start` `ready` | `0x2B00005E` | `0x3330000D` | |
| 986.58 | Tone, rc 0; jack on, ping 2/2 | | | "Heard it" |

Noise, same boot, after three tones and the reloads, with the owner pressing a key at each burst
(first line of each press, by a small logger):

- Presses at 1167.58, 1197.73, 1227.59 and 1257.62 s, a period of 30.0 s to within 0.15 s.
- Silent stream 1278.57-1368.59 s, `aplay` rc 0, `HPL Power` and `HPR Power` on: no press, where the
  period predicts three. The owner: "now it is really silent", "it works".
- Presses resume at 1407.63 and 1437.62 s, `HP Power` off. The slot at 1377.6 s has no press, about
  9 s after the stream, but the custodian was speaking to the owner then, so it may be a miss.
- `BSS timeout ignored` printed last at 838.48 s (print limit). Extrapolated by the custodian over 12
  cycles, it falls about 0.85 s after each press, including reaction time.
- No pop was reported at the stream's start or end; this was not asked specifically.

[`pmic-audio-read.sh`](pmic-audio-read.sh) at `a13a5aab` ran in 0.2 s per read, 141 lines, with no
format stop. Selected registers, all after playback:

| Register | Loaded, idle, noise | During stream, no noise | Modules out |
| --- | --- | --- | --- |
| `0x0CF2` `AUDDEC_ANA_CON0` | `f400` | `f46f` | `f400` |
| `0x0CF4` `AUDDEC_ANA_CON1` | `2000` | `2000` | `2000` |
| `0x0CF6` `AUDDEC_ANA_CON2` | `0004` | `0005` | `0004` |
| `0x0D04` `AUDDEC_ANA_CON9` | `1155` | `a255` | `1155` |
| `0x201C` `AFUNC_AUD_CON0` | `c3a1` | `c3a1` | `c3a1` |
| `0x2020` `AFUNC_AUD_CON2` | `000b` | `000b` | `000b` |
| `0x0D1C` `AUDENC_ANA_CON10` | `00f0` | `00f0` | `0000` |
| `0x0D1E` `AUDENC_ANA_CON11` | `080f` | `080f` | `0000` |
| `0x0F48` `ACCDET_CON1` | `0004` | `0004` | `0000` |

Two idle reads 288 s apart differ only in the uptime line. The noise was not asked about at the
modules-out read; it was reported with modules out after removal 1, with no register read then.

**A72 boot `7dd24578` (image `e99adaa3`, package `af871fff`, no `0445`), run by the custodian:** the
owner reports the noise here too. Headphones out at power-on, `jack in` at 240.76 s, one tone at
257.03 s, rc 0, heard in both ears. When the noise started was not asked, so this boot neither
supports nor contradicts the first playback as the trigger. It does show the noise does not need
`0445`.

## Analysis

The hypothesis holds on both pairs: with the clocks on the domain, AUDIO powers fully off on
removal, and the tone is heard after a reload.

The noise is still interim.

On this one boot the noise was absent before any playback and present from just after it, and it
stayed with the AFE off and the modules gone. So the loaded idle state and the AUDIO domain are not
what carries it, and playing once is the trigger. This also fits station 31, whose first report came
after a tone played with the headphones out, and the quiet stock listen, where nothing had played.
Wi-Fi remains the likely source from station 31; on this reading playback opens the path it reaches
the headphones through.

A driven output stops the noise, which supports the owner's reading: the idle output picks it up, and
the source is outside the audio path. "It's like before we were picking electrical noise", as they
put it. The stream changes the path, not the source: nothing here shows that Wi-Fi stopped. The
timing fits a beacon-window event, but the phase rests on an extrapolation.

The ACCDET setup looks excluded. Removal clears it, and the noise was reported with the modules out,
though that report and the read showing it cleared came from different removals.

These reads cannot say what the first tone changed, because all of them follow a tone. They show
which values persist through idle and removal, including all three candidates below. That needs
the fresh-boot baseline in step 10.

Inference: the first stream changes state in the MT6351, which is outside the AUDIO domain and which
removal does not reset. The driver's power-up writes registers that its power-down does not restore:
`AUDDEC_ANA_CON1` stays `0x2000`, which the code comments as the output stability enhancement, and
`AFUNC_AUD_CON0` and `AFUNC_AUD_CON2` keep their values. Those are candidates from reading the code,
not measurements. The change could also be a bit that was set before Linux and that the first stream
clears.

## Conclusion

`confirmed` for the named Gemini, Linux 7.1.3 and package `24857504`: reload is safe for development,
with two heard removal and reload pairs on one boot. The noise stops while a stream drives the
output; one silent stream on one boot. What the first tone changes is not established.

## Follow-up

- [Audio at boot](../2026-11-01-gemini-audio-boot/README.md)
