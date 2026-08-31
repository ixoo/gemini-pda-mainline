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
- Buildbox generated and deterministically replayed exactly one patch from the
  checksum-pinned post-`0453` source. Its SHA-256 is `09f8c433...`.
- The source audit proves one CPU8 prepare, one CPU8 arm, at most one readback,
  nine binder KUnit cases, and no new CPU request, CPU9, CPU_OFF, retry,
  power-sequence, storage, or device-action path.
- Buildbox compiled and checksum-validated the focused
  `a72-default-off-binder-kunit` package from project commit `338357c3`.
  Its kernel release is `7.1.3-gemini-a72-binder-kunit`, patchset identity is
  `d1cefcd6...`, configuration identity is `f5658fe7...`, and compressed Image
  identity is `64834105...`. The exact packaged configuration enables the P30E
  wire together with the three focused KUnit suites.
- The first four-CPU QEMU run stopped during secondary bring-up before KTAP.
  A debugger snapshot showed CPU1 taking an instruction abort at
  `arm64_mt6797_a72_p30e_target_publish`; the fault address and that symbol's
  linked address were both `0xffff800080a9e328`. The function was linked in
  `.idmap.text` but called after the MMU was enabled.
- A bounded one-CPU discriminator on the same exact package reached the normal
  terminal marker with all 30 owner, 12 transition, and 9 binder/P30E cases
  passing. This separates the new binder logic from the secondary-entry fault;
  it is diagnostic evidence, not an acceptable replacement for the required
  multi-CPU proof.
- Buildbox generated and deterministically replayed follow-up patch `0455` from
  the exact post-`0454` source. Its SHA-256 is `07380e7a...`; the generator
  proves one normal-text publisher, no idmap publisher, nested MMU-off link
  preservation, terminal-state cache-clean ordering, and no new CPU request,
  CPU9 request, CPU_OFF, retry, or storage path. Strict checkpatch reports no
  warning or check; the sole error is the intentionally absent synthetic DCO
  sign-off on this experiment-only patch.
- Buildbox then compiled and checksum-validated the repaired focused package
  from exact project commit `fffb99b4`. Its patchset identity is `31c58247...`,
  compressed Image identity is `3507babd...`, and configuration identity is
  `f5658fe7...`. The required four-CPU QEMU run reached the expected terminal
  marker with all 30 owner, 12 transition, and 9 binder/P30E cases passing:
  51/51, with no failures, skips, unexpected fault, physical CPU request,
  CPU_OFF request, retry, network, or device action. The sanitized receipt is
  [recorded here](results/focused-kunit-qemu-post-fix-20260831.txt).
- Buildbox compiled the exact production profile from clean published commit
  `23b21b6f`. Its patchset identity is `31c58247...`, compressed Image identity
  is `f629b74a...`, and configuration identity is `96784159...`; the production
  configuration enables P30E and disables KUnit.
- The checksum-pinned composer transferred the package-exact A41 provenance
  leaf into the serviceability/admission DT. The resulting DT identity is
  `461e2d1c...`, with one controller, one binder, one exact runtime-binding
  leaf, no standalone observer, and all required serviceability nodes enabled.
- Two independent candidate assemblies produced byte-identical raw and padded
  images. Two independent validations passed all 32 LK gates, rejected all six
  mutations, and confirmed one CPU8 request path with no CPU request executed,
  no CPU9 route, CPU_OFF route, or retry. The exact padded `boot2` identity is
  `a4ad4915...`; the sanitized receipt is
  [recorded here](results/production-candidate-20260831.txt).
- The first installation preflight correctly rejected the older inherited
  generation-10/stage-5 ledger pin before any write. The guarded installer was
  then retargeted to the already-published exact selector predecessor record:
  generation 14, phase 3, stage 7, terminal 4. A separate read-only preflight
  accepted that checksum-valid record, the exact `cd36efdf...` boot2
  predecessor, and empty admission traces without a retained-RAM or storage
  write. The sanitized receipt is
  [recorded here](results/installation-preflight-20260831.txt).

## Analysis

The predecessor proves the selector repair and the complete power-owner prefix
through CPU_ON, but does not identify whether the target core executed any
kernel entry instruction. P30E is the smallest existing independent observation
path that can resolve that ambiguity without changing the physical power
sequence. The focused multi-CPU run also found a pre-existing P30E section
boundary defect before it could reach `boot2`: the MMU-off claim belongs in
`.idmap.text`, while the publication call from `secondary_start_kernel()` must
be ordinary executable kernel text.

## Conclusion

Running; the repaired P30E candidate has passed the complete hardware-free
gate and is an exact boot candidate. No hardware conclusion until it is
installed with full-partition readback and one attributable trigger result is
captured.

## Follow-up

Install exact padded candidate `a4ad4915...` to inactive `boot2`, verify the
full-partition readback, and shut down. Use its first exact P30E state to choose
the next action: ARMED/EMPTY sends the investigation below `secondary_entry`;
CLAIMED sends it into early arm64 setup; PUBLISHED sends it into the late
completion/notification path. Do not begin a CPU9 transaction until CPU8 is
reproducibly online.
