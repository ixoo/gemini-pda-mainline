# Experiment: retained ram-console copy-owner audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-retained-ram-console-copy-owner-audit` |
| Status | completed source audit; copy owner selected; secure-epoch authority unresolved |
| Subsystem | MediaTek retained ram-console, reserved memory, and A34 provenance |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Can mainline take one immutable copy of the exact Gemini ram-console
reservation without modifying or persistently mapping it, and does any newly
audited ordering fact independently prove the fresh secure-platform epoch
required by A34?

The two parts are deliberately independent:

1. a normal platform consumer can bind the existing reservation through a DT
   `memory-region`, validate its exact contract, map it with ordinary-memory
   semantics only long enough for one full copy, and unmap before parsing; and
2. firmware-writer ordering or that copied reset history can prove that the
   exact secure payload was freshly loaded with its private A72 replay state
   initialized from the image.

## Provenance and environment

- Repository input: signed and pushed commit
  `1d0b3c55d8743d0fa2983dda0a228e5a61e6d41b`.
- Kernel source: Linux 7.1.3 archive with SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`,
  inspected in the managed Buildbox prepared tree.
- Canonical board reservation: patch `0020`, which describes
  `[0x44400000, 0x44410000)` as anonymous `no-map` reserved memory.
- Canonical parser: patch `0304`, which consumes only a caller-owned byte
  buffer and has no mapping operation.
- Planet LK: [`dguidipc/gemini-lk-android8`](https://github.com/dguidipc/gemini-lk-android8/tree/f4988d74bb70a0a15d7f362f412afba7e7fcda46)
  at `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Gemian kernel: [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/d388d350cb2dda8f23b99be6fa5db9628896e87f)
  at `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Exact file hashes and observations are frozen in
  [`results/source-provenance-20260821.txt`](results/source-provenance-20260821.txt).

## Safety assessment

This was a read-only public-source audit. It used temporary partial Git clones
on Buildbox and the existing prepared kernel tree. The temporary directories
were removed by cleanup traps. It did not access the Gemini, map live retained
RAM, build a kernel, create a boot image, write `boot2`, reboot, or request a
CPU.

The selected future implementation is also read-only with respect to the
physical reservation. It must not write, clear, repair, retry, expose, or keep
a mapping of the retained bytes. This audit does not authorize a boot
candidate or device attempt.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the selected copy-owner and its rejected
  alternatives.
- [`results/source-provenance-20260821.txt`](results/source-provenance-20260821.txt)
  records exact source identities and writer/mapping facts.
- [`results/decision-matrix.tsv`](results/decision-matrix.tsv) separates the
  mapping decision from the secure-epoch decision.
- [`scripts/validate.py`](scripts/validate.py) checks the frozen source inputs,
  decision inventory, exclusions, and publication hygiene.

## Procedure

1. Inspect the exact Linux 7.1.3 reserved-memory lookup, platform population,
   `memremap()`, arm64 `no-map`, and existing reserved-memory consumer paths.
2. Search the prepared tree for all Gemini ram-console physical-address,
   signature, mapping, and writer references.
3. Inspect exact pinned LK initialization and mutation paths, their call
   placement before Linux handoff, and the target platform header/config.
4. Inspect the exact pinned Gemian early ram-console copy and every mutation
   immediately following it.
5. Compare direct reserved-node binding, generic `nvmem-rmem`, a hard-coded
   physical address, and a normal root platform consumer with a
   `memory-region` phandle.
6. Evaluate transient `MEMREMAP_WB` against a persistent mapping and prove why
   it has ordinary-memory rather than I/O-copy semantics on arm64 `no-map`
   System RAM.
7. Re-evaluate secure-epoch authority separately; do not promote mapping or
   writer ordering into a reset/epoch classifier.

## Observations

Linux marks the existing reservation `MEMBLOCK_NOMAP`. On arm64 that keeps the
range out of the direct map, makes `pfn_is_map_memory()` false for the range,
and permits `memremap(..., MEMREMAP_WB)` to establish an explicit cacheable
ordinary-memory mapping. This is the appropriate primitive for retained DRAM:
the bytes have no I/O read side effects, and an `__iomem` access loop would
misdescribe the resource.

Linux 7.1.3 already contains the narrow pattern needed here. The generic
reserved-memory NVMEM driver maps a `no-map` reservation with `MEMREMAP_WB`
only for a requested read, copies into caller memory, and immediately unmaps
to reduce unintended writes. It is useful implementation evidence, but it is
not the correct owner: its binding admits a different bootloader-data
provider contract, registers a general NVMEM interface, and may remap on
multiple consumer reads.

A new compatible placed directly below `/reserved-memory` would not receive a
platform device automatically. The exact OF population code has a small
whitelist for such children. A normal root child is populated without that
exception and can refer to the anonymous reservation through `memory-region`.
`of_reserved_mem_region_to_resource()` resolves that phandle to the registered
reserved-memory range. The driver can separately resolve the same phandle to
require `no-map`, then require the exact 64 KiB resource before mapping.

The prepared mainline tree through patch `0304` has no physical ram-console
reader or writer. Its only exact address reference is the board reservation;
its only signature reference is the pure parser. Therefore no concurrent
mainline writer exists in the selected configuration.

Pinned LK chooses the DRAM ram-console when the SRAM signature is absent.
`ram_console_init()` derives current/prior LK and Linux offsets, copies the
current LK record to the prior-LK record, and can clear an invalid Linux
`fiq_step`; LK helpers also write its current record and dump step. Those LK
operations occur while LK owns execution, before the non-returning Linux
handoff. A Linux probe therefore observes LK's final handoff state, not an
immutable pre-LK record.

The pinned vendor kernel demonstrates the opposite Linux-side ordering.
`ram_console_early_init()` runs as a `console_initcall`, maps the physical
range, copies the entire buffer to `ram_console_old`, and then rewrites header
fields, clears invalid content, sets Linux/console fields, and zeroes from the
Linux offset to the end. Later logging continues to write the live range.
This proves why an immutable reader must copy before any future mutable
mainline ram-console driver. It does not create a conflict in the current
mainline series because that writer is absent.

No complete public preloader source or independently attested secure-payload
load event was found. LK's completed execution before Linux establishes a
writer boundary for the copied ram-console bytes, but it says nothing about
whether the secure payload was freshly loaded or whether private replay state
survived an earlier epoch.

## Analysis

The mapping hypothesis is confirmed at source-contract level. The smallest
honest owner is a default-off MediaTek platform driver attached to a normal DT
consumer node. It accepts one `memory-region`, requires that target to be
available and `no-map`, requires exactly 64 KiB, allocates one caller-owned
buffer, performs one transient `MEMREMAP_WB` mapping to copy once at probe,
unmaps before parsing, and publishes only the parser's typed immutable raw
snapshot. Every failure leaves the snapshot invalid. There is no physical
address fallback, repeated read, persistent pointer, binary export, or write.

The implementation should retain the exact Gemini range in DT rather than
duplicate `0x44400000` in C. Its safety identity is the consumer's sole phandle
to the named 64 KiB `no-map` reservation. Static source/DT validation must pin
that phandle back to the exact existing range for the Gemini profile.

Probe-time ordering is sufficient only because the exact current mainline
tree has no other ram-console writer. If a mutable owner is added later, the
copy owner must become its explicit predecessor or both must be replaced by a
single owner. The copy operation must never silently coexist with a writer
whose earlier init level is not proven.

The secure-epoch hypothesis remains inconclusive. The audit adds no new
independent epoch bit, loader measurement, or secure-world attestation.
Ram-console status, raw TOPRGU status, LK boot reason, LK completion, and a
manual report of a cold-looking boot are still reset-path evidence. None proves
the exact secure image initialized private replay state in the current epoch.
Combining them remains forbidden.

## Conclusion

`confirmed` for the source-level, one-shot immutable copy owner described in
[`DESIGN.md`](DESIGN.md). This selects a default-off implementation and
Buildbox/KUnit validation boundary; it is not hardware support and cannot yet
prove the physical mapping path on Gemini.

`inconclusive` for independent fresh secure-platform-epoch attestation. The
production A34 owner and CPU8/CPU9 admission remain CLOSED.

## Follow-up

Implement the selected mapping/copy owner as one reviewable default-off patch
plus binding and Gemini DT consumer, and prove all injectable copy/publication
semantics without physical mapping. Build it only on Buildbox. Do not add a
reset classifier, secure-epoch combiner, A34 caller, lifecycle publication,
provider effect, P30 arm, PSCI call, CPU-veto change, boot image, or device
attempt.

In parallel conceptually—but not by combining reset-history values—continue
seeking a pinned preloader or secure-loader contract, a measured loader event,
or a secure-world read-only attestation that is independent of Linux reset
history.
