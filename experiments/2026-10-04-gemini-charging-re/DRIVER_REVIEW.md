# BQ25890 driver write review for C2b

Offline review, 2026-10-05, of `drivers/power/supply/bq25890_charger.c` in
pinned Linux 7.1.3. Chip facts come from the public TI BQ25896 datasheet,
SLUSC76C. No device access, build or register read was performed.

## Question

The roadmap's C2b gate binds `bq25890` only after a reviewed sequence
programs and verifies 4.2 V and 500 mA before charging starts. Can the
unmodified driver do that?

## Chip behaviour that matters

- After a register reset, charging is enabled by default. `CHG_CONFIG` is 1,
  the charge current is 2.048 A and the charge voltage 4.208 V.
- Input source detection is on by default. A dedicated charger raises the
  input current limit to 3.25 A without any host write.
- The watchdog defaults to 40 s. When it expires, charge settings return to
  defaults, except the input limit and a few BATFET bits.
- The ILIM pin caps input current only when `EN_ILIM` is set, and only at
  500 mA or above. The Gemini's ILIM resistor value is not known.

## Every write the driver can make

| Path | Writes | Notes |
| --- | --- | --- |
| Probe, default | `REG_RST`, then watchdog off, then limits | Charging runs at reset defaults until the limits land. |
| Probe, `linux,skip-reset` | `CHG_CONFIG=1`, then watchdog off, then limits | Charging is enabled before any limit is written. |
| Probe, `linux,read-back-settings` | none of the limits | Adopts the loader's values. |
| Probe, limits | ICHG, VREG, ITERM, IPRECHG, SYS_MIN, BOOSTV, BOOSTI, BOOST_FREQ, EN_ILIM, TREG, BAT_COMP, VCLAMP | No input current limit. No readback. A write error aborts probe with partial state. |
| Probe, end | ADC continuous rate | Follows online state. |
| IRQ thread | `EN_HIZ` restore, ADC rate | Only on state change. |
| Property read | `CONV_START` | ADC properties while offline. |
| Property write | ICHG, VREG, input limit, `EN_HIZ` | ICHG and VREG are clamped to the DT values. The input limit is not clamped and can reach 3.25 A. |
| USB PHY notifier | `OTG_CONFIG` | Only with a legacy USB2 PHY; the Gemini has none. |
| VBUS regulator | `OTG_CONFIG` | Only if a consumer enables it. |
| External power change | input limit | BQ25892 only; not this chip. |
| Pump Express work | `PUMPX_EN`, `PUMPX_UP` | Only with `linux,pump-express-vbus-max`. |
| Remove | `REG_RST` | Unless skip-reset: restores 2.048 A, 4.208 V charging. |
| Shutdown | `OTG_CONFIG=0` | Without a USB PHY. |
| Suspend, resume | ADC rate | |

Values round down to the register step. A 4.2 V request programs 4.192 V,
and a 500 mA charge current programs 448 mA; 512 mA is exact.

## Findings

1. **The gate cannot be met unmodified.** Neither probe path keeps charging
   off until the limits are written. The reset path charges at 2.048 A and
   4.208 V for the duration of a few I2C writes. The skip-reset path enables
   charging under whatever state the chip holds at handoff. The stock Gemian
   kernel requests 4.416 V nominal per the
   [binary audit](../2026-10-04-gemian-session-a/CHARGER_CV_BINARY.md), and
   the charger keeps its registers across an SoC restart unless its own
   watchdog expires. What the loader leaves is not measured.
2. **The input limit is never set at probe.** With a dedicated charger, the
   chip's own detection allows 3.25 A input. Only a sysfs write or the ILIM
   pin limits it.
3. **Nothing is read back.** A failed or misapplied write is only visible as
   a probe error, or not at all.
4. **`linux,read-back-settings` is unsafe on this device.** It keeps
   whatever voltage the chip holds, possibly the stock 4.416 V request.
5. **Disabling the watchdog is right for this test.** Programmed limits then
   survive a host stall instead of reverting to 2.048 A charging.
6. **Unbinding is unsafe without skip-reset**, because remove resets the chip
   to its charging defaults.

7. **Probe needs an interrupt the board has not identified.** The driver
   fails probe when neither `interrupts` nor a `bq25890_irq` GPIO resolves.
   F3 records that the vendor driver requests no interrupt, so the INT pin's
   wiring is unknown. C2b needs that wiring, or a reviewed polling
   alternative, before any node can bind.

## Smallest change that meets the gate

One driver patch for the C2b profile, behind skip-reset:

1. Write `CHG_CONFIG=0` first, instead of 1.
2. Disable the watchdog and write the limits as today.
3. Write the input current limit from a DT value, 500 mA for C2b.
4. Read back every written field and refuse probe on any mismatch, leaving
   charging disabled.
5. Only then write `CHG_CONFIG=1`.

The board node then uses skip-reset, 4.2 V, 512 mA, conservative
precharge and termination, and `ti,use-ilim-pin` only once the resistor is
known. The first C2b boot checks the read-back log before any cable is
attached for longer than the observation. This review adds no patch,
profile or node.
