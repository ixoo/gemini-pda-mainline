# Independent review of the finite PIO primitive

## Result and exact scope

No correctness defect was found in the reviewed scalar callback implementation
at `54c9caac9aa947774b312107e1cb57904c912f50`. This review inspects the actual
`hif_pio.h`, command encoder and transfer-size helper, then runs the author's
fixture and an independent boundary/fault oracle with AddressSanitizer and
UndefinedBehaviorSanitizer. [Results](results.json) identify every input by hash.
It does not review a real MMIO adapter, compile the kernel include branch or
admit a device operation. No backend or device was accessed.

## Implementation findings

The command encoder validates the selected direction/port and PIO-only padded
capacity before the first callback. For 1–508 payload bytes, the transfer is
rounded to four bytes; 509 and above enter 512-byte block mode. The maximum is
511 blocks, 261,632 bytes. Thus the four-byte loop and byte additions cannot
wrap on the target's 32-bit unsigned-int/64-bit size types. This is a source
argument, not a separate 32-bit execution result.

TX constructs each numeric word with byte zero in bits 0–7 and byte three in
bits 24–31. Casting before the shift avoids signed-byte promotion. It reads
only positions below the logical payload length and starts every word at zero,
so partial-word and full-block padding do not disclose stale buffer contents.
TX does not modify storage. RX extracts the same low-to-high byte ordering and
stores the entire padded transfer, which is why capacity must cover the encoded
span rather than only the logical payload. Byte accesses permit unaligned
buffers. The documented scalar readl/writel adapter is part of this contract;
substituting repeated FIFO accessors needs a separate endian/ordering review.

There is exactly one callback to write setup at offset zero before any data
callback. Every subsequent access uses offset `0x1000`; the address is not
advanced with buffer position. The C call sequence establishes callback order,
not posted-write completion on real hardware. The caller still holds lifetime,
ownership and setup/data serialization as documented by
[the reviewed primitive](https://github.com/ixoo/gemini-pda-mainline/blob/54c9caac9aa947774b312107e1cb57904c912f50/experiments/2026-09-05-mt6797-wifi-contract/HIF_PIO.md).

A failed setup prevents data calls. A failed data callback terminates immediately
without retry; RX does not copy a value returned with an error. `data_bytes`
counts only successfully returned words, and `setup_submitted` records a
successfully returned setup callback. These fields do not establish absence of
hardware side effects on a failing access and are not a recovery cursor.
Clearing the result before validation is correct under the documented requirement
that buffer, result and I/O seam objects are distinct, valid and stable.

## Independent checks

[The independent C oracle](boundary-test.c) checks 10,041 calls:

- Every payload length 1–1,025 and the maximum minus three through maximum plus
  one, for TX and both RX ports, with capacity one below, equal to and one above
  the independently calculated span.
- Exact literal setup encoding, setup-first sequencing, fixed data offsets,
  varying high-bit byte patterns, full RX padded output and surrounding canaries,
  unchanged TX payload/padding, and exact success/refusal accounting.
- All 257 possible failing callback positions for a 513-byte/block-padded
  transfer in all three direction/port combinations. No later callback or
  failed RX word store is accepted.

TX padding is additionally poisoned using ASan's interface; this catches reads
of poisoned padding even if the value would later be discarded. Poisoning has
ASan granularity limits, so the independent expected-word assertions also check
zero padding at every partial-word boundary. The original fixture covers null
pointers/callbacks, invalid fields and its literal sample words.

Five implementation mutations are rejected by attributable assertions or
sanitizer failures: reversed TX bytes, reversed RX bytes, wrong setup offset,
storing failed reads and removed capacity checks. [The runner](verify.py)
extracts only the four project-owned inputs from the exact Git commit into a
managed temporary directory, compiles with strict C11 warnings plus sanitizers,
and removes temporary state on success/failure. It does not fetch kernel sources
or reconstruct the tested implementation in the oracle.

All checks passed on the recorded host compiler. This establishes the bounded
scalar callback behavior only. Resource ownership, actual bus ordering/flush,
credits, response framing, selected extra-RX policy, firmware completion and
recovery remain the caller/integration contracts. No new blocker or broader
runtime claim is introduced by this review.

The common repository gate passed for this four-file review packet (190 profiles,
unchanged metadata debt 37), as did syntax, local-link and sensitive-data checks.
Linux-only package-provenance fixtures were skipped locally and remain CI-only.
