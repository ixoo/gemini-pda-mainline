# Experiment: arm64 entry-ledger safety audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-arm64-entry-ledger-audit` |
| Status | read-only design audit complete; owner authorization pending |
| Subsystem | arm64 primary entry, MMU transition, setup_arch, pstore/ramoops |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline pre-setup_arch localization |

## Question or hypothesis

Can one isolated four-stage retained ledger safely distinguish failure before
arm64 Image entry, during MMU-off primary setup, during the MMU transition, or
before the reserved-memory scan, after the prior C-only ledger retained no
stage?

This audit evaluates the observation mechanism. It does not claim that LK
entered the Image and it does not test DA921x, CPU admission, or hardware
support.

## Provenance and environment

- Kernel: pinned Linux 7.1.3 plus the canonical series through patch 0280.
- Authoritative built source state: exact Buildbox checkout for repository
  commit `ca56f0161f6d67900d0fc58719e9190e7d1bb4a3` and profile
  `da921x-modules-pre-ramoops-ledger`.
- LK source: public Planet Android 8 LK commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`; the exact handoff calls
  `lk_jump64(entry, tags, 0, KERNEL_64BITS)`.
- Relevant prior candidate contract: Image range
  `[0x40200000,0x40df0000)`, ramdisk range
  `[0x45000000,0x451fa361)`, and retained reservation
  `[0x44410000,0x444f0000)` do not overlap.
- This audit performs no kernel build. Native VM kernel builds remain
  prohibited unless explicitly requested by the owner.

Exact source hashes and insertion-point observations are recorded in
`results/source-and-safety-audit-20260816.txt`.

## Safety assessment

The design is not yet authorized for implementation, build, or device use.
Its exceptional boundary is explicit: the first two stages would write
physical retained RAM before ordinary DT parsing. They may do so only when an
isolated default-off configuration is selected and all of these gates pass:

- execution is at EL1 or EL2 after `record_mmu_state`;
- direct reads prove both the MMU bit and data-cache bit are zero;
- all four exact 4 KiB zone headers form the expected physical fingerprint;
- every prior slot is either empty or contains the exact candidate record;
- the target slot is empty and has the exact `DBGC` signature;
- only caller-clobbered registers `x9`--`x15` are changed; `x0`--`x3`,
  `x19`--`x21`, `x30`, and `sp` remain untouched;
- record data is committed before start and size, followed by `dsb sy` and
  complete readback; assembly uses aligned 32-bit or narrower accesses only.

The later two stages use `early_ioremap`; the final stage also requires the
exact Gemini flat DT, exact ramoops address/size and `no-map`, and memblock
reservation. Each stage owns only one zone:

| Stage | Slot | Hook | Access mode |
| --- | ---: | --- | --- |
| `primary-entry` | 171 | after `record_mmu_state`, before `preserve_boot_args` | MMU-off physical |
| `pre-primary-switch` | 172 | after `__cpu_setup`, before `__primary_switch` | MMU-off physical |
| `post-mmu` | 173 | after `early_ioremap_init`, before `setup_machine_fdt` | early fixmap |
| `post-reserved-scan` | 174 | after `arm64_memblock_init`, before `paging_init` | early fixmap plus exact DT/reservation |

No stage may access storage, partitions, I2C, regulators, CPU admission,
timers, watchdog controls, or restart controls. CPU8 and CPU9 remain closed.
Normal ramoops registration must be bypassed only for the isolated profile so
returned Gemian can recover the records. A guarded deployment would retain the
existing live-GPT `boot2` checks, no-fresh-backup policy, full readback, and
clean shutdown.

The key remaining risk is that the first two stages intentionally cannot parse
the DT. Their replacement runtime identity is the exact four-header physical
fingerprint plus the exact candidate/container/deployment chain. That is a
materially earlier and more privileged write boundary than the prior ledger,
so it requires a new explicit owner authorization after review.

## Associated code

- `DESIGN.md`: exact stage, register, memory, record, and decision contract.
- `scripts/oracle.py`: independent structural and outcome oracle.
- `scripts/test-oracle.py`: unsafe-design negative mutations.
- `results/source-and-safety-audit-20260816.txt`: pinned source and placement
  audit.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-08-16-mainline-arm64-entry-ledger-audit/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-08-16-mainline-arm64-entry-ledger-audit/scripts/test-oracle.py
```

Both commands are offline and perform no build or device access.

## Procedure

1. Pin and hash the exact arm64 entry, MMU, setup, pstore, and LK handoff
   sources.
2. Prove the candidate Image, ramdisk, tags/FDT, and retained ledger ranges do
   not overlap.
3. Select only insertion points whose ordering is explicit in the pinned
   source.
4. Define register clobbers, MMU/cache refusal, physical fingerprint, stage
   independence, write order, readback, and returned-Gemian recovery.
5. Enumerate all monotonic reach states and independent stage refusals; require
   the highest valid marker never to overstate execution progress.
6. Reject unsafe mutations before proposing a patch or build.
7. Present the exact privileged write boundary for owner authorization.

## Observations

Pinned Linux source places `record_mmu_state` before `preserve_boot_args`,
calls `__cpu_setup` while the MMU remains off, and enables/maps/relocates the
kernel inside `__primary_switch` before branching to `__primary_switched` and
`start_kernel`. `start_kernel` calls `setup_arch`; arm64 then initializes the
fixmap and early ioremap before FDT setup, and calls `arm64_memblock_init`
before `paging_init`.

The prior exact container's Image, ramdisk, tags/FDT, and retained reservation
are disjoint. Its four live headers were exact `DBGC`, start zero, size zero
before deployment and again after the no-stage cycle. The public LK handoff
confirms the entry and FDT arguments but does not by itself close the incoming
MMU/cache state; the proposed entry code therefore reads and gates that state
rather than assuming it.

The oracle accepts the exact four-stage contract, enumerates every monotonic
reach/refusal combination, and rejects the unsafe mutations recorded by its
test suite.

## Analysis

Stage independence is essential. A later checkpoint may write when an earlier
one safely refused, provided every earlier slot is still empty or exact; this
prevents an entry-state refusal from hiding proof that the kernel reached
post-MMU C code. A malformed or foreign earlier slot disarms later writes and
rejects attribution.

The highest valid stage has this meaning:

- none: Image entry remains unestablished, or the entry writer refused and
  execution stopped before `post-mmu`;
- 171: `primary_entry` ran with MMU/cache off, but the pre-switch hook was not
  completed;
- 172: primary CPU setup completed while still MMU/cache off, but the
  post-MMU hook was not completed;
- 173: `start_kernel` reached early `setup_arch`, but the reserved-scan hook
  was not completed or refused its exact DT/reservation gate;
- 174: the same post-`arm64_memblock_init` boundary as the prior ledger was
  reached, proving that the earlier no-stage result was an instrumentation
  refusal or artifact-specific difference rather than that boundary itself.

If slot 173 or 174 exists without an earlier marker, Image entry is still
proved by the later stage; the missing earlier record is classified as a safe
writer refusal rather than a chronological gap. Any bad identity, CRC,
header, duplicate, or unknown record rejects attribution.

## Conclusion

The lower observation boundary is feasible as an isolated, fail-closed design.
The audit closes source placement, range non-overlap, register preservation,
MMU/cache gating, per-slot ownership, stage independence, write ordering,
readback, and decision semantics. It does not authorize or provide a kernel
patch, Buildbox package, boot candidate, device write, or boot.

## Follow-up

Obtain explicit owner authorization for the pre-DT physical-write boundary.
Only then add one default-off patch/profile, validate it and its negative
mutations, commit and push the exact input, build on Buildbox, construct one
candidate, restate the hypothesis and decision map, deploy only to `boot2`,
shut down, and spend one physical selection. The ordered project path remains
in [`docs/ROADMAP.md`](../../docs/ROADMAP.md).
