# Experiment: audio ready at station boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-audio-boot` |
| Status | `running`: station 31 boots with audio ready; idle cost within noise; periodic headphone noise open |
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
ACCDET interrupt on that cycle. A `jack out` was logged at 554.02 s, before the removal, which
the owner has not yet accounted for; the count stayed 2 through the reload.

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
idle has to fix this first. Until a reboot, a reloaded card may run in that state.

## Conclusion

`confirmed` for the named Gemini, Linux 7.1.3 and package `b36b2f7f`: audio is ready after boot
and plays through the headphones with no setup. Audio holds its power domain and clocks on
for the whole uptime, at a cost too small to see in this measurement.

Open: the periodic headphone noise, and whether the card plays after a module reload.

## Follow-up

- [Gemini audio](../../docs/hardware/gemini-audio.md)
