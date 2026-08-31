# Experiment: repair the CPU8 SRAM selector-mask contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-sram-selector-mask-contract-repair` |
| Status | `exact boot2 candidate passes all offline gates; deployment pending` |
| Subsystem | MT6797 CPU8 binder and BigiDVFS SRAM result contract |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Will applying the SRAM owner's existing 12-bit selector mask in the CPU8
binder accept the production value `0x4008fb` while continuing to reject a
selector whose low 12 bits differ from `0x8fb`?

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0452`.
- Parent source state:
  `ebedf76c35a7deab5711162ccc2799ed22bf576bd88974c3de926772bc33f6bf`.
- Parent integrity:
  `fb43852cd2024ccbf8101a61699104beeee321fff21787dccb07adc5ee79dd6b`.
- Build and patch generation backend: Buildbox only.
- Runtime source: the one-shot result in the preceding
  [SRAM terminal diagnostic](../2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/README.md).

## Safety assessment

The change masks two already-read selector values before comparing them to the
same expected low-12-bit value. It does not add, remove, or reorder an SRAM
owner call, P28 transition, MMIO access, secure call, CPU request, CPU9 path,
CPU_OFF path, retry, retained-RAM write, storage access, delay, watchdog
operation, or reboot. The existing owner already requires the complete first
and second reads to be equal, so accepting upper status bits does not weaken
the stable-read requirement.

No device image may be prepared until deterministic patch replay, strict
review, focused KUnit, and the exact production profile pass on Buildbox. CPU9
remains vetoed until CPU8 is reproducibly online.

## Associated code

- `scripts/source_edits.py` applies the exact two-file repair to checksum-pinned
  post-`0452` sources.
- `scripts/generate_patch.py` creates and replays canonical patch `0453`,
  proves physical/request call counts unchanged, and rejects new write paths.
- `scripts/generate-on-buildbox` pins the managed source and clean project
  commit and produces a checksum-covered patch review package.
- `scripts/run-kunit-qemu` and `scripts/classify-kunit.py` accept only the
  exact fetched Buildbox package and the 30/12/8 focused suite inventory.

The generator writes only a temporary Git tree and a review package on
Buildbox. It performs no device access.

## Procedure

1. Generate one normal format-patch from the exact post-`0452` source.
2. Mask both binder selector comparisons with the existing SRAM-owner selector
   mask; do not change any other production predicate.
3. Add one KUnit case that accepts the observed upper status bit and rejects a
   low-bit mutation.
4. Replay the patch and prove all physical and request call counts unchanged.
5. Admit it canonically only after source, style, and manifest invariant gates.
6. Run focused binder KUnit and the exact live-trigger production build on
   Buildbox before preparing at most one boot2 candidate.

## Observations

- Candidate `7cddf030...` issued one CPU8 request and reached SRAM.
- The SRAM owner returned success, all steps complete, stable identical reads,
  valid calibration, the correct transaction identity, and a sealed result.
- Both reads were `0x4008fb`; their low 12 bits are the expected `0x8fb`.
- The binder match mask was `0xfcf` of required `0xfff`; only the two unmasked
  selector comparison bits were absent. P28 completion was not attempted.
- CPUs 0-7 remained online and CPUs 8-9 remained offline. There were zero
  CPU9, CPU_OFF, retry, or reboot requests.
- Buildbox generated and deterministically replayed exactly one patch from the
  checksum-pinned post-`0452` source. Its SHA-256 is `fe404106...`.
- The source audit proves two masked predicates, positive upper-status-bit
  coverage, low-bit rejection coverage, and unchanged hardware/request call
  counts.
- Strict Checkpatch reports zero warnings and zero checks. Its sole error is
  the deliberately absent DCO sign-off for the synthetic experiment author;
  this internal archive is not submission-ready.
- All 158 manifest profiles remain canonical-order subsequences, and eight
  invariant mutations are rejected.
- Buildbox built the exact `a72-default-off-binder-kunit` profile from patch
  commit `3bf4cc6e...`; the fetched package passed all checksum and provenance
  gates.
- The isolated no-network QEMU run passed all 50 expected tests: 30 P24 owner,
  12 transition executor, and 8 binder cases. The new case accepts the observed
  upper selector status bit and rejects a low selector-bit mutation. It issued
  zero physical CPU, CPU_OFF, or retry requests. See the
  [KUnit result](results/kunit-qemu-3bf4cc6e-20260831.txt).
- Buildbox built the exact production profile from clean pushed commit
  `2d682d8a...`. The fetched package is checksum-valid, identifies patchset
  `2942ab05...`, and contains no KUnit configuration.
- Two independent package-exact provenance compositions produced the same DT,
  and two independent Android-v0 assemblies and padding methods produced raw
  candidate `add111ac...` and full-partition image `cd36efdf...` byte for byte.
- Two independent validations passed all 32 LK gates and rejected all six
  container mutations. The image retains one CPU8 request route and no CPU9,
  CPU_OFF, or retry route. The boot-bound runtime contract passes three result
  branches and rejects ten unsafe status mutations. See the
  [offline candidate result](results/offline-candidate-20260831.txt).

## Analysis

The physical owner and binder currently apply different result contracts to
the same selector. The owner accepts `(selector & GENMASK(11, 0)) == 0x8fb`
and separately requires the full reads to be identical. The binder compares
each full value directly to `0x8fb`, rejecting valid upper status bits after
the owner has already verified and sealed the result. The proposed change
makes the consumer use the producer's existing contract without changing the
hardware transaction.

## Conclusion

The exact source repair, production package, deterministic candidate, and
hardware-free proofs pass. The repair has not yet run on the device.

## Follow-up

Install exact padded candidate `cd36efdf...` to live-GPT-resolved inactive
`boot2`, require matching full-partition readback, and shut down. On its one
accepted boot, require a pristine ABI-2 armed frame and issue one boot-bound
CPU8 trigger. Its unique evidence is whether the SRAM match becomes `0xfff`,
P28 completion is attempted, and the transition advances beyond stage 5.
Retain the CPU9 veto.
