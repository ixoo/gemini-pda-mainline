# MT6797 shared-remap field compile proposal

This experiment adds a separately compiled private `remap-fields.o` containing
only checked arithmetic for the two source-established fields in shared
register `0x10001340`. The common field encodes a 1 MiB-aligned base and
explicit enable bit; the optional WLAN field encodes a 64 KiB-aligned base.
Expected-state replacement is field-specific and preserves all neighboring
bits. There is no MMIO, regmap, lock, caller, owner, probe, registration,
secure call, mapping, firmware, DMA, IRQ, power, reset or policy path.

The generated proposal is
[`0009-wifi-mediatek-compile-remap-fields.patch`](0009-wifi-mediatek-compile-remap-fields.patch),
SHA-256 `84e6abef1139e744ecb59846b3fb3160b98ac50df4a59e058250a77b92d09cb6`.
Run `python3 scripts/verify.py` to regenerate, compile the implementation as
a separate host object, run the exhaustive fixture under ASan/UBSan, and run
pinned strict Checkpatch. The host fixture covers all 8,192 common encodings,
all 65,536 WLAN encodings, every alignment residue, overflow boundaries,
malformed fields, expected-state mismatch, cleared refusals, null outputs,
and exhaustive outside-mask preservation.

The host validation and frozen named-series byte/order audit pass. The series
`patches/series-mt6797-provider-compile` has SHA-256
`f28ab97bae1163a26d2be85cd459396baf005e916ba7708e12f2d823c547685f` and 11
exact ordered entries; the two source evidence documents are pinned by hash in
`inputs.json`. The exact named series replayed on Buildbox, and Linux compile
and package validation passed at commit
`8af75b14cba55dcd1078ac74eb96b11e1656b79a`. The
[build result](BUILD_RESULT.md) and [object evidence](object-evidence.txt)
record the exact package, object, command, symbol and no-caller evidence. The
expected Checkpatch findings are the synthetic missing DCO and new-file
MAINTAINERS warning. The exact expected field is supplied by an existing
owner/read observation; equality alone does not prove its provenance or exclude
an external writer.

This is compile evidence only and does not establish remap ownership, register
state, serialization, readback, hardware behavior or Wi-Fi support.
