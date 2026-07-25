# Experiment: MT6797 A72 firmware and power contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-a72-firmware-power-contract` |
| Status | `completed` |
| Subsystem | MT6797 Cortex-A72 external power, PSCI, secure iDVFS, PLL, DCM, and CCI |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Do the pinned public Gemian kernel source, the private immutable secure-firmware
backup, and retained runtime evidence define a complete and reversible contract
for replacing draft patch 0093 with a safe MT6797 Cortex-A72 power provider?

The question separates three layers that patch 0093 partially conflates:
Linux-owned external power preparation, secure-firmware-owned CPU/cluster
bring-up, and post-`CPU_ON` Linux clock policy.

## Provenance and environment

- Public vendor kernel source: Gemian Linux 3.18 commit
  [`d388d350cb2dda8f23b99be6fa5db9628896e87f`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/d388d350cb2dda8f23b99be6fa5db9628896e87f),
  inspected read-only in recovery VM `gemini-pda-build-recovery-20260717`.
- Later reconciliation separated the active March 29 boot image from the
  different May 24 `gbp59e00a` package installed in the filesystem. The active
  image is `3.18.41+ #7`, built with GCC 6.3.0-18; its boot image, Android
  kernel field, and plain configuration have SHA-256
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`,
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`,
  and `231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
  Its exact public source commit remains unresolved. Public commit
  `59e00a9144d782e148332009a835b99c43382467` is the chosen observer-source
  equivalent, not exact active provenance: the observer-hook blobs are
  identical across the relevant March/April public lineage and agree with the
  active binary, while the active private image also contains the
  `MAX_RESERVED_REGIONS=32` fix and a different keymap. See
  [`results/active-gemian-kernel-reconciliation-20260723.txt`](results/active-gemian-kernel-reconciliation-20260723.txt).
- Secure firmware: private mode-0600 `tee1` and `tee2` backups captured from the
  named unit on 2026-07-15. Both are 5 MiB and have SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
  The images remain Git-ignored and are not redistributed.
- Firmware identification found offline: `v1.0(debug):df3e3f8`, built
  `15:46:24, May 17 2019`. This identifies the analyzed payload; it is not yet
  a read-only measurement proving that every future boot uses the same payload.
- Runtime cross-check: retained Gemian capture
  `artifacts/runtime-captures/gemian-cpu-scheduler-20260721/live-boot-385cc5d1.txt`,
  SHA-256 `aeabdc0d62aaca0520ff9f8a849870f5f2b1b7d5aeaea3e5494ea3c4a2020ba4`.
- Candidate context: fail-closed patch 0092 SHA-256
  `cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5`;
  unselected draft patch 0093 SHA-256
  `25919426c790a8f34945070c5f76aea678470708de0c2204c0691a19c41c936f`.
- Detailed findings and source hashes are in
  [`results/a72-firmware-power-contract-prerequisites-20260722.md`](results/a72-firmware-power-contract-prerequisites-20260722.md).
- A later live, read-only identity check resolved both GPT TEE labels and found
  that each complete 5 MiB slot matches the exact privately analyzed payload.
  The boot ID and external-power state remained stable around both reads; no
  firmware bytes were copied into Git. See
  [`results/live-tee-identity-20260723.txt`](results/live-tee-identity-20260723.txt).

## Safety assessment

This investigation was entirely offline and read-only. It did not connect to
the live Gemini, invoke an SMC on hardware, change a CPU mask, load a module,
write a partition, select a candidate, build a kernel, or reboot the device.
The private firmware was analyzed only in the approved recovery VM and no
firmware bytes or disassembly were copied into Git.

The resulting report is deliberately not authorization to activate patch 0093.
It defines fail-closed prerequisites and a later read-only Gemian capture. An
active CPU8 experiment still requires its own kernel/DT/configuration
hypothesis, independent watchdog and USB evidence, exact candidate identity,
and recovery boundary.

## Associated code

No code was executed on the device and no kernel code was changed. Inputs were:

- pinned public Gemian source paths and hashes listed in the detailed report;
- private `tee1`/`tee2` backup images retained below
  `artifacts/device-partitions/20260715T020041Z/`;
- the retained Gemian runtime capture above;
- [`patch 0092`](../../patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch)
  and [`draft patch 0093`](../../patches/v7.1.3/0093-soc-mediatek-enable-MT6797-A72-power-sequence.patch).

## Procedure

1. Pin and hash each relevant public Gemian source file at commit `d388d350`.
2. Reconstruct the vendor Linux external-buck sequence, its delays, DCM
   transition, CPU-on ordering, and incomplete CPU-off path.
3. Analyze the immutable secure-firmware payload offline to identify the
   implemented SMC dispatcher entries, argument and return conventions, the
   PSCI-owned A72 PLL/MTCMOS/reset sequence, and CCI coherency ownership.
4. Cross-check the inferred order against the retained working Gemian boot log.
5. Compare the resulting contract to patch 0093 and classify each state change
   by owner, observability, and rollback confidence.
6. Enumerate the missing values that must be captured read-only during natural
   Gemian HPS transitions before an active mainline implementation is selected.
7. Reconcile the exact active boot components against the separately installed
   package and select a public source equivalent only for verified
   observer-relevant blobs.

## Observations

The public vendor kernel establishes a narrow external preparation sequence:
release the MP2 cluster-top reset bit, perform a B-PLL ordering read, hold the
PWRAP SPI controller in reset while enabling DA9214 BUCKB, wait 1 ms for a
hotplug transition, clear both external-buck isolation bits, release PWRAP,
wait 240 microseconds, request a 1.1 V SRAM-LDO setting through secure firmware,
wait another 240 microseconds, and only then call standard PSCI `CPU_ON`.

Offline firmware analysis establishes that PSCI, not Linux, programs the
initial A72 PLL/mux/divider, powers the MP2 cluster and individual CPU8/9
MTCMOS domains, manages their reset, and admits the cluster to CCI coherency.
Linux must not duplicate those operations. The firmware's SRAM-LDO service
always returns zero in the captured build, so its return value is not proof of
the resulting register state.

The vendor CPU-off path disables BUCKB and calls an SRAM-LDO disable function
that is actually a no-op. It does not reconstruct external isolation, reset,
PLL, or DCM state. Existing evidence therefore does not define a safe inverse.

On 2026-07-23, a live read-only check resolved `tee1` and `tee2` from the
running GPT, verified each as an unmounted 5 MiB partition, and hashed both
complete slots. Each matches the exact payload used by the offline firmware
analysis. This closes persistent TEE-slot identity for the named unit; it is
not a dump of runtime secure memory and does not replace the missing
synchronized power-state observation.

Offline reconciliation on the same date explains the earlier source/binary
logging contradiction without assigning a false commit identity. The active
March 29 boot image is not the May 24 package whose version contains
`gbp59e00a`. Its exact public source commit remains unresolved. Commit
`59e00a` is instead a chosen equivalent for the verified observer-hook blobs;
its active HPS action-end printk agrees with the active binary, unlike later
`d388d350`, where that block is commented. The equivalent source identifies
owner-safe observer locations for the DA9214 transaction, TOPRGU reset,
protected B/CCI clock tuple, raw and mapped PSCI results, secondary completion,
MP2 DCM, and the last-A72 offline transition. HPS action-end increments local
policy counts even when `cpu_up()` fails, so it remains policy evidence rather
than completion evidence.

## Analysis

The on-path ownership split, observer-relevant source equivalence, observer
hook locations, and SMC ABI are now substantially resolved. The exact active
whole-tree source revision is not. More broad binary reverse engineering is
not a prerequisite for the observer, because the relevant public blobs were
reconciled independently. A safe active implementation is still blocked by
missing transaction-local pre-state and inverse evidence.
In particular, no retained capture contains synchronized offline/online values
for DA9214 BUCKB, SPM external isolation, TOPRGU PWRAP reset, SRAM-LDO state,
MP2 DCM, and the protected B/CCI clock fields.

The first implementation should be a one-way, cluster-singleton CPU8 experiment
with CPU hotplug-off unavailable. Before the external-isolation write it may
undo only changes for which it captured and exclusively owns the prior state.
At or after that write, any failure must fault the provider, retain power, make
no retry, and rely on the independently proven watchdog/native reset recovery
path. CPU9 is a separate follow-up after CPU8 completes and is observed.

## Conclusion

`rejected` for the hypothesis that existing evidence defines a complete,
reversible implementation contract. The exact forward ownership boundary and
the implemented secure-firmware ABI are now documented, but the external
pre-state and inverse remain unproven. Draft patch 0093 must remain unselected
and must not be used as an active boot candidate.

## Follow-up

Use bounded Gemian load only to calibrate a natural HPS trigger. Implement the
fixed-register, owner-local in-kernel observer as an unlabeled observation
experiment from the chosen equivalent source, preserving the exact active
ramdisk, DTB, and Android-v0 container contract, while deriving configuration
from the exact active configuration and recording only the observer delta. Use
that trigger to capture the complete online and last-A72-offline transactions.
Do not write `/sys/devices/system/cpu/*/online`, use `/dev/mem`, expose
arbitrary SMC/register access, or change frequency/voltage policy. Candidate AL
is the separate mainline I2C6/DA9214 resource-only predecessor and must not
request CPU8/9. Only after AL and the owner-local observations are reviewed
should patch 0093 be replaced with a new one-way provider for Candidate AM, the
first active mainline CPU8 experiment.
