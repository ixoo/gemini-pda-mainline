# REG06 observation access review

Offline successor to the [matched CV binary audit](CHARGER_CV_BINARY.md).
The [receipt](results/reg06-access-review.json) pins five additional instruction
spans, the retained configuration and public TI document. No charger access,
configuration change, module load, new boot or device connection was performed.
This is a design review, not an admitted executable protocol.

## Target semantics and full-map effects

TI's [BQ25896 datasheet](https://www.ti.com/lit/ds/symlink/bq25896.pdf),
SLUSC76C (May 2018), printed page 38, describes REG06 as configuration fields
without a documented read-clear effect. VREG occupies bits 7:2; its nominal
encoding starts at 3.840 V in 16 mV steps and clamps above code 48. This supports
a single REG06 observation as distinct from a configuration-data write. The
address-pointer phase is still a bus write, and controller activity/ownership
and finite transfer behavior need their own review. No absence of all physical
effects is inferred from a register's R/W type.

Printed page 31 describes REG0C as fault history that changes on read. Thus
the planned C2a REG00–REG14 map is not uniformly passive: its first REG0C result
consumes a historical fault observation. Preserve that first result and admit
the effect explicitly; do not issue a second read merely to obtain current
faults or silently shrink the full-map requirement. This single-target review
does not admit C2a.

## Existing interfaces do not preserve attribution

The matched retained binary's `show_bq25890_access()` only prints a shared byte.
`store_bq25890_access()` chooses the read branch for nonempty counts no greater
than three, but ignores both integer-parser and read-interface returns, then
returns the original input count. Counts above three enter register-update
code. Do not use an unchecked echo/cat sequence or assume `0x06` plus a newline
is a read: that spelling has five bytes and selects the update branch.

`bq25890_read_interface()` initializes its local byte to zero, calls the low-level
byte reader, copies the masked byte to the caller regardless of transport
status, and returns the reader's result. Hence a failed request can replace the
shared cache with zero rather than retain an old successful value. Store/show
also lacks a lock holding result ownership across the separate userspace calls.
A numeric zero or successful store does not prove a fresh successful read.

The retained matched-kernel configuration disables `I2C_CHARDEV`; there are no
I2C-dev entry symbols in its reconstructed ELF. A standard userspace tool is
not an available proven alternative for this kernel. This review neither loads
a module nor forces access past a bound client.

The vendor `bq25890_dump_register()` starts an ADC conversion by updating REG02
bit 7 on both paths. Its full branch reads every register from 0 to 0x14 and
ignores individual transport outcomes, including REG0C's read-sensitive history.
Do not trigger it or increase logging level as a substitute for one REG06 read.
Already-emitted logs remain passive evidence, with historical/transport limits.

## Smallest attributable successor

Use the existing bound driver and low-level `bq25890_read_byte()` for a
default-off, one-shot observation of REG06. That helper submits two one-byte
messages (address pointer then read) under the driver's I2C mutex and returns
1 only when `i2c_transfer()` returns two; all other results become -1. Capture
that result alongside a private local byte in one operation; omit the value
on failure. Do not use the higher read-interface helper, shared cache, broad
dump, alternate raw transport, automatic retry or charger-policy write.

Before implementation/admission, pin the actual controller/core retry and
timeout behavior and MMIO/DMA effects, define one consumed entry and its
identity/evidence boundary, test actual failure and partial-completion paths,
and compile clean pushed inputs on Buildbox. A userspace timeout cannot supply
a kernel effect budget. There is no executable or deployable candidate here.
The subsequent value will describe one instant while vendor policy continues;
it will not establish continuous safety or authorize changing CV limits.

The subsequent [transport review](REG06_TRANSPORT_REVIEW.md) finds that helper
success alone does not establish exact FIFO completion. It supersedes the
byte/status-only design above and records controller/DMA failure effects.

## Validation

The full ELF kernel section matches the pinned Image; all instruction words
in the five receipt spans match it. Spans include trailing alignment where
present. The prior audit already matched the live primary boot partition to
this image. Config and TI document checksums are pinned separately. Public
output contains facts/hashes only; no vendor code, disassembly or document
bytes are redistributed. Repository Markdown/JSON checks apply, with no kernel
or DT change in this review.
