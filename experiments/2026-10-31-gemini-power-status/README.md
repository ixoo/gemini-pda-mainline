# Experiment: read-only battery and power status on the station

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-power-status` |
| Status | `running`: S1 approved and implemented; not yet run on the device |
| Subsystem | BQ25896 charger (I2C0 `0x6b`), MT6351 PMIC |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-10-31 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question

The owner asked for battery and power status on the
[development station](../2026-10-30-mainline-dev-station/README.md).

**Question:** what is the smallest read-only way to answer "is external power
connected, is the battery charging, and roughly how full is it", without
taking over charge control?

## What is already known

From the [charging RE](../2026-10-04-gemini-charging-re/README.md) and the
[C2b charger record](../2026-10-06-gemini-c2b-charger/README.md):

- **Charger:** a BQ25896 on I2C0 (`i2c@11007000`) at `0x6b`, identified
  once under Gemian. Mainline has never read it.
- **Battery measurement:** the vendor measures battery voltage, current,
  temperature, VBUS and charge level on the MT6351 (AUXADC and its coulomb
  counter), not on the charger. Mainline has no MT6351 AUXADC or gauge
  driver.
- **Upstream `bq25890` driver:** not usable here. It resets the chip or sets
  `CHG_CONFIG` at probe, never sets the input limit, writes `CONV_START` on
  some reads, and resets the chip on removal
  ([driver review](../2026-10-04-gemini-charging-re/DRIVER_REVIEW.md)). C2b
  is the reviewed path to charge control, and it is not admitted.
- **Charger state on mainline:**
  - Gemian programs the charger and kicks its 40 s I2C watchdog. No
    mainline kernel touches the charger.
  - So on every mainline boot so far the charger has most likely run on its
    own defaults once that watchdog expired. This is inferred from the
    BQ25896 datasheet behaviour, not measured.
  - This design does not change that. Its first reading would show it.
- **No admitted read:** a charger register read has no admitted protocol
  yet. The C1 records ask for an I2C transport review first. REG0C (fault
  history) clears on read.

## Proposed design: S1, charger status by plain register reads

**Kernel and DT** (station profile only):
- I2C0 enabled in the station DT, with no child device: the FAN49101 node
  stays disabled, and no charger driver binds;
- `CONFIG_I2C_CHARDEV=y`.

**Userspace:**
- A small static `power-status` program, built like `lid-guard`, reads one
  byte at a time with `I2C_RDWR` from address `0x6b` only.
- It reads this fixed register list:

  | Register | Content |
  |---|---|
  | REG02 | ADC conversion mode (`CONV_RATE`), read only to say whether the ADC values are live |
  | REG0B | VBUS type, charge state, power good |
  | REG0E | battery voltage, thermal regulation flag |
  | REG0F | system voltage |
  | REG10 | TS percentage |
  | REG11 | VBUS voltage, VBUS good |
  | REG12 | charge current |
  | REG14 | part number and revision, a check that the right chip answers |

- It never reads REG0C, and never writes any register: no `CONV_START`,
  watchdog kick, mode or limit.
- It prints one line, for example `power=usb-sdp charging=fast
  battery=3.92V (estimate 70%) vbus=5.01V ichg=0.45A adc=live`.
- **Percentage:** a coarse estimate from battery voltage only, labelled as
  an estimate. There is no gauge, and the vendor battery profile is not
  copied.
- **Stale ADC:** if REG02 shows one-shot mode, the ADC fields are printed
  as `stale`, because the values come from an unknown earlier conversion.
  Starting a conversion would be a write, and is not admitted here.

**Effects:**
- I2C read transactions to one address on I2C0;
- the I2C0 controller is enabled, its clock on during transfers.

Nothing is written to the charger or the PMIC.

**Status bar:** once the readings are trusted, a later step can show the
power state on the console or behind a hotkey. That is not part of S1.

## Later steps (not proposed now)

- **S2:** an MT6351 AUXADC read of battery voltage and temperature. This
  needs a new IIO driver, and conversion requests are PMIC register writes.
- **C2b:** the reviewed charge-control path, so the station charges at
  4.2 V / 500 mA instead of the chip defaults.

## Device test, predeclared

1. Boot the station with S1, external power attached.
2. Run `power-status` twice, two minutes apart.
3. Unplug for 20 s with a delayed run, then plug back in and run it again.

| Observation | Reading |
|---|---|
| REG14 reads part number 000 (BQ25896) | The right chip answers; continue |
| REG14 reads anything else, or a read fails | Stop; no further reads this boot |
| REG0B power good and VBUS type follow the cable | Power status works |
| Charge state is fast or pre-charge with the cable in | The charger charges on mainline, most likely on its defaults; record it for C2b |
| REG02 one-shot and the REG0E/REG11 values identical across runs | The ADC is idle; voltage needs S2 or an admitted conversion start |
| REG02 continuous and the values change with the cable | Voltage and current are live from the charger alone |

## Safety

- The reads are bounded and change no charger or PMIC state: REG0C is not
  read.
- The owner keeps an independent way to remove power (the cable, and the
  power key).
- Heat or swelling stops the session, as [SAFETY](../../docs/SAFETY.md)
  requires.

## Implementation (S1)

The owner approved S1 on 2026-10-31.
- [`power-status.c`](../2026-10-30-mainline-dev-station/power-status.c):
  - finds the adapter under `11007000.i2c`;
  - uses SMBus byte reads only;
  - REG14 is read first, and the program stops unless the part number is
    BQ25896's;
  - `-r` adds the raw registers.
  - Built with `gcc -static -O2 -Wall -Wextra -Werror` on the VM (aarch64).
- **Host test:** a scratch harness swapped in a fake register bus. It checked
  the decoding, that REG0C is never read, that every access is a read, and
  that a wrong part number stops the run.
- **Station DT:** [`station-dt.sh`](../2026-10-30-mainline-dev-station/station-dt.sh)
  enables I2C0. The FAN49101 child stays disabled, and the DT delta is
  checked exactly.
- **Station profile:** `CONFIG_I2C_CHARDEV=y`.
- **RAM root:** the station builder now takes a tools directory holding
  `lid-guard` and `power-status`.

## Observations

None. Not run on the device.
