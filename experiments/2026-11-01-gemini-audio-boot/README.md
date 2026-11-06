# Experiment: audio ready at station boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-audio-boot` |
| Status | `completed`: audio ready at boot on station 31; a module reload silences playback; 30 s noise follows Wi-Fi |
| Subsystem | audio; station RAM root |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | audio session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

With the audio modules and ALSA tools in the RAM root, a station boot reaches
`audio=ready` in `/run/station/status` with Wi-Fi unchanged, and plain
`aplay FILE` plays through the headphones at the minimum gain with no setup.

It is falsified if the status is anything else, Wi-Fi changes, or the tone is not
heard. Two more things this boot measures:

- whether the AUDIO domain turns off when idle, or stays on after load (battery);
- whether the card's first power-up raises a false jack interrupt, which the
  [jack experiment](../2026-11-01-gemini-jack-detect/README.md) left open.

## Design

No kernel change: modules stay modules, as [`0395`](../../patches/proposals/0395-ASoC-aw8738-add-the-AW8736-compatible.patch)
onward already build. The RAM root gains:

- [`audio-start`](../2026-10-30-mainline-dev-station/initramfs/audio-start): loads the
  ten modules in `modules.dep` order and sets the mixer. Init records its one-word result
  and carries on if it fails, like every other step;
- `amixer`, `aplay`, `arecord` and `/usr/share/alsa`, from
  [`build-alsa-tools.sh`](../2026-11-01-gemini-audio-station/build-alsa-tools.sh), now
  compiled for that path.

The default mixer is deliberately cautious. Speakers and microphones are off, and gains
are at the minimum, so a stray `aplay` cannot be loud. The speakers need
`amixer cset name='Speaker Switch' on`. Nothing switches between speakers and headphones
on a jack event yet.

Since the [FM radio](../2026-11-05-gemini-fm-radio/README.md) path, `audio-start` also switches
`ADDA_DL_CH1 I2S0_CH1` and `ADDA_DL_CH2 I2S0_CH2` on when the kernel has them. They carry nothing
unless the Hostless FM PCM runs.

## Provenance and environment

- Kernel: any station package with `0415`-`0417`; modules must come from the same package.
- Tools: `amixer` `c8583ead…`, `aplay` `df03d8fa…`, static, on Buildbox-2, not in Git.

## Offline check

`compose-station.py` with package `b3cfdeb6` and the retained parent RAM root produces a boot
image of 15,171,584 bytes (station 30: 13,541,376), inside the 16 MiB partition with about
1.6 MiB left, and passes its LK checks. The RAM root holds `audio-start`, the tools, the
configuration and all ten modules. This composition was not flashed. Device action: none.

## Safety assessment

Every boot now loads audio, which runs what stations 29 and 30 already ran by hand:
the AUDIO power-on, AFE and codec probe, GPIO243/244 driven low, and the ACCDET EINT. A
hang there would stop this boot before `exec init`, so before SSH and the console shell.
That has not been seen in any run. Recovery is the usual one, Gemian on the primary boot
with the owner selecting the slot, and boot2 is overwritten only through the reviewed path.
No signal is produced until a stream runs. No NVRAM, calibration, radio or eMMC writes.

## Associated code

- [`audio-start`](../2026-10-30-mainline-dev-station/initramfs/audio-start), the station
  [`init`](../2026-10-30-mainline-dev-station/initramfs/init) and
  [`build-station-initramfs.py`](../2026-10-30-mainline-dev-station/build-station-initramfs.py).

## Procedure

See the request to the custodian; run on one boot with the headphones out at power-on:

1. Read `/run/station/status`, the cards, the `mt6351-accdet` count and `PWR_STATUS`.
2. Confirm Wi-Fi as on the previous station.
3. Play the tone with the headphones out; read the count and `PWR_STATUS` again.
4. Plug in, play the tone, and let the owner listen. Read `PWR_STATUS` after 30 s idle.

| Observation | Next |
| --- | --- |
| `audio=ready`, tone heard, Wi-Fi unchanged | Record; audio is usable after every boot |
| A `-failed` status | Read the status word and `dmesg`; fix offline |
| No SSH after boot | Recover; move audio after the shell starts |
| AUDIO stays on when idle | Find what holds it; measure the cost |
| Interrupt at the first tone with the headphones out | False EINT: read the level instead of toggling |

## Observations

**Station 31 (boot `24465562`, boot2 `293a0dbc`, package `b36b2f7f`, `Image.gz` `933a7d70`), run
by the custodian, owner present, headphones out at power-on:**

- `/run/station/status` holds `audio=ready`; card 0 present at 24.5 s; SSH with no delay;
  `mt6351-accdet` count 0; CPUs 0-7; not tainted.
- Wi-Fi joined channel 40 through `wifi-up.sh`, signal -61 dBm, ping 5/5, and 3/3 afterwards.
- Tone with the headphones out: `aplay` rc 0, count stayed 0, jack off.
- Owner plug: `jack in` at 308.44 s, count 1. Three tones at the minimum gain, rc 0 each, count
  stayed 1. The owner: "Heard in both ears".
- `0x10006180` = `0x2B00005E` and `0x10006314` = `0x3330000D` in every reading: before any tone,
  after it, and after 30 s idle.

Not tried on this boot: speakers, microphones.

Same boot, with battery status `Not charging`, USB attached and Wi-Fi associated, 60 one-second
samples of `current_now` in the units sysfs reports:

| State | Mean | Min | Max | `0x10006180` |
| --- | --- | --- | --- | --- |
| Loaded | 339.35 | -1091 | 1818 | `0x2B00005E` |
| All ten modules removed | 163.6 | -1818 | 2182 | `0x2B00005E` |
| Loaded again | 490.817 | -1454 | 2182 | `0x2B00005E` |

Removal raised no error in `dmesg`, and `0x10006314` went from `0x3330000D` to `0x33300F0D`.
Afterwards `audio-start` printed `ready`. Playback after that was not tried.

The owner also reports low noise in the headphones for about 1 s every 30 s, since plugging them
in. The custodian found a `WLAN BSS timeout ignored` log line exactly every 30 s, and no audio or
ACCDET interrupt on that cycle. A `jack out` at 554.02 s, before the removal, was the owner
unplugging. No noise has been reported with the headphones out.

Read at 935.8 s, headphones out, reloaded, no stream: `0x10006314` = `0x3330FF0D`, the jack off,
all four DAPM bias levels off, no widget on, and `HPL Power` and `HPR Power` off.

Noise, owner listening with the headphones in, on the reloaded card:

| Condition | Owner |
| --- | --- |
| Baseline | "Yes, still there" |
| Wi-Fi disconnected for 90 s, 3463.9-3554.1 s | "no noise" |
| Wi-Fi reconnected, next 90 s | "Yes, it's back" |

With the noise present at 3125.9 s the jack read on, all bias levels off, and no widget on.

Playback on the reloaded card: three tones at 5788.94-5796.99 s, `aplay` rc 0 each. The owner:
"Silence". `0x10006314` stayed `0x3330FF0D`, nothing in `dmesg`, not tainted.

## Analysis

The hypothesis holds. Plain `aplay` plays with no setup, every boot reaches `audio=ready`, and
Wi-Fi is unchanged.

**The first-power-up false interrupt is ruled out for this case.** This boot took the card
through load and a first tone with the headphones out and raised nothing, then saw the first
plug. So the 156 s event on station 30 was most likely the owner's plug, too.

**AUDIO stays on from load.** Bit 24 is set in every reading (`0x2A…` before load on stations 27
and 29), and `PWR_CON` reads powered. The reason is in the mainline driver:
`mt6797_afe_pcm_dev_probe()` calls `pm_runtime_get_sync()` with no matching put until removal,
so the domain and the AFE clocks never idle. Inference: simply dropping that hold is unsafe, because
the AFE regmap has no cache, and a mixer write with the domain off would reach an unpowered
block. Letting it idle needs a register cache, as `mt8183` has, and that needs its own test.

**The cost did not show up.** The two loaded means differ from each other by about as much as they
differ from the unloaded one, and each range spans 3,000-4,000, so this is within the noise. By the
decision rule, we leave it. That bound is weak: it was taken on USB with Wi-Fi up.

**Removal does not turn AUDIO off.** The status bit stayed set. In `PWR_CON` the SRAM power-down
bits (8-11) are set, but their acknowledge bits (12-15) are not, and they were all set in the real
off state before load. Inference: `scpsys_sram_disable()` timed out waiting for the
acknowledge, possibly because the AFE clocks were already off, so `scpsys_power_off()` gave up
with no message and the domain stayed on with its SRAM bits set. Any patch that lets the domain
idle has to fix this first. By 935.8 s, after the reload had turned the AFE clocks back on, the
acknowledge bits had appeared too, which fits the clock reading. So the reloaded card sits with its
domain on and its SRAM powered down until a reboot.

**So a module reload silently breaks playback until a reboot.** `aplay` reports success and nothing
is heard. Inference: the SRAM state is the cause; one on/off pair of boots would prove it. A normal
boot never unloads audio, so this affects development, not use. A likely fix is giving
`power-domain@4` the audio clocks, so they run during its power-off, as other MediaTek SoCs do;
see the [reload experiment](../2026-11-01-gemini-audio-reload/README.md).

**The headphone noise follows Wi-Fi**, on one off/on sequence, and is audible with the HP path reading
off. The codec is not holding it on, so this is coupling from the radio or its supply, not an
audio driver fault. Whether stock Gemian has it too is not known yet. The 30 s rhythm matches the
`BSS timeout ignored` line, which is only a matching period so far.

On stock Gemian (boot `a0b54f1d`, kernel 3.18.41+), with Wi-Fi up, headphones in and nothing playing,
the owner reported "No noise" in one 90 s listen, early in that boot. So the noise looks specific to
mainline, though stock may hold the HP path differently, so the board is not cleared. The
owner also reports that it is absent during playback: "I think when the audio driver is driving
output, it doesn't pick up sound". Inference: an off amplifier leaves the line floating and easier
to couple into. The Wi-Fi session finds no 30 s timer in the driver; a firmware notice repeats at
about 30-37 s but starts about 6 minutes after a join, and the noise returned inside a 90 s listen
after a reconnect, which is a weak timing against it.

## Conclusion

`confirmed` for the named Gemini, Linux 7.1.3 and package `b36b2f7f`: audio is ready after boot
and plays through the headphones with no setup. Audio holds its power domain and clocks on
for the whole uptime, at a cost too small to see in this measurement.

Open at the time: playback after a module reload was silent until a reboot, and the 30 s Wi-Fi noise
was not compared with stock. The [reload experiment](../2026-11-01-gemini-audio-reload/README.md) has
since fixed the first and found the noise begins at the first playback, which revises the reading above
that the audio driver is not involved.

## Follow-up

- [Gemini audio](../../docs/hardware/gemini-audio.md)
