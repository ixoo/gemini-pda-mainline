# Experiment: headphone jack detection on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-jack-detect` |
| Status | `completed`: the jack control follows plug and unplug on station 30 |
| Subsystem | audio: MT6351 ACCDET EINT, card jack |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | audio session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

With the ACCDET EINT armed by the MT6351 codec driver, the card's `Headphone Jack`
control follows the physical jack: it reads on with headphones present at load,
then follows three unplug and replug cycles, with one PMIC interrupt per change.

It is falsified if the control does not follow the jack or the interrupt never
fires. Telling a headset from headphones, the headset microphone and the buttons
are later stages of the [driver plan](../../docs/hardware/mt6351-accdet.md).

## Why not first read the stock IRQ counts

The [runtime sequence](../2026-10-04-gemini-audio-re/README.md#first-runtime-sequence)
asked for ACCDET IRQ counts on Gemian before any driver. That check would only
confirm that the stock build uses PMIC interrupts 12 and 13, which its source and
configuration state. Testing the driver answers the same question on mainline with
no extra owner boot, and a silent interrupt would send us back to Gemian.

## Design

Smaller than the plan's separate driver, because the only consumer so far is the
codec's own card:

- the `mt6351-sound` MFD cell gets interrupt 13, with no new DT node or binding;
- the codec's `set_jack()` arms the EINT with the board's vendor values, and each
  EINT flips the polarity and debounce and reports `SND_JACK_HEADPHONE`;
- the card's `Primary Codec` link creates the jack.

The ACCDET detection unit stays off. The vendor runs it after a plug to classify
the cable, and re-initialises the block then; this driver does neither. Whether
the unplug EINT needs either is one thing this test shows.

## Build

Buildbox-3, commit `d053ffd13f6dace0c32e3423b9c8f7672b0c1fd4`, job `d053ffd1…-mt6797-a53-station-m1`, inventory `13d0656e…`. Compiled, checksums pass. Device action: none.

At the custodian's request, so that one image carries audio, Wi-Fi and GNSS, the test
package is commit `b3cfdeb6cb720a7570839f201ec4772a8346b8e9`, job
`b3cfdeb6…-mt6797-a53-station-m1`, inventory `ca1802df…`, `Image.gz` `ee620135…`, with
`0415`-`0419`. Its audio modules match the `d053ffd1` package. Device action: none.

## Safety assessment

The kernel image changes, so this needs a boot2 write through the reviewed path.
Without the audio modules nothing here runs. Module load admits:

- the ACCDET clock, reset and registers, interrupt 13, and the analog ACCDET bits;
- the MICBIAS1 reference and low-power bits in `AUDENC_ANA_CON10`, not its power bit.

The test plays nothing. No NVRAM, calibration, radio or eMMC writes. Stop on an
oops, a hang or an interrupt storm: a count far above the number of changes is
a stuck line, so stop and unload.

## Associated code

- [`jack-test.sh`](jack-test.sh): device test, root.
- `0415`-`0417`.

## Procedure

Run by the custodian on a fresh boot, with the owner present:

1. Plug the headphones in before loading anything.
2. Run `jack-test.sh`: follow the prompts for three unplug and replug cycles, then unplug,
   a tone with the headphones out, then plug in. It reuses loaded modules.
3. On a boot where the modules were already loaded, `RELOAD=1 jack-test.sh` covers the
   headphones-in-at-load case and module removal.

| Observation | Next |
| --- | --- |
| Control follows all changes, one interrupt each | Record; then classify headset, mic and buttons |
| Correct after a change but wrong at load | Read the EINT level at enable |
| No interrupt at all | Read the stock counts on Gemian; check the sequence |
| Interrupt storm | Stop; check polarity and the clear sequence |
| Interrupt during playback with the headphones out | False EINT from the HP driver; read the level, do not toggle |

## Observations

**Run 1, station 30 (boot `4ac95e75`, package `b3cfdeb6`, `Image.gz` `ee620135…`), run by the
custodian.** `jack-test.sh` stopped before its 60 s window: `Headphone Jack` is a card
control, and `cget name=` looks on the mixer interface. No plug cycle was logged.

- The control and the input device (`event2`) exist. `mt6351-accdet` read 0 from load at
  115 s.
- At 156.22 s the count went to 1 with `jack in`, about when the first `audio-test.sh` tone
  started. The headphones were not in at load, contrary to the request, and the owner
  plugged them in at an unknown time up to about 200 s. The count stayed 1 afterwards, through a
  later full playback run with the headphones in.
- Unprompted, the owner unplugged the headphones: `jack out` at 272.91 s, count 2, control
  off, read at 356.7 s by the custodian. One interrupt, no storm.
- Regression: `audio-test.sh` exit 0 twice; tone heard in both ears on the second run,
  with the headphones in. No oops or warning, Wi-Fi `COMPLETED`.

**Run 2, same boot, `jack-test.sh` `299073d4…`, run by the custodian; times from `dmesg`:**

| Event | Time (s) | Interrupt count after |
| --- | --- | --- |
| Plug, from a known off state | 1345.88 | 3 |
| Three owner cycles: out, in, out, in, out, in | 1390.39, 1393.57, 1396.66, 1399.38, 1402.11, 1404.55 | 4 to 9 |
| Unplug | 1430.22 | 10 |
| 2 s tone with the headphones out, 1463-1465 | no event | 10, `aplay` rc 0 |
| Plug | 1533.66 | 11 |
| `RELOAD=1`: `rmmod` and reload with the headphones in | 1547.62 | 12, control on 2 s after load |

Both scripts exit 0. No oops, warning, call trace or `nobody cared`; not tainted; Wi-Fi
`COMPLETED` throughout. Playback was not repeated after the reload.

## Analysis

Run 1 cannot separate two readings of the one interrupt: the owner's plug, or a false
EINT from the first headphone power-up, after which the driver would wait for an unplug
and the real plug would raise nothing. The script now logs every state and count change
against uptime, and plays with the headphones out to test the second reading.

The unplug shows the unplug EINT works with the detection unit off, which removes that
decision branch. It does not separate the two readings: a false `in` at 156 s, a plug that
raises nothing and a real unplug would log the same sequence.

Run 2 confirms the hypothesis: twelve changes, twelve `jack` lines, twelve interrupts, each
with the control following. Headphones in at load are seen, because the EINT is level
triggered. Module removal and reload run without error, but [removal leaves the AUDIO domain
half off](../2026-11-01-gemini-audio-boot/README.md), and playback after a reload is untested.

Playback with the headphones out raised nothing, so playback is not a general source of
false EINTs, and the 156 s event was probably the owner's plug. That is an inference: run 2
did not repeat the card's first power-up on a boot, which is when that event happened.

## Conclusion

`confirmed` for the named Gemini, Linux 7.1.3 and package `b3cfdeb6`: the `Headphone Jack`
control and input device follow plug and unplug, with the plug used here. The owner reports
headphones with no microphone, the only set tried, so a headset plug is untested. The debounce
values are the board's, not measured.

Not established: a false EINT at the first power-up on a boot, telling a headset from
headphones, the headset microphone, the buttons, and suspend. Nothing switches audio paths on
a jack event yet.

## Follow-up

- [MT6351 ACCDET contract and driver plan](../../docs/hardware/mt6351-accdet.md)
- Cheap check on any fresh boot: load and play once with the headphones out, then read the count.
- Next stages: headset classification with the detection unit, the headset microphone, the buttons.
