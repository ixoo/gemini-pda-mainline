# MT6351 ACCDET contract and driver plan

Scope: the MT6351 accessory-detect block used by the Gemini headset jack.
This is a design record, not a claim of runtime support. The vendor source,
the register map and the existing MT6359 driver are the inputs.

Plug and unplug already reach the `Headphone Jack` control on the station, through
[a smaller change](../../experiments/2026-11-01-gemini-jack-detect/README.md) on the ACCDET EINT.
Headset classification, the microphone bias path and buttons remain this plan.

## 1. Why the MT6359 driver is not reusable

Mainline `sound/soc/codecs/mt6359-accdet.c` is a roughly 1,000-line driver
built around MT6359 register names and MT6359 EINT routing. It has no
`mediatek,mt6351-accdet` compatible and cannot describe the MT6351 block by
changing a few constants:

- MT6351 ACCDET lives at `ACCDET_CON0..CON24` (`0x0F46..`) with different
  field layouts.
- MT6351 uses the PMIC interrupt bank sources 12/13/14
  (`ACCDET`, `ACCDET_EINT`, `ACCDET_NEGV`), not the MT6359 EINT0/EINT1
  register set.
- MT6351 routes headset-mic bias through `AUDENC_ANA_CON10` (MICBIAS1) and the
  ACCDET analog input through `AUDENC_ANA_CON11`.
- MT6351 button detection reads AUXADC channel 5; it is not part of the MT6359
  register set.

The MT6359 driver is therefore a useful structure reference, not a base for a
compatible string.

## 2. MT6351 register contract

| Function | Register | Notes |
| --- | --- | --- |
| Control | `MT6351_ACCDET_CON1` | enable, EINT enable, NEGV enable |
| State switch | `ACCDET_CON2` | vendor writes `0x07` |
| PWM width | `ACCDET_CON3` | board value |
| PWM threshold | `ACCDET_CON4` | board value |
| Debounce | `ACCDET_CON6..CON10` | plug-in/out and EINT debounce |
| IRQ status | `ACCDET_CON12` | IRQ/EINT/NEGV status and clear bits |
| State | `ACCDET_CON14` | current jack state |
| EINT control | `ACCDET_CON15` | EINT polarity and PWM |
| Negative-voltage | `ACCDET_CON20` | NEGV control |
| Current debounce | `ACCDET_CON21/22` | current-mode debounce |
| ADC control | `MT6351_AUXADC_RQST0` | channel 5 request |
| ADC result | `MT6351_AUXADC_ADC5` | 12-bit button value |
| MICBIAS1 | `MT6351_AUDENC_ANA_CON10` | `(mic_vol << 4) | 0x80` |
| ACCDET analog | `MT6351_AUDENC_ANA_CON11` | `|= 0xF`, EINT link bit 11 |
| Clock gate | `MT6351_TOP_CKPDN_CON2` | bit 9 |
| Reset | `MT6351_TOP_RST_CON0` | bit 4 |

PMIC interrupt sources:

- 12 `MT6351_IRQ_ACCDET` — jack state change;
- 13 `MT6351_IRQ_ACCDET_EINT` — EINT edge;
- 14 `MT6351_IRQ_ACCDET_NEGV` — negative-voltage event.

## 3. Vendor initialisation order

The vendor `accdet.c` sequence is:

```text
ungate ACCDET clock and release reset
program PWM width/threshold and state switch (0x07)
program rise/fall delay and debounce
set EINT polarity
enable IRQ 12 and 13
AUDENC_ANA_CON11 |= 0xF
AUDENC_ANA_CON10 |= (mic_vol << 4) | 0x80   // MICBIAS1
ACCDET_CON0 = 0x0010
AUDENC_ANA_CON11 |= BIT(11)                 // ACCDET to EINT
```

The vendor uses:

- plug-in debounce 256 ms and plug-out 1 ms;
- MICBIAS1 left on for 6 s after an event;
- three-button thresholds 0/80/220/400 mV;
- `accdet-mic-vol = 7`, `accdet-mic-mode = 1` (ACC);
- button values on AUXADC channel 5 with an efuse offset from OTP word 3.

These are configured values, not an acoustic calibration.

## 4. Driver shape

The correct mainline shape is a small platform driver under the MT6351 MFD:

```text
mt6351 MFD
 ├─ mt6351-sound
 ├─ mt6351-accdet
 │    ├─ IRQ 12/13 from the MFD IRQ domain
 │    ├─ regmap from the PWRAP grandparent
 │    ├─ snd_soc_jack / input button reporting
 │    └─ MICBIAS1 and AUXADC channel 5
 └─ ...
```

Implementation stages:

1. **MFD cell and binding.** Add an `mt6351-accdet` cell with IRQ resources
   12/13 and a DT child under the PMIC.
2. **Jack-only driver.** Configure ACCDET, request IRQ 12/13, read
   `ACCDET_CON12/14`, debounce, and report `SND_JACK_HEADPHONE` /
   `SND_JACK_HEADSET` through the card jack.
3. **Headset mic.** Enable MICBIAS1 and route AIN1 for capture; the existing
   MT6351 codec DAPM already provides `Mic Bias 1` and `AIN1`.
4. **Buttons.** Add AUXADC channel 5 reads, efuse offset, and
   `SND_JACK_BTN_0..2` or input key events.
5. **Power management.** Disable MICBIAS1 after the 6 s timer, suspend/resume
   ACCDET, and keep the IRQ wake policy explicit.

Do not copy the vendor moisture, four-key, AP-EINT or debug paths. They are
not needed for the Gemini and would add unverified state.

### 4.1 What was built first

Proposals `0415`-`0417` are smaller than the shape above. The codec driver owns the
jack through `set_jack()`, and the existing `mt6351-sound` cell carries interrupt
13, so there is no new cell, DT node or binding. Only the EINT is armed, and plug
and unplug are reported as `SND_JACK_HEADPHONE`. A separate driver is worth
revisiting if classification and buttons outgrow the codec. See the
[jack experiment](../../experiments/2026-11-01-gemini-jack-detect/README.md): plug and
unplug are followed on station 30, one interrupt per change, with the detection unit
off and no re-initialisation after a plug.

## 5. Preconditions

The driver should not be written before the card probes:

- `mt6351-sound` and the AFE card must bind (proposals `0396`-`0399`);
- the PMIC IRQ domain must deliver child IRQ 12/13;
- the card must expose a jack object for `snd_soc_jack`.

Without those, the driver has no consumer and cannot be validated.

## 6. Decision

- **Not** a mechanical MT6359 port.
- **Not** a vendor-driver copy.
- A new, small MT6351 ACCDET driver is required.
- The first implementation should be jack detection only, then headset mic,
  then buttons.
- Runtime validation is a separate reviewed experiment after the card boots.

## 7. Evidence

- Vendor `drivers/misc/mediatek/accdet/mt6797/accdet.c`,
  `reg_accdet.h`, and `mt6351` register headers.
- Mainline `sound/soc/codecs/mt6359-accdet.c` and its binding, used only as a
  structure reference.
- [Gemini audio input/output](gemini-audio.md) and
  [audio RE](../../experiments/2026-10-04-gemini-audio-re/README.md).
