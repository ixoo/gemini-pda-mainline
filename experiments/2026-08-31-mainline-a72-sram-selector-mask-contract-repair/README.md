# Experiment: repair the CPU8 SRAM selector-mask contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-sram-selector-mask-contract-repair` |
| Status | `exact repair tooling prepared; Buildbox generation pending` |
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

## Analysis

The physical owner and binder currently apply different result contracts to
the same selector. The owner accepts `(selector & GENMASK(11, 0)) == 0x8fb`
and separately requires the full reads to be identical. The binder compares
each full value directly to `0x8fb`, rejecting valid upper status bits after
the owner has already verified and sealed the result. The proposed change
makes the consumer use the producer's existing contract without changing the
hardware transaction.

## Conclusion

Pending Buildbox generation, KUnit, and device evidence.

## Follow-up

If the repair passes offline gates, build and validate one exact boot2
candidate. Its unique runtime evidence is whether the SRAM match becomes
`0xfff`, P28 completion is attempted, and the transition advances beyond stage
5. Retain the CPU9 veto.
