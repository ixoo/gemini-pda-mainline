# Experiment: repair READY plan expectations

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-plan-expectation-repair` |
| Status | `running` |
| Subsystem | arm64 late-CPU plan validation |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact post-`0439` runtime value frame localized the READY-plan rejection to
three stale profile expectations. Does repairing only those expectations allow
the otherwise identical production plan to validate without changing its
producers, expected-effects model, or any CPU action?

The hypothesis is falsifiable: an exact live candidate must produce no
`A72_READY_PLAN_DIAG_V1` or `A72_READY_PLAN_VALUES_V1` failure line, no profile
blocker, and no CPU request. Any remaining validator failure selects another
read-only diagnostic; a clean READY result selects one later CPU8-only trigger
candidate. CPU9 remains vetoed.

## Provenance and environment

- Parent repository commit: `e0078b04...`.
- Parent kernel series: canonical Linux 7.1.3 through patch `0439`.
- Parent prepared source state: `404d5b64...`.
- Parent prepared source integrity: `1f8f978d...`.
- Parent `mt6797_psci.c` SHA-256: `08f3be5c...`.
- Runtime evidence: exact boot ID `ec5f3d02...`, kernel
  `7.1.3-gemini-a72-admission-live`, and boot2 SHA-256 `1c08f1fc...`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The patch changes only hard-coded validator expectations. It adds the observed
early `ARM64_WORKAROUND_845719`, removes the unobserved target and required
`ARM64_MISMATCHED_CACHE_TYPE`, and changes the production policy expectation
and its diagnostic from SMC to the observed NONE conduit. Fixture evidence
remains SMC. The patch adds no CPU operation, hardware access, firmware call,
power or storage operation, retained-RAM write, retry, CPU_OFF, or reboot.
CPU8 and CPU9 remain offline and unrequested throughout this experiment.

## Associated code

- `scripts/source_edits.py`: exact post-`0439` edits.
- `scripts/validate_source.py`: source-contract and safety validation.
- `scripts/test_mutations.py`: decision-changing mutation rejection.
- `scripts/generate_patch.py`: deterministic format-patch generation/replay.
- `scripts/generate-on-buildbox`: pinned Buildbox entry point.
- `scripts/build-composed-dtb.py` and `scripts/validate-composed-dtb.py`:
  reproduce and independently validate the exact provenance-only DT delta.
- `scripts/build-candidate.sh` and `scripts/validate-candidate.py`: reproduce
  and independently validate the Android-v0/LK boot container.
- `scripts/install-boot2.sh`: guarded inactive-`boot2` installation, full
  readback, and mandatory clean shutdown without a fresh partition backup.
- `scripts/remote-ready.sh`, `scripts/collect-ready.sh`, and
  `scripts/validate-ready.py`: one read-only, no-trigger READY capture.

## Procedure

1. Generate and replay one format-patch from the exact post-`0439` Buildbox
   source.
2. Reject mutations that restore any stale expectation, alter the fixture
   conduit, bypass the validator wrapper, or add a CPU action.
3. Admit the patch canonically and build the default and exact live profiles
   on Buildbox.
4. Recompose and independently validate an otherwise unchanged serviceability
   candidate.
5. Install exact inactive logical `boot2`, verify its full readback, and shut
   down the device.
6. Capture one read-only boot and require a silent diagnostic, zero blockers,
   and zero CPU requests. Do not send a trigger.

## Observations

Buildbox generated exactly one format-patch from prepared source state
`404d5b64...` and integrity `1f8f978d...`. The parent and final
`mt6797_psci.c` hashes are `08f3be5c...` and `3179b9f3...`; patch `0440` is
`b629ff95...`. Strict checkpatch, deterministic replay, exact contract checks,
and all eight adverse source mutations pass. The generation changed no profile
fragment, performed no native VM build or device action, and marks its output
`boot_candidate=false`. See
[`results/buildbox-generation-20260830.txt`](results/buildbox-generation-20260830.txt).
The canonical patch is byte-identical to that output; the canonical-order
audit passes all 158 manifest profiles and its self-test rejects eight invalid
series mutations.

Repository commit `a07d9c45...` passed both the default and exact
`a72-admission-live-trigger-candidate` profiles on Buildbox. The exact package
was fetched and recomposed twice with the unchanged serviceability DT and
ramdisk. Both composed DTs and both boot containers are byte-identical.
Independent validation passes all 32 LK gates, rejects ten DT mutations,
six container mutations, and thirteen runtime-frame mutations, and confirms
zero executed CPU requests. The exact padded boot2 candidate is
`9abdd1c6...`. See
[`results/offline-candidate-20260830.txt`](results/offline-candidate-20260830.txt).

The guarded installer then resolved inactive logical `boot2` from the live GPT
as `/dev/mmcblk0p30`, required the exact `1c08f1fc...` predecessor, wrote and
flushed `9abdd1c6...`, obtained the same full-partition readback identity, and
shut the device down. It created no fresh partition backup and did not reboot.
See
[`results/deployment-boot2-9abdd1c6-20260830.txt`](results/deployment-boot2-9abdd1c6-20260830.txt).

## Analysis

The review contains only the three corrections selected by the exact live
value frame. It does not change the production producers or expected-effects
model, and the fixture continues to require and publish SMC. Canonical-series,
compile, DT, container, reproduction, negative-mutation, deployment, and full
readback validation all pass. One silent READY capture remains pending.

## Conclusion

`deployed-runtime-pending`.

## Follow-up

Install exact inactive logical `boot2`, shut down, and collect one attributable
read-only boot. Accept only exact kernel and partition identity, one verified
runtime identity, zero profile blockers, zero diagnostic/value lines, CPUs
0--7 online with 8--9 offline, an armed controller, and zero CPU actions. Only
that clean READY result may select a separate CPU8-only trigger candidate.
CPU9 remains out of scope until CPU8 admission is repeatable.
