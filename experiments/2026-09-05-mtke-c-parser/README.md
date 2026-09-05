# Experiment: pure C MTKE structural parser

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-mtke-c-parser` |
| Status | completed, bounded host implementation only |
| Subsystem | Wi-Fi firmware container parsing |
| Device variant | Gemini MT6797 context; no device tested |
| Date | 2026-09-05 |
| Investigator | Codex implementation task; coordinator host review completed |
| Tracking | Coordinator-assigned offline parser handoff |

## Question and provenance

Can an original allocation-free C parser reproduce the accepted structural
contract of `parse_mtke` without file access or hardware effects?

The differential oracle is
`experiments/2026-09-05-mt6797-wifi-contract/scripts/wifi_firmware.py`
at integration revision `b441128eadf8cd834d74a5f8262d3a43e2d93778`, SHA-256
`4d8b57da9dabf20070aff27f6a5cc21f1f958c8b127af70ced8620a9be5c1f98`.
It is not present in this worker's older base; the test accepts an explicit
path and verifies its bytes before import. No vendor implementation or firmware
bytes were copied. Worker parent: `ff83bf63`.

## Safety and ownership contract

[mtke.c](mtke.c) consumes a caller-owned immutable memory span. It has no file,
device, allocation, transport, power, sequence, CONFIG or START operations.
Acceptance is structural only: it does not establish firmware identity,
redistribution rights, image eligibility, destination authorization, EMI mapping
or readiness to start firmware.

The caller must retain the input unchanged through CRC, validation and every
getter/use of a returned view. It must serialize parse/get operations and must
not alias context, input and output view storage. Initialize the context to zero
before first use; treat its fields as private implementation state. The
small context may use caller stack or heap storage. Context size is constant;
the parser rescans at most 256 entries with bounded pairwise comparisons, so it does not
need a multi-kilobyte section array or a payload copy.

Every parse invalidates the old context before examining input. Only complete
success publishes the source and validated count. A getter refuses invalid
contexts and out-of-range indices, clearing its output on refusal. Previously
returned views must be discarded before reparsing or releasing input. The C API
cannot enforce caller lifetime, concurrency or aliasing obligations.

Return 0 means accepted structure, -1 means invalid or unsupported structure,
and -2 means unknown reserved semantics, without declaring firmware corruption.
Unlike the inspection oracle's inconclusive result, reserved fields are refused.
This reason distinction does not promise the oracle's error precedence when
multiple defects coexist. A reserved-field return may occur before remaining
entries are checked; it does not validate the rest of the structure.

## Interface and validation

[mtke.h](mtke.h) exposes context, parse and indexed view access. Each view retains
source offset, length, pointer, original destination, ordinary/EMI route and
masked EMI offset. Raw encryption and key bytes remain distinct from ordinary
route boolean encryption and its masked two-bit key index. EMI entries never
acquire ordinary encryption semantics through these interpreted fields.

Checks include the 24-byte header, 16-byte entries, 1 MiB input and 256 section
caps, CRC over bytes 8 through end, nonzero lengths, source bounds and metadata
exclusion, source disjointness, 32-bit destination endpoints (exact 2^32 endpoint
permitted), ordinary destination disjointness, and masked EMI ranges within
512 KiB with disjointness. Header bytes 12 through 19 are not newly constrained;
they remain CRC-covered, matching the oracle. Unreferenced bytes are allowed.

[crc-kernel.c](crc-kernel.c) adapts the standard Linux `crc32_le` API using the
initial/final complement required by the oracle's zlib convention. Future
integration must enable the appropriate kernel CRC dependency. No duplicate
kernel CRC algorithm is supplied. The host fixture links system zlib instead.

## Reproduction and observations

Run from the repository root, supplying the pinned oracle from a checkout that
contains it:

```sh
python3 experiments/2026-09-05-mtke-c-parser/test-parser.py --oracle ORACLE_PATH
```

[test-parser.py](test-parser.py) creates a scoped temporary host library and
removes it on completion/failure. It compiles the pure C parser with C99,
`-Wall -Wextra -Werror -Wconversion -pedantic`, using the host C compiler.
Compiler: Apple clang 21.0.0, arm64 host. Only synthetic bytes enter the library.
No private firmware file is opened.

Observed: **4,487 differential cases passed; 1,228 accepted containers had every
view compared**. Coverage includes truncated inputs, caps, header and entry
mutations with both stale and recomputed CRCs, reserved semantics, source and
destination boundaries, exact 32-bit endpoint, masked EMI aliases and window
edges, truthy encryption bytes, key masking, deterministic random mutations,
null arguments, failed-parse invalidation, and out-of-range getters. Accepted
length/count/encryption summaries come from the Python oracle; raw fields and
payload addresses/bytes are checked independently against synthetic entries.

## Conclusion and integration limits

Confirmed only for the stated synthetic host suites. The standalone ASan+UBSan
suite passed **4,563 exact-allocation cases**,
including short allocations (without spare NUL bytes), truncated tables through
256 entries, source/destination edges, exact cap and cap+1, payload endpoint
reads, and successful-then-failed parse/getter revocation. Run
`python3 experiments/2026-09-05-mtke-c-parser/test-memory.py`; it compiles
[test-memory.c](test-memory.c) with both sanitizers and fail-fast recovery
disabled, executes it, and removes temporary output.

The common repository publication gate passed, including 189 profile checks
and eight rejected manifest mutations. Linux-only provenance checks were
explicitly skipped on this host. The three pre-existing eMMC enablement changes
remain outside this experiment commit.

Kernel-style preparation uses native `u8`/`u32` types under `__KERNEL__`,
with standard fixed-width host aliases only outside the kernel, tab indentation
and kernel block-comment conventions. Checkpatch was unavailable locally and
was not run; this manual preparation is not a checkpatch receipt.

No kernel build, kernel CRC adapter compilation, firmware load or hardware
test was performed. This is proposed source, not a kernel patch or upstream
submission, and has no fabricated author certification. Kernel integration owns
adaptation to its image eligibility and ordinary HIF interface; views do not
imply EMI permission. Replace this experiment implementation when a reviewed
upstream loader owns the equivalent contract. Ordered work remains in the
[roadmap](../../docs/ROADMAP.md).

## Integration review

The coordinator reviewed the seven-file handoff at `eb38185e` and independently
reproduced both host suites: 4,563 sanitizer cases and 4,487 differential cases,
including 1,228 accepted containers with all views compared. The review checked
subtraction-based source bounds, destination endpoint overflow, pairwise overlap
checks, context invalidation and the immutable-input lifetime contract. No
blocking defect was identified within that structural-parser scope.

Kernel CRC compilation and Checkpatch remain outstanding. Integrating these
experiment sources does not select a kernel profile or admit a device session.
