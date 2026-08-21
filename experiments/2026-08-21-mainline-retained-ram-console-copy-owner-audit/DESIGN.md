# Immutable retained ram-console copy owner

## Selected layering

```text
anonymous 64 KiB no-map reservation
  <- memory-region phandle from a normal platform node
  -> one transient MEMREMAP_WB mapping
  -> one complete copy into private kernel memory
  -> immediate memunmap
  -> proven strict parser
  -> immutable typed raw snapshot
```

The mapping owner is a transport boundary. It does not interpret reset status
and does not supply secure-epoch authority.

## DT contract

Retain the existing reservation and give it a label; do not place a new driver
compatible directly on the reserved-memory child. Add one normal default-off
platform node with:

- a MediaTek ram-console consumer compatible;
- exactly one `memory-region` phandle to the existing reservation; and
- `status = "disabled"` in reusable SoC/board policy unless a named experiment
  profile explicitly enables it.

The Gemini source validator must resolve that phandle to base `0x44400000`,
size `0x10000`, and `no-map`. The driver must not contain a fallback physical
address.

## Probe contract

The production probe must execute these steps exactly once:

1. clear the private output snapshot;
2. parse the sole `memory-region` phandle and reject a missing, unavailable,
   multiply specified, or non-`no-map` target;
3. resolve it with `of_reserved_mem_region_to_resource()`;
4. require resource size `0x10000` and reject wraparound;
5. allocate exactly one 64 KiB caller-owned buffer;
6. call `memremap(resource.start, resource_size, MEMREMAP_WB)` once;
7. copy all 64 KiB exactly once using ordinary-memory copy semantics;
8. call `memunmap()` before parsing or publication;
9. invoke `mtk_ram_console_parse()` on only the private copy; and
10. publish the typed snapshot once only when parsing succeeds.

The physical pointer must be local to the copy helper. No devres-held mapping,
global pointer, retry, partial copy, lazy consumer read, debugfs/procfs/NVMEM
export, or raw-byte publication is permitted.

## Test seam

Factor the copy/publication state transition from physical discovery so KUnit
can inject ordinary source bytes and a copy callback. Focused tests must cover:

- invalid source and output arguments;
- exact one-copy/one-publication success;
- source-copy failure with invalid output;
- parser failure with invalid output;
- a second capture or publication refusal;
- every raw status bit preserved through copy and parse;
- copy independence after source mutation; and
- no status classifier or A34 lifecycle call.

Build and KUnit can prove the software state machine. The real
`memory-region`/`MEMREMAP_WB` branch remains compile- and source-reviewed until
a separately justified device observation exists.

## Writer ordering invariant

At the selected revision, LK owns and may mutate the region before its
non-returning handoff, and mainline has no physical ram-console writer. The
probe therefore copies LK's final handoff state before any Linux writer
exists.

Future code that writes the region invalidates this invariant. It must either
depend on completion of the copy owner or replace it under one reviewed owner.
An undocumented initcall race is a hard failure, not a tolerated timing
assumption.

## Rejected alternatives

- a magic `0x44400000` mapping in C;
- direct binding under `/reserved-memory` by expanding the OF whitelist;
- generic `nvmem-rmem` registration or any userspace-readable raw provider;
- `ioremap()`/`readl()` byte loops for ordinary retained DRAM;
- `devm_memremap()` or another persistent writable mapping;
- mapping only the four-byte status word before header validation;
- retrying after a mapping, copy, or parser failure;
- parsing directly from the physical mapping;
- using probe success as fresh secure-epoch evidence; or
- combining reset-history fields into A34 authority.

## Secure-epoch boundary

No secure-epoch implementation is selected. A future positive input must be
independent of Linux reset history and must attest the exact secure payload's
initialization of its private replay state for the current epoch. Until then,
the production A34 owner remains CLOSED even when the copied ram-console
snapshot is valid.
