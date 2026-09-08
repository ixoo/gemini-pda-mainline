# MD1 reservation tail in the retained loader

## Result

The extra 32 MiB in the [Gemian reservation observation](GEMIAN_HANDOFF.md)
has a concrete loader-side explanation: the public loader allocates a maximum
image region, then records the unused portion for deferred reclamation. Bounded
static analysis of the retained LK corroborates the deferred-tag branch.
This is an explanation consistent with the observed reservation, **not proof
of the actual tags emitted on that boot or permission to reclaim memory**.
Preserve the complete 160 MiB MD1 reservation.

## Source mechanism

The [source and binary receipt](results/loader-tail-audit-20260908.json) pins
individual public LK files at `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
The source is evidence only; no vendor implementation is copied into this
repository and no source-to-installed-binary equivalence is asserted.

| Step | Source location | Meaning |
| --- | --- | --- |
| Initial allocation | `ccci_ld_md_core.c:441–446`, `253–286` | Normal MD1 main-image maximum is `0x0a000000` (160 MiB); allocation uses the maximum. |
| Header requirement | `ccci_ld_md_ass.c:330–337` | A requirement exceeding the allocation is rejected; otherwise the reported reservation requirement becomes the header's memory size. |
| Successful-load tail | `ccci_ld_md_core.c:419–426` | After cache synchronization, differing allocated and required sizes reach the unused-memory helper. |
| Deferred policy | `ccci_ld_md_api_wrapper.c:213–238` | The mblock-v2 build condition sets `free_in_kernel` to 1 and exports it as a four-byte tag. |
| Tail arithmetic | `ccci_ld_md_api_wrapper.c:128–144` | For a positive smaller requirement and deferred policy, report `(base + required, allocated - required)`; otherwise use the resize branch. A zero requirement preserves the default allocation. |
| Deferred record | `ccci_ld_md_api_wrapper.c:111–125`, `ccci_ld_md_padding.c:528–539` | The mblock-v2 retrieve helper records a tag without returning the range to LK. Each `retrieveN` carries two 64-bit values: address and size. |
| Record count | `ccci_ld_md_core.c:676–677` | `retrieve_num` exports the number of records. |

Applying this arithmetic to the independently observed base, allocation and
header requirement yields `0xbc000000 + 0x02000000`, exactly the reserved tail.
That arithmetic does not establish that the tail was unused throughout boot,
that the tag insertion succeeded, or that it is safe to release now.

## Retained LK corroboration

Analysis used the RE VM and the existing 524,288-byte LK capture with SHA-256
`75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c`.
Its capture identity and ARM32 Thumb mapping are already recorded in the
[boot-selection audit](../2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt).
No partition was reread and no firmware was executed. Function names below
are inferred by matching strings, arguments and control flow, not symbols.

The loader routine calls the wrapper initializer at `0x4603b4c6`. The initializer
at `0x4603aa18` writes 1 to `0x460721e0`; the tag exporter at `0x4603aa34`
passes that same location and length 4 with the `free_in_kernel` name. The
reservation helper at `0x4603a860` tests the same flag and its nonzero branch
passes the extended allocation flag 1. These are compiled behavior observations,
not just matching diagnostic strings.

The unused-memory helper at `0x4603a930` checks for zero and for a smaller
requirement, reads that same flag, and passes base-plus-requirement and
allocation-minus-requirement to `0x4603a910`. That helper calls `0x46038fc0`
and returns zero without a memory-release call. The callee constructs the
`retrieveN` name and submits a 16-byte address/size pair. The successful-load
path compares sizes at `0x4603b41c` and calls the unused-memory helper at
`0x4603b42c` when they differ. This corroborates the deferred mechanism; this
bounded analysis does not independently recover the complete image table,
header parser, tag insertion success or execution history.

## Kernel consumer and limits

A whole tracked-tree search of the pinned public Planet kernel
`c5b0be85017ad0c599725e8273842efdbecdd88a` found no matches for
`free_in_kernel|retrieve_num|retrieve[0-9]|retrieve_info|retrieve_mem`.
The exact command and no-match exit status are recorded in the receipt.
This is a negative literal/symbol search, not proof against an indirect,
differently named or out-of-tree consumer. It also does not attest the complete
source of the running Gemian kernel. The earlier
[access-source comparison](results/gemian-handoff-access-sources.json) establishes
only selected file equality with the pinned Gemian source.

Together, the source, retained binary and observed memblock reservation support
deferred reclamation without a demonstrated consumer as the explanation to
pursue. They do not close runtime attribution: the consumed LK tag buffer was
not read, the retained July LK capture was not re-attested on the September
boot, and the actual loaded modem image digest remains unknown. Secure MPU
acceptance/lock authority and shared MD3 lifetime also remain unresolved.
No new mapping, release, driver, firmware load or radio experiment is admitted.

## Reproduction and validation

Use the pinned individual source URLs and hashes in the receipt. On the RE VM,
verify the existing private LK digest, map the raw file at `0x45fffe00` with
radare2 5.5.0 in ARM Thumb mode, and inspect the bounded addresses listed above.
The receipt includes the disassembly command and private output digest; raw
firmware, disassembly and unrelated strings remain outside Git. Run the
recorded kernel search in its existing Buildbox bare source cache.

Source hashes, PC-relative flag/string addresses, tag widths, call targets and
tail arithmetic were checked. Repository validation and staged whitespace,
local-link and sensitive-data checks passed before publication. This was offline
analysis and documentation only: no kernel build, device access or hardware
support test occurred. Gemian custody remains released.
