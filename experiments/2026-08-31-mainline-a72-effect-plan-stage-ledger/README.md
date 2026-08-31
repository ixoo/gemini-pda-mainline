# Experiment: localize the A72 effect-plan rejection

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-effect-plan-stage-ledger` |
| Status | `complete; exact expected-pair rejection localized with zero CPU requests` |
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

The guarded installer resolved inactive `boot2` as `/dev/mmcblk0p30`, matched
the exact model-guard predecessor, wrote the stage-ledger candidate, and
verified its full-partition readback. The device was then shut down and
confirmed unreachable. See the
[deployment evidence](results/deployment-boot2-20260831.txt).

Two bounded observer windows after deployment saw no exact USB interface and
therefore captured no boot. They are absence-of-selection observations, not
candidate or CPU8 results. During that wait, a read-only audit of the exact
prepared source established that `local_caps_planned=1` implies the capability
planner returned success and the effect planner was called. Evaluating the
clean captured evidence and immutable r0p1 expectation against every current
effect predicate predicts completion, which makes the runtime stage ledger the
required discriminator before any repair. See the
[observer-window evidence](results/observer-windows-20260831.txt) and
[offline predicate audit](results/offline-effect-plan-predicate-audit-20260831.txt).

The fresh diagnostic boot resolved the contradiction without issuing a CPU
request. Exact stage `expected-pair` returned `-EAGAIN`, and the generic
planner reported the same return at `derive`; validation and completion were
not reached. The immutable pair carries the independently observed r0p1 MIDR
`0x410fd081`, while both production `expected_target_midr[]` entries still
carry revision-zero model base `0x410fd080`. The generic completeness helper
requires those representations to be exactly equal, so it rejected the draft
before effect planning. CPU0--7 remained online, CPU8--9 remained offline,
and CPU8, CPU9, CPU_OFF, retry, and storage-write counts were all zero.

The collector initially searched the diagnostic target field as logical CPUs
8 and 9, although the ledger defines it as profile indices 0 and 1. A bounded
same-boot read-only query recovered the exact `target=-1` rejection, and the
collector is corrected for future target-local exits. The identity-gated USB
recovery returned the device to changed-ID Gemian. See the
[runtime result](results/runtime-attempt-1-expected-pair-rejection-20260831.txt).

The selected successor must align the production expected-target MIDR
representation with the exact r0p1 pair while keeping model-only capability
classification revision-neutral and later target-register validation exact.
It must pass Buildbox and offline gates before one new CPU8-only attempt.
CPU9 remains vetoed until CPU8 is reproducibly online.
