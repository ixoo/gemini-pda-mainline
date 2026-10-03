# Checked pre-negotiation version-read owner

Status: hardware-free draft. No kernel caller, profile, candidate or live
chip/HW/ROM tuple acceptance is admitted by this checkpoint.

The [measured chip response](CHIP_REPLY.md) resolves opcode-0x08 register-read
framing for the chip exchange. The existing [request constructor](IDENTITY_READ_PREPARATION.md)
selects chip/HW/ROM addresses in that order with deterministic input values.
This draft supplies the missing checked IRQ reader and finite three-read owner.
It stops before negotiation, patching, DLM, MCU-clock writes, calibration or WLAN.

## Exact acceptance and remaining inference

`tests/wmt-version-reply.h` accepts only a complete 22-byte mandatory frame:
measured header 0x80/0x40, outer payload size 16, event type 2/opcode 8, inner
payload size 12, status/type/reserved bytes zero, count one, the selected echoed
address, exact 32-bit value and two zero trailer bytes. The chip address/value
are measured (0x80000008 / 0x00000279). The HW and ROM variants require addresses
0x80000000 and 0x80000004, respectively, and the vendor-reported value
0x00008a00 for each. The common format and HW/ROM values are hypotheses until
attributable live reads. This deliberately rejects a different tuple or event
encoding; it does not repair, guess or fall back to E1 selection.

A future identity-only measurement can test these strict hypotheses using the
selected read requests. It must retain the first unknown reply and stop, rather
than loosen acceptance or issue later reads after failure. No firmware or radio
operation is needed to measure them. Even a validated tuple does not resolve the
remaining common-init effect contracts or independently admit firmware transfer.

## Checked leaf and finite ordering

`tests/mt6797-wmt-version-io.h` reuses the reviewed capture leaf's bounded FIFO
accounting, exclusive IRQ retirement and retained failure lifetime. It supplies
the ordinal to the existing constructor. Each persistent read owns one attempt,
26 THR writes, at most 22 RBR reads, 64 services including the initial kick,
eight RX bytes per service and a maximum 500-ms deadline. Early/stale RX,
nonempty initial TX, unexpected IRQ causes, incomplete replies, unknown bytes,
queued trailing RX and deadlines refuse success. The final-byte and final-IIR
deadline checks prevent complete-looking late data from being accepted.

Success requires the complete expected reply and no queued RX in the last IIR
observation. It retires source/CPU IRQ, synchronizes and frees the sole initially
disabled registration. A timeout never indicates identity acceptance. No reset,
flush, DMA start, clock acquisition or setup repetition is added by this leaf.
The original raw chip-capture executor remains unchanged historical evidence.

`tests/mt6797-wmt-versions.h` holds three persistent leaf records and consumes its
whole attempt before the first read. The caller must hold the shared CONSYS mutex
and supply the exact BTIF mapping/IRQ after the reviewed setup with retained
clocks. The owner prepares and runs chip, then HW, then ROM, each only after the
preceding zero result. It clips each 500-ms exchange to a whole 1500-ms budget,
checks that budget before and after each exchange and records the first failure.
It returns success only after all three checked replies. Maximum combined effect
counts are 78 THR writes, 66 RBR reads, 192 services and three sequential exclusive
IRQ registrations. No scheduling/framework hard real-time guarantee is claimed.
Power/clocks and completed-step evidence remain retained on every failure.

## Validation and boundary

[Validation](results/version-read-owner.json) covers actual IRQ/MMIO leaf code
for all three semantic reply variants, 16830 one-byte corruptions, every TX and
RX expiry position, incomplete replies, fragmented arrivals, extra queued RX at
a quota boundary, last-IIR expiry, early/stale RX, stuck TX, consumed attempts,
registration failure and balanced IRQ retirement. The owner fixture separately
checks ordering, preparation/exchange failure at every ordinal, whole-budget
expiry, pristine prerequisites and no retry; its leaf operations are mocked.
Both execute under ASan/UBSan with Wall/Wextra/Werror. The pure matcher also
passes the existing strict C11 chip corruption fixture and private sealed chip
reply; this verifies that the new ordinal-zero acceptance preserves the measured
chip contract. It supplies no live evidence for the HW/ROM variants.

All three authored headers pass strict Checkpatch (zero errors/warnings/checks).
An additional conversion/pedantic build of the IRQ fixture fails on inherited
full-STP codec conversions and GNU void-MMIO arithmetic, plus the fixture's
completion return conversion; the ordinary kernel-style fixture flags pass.
No unrelated codec cleanup or diagnostic suppression was introduced. No kernel
build, binding/DT change or device test is claimed for this draft. Next integrate
a default-off identity-only caller, then Buildbox compile, candidate validation,
guarded deployment and one unique version-tuple measurement.
