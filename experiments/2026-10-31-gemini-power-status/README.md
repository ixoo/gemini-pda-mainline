# Experiment: read-only battery and power status on the station

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-power-status` |
| Status | `running`: S1 power and charge state and S1b live ADC readings work, plugged and unplugged |
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

Station 8 (boot2 `62ae2230…`, built at `0b3bb43f`) carries S1. It is
flashed and ready to boot.

## S1b: one conversion start

The owner chose live charger readings on 2026-10-31, which admits this one
write.
- **The write:** before reading, `power-status` writes REG02 back with only
  `CONV_START` (bit 7) added to the value it just read. It then polls REG02
  every 100 ms, for at most 2 s, until the bit clears, and reads as before.
  - In continuous mode (`CONV_RATE` set), nothing is written.
  - If the bit never clears, the values are printed `stale`.
- **Unchanged:** no other register is written, and REG0C is never read.
- **Expected side effect, from the datasheet and unverified:**
  - a write may take the BQ25896 out of its default mode until its 40 s
    I2C watchdog expires again;
  - no charge parameter is changed, because REG02's other bits are written
    back as read.
- **Host test** (fake bus):
  - the only write is REG02 `0x11` becoming `0x91`;
  - continuous mode writes nothing;
  - REG0C is never read, and a wrong part number still stops before any
    access.
- **Binary:** `22b223ac…`, deployed live to station 8 over SSH (boot
  `aa795da9…`); the next station image carries it.

**Readings (predeclared):**

| Observation | Reading |
|---|---|
| `adc=live`, with REG0E/REG11/REG12 changed from the stale `5e/9a/00` | The conversion gives live battery voltage, VBUS and charge current |
| `adc=stale` (the bit never clears) | The ADC does not convert on request in this state; stop and record |
| The charge state or power good changes right after the write | The write affected charger mode; stop and record |

## Observations

**Station 8, boots `975af37c…` and `bb6c4873…`.**
- **Identity:** I2C0 is `i2c-0`. REG14 read `0x06`, part number 000 and
  revision 10: the BQ25896, the same value as the earlier Gemian read.
- **Cable in, about 20 s after boot:**
  - `power=usb-sdp good=1 charging=no adc=stale`;
  - raw `02=11 0b=26 0e=5e 0f=5d 10=3e 11=9a 12=00`.
- **Two minutes later:**
  - `charging=fast` (`0b=36`);
  - every ADC register unchanged.
- **Next boot, about 15 s after it:** `charging=no` again (`0b=26`).
- **Unplugged read:** inconclusive. It was scheduled 45 s ahead, but the
  cable was most likely still in at that moment.
- **Errors:** no read failed, and the program read REG0C at no point.

**Readings:**
- The right chip answers, and power-good and VBUS type report USB SDP.
  Their response to removing the cable is not yet observed.
- **The charge state field changes on its own:** the field starts at `no`
  after boot, then reads `fast` within two minutes with no mainline kernel
  programming the charger. That matches its 40 s I2C watchdog expiring and
  the chip returning to its defaults (inference from the datasheet; the
  register defaults were not read).
  - The field names the charger's state, not the current. The current
    reading is stale.
  - The owner reports the battery at 100%, so the charge was most likely a
    constant-voltage top-off at little current, not heavy charging.
  - It still means the chip, not reviewed limits, sets the charge voltage
    on mainline: 4.208 V by datasheet default, against Gemian's 4.416 V
    setting and C2b's planned 4.192 V. This argues for C2b, and is not
    evidence of a fault.
- **The ADC is idle:** REG02 is one-shot, and the values never changed. So
  battery voltage, VBUS and current here are from an unknown earlier
  conversion. Live values need S2 (MT6351 AUXADC) or an admitted
  conversion start.

**Station 8, boot `aa795da9…`: S1b deployed live.**
- **Identity:** the same station 8 image. `/bin/power-status` was replaced
  over SSH by `22b223ac…` at 25 s uptime, after one S1 read.
- **S1 read just before (24 s):** `adc=stale`, raw `02=11 0b=26 0e=61 0f=60
  10=3e 11=9a 12=00`. The stale values differ from the previous boot's
  `5e/5d`, so some earlier conversion left them.
- **S1b reads, cable in:**

  | Uptime | Charge state (`0b`) | Battery | SYS | VBUS | ICHG | `adc` |
  |---|---|---|---|---|---|---|
  | 25 s | no (`26`) | 4.34 V (`66`) | 4.38 V | 5.1 V (`99`) | 0.00 A | live |
  | 28 s | no (`26`) | 4.34 V | 4.38 V | 5.1 V | 0.00 A | live |
  | 36 s | no (`26`) | 4.34 V | 4.38 V | 5.1 V | 0.00 A | live |
  | 66 s | fast (`36`) | 4.20 V (`5f`) | 4.16 V | 5.2 V (`9a`) | 0.00 A | live |
  | 96 s | fast (`36`) | 4.20 V | 4.16 V | 5.2 V | 0.00 A | live |
  | 126 s | fast (`36`) | 4.22 V (`60`) | 4.20 V | 5.2 V | 0.00 A | live |

- REG02 read `0x11` after every conversion: the start bit cleared and no
  other bit changed. Every read returned, and the kernel log shows no I2C
  error or warning.

**Readings:**
- **The conversion gives live values** (first row of the S1b table): battery,
  SYS and VBUS change between reads and from the stale values.
- **The write did not change the charger mode:** the charge state and power
  good were unchanged in the reads taken right after each write, at 25, 28
  and 36 s.
- **Charge state change:** it moved to `fast` between 36 s and 66 s. That is
  the same timing as the earlier boots, which made no writes, so it is not
  attributed to S1b.
- **Charge current:** reads 0 in `fast`. ICHGR has a 50 mA step, so the
  current is below 50 mA. That fits a top-off of a full battery (owner
  report).
- **Battery voltage drop, unexplained:** the battery read 4.34 V before the
  change and about 4.20 V after. One possible reason is the chip returning
  to its 4.208 V default target after a battery charged higher under
  Gemian's 4.416 V setting. That is not established: the charge-voltage
  register was not read.
- **Percentage:** the voltage estimate saturates at 100% here, so it says
  nothing more than "full".

**Station 8, boot `aa795da9…`: cable removed and reinserted.**
- **Method:** `power-status -r` ran every 5 s, started over SSH and detached
  from it, into `/run/station`. The owner unplugged the cable for about 45 s
  and plugged it back in. The file was fetched after SSH came back, in the
  same boot (uptime 372 s).
- **Results:** 14 reads, all `rc=0`, all `adc=live`.

  | Uptime | Power | Good | Charge state | Battery | SYS | Raw `0b` / `11` |
  |---|---|---|---|---|---|---|
  | 305–315 s | usb-sdp | 1 | fast | 4.22 V | 4.18 V | `36` / `9a` |
  | 320–361 s | none | 0 | no | 4.22 V | 4.20–4.22 V | `02` / `00` |
  | 366–371 s | usb-sdp | 1 | fast | 4.22 V | 4.18–4.20 V | `36` / `9a` |

**Readings:**
- **Power status follows the cable:** the VBUS type, power good, VBUS good
  (REG11 bit 7) and charge state all changed within one 5 s read of each
  change.
- Unplugged, VBUS reads the ADC floor (2.6 V, field 0) and SYS rises to the
  battery voltage. Bit 1 of REG0B, which reads 1 unplugged, is not decoded.
- **Replug:** the charge state went straight to `fast`, with no delay like
  the one after boot. That fits a chip that already runs on its own defaults
  (inference).
- **Battery voltage:** unchanged at 4.22 V through the unplug, so the drop
  recorded at boot did not come back.
