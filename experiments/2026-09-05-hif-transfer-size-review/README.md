# Independent review: HIF transfer-size helper

## Record and decision

Completed source and host review on 2026-09-05 of published Wi-Fi revision
`b3e056c7f661ebd4533061d39c62d6bbb2b7efda`. **Accepted for its stated pure
packet-DMA arithmetic scope; no concrete helper defect found.** The author's
files were read at that exact Git revision and were not changed.

Owning [HIF contract](https://github.com/ixoo/gemini-pda-mainline/blob/b3e056c7f661ebd4533061d39c62d6bbb2b7efda/experiments/2026-09-05-mt6797-wifi-contract/HIF_DMA_CONTRACT.md),
[helper](https://github.com/ixoo/gemini-pda-mainline/blob/b3e056c7f661ebd4533061d39c62d6bbb2b7efda/experiments/2026-09-05-mt6797-wifi-contract/src/hif_transfer_size.h)
and [author's fixtures](https://github.com/ixoo/gemini-pda-mainline/blob/b3e056c7f661ebd4533061d39c62d6bbb2b7efda/experiments/2026-09-05-mt6797-wifi-contract/src/hif_transfer_size_test.c)
remain separate from this independent review. No hardware-support conclusion,
selected kernel profile, backend or device action follows from this acceptance.

## Source contract cross-check

Read and hash-verified four decisive public files at Planet pin
`c5b0be85017ad0c599725e8273842efdbecdd88a`, against the author's published
[source ledger](https://github.com/ixoo/gemini-pda-mainline/blob/b3e056c7f661ebd4533061d39c62d6bbb2b7efda/experiments/2026-09-05-mt6797-wifi-contract/results/hif-dma-sources.json):

| File under gen3 `os/linux/hif/ahb_sdioLike/` | SHA-256 | Decisive observation |
| --- | --- | --- |
| `ahb.c` | `d9b4e80fe98695284627e495ad640e39728ebe7df235df129f64d48e8a2e726b` | RX lines 811–836 and TX 1093–1114 round to four bytes before choosing blocks; RX DMA byte mode rounds to eight |
| `include/sdio.h` | `adc07b543c958e85332cb68eae1a457a590465ef547309fd4fa45989f68b55b4` | nine-bit command count, fixed 512-byte block definition |
| `include/hif_pdma.h` | `898874f9f3180000a393fab0a13666fd4960364f3c4b7517a1f965f027213028` | channel length field bits 0–19 |
| `ahb_pdma.c` | `83c23a5582be2dcaa385359b7cd0f82af0ec9d6a4e102ea6faea57f59d75b480` | line 265 masks configured length through that field |

These were bounded public reads in memory; no vendor implementation is copied
into this review. This checks sizing, not the complete DMA/EMI ownership contract.
The source's eight-byte RX rule is conditional on DMA and excludes its WHISR
register read. The helper is consequently appropriate only for the selected
packet-DMA contract, not every register/PIO transfer or another block size.

## Arithmetic and boundary findings

The initial `1..261632` payload gate precedes every addition. Its largest
four-byte round-up intermediate is 261635, and the later block-rounding
intermediate is at most 262143. Neither can overflow 32- or 64-bit `size_t`.
The largest accepted DMA length is 261632, below the 20-bit limit. Thus the
command-count policy is the tighter bound; the 20-bit check is defensive and
cannot independently fire for an otherwise admitted payload under this policy.

The independent oracle uses explicit payload intervals: block mode starts at
509, byte-mode TX pads to four, byte-mode packet RX pads to eight. It computes
padding with a remainder expression, independently of the helper's bit masks
and two-stage rounded-count calculation. Block results are multiples of 512
with counts `1..511`. Byte counts are nonzero and at most 511.

RX payloads 505–508 pad to 512 while staying in the source-selected byte mode;
refusal matches the documented exclusion of ambiguous zero-count encoding.
Payload 509 instead enters block mode with count one. This non-monotonic
admission boundary is intentional and must not be normalized by callers.
Capacity is compared against the final padded DMA length. Every non-null
failure clears all three output fields; null output returns `-EINVAL`.

## Host evidence and reproduction

[verify.py](verify.py) reads only the two exact published Git objects, checks
their SHA-256 values, and compiles both the author's original test and the
independent [exhaustive fixture](exhaustive.c) with AddressSanitizer and
UndefinedBehaviorSanitizer. Run from this repository:

```sh
python3 -B experiments/2026-09-05-hif-transfer-size-review/verify.py
```

[Results](results.json): the author's 30 cases plus null-output check pass.
The independent fixture passes 3,672,080 calls: all payloads `0..262144`, both
directions and seven capacity choices around payload/padded boundaries, plus
`SIZE_MAX` down through `SIZE_MAX-1024` in both directions. Duplicate boundary
capacity choices are intentionally counted as calls, not distinct tuples.
Null output is checked separately. No sanitizer diagnostic was emitted.

Four separately compiled mutations fail at attributable cases: removing the
capacity check, admitting command count 512, delaying block mode to payload
512, and preserving stale failure output. They are rejected by result checks,
not a compiler error or arbitrary crash. Mutation binaries are unsanitized;
the original and exhaustive unmodified binaries carry both sanitizers.

Temporary files are context-managed under ignored
`artifacts/hif-transfer-size-review/` and removed on exit. Fixed compiler/test
commands have a 30-second deadline, process-group cleanup, no core dumps and a
16 MiB per-file write limit. Captures above 64 KiB refuse. Exact Git reads have
a ten-second timeout. No author's worktree file is edited.

## Limits and handoff

Runtime fixtures use the recorded host's 64-bit `size_t`; the 32-bit overflow
statement is a mathematical bound, not a 32-bit ABI execution claim. Kernel
includes and integration were not compiled. No packet buffer is allocated or
mapped by the helper, so caller-reported capacity truthfulness, TX padding
initialization, actual buffer alignment/cache ownership, address encoding,
channel serialization, completion/quiescence, IRQ and firmware/EMI ownership
remain outside this test. The review does not admit active DMA or change the
existing hardware gates. Root can adopt the arithmetic component with these
same scope limits; no correction is requested of its author.

Common repository checks passed with four changed files, 190 profiles and
unchanged grandfathered metadata debt (37). Python syntax and diff checks
passed. Kernel build, checkpatch, DT schemas and device tests were not run.

## Integration assessment

Project Planning reviewed the original helper, contract and fixtures plus this
independent interval oracle and mutation results. The nine-file component and
review are adopted without selecting a driver, DMA mask or device test. The
integration run independently reproduced the original 30 cases, 3,672,080 oracle
calls and all four targeted mutation refusals under the recorded host ABI.
This closes arithmetic review only; the resource and runtime limits above remain.
