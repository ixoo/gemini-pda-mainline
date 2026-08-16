# Experiment: arm64 entry four-stage retained ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-arm64-entry-ledger` |
| Status | implementation and offline validation passed; Buildbox package pending |
| Subsystem | arm64 primary entry, MMU transition, setup_arch, pstore/ramoops |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline pre-setup_arch localization |

## Question or hypothesis

Does the exact current mainline artifact reach arm64 `primary_entry`, complete
MMU-off CPU setup, enable the MMU, or complete the reserved-memory scan before
its automatic return to known-good Gemian?

Four independent retained records distinguish those boundaries without normal
ramoops registration. This is an entry-localization experiment, not a DA921x,
regulator, CPU-admission, or hardware-support experiment.

## Provenance and environment

- Kernel: pinned Linux 7.1.3 from `kernel/manifest.json`.
- Parent profile: `da921x-resource-only-provider-modules-control`.
- Experiment profile: `da921x-modules-arm64-entry-ledger`.
- Patch: canonical `0281-arm64-add-Gemini-entry-stage-ledger.patch` after the
  exact canonical series through 0280.
- Design authority: the completed
  [entry-ledger safety audit](../2026-08-16-mainline-arm64-entry-ledger-audit/README.md).
- Build backend: explicit Buildbox only; native VM builds remain prohibited.
- Boot path: retained LK Android-v0 container on inactive logical `boot2`.
- Recovery path: ordinary known-good Gemian and changed-cycle pstore/raw-zone
  capture.
- Exact build, package, container, partition, and boot identities are pending.

## Safety assessment

The exact authorized write boundary is token `GAEL-20260816-A`, four existing
4 KiB dmesg zones at `[0x444bb000,0x444bf000)`, and at most one short record per
slot. The first two checkpoints execute without calls, stack access, literal
pools, or writes outside that range. They accept only EL1/EL2 after directly
proving SCTLR translation and data-cache bits clear; require four exact `DBGC`
headers; preserve `x0`--`x8`, `x16`--`x30`, and `sp`; and use aligned 32-bit or
narrower accesses. Later stages map only the four-zone range and accept every
earlier slot only when empty or byte-exact. The final stage also requires the
exact Gemini flat DT, ramoops address/size, `no-map`, and memblock reservation.

Every stage writes data before start and size, issues full-system ordering,
then reads back the signature, lengths, and complete record. No stage retries,
repairs, clears, or overwrites. The runtime patch performs no storage,
filesystem, firmware, I2C, regulator, clock, CPU admission, timer, watchdog,
reset, reboot, or power operation. CPU8 and CPU9 stay closed.

The guarded installer may write only live-GPT-resolved inactive `boot2`, records
but does not newly back up its predecessor, requires full-partition readback,
and shuts Gemian down after success. The project-wide device backup captured at
project start remains the recovery source. Stop on any source, config, package,
record, header, partition, power, or readback mismatch. Visual screen state is
not attributable evidence.

The owner explicitly authorized this exact implementation, Buildbox build, and
one boot2 attempt on 2026-08-16 and granted standing authorization for future
diagnostics within the same documented fail-closed retained-RAM policy. See
`results/owner-authorization-20260816.txt` and `docs/SAFETY.md`.

## Associated code

- `scripts/validate.py`: exact patch/profile/assembly/C safety validator.
- `scripts/test-validate.py`: unsafe mutation rejection suite.
- `results/offline-implementation-validation-20260816.txt`: patch application,
  compiler-smoke, oracle, manifest, mutation, and checkpatch evidence.
- The audit's `scripts/record-layout.py` freezes the exact bytes and assembly
  words; its classifier and fixtures own returned-Gemian interpretation.
- Candidate construction, independent validation, guarded installation, and
  exact invocations will be recorded after the validated Buildbox package
  exists.

## Procedure

1. Validate patch application, profile isolation, exact hooks, MMU/cache and
   register gates, record bytes, independent-stage rules, normal-ramoops bypass,
   and prohibited-effect absence.
2. Run manifest invariants, Python/shell checks, strict patch review, and the
   focused mutation suite.
3. Commit and push the exact clean input, build only with explicit Buildbox,
   and fetch only its validated package.
4. Independently validate package provenance, resolved configuration, Image,
   DTB, symbols, and exact source-to-record identity. Construct and validate one
   Android-v0 candidate with the unchanged working initramfs/LK contract.
5. Freeze the exact candidate hypothesis and decision map. Re-read the four
   live headers immediately before deployment and require the expected state.
6. Pre-arm changed-cycle recovery. Install only to live-GPT-resolved inactive
   `boot2`, require full readback, and shut the device down.
7. Select boot2 once. After return to Gemian, immediately recover pstore and the
   bounded four-zone read, classify every independent stage, and stop the exact
   artifact.

Exactly one physical boot selection is authorized. The same candidate must not
be repeated unless repeatability itself is separately justified by new
decision-changing evidence.

## Observations

Canonical patch 0281 applies to the exact managed source through patch 0280.
The exact MMU-off `head.S` and later-stage C translation units compile without
diagnostics under the Buildbox cross-toolchain. The implementation validator
matches both assembly records byte-for-byte with the frozen generator, confirms
the exact hooks and refusal rules, and rejects all 16 unsafe mutations. All 79
manifest profiles preserve the canonical-series invariant.

Strict checkpatch has zero checks. Its five warnings are the expected
experiment-only new-file/MAINTAINERS question and four intentionally split
exact record strings. Its sole error is the deliberately absent sign-off on a
synthetic, non-certifying, explicitly non-submission patch. No full kernel
build, package, candidate, partition write, shutdown, or boot has occurred yet.

## Analysis

The previous C-only checkpoint could not distinguish absence of Image entry
from refusal before its post-memblock write. The new independent post-MMU stage
can prove Image entry even if either physical writer refuses. Conversely, an
exact slot 171 or 172 record directly establishes progress inside the arm64
MMU-off primary path. Empty earlier slots are therefore not treated as a
chronology gap when a valid later record exists.

## Conclusion

Runtime result pending. A compile or validated candidate will not establish
Image entry or hardware support.

## Follow-up

Complete the single Buildbox-to-boot2 attempt and let its highest valid
independent stage choose the next observation boundary. The ordered project
path remains in [`docs/ROADMAP.md`](../../docs/ROADMAP.md).
