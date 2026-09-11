# Retained LK selection of the ARM7 component

The retained bootloader's compiled MD1 load path selects the normal v5 table,
which includes `md1arm7`. Its header callback requires that entry and assigns
its destination and reservation size. The subimage loop has no one-byte
exception. The [one-byte retained payload](RETAINED_FIRMWARE.md) therefore does
not justify omitting the component or synthesizing a full ARM7 image.
This is static load-path evidence, not proof of a successful load or execution.

## Compiled selection and table

The [receipt](results/arm7-selection-20260911.json) pins the existing July LK
capture, five public source files, private decoder and bounded disassembly.
Analysis ran only in the RE VM. Function names are inferred from strings,
arguments and control flow; the retained binary supplies no asserted symbols.

The common loader queries `ld_version` at `0x4603b5de`. Its wrapper resolves to
the linked platform function at `0x46023120`. That function compares the same
configuration string and returns low word `0x10000`, high word zero. The caller's
matching branch selects table `0x46067df0` and invokes the image-list loader at
`0x4603b98c`. Its default branch also selects that table. This corroborates
`ccci_lk_load_img_plat.c:830–864`, `ccci_ld_md_hal.c:51–64` and
`ccci_ld_md_core.c:591–614` at the pinned source revision.

The decoded table uses 32-byte rows followed by a zero terminator:

| Type | Partition | Image name | Maximum payload |
| --- | --- | --- | ---: |
| Main | `md1img` | `md1rom` | 160 MiB |
| DSP | `md1dsp` | `md1dsp` | 2 MiB |
| ARM7 | `md1arm7` | `md1arm7` | 2 MiB |

All three initial destination, size and extension-flag fields are zero. The main
row points to Thumb callback `0x460391b9`; the subimage callbacks are null.
The receipt records the complete table digest and exact field values.

## Header assignment and load-loop boundary

The callback at `0x460391b8` searches the table by type. A missing ARM7 entry
returns `-9`; it is not treated as an optional missing descriptor. For a found
entry, it reads header fields at `0x114` and `0x118`, adds the offset to the main
image's destination, then stores the result and size in the ARM7 row. These
offsets independently decode to `0x04530000` and 3 MiB in the checksum-verified
retained main header. The 3 MiB header reservation is distinct from the table's
2 MiB loader maximum and the component's one-byte declared payload.

The compiled subimage loop skips a zero destination or zero header size. Other
subimages reach the existing image helper at `0x4603ad44`, called at
`0x4603b358` with the descriptor's maximum and flags. A negative result or one
larger than the header allowance takes an error branch. Non-DSP entries return
to the loop after those checks; this path neither rejects a result of one byte
nor contains a one-byte placeholder expansion. Earlier main-image, callback,
allocation and security failures can still prevent reaching it.

The source-only prediction of one byte plus fifteen alignment bytes remains
conditional on actual input selection and successful security policy. The
generic image/security helpers were not fully rederived from this binary.
The payload's purpose, authentication result and executing-image digest remain
unresolved. Preserve the retained component and complete memory reservation;
this analysis admits no firmware load, radio action, mapping or memory release.

## Reproduction and validation

Verify the receipt's private LK digest and map base `0x45fffe00`, then use
radare2 5.5.0 in ARM Thumb mode with the recorded bounded commands and color/byte
display disabled. Decode the table as little-endian eight-word rows. The private
decoder checks both selection literals, the shared query string, linked platform
pointer, table fields/terminator, all five source hashes and the retained main
header's digest and ARM7 fields. The two newly used source files also matched
fresh downloads from their pinned public URLs byte for byte.

Source/table checks, JSON, repository, whitespace, link and sensitive-data checks
passed before publication. No firmware was executed, no kernel was built and
no device was accessed for this audit. Raw firmware and disassembly stay private.
