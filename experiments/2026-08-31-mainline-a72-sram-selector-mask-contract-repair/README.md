# Experiment: repair the CPU8 SRAM selector-mask contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-sram-selector-mask-contract-repair` |
| Status | `selector repair passed live; CPU8 now stops at generic secondary completion` |
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
- `scripts/collect-recovery.sh` and `scripts/classify-recovery.py` preserve and
  validate the exact changed-ID transition ledger even when the advisory
  admission-entry trace is absent.

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
- Live GPT resolved inactive, unmounted 16 MiB `boot2` as `/dev/mmcblk0p30`;
  active root remained `/dev/mmcblk0p29`. The installed predecessor and exact
  generation-10 stage-5 ledger matched the diagnostic result. The installer
  made no fresh backup, wrote `cd36efdf...`, synchronized and flushed it, and
  obtained the same full-partition readback. It then shut the device down;
  SSH and three consecutive TCP probes confirm it is off. See the
  [deployment result](results/deployment-boot2-cd36efdf-20260831.txt).
- The pre-armed first physical boot saw neither the mainline USB interface nor
  a netcat session before a changed-ID Gemian return. No CPU8 trigger was sent.
  Changed-ID recovery confirmed the exact `cd36efdf...` image remains on
  `boot2`, found no pstore file, and found both the transition ledger and
  admission trace empty with the controller not established. There were zero
  CPU8, CPU9, CPU_OFF, retry, or native reboot requests and no retained-RAM
  write. See the
  [runtime result](results/runtime-boot-attempt-1-prearm-reboot-20260831.txt).
- The one allowed exact repeat reached boot ID `b8e5d9c1...`, passed the
  pristine ABI-2 serviceability gate, and consumed exactly one CPU8 trigger.
  The repair worked: both `0x4008fb` selector reads now match the complete
  `0xfff` binder contract, P28 completion returned zero, and the transition
  advanced from SRAM stage 5 to online-wait stage 7.
- The CPU8 callback returned zero and one request was issued, but generic arm64
  never reported secondary completion. The transition terminated with
  `-EIO`; CPUs 0--7 remained online and CPUs 8--9 remained offline, with zero
  CPU9, CPU_OFF, retry, or native reboot requests. The recovery watchdog then
  returned the unit to changed-ID Gemian.
- Changed-ID recovery preserved a checksum-valid generation-14 terminal ledger
  at stage 7. The advisory admission trace is empty, consistent with the live
  `entry_trace_ret=-EIO`; pstore contains no attributable candidate identity.
  The installed image remains exact. See the
  [runtime result](results/runtime-attempt-2-online-wait-timeout-20260831.txt).
- The exact production configuration has the existing P30E MMU-off wire
  disabled and the canonical series has no production arm caller, so this boot
  cannot distinguish a CPU8 that never reached `secondary_entry` from one that
  entered but stopped before `secondary_start_kernel()` completed.

## Analysis

The physical owner and binder currently apply different result contracts to
the same selector. The owner accepts `(selector & GENMASK(11, 0)) == 0x8fb`
and separately requires the full reads to be identical. The binder compares
each full value directly to `0x8fb`, rejecting valid upper status bits after
the owner has already verified and sealed the result. The proposed change
makes the consumer use the producer's existing contract without changing the
hardware transaction.

## Conclusion

The selector-mask hypothesis is confirmed on the named device and exact
revision. The repaired consumer accepted the owner's stable masked result and
P28 completed. CPU8 still is not online: the next failure is the generic arm64
secondary-completion timeout after a zero-returning CPU_ON callback. Candidate
`cd36efdf...` is retired and must not be repeated.

## Follow-up

Add one default-off CPU8 P30E entry diagnostic around the existing wire object:
arm the exact transaction before CPU_ON, preserve its one-shot and fail-closed
semantics, and expose one read-only controller-side snapshot on generic
rollback. An unchanged ARMED state localizes the fault before
`secondary_entry`; CLAIMED localizes it between entry claim and
`secondary_start_kernel()` publication; PUBLISHED moves the investigation to
the later architecture bring-up path. Prove the wiring in focused Buildbox
KUnit/QEMU before preparing one successor candidate. Retain the CPU9 veto.
