# Experiment: speakers, headphones and microphones through UCM

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-08-gemini-audio-ucm` |
| Status | `planned`: profile written; not run on the device |
| Subsystem | audio: card profile for PipeWire |
| Device variant | named Gemini PDA (MT6797X), Arch card root |
| Date(s) | 2026-11-08 |
| Investigator(s) | audio session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

The owner wants the speakers as the default output and the microphones as the input. The
[Arch root](../2026-11-06-gemini-arch-root/README.md) has one PipeWire sink, on the headphones,
with no profile for the card.

Hypothesis: an ALSA UCM profile with three devices (Speaker, Headphones with the `Headphone Jack`
control, and Mic) is read by `alsaucm`, and each device's sequence sets the mixer to play on that
output or capture from the microphones. With it, WirePlumber can use the card itself: one sink with
a speaker and a headphone port, switching on the jack, and one source.

It is falsified if `alsaucm` does not find or parse the profile, a device's sequence leaves the
mixer wrong, or a tone is not heard on the selected output.

## Design

- [`HiFi.conf`](ucm2/Gemini/HiFi.conf), and its entry,
  [`mt6797-mt6351.conf`](ucm2/conf.d/mt6797-mt6351/mt6797-mt6351.conf). The entry's directory
  assumes the card's driver name is `mt6797-mt6351`; the test prints it.
- The [card routing](../../patches/proposals/0399-ASoC-mt6797-add-the-Gemini-speaker-amplifiers.patch)
  feeds the AW8736 inputs from the headphone outputs, as stock's `OpenSpeakerPath` does. So both
  outputs use PCM 0, and they differ only in `Speaker Switch` and `Headphone Switch`. When the
  speakers play, a plugged-in headphone gets the same signal, and `Headphone Volume` sets both levels.
- `Headphone Volume` stays at 0, −10 dB, the only tested value. Volume is PipeWire's software volume.
  The amplifiers' gain is fixed by their mode (3) at power-up, and they are enabled only while a
  stream plays.
- Headphones have the higher priority, so with the jack in they are selected; the speakers are
  the default otherwise.
- The microphones are AIN0 and AIN2 at 18 dB PGA, the tested capture setting. Which physical
  microphone each one is, is not established.

## Safety assessment

Mixer writes only, through the sequences, and quiet tones: no kernel, NVRAM, calibration, radio or
eMMC change. The test uses a copy of the UCM tree in `/tmp` through `ALSA_CONFIG_UCM2` and installs
nothing. Speaker loudness at full scale is not measured, so the test uses the −40 dBFS tone at the
minimum gain. Stop on a loud or distorted speaker.

## Associated code

- [`ucm-test.sh`](ucm-test.sh): device test, root.

## Procedure

Run by the custodian on the card root, owner present, headphones out for the speaker tone and in for
the headphone tone:

1. `ucm-test.sh PROFILE_DIR TONE`, with `PROFILE_DIR` holding this experiment's `ucm2` tree and
   `TONE` the −40 dBFS 48 kHz stereo tone used before.
2. The owner says where each tone is heard.

| Observation | Next |
| --- | --- |
| Profile listed, tones on the right outputs, capture not silent, switches as expected | Hand the profile to the Arch root; WirePlumber uses the card |
| No profile found | Move the entry to the driver name `/proc/asound/cards` shows |
| A sequence fails | Fix the control name or value from `run.log` |
| Speaker tone silent with `Headphone Switch` off | The speakers need the headphone pin; enable both in the speaker sequence |

## Observations

Before any UCM test, on card-27 (boot `58bcf387`, station-work-98 kernel), run by the custodian. Speakers
enabled by hand through PipeWire's single headphone sink: `Speaker Switch` on, `Headphone Volume` 0, sink
volume 0.25. The owner first reported sound on the left speaker only. Both amplifier enables (GPIO243/244)
were owned by their amplifiers and high while playing. With the left and right tones, then music, the
owner: "all sounds ok". So both speakers work on this kernel; the first report was not a fault.

## Analysis

None yet.

## Conclusion

`inconclusive`: nothing here has run.

## Follow-up

- [Gemini audio](../../docs/hardware/gemini-audio.md)
