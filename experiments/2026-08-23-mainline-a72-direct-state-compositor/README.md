# Experiment: mainline A72 direct-state compositor

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-a72-direct-state-compositor` |
| Status | hardware-free implementation prepared for Buildbox generation |
| Subsystem | MT6797 A72 direct-state composition and hotplug ownership |
| Device variant | Gemini PDA contract; injected KUnit phase |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, direct-state composition |

## Question or hypothesis

Can the existing A72 membership owner expose one default-off physical-state
composition boundary that holds the Linux CPU-hotplug read lock and its own
transition lock, publishes only a complete injected record, and leaves A34,
owner lifecycle, hardware operations, and CPU admission closed?

## Provenance and environment

- Decision authority: the
  [source/lock audit](../2026-08-23-mainline-a72-direct-state-compositor-audit/README.md).
- Repository parent: signed and pushed commit
  `a8734f1d`.
- Canonical kernel parent: patch `0336`.
- Managed prepared source state and exact file identities are pinned in
  [`contract.json`](contract.json).
- Generation and compilation use Buildbox only. No native VM build is
  permitted and no source tree is copied to or from Buildbox.

## Safety assessment

The first phase is hardware-free. It adds no physical reader caller, DT node,
device match, MMIO, SMC, I2C transfer, setter, retry, polling loop, A34 ABI
change, lifecycle publication, CPU veto change, CPU_ON, CPU_OFF, boot image,
device access, or partition write.

The destination is cleared before every lookup. Every source, topology, owner,
or lifecycle failure must leave it all-zero. A successful injected snapshot
must leave the A72 owner byte-identical and still `CLOSED / UNINITIALIZED`.

## Associated code

- [`source/mt6797-a72-direct-state.h`](source/mt6797-a72-direct-state.h) is the
  proposed platform-private hardware-only source record.
- [`source/mt6797_a72_direct_state_test.c`](source/mt6797_a72_direct_state_test.c)
  is the focused injected KUnit suite.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the deterministic
  owner and test changes to the exact managed source.
- [`scripts/validate_source.py`](scripts/validate_source.py) validates the
  edited source semantics.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates two
  normal format patches, replays them, and runs strict checkpatch.

## Procedure

1. Validate the repository-side definition and deterministic source editor.
2. Commit and push a clean exact input.
3. Generate two normal patches on Buildbox from the prepared source through
   canonical patch `0336`.
4. Require exact replay, semantic source validation, strict checkpatch, and a
   checksum-covered review package.
5. Admit the reviewed patches canonically and add an isolated KUnit profile.
6. Build that profile on Buildbox and run the focused suite under no-network
   arm64 QEMU.

## Observations

- Buildbox submission `bf563205` stopped before patch creation because the
  source validator counted older `cpu8_online`/`cpu9_online` fields outside
  the new direct-state ABI. The source editor had completed, but no patch was
  packaged or admitted.
- The validator now scopes that count to the direct-state definition itself.

No generated patch, compile, or KUnit result exists yet. Repository-side
definition validation remains the current phase.

## Analysis

The split keeps the outer ownership proof independent from physical reader
binding. A hardware-free pass will establish only the registry, lock order,
complete-record validation, failure behavior, and closed-owner preservation.
It cannot establish a physical value, firmware call, device support, A34
eligibility, or CPU8/CPU9 admission.

## Conclusion

`inconclusive`: the implementation definition is ready for exact Buildbox
generation, but no generated patch or compiled result is yet admitted.

## Follow-up

The authoritative execution order remains in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment owns
the exact implementation chronology and generated identities.
