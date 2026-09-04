# PMIC-wrapper reset serviceability design

## Accepted parent

Candidate AW is retained as private local evidence because it naturally bound
PWRAP, its MT6351 child, VEMC/VIO18, and the MT6797 eMMC host while preserving
eight A53 CPUs and USB serviceability. Its kernel profile is historical-only:
it selected a noncanonical DA9214 series and may not be reused.

This experiment therefore reuses only AW's independently hashed final DT and
initramfs. The new kernel comes from the current canonical series with a fresh
focused profile. The new profile retains the same console, USB gadget,
keyboard, SMP8, PWRAP, MT6351, and eMMC configuration but omits the old
DVFSP/I2C6/DA9214 experiment chain.

## Exact DT delta

The accepted control property is:

```dts
pwrap@1000d000 {
    resets = <0x03 0x40>;
};
```

The first cell is the exact infracfg phandle. The sole transform changes the
second cell to compact public input 1:

```dts
pwrap@1000d000 {
    resets = <0x03 0x01>;
};
```

The transformer operates on the parsed property offset without reserializing
the FDT and requires the output to differ by that one big-endian cell only.
The thermal node receives no reset property and remains disabled.

## Runtime boundary

The boot performs the PWRAP driver's existing natural reset during probe. No
new debugfs trigger, reset retry, register poke, CPU action, workload, thermal
sample, or storage write is added. The attributable observations are the exact
kernel identity and natural probe outcomes for PWRAP, the MT6351 child and
regulators, the eMMC host/card, and the pre-existing USB shell.
