# Experiment: headphone jack detection on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-jack-detect` |
| Status | `planned`: patches written; not booted |
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
2. Run `jack-test.sh`, and follow the prompts for three unplug and replug cycles.
3. Run the existing `audio-test.sh` once as a playback regression; the owner
   listens for the tone.

| Observation | Next |
| --- | --- |
| Control follows all changes, one interrupt each | Record; then classify headset, mic and buttons |
| Correct after a change but wrong at load | Read the EINT level at enable |
| Plug seen, unplug not | Run the detection unit as the vendor does |
| No interrupt at all | Read the stock counts on Gemian; check the sequence |
| Interrupt storm | Stop; check polarity and the clear sequence |

## Observations

None yet: no boot.

## Analysis

None yet.

## Conclusion

`inconclusive`: nothing here establishes hardware behavior.

## Follow-up

- [MT6351 ACCDET contract and driver plan](../../docs/hardware/mt6351-accdet.md)
