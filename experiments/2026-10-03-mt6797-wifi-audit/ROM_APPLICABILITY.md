# Installed ROM pair and version-selection boundary

The [bounded Gemian inspection](results/rom-applicability.json) verifies the
current kernel and boot identity before and after reading two exact installed
file sizes/digests and filtering existing version-selection log records. Both
installed files match the [retained ordered pair](ROM_PATCH_ORDER.md) exactly.
No firmware was downloaded, no WMT command issued and no radio state changed.
Installed attribution is now established; load history and applicability on a
new mainline power lifetime remain separate questions.

The log reports chip `0x0279`, hardware and ROM `0x8a00`, revision E1 and
patch extension `_e1`. This is an observed vendor selection, not a checked ROM
read receipt. In pinned `mtk_wcn_soc_ver_check`, the hardware read return is
assigned and checked, but the ROM read return is discarded and the previous
hardware return checked again. The ROM output is not initialized there.
Additionally, `wmt_core_reg_rw_raw` checks transport size and returned address
but does not validate the event header, status, type, reserved byte or count.
A future mainline selector must check each read independently and reject an
unrecognized chip/HW/ROM tuple before any patch or calibration effect.

## Exact source ordering and wire uncertainty

Pinned [register definitions](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/common/common_main/core/include/wmt_ic.h#L83)
define firmware register addresses `0x80000008` (chip), `0x80000000` (HW),
and `0x80000004` (ROM), each with mask `0x0000ffff`. These are firmware wire
addresses, not permission to access AP MMIO. The 20-byte opcode-0x08 read
request has operation 2, register type 1, reserved zero, count 1, the
little-endian address, input value and little-endian mask. The helper copies
the caller value into the request; chip storage is initialized to zero but
HW/ROM storage is uninitialized. A new constructor should supply a deterministic
zero read value instead of inheriting those undefined request bytes.

In [the pinned core](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L782),
mandatory STP is enabled, then `wmt_core_hw_check` reads chip/HW/ROM and selects
operations, then `sw_init` performs negotiation and common initialization.
Thus the complete owner must insert checked identity reads before the
[proved negotiation](../2026-10-03-mt6797-wmt-negotiate/results/runtime-1.json).
The earlier negotiation lifetime proves its scoped transport boundary; it
contains no such firmware-register replies and cannot prove applicability.

The source read-event array has 16 bytes, including returned address/value,
but declares a payload length of four bytes, as does the eight-byte write-event
array. The read helper uses the array size and ignores its declared length.
This inconsistency is source evidence only: neither a four-byte nor a twelve-byte
payload length is established on the wire by that template. Do not fix or loosen
a validator based on an assumption. Resolve the exact reply encoding from
attributable retained wire evidence or the selected firmware implementation
before using a version exchange to admit patch download. A separately reviewed
capture-only diagnostic can measure the unknown reply and stop without
accepting applicability. Require exact transport framing,
event size, header/status/count, address and checked value; preserve failure
outcomes without proceeding to patch download.

The remaining common-init gates include DLM register effects, checked MCU-clock
changes, PA ownership and calibration-result semantics. No candidate or support
claim follows from this review. Firmware remains private; file attribution does
not grant redistribution rights.

The [request preparation](IDENTITY_READ_PREPARATION.md) now constructs the three
selected read requests with deterministic value bytes. It records why the next
measurement needs a bounded mandatory-mode FIFO executor and a capture-only
stop; it implements no reply acceptance or hardware action.

The [completed chip-reply measurement](CHIP_REPLY.md) now resolves this encoding
for one actual pre-patch chip read: a 22-byte mandatory frame carries a 16-byte
WMT event with declared inner payload length 12 and chip value 0x0279. The strict
matcher recognizes only that measured response. HW/ROM encoding and values,
full tuple applicability, DLM effects and calibration remain unresolved.
