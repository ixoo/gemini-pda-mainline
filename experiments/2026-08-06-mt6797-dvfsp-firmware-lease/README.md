# Experiment: MT6797 I2C6 firmware-owner lease contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-mt6797-dvfsp-firmware-lease` |
| Status | `public hybrid owner source identified; mainline owner and image admission unproven` |
| Subsystem | MT6797 DVFSP/CSPM, I2C6 firmware ownership |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `PARTIAL_HYBRID_OWNER_SOURCE_IDENTIFIED` |

## Question

Can the missing vendor `SEMA_I2C_DRV` boundary be represented as a strict
private callback protocol without pretending that the Linux generation/cookie
lease is firmware ownership or adding an unreviewed MMIO path?

## Result so far

Patch `0175` defines a default-unregistered, platform-private callback pair.
The request carries ABI/user identity, pause-source `0x2`, `SW_PAUSE` bit 13,
`FW_DONE` bit 15, the vendor 2 ms bound, and the exact Linux transfer
generation/cookie. A successful acquire must echo the identity, return a
nonzero opaque owner handle, report all three pause words and all three
`FW_DONE` words, and only then create the firmware lease. Release requires the
same handle and clears the pause-source and all pause words. Registration
requires both callbacks and cannot be removed while a lease is held.

An absent owner returns a structured `-EOPNOTSUPP`. A malformed refusal,
timeout, state change, stale token, or invalid acquire/release response faults
the handoff; the code never guesses an inverse. No callback is registered by
the patch, and the current provider remains read-only.

This is a protocol boundary, not proof that the stopped one-way receiver is
authoritative for the vendor firmware. The external owner and any firmware
implementation remain unproven.

The exact retained vendor-kernel ELF and the Candidate AN observer now have a
stronger reconciliation: both use the same CSPM window
(`0x11015000..0x11015fff`) and the same `SW_RSV0..6` offsets, including the
three SW_PAUSE bit-13 words and three FW_DONE bit-15 words. This proves
register-window identity, not receiver authority. Candidate AN disabled I2C6,
did not exercise the pause handshake, observed no FW_DONE response, and left
I2C_APPM ungated, so the external owner gate remains open.

A read-only revalidation of the public Gemian kernel source now identifies the
historical hybrid owner directly. Its `cspm_probe()` maps CSPM and CSRAM under
one owner, obtains the `INFRA_I2C_APPM` clock, and initializes the SW/HW status
windows. Its `cspm_go_to_dvfs()` performs the reset, instruction-memory fetch,
register/event/wakeup setup, CSRAM record initialization, and PCM kick. The
same owner routes `SEMA_I2C_DRV` through the three-word SW_PAUSE/FW_DONE
handshake and paired clock release. The source embeds both governor and
non-governor PCM descriptors; the non-governor `pcm_dvfs_v0.1_160131_02`
descriptor matches the retained vendor ELF and public array identity. The
repository and header are GPLv2, but source attribution, notice propagation,
and mainline image packaging still require an explicit admission step. The complete source identity and line anchors
are recorded in
[`results/public-hybrid-owner-source-20260806.txt`](results/public-hybrid-owner-source-20260806.txt).
This closes historical owner attribution, not the current mainline owner gate:
the handoff still maps only CSPM, has no PCM image residency/start path, and
registers no callback. Vendor `BUG()` and unbounded wait behavior also cannot
be copied directly into a mainline failure/PM path.

## Safety and nonclaims

- The patch adds no `readl()`, `writel()`, I2C transfer, regulator operation,
  CPUHP operation, PSCI call, or CPU_ON path.
- There is no Device Tree consumer and no callback registration in the current
  source series.
- The result does not authorize a DA921x page/register-data write, a provider
  vote, a boot candidate, CPU8/CPU9 admission, or device validation.
- The retained Gemian archive and managed reverse-engineering payload remain
  userspace/PCM evidence only; LK/TEE/SCP owner payloads are not present.

## Evidence

- [Protocol design](DESIGN.md)
- [PCM residency/start contract](PCM_START_CONTRACT.md)
- [Static oracle](scripts/oracle.py)
- [Source validation](results/source-validation-20260806.txt)
- [Buildbox validation](results/buildbox-validation-20260806.txt)
- [Initial Buildbox input failure and repair](results/buildbox-failure-20260806.txt)
- [Exact retained vendor-kernel SEMA contract](results/vendor-kernel-sema-contract-20260806.txt)
- [Public hybrid owner source](results/public-hybrid-owner-source-20260806.txt)
- [Public owner startup-state boundary](results/public-owner-startup-state-20260806.txt)
- [Public Gemian CPU-clock owner corroboration](../2026-07-12-mt6797-clock-power-reset-recovery/results/public-gemian-cpu-clock-backend-20260806.txt)
- [Buildbox validation after owner-source review](results/public-owner-buildbox-validation-20260806.txt)
- [Current-head full-profile Buildbox resume](results/current-head-full-buildbox-20260806.txt)
- [Dormant state-owner contract Buildbox validation](results/state-owner-contract-buildbox-20260806.txt)
- [State-owner transition-hold Buildbox validation](results/state-owner-transition-hold-buildbox-20260806.txt)
- [Bounded PCM adapter admission model](results/pcm-adapter-model-20260806.txt)
- [Bounded PCM admission shell Buildbox validation](results/pcm-adapter-shell-buildbox-20260806.txt)
- [Protected state-owner identity Buildbox validation](results/state-owner-identity-buildbox-20260806.txt)
- [Protected state-backend composition Buildbox validation](results/protected-state-backend-composition-buildbox-20260806.txt)
- [Protected clock readback transport Buildbox validation](results/protected-clock-readback-buildbox-20260806.txt)
- [Protected clock and BigiDVFS readback Buildbox validation](results/protected-readback-buildbox-20260806.txt)
- [Protected-owner protocol identity revalidation](results/protected-owner-protocol-20260806.txt)
- [Public DVFS startup-state owner boundary](results/public-dvfs-state-owner-20260806.txt)
- [Mainline clock/state-owner inventory](results/mainline-clock-owner-inventory-20260806.txt)
- [Current-head bfd04ae full-profile Buildbox resume](results/current-head-bfd04ae-full-buildbox-20260806.txt)
- [Calibration lifecycle Buildbox validation](results/calibration-lifecycle-buildbox-20260806.txt)
- [Transition-lock Buildbox validation](results/transition-lock-buildbox-20260806.txt)
- [Calibrated table-state Buildbox validation](results/calibrated-table-state-buildbox-20260806.txt)
- [Locked MT6797 EEM readback Buildbox validation](results/eem-readback-buildbox-20260806.txt)
- [EEM calibration-builder Buildbox validation](results/eem-calibration-builder-buildbox-20260806.txt)
- [Protected clock-state decoder Buildbox validation](results/clock-state-decoder-buildbox-20260806.txt)
- [Runtime invalidation ledger Buildbox validation](results/runtime-invalidation-buildbox-20260806.txt)
- [Runtime notifier binding Buildbox validation](results/runtime-binding-buildbox-20260806.txt)
- [Receiver register-window identity reconciliation](results/receiver-register-identity-20260806.txt)
- [Retained TEE secure-owner disassembly](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt)
- [Retained SCP local-alias inventory](../2026-08-06-da921x-page-owner-audit/results/scp-alias-inventory-20260806.txt)
- [Patch 0175](../../patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch)
- [Dormant state-owner contract](../../patches/v7.1.3/0192-soc-mediatek-define-MT6797-state-owner-contract.patch)
- [Dormant state-owner transition hold](../../patches/v7.1.3/0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch)
- [PCM start contract result](results/pcm-start-contract-20260806.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-06-mt6797-dvfsp-firmware-lease/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-06-mt6797-dvfsp-firmware-lease/scripts/pcm_adapter_oracle.py
```

## Follow-up

The exact pushed commit `23c793aefaccef36253b37654397199c24a228d1` now passes
the named Buildbox profile and package checksum validation, and the single
validated package has been fetched locally; this is compile-only evidence. The next
hardware-independent gate is an attributable external owner implementing this
protocol, or a reviewed one-way receiver proof that supplies the same
responses. The exact retained vendor-kernel ELF now supplies positive Linux-
side evidence for the contract: user 1 is routed to
`cspm_pause_pcm_running(PAUSE_I2CDRV)`, with three SW_PAUSE bit-13 writes,
three FW_DONE bit-15 polls, the 2 ms bound, and paired release around the
I2C transaction. This confirms the historical caller contract but not the
external firmware receiver owner. The public hybrid source now supplies a
positive historical owner path, but the exact PCM variant, image redistribution
boundary, and a robust mainline adapter remain open; see the
[public hybrid owner source](results/public-hybrid-owner-source-20260806.txt).
The bounded SCP disassembly narrowed likely local aliases to DMA
remap, interrupt, clock, and generic SPM/DVFS paths; it did not identify the
`SEMA_I2C_DRV` owner or a pause/release implementation. See the
[vendor-kernel contract](results/vendor-kernel-sema-contract-20260806.txt) and the
[SCP disassembly result](../2026-08-06-da921x-page-owner-audit/results/scp-owner-disassembly-20260806.txt).
The retained TEE disassembly separately identifies only keyed CSPM control and
secure-semaphore `+0x448` ownership, with no direct PCM restart or
`SW_RSV`/`FW_DONE` lease path; see the
[TEE owner result](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt).
The SCP literal-pool inventory similarly classifies the remaining local
`0x400a…`, `0xa000…`, and NVIC paths without identifying a pause/release owner;
the computed/secure-alias residual remains explicit in the
[SCP alias result](../2026-08-06-da921x-page-owner-audit/results/scp-alias-inventory-20260806.txt).
The observer and vendor ELF also match the receiver register window and exact
pause/status offsets, but no pause/FW_DONE handshake was exercised; see the
[register identity reconciliation](results/receiver-register-identity-20260806.txt).
Until then the DA921x provider remains fail-closed and the Candidate AO/AN
stopped-state or clock-normalization boot must not be repeated.

The PCM start contract is now explicit in
[`PCM_START_CONTRACT.md`](PCM_START_CONTRACT.md). It makes image identity,
CSPM/CSRAM residency, the authoritative OPP/frequency/voltage/VSRAM startup
state, reset/IM/PCM kick order, CSRAM initialization, runtime lease responses,
and fault/resume invalidation prerequisites for registering the callback. The
current mainline handoff has no MT6797 startup-state owner, so this result
advances the design boundary only and does not authorize a loader, firmware
copy, provider write, build, or device boot. See the
[startup-state boundary result](results/public-owner-startup-state-20260806.txt).

The owner-source review itself was validated on Buildbox at pushed commit
`5aced75e948be894fda47ef59a9b41434f02589b` with the dedicated
`a72-p32-rollback` profile; all 180 patches and 119 DTBs passed package
checksums. This is still compile-only evidence: no PCM image was loaded, no
callback was registered, and no device action occurred. See the
[Buildbox result](results/public-owner-buildbox-validation-20260806.txt).

The dormant state-owner contract was then rebuilt on Buildbox at exact pushed
commit `e537c2c3b955a02aa26ffb086f410311426b482d` after correcting a C tag
namespace collision. All 192 patch files applied, the full profile compiled,
119 DTBs and package checksums passed, and the validated package was fetched
locally. This remains compile-only evidence: the state owner is unregistered,
the PCM image/start path is absent, and no provider or device action occurred.
See the [state-owner Buildbox result](results/state-owner-contract-buildbox-20260806.txt).

The next adapter boundary is now explicit in
[`PCM_ADAPTER_DESIGN.md`](PCM_ADAPTER_DESIGN.md). Its deterministic model
requires exact image identity and residency, a complete startup-state
generation, exact CSPM/CSRAM and clock/semaphore ownership, ordered reset and
PCM-start acknowledgements, and generation-bound lease registration. It rejects
premature callbacks and stale state or owner handles, and invalidates on
suspend/resume. See the [adapter model result](results/pcm-adapter-model-20260806.txt).

Patch `0193` now pins the startup-state generation across the future
multi-step start sequence with an exact transition-hold token; it remains
dormant and unregistered until a real protected owner exists.

The exact pushed commit `9ba17484c9312798fdfa7115ec2460664c94200e` now passes
the full 182-entry Buildbox series and package checks, with the validated
package fetched locally. This is compile-only evidence for patch `0193`; it
does not establish a protected owner, PCM image/start path, provider vote, or
device action. See the [transition-hold Buildbox result](results/state-owner-transition-hold-buildbox-20260806.txt).

A bounded read-only Buildbox inventory confirms the missing implementation seam:
the current tree has generic MT6797 topckgen/apmixedsys providers but no
MT6797 cpufreq driver, protected MCUMIXED/DVFSP clock owner, or BigiDVFS secure
backend. The existing A72 observer reads Vproc/MCUCFG state and denies CPU_ON;
it is not a startup-state owner. See the [clock/state-owner inventory](results/mainline-clock-owner-inventory-20260806.txt).

Patch `0194` now provides the bounded, default-off PCM admission shell around
that contract. The exact pushed commit `e1c88a6` applied all 183 series entries
on Buildbox, compiled the full arm64 profile, produced 119 DTBs, passed package
checksums, and fetched the validated package locally. This is compile-only
evidence: no adapter is registered, no provider or MMIO path is enabled, and
the device was not touched. See the [PCM admission shell Buildbox result](results/pcm-adapter-shell-buildbox-20260806.txt).

The next discriminator remains the real protected MCUMIXED/DVFSP and BigiDVFS
startup-state owner. Only after that owner is independently reviewed can the
external callbacks be bound and the PCM image/residency/start and runtime
lease path be tested.

Patch `0195` now adds an exact, default-off identity gate for that owner. The
pushed commit `5e94f04` applied all 184 series entries on Buildbox, compiled
the full profile, produced 119 DTBs, passed package checksums, and fetched the
validated package locally. It requires the MCUMIXED/DVFSP CPU-PLL backend and
the separate BigiDVFS secure backend, with the complete resource mask and a
nonzero owner handle; the owner remains unregistered and no provider or MMIO
path is enabled. See the [protected identity Buildbox result](results/state-owner-identity-buildbox-20260806.txt).

The next real gate is still a reviewed implementation of the protected
MCUMIXED/DVFSP and BigiDVFS startup-state owner. Only after that owner is
independently reviewed can callbacks be bound and the PCM
image/residency/start and runtime lease path be tested.

Patch `0196` now adds the bounded composition seam for those two protected
domains. It validates exact backend descriptors, disjoint LL/L/CCI and B
cluster masks, complete state fields, matching generations, and one owner
handle; paired transition holds roll back and invalidate both sides on a
failure. The exact pushed commit `06f0a87` applied all 185 series entries on
Buildbox, compiled the full profile, produced 119 DTBs, passed package
checksums, and fetched the validated package locally. This remains
compile-only evidence: neither backend is implemented or registered, and no
provider, MMIO, secure call, firmware action, or device boot is enabled. See
the [protected composition Buildbox result](results/protected-state-backend-composition-buildbox-20260806.txt).

The next gate is still the independently reviewed hardware implementation of
the MCUMIXED/DVFSP CPU-PLL owner and BigiDVFS secure owner, including their
authoritative OPP/frequency/voltage/VSRAM state and transition locks.

Patch `0197` now adds the smallest compile-only MCUMIXED/CSPM clock readback
transport. Its Device Tree node is disabled, its profile leaves
`CONFIG_MTK_INFRACFG` disabled, and the helper performs only a bounded
semaphore acquire/read/release sequence for raw LL/L/CCI clock-window words.
The exact pushed commit `2c9d1b9` applied all 186 series entries on Buildbox,
compiled the dedicated arm64 profile, produced 119 DTBs, passed package
checksums, and fetched the validated package locally. No owner or clock
provider is registered, no secure or firmware call is made, and no device
action occurred. See the [protected clock readback Buildbox result](results/protected-clock-readback-buildbox-20260806.txt).
This transport identifies and bounds the protected read path; it does not
provide calibrated OPP/rail state or unlock CPU8/CPU9.

The combined `dvfsp-protected-readback` profile now builds both protected
readback transports at pushed commit `43b596a`. Patch `0198` uses only the
documented `0xc200035f` secure REG_READ service and the four whitelisted
BigiDVFS addresses; it does not call the unvalidated getter FIDs or any secure
write. Buildbox applied all 187 series entries, produced 119 DTBs, passed
package checksums, and fetched the validated package. Both nodes remain
disabled, so this is still compile-only evidence and not CPU8/CPU9 support.
See the [combined protected-readback Buildbox result](results/protected-readback-buildbox-20260806.txt).

The clean pushed follow-up revision `6c3cb4f` was rebuilt on Buildbox after the
resume request. It reproduced the same validated artifact and byte-identical
kernel, DTB, and map outputs; the repeat run also performed no device action
and does not change the CPU8/CPU9 gate.

The read-only protocol revalidation now closes the public identifiers needed
to implement those adapters: the BigiDVFS secure FIDs and secure register
offsets, and the MCUMIXED/DVFSP semaphore's exact acquire/release sequence,
2 ms bound, IRQ/spinlock serialization, and shared kernel/SPM/ATF ownership.
It also records why this is not yet an owner: the target firmware response and
variant remain unvalidated, the authoritative OPP/rail/cluster-state contract
is absent, and the historical fatal timeout paths need bounded mainline
rollback. The next implementation gate is therefore a default-off,
read-only protocol adapter with explicit state and transition-lock proof; no
writable provider or CPU8/CPU9 admission is permitted until that proof exists.

The public DVFS owner audit now supplies the missing historical state shape:
`__set_cpuhvfs_init_sta()` samples OPP, physical frequency, Vproc, VSRAM,
ceiling/floor limits, and cluster membership under the vendor `cpufreq_mutex`
before the PCM kick. It also proves that the tables are selected and mutated
from efuse, EEM/PTP, and PPM state, so copying a static OPP table would be an
incorrect substitute. Mainline still has no equivalent cpufreq/calibration/
rail owner; the next implementation task is to design that owner boundary and
then bind the protected backends under one lock.

Patch `0199` now closes the next contract gap: the CPU-PLL and BigiDVFS
snapshots, protected owner identity, and every paired transition hold must
echo one nonzero opaque transition-owner handle as well as the generation and
owner handle. The exact pushed commit `8f0aadf` applied all 188 series entries
on Buildbox, produced 119 DTBs, passed package checksums, and fetched the
validated package. This remains compile-only evidence: the handle is a binding
contract, not an implementation of the historical `cpufreq_mutex`; both
backends remain default-off, with no provider, secure write, firmware action,
or device boot. See the [protected transition-owner Buildbox result](results/protected-transition-owner-buildbox-20260806.txt).

The remaining gate is the real, independently reviewed calibrated state owner
and transition-lock implementation, including clock/rail arbitration,
suspend/fault invalidation, and runtime identity evidence. CPU8/CPU9 admission
and all hardware writes remain blocked until that gate is met.

Patch `0200` now makes the calibration boundary fail closed. The protected
owner identity and both backend snapshots must identify the complete historical
source set—efuse variant, EEM/PTP mutation, PPM limits, live VPROC/VSRAM, and
clock/rail owners—plus a mutable-table epoch and nonzero calibration handle;
the two backends must echo identical provenance. The exact pushed revision
`4cecc04` applied all 189 series entries on Buildbox, produced 119 DTBs,
passed package checksums, and fetched the validated package. Its dormant
contract leaves both backends unregistered, so the packaged Image, Image.gz,
System.map, and Gemini DTB remain byte-identical to the earlier dormant
profile. This is not hardware support or CPU8/CPU9 evidence. See the
[calibrated-state provenance Buildbox result](results/calibrated-state-provenance-buildbox-20260806.txt).
The current-head docs-only resume at `6883aff` rebuilt the same named profile
and fetched its validated package; see the [resume receipt](results/calibrated-state-provenance-buildbox-resume-20260806.txt).

Patch `0201` now binds that provenance to the protected owner's lifecycle. A
future provider must snapshot and validate the complete calibration identity,
hold it for the paired CPU-PLL/BigiDVFS transition, release it, and invalidate
it with the same generation, transition owner, and provenance echoed by both
backends. The exact pushed revision `f984738` applied all 190 series entries
on Buildbox, produced 119 DTBs, passed package checksums, and fetched the
validated package. The owner and provider remain unregistered and default-off;
no calibration provider, firmware action, device boot, or CPU8/CPU9 admission
occurred. See the [calibration lifecycle Buildbox result](results/calibration-lifecycle-buildbox-20260806.txt).
The next gate is still an independently reviewed provider that supplies the
real EEM/PTP/PPM-calibrated state and clock/rail arbitration; this patch only
closes the admission boundary around that future implementation.

Patch `0202` then requires the future clock/rail owner to provide one external
transition lock across composite snapshots, validation, paired holds/releases,
and invalidation; failed CPU-PLL holds roll back the calibration hold. The
exact pushed revision `d85cffe` applied 191 series entries on Buildbox and
passed package checksums; see the
[transition-lock result](results/transition-lock-buildbox-20260806.txt).

Patch `0203` now requires the concrete calibrated-state payload that the
future owner must return while that lock is held: stable MON phase, BIG/L/2L/
CCI EEM/PTP banks, ordered frequency rows with VPROC/VSRAM/PPM values, and
independent thermal, clock-owner, and rail-owner generations. The exact pushed
revision `652d164` applied all 192 series entries, produced 119 DTBs, passed
package checksums, and fetched the validated package. This remains
compile-only admission evidence: the owner/provider are unregistered and
default-off, with no EEM/thermal or PMIC/clock access, firmware action, device
boot, or CPU8/CPU9 admission. See the
[calibrated table-state result](results/calibrated-table-state-buildbox-20260806.txt).

Patch `0204` now adds the first source-backed EEM/PTP readback seam through the
existing MT6797 thermal resource owner. It serializes PTPCORESEL bank selection
under the thermal lock, reads raw status and the documented frequency/VOP
anchors for BIG/L/2L/CCI, and restores the exact selector word. Revision
`20ad8b6` applied all 193 series entries, compiled the thermal object and full
arm64 kernel on Buildbox, produced 119 DTBs, passed package checksums, and
fetched the validated package. This is still compile-only: the thermal node is
disabled, no provider is registered, no EEM phase or calibrated VPROC/VSRAM/PPM
table is synthesized, and no rail, clock, secure-firmware, device, or CPU8/CPU9
action occurred. See the [EEM readback Buildbox result](results/eem-readback-buildbox-20260806.txt).

Patch `0205` adds the source-backed, read-only conversion boundary from that
locked readback into the calibrated-state contract. It requires caller-owned
silicon-selected frequency/PPM rows, recorded VPROC caps, live VSRAM, voltage
limits, temperature, owner generations, and complete provenance; it matches
the eight anchors, applies the BIG versus normal EEM units, interpolates all
sixteen rows, applies the low-temperature offset and caps, and validates the
VSRAM delta. Revision `df2c410` applied all 194 series entries on Buildbox,
compiled the full arm64 kernel without warnings from the new helper, produced
119 DTBs, passed package checksums, and fetched the validated package. This is
still compile-only: the thermal node and provider remain default-off, no EEM
phase or hardware write occurred, and CPU8/CPU9 admission remains closed. See
the [calibration-builder Buildbox result](results/eem-calibration-builder-buildbox-20260806.txt).

Patch `0206` adds the source-backed, read-only decoder over the existing
protected LL/L/CCI and BigiDVFS clock samples. It preserves generation tags and
raw mux/divider selectors, rejects malformed or in-flight PLL samples, and
applies the recovered 26 MHz PCW/POSDIV and ARMPLLDIV_CKDIV formulas to derive
LL, L, B, and CCI frequencies. Revision `4d5d8da` applied all 195 series
entries on Buildbox, compiled the full arm64 kernel, produced 119 DTBs, passed
package checksums, and fetched the validated package. This remains a pure
conversion boundary: no clock or rail owner, provider, secure call, hardware
write, firmware action, device boot, or CPU8/CPU9 admission is enabled. See the
[clock-state decoder Buildbox result](results/clock-state-decoder-buildbox-20260806.txt).

Patch `0207` now binds the vendor-identified CPU and PM transition events plus
clock, rail, and PCM-fault events to the existing state-owner invalidation
reasons through a default-off monotonic event ledger. It rejects replayed or
non-monotonic sequence/generation events without registering notifiers or
touching hardware. Revision `870dcc1` applied all 196 series entries on
Buildbox, compiled the full arm64 kernel, produced 119 DTBs, passed package
checksums, and fetched the validated package. This is compile-only evidence:
the state owner and provider remain unregistered, and no secure call, firmware
action, device boot, or CPU8/CPU9 admission occurred. See the [runtime
invalidation Buildbox result](results/runtime-invalidation-buildbox-20260806.txt).

Patch `0208` now connects that ledger to the real Linux 7.1.3 lifecycle APIs:
the CPU-hotplug state machine supplies online/down-prepare/down-failed events,
and the PM notifier chain supplies suspend/resume events. Registration requires
an active state owner, arms only after both hooks succeed, serializes the
generation-tagged source callback with the ledger, and disarms before removing
the hooks. Revision `44f617d` applied all 197 series entries on Buildbox,
compiled the full arm64 kernel, produced 119 DTBs, passed package checksums,
and fetched the validated package. No caller registers the binding, so this is
still compile-only evidence with no provider, hardware, firmware, device, or
CPU8/CPU9 action. See the [runtime notifier binding Buildbox
result](results/runtime-binding-buildbox-20260806.txt).

Patch `0209` adds the missing source-to-owner conversion boundary. It assembles
the decoded protected-clock state, the calibrated MON/EEM table state, and the
future owner's live OPP, voltage, VSRAM, membership, ceiling/floor, clock, and
rail fields into the existing complete four-cluster startup snapshot. The
assembler rejects incomplete, guessed, stale, or mismatched inputs: every
current frequency must match the decoded clock and a calibrated table row, and
the provenance, generation, and all bank/phase requirements must agree. The
exact pushed revision `7b59354` applied all 198 series entries on Buildbox,
produced 119 DTBs, passed package checksums, and fetched the validated package;
see the [state-snapshot Buildbox result](results/state-snapshot-buildbox-20260806.txt).
This remains compile-only conversion evidence: the owner/provider are still
unregistered and default-off, and there was no hardware, firmware, device,
CPU8, or CPU9 action. The assembler closes the conversion gap but is not an
owner and cannot authorize a transition.

Patch `0210` now provides one callback-only source adapter for the future
owner. While that owner holds its transition lock, the adapter orders protected
clock readback, BigiDVFS readback, EEM readback and calibration construction,
then collects live fields and invokes the four-cluster assembler. Missing
sources or any conversion failure abort without publishing a snapshot. The
exact pushed revision `8b7434c` applied all 199 series entries on Buildbox,
produced 119 DTBs, passed package checksums, and fetched the validated package;
see the [state-source adapter Buildbox result](results/state-source-adapter-buildbox-20260809.txt).
This narrows the integration seam but still does not implement the owner:
callbacks remain external, registration is absent, and there was no hardware,
firmware, device, CPU8, or CPU9 action.

Patch `0211` now wires the existing clock, BigiDVFS, and thermal EEM readback
transports into that source adapter through a caller-owned device tuple. The
bridge fails closed for an incomplete tuple or disabled backend configuration,
retains no device references, and initializes only the three raw-read
callbacks; calibration-table and live-state callbacks remain mandatory inputs
from the eventual owner. Revision `e962efb` applied all 200 series entries on
Buildbox, produced 119 DTBs, passed package checksums, and fetched the
validated package; see the [source-backend bridge Buildbox result](results/state-source-backend-bridge-buildbox-20260809.txt).
This is still compile-only: no owner/provider registration, platform driver,
direct MMIO, secure write, firmware action, device boot, or CPU8/CPU9 admission
occurred. The remaining gate is the real calibrated EEM/PTP/PPM and PMIC/clock
owner that supplies calibration and live state while arbitrating transitions
and generation invalidation.

The clean pushed head `75aa3e0` was then rebuilt on Buildbox to resume the
workflow after the documentation update. It applied the same 200-entry series,
reproduced the package hashes, passed the 119-DTB checksum validation, and
fetched only the validated package; see the [Buildbox rerun result](results/state-source-backend-bridge-buildbox-rerun-20260809.txt).
This rerun changes no hardware or support status and does not advance the
owner/provider or CPU8/CPU9 gate.

The documentation head 85f3fb6 was subsequently rebuilt on Buildbox through
the same explicit profile. It again applied all 200 series entries, produced
119 DTBs, passed package checksums, and fetched only the validated package;
see the [Buildbox resume result](results/state-source-backend-bridge-buildbox-resume-20260809.txt).
This is reproducibility evidence only and does not change the owner/provider
or CPU8/CPU9 gate.

Patch `0213` adds the next source-backed conversion seam. It decodes the exact
public MT6797 `M_HW_RES1`, `M_HW_RES7`, and `M_HW_RES9` bitfields into explicit
BIG/L/2L/CCI INIT/MON, DVFS-level, and bin-selection state, and fails closed
unless all four detector banks are enabled. It also makes the efuse-variant
identity mandatory in the existing calibration provenance checks. The decoder
is pure and remains callback-only: no provider registration, MMIO, secure
operation, firmware action, device boot, or CPU8/CPU9 admission is included.
Revision `e335ba8` applies all 202 canonical entries on Buildbox, compiles the
Gemini DTB and full arm64 image, produces 119 DTBs, passes package checksums,
and fetches only the validated package; see the [PTP state decoder Buildbox
result](results/state-source-ptp-decode-buildbox-20260809.txt). This is still
compile-only: no runtime calibration was read and no hardware, firmware,
device, or CPU8/CPU9 action occurred.

Patch `0214` closes a concrete conversion gap by making the decoded PTP state a
required input to the calibration builder. The builder now validates the
BIG/L/2L/CCI bank identity, INIT/MON enablement, DVFS level, and bin range
before accepting calibration state. Revision `be44cbc` applied all 203
canonical entries on Buildbox, compiled the Gemini DTB and full arm64 image,
produced 119 DTBs, passed package checksums, and fetched only the validated
package; see the [PTP calibration-binding Buildbox result](results/state-source-ptp-calibration-buildbox-20260809.txt).
This is still a pure, default-off seam: no provider registration, runtime
calibration read, hardware, firmware, device, or CPU8/CPU9 action occurred.

Patch `0215` binds the PTP-derived silicon identity, calibration rows, live
state, full provenance, and owner/transition handles under one transition
mutex. Revision `180d5d7` applied 204 canonical series entries on Buildbox,
produced 119 DTBs, passed package checksums, and fetched only the validated
package; see the [calibrated state-owner source Buildbox result](results/state-owner-source-buildbox-20260809.txt).
The seam remains default-off and unregistered: actual efuse/EEM/PMIC/clock
source callbacks and protected owner registration are not yet implemented.

Patch `0216` binds that source to an external clock/rail transition lock and
monotonic generation callback. It rejects a generation change during a full
readback/conversion snapshot and rejects generation rollback, while exposing
only dormant owner callbacks. Revision `0808526` applied 205 canonical series
entries on Buildbox, produced 119 DTBs, passed package checksums, and fetched
only the validated package; see the [transition-generation arbitration
Buildbox result](results/state-owner-arbitration-buildbox-20260809.txt).
This remains compile-only and unregistered; the real efuse/EEM/PMIC/clock
provider and protected owner registration remain open.

Patch `0217` closes the lifecycle gap in that arbitration seam: a generation
read error, zero/rollback, mid-snapshot change, or explicit invalidation now
latches the wrapper fault, invalidates the calibrated source, and rejects reuse
until explicit reinitialization. Revision `29ca791` applied 206 canonical
series entries on Buildbox, produced 119 DTBs, passed package checksums, and
fetched only the validated package; see the [arbitration-fault Buildbox
result](results/state-owner-arbitration-fault-buildbox-20260809.txt). This is
still compile-only and unregistered: no real owner/provider callback, hardware
operation, device boot, or CPU8/CPU9 admission was added.

Patch `0218` adds the explicit opt-in registration and unregistration lifecycle
around the arbitration wrapper. It owns the callback table, binds the
external transition hold/release callbacks, runs the existing protected
identity check before registration, and invalidates the source before
unregistration. Revision `340b9bd` applied 207 canonical series entries on
Buildbox, produced 119 DTBs, passed package checksums, and fetched only the
validated package; see the [state-owner registration Buildbox result](results/state-owner-registration-buildbox-20260809.txt).
The default profile never calls this lifecycle: the provider remains absent,
no hardware or device action occurred, and CPU8/CPU9 admission remains closed.

The clean documentation head `668a62f` was then rebuilt on Buildbox through
the same explicit profile. It reproduced the 207-entry package, all image and
DTB checksums, and fetched only the validated package; see the [Buildbox rerun
receipt](results/state-owner-registration-buildbox-rerun-20260809.txt). This
is compile-only reproducibility evidence and does not change the provider,
hardware, device, or CPU8/CPU9 gate.

Patch `0219` tightens that lifecycle boundary: the existing complete snapshot
and validation callbacks must both succeed before the owner registry is
published, and every failed registration clears the private callback table.
It remains default-off and contains no hardware operation. A real calibrated
EEM/PTP/PPM and PMIC/clock provider is still required.

The corrected patch revision `accd595` applied all 208 canonical entries on
Buildbox, produced 119 DTBs, passed the package checksums, and fetched only the
validated package; see the [0219 Buildbox receipt](results/state-owner-registration-gate-buildbox-20260809.txt).
This confirms patch application and compilation only: the provider is still
absent and CPU8/CPU9 admission remains closed.

The clean follow-up head `4e7c502` was rebuilt on Buildbox with the same
explicit profile. It reproduced the same 208-entry package and checksums, and
fetched only the validated package; see the [Buildbox resume receipt](results/state-owner-registration-gate-buildbox-resume-20260810.txt).
This remains compile-only evidence: the provider is absent, no device action
occurred, and CPU8/CPU9 admission remains closed.

A bounded read-only Gemian resource-owner probe then confirmed that the vendor
`cspm`, `mt-eem`, `mt-ppm`, `mt-cpufreq`, and `mt_idvfs_driver` bindings are
present, while no authoritative generation or transition-lock endpoint is
exported. The existing procfs/debugfs surfaces therefore cannot serve as the
mainline owner; the sanitized result is in the [resource-owner boundary probe](results/live-resource-owner-boundary-probe-20260810.txt).
The next provider must bridge efuse/PTP identity, mutable PPM rows, live
VPROC/VSRAM, and clock/rail generations under one transition lock.

A read-only Gemian probe then confirmed the missing runtime-owner evidence on the
named device: `/proc/eem/eem_dump` exposes the 19-word EEM handoff and each PPM
cluster exposes a 16-entry table, while one-second samples showed the OPP index
and VPROC/VSRAM changing independently of the reported frequency. The reads
were not atomic and the raw EEM/PPM payloads were not retained; see the
[sanitized live-source probe](results/live-dvfs-owner-source-probe-20260809.txt).
This makes the next implementation requirement concrete: a real owner must
hold the transition lock and publish one generation-tagged frequency,
VPROC/VSRAM, PPM/membership, and EEM/PTP state snapshot.

The next gate is still the real MT6797 EEM/PTP/thermal and PMIC/clock provider
that supplies those inputs from efuse and live hardware, arbitrates the shared
EEM/thermal resource, and independently proves clock/rail transition locking
and runtime invalidation. The decoder, event ledger, notifier binding, and
registration bridge now provide deterministic conversion and lifecycle
boundaries, but none is an owner and none can authorize a transition without
the real callbacks. The protected owner still needs real EEM/PTP/rail state,
transition-lock integration, generation-producing callbacks, and runtime
proof; until then, the owner/provider and CPU8/CPU9 admission remain closed.

Patch `0220` raises the locked EEM readback ABI to carry the calibrated thermal
zone maximum collected while the existing thermal-driver lock is held. The
calibration builder must consume that exact readback temperature and the
selector is restored before returning. Revision `109aaf3` applied all 209
canonical entries on Buildbox, produced 119 DTBs, passed package checksums, and
fetched only the validated package; see the [EEM temperature readback Buildbox
result](results/eem-temperature-readback-buildbox-20260810.txt). This is a
compile-only provider prerequisite: no EEM/PTP/PPM or PMIC/clock provider,
generation callback, hardware operation, device boot, or CPU8/CPU9 admission
was added.

Patch `0221` extends the disabled clock readback through the vendor-mapped CSPM
hardware-semaphore transaction. It captures the three physical-cluster limit
words and four current-state words, then decodes the vendor OPP reversal,
pause/enable flags, and raw VPROC/VSRAM codes without inventing voltage units;
the CCI current word is retained but has no physical limit word. Revision
`4fada45` applied all 210 canonical series entries on Buildbox, produced 119
DTBs, passed package checksums, and fetched only the validated package; see the
[CSPM live-state readback Buildbox result](results/cspm-live-state-readback-buildbox-20260810.txt).
This remains a compile-only source prerequisite: no PPM rows, real rail/clock
generation, provider registration, hardware operation, device boot, or CPU8/CPU9
admission was added.

Patch `0222` adds a strict, disabled MT6797 PPM snapshot contract. It captures
the vendor's three physical clusters (LL/L/B), their exact 16-entry frequency
tables, current client limits, and advice fields, and validates the vendor
index ordering and cluster shape. Current limit conversion is explicit
(`min_cpufreq_idx` is the floor and `max_cpufreq_idx` is the ceiling); a caller
must hold the vendor private PPM lock and provide a nonzero table epoch. The
contract deliberately supplies no CCI limit, per-row PPM limit source, provider
registration, or hardware action. Revision `028c460` applied all 211 canonical
entries on Buildbox, produced 119 DTBs, passed package checksums, and fetched
only the validated package; see the [PPM snapshot contract Buildbox result](results/ppm-snapshot-contract-buildbox-20260810.txt).
This is compile-only evidence: the real PPM/EEM/PTP and PMIC/clock owner,
generation source, device boot, and CPU8/CPU9 admission remain closed.

Patch `0223` binds the validated PPM snapshot into the protected state-source
pipeline. The source now requires a PTP-bound PPM read, matches its nonzero
table epoch to both calibrated and live provenance, verifies each LL/L/B live
frequency against an exact vendor table row, and derives those physical
clusters' floor/ceiling from the current client index interval. CCI remains
without a fabricated PPM limit. The first pushed revision `dd89fbc` was
rejected before compilation by one whitespace-only patch-context mismatch;
corrected revision `7c4bd43` applied all 212 canonical entries on Buildbox,
produced 119 DTBs, passed package checksums, and fetched only the validated
package; see the [PPM state-source binding Buildbox result](results/ppm-state-source-binding-buildbox-20260810.txt).
This remains compile-only and default-off: the real external PPM/EEM/PTP and
PMIC/clock owner, generation callbacks, device boot, and CPU8/CPU9 admission
remain closed.

The clean pushed documentation commit `3f07c40` was then rebuilt on Buildbox;
it reproduced the same content-addressed package and passed the same 119-DTB
and package checks. The receipt records both Buildbox job identities.

Patch `0224` now requires the exact three physical PPM frequency tables to
match the EEM-derived calibration rows. PPM rows are descending while the
calibration state is ascending, so validation compares `table[15 - row]` with
`frequency[row]`; CCI remains excluded because no vendor CCI PPM table is
available. Clean revision `04e7ad0` applied all 213 canonical entries on
Buildbox, produced 119 DTBs, passed package checksums, and fetched only the
validated package; see the [PPM/EEM table-identity Buildbox result](results/ppm-eem-table-identity-buildbox-20260810.txt).
This is compile-only and default-off: no real provider, generation callback,
hardware operation, device boot, or CPU8/CPU9 admission was added.

Patch `0225` binds the exact validated PPM snapshot into the EEM calibration
builder. Calibration now receives the PPM snapshot directly, requires its
nonzero table epoch to match the calibration provenance, and checks the
descending PPM B/L/LL rows against the ascending EEM BIG/L/2L rows before
constructing calibration state. CCI remains excluded because no vendor CCI PPM
table is available; per-row PPM limits remain provider-owned and are not
invented here. Clean revision `47339d7` applied all 214 canonical entries on
Buildbox, produced 119 DTBs, passed package checksums, and fetched only the
validated package; see the [PPM calibration binding Buildbox result](results/ppm-calibration-binding-buildbox-20260810.txt).
This is compile-only and default-off: the real EEM/PTP/PPM and PMIC/clock
provider, generation callbacks, device boot, and CPU8/CPU9 admission remain
closed.

Patch `0226` tightens the protected snapshot assembler at the next coherence
boundary. After the live frequency selects an exact calibrated row, live
VPROC and VSRAM must equal that row's calibrated rail pair; a mixed-frequency
rail sample is rejected. This directly closes the incoherent condition seen in
the read-only Gemian source probe, while still leaving generation production,
the PMIC/clock owner, and PPM policy ownership to the real provider. Clean
revision `26341a4` applied all 215 canonical entries on Buildbox, produced 119
DTBs, passed package checksums, and fetched only the validated package; see the
[live-rail coherence Buildbox result](results/live-rail-coherence-buildbox-20260810.txt).
This is compile-only and default-off: no provider registration, hardware
operation, device boot, or CPU8/CPU9 admission was added.

Patch `0227` closes the next source-contract gap by adding a provider-owned
PPM policy snapshot for all four EEM banks (BIG/L/2L/CCI). Calibration now
requires exact frequency and per-row limit matches, including a real CCI row
set, under one table epoch; no CCI or limit value is inferred from the
three-cluster vendor snapshot. The state-source ABI is bumped and the owner
wrapper now receives both the PPM snapshot and policy object explicitly. The
first revision `83880fb` was rejected before compilation by a thermal patch
context mismatch; `0789c30` corrected its indentation, and final revision
`31edbb9` corrected the hunk count and applied all 216 canonical entries on
Buildbox. It produced 119 DTBs, passed package checksums, and fetched only the
validated package; see the [PPM policy binding Buildbox result](results/ppm-policy-binding-buildbox-20260810.txt).
This remains compile-only and default-off: no provider registration, hardware
operation, device boot, or CPU8/CPU9 admission was added.

The clean documentation follow-up `d10796f` was rebuilt on Buildbox to resume
the validated pipeline. It reproduced the same content-addressed package,
119-DTB package validation, and checksums; see the [Buildbox resume receipt](results/ppm-policy-binding-buildbox-resume-20260810.txt).
The follow-up changed documentation only and adds no new kernel or hardware
evidence.

Patch `0228` binds calibrated rows and live state to one provider-owned
`source_generation`. The calibration builder publishes it, the owner wrapper
and source adapter require an exact match, and the final snapshot assembler
rejects missing or mismatched epochs. The patch deliberately does not equate
the independent clock and BigiDVFS backend readback counters. Corrected clean
revision `fb6697f` applied all 217 canonical entries on Buildbox, produced 119
DTBs, passed package checksums, and fetched only the validated package; see the
[shared-generation Buildbox receipt](results/generation-coherence-buildbox-20260810.txt).
This remains compile-only and default-off: no real provider, hardware
operation, device boot, or CPU8/CPU9 admission was added.

A source-only audit of the current managed vendor checkout (`HEAD`
`8cfe6596a503612e3332d9c26e292a19525a7f07`) now fixes the historical owner
boundary that the mainline provider must cross. PPM policy is protected by
`ppm_main_info.lock` and exposes three 16-entry physical-cluster tables plus
client limits; CCI uses a separate `cpu_dvfs[MT_CPU_DVFS_CCI]` table. CSPM/PLL
state uses the independent `dvfs_lock`, while EEM/PTP use separate locks.
The vendor structs contain no shared generation and no single transition lock.
The exact source hashes and field-level summary are in the
[vendor PPM owner-boundary result](results/vendor-ppm-owner-boundary-20260810.txt).
No vendor code was copied and no hardware or device action occurred. The next
implementation therefore has to introduce one mainline owner lock and
generation while bridging the real PPM/CCI rows, EEM/PTP identity, live
VPROC/VSRAM, and clock state; the provider and CPU8/CPU9 admission remain
closed until that bridge is backed by named runtime evidence.

Patch `0229` closes the next ownership boundary by requiring the dormant state
owner to use an explicit PPM owner with lock, unlock, and snapshot operations.
The PPM owner must copy the three-cluster snapshot and all four provider-owned
policy banks under its lock; the owner then validates one shared table epoch and
preserves the exact policy copy into calibration. The documented lock order is
the outer transition lock first, then the PPM owner lock. Clean revision
`692a6a5` applied all 218 canonical entries on Buildbox, produced 119 DTBs,
passed package checksums, and fetched only the validated package; see the
[PPM owner-lock Buildbox result](results/ppm-owner-lock-buildbox-20260810.txt).
This remains compile-only and default-off: no real provider, hardware
operation, device boot, or CPU8/CPU9 admission was added.

Patch `0230` adds the first concrete resource-only owner lifecycle. It retains
the four backend device references across explicit attach/detach, waits for
active transition holds before detach, and exposes one transition mutex plus a
monotonic generation through the arbitration-ops adapter. It has no DT match,
consumer binding, hardware access, write path, handoff registration, or CPU
admission; writes are permanently disabled in this lifecycle. Clean revision
`d506e28` applied all 219 canonical entries on Buildbox, produced 119 DTBs,
passed package checksums, and fetched only the validated package; see the
[resource-owner Buildbox result](results/resource-owner-buildbox-20260810.txt).
This is a compile-only resource boundary, not hardware support: the real
provider still must supply PPM/CCI rows, EEM/PTP identity, live VPROC/VSRAM,
and clock/rail callbacks before any state-owner registration or CPU8/CPU9
admission.

Patch `0231` adds a platform provider for the resource-only owner lifecycle. It
resolves the four backend phandles, retains the references through explicit
bind/unbind, and keeps the node disabled by default. The provider contains no
MMIO, secure, firmware, clock, rail, readback, registration, or CPU action.
The named `dvfsp-resource-owner-readonly` profile also compiles the disabled
clock, BigiDVFS, and EEM transport fragments so the owner source links
completely; this is build completeness only, not runtime support.

The first profile compile exposed two malformed ABI declarations from `0229`;
patch `0232` restores the PPM-owner header and owner/transition handles in the
snapshot ABI. The next compile exposed malformed historical source boundaries:
`0233` repairs the handoff helper's lost return/export and the calibration
cluster type, while `0234` restores state-owner mutex initialization to probe
setup and removes its duplicate tail. These repairs are canonical build
hygiene, not new hardware evidence.

Clean revision `3b18307e42cb0ce6daefd26cec2790bed570a5b5` then passed the named
Buildbox profile and package validation: 223 patches, six config fragments,
119 DTBs, image/package checksums, and a validated package fetched locally.
See the [resource-owner provider Buildbox receipt](results/resource-owner-provider-buildbox-20260810.txt).
This remains compile-only evidence: the DT node and backend resources remain
disabled, the owner is unregistered, no hardware action occurred, and CPU8/CPU9
admission remains closed. The real calibrated provider still must supply
efuse/PTP identity, coherent PPM/CCI rows, live VPROC/VSRAM, and
clock/rail generation plus a single transition lock before any provider
registration or CPU8/CPU9 experiment.

Patch `0235` binds this source contract to the resource owner's lifetime. It
requires the explicit efuse/PTP identity, PPM snapshot/policy, calibration,
live-state, invalidation, and PPM lock callbacks; composes the existing source
and generation-arbitration layers; and prevents resource detach while the
calibrated source borrows its four devices. Exit invalidates the source before
unbinding it. The binding only exposes snapshot, validation, identity, and
dormant owner-callback helpers; it does not register the handoff owner or add a
platform consumer.

The first clean submission stopped before compilation on a Makefile context
mismatch; the narrowed patch was pushed at `a28dd0f`. That revision then passed
the named Buildbox profile and package validation: 224 patches, six config
fragments, 119 DTBs, image/package checksums, and a validated package fetched
locally. See the [calibrated-provider Buildbox receipt](results/calibrated-provider-buildbox-20260810.txt).
This remains compile-only evidence: all required source callbacks are still
external, registration is absent, no hardware action occurred, and CPU8/CPU9
admission remains closed. The next implementation must provide the actual
efuse/PTP identity, coherent PPM/CCI rows and limits, live VPROC/VSRAM, and
clock/rail generation callbacks under the introduced transition lock.

Patch `0236` now threads the semaphore-protected CSPM live-state decoder into
the source callback. The provider must consume the decoded raw OPP, limit, and
rail-code sample and echo its backend-local `cspm_sample_generation`; that
sample epoch is deliberately kept distinct from the provider-owned transition
`source_generation`. A missing or mismatched echo fails closed before snapshot
publication. The clean `0044311` revision applied all 225 canonical entries on
Buildbox, produced 119 DTBs, passed package checksums, and fetched only the
validated package; see the [CSPM live-binding Buildbox receipt](results/cspm-live-binding-buildbox-20260810.txt).
This remains compile-only and default-off: no provider registration, hardware
write, device action, runtime evidence, or CPU8/CPU9 admission was added.

Patch `0237` adds a read-only MT6797 efuse/PTP identity cell and pure CSPM
VPROC/VSRAM code-to-microvolt conversion helpers. Buildbox validated revision
`85e96f7` with 226 patches and 119 DTBs; no efuse read, rail write, provider
registration, device action, or CPU8/CPU9 admission occurred. Patch `0238`
binds that identity source to the dormant owner-source seam and requires
explicit table-epoch and calibration-handle callbacks. Revision `6ffe283`
validated 227 patches with the same default-off boundary.

Patch `0239` adds the read-only PPM/CCI source adapter: it requires the vendor
three-cluster rows, separate CCI table, four policy-limit banks, and one table
epoch under the external PPM lock. Revision `51b3f30` validated 228 patches.
Patch `0240` adds the live clock/rail source adapter with exact frequency,
calibrated-row, CSPM-rail, owner-handle, transition-handle, and generation
checks. Revision `84cfb27` validated 229 patches. Both remain dormant and
compile-only.

Patch `0241` composes the identity, live-state, and PPM/CCI adapters inside the
calibrated provider without registration. Patch `0242` validates policy-derived
CCI bounds against the calibrated row and provider-owned PPM ceiling. Patch
`0243` routes validated generation-tagged lifecycle events through the provider
invalidator without registering CPU-hotplug or PM notifier hooks. The first
`eedafc7` submission stopped during 0243 patch application; corrected revision
`da7cad7` validated all 232 patches on Buildbox, produced the arm64 image and
119 DTBs, passed checksums, and fetched only the validated package. See the
[source/runtime gates receipt](results/source-runtime-gates-buildbox-20260810.txt).

A new named-device, read-only Gemian probe confirms `/proc/eem`, the three PPM
tables, cpufreq frequency/voltage/OPP endpoints, and the clock debug tree are
available, but finds no authoritative generation, transition-lock, or owner
surface beyond generic `mt-cpufreq` and `mt-ppm` nodes. Raw payloads were not
retained; only bounded metadata and hashes are recorded in the [runtime owner
boundary v2 receipt](results/runtime-owner-boundary-v2-20260810.txt). The next
implementation must introduce one dedicated generation/transition-lock owner
that can prove coherent source snapshots before provider registration or any
CPU8/CPU9 action is reconsidered.

A three-sample, one-second read-only hash repeat then observed frequency,
voltage, and OPP changes while the PPM and EEM hashes remained stable. This
confirms mutable live state but does not establish an atomic snapshot or a
hardware-support claim. The bounded result is recorded in the [live hash repeat
receipt](results/runtime-owner-live-hash-repeat-20260810.txt); the required
contract remains one transition lock, before/after generation, and live
frequency/VPROC/VSRAM/PPM membership from one owner. No provider was registered,
no hardware action occurred, and CPU8/CPU9 admission remains closed.

The pushed head was also rebuilt with the explicit `full` Buildbox profile:
all 232 canonical patches applied, the arm64 Image/Gemini DTB and 119 total
DTBs passed checksums, and only the validated package was fetched. The exact
receipt is [recorded here](results/source-runtime-gates-buildbox-full-20260810.txt).
This rerun changes no runtime or hardware boundary; the owner/provider remain
dormant and CPU8/CPU9 admission remains closed.
