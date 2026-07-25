# MT6797 Cortex-A72 firmware/power implementation prerequisites

Date: 2026-07-22

Scope: named Gemini PDA, exact active Gemian `3.18.41+ #7` boot artifacts,
public vendor-source equivalents, and the privately retained 2019
secure-firmware payload identified below.

Decision: draft patch 0093 is not implementation-ready and must remain
unselected.

## 1. What is established

The working design has three distinct owners:

| Resource or transition | Owner established by evidence | First mainline provider action |
| --- | --- | --- |
| DA9214 BUCKB (`vproc-big`) enable and fixed inherited voltage | Linux before PSCI | Use the regulator framework; capture enable/voltage first, enable once per cluster, wait 1 ms, and verify readback. Do not program an arbitrary voltage. |
| TOPRGU PWRAP SPI controller reset, WDT `SWSYSRST` bit 11 | Linux temporarily around DA9214/SPM preparation | Use the reset controller's locked, keyed RMW. Assert before BUCKB/isolation work; deassert before the first 240-us delay. Verify both transitions. |
| SPM `MP2_CPUSYS_PWR_CON` at `0x10006218`, bit 0 | Shared boundary; vendor Linux releases reset before PSCI and ATF owns the rest of MP2 power-up | Preserve all other bits and set only `MP2_CPUTOP_PWR_RST_B`. Do not implement the remaining MTCMOS sequence in Linux. |
| SPM `CPU_EXT_BUCK_ISO` at `0x10006290`, bits 1:0 | Linux external preparation | Preserve other bits and clear both `B_EXT_BUCK_ISO` and `L_EXT_BUCK_ISO`, exactly as the working source does. The reason the L bit is included is not yet observed. |
| B-cluster SRAM LDO registers at `0x102222b0`/`0x102222b4` | Secure firmware, requested by Linux | Invoke only the implemented `SRAM_LDO_SET` service after the first 240-us delay; independently read back because its return value is not confirmation. |
| Initial B PLL, B clock mux/divider, cluster-top MTCMOS and internal bus protection | Secure firmware PSCI path | Do not write these from the first Linux provider. Observe them around a working transition. |
| CPU8/CPU9 per-core MTCMOS and reset | Secure firmware PSCI path | Supply standard MPIDR and `secondary_entry` through generic PSCI only. |
| CCI-400 coherency admission | Secure firmware PSCI on-finish path | Do not duplicate it in Linux. Require secondary completion as evidence. |
| MP2 synchronous DCM at `0x10222274`, bits 6:0 | Vendor Linux after `CPU_ON` | Apply the exact two-write toggle only after an accepted and reconciled CPU-on result; read back. |
| CCI PLL/rate | Separate vendor cpufreq/frequency-hopping domain | Observe and leave unchanged in the first CPU8 experiment. |
| Dynamic B iDVFS, OPP/cpufreq, EEM, idle, thermal, HPS/PPM and scheduler policy | Later policy providers | Keep out of the first CPU8 power experiment. They are not proof prerequisites for the accepted first `CPU_ON`, though they are required before normal performance scaling. |

This boundary is stronger than the public Linux sequence alone. Offline analysis
of the retained ATF payload shows that its MP2 PSCI helper performs the initial
B-PLL/mux/divider and cluster MTCMOS work, and that its per-core helper powers
and releases CPU8/9. Linux therefore supplies external rail/isolation
prerequisites and calls PSCI; it does not reproduce secure internals.

## 2. Exact public Linux forward sequence

The sequence is in `arch/arm64/kernel/psci.c`, function
`cpu_power_on_buck()`, lines 505--552 of the pinned tree:

1. Set the vendor software `reset_flags` under `reset_lock`. This only blocks
   its OCP code while external preparation is in progress. Mainline has no OCP
   provider today, but the new power provider must provide a cluster mutex and
   a shared ownership contract for future OCP/iDVFS consumers.
2. Read-modify-write SPM `0x10006000 + 0x218`, setting bit 0 and preserving all
   other bits. The register is `MP2_CPUSYS_PWR_CON`, and bit 0 is the active-low
   `MP2_CPUTOP_PWR_RST_B` release. It is not an A53/"CA7 CPU1" register.
3. Perform one ordering read from `0x10222000 + 0x4a0`, physical
   `0x102224a0`, the B-PLL enable/post-divider register.
4. Assert TOPRGU `PWRAP_SPI_CTL_RST` through `SWSYSRST` bit 11. The vendor WDT
   implementation performs a locked keyed RMW at TOPRGU offset `0x18`, with key
   `0x88000000`; setting the bit asserts reset and clearing it deasserts reset.
5. For a hotplug transition, explicitly select DA9214 page 0 with register
   `0x00[3:0]=0`, set BUCKB enable at `0x5e[0]=1`, and wait 1,000 us. The
   vendor cold-boot bypass path skips this enable and delay; the working Gemian
   capture used later policy hotplug, so the active mainline CPU8 experiment
   must use the hotplug form unless a new observation proves BUCKB was already
   enabled and owned elsewhere.
6. Read-modify-write SPM `0x10006000 + 0x290`, clearing bits 1:0 and preserving
   every other bit. The bits are `B_EXT_BUCK_ISO` and `L_EXT_BUCK_ISO`.
7. Deassert TOPRGU PWRAP reset and clear the vendor `reset_flags` guard.
8. Wait 240 us.
9. Call `BigiDVFSSRAMLDOSet(110000)`, where the argument is millivolts times
   100, i.e. a nominal 1.1 V request.
10. Wait another 240 us.
11. Call standard PSCI `CPU_ON`.

The mainline version must add immediate error checks and readback at every
observable boundary. The vendor DA9214 byte helpers return `unsigned int` even
when they return `-1`; consequently some vendor `< 0` tests are ineffective and
must not be copied. BUCKB voltage register `0xd9[6:0]` uses
`300 mV + code * 10 mV`; capture its inherited value and ownership before any
enable. A fixed 1.0 V assumption is not yet supported by a synchronized
offline-state capture.

The public source contains no complete inverse. `cpu_power_off_buck()` clears
BUCKB enable and calls `BigiDVFSSRAMLDODisable()`, but that function only records
an AEE value and returns zero; its intended hardware write is commented out.
The path does not reassert external isolation, restore MP2 reset, restore PLL or
DCM state, or prove that another consumer no longer needs BUCKB.

## 3. Implemented private SMC ABI

The private `tee1` and `tee2` images are identical 5 MiB backups with SHA-256
`2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
The analyzed payload identifies itself as `v1.0(debug):df3e3f8`, built
`15:46:24, May 17 2019`. No image bytes or disassembly are included here.
The addresses below are analysis virtual addresses from an AArch64 radare2
mapping at `0xff3c0`; they let the findings be reproduced against the private
hash without redistributing the payload.

The SMC dispatcher at analysis address `0x1083b4` has explicit branches for
both the AArch64 `0xc200....` and AArch32 `0x8200....` IDs. It does not normalize
one class into the other. The vendor AArch64 wrapper supplies the function ID in
`x0`, arguments in `x1`--`x3`, executes `smc #0`, and exposes only the signed
low 32 bits of returned `x0`; it discards `x1`--`x3`.

| AArch64 FID | Arguments | Captured handler behavior | Return behavior |
| --- | --- | --- | --- |
| `0xc20003b0` (`BIGIDVFS_ENABLE`) | `x1=idvfs_ctrl`, `x2=current Vproc (mV*100)`, `x3=current Vsram (mV*100)` | Initializes the iDVFS APB, derives the current Vproc code from `x2`, waits 2 us and enables control. This build does not consume `x3`. Handler `0x105eb0`. | Always `0` in this build. |
| `0xc20003b1` (`BIGIDVFS_DISABLE`) | no effective arguments | Runs the dynamic-disable sequence. Handler `0x105ffc`. | Always `0`, including after an internal polling timeout; not completion evidence. |
| `0xc20003b8` (`BIGIDVFS_PLL_SET_FREQ`) | `x1=MHz`, `x2=x3=0` | Programs B-PLL post-divider and PCW, toggles the PCW latch, and waits 20 us after 1-us transition delays. Handler `0x106450`. | Always `0`; ATF itself does not range-check. Public Linux checks 250--3000 MHz. |
| `0xc20003bf` (`BIGIDVFS_SRAM_LDO_SET`) | `x1=mV*100`, `x2=x3=0` | Programs SRAM calibration and selector state at `0x102222b4`/`0x102222b0`. Handler `0x1065dc`. | Always `0`; ATF itself does not range-check. Public Linux checks 50000--120000. |
| `0xc20003c1` (`BIGIDVFS_SWREQ`) | `x1=request`, `x2=x3=0` | Performs a software-request handshake. Handler `0x1062d0`. | `0`, or `-1` after an approximately 200-us handshake timeout. |
| `0xc200035f` (`REG_READ`) | `x1=physical address` | Reads one 32-bit word only when `(address & 0xffffc000) == 0x10220000`. | Zero-extended register value, or `-3` outside the whitelist. Treat the return as `u32`, because bit 31 can look negative in the vendor wrapper. |
| `0xc200035e` (`REG_WRITE`) | `x1=physical address`, `x2=u32 value` | Writes one 32-bit word and executes a barrier under the same whitelist. | `0`, or `-3` outside the whitelist. This service is state-changing and is forbidden in the observation capture. |

Header-declared services `0xc20003b2` through `0xc20003b7` and
`0xc20003b9` through `0xc20003c0` have no dispatcher branch in this payload and
return `-1`. They must not be exposed merely because the public header names
them. The generic firmware result vocabulary includes `0`, `-1`, `-2`, `-3`
and `-4`, but the per-handler behavior above is the enforceable contract.

The `0xc20003bf` handler first writes SRAM calibration at `0x102222b4`, using
the low 16 bits of efuse register `0x1020666c` or `0x7777` as fallback. It then
preserves the upper bits of `0x102222b0` and writes low state equivalent to
`0x8f0 | selector`. Its selector is 1 at or below 69999, 2 from 70000 through
89999, and `3 + floor((argument - 90000) / 2500)` at and above 90000. Thus the
vendor 110000 request selects `0xb`, while 120000 selects `0xf`. A zero return
does not show that calibration, selector, or resulting voltage is correct;
readback through `REG_READ` or an independently reviewed observer is mandatory.

The `0xc20003b8` frequency handler uses post-divider encoding 2 and four times
the requested MHz through 500 MHz, encoding 1 and twice the request through
1000 MHz, and encoding 0 above 1000 MHz. It derives PCW as
`(adjusted_MHz << 24) / 26`. These details document later clock ownership; the
first CPU8 provider must not invoke this service.

## 4. PSCI and secure-firmware ownership

The platform uses PSCI v0.2 with the SMC conduit. AArch64 `CPU_ON` is
`0xc4000003` with:

- `x1 = 0x200` for CPU8 or `0x201` for CPU9;
- `x2 = physical address of secondary_entry`;
- `x3 = 0` context.

Raw standard results are success `0`, not supported `-1`, invalid parameters
`-2`, denied `-3`, already on `-4`, on pending `-5`, internal failure `-6`, not
present `-7`, and disabled `-8`. `AFFINITY_INFO` level 0 reports ON `0`, OFF
`1`, or ON_PENDING `2`, or a standard error. Generic mainline PSCI should issue
the calls; a platform provider must not invent a second PSCI ABI.

Offline ATF analysis establishes these secure-owned operations:

- The MP2 cluster-top helper at analysis address `0x102cdc` sets the SPM
  cluster `PWR_ON` state and polls its status, establishes the secure iDVFS boot
  constants, programs B-PLL register `0x102224a0` through its enable and
  post-divider sequence, takes the DVFSP hardware semaphore to alter the B
  mux/divider, measures/retries the clock, and performs internal bus-protection
  and MTCMOS sequencing. Its observed waits include 20, 1, 10 and 30 us.
- The per-core helper at `0x103c84` owns CPU8/CPU9 MTCMOS and reset using
  per-core `PWR_CON` at `0x10006240` and `0x10006244`: assert core reset, set
  `PWR_ON`, poll status/acknowledgment, then release core reset.
- The PSCI on-finish path at `0x102558`, through helpers at `0x104b84` and
  `0x1003b4`, enables the cluster's CCI-400 coherency and polls snoop status.

Consequently, Linux must not program initial B PLL/mux/divider, cluster
`PWR_ON`/isolation/SRAM fields, per-core reset/MTCMOS, internal bus protection,
or CCI snoop admission. Secondary-entry completion is the durable observation
that the secure path and coherency admission completed.

The shared MCUMIXED window uses B/LL/L/CCI mux fields at `0x1001a270` and
dividers at `0x1001a274`. Vendor clock writes take DVFSP semaphore 3 at
`0x11015440`, with an approximately 2-ms bounded acquisition in 10-us polls,
local interrupt/spinlock protection, and short workaround delays. The first
provider avoids this window. Any later mainline clock provider must implement
that shared arbitration and fail closed on timeout rather than reproduce the
vendor `BUG_ON` behavior.

CCI frequency is a distinct PLL/cpufreq domain, not the CCI coherency switch.
The working Gemian log reports 676 MHz before the observed big-cluster policy
activity. This is an observation target, not a value to program.

## 5. Post-CPU_ON DCM and result reconciliation

The vendor Linux `dcm_mcusys_mp2_sync_dcm(1)` transition operates on physical
`0x10222274`, preserving every bit outside `GENMASK(6, 0)`. The exact ON form is:

1. write `ON bit 0 | DIV4 (3 << 2) | TOGGLE bit 1`;
2. write `ON bit 0 | DIV4`, clearing the toggle.

The OFF form writes `DIV0 | TOGGLE`, then `DIV0` with ON clear. No explicit
delay occurs between the synchronized writes. The vendor mistakenly performs
the ON sequence before checking the `CPU_ON` error. A corrected provider must
not do that: it enables DCM only after raw success or a reconciled already-on /
on-pending state and must read back the exact mask.

After any nonzero generic `cpu_boot()` result, query `AFFINITY_INFO` and wait for
the existing bounded secondary-completion signal before classifying state.
`ALREADY_ON` and `ON_PENDING` are not permission to unwind external power. If
firmware says OFF and no secondary completed, the external path is still beyond
the proven inverse boundary and must remain powered and faulted. A mapped Linux
errno alone is insufficient to choose rollback.

CPU9 must not replay cluster preparation after CPU8 has prepared or entered the
cluster. Maintain a cluster singleton lock, a per-CPU state, and a refcount or
equivalent state machine. Attempt CPU8 once; attempt CPU9 only in a separate
experiment after CPU8 reaches secondary completion and its state is captured.

## 6. Required fail-closed state machine

Before every write, synchronously capture at least:

- SPM `0x10006218` and `0x10006290`;
- TOPRGU `SWSYSRST` bit 11;
- DA9214 page selector, BUCKB enable `0x5e[0]`, and BUCKB VSEL `0xd9[6:0]`;
- SRAM/iDVFS registers through the read-only secure service;
- MP2 DCM `0x10222274`;
- B and CCI clock mux/divider/rate through an owner that honors DVFSP locking.

Use these state boundaries:

| Boundary | Permitted response to failure |
| --- | --- |
| Before any write | Return failure; no cleanup needed. |
| PWRAP reset asserted, before regulator enable | Deassert PWRAP only if this attempt asserted it and readback confirms ownership. |
| Regulator enabled, before external isolation clear | Deassert PWRAP; disable BUCKB only if this attempt uniquely changed disabled to enabled and current readback still matches. Otherwise retain it and fault. |
| At or after clearing `CPU_EXT_BUCK_ISO` | No proven inverse. Retain power, deassert PWRAP if safely owned, mark the cluster FAULT, reject retry, and rely on the independent watchdog/native reset recovery. Do not guess isolation or reset restoration. |
| At or after SRAM-LDO SMC | Same one-way fault boundary; validate by readback, never by `x0 == 0` alone. |
| PSCI accepted, already-on, on-pending, timed out, or returned an ambiguous error | Reconcile `AFFINITY_INFO` and secondary completion. Never remove external power. Mark ONLINE only after completion; otherwise mark FAULT and reject retry. |

The first provider must not register a working CPU-disable/hotplug-off callback.
Return false from `cpu_can_disable()` for CPU8/9 and provide no hardware-off
path. The vendor parent-side kill loop polls ten times at 10 ms but disables
iDVFS/DCM before affinity is conclusively off, then runs the incomplete external
off function. It is evidence of policy, not a safe inverse to copy.

Arm the already-proven hardware watchdog independently before exactly one CPU8
request, and maintain a USB observation path and pstore markers containing the
immediate pre-state, each completed boundary, raw/mapped PSCI result, affinity
state, secondary completion, and exact DCM readback. The watchdog is recovery,
not proof that a sequence is safe. CPU9 gets its own later attempt and reboot
boundary.

## 7. Missing read-only Gemian evidence

No active mainline provider should be selected until a separately reviewed
Gemian observer captures natural HPS transitions without changing policy.
Collect synchronized samples for A72-offline, CPU8-only if it naturally occurs,
both-online, and offline-again. For every sample record timestamp, boot ID,
online mask, external power/battery status, and:

1. DA9214 page/selector state, `0x5e` enable and `0xd9` VSEL. Use the existing
   driver under its I2C lock; page-selection writes must be restored and
   reported. Do not use raw `/dev/i2c-*` while the driver owns the device.
2. SPM `0x10006218` and `0x10006290`, plus TOPRGU `SWSYSRST` bit 11, through
   existing synchronized providers or a read-only observer. Do not use
   `/dev/mem`.
3. Secure read snapshots of `0x10222470`, `0x10222498`, `0x1022249c`,
   `0x102224a0`, `0x102224a4`, `0x102224ac`, `0x102224b0`, `0x102224b4`,
   `0x102224cc`, `0x102222b0`, and `0x102222b4`. Use only the existing
   read-only `0xc200035f` service and preserve returned bits as `u32`; never
   invoke `REG_WRITE`, SRAM-LDO, PLL, enable, disable, or SWREQ services.
4. Protected MCUMIXED mux/divider and B/CCI PLL/rate through existing vendor
   diagnostics or a read-only observer that honors the DVFSP hardware
   semaphore. Do not add an unarbitrated overlapping mapping.
5. MP2 DCM `0x10222274` and the existing CCI-rate report.
6. Existing function trace/log timing around natural `cpu_power_on_buck()`,
   PSCI return, secondary completion, iDVFS enable, DCM change, and natural
   last-A72 off. Do not write any CPU `online` file or force HPS/PPM targets.

The capture must answer these decision-changing questions:

- Is BUCKB already enabled while both A72s are offline, at which voltage, and
  which driver holds the regulator reference?
- Is MP2 `PWR_RST_B` already released while offline?
- Are both external-buck isolation bits set offline and cleared together on
  entry, or is clearing `L_EXT_BUCK_ISO` merely an inherited no-op?
- Does TOPRGU PWRAP reset begin and end deasserted around every natural event?
- What exact SRAM selector/calibration and B PLL/mux/divider values bracket the
  transition, and do the 240-us points correspond to stable readback?
- Does MP2 DCM change only after accepted `CPU_ON`, and what state remains after
  the last A72 naturally goes offline?
- Does the running unit's read-only TEE partition checksum match the analyzed
  private payload? Record only a checksum and partition identity; do not copy
  or commit firmware.

## 8. Why draft patch 0093 remains unselectable

Draft patch
[`0093-soc-mediatek-enable-MT6797-A72-power-sequence.patch`](../../../patches/v7.1.3/0093-soc-mediatek-enable-MT6797-A72-power-sequence.patch)
has SHA-256 `25919426c790a8f34945070c5f76aea678470708de0c2204c0691a19c41c936f`.
It must not be edited in place or selected because:

- it names SPM `0x218` as an A53/"CA7 CPU1" register, but it is
  `MP2_CPUSYS_PWR_CON`, and names `0x290` generically instead of preserving its
  distinct L/B external-isolation semantics;
- it assumes a fixed inherited 1.0 V regulator state without the required
  synchronized Gemian offline-state evidence;
- it treats a nonnegative SRAM-LDO SMC result as success even though the
  captured handler always returns zero and performs additional calibration
  side effects;
- its probe-time snapshot is not a transaction-local pre-state/readback record;
- it crosses the external-isolation one-way boundary without a proven inverse;
- an active userspace watchdog gate bounds recovery time but cannot validate
  rail ownership, firmware identity, readback, or rollback;
- it does not embody the raw PSCI/affinity/secondary reconciliation required for
  already-on, on-pending, and ambiguous outcomes;
- its direct post-`CPU_ON` DCM action lacks the complete state/readback contract,
  while the vendor ordering it was derived from checks the PSCI error too late.

Keep fail-closed patch 0092 as the selected behavior until a replacement is
derived from the missing capture. Candidate AL is the separate mainline
I2C6/DA9214 resource-only predecessor and requests neither A72. The replacement
should be a new logical patch, not a mutation of 0093; Candidate AM is the first
active provider candidate and should request CPU8 only.

## 9. Evidence pins

Public source files below are from recovery-VM path
`/home/julien.guest/src/reference/gemian-linux-kernel-3.18` at commit
`d388d350cb2dda8f23b99be6fa5db9628896e87f`:

Correction, 2026-07-23: the active March 29 kernel and the installed May 24
`gbp59e00a` package are different artifacts. The active Android boot image has
SHA-256
`1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`;
its kernel field has SHA-256
`b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
The active private build's exact public source commit remains unresolved.
Public `59e00a` is the chosen observer-source equivalent, not exact active
provenance: all observer-hook blobs are identical across the relevant public
lineage, while the active private binary also has the
`MAX_RESERVED_REGIONS=32` fix and a different keymap. `mt_idvfs.c` and
`mt_freqhopping.c` are also byte-identical between the original `d388d350`
contract input and `59e00a`, but PSCI, SMP, HPS, DCM, SPM, DA9214, and watchdog
files drifted. Use this table as the original contract input and the
[active-kernel reconciliation](active-gemian-kernel-reconciliation-20260723.txt)
for the verified source-equivalence boundary. Package-derived virtual
addresses are not active-binary addresses and are intentionally not carried
forward as observer hooks.

| Source path | SHA-256 | Relevant contract |
| --- | --- | --- |
| `arch/arm64/kernel/psci.c` | `81c4c2851fef7dea691dbc7d1f9e54c6185e127f6b136b77a7d7711cf82b6fe4` | external buck sequence, PSCI order, incomplete off path |
| `drivers/misc/mediatek/base/power/mt6797/mt_idvfs.h` | `7c0e142b4a61ef89f432195e779c9a3408a8b25282732dad9a0eb98be96cfd68` | public iDVFS API and units |
| `drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c` | `7232f5ba7347511d97da6947c6833811b439d3116f95a13e631be40d7033b2e7` | SRAM wrapper, dynamic enable, DA9214 conversion, secure accesses |
| `drivers/misc/mediatek/base/power/mt6797/mt_dcm.c` | `46304a982c544276ed9d75e4119617646b9e6c9ecc6ae997c8b43f41ea4029ad` | exact MP2 DCM toggle |
| `drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c` | `a420033f65c49bf509182388fcb803161e69e93cf7d334b723fe7a0c55b8c293` | LL/L/B/CCI ownership and policy |
| `drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c` | `6f4165bdedd7ec318eb35e48fbc7da35967edb1af3729e47feb2537d944ac2a4` | PLL-domain separation |
| `drivers/misc/mediatek/base/power/include/spm_v2/mt_spm_reg_mt6797.h` | `a89a7b879f0b5ef8fd7d9625ff767741c6ad9e4f56a6bd82b52865cfd2d93c6b` | exact SPM names and bit masks |
| `drivers/watchdog/mediatek/wdt/mt6797/mt_wdt.h` | `fdbd42a1e238cc5148486a0d765434bddf008808244ad76af77d9371a208fa30` | PWRAP reset ID/bit |
| `drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c` | `31aa4fe4ce00125b4a09da75534cd840c9a962aaa33752aecfce96c10b3ef20a` | keyed locked reset RMW and polarity |
| `drivers/misc/mediatek/power/mt6797/da9214.c` | `32306d145361d5b3da8a024d0a495906ea275f71741cee39d1fc3dcaf7c096a3` | DA9214 byte access, paging, and return-type defect |
| `drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_secure_api.h` | `f810af34727ccedfa6a24cf9721d75301875e32cc6e9c6e1aaa5a6cb8ba4b421` | declared SMC IDs and wrapper calling convention |

Runtime interpretation is cross-linked to the
[`Gemian CPU and scheduler policy experiment`](../../2026-07-21-gemian-cpu-scheduler-policy/README.md).
Its private capture records the vendor 1.1-V SRAM request, later 1.2-V dynamic
iDVFS request, and successful 750-MHz iDVFS start. Its HPS four/four/two tuple
is an unchecked algorithm-local count, not all-ten completion evidence. A
later bounded direct capture proves one CPU8 online/offline cycle while CPU9
remains unconfirmed. Neither capture supplies the missing synchronized
register pre-state or a reversible mainline sequence.
