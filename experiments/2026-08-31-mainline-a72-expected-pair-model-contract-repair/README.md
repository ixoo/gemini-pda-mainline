# Experiment: repair the A72 expected-pair model contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-expected-pair-model-contract-repair` |
| Status | `definition in progress; no build or device action` |
| Subsystem | generic arm64 late-CPU expected-pair completeness |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Will comparing the immutable pair's MIDR model bits with the production
`expected_target_midr[]` model fields allow exact r0p1 evidence to complete
effect planning while preserving the later exact r0p1 target-register check?

## Selected evidence

Exact stage-ledger candidate `b78ac044...` reached serviceable mainline with
CPU0--7 online, CPU8--9 offline, verified runtime identity, and zero actions.
The profile ledger returned `-EAGAIN` at `expected-pair`; the generic planner
returned the same value at `derive`. The immutable pair contains exact r0p1
MIDR `0x410fd081`, while the two production target expectation fields contain
revision-neutral Cortex-A72 model base `0x410fd080`.

See the parent
[runtime result](../2026-08-31-mainline-a72-effect-plan-stage-ledger/results/runtime-attempt-1-expected-pair-rejection-20260831.txt).

## Safety assessment

The selected change is one pure generic predicate. It adds no CPU request,
CPU9 route, CPU_OFF route, retry, power operation, hardware access, storage
access, retained-RAM access, reboot path, or device action. The exact expected
pair remains unchanged, and the late-target validator continues comparing its
exact MIDR directly with the captured CPU register.

## Procedure

1. Generate and replay canonical patch `0462` on exact post-`0461` Buildbox
   source.
2. Prove exact A72 r0p1 and another A72 revision match the A72 model field,
   while an A53 value and a revision-bearing target field are rejected.
3. Prove the exact late-target MIDR comparison and every action-call inventory
   remain byte-for-byte unchanged.
4. Add the patch to the canonical series and audit every manifest profile.
5. Build focused and production profiles on Buildbox and run the existing
   no-network 51-test suite.
6. Construct and independently validate one exact production candidate.
7. Deploy only to live-resolved inactive `boot2`, verify full readback, and
   shut down.
8. On one fresh boot, require both effect planners to complete and READY to be
   exact before issuing CPU8 once.

CPU9 remains vetoed until CPU8 is reproducibly online.
