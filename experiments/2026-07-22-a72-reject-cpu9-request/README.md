# Experiment: fail-closed Cortex-A72 CPU9 request

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-a72-reject-cpu9-request` |
| Status | `hardware control experiment passed; CPU8/9 intentionally remained offline` |
| Subsystem | arm64 SMP, MT6797 PSCI method selection |
| Device variant | Gemini PDA, named unit only |
| Date(s) | 2026-07-22 design, build, and guarded install; 2026-07-23 hardware attempt |
| Investigator(s) | Codex with owner attendance required for hardware |
| Tracking issue | Local roadmap |

## Question or hypothesis

Given Candidate AJ's exact runtime-to-recovery safety-predecessor PASS, will
changing only forced `maxcpus=9` to
`maxcpus=10` dispatch CPU9 after CPU8 returns `-EAGAIN`, with both Cortex-A72
cores still rejected before `PSCI_CPU_ON` and CPU0–7 remaining stable?

This is a CPU9 fail-closed dispatch control. It is not a power-on, topology,
capacity, or scheduling experiment.

## Provenance and environment

- Kernel release/source: Linux 7.1.3, source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Parent: exact [Candidate AJ](../2026-07-22-a72-reject-cpu8-request/README.md),
  whose resolved configuration SHA-256 is
  `64f1c3d1b9a506aad5b0ee0549188abac2fbcff12e9e8aacbda015cf4ee7b8cb`.
- Patch series: unchanged `patches/series-a72-reject-gate`; patch 0092 assigns
  CPU8 and CPU9 the same fail-closed method and returns before generic PSCI.
- Selected configuration: exactly one forced-command-line token changes from
  `maxcpus=9` to `maxcpus=10`. Direct byte substitution predicts resolved
  configuration SHA-256
  `e4e9ffe96810ad135469d42edaa14dc43ad7fb463b23bc3cd3008ca8ba789228`,
  but that value is not a selected package identity until merge,
  `olddefconfig`, and two independent builds reproduce it.
- DTB and initramfs: must remain byte-identical to AJ.
- Boot path: Android-v0 image in live-GPT logical `boot2`, only after exact AJ
  is the validated predecessor.

The exact AJ `System.map` and compiled control flow are recorded in
[`results/static-control-flow-audit-20260722.txt`](results/static-control-flow-audit-20260722.txt).

## Safety assessment

Candidate AJ remains overall `PARTIAL` solely because its attempt-2 visible
console subgate is pending; no console result is inferred. Its separately
adjudicated AK safety-predecessor gate is `PASS`: exact boot-ID-bound runtime
showed one pre-PSCI CPU8 rejection and stable CPU0–7, exact fresh-ID native
reboot returned to changed-boot-ID Gemian, and the full read-only `boot2`
checksum still matched AJ
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`.
This compound evidence is not a paired observer and does not establish a
readable console. See the source-pinned
[`AK predecessor adjudication`](../2026-07-22-a72-reject-cpu8-request/results/ak-predecessor-gate-adjudication-20260722.txt)
(SHA-256
`6e3209d5b433fbeb2b9f5b8eff1b9c5dea1966d1abe04c4b9932ed92bc9077fc`).

That adjudication permits only this one-token, non-powering control to be
built, packaged, and guardedly installed over the exact AJ predecessor. AK
must retain patch 0092's
fail-closed callbacks, no active A72 power provider, no regulator/reset/clock
sequence, no CPU power-off callback, no cpufreq/OPP/capacity/energy-model
policy, and no CPU-map change. Any `PSCI_CPU_ON`, A72 secondary boot, fault,
stall, unexpected reset, or identity mismatch is an immediate stop.

## Associated code

- `configs/gemini-a72-reject-cpu9-request.fragment`: final one-token command-line
  override, applied after AJ's fragment.
- `kernel/manifest.json`: selectable AK profile pinned to the unchanged
  `patches/series-a72-reject-gate` boundary.
- `scripts/candidate_ak.py` and `scripts/validate-profile.py`: independent AK
  identity and exact AJ-to-AK profile gate.
- `scripts/validate-package*.py`, `scripts/validate-boot.py`,
  `scripts/finalize-artifact.py`, and `scripts/validate-artifact*.py`: staged
  two-build and two-artifact reproduction gates. All package, raw artifact,
  manifest, and padded identities are selected from the exact reproduced
  outputs.
- `scripts/build-candidate-ak.sh`: non-flashing Android-v0 assembly; it refuses
  operation until package identities are selected.
- `scripts/collect-runtime.sh`, `scripts/validate-runtime.py`, and the native
  reboot/post-return helpers: source-pinned, fail-closed evidence paths for the
  one attended hardware attempt. Runtime and returned-boot evidence pins remain
  intentionally unresolved until those observations exist.
- `scripts/derive-installer.py`: reconstructs the exact AJ guarded installer,
  proves the transform reversible, and selects only AK's reproduced identities
  plus exact AJ as predecessor.

AJ's validators continue to reject `maxcpus=10` and every CPU9 request; AK has
its own identity rather than presenting the derivative as AJ.

## Procedure

1. Require the exact source-pinned AJ AK-safety-predecessor adjudication: the
   runtime, native reboot, changed-Gemian return, and full AJ `boot2` readback
   chain must pass. Keep AJ's console subgate independently pending and do not
   describe the compound chain as a paired observer.
2. Apply one later profile fragment which changes only forced `maxcpus=9` to
   `maxcpus=10`; retain the exact AJ patch series, DTB semantics, and initramfs.
3. Build twice through `./scripts/dev-vm build-kernel` in independent roots.
   Prove the complete packages and Android-v0 artifacts reproduce, and verify
   the resolved configuration has exactly the one declared token delta.
4. Add production identities plus mutation-tested package, artifact, runtime,
   installer, native-reboot, recovery, and post-cycle gates. Do not reuse AJ's
   identity module as if AK were AJ.
5. Install only over the exact validated AJ predecessor through the guarded
   live-GPT logical-`boot2` path, preserving a private full backup and requiring
   a matching full readback. Do not reboot from the installer.
6. Start the reviewed Gemian disconnect/recovery observation and exact USB
   runtime collector before attended `boot2` selection. Record the actual
   observer attribution; do not predeclare it paired or infer console output.
7. Require, in relative order, exactly one CPU8 rejection/failure pair, exactly
   one CPU9 rejection/failure pair, and the eight-CPU SMP summary. Unrelated
   log lines may interleave, but no pair may duplicate or reverse.
8. At 45+5 seconds require `possible=0-9`, `present=0-9`, `online=0-7`,
   `offline=8-9`, eight processors, one stable boot ID, and advancing CPU0–7
   accounting.
9. Use only the exact fresh-boot-ID-gated native reboot path, recover through a
   changed Gemian boot ID, and verify the full `boot2` checksum read-only.

One hardware attempt is sufficient. Do not repeat an inconclusive identical
artifact unless the observation path itself gains a decision-changing unit
binding or missing independent gate.

## Observations

Linux 7.1.3's serialized present-CPU loop counts CPU0 as visit one, advances in
logical order, and decrements its remaining visit count after both successful
and failed `cpu_up()` calls. Therefore AJ's `maxcpus=9` visits CPU0–CPU8,
whereas `maxcpus=10` visits CPU0–CPU9 even after CPU8 returns `-EAGAIN`.

Exact AJ has SMP and CPU hotplug enabled, parallel hotplug disabled, and both
A72 logical CPUs assigned to the same pre-PSCI rejection callback. The shared
warning rate limit permits both first-call warnings. These are static source
and compiled-binary observations only.

Two independent kernel builds reproduced 227-member packages byte-for-byte
apart from the declared generation timestamp and derived manifest. Two
independent Android-v0 assemblies then reproduced all 20 members and modes.
The raw boot image is 7,380,992 bytes with SHA-256
`e8fd45b4c6b3626330d49c84b13f6c7147ab5d324422bff5901c35545f5b6d28`;
both sparse extension and explicit zero-overlay construction reproduced the
same exact 16 MiB identity
`66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e`.
See [`results/offline-reproduction-20260722.txt`](results/offline-reproduction-20260722.txt).

The production installer was derived from exact AJ and passed its reversible
safety contract. It requires exact AJ on live-GPT logical `boot2`, performs at
most one bounded 16 MiB write, requires a full matching readback, and contains
no reboot or slot-selection path. See
[`results/installer-derivation-20260722.txt`](results/installer-derivation-20260722.txt).

The guarded installer resolved live-GPT logical `boot2` as `/dev/mmcblk0p30`
while exact known-good Gemian remained active on `/dev/mmcblk0p29`. All target
use, stable-power, and stable-boot-ID gates passed. The full pre-write checksum
matched exact AJ, a private mode-0600 backup was preserved, one bounded 16 MiB
write was synced and flushed, and both the remote post-flush checksum and local
full readback matched exact AK
`66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e`.
No reboot or slot selection occurred. See
[`results/install-readback-20260722.txt`](results/install-readback-20260722.txt).

On the named unit, the owner reported a readable console and the exact USB
runtime gate passed after 45+5 seconds. CPU8 and CPU9 were each requested once
in order and each returned the expected pre-PSCI `-EAGAIN`/`-11` rejection;
CPU0-7 remained online with advancing accounting, CPU8-9 remained offline,
and no A72 secondary transition, fault, or unexpected reset appeared. The
boot-ID-bound native reboot then disconnected USB and returned to a distinct,
stable exact-Gemian boot. One attributable full read-only `boot2` checksum on
that returned boot still matched exact AK. See
[`results/hardware-attempt-1-20260723.txt`](results/hardware-attempt-1-20260723.txt).

The first native-reboot evidence interpretation rejected the legitimate fixed
USB-service/BusyBox prelude. The preserved capture was not changed or repeated;
the validator was corrected to require the exact 17-line prelude and global
`HOST -> banner -> prelude -> REQUEST -> wrapper -> RESULT` order, then passed
the original capture and 29 mutation tests. See
[`results/native-reboot-prelude-validator-correction-20260723.txt`](results/native-reboot-prelude-validator-correction-20260723.txt).

## Analysis

The planned one-token derivative uniquely tests whether CPU9 reaches and stays
behind the same kernel gate as CPU8. That is useful before active A72 work
because CPU9 could otherwise remain an unexercised topology entry. It
necessarily repeats CPU8's rejection but introduces no new power mutation.

Expected relevant order:

```text
mt6797-psci: CPU8 boot rejected: A72 power sequence inactive
CPU8: failed to boot: -11
mt6797-psci: CPU9 boot rejected: A72 power sequence inactive
CPU9: failed to boot: -11
smp: Brought up 1 node, 8 CPUs
SMP: Total of 8 processors activated.
```

The hardware attempt establishes warning retention, runtime masks, stable
CPU0-7 accounting, ordered CPU8/CPU9 fail-closed dispatch, native reboot, and
post-return image integrity for exact AK. It does not establish A72 power-on,
secondary execution, scheduling, frequency policy, or usable CPU8/CPU9.

## Conclusion

Confirmed offline: exact AJ's source and compiled control flow continues to
CPU9 after CPU8 returns `-EAGAIN`, and two independent AK builds, packages,
Android-v0 assemblies, and padding constructions reproduce. Candidate AJ's
narrowly scoped AK safety-predecessor gate passes even though AJ's independent
console subgate remains pending. Exact AK's hardware control experiment also
passes: both A72 logical CPUs reached the kernel rejection path in order, no
power transition occurred, CPU0-7 remained stable, native reboot returned to
Gemian, and `boot2` retained exact AK. This was intentionally a negative
control, not an A72 enablement attempt; no Cortex-A72 support is claimed.

## Follow-up

- Run Candidate AL only as the separate mainline I2C6/DA9214 resource
  predecessor, with CPU8/9 still unrequested. Do not select the unsafe draft
  patch 0093.
- Before building Candidate AM, the first active CPU8 experiment, obtain the
  missing owner-synchronized Gemian A72
  offline/online/offline power-state contract for DA9214, SPM, TOPRGU, secure
  registers, DVFSP-locked B/CCI clocks, MP2 DCM, and loaded firmware identity.
