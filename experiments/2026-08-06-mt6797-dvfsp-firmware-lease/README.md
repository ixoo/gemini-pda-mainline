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
