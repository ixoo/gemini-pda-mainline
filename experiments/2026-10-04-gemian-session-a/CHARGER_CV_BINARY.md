# Gemian CV log versus actual write request

The [binary receipt](results/charger-cv-binary.json) joins the
[passive baseline](README.md) to the retained kernel analyzed in the RE VM.
No charger transaction was performed. One 40-second identity-checked LAN packet
resolved the unique live GPT `boot` label through `lsblk`, required agreement
with its by-partlabel target and the exact 16 MiB block size, and obtained a
full read-only SHA-256 through `sudo -n`. Its hash matches the retained captured
boot image. The same returned Gemian boot identity/release remained before/after.
This is stored-image attribution, not a hash of live instruction memory.

## Identity and independent byte checks

The Image and reconstructed ELF hashes match the prior
[RTC audit](../2026-07-11-mt6351-pmic-recovery/results/rtc-binary-audit-20260908.md#identity-and-method),
which establishes boot-payload extraction. The entire `.kernel` section equals
the Image. GNU AArch64 objdump 2.42 disassembled six selected functions; every
printed instruction in their bounded spans was checked against Image words.
Receipt spans include trailing alignment where present. The 49-entry CV table
and log-format string were independently located and hashed in the Image.
Private disassembly remains in the RE VM; only normalized facts were exported.

## Computation is logged, then overridden

`charging_set_cv_voltage()` computes a closest table voltage from its caller's
request, then obtains that voltage's register index. The enabled logging branch
prints the computed index, the caller request and selected table voltage. It
then rejoins the non-logging branch at a fixed `0x24` argument to
`bq25890_set_vreg()`. Both branches disregard the computed selector for the
actual setter call and return zero without checking its result.

Consequently the observed `0x1f 4340000 4336000` log is consistent with this
binary's fixed `0x24` write request. It is neither a readback nor evidence that
the running kernel differs from the public fixed-selector source at this call.
The actual table maps `0x1f` to 4.336 V and `0x24` to 4.416 V. These are nominal
programming values, not measured battery or regulator voltage.

## Setter and transport limits

`bq25890_set_vreg()` passes register 6, mask `0x3f` and shift 2 to the config
helper. Under its mutex, that helper starts a temporary byte at zero, calls
`bq25890_read_byte()` without checking its return, preserves bits outside the
mask from the resulting temporary byte, merges the requested field, and calls
`bq25890_write_byte()`. The write helper submits one two-byte I2C message and
returns 1 only for a transfer result of one; other results become -1. The config
helper returns that write result, but the CV callback ignores it. There is no
post-write register readback in the inspected call chain.

This establishes a compiled REG06 write request and error-propagation gap, not
successful application. Failed initial reads may lose unrelated low bits when
the initialized temporary byte is used. No read-clear behavior, actual I2C
transaction, latched REG06 state, cell chemistry or safe maximum voltage is
proved by this analysis. Other charger writers and watchdog/reset behavior
remain separate.

## Consequence

The computed 4.336 V log cannot establish safe charging or close charging H10.
Keep the existing recommendation against long unattended Gemian charging while
latched state is unresolved. Do not silently change the vendor policy from
this evidence. A subsequent live observation needs a reviewed bounded REG06
read with attributable transport success and result ownership. The future
mainline C2b stage must program and verify the reviewed 4.2 V / 500 mA limits
before enabling charging; `read-back-settings` cannot enforce those DT limits.

Validation is exact binary/section/instruction/table identity checking plus
repository documentation/JSON checks. No kernel build, driver modification,
charger access, calibration, restart or boot2 write was performed.
