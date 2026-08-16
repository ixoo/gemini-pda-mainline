# Arm64 entry-ledger design contract

## Objective

Produce durable, cross-version evidence at four exact primary-CPU boundaries
without depending on ordinary ramoops registration or late serviceability.
This contract governs a possible future implementation; it is not itself an
authorization or patch.

## Fixed identity

- token: `GAEL-20260816-A`
- reservation: `[0x44410000,0x444f0000)`
- zones: slots 171--174, each 4 KiB, at
  `[0x444bb000,0x444bf000)`
- persistent header: little-endian `DBGC` (`0x43474244`), 32-bit start, 32-bit
  size
- record framing: `====0.000000-D\n`, followed by the exact line
  `GAEL-20260816-A E#\n`; the fixed stage-to-zone mapping supplies the slot
  identity and the complete payload is 34 bytes
- records:
  - slot 171: `E0`, stage `primary-entry`
  - slot 172: `E1`, stage `pre-primary-switch`
  - slot 173: `E2`, stage `post-mmu`
  - slot 174: `E3`, stage `post-reserved-scan`

The design oracle retains its derived stage CRCs as an offline mutation guard;
they are not duplicated in the wire record. Runtime integrity is byte-exact
matching of the frozen payload in its stage-owned zone, bounded by the exact
candidate/container/deployment checksum chain.

## Stage contract

### E0: primary entry

- Hook immediately after `record_mmu_state` returns and before
  `preserve_boot_args`.
- Inline assembly only; no call, stack, literal-pool, allocator, DT, or normal
  virtual-address dependency.
- Use aligned 32-bit or narrower loads/stores only; payload offset 12 is
  32-bit-aligned and no unaligned 64-bit access is permitted.
- Accept only CurrentEL EL1 or EL2.
- Read the corresponding SCTLR and require both `SCTLR_ELx_M == 0` and
  `SCTLR_ELx_C == 0`.
- Clobber only `x9`--`x15`; preserve boot arguments `x0`--`x3`, Linux's
  documented primary-path `x19`--`x21`, link register `x30`, and `sp`.
- Before any write, require all four headers exact and empty.
- Write only slot 171.

### E1: pre-primary-switch

- Hook after `__cpu_setup` returns and before the branch to
  `__primary_switch`.
- Preserve `x0`, which contains the prepared SCTLR value passed to
  `__enable_mmu`, as well as the E0 preserved set.
- Re-read CurrentEL/SCTLR and require MMU and data cache still off.
- Accept slot 171 only when empty or byte-exact E0; require slots 172--174
  empty before any write.
- Write only slot 172.

### E2: post-MMU

- Hook in `setup_arch` after `early_fixmap_init()` and
  `early_ioremap_init()`, before `setup_machine_fdt()`.
- Map only the four-zone range with early ioremap.
- Accept slots 171--172 only when empty or their byte-exact record; require
  slots 173--174 empty before writing.
- Write only slot 173, read it back, and unmap.

### E3: post-reserved scan

- Hook immediately after `arm64_memblock_init()` and before `paging_init()`.
- Require exact root compatible `planet,gemini-pda`, exact flat-DT
  `ramoops@44410000`, compatible `ramoops`, exact address and size, `no-map`,
  and memblock reservation.
- Accept slots 171--173 only when empty or byte-exact; require slot 174 empty.
- Write only slot 174, read it back, and unmap.

## Common write protocol

1. Validate every required header and prior record before the first write.
2. Copy the complete record bytes to payload offset 12.
   Assembly stages use aligned 32-bit or narrower stores.
3. Issue the stage-appropriate full-system ordering barrier.
4. Commit start equal to record length.
5. Order again, then commit size equal to record length.
6. Order and read back signature, start, size, and every record byte.
7. On any mismatch, write nothing further from that stage.

No stage retries, overwrites, clears, or repairs a slot. Later stages may
accept an earlier empty slot, but never a malformed or foreign nonempty slot.

## Configuration and recovery

- One default-off option and one isolated profile extending the exact
  module-policy/provider-only parent.
- The option must be built-in and may bypass normal ramoops registration only
  on `planet,gemini-pda`.
- Returned known-good Gemian performs changed-cycle pstore capture followed by
  a bounded raw-zone marker check.
- The exact candidate is attempted once and then stopped.

## Prohibited effects

- partition, block, filesystem, or firmware writes at runtime;
- I2C, regulator, clock, SPM, PSCI, CPU_ON/OFF, or Linux CPU admission;
- interrupt, timer, watchdog, delay, reset, restart, or poweroff action;
- writes outside `[0x444bb000,0x444bf000)`;
- primary `boot`, `boot3`, preloader, GPT, NVRAM, or whole-device deployment.

## Authorization boundary

The exceptional act is a maximum of four short retained-RAM record writes,
including up to two before DT validation. Physical fingerprint, incoming
MMU/cache refusal, exact candidate identity, guarded `boot2` deployment, full
readback, and clean shutdown are mandatory. The owner supplied explicit
authorization on 2026-08-16 and made equivalent future fail-closed retained-RAM
diagnostics standing authorization. The successor experiment records the exact
statement and remains subject to every gate in this contract.
