# MT6797 thermal/AUXADC transaction implementation

## Boundary

This gate implements the disabled-node production path and exercises its
ordering through injected hardware-free operations. It does not enable the
thermal or standalone AUXADC DT node, add the thermal reset phandle, request an
IRQ, program a watchdog threshold, register a synthetic platform device, make
a boot candidate, or contact the Gemini.

The MT6797 thermal driver remains the sole prospective owner of the AUXADC
block. The standalone IIO node remains disabled. `AUXADC_MISC[14]` has no
operation in the transaction because the pinned Gemini vendor configuration
does not write it and its required mainline state remains unresolved.

## Production order

Calibration remains the first fail-closed check. Once the exact three-word
payload passes, probe may map all three resources, acquire the mandatory
exclusive thermal reset, and acquire both clocks. The transaction executor
then owns this order:

1. enable the AUXADC clock;
2. enable the thermal clock;
3. reset the thermal controller through the exclusive source-proven reset;
4. save APMIXED `TS_CON1`, clear only bits 5:4, wait 200 microseconds, and
   verify the complete expected word;
5. poll thermal AHB busy and AUXADC `CON2[0]` global idle with bounded
   timeouts;
6. pause and disable periodic sensing in all six banks;
7. clear channel 11 synchronous and immediate modes;
8. completely prepare all six banks without enabling sensing and without
   programming `TEMP_AHBTO`;
9. set channel 11 once;
10. enable the defined sensing points in all six banks;
11. release periodic sensing in all six banks;
12. require a bounded nonzero, converted-in-range first sample from every
    defined sensor in every bank;
13. only then permit thermal-zone registration.

The generic paths for other MediaTek SoCs retain their existing transaction.

## Unwind

Every failure after bank access starts, and normal driver removal, follows one
close operation: pause and disable all banks, clear channel 11, restore the
complete saved APMIXED word, assert the thermal reset, disable the thermal
clock, and disable the AUXADC clock. State flags make the unwind proportional
when a failure occurs before one of those resources was changed.

The injected KUnit operation table is the same executor used by production.
It proves the exact success order, every fallible boundary, reverse cleanup,
raw-zero rejection, temperature-range rejection, AHB/global-idle predicates,
and the exact APMIXED mask without MMIO, clocks, resets, DT probing, or device
access.

## Deferred contracts

The first implementation deliberately leaves the thermal IRQ unused and does
not program the AHB timeout that could raise it. SPI 78 bank status and
acknowledgement, watchdog direct-reset ownership, trips/cooling, PM callbacks,
standalone AUXADC coexistence, cpufreq/OPP, CPU8/CPU9 load, idle, and suspend
remain later gates.
