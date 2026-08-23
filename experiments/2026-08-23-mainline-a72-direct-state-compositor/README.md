# Experiment: mainline A72 direct-state compositor

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-a72-direct-state-compositor` |
| Status | generated patches admitted; Buildbox compile pending |
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
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) accepts only the exact
  fetched Buildbox package for the current published commit and runs the sole
  focused suite under bounded no-network arm64 QEMU.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires all seven
  named cases, exact KTAP summaries, and the expected post-test rootfs panic.

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
- Buildbox submission `38c17b2a` then completed semantic validation and exact
  replay, but strict checkpatch rejected declarations split immediately after
  `(` and its generic MAINTAINERS warning for new experiment-review files. The
  declarations now use normal kernel continuation style; only the named
  `FILE_PATH_CHANGES` heuristic is ignored during generation.
- Buildbox submission `0ceb6509` stopped before packaging when the semantic
  validator still searched for the declaration's old return-type layout. Its
  production-wrapper anchor now uses the stable function name instead.
- Buildbox submission `bc774b52` passed semantics and replay; strict
  checkpatch found one remaining continuation-column mismatch in the public
  registration prototype. That exact whitespace is corrected.
- Buildbox submission `46a5dac3` proved the core patch strict-clean and found
  only two continuation-column checks in the KUnit patch. Both short calls are
  now kept on one line.
- Buildbox submission `24bc92a7` generated two checksum-covered patches from
  canonical patch `0336`. Semantic validation, exact replay, and strict
  checkpatch all passed. The admitted patch hashes are pinned in
  [`contract.json`](contract.json).

The generated patches and isolated `a72-direct-state-kunit` profile are now
admitted. No compile or KUnit runtime result exists yet.

## Analysis

The split keeps the outer ownership proof independent from physical reader
binding. A hardware-free pass will establish only the registry, lock order,
complete-record validation, failure behavior, and closed-owner preservation.
It cannot establish a physical value, firmware call, device support, A34
eligibility, or CPU8/CPU9 admission.

## Conclusion

`inconclusive`: the exact implementation patches are admitted and source-clean,
but the focused profile has not yet compiled or executed in QEMU.

## Follow-up

The authoritative execution order remains in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment owns
the exact implementation chronology and generated identities.
