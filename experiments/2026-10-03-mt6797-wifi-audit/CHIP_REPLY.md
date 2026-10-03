# Measured chip reply and strict offline matcher

The [retired capture lifetime](../2026-10-03-mt6797-wmt-identity-capture/SESSION.md)
retained exactly 22 bytes after one deterministic pre-negotiation chip read.
Complete sealed-log evidence accounts for the 26 transmitted bytes and six
services. The mandatory-mode envelope reports a 16-byte WMT event. That event
has type 2, opcode 8, declared payload length 12, status zero, three zero bytes
across status/type/reserved fields, count one, echoed address 0x80000008 and
32-bit value 0x00000279. Both mandatory trailer bytes are zero. This is the
observed chip response, not an assumption based on the inconsistent vendor
read-event template.

`tests/wmt-chip-reply.h` is a hardware-free matcher for this exact measured
variant. It checks the whole caller-supplied frame and requires exactly 22 bytes;
no scanning, partial acceptance, trailing data or unknown sequence variant is
accepted. It exposes no I/O or continuation. Exact chip matching does not select
a ROM patch: HW/ROM reply encodings and values are still unmeasured, and the full
applicability tuple remains unresolved. Do not widen the matcher or carry the
vendor unchecked-return policy into a future identity owner.

[Validation](results/chip-reply-validation.json) records strict C11 warnings,
ASan/UBSan, 5675 refusals and positive matching against a private extraction from
the complete sealed log. The public test constructs a semantic protocol fixture;
it does not publish a raw capture. Per-byte alternate values exercise header,
status, count, address, chip value and trailer corruption; every other supplied
length from 0 through 64 and a null input are refused. These checks prove offline
recognition of the observed chip response only. There is no kernel integration,
new boot candidate or live acceptance claim.

The next identity owner must obtain checked chip/HW/ROM reads before negotiation.
A separately reviewed HW/ROM measurement is decision-changing; an identical
chip-only capture repeat is not. Common-init writes and calibration remain behind
their own exact effect and failure-lifetime contracts.
