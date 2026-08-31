# Experiment: localize the A72 effect-plan rejection

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-effect-plan-stage-ledger` |
| Status | `validated diagnostic candidate; boot2 deployment pending` |
| Subsystem | arm64 late-CPU effect planning |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question

Which exact production effect-derivation branch or generic effect-plan
validation stage prevents the otherwise exact Cortex-A72 plan from reaching
READY?

## Selected evidence

The parent candidate restored all three expected mitigation capabilities and
produced exact aggregate and per-target capability vectors. Its read-only
pretrigger frame nevertheless reported plan mask `0x36000`: local capability
planning completed, while effects and dependent HWCAP planning remained
empty. The final profile validator returned `-EINVAL`, but the earlier effect
planner's return and substage were not emitted. CPU8 and CPU9 were untouched.

See the parent
[runtime result](../2026-08-31-mainline-a72-expected-midr-model-guard-repair/results/runtime-attempt-1-local-caps-restored-20260831.txt).

## Diagnostic boundary

Add one source-local, boot-time ledger line to every return from the MT6797
A72 effect derivation and one generic line distinguishing derivation from
validation. Every return value and control-flow edge is preserved. The patch
adds no CPU request, CPU9 path, CPU_OFF path, retry, hardware access, storage
access, retained-RAM access, power operation, or reboot path.

## Procedure

1. Generate one normal format-patch from the exact canonical source through
   patch `0460` on Buildbox.
2. Validate every stage label, preserved return value, unchanged action-call
   inventory, strict style, and deterministic replay.
3. Add the patch to the canonical series and audit all manifest profiles.
4. Build focused and production profiles on Buildbox and run the existing
   no-network KUnit suite.
5. Assemble and validate one serviceable diagnostic candidate.
6. Deploy only to live-resolved inactive `boot2`, verify full readback, and
   shut down.
7. On one fresh boot, collect the read-only stage ledger and do not trigger
   CPU8, even if READY unexpectedly appears.

CPU9 remains vetoed until CPU8 is reproducibly online.

Buildbox generated and replayed canonical patch `0461` from the exact
post-`0460` prepared source. The patch preserves every return edge and action
inventory while adding 14 MT6797 derivation stages and four generic planner
stages. Strict style completed with zero errors, warnings, or checks. See the
[generation evidence](results/patch-generation-20260831.txt).

Both focused profiles and the production profile compiled and packaged on
Buildbox from published commit `6382feb5`. The no-network four-vCPU suite
passed all 51 tests with no physical CPU operation. See the
[build evidence](results/buildbox-builds-20260831.txt) and
[KUnit evidence](results/focused-kunit-qemu-20260831.txt).

The production Image was combined with the unchanged serviceability DT and
its exact package-owned A41 provenance leaf. Two raw assemblies and two
padding constructions were byte-identical; all 32 LK gates and six negative
container mutations passed. The diagnostic candidate is exact full-partition
SHA-256 `b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1`.
See the [candidate evidence](results/production-candidate-20260831.txt) and
[predeployment hypothesis](results/predeployment-hypothesis-20260831.txt).
