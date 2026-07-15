# NT36xxx mainline backend design record

This is a source-derived implementation boundary with a live trim identity
capture. The vendor source is Planet MT6797 commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`.

The immutable vendor-kernel ELF (`e185566db67405c7747c01dbfe840ab9df69288c03f71eacacba9617827546f0`)
retains the same probe functions, memory-map pointers, and eleven-entry trim
table. A fresh filtered `dmesg` capture records returned bytes
`00 00 03 72 66 03`, which match masked source/ELF table entry 8: NT36772,
with event map `0x11e00`. The sanitized evidence is retained in
[`nvt-live-trim-identity-20260714.txt`](nvt-live-trim-identity-20260714.txt).
The exact source-derived IDs, masks, and map constants are normalized in
[`nt36xxx-trim-map-metadata-20260714.txt`](nt36xxx-trim-map-metadata-20260714.txt);
the live capture now selects the NT36772 row rather than leaving the family
unresolved. The reproducible masked-byte check is
[`nvt-trim-consistency-20260714.txt`](nvt-trim-consistency-20260714.txt).

## Required transport layers

The vendor implementation uses one normal I2C client at `0x62`, but passes
two target addresses to its transfer helpers:

- `0x62`: reset commands (`0x69`, `0xa5`, `0x35`);
- `0x01`: bootloader/event/xdata commands and point data.

The vendor `CTP_I2C_READ()` and `CTP_I2C_WRITE()` implementations assign the
supplied address directly to every `i2c_msg`; the MTK DMA/non-DMA variants only
mask controller flag bits before the same transfer. `0x01` is therefore an
alternate target address selected by the controller's firmware state, not a
software register-page flag. The mainline backend must use a bounded helper
that copies the message address for the transfer rather than registering a
second ordinary I2C client at `0x01`. This address transition must be verified
on the actual controller before submission; it is not represented by a second
DT `reg` property.

## Bounded identification sequence

The vendor trim probe performs, up to five times:

1. write `00 69` to `0x62`, wait 35 ms;
2. write `00 a5` to `0x62`, wait 15 ms;
3. write `00 35` to `0x62`, wait 10 ms;
4. write `ff 01 f6` to `0x01` to select xdata;
5. read command `0x4e` at `0x01`, compare six returned bytes with the trim
   table.

After a successful trim match, the vendor probe writes `00 69` to `0x62`
again, waits 35 ms, then polls reset state before reading firmware info. The
mainline backend preserves that second bootloader reset.

This is state-changing reset/xdata activity but does not write firmware. It
must be an explicit opt-in diagnostic or probe path, never hidden behind a
generic compatible match without a verified trim table.

## Runtime event path

For the NT36772 map, select xdata `0x11e00` at `0x01`, then issue command `0x00`
and read 65 data bytes (the vendor helper describes this as a 66-byte
command-plus-data transaction). Ten records begin at data byte 0, with six
bytes per record. A record is active when its
status is `0x01` or `0x02`; ID is the first byte shifted right by three. X and
Y are packed 12-bit values, width is one byte, and pressure is 16-bit only for
the first two records (later records use the width byte). The vendor clamps
pressure to 1000 and width to 255, swaps X/Y, then reverses the resulting Y
against `abs_x_max - 1`.

The mainline implementation should use a threaded IRQ or a bounded work item,
`input_mt_init_slots(..., 10, ...)`, and release every slot not present in the
current frame. It should reject IDs outside 1–10 and coordinates above the
validated runtime maxima. The vendor kthread's real-time scheduling policy is
not a hardware requirement and should not be copied.

## Mainline implementation boundary

The Linux 7.1.x driver can provide the input/PM scaffolding, but its direct
register read at client address `0x62` cannot be extended by an OF alias: the
Gemini controller changes its I2C target to `0x01` after the reset sequence.
The smallest reviewable NT36772 backend should therefore have these layers:

1. Keep one ordinary I2C client at `reg = <0x62>`. A private transfer helper
   copies a caller-supplied logical target into each `i2c_msg.addr`, bounds the
   command/data lengths, and converts short transfers to `-EIO`. It must never
   register a second client at `0x01`.
2. Acquire named regulators, reset GPIO, and IRQ from a future board node,
   then perform the bounded `0x62` reset / `0x01` trim transaction. Accept only
   the observed masked NT36772 entry (or an explicitly reviewed additional
   map), and fail closed on an unknown map. Do not include the vendor delayed
   firmware worker or `/proc/NVTflash` path.
3. Select the NT36772 event page `0x11e00`, read and validate the `0x78`
   firmware-information block (including the version complement and nonzero
   dimensions), and derive the input ranges rather than silently applying the
   vendor fallback dimensions. The live vendor log proves PID `0x0101` and
   firmware `0x05`/bar `0xFA`, but not the parameter block, so this remains a
   runtime gate.
4. Use a threaded IRQ and standard `input_mt` slots. Read one command plus 65
   event data bytes at target `0x01`, parse ten six-byte records, reject
   invalid IDs/coordinates, clamp pressure to 1000 and width to 255, swap X/Y, and
   reverse the resulting Y using the validated X maximum. Release missing
   slots with `INPUT_MT_DROP_UNUSED`; do not copy the vendor real-time
   kthread or framebuffer notifier.

This decomposition permits compile/schema testing with a disabled DT node
before any reset or I2C traffic is attempted. A future binding should describe
only the physical `0x62` client and standard Linux resources; the logical
`0x01` target is an implementation detail of the driver.

## Firmware and power policy

Firmware info is read from event offset `0x78` after selecting the event page;
project ID is read from `0x9a`. Reset-complete polling reads `0x60` until the
requested state or a bounded retry limit. Suspend sends host command `0x11`
and disables the IRQ; resume repeats bootloader reset and reset-complete
polling. Mainline should express reset, regulators, and runtime PM through
standard device APIs and must not copy the vendor display-notifier dependency.

The vendor configuration schedules a firmware update 14 seconds after probe
and exposes `/proc/NVTflash`, whose read handler can issue I2C writes. Both
behaviors are excluded from the mainline backend. Firmware update, if ever
needed, must be a separate explicit operation with license and recovery
review.

## Static ELF parity

The ELF audit recovers `nvt_ts_probe`, `nvt_read_pid`, `nvt_get_fw_info`, the
reset helpers, and the explicit `CTP_I2C_READ`/`CTP_I2C_WRITE` helpers. The
trim table begins at `0xffffffc000e04118` with 0x20-byte entries; its data and
memory-map pointers match the source table. The probe compares only bytes whose
source masks are set, so the `0xFF` placeholders in the table are wildcards,
not literal silicon bytes. This is strong binary/source parity, and the
selected live ID is recorded in the filtered dmesg result linked above.

## Unresolved gates

- the alternate `0x01` target-address behavior needs a controlled hardware
  validation;
- the exact touch regulator net and reset polarity need board confirmation;
- no mainline runtime input test has been performed; the live vendor log also
  shows a delayed `novatek_ts_fw.bin` helper/checksum path, but the collector
  did not request or update firmware.
