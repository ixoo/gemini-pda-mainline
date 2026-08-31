# Experiment: localize CPU8 after capability acceptance

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-post-capabilities-checkpoints` |
| Status | `runtime complete; exact MIDR expected-pair repair selected` |
| Subsystem | arm64 secondary startup and MT6797 P30E wire |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact predecessor proves that CPU8 entered normal virtual C execution and
retained checkpoint 5 after `check_local_cpu_capabilities()` returned. Does it
then complete CPU-operations postboot, CPU-info capture, exact late-target
validation, topology storage, and interrupt/IPI/NUMA setup?

If exact late-target validation rejects CPU8, one boot should also preserve the
complete mismatch bitmap plus the expected and observed values for its first
mismatched field. That makes the result directly repairable rather than merely
moving the boundary to the validator.

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0457`.
- Parent prepared source state:
  `08f72dc179b1dbbf848971fcc112f0ae9a18d22e1544faa7164fc90609f6d271`.
- Parent source integrity:
  `2bd0626daa8966a8e5036dd7238fce90457ff2ebcecfdaf5815cc68aee4ee7c1`.
- Build and patch-generation backend: Buildbox only.
- Runtime predecessor: exact padded candidate `6d0bf75b...`, classified
  [P30E checkpoint 5](../2026-08-31-mainline-a72-secondary-entry-checkpoints/results/runtime-attempt-1-checkpoint-5-20260831.txt).

## Safety assessment

This successor keeps the existing default-off, one-shot CPU8 transaction. It
adds no CPU request, CPU9 route, CPU_OFF route, retry, power step, storage
access, retained-RAM access, or device action. The target writes only its
already-owned P30E slot while it remains ARMED/CLAIMED with sequence zero.

Normal checkpoints require zero detail. The expectation-failure checkpoint
requires a nonzero, known mismatch bitmap and writes detail values before its
reason commit. A full-slot clean and barrier retain the existing readback
contract. Observation failure cannot create a second CPU action. The existing
watchdog remains the recovery owner and CPU9 remains vetoed.

## Associated code

- `DESIGN.md` freezes the extended reason values and mismatch-bit meanings.
- `scripts/source_edits.py` applies checksum-pinned post-`0457` source edits.
- `scripts/generate_patch.py` generates, audits, and replays canonical patch
  `0458`.
- `scripts/generate-on-buildbox` binds generation to the exact pushed project
  commit and managed post-`0457` source.
- `scripts/run-kunit-qemu` boots only the exact default-off binder KUnit
  package without networking.
- `scripts/classify-kunit.py` enforces the expected three-suite, 51-test TAP
  result and emits a durable machine-readable record.
- `scripts/build-composed-dtb.py`, `scripts/build-candidate.sh`, and
  `scripts/validate-candidate.py` compose and independently validate the exact
  production container.
- `scripts/install-boot2.sh` requires the exact checkpoint-5 predecessor,
  resolves `boot2` from the live GPT, verifies a full readback, and shuts down.
- `scripts/collect-pretrigger.sh`, `scripts/validate-pretrigger.py`,
  `scripts/remote-trigger.sh`, `scripts/execute-trigger.sh`, and
  `scripts/classify-attempt.py` enforce the single-boot, single-CPU8 ABI-5
  observation contract.

## Procedure

1. Generate and deterministically replay one normal format-patch on Buildbox.
2. Review the target-owned detail ordering, mismatch inventory, ABI-5
   diagnostic, status fields, and unchanged action-call inventory.
3. Run manifest invariants, strict style checks, and the focused four-CPU
   KUnit/QEMU suite on Buildbox.
4. Build the exact production profile on Buildbox and independently construct
   and validate one successor container.
5. State the exact boot hypothesis and decision map, deploy only to
   live-resolved inactive `boot2`, verify full readback, and shut down.
6. On one serviceable boot, prove pristine zero execution and issue exactly
   one CPU8 trigger. Do not request CPU9, CPU_OFF, retry, or reboot.

## Observations

- The predecessor retained reason `5`, returned `-EIO`, and left CPU8 offline.
- Its request counts were CPU8 `1`, CPU9 `0`, CPU_OFF `0`, retry `0`, and
  reboot `0`.
- The post-`0457` Buildbox parent and all nine intended parent-file checksums
  are pinned in `scripts/source_edits.py`.
- Buildbox generated and deterministically replayed canonical patch `0458`
  from project commit `166ca242a19e...`; strict Checkpatch reported zero
  errors, warnings, or checks. The exact patch SHA-256 is `2a6c72ae0a10...`.
- The patch adds five post-capabilities call sites, preserves 26 architectural
  comparisons plus three structural mismatch bits, and rejects unknown detail
  bits before any P30E slot mutation.
- Both repository series-invariant checks pass: all 158 manifest profiles were
  audited, and the focused self-test rejected all eight mutations. See the
  [patch-generation evidence](results/patch-generation-20260831.txt).
- Both focused Buildbox configurations compile and package from clean project
  commit `0bce8c9a8c8f...`; all package checksums validate. See the
  [Buildbox evidence](results/buildbox-kunit-builds-20260831.txt).
- The exact default-off binder package passed all 51 tests in its no-network,
  four-vCPU QEMU boot, including all nine binder tests. No physical CPU,
  CPU_OFF, retry, network, or device action occurred. See the
  [KUnit/QEMU evidence](results/focused-kunit-qemu-20260831.txt).
- Buildbox produced the clean production package from commit `590dbedc974c...`.
  The package, package-exact provenance/serviceability DT composition, two
  independent raw assemblies, two independent padding constructions, all 32
  LK gates, the independent layout validator, and six negative container
  mutations pass. The exact padded `boot2` identity is `9f7ff84912ff...`.
  See the [production-candidate evidence](results/production-candidate-20260831.txt).
- The predeployment hypothesis and decision map are frozen before the write;
  each retained reason from 5 through 11 selects a distinct next code interval,
  while reason 8 also preserves the exact mismatch bitmap and first
  expected/observed pair. See the
  [predeployment record](results/predeployment-hypothesis-20260831.txt).
- The live GPT resolved inactive, unmounted `boot2` as `/dev/mmcblk0p30`
  while root remained `/dev/mmcblk0p29`. Its exact checkpoint-5 predecessor
  matched, the full 16 MiB write/readback matched `9f7ff84912ff...`, and the
  device shut down cleanly. No fresh backup was made. See the
  [deployment evidence](results/deployment-boot2-20260831.txt).
- A fresh serviceable boot exposed ABI 5 with CPUs 0--7 online, CPUs 8--9
  offline, and every action counter zero. Exactly one CPU8 trigger completed
  P27, P28, SRAM, P30E arming, CPU-operations postboot, and CPU-info capture.
  It stopped at reason `8` with mismatch bitmap `0x2`: expected MIDR
  `0x410fd080`, observed MIDR `0x410fd081`. All other late-target comparisons
  passed; CPU9, CPU_OFF, retry, storage-write, and reboot counts remained zero.
  See the [runtime evidence](results/runtime-attempt-1-midr-mismatch-20260831.txt).

## Analysis

The reason-8 ledger proves CPU8 reached `secondary_start_kernel()` through
CPU-operations postboot and CPU-info capture. Its sole mismatch bit identifies
MIDR, and the expected/observed pair exposes the exact error: the immutable
prior-cycle expectation stored the generic Cortex-A72 model value
`0x410fd080`, while both earlier target-local capsules and this mainline CPU8
read report the named unit's r0p1 value `0x410fd081`. No broader architectural
expectation changed.

## Conclusion

The one physical attempt is attributable and decision-changing. It closes the
post-capabilities localization question: CPU8 reaches CPU-info capture and is
parked by the exact late-target validator solely because the expected-pair MIDR
uses the A72 model base rather than the observed r0p1 value. CPU8 is not online,
and CPU9 remains untouched.

## Follow-up

Repair only the immutable expected-pair MIDR to `0x410fd081`, retain generic
all-revisions capability matching and the exact one-shot CPU8 path, then run
the same offline and physical gates. The ordered action remains in
`docs/ROADMAP.md`; CPU9 stays vetoed until CPU8 is reproducibly online.
