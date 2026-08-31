# Experiment: localize the CPU8 secondary-entry boundary with P30E

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-p30e-entry-diagnostic` |
| Status | `running` |
| Subsystem | MT6797 CPU8 binder, arm64 secondary entry, and P30E wire |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

After the exact CPU8 power transaction returns zero from CPU_ON, does CPU8
reach `secondary_entry`, and does it progress as far as the publication point
in `secondary_start_kernel()` before generic secondary completion times out?

The existing P30E wire gives three decision-bearing results: an unchanged
ARMED/EMPTY target state means CPU8 did not reach `secondary_entry`; CLAIMED
means it reached the early entry hook but not the late publication point; and
PUBLISHED means it reached the late hook and moves the fault boundary into the
remaining generic arm64 completion path.

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0453`.
- Parent source state:
  `cf235b38e3b867af35e6b8ee62daa01e85dbabc4c1b7beef114073abf894eaab`.
- Parent integrity:
  `0826f01169395f51d7a6c8ef2ff1da28e54b3f4aa3eda6f266881b064fe56bf2`.
- Build and patch generation backend: Buildbox only.
- Runtime predecessor: the exact selector-mask repair result in
  [the prior experiment](../2026-08-31-mainline-a72-sram-selector-mask-contract-repair/README.md).

## Safety assessment

This is a default-off CPU8 diagnostic. When both the existing binder and P30E
wire are selected, it prepares one identity-bound CPU8 handoff, consumes the
existing CPU_ON budget, arms one retained 2 KiB CPU8 slot, and invokes the
unchanged CPU_ON callback. An immediate callback error or generic rollback can
perform at most one controller readback. The target writes only its existing
state words if it reaches the already-reviewed early or late hooks.

The integration adds no CPU request route, CPU9 route, CPU_OFF route, retry,
power-sequence call, storage write, reboot, or automatic device action. Every
new production branch checks CPU8 and the CPU8-up operation. A preparation or
arm failure is terminal and fail-closed before CPU_ON. CPU9 remains vetoed.

No device image may be prepared until deterministic replay, review, focused
KUnit/QEMU, and the exact production build pass on Buildbox.

## Associated code

- `scripts/source_edits.py` applies the checksum-pinned six-file source change.
- `scripts/generate_patch.py` creates and replays canonical patch `0454`,
  audits operation counts, and rejects CPU9, CPU_OFF, retry, and storage paths.
- `scripts/generate-on-buildbox` pins the clean project commit and managed
  post-`0453` source before producing a checksum-covered review package.

## Procedure

1. Generate and deterministically replay one normal format-patch on Buildbox.
2. Review the CPU8-only prepare, arm, and one-readback integration and its
   ARMED/CLAIMED/PUBLISHED KUnit branches.
3. Enable the existing P30E object only in the focused binder KUnit and exact
   live-trigger production fragments.
4. Run manifest invariants, focused KUnit/QEMU, and the exact production build
   on Buildbox.
5. Assemble and validate one successor candidate, install it to inactive
   `boot2` with full-partition readback, and shut the device down.
6. Capture a pristine boot frame, issue exactly one CPU8 trigger, and classify
   the one P30E readback. Do not request CPU9, CPU_OFF, a retry, or a reboot.

## Observations

- The predecessor reached transition stage 7 (`ONLINE_WAIT`) after a
  zero-returning CPU_ON callback, but CPU8 never completed generic arm64
  secondary startup.
- Its production configuration had
  `CONFIG_ARM64_MT6797_A72_P30E_WIRE` disabled, and no production caller armed
  the existing wire, leaving the entry boundary unobservable.

## Analysis

The predecessor proves the selector repair and the complete power-owner prefix
through CPU_ON, but does not identify whether the target core executed any
kernel entry instruction. P30E is the smallest existing independent observation
path that can resolve that ambiguity without changing the physical power
sequence.

## Conclusion

Running; no hardware conclusion until an exact candidate is built and one
attributable trigger result is captured.

## Follow-up

Use the first exact P30E state to choose the next action. ARMED/EMPTY sends the
investigation below `secondary_entry`; CLAIMED sends it into early arm64 setup;
PUBLISHED sends it into the late completion/notification path. Do not begin a
CPU9 transaction until CPU8 is reproducibly online.
