# Experiment: Gemian MT6797 A72 owner-local transition observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-23-gemian-a72-owner-observer` |
| Status | `inconclusive`: four source patches and static checks are complete; compiler and hardware evidence do not yet exist |
| Subsystem | MT6797 A72 hotplug, PSCI, external buck, SPM, iDVFS, B/CCI clocks, MP2 DCM and TOPRGU |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-23 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can a fixed-function observer be placed inside the Gemian 3.18 owners of the
A72 transition resources so that one natural CPU8/CPU9 online/offline
transaction yields attributable pre-state, mutation and post-state evidence
without adding a user-controlled register, SMC, hotplug or policy interface?

This directory answers only the source-preparation part of that question.
Successful patch application is not a compile result, and neither one
establishes safe timing or hardware behavior.

## Provenance and environment

- Exact active Gemian boot image SHA-256:
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`.
- Android boot-image kernel field SHA-256:
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
- Active `Image.gz` stream SHA-256:
  `14b4e079bf87b10b14df09a83673f065a342566daed509767bba08420f6c5257`.
- Correct active appended DTB SHA-256:
  `9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9`.
- Active ramdisk SHA-256:
  `a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4`.
- Active `/proc/config.gz` SHA-256:
  `53b53b62fa5a111cb7d6ea4f513aec1e8a6b436c8c17bfd86cb00a9bc4bf6ae1`.
- Decompressed active configuration SHA-256:
  `231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
- The exact source revision that produced the active kernel remains
  unresolved. Public
  `gemian/gemini-linux-kernel-3.18@59e00a9144d782e148332009a835b99c43382467`
  is selected only because its observer-relevant hooks match the reconciled
  binary/source evidence. It must not be described as the exact active source.
- Source patch commits used to generate this series:
  `7bddafa6`, `c8475b56`, `429afb35`, and `349f24b6`.
- A future source build must use the private recovery-VM environment
  `/home/julien.guest/toolchains/debian-stretch-20170618-arm64-rootfs`,
  pinned to Debian snapshot `20170618T000000Z`, GCC
  `6.3.0 20170516` (`gcc-6`, Debian `6.3.0-18`) and GNU ld `2.28`.
  The 2019 `+deb9u1` rootfs is not an acceptable substitute.
- The reconciliation source is
  [`../2026-07-22-a72-firmware-power-contract/results/active-gemian-kernel-reconciliation-20260723.txt`](../2026-07-22-a72-firmware-power-contract/results/active-gemian-kernel-reconciliation-20260723.txt).

This experiment has no boot-candidate label. `AL` remains the mainline
resource-only work, while `AM` is the first mainline image that made CPU8
active. This Gemian observer series is a separate vendor-kernel diagnostic.

## Safety assessment

The exported proc ABI is root-read-only (`0400`) and fixed-function. It has no
write operation, clearing operation, register selector, address parameter,
SMC selector, CPU-hotplug control, policy control, module parameter or debug
command. Writers append typed records to a preallocated 2048-entry ring; proc
open takes a point-in-time private copy.

That does **not** make the patch zero-effect or ready to boot. The owner-local
DA9214 snapshot temporarily selects page zero and restores the exact previous
page while holding the existing DA9214 mutex. When PAGE_REVERT was originally
set it deliberately omits a verify-read whose access could itself change the
selector. The B/CCI snapshot enables the existing DVFSP arbitration clock,
performs one nominally two-millisecond hardware-semaphore attempt and releases
it. Mutation logging holds existing owner locks across added readbacks. MP2 DCM
is newly serialized by a dedicated spinlock. These operations can change
serialization, latency and transition timing even when every captured value is
discarded.

The patches preserve the vendor transition's mutation order and return-value
ABI. Observer failures are recorded or ignored and do not introduce a new
retry, `BUG`, warning, panic or transition return. Where the observer's SPM
mapping cannot be obtained, the exact original direct RMW path still runs.
The configured DA9214 path replaces two ineffective unsigned-return
`BUG_ON(... < 0)` expressions; the configuration-off path retains them. The
observer deliberately does not repair the vendor ordering in which DCM/iDVFS
actions can precede checking the PSCI result.

Owner serialization and timing are a separate safety gate. Before any device
boot, the final series must receive:

1. a clean source build and compiler-warning review using the pinned 2017
   toolchain environment;
2. a configuration review proving that only the intended diagnostic option
   changes;
3. line-by-line review of DA9214 selector restoration, the hardware-semaphore
   bound, added readbacks, DCM serialization and every lock context;
4. a compatible kernel `checkpatch.pl` run or an explained equivalent;
5. a named artifact identity, packaging/readback validation, recovery plan,
   exact test hypothesis and stop conditions.

No VM, device, partition, boot image, configuration, policy or hardware state
was accessed or changed while preparing this directory.

## Associated code

- [`patches/series`](patches/series): exact four-patch order.
- [`patches/0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch`](patches/0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch):
  typed static ring, transaction IDs and root-read-only snapshot ABI.
- [`patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch`](patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch):
  fixed DA9214, SPM, secure-monitor and B/CCI clock snapshots.
- [`patches/0003-diagnostic-record-A72-power-mutations-under-owners.patch`](patches/0003-diagnostic-record-A72-power-mutations-under-owners.patch):
  owner-serialized SPM, buck, TOPRGU and MP2 DCM mutation records.
- [`patches/0004-diagnostic-correlate-A72-hotplug-lifecycle.patch`](patches/0004-diagnostic-correlate-A72-hotplug-lifecycle.patch):
  HPS, raw/mapped PSCI, secondary-online and offline correlation.
- [`DESIGN.md`](DESIGN.md): event contract, fixed register allowlist and
  concurrency review.
- [`scripts/validate.py`](scripts/validate.py): experiment-local patch
  invariants.
- [`scripts/test-static.py`](scripts/test-static.py): positive and mutation
  tripwire tests for the validator.
- [`results/source-and-static-validation-20260723.txt`](results/source-and-static-validation-20260723.txt):
  exact source/static validation record.

The local validation invocation is:

```sh
python3 experiments/2026-07-23-gemian-a72-owner-observer/scripts/validate.py
python3 experiments/2026-07-23-gemian-a72-owner-observer/scripts/test-static.py
```

Neither command needs privilege, network, VM or device access.

## Procedure

### Completed source preparation

1. Reconcile the exact active image components and active configuration.
2. Select public commit `59e00a…` only as a hook-equivalent source baseline.
3. Keep the recorder, owner snapshots, owner mutations and lifecycle
   correlation as four logical `git format-patch` changes.
4. Apply all four patches in order to a detached `59e00a…` worktree.
5. Run whitespace checks, the experiment validator and its negative tripwire
   tests. Record tool limitations rather than treating a skipped tool as a
   pass.

### Required compiler review before any boot

1. In the recovery VM, verify the selected environment is exactly
   `/home/julien.guest/toolchains/debian-stretch-20170618-arm64-rootfs` and
   reports GCC `6.3.0 20170516` and ld `2.28`. Stop if it resolves to the 2019
   `+deb9u1` environment.
2. Start from a clean `59e00a…` checkout, apply [`patches/series`](patches/series)
   in order, and import the exact active plain configuration identified above.
3. Enable only `CONFIG_MTK_A72_TRANSITION_OBSERVER=y`, retain the complete
   resulting config and diff, and build the full source tree with warnings
   preserved.
4. Review every compiler diagnostic and compare generated symbol/reference
   placement with the source-level hook table in [`DESIGN.md`](DESIGN.md).
5. Stop before packaging or device access. A separate reviewed experiment must
   define the exact boot artifact and transition test.

## Observations

All four patches applied in order to the selected public baseline and the
result passed `git diff --check`. The experiment validator and its deliberate
corruption tests pass. The vendor tree's old `scripts/checkpatch.pl` cannot run
under the host's modern Perl because its own regular expressions are rejected;
this is recorded as a tooling limitation, not as a clean checkpatch result.

No source build, compiler diagnostic review, kernel execution or hardware
transition has occurred.

## Analysis

The source layout supplies the requested observation points and confines
device-specific snapshots to the corresponding owner files. It can correlate
HPS `cpu_up`/`cpu_down` return values, raw PSCI firmware status, Linux-mapped
PSCI status, secondary-online publication, each affinity-info retry, iDVFS,
DCM, buck and final offline state under per-A72 transaction IDs. A ring
overwrite counter exposes loss without adding a control to clear state.

Static checks cannot prove that the old compiler accepts every construct, that
the additional owner-lock duration is safe, that fixed SMC reads are benign at
each hook, or that the hook-equivalent public source exactly represents the
running binary. Those unresolved questions are decision-changing.

## Conclusion

`inconclusive` for hardware behavior. A reviewable four-patch observer series
exists and passes the recorded source/static checks against public
`59e00a…`. It is not yet a kernel, boot image or installable candidate. The
mandatory next result is a clean build plus compiler and owner-timing review in
the pinned 2017 environment.

## Follow-up

Complete the compiler review and preserve its full warnings, configuration
diff and output hashes. Only if that gate passes should a separate experiment
define one natural online/offline capture, retrieval of
`/proc/mt6797_a72_transition`, exact expected event ordering, stop conditions
and how each possible result changes the mainline A72 implementation.
