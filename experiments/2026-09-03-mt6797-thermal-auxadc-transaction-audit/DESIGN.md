# MT6797 thermal/AUXADC transaction design

## Ownership decision

The first runtime observer has one owner for the AUXADC register block: the
thermal controller driver. The standalone IIO AUXADC node remains disabled.
Two drivers cannot independently own the same clock, `MISC.PDN_EN`, channel-11
mode, conversion trigger, and suspend state without a shared arbitration API,
which does not exist in the current tree.

The pinned Gemini vendor defconfig leaves `CONFIG_AUXADC_NEED_POWER_ON` unset,
so its `MISC[14]` power helper performs no write. Mainline's standalone driver
sets the bit unconditionally. The first thermal implementation must preserve
that unresolved bit, own its clock, verify global idle before changing channel
state, and unwind every acquired resource.

## Required fail-closed order

The eventual MT6797-specific implementation must make these phases explicit:

1. `CLOSED`: no clock, reset, buffer, AUXADC, bank, IRQ, or thermal-zone side
   effect.
2. Validate the exact three-word calibration payload.
3. Parse and map thermal, AUXADC, and APMIXED resources; reject every failed
   mapping and acquire the correct exclusive thermal reset.
4. Enable AUXADC and thermal clocks and assert/deassert thermal through
   infracfg RST0 SET/CLEAR. Preserve `AUXADC_MISC[14]` until its MT6797 meaning
   and required state are independently established.
5. Clear only APMIXED `TS_CON1[5:4]`, delay 200 microseconds, and verify those
   two bits are zero without modifying unrelated fields.
6. Poll thermal AHB busy and AUXADC global idle with bounded timeouts; on
   failure, return to `CLOSED`.
7. Pause and disable periodic sensing in every bank, clear AUXADC channel 11
   synchronous and immediate modes, then program all six banks completely.
   `TEMP_MONCTL0`, global channel enable, and pause release remain off during
   this preparation phase.
8. Commit once: set AUXADC channel 11, enable the defined sensing points in all
   six banks, then release periodic sensing in all six banks.
9. Poll for bounded, attributable first samples from every defined sensor.
   Raw zero is not a valid readiness sentinel. Any missing, out-of-range, or
   inconsistent bank sample aborts and unwinds before zone registration.
10. Register the read-only thermal zone only after all six banks pass.
11. On any later failure or removal, pause and disable all banks, clear channel
    11, restore the APMIXED buffer field, preserve the unresolved AUXADC power
    bit, and disable clocks in reverse order.

No IRQ is requested and no hardware threshold or watchdog direct-reset path is
enabled until the SPI-78 bank-status/acknowledgement contract and a standard
mainline watchdog ownership interface are separately resolved. `TEMP_AHBTO`
must not be configured to generate an unhandled interrupt.

## Reset prerequisite

The present reset provider cannot be used:

```text
current ID 0  -> MTK_RST_SIMPLE RMW at +0x120 for assert and deassert
required ID 0 -> write bit 0 to SET +0x120, then CLEAR +0x124

current ID 64  -> MTK_RST_SIMPLE RMW at +0x128
required ID 64 -> write bit 0 to SET +0x140, then CLEAR +0x144
```

The pinned MT6797 sources directly prove SET/CLEAR pairs `0x120/0x124` for
thermal and `0x140/0x144` for PMIC wrap. The existing mainline MediaTek reset
header and the `0x10` bank stride suggest `0x130/0x134` for RST1, but this audit
did not find that pair in the vendor tree. A repair must use SET/CLEAR semantics
for proven IDs 0 and 64, obtain a primary source for IDs 33/48 or quarantine
them, and test invalid IDs. The PMIC-wrap node is the only current infracfg
consumer and therefore owns the first runtime regression obligation. The
disabled thermal node must not gain a reset phandle in the same change.

## Standalone AUXADC prerequisite

If the IIO node is enabled later for non-thermal channels, MT6797 needs its own
compatibility data and conversion order:

```text
lock -> power/clock owned -> poll CON2 idle -> clear channel ->
poll old RDY clear -> trigger -> 25 us -> poll RDY set -> read -> unlock
```

The current `mt8173_compat` path polls `CON2` only after trigger and is not an
accepted MT6797 implementation. Any future coexistence with thermal needs a
shared owner/arbitration design rather than two DT nodes directly controlling
the same block.

## Explicit non-scope

This audit and the selected reset repair add no DT enable, thermal sample,
thermal zone, IRQ, trip, cooling device, watchdog request, cpufreq/OPP change,
A72 load, device candidate, or device action.
