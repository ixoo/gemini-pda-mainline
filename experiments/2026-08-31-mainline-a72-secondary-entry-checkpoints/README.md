# Experiment: localize CPU8 inside arm64 secondary startup

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-secondary-entry-checkpoints` |
| Status | `running` |
| Subsystem | arm64 secondary entry and MT6797 P30E wire |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

After CPU8 successfully claims its P30E slot in `secondary_entry`, what is the
highest exact checkpoint it reaches before the existing publication in
`secondary_start_kernel()` remains absent?

The predecessor proves physical CPU_ON and early target execution, but its
single CLAIMED state spans `__cpu_setup`, MMU enablement, the virtual switch,
secondary-task setup, and most architecture C initialization. One monotonic
checkpoint word can split that interval without changing the power sequence.

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0456`.
- Parent source state:
  `5d06e3d451788541a2f28666e3427c90320fc440b72a53d8ed6f50427ea7fa55`.
- Parent integrity:
  `a9b9210dfb6aa27a6cec6a9c438d4c7eb1016a8e33cbe29a60fbda458d8dee5e`.
- Build and patch-generation backend: Buildbox only.
- Runtime predecessor: exact padded candidate `459bcf66...`, classified
  [P30E target CLAIMED](../2026-08-31-mainline-a72-p30e-ready-identity-repair/results/runtime-attempt-1-p30e-claimed-20260831.txt).

## Safety assessment

This remains the existing default-off, one-shot CPU8 diagnostic. Patch `0457`
will not add or move a CPU request, CPU9 route, CPU_OFF route, retry, power
operation, storage access, or device action. It will only update P30E's existing
target-owned reason word while state remains CLAIMED and sequence remains zero.
Every update requires the exact A72 MPIDR, ARMED controller state, CLAIMED
target state, zero target sequence, and a strictly increasing known checkpoint.

The MMU-off checkpoint preserves the `__cpu_setup` SCTLR result and boot mode,
uses only caller-clobbered registers, and performs the existing full-slot cache
clean. Later checkpoints use the existing normal-text slot mapping, lock,
invalidate, and full-slot clean. Observation failure does not create another
CPU action. The existing watchdog remains the recovery owner and CPU9 remains
vetoed.

No device image may be prepared until deterministic patch replay, source
review, focused multi-CPU QEMU, and the exact production build pass on
Buildbox.

## Associated code

- `DESIGN.md` freezes checkpoint identities and the decision map.
- `scripts/source_edits.py` applies the exact checksum-pinned source edits.
- `scripts/generate_patch.py` creates and replays canonical patch `0457` and
  audits its call and safety inventory.
- `scripts/generate-on-buildbox` binds generation to the exact pushed project
  commit and prepared post-`0456` source.

## Procedure

1. Generate and deterministically replay one normal format-patch on Buildbox.
2. Review the MMU-off register contract, monotonic C writer, ABI-4 diagnostic,
   status field, and focused fake readback.
3. Run manifest invariants, strict style checks, and the existing focused
   four-CPU KUnit/QEMU suite on Buildbox.
4. Build the exact production profile on Buildbox and independently construct
   and validate one successor container.
5. State the exact hypothesis and decision map, deploy only to live-resolved
   inactive `boot2`, verify full readback, and shut down.
6. On one serviceable boot, prove pristine zero execution and issue exactly
   one CPU8 trigger. Do not request CPU9, CPU_OFF, retry, or reboot.

## Observations

- The exact predecessor reached P30E target state `CLAIMED`, target sequence
  `0`, controller sequence `1`, and returned `-EIO` with CPU8 still offline.
- Changed-ID Gemian recovery contained no attributable ramoops trace.
- The prepared post-`0456` Buildbox source and all nine intended parent-file
  checksums are pinned in `scripts/source_edits.py`.
- Deterministic generation produced canonical patch `0457` with SHA-256
  `485b75d1755475dc855a8a847e72b15253e5029521fe6b0b73f360d0348ca8f4`.
- Buildbox compiled patchset
  `f3f64e40d05ffa5a91ba28486fe93b70cff293597e415404a45e690c02c0f654`
  in both the live-trigger and default-off binder KUnit profiles.
- The no-network, four-vCPU binder KUnit boot passed all 51 tests, including
  the P30E checkpoint-reason readback, with no physical CPU request, CPU_OFF,
  or retry. See
  [the exact classifier record](results/focused-kunit-qemu-20260831.txt).
- Buildbox produced the exact production package from commit `e91394af`; the
  independently validated raw candidate is `fdf302e8...` and its exact 16 MiB
  boot2 representation is `6d0bf75b...`. All 32 LK gates passed and all six
  negative container mutations were rejected. See
  [the candidate record](results/production-candidate-20260831.txt).
- Exact candidate `6d0bf75b...` replaced predecessor `459bcf66...` on
  live-resolved inactive `/dev/mmcblk0p30` (`boot2`). The synced and flushed
  full-partition readback matched, no fresh backup was made, and the device was
  cleanly shut down without reboot. See
  [the deployment record](results/deployment-boot2-20260831.txt).

## Analysis

The predecessor eliminates no-entry and pre-CPU_ON explanations. The focused
KUnit proof validates that the new reason value is carried through the existing
diagnostic without adding a CPU or device action. The smallest remaining useful
observation is therefore the highest monotonic target checkpoint inside the
already-proved CLAIMED interval. Repeating `459bcf66...` would add no new
measurement and is forbidden.

## Conclusion

Running; no new hardware conclusion until the exact successor is built and one
attributable trigger is classified.

## Follow-up

Install exact padded candidate `6d0bf75b...` only to live-resolved inactive
`boot2`, verify its full-partition readback, and shut down. On its first
serviceable boot, require pristine ABI-4 reason zero, then issue one CPU8
trigger. Interpret the highest retained reason as follows:

- `0`: no checkpoint beyond the already-proved target claim;
- `1`: `__cpu_setup` returned;
- `2`: the secondary task and virtual entry were ready;
- `3`: `secondary_start_kernel()` began;
- `4`: the identity map was removed;
- `5`: local CPU capabilities were accepted;
- `6`: target validation and topology completed;
- `7`: interrupt, IPI, and NUMA setup completed.

Terminal publication or CPU8 online moves the boundary later. Any malformed
state/reason/sequence combination is rejected rather than interpreted. Use the
result to select one repair or narrower discriminator. Do not begin CPU9 work
until CPU8 is reproducibly online.
