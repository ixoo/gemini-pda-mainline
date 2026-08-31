# Experiment: repair the exact A72 expected MIDR revision

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-r0p1-expected-pair-repair` |
| Status | `complete; pre-trigger rejection localized with zero CPU requests` |
| Subsystem | arm64 late-CPU expected pair |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Will replacing the immutable expected-pair MIDR model base `0x410fd080` with
the named unit's independently observed Cortex-A72 r0p1 value `0x410fd081`
allow CPU8 to pass exact late-target validation and continue toward generic
online publication?

## Provenance

- Parent: canonical Linux 7.1.3 series through patch `0458`.
- Parent prepared source state:
  `9c4c8924132e37a40fb6b334e8bcfa4e1d241bd34542a6736d6fba9f5e488b8e`.
- Parent source integrity:
  `19387cb31b807805a120732f76b2183534aa63ab9cb811f1acb20dd185616e10`.
- Parent `mt6797_psci.c` SHA-256:
  `db06b8ad0f8552c908c4f29f7cda4a86745efceea27e0d8a15cd68dfe93c7265`.
- Runtime selector: predecessor reason 8, bitmap `0x2`, expected
  `0x410fd080`, observed `0x410fd081`.

## Safety assessment

This is a one-line expectation repair. It adds no hardware access, power step,
CPU request, CPU9 route, CPU_OFF route, retry, storage access, retained-RAM
access, or reboot path. The existing default-off one-shot CPU8 transaction and
watchdog recovery ownership remain unchanged.

## Procedure

1. Generate and replay canonical patch `0459` on the exact managed Buildbox
   source.
2. Prove the revision-neutral capability model checks and action-call inventory
   are unchanged.
3. Add the patch to the canonical series and audit every manifest profile.
4. Build the focused KUnit and production profiles on Buildbox and run the
   existing no-network 51-test suite.
5. Construct and independently validate one exact production candidate.
6. Deploy only to live-resolved inactive `boot2`, verify full readback, and
   shut down.
7. On one fresh boot, prove zero prior execution and issue CPU8 exactly once.

## Current conclusion

Buildbox generated and replayed canonical patch `0459` from the exact post-0458
source. The patch changes one source line, passes strict Checkpatch with zero
findings, keeps all revision-neutral model checks unchanged, and adds no action
path. See the [generation evidence](results/patch-generation-20260831.txt).

The repair is selected by exact mainline runtime evidence and agrees with the
independent CPU8/CPU9 target-local capsules. No new hardware conclusion exists
until the successor passes offline gates and one attributable CPU8-only boot.

Both focused KUnit profiles and the production profile compile and package on
Buildbox from clean project commit `e0090fe57490...`; all package checksums
validate. See the [Buildbox evidence](results/buildbox-builds-20260831.txt).

The exact default-off binder package passes all 51 tests in its no-network,
four-vCPU QEMU boot. No physical CPU, CPU_OFF, retry, network, or device action
occurred. See the [focused KUnit evidence](results/focused-kunit-qemu-20260831.txt).

The exact production package, package-owned provenance leaf, preserved
serviceability DT, two independent raw assemblies, two independent padding
constructions, all 32 LK gates, independent layout validation, and six
negative container mutations pass. The selected padded `boot2` candidate is
`b5328f6a4226...`. See the
[candidate evidence](results/production-candidate-20260831.txt).

The physical hypothesis and checkpoint decision map are frozen before the
write. Reason 8 means the exact validator still disagrees; reasons 9--11 and
publication each select one later generic CPU-online interval; CPU8 online
requires a fresh-boot repeat before CPU9. See the
[predeployment record](results/predeployment-hypothesis-20260831.txt).

The live GPT resolved inactive `boot2` as `/dev/mmcblk0p30` while Gemian ran
from `/dev/mmcblk0p29`. Stable power and the exact predecessor passed the
deployment gates. The installer wrote, synchronized, flushed, and fully read
back exact padded candidate `b5328f6a4226...`; the full-partition checksum
matched, no fresh backup was created, and the device then shut down and stayed
unreachable. See the [deployment evidence](results/deployment-boot2-20260831.txt).

The first fresh boot reached the exact kernel and serviceability frame with
CPU0--7 online and CPU8--9 offline, but the pre-trigger gate rejected READY
before any CPU request. The failure-only plan mask was `0x12f7b00`; the target
and required capability sets had lost the three v2/v4/BHB bits while the bound
evidence mask remained zero. Source tracing localizes the cause to the
mitigation planner's `late_cpu_expected_field_valid()` guard: it still requires
the expected MIDR to equal the revision-zero `MIDR_CORTEX_A72` literal, so the
new exact r0p1 expected value makes those otherwise valid expected fields
unresolved. The device was returned through the validated USB reboot path to a
changed-ID Gemian boot. See the
[runtime evidence](results/runtime-attempt-1-pretrigger-plan-rejection-20260831.txt).

This is not a CPU8 execution result: the trigger was never sent. The selected
successor is a one-line model-mask repair to that stale guard, leaving the
exact r0p1 late-target comparison unchanged.

CPU9 remains vetoed until CPU8 is reproducibly online.
