# Experiment: speakers, headphones and microphones through UCM

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-08-gemini-audio-ucm` |
| Status | `running`: profile confirmed on card-31; speaker volume cap pending |
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
- Device comments are the names the owner expects to see in the desktop's audio panel:
  "Speaker", "Headphones" and "Mic".
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

**card-31 (boot `242ba06e`, station-work-100 kernel), run by the custodian with the owner's PipeWire
stopped**, the steps of `ucm-test.sh` by hand from a copy of the profile made before the device comments
were renamed. `/proc/asound/cards` gives the driver name `mt6797-mt6351`, so the entry directory is right.

- `alsaucm` lists the `HiFi` verb and the Speaker, Headphones and Mic devices, with `PlaybackPCM` on
  device 0, `CapturePCM` on device 3 and `JackControl` `Headphone Jack`.
- Speaker, jack out: only `Speaker Switch` on; −50 dBFS tone three times, rc 0. The owner: "yes it worked".
- Headphones, jack in: only `Headphone Switch` on. The owner: "yes heard the tone only in headphones".
- Mic: both microphone switches on, `PGA Volume` 3,3; 2 s capture, rc 0, RMS −40.0 and −39.1 dBFS. The
  owner was not asked to judge it.
- Setting the verb again turns every switch off; `PGA Volume` stays 3,3.
- Speaker ladder, 1 kHz tones straight to the PCM, each twice, owner asked after each: clean at −55, −50,
  −45, −40, −35 and −30 dBFS.

Before this, on the same card with the manual sink, the owner found YouTube saturates the speakers at
100 % stream volume, and 55 % is the most without saturation, at a sink volume of 0.35. Both are the
desktop's figures. If both are PipeWire's cubic volumes, that is about −43 dB.

Same card and setup, 2 s sines on both channels straight to the speaker PCM, each twice, levels chosen by
halving, owner's words:

| Frequency | Levels (dBFS) and owner |
| --- | --- |
| 100 Hz | −40, −25, −15: not heard |
| 200 Hz | −40, −25: "nothing"; −20: "rattly"; −15: "rattly" |
| 400 Hz | −40: "nothing"; −25, −20, −15: clean |
| 1 kHz | −25, −15: clean, and −55 to −30 clean in the ladder |

## Analysis

The hypothesis holds: the profile is found, each device's sequence sets only its own switches, and each
tone plays only on its own output.

Speaker saturation is not fixed by the profile. `Headphone Volume` is already at its minimum, and nothing
lower exists in hardware. A 1 kHz sine is clean at −30 dBFS, yet music distorts near −43 dB if the volume
figures are cubic. Inference: the distortion depends on frequency, such as bass overdriving the small
speakers, which a 1 kHz tone does not show. Low-frequency tones test that.

They point that way: 200 Hz rattles as soon as it is audible, and 400 Hz and 1 kHz stay clean to −15 dBFS.
So a level cap alone does not help, and the speaker needs the bass removed, a high-pass somewhere between
200 and 400 Hz; the exact corner is not measured. The levels do not fully fit the YouTube figures: on the
cubic reading, music's bass would sit well below −20 dBFS when it saturated. So whether the high-pass
removes the saturation the owner hears needs a listen with music. Stock's kernel does not use the AFE's
downlink IIR, so stock's speaker compensation, if any, is in its closed audio HAL.

The speakers and headphones share one PCM and one DL path, so any filter on that path also takes the
bass out of the headphones, unless it follows the selected output.

## Conclusion

`confirmed` for the profile on card-31: speakers, headphones on the jack and the microphones work through
UCM. Not established: a safe maximum speaker level for music.

## Follow-up

- [Gemini audio](../../docs/hardware/gemini-audio.md)
