# Experiment: audio ready at station boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-audio-boot` |
| Status | `planned`: RAM root composed offline, device test requested; not booted |
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

None yet: no boot.

## Analysis

None yet.

## Conclusion

`inconclusive`: nothing here establishes hardware behavior.

## Follow-up

- [Gemini audio](../../docs/hardware/gemini-audio.md)
