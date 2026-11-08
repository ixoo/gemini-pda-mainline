# MT6797 CPU clusters and core configuration

Scope: the ten application CPUs in the MT6797X Gemini PDA, their cluster and
power/clock topology, frequency scaling, voltage regulation, the firmware and
vendor-kernel stages that configure them, the per-unit operating-point
selection observed on the named development unit, and the boundary between
that vendor stack and current mainline Linux.

This document consolidates static Gemian-source analysis, retained boot-chain
firmware analysis, and previously published runtime evidence. It does not
claim mainline CPU frequency, idle, thermal, suspend, or general hotplug
support. Runtime status remains in the
[hardware support matrix](../HARDWARE_SUPPORT.md), and unresolved work remains
in the [roadmap](../ROADMAP.md).

| Field | Value |
| --- | --- |
| Device | Named Gemini PDA development unit (MT6797X) |
| Last verified | 2026-10-31 |
| Vendor baseline | Gemian Linux `3.18.41+`; public source equivalent [`59e00a91`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467) |
| Loader baseline | Planet LK `f4988d74`; retained preloader/LK/TEE/SCP partition code |
| Mainline baseline | Linux 7.1.3 plus the repository patch series |
| Decisive topology evidence | [4+4+2 topology/RAM result](../../experiments/2026-09-02-mainline-mt6797-cpu-map/results/runtime-attempt-2-topology-ram-pass-20260902.txt) |
| Decisive A72 register evidence | [Complete CPU8/CPU9 target capture](../../experiments/2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt) |

Confidence follows the [hardware knowledge base](README.md) convention. A
vendor-source statement is not a measurement, and one unit is not every
variant.

## 1. Cores, clusters, and identities

The package exposes ten 64-bit application cores in three clusters. There is
one hardware thread per core and no SMT.

| Logical CPU | DT `reg` / MPIDR | Cluster | Core in cluster | Part | Vendor role |
| --- | --- | --- | --- | --- | --- |
| 0 | `0x000` | 0 | 0 | Cortex-A53 (`0xd03`) | Boot CPU, LL |
| 1 | `0x001` | 0 | 1 | Cortex-A53 | LL |
| 2 | `0x002` | 0 | 2 | Cortex-A53 | LL |
| 3 | `0x003` | 0 | 3 | Cortex-A53 | LL |
| 4 | `0x100` | 1 | 0 | Cortex-A53 | L |
| 5 | `0x101` | 1 | 1 | Cortex-A53 | L |
| 6 | `0x102` | 1 | 2 | Cortex-A53 | L |
| 7 | `0x103` | 1 | 3 | Cortex-A53 | L |
| 8 | `0x200` | 2 | 0 | Cortex-A72 (`0xd08`) | B / big |
| 9 | `0x201` | 2 | 1 | Cortex-A72 | B / big |

Vendor names are LL (`0-3`), L (`4-7`), B (`8-9`), plus an independent CCI
clock/voltage domain. The four names are used throughout the vendor
`mt-cpufreq` code and are not four CPU clusters: CCI is the cache-coherent
interconnect.

Durable identity facts:

| Fact | Confidence | Evidence |
| --- | --- | --- |
| Eight A53 and two A72 cores, all `enable-method = "psci"` | `observed` | Ten CPU nodes in the vendor and live DT |
| A53 cluster-local MPIDRs `0x000`-`0x003` and `0x100`-`0x103`; A72 `0x200`, `0x201` | `confirmed` | DT `reg`, live scheduler topology, and the A72 pmsg capture |
| A53 part `0xd03`, revision 4; A72 part `0xd08` | `observed` | `/proc/cpuinfo` and A72 secondary-startup registers |
| A72 MIDR `0x410fd081`, REVIDR 0 | `observed` | [A72 register capture](../../experiments/2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt) |
| Both A72s report the same AArch64 and AArch32 identification vectors | `observed` | Same capture |
| CNTFRQ `0x00c65d40` (13 MHz), CTR `0x8444c004`, DCZID `0x4`, CLIDR `0x0a200023` | `observed` | Same capture |
| One SoC package: `core_siblings_list=0-9`, leaf `cluster_cpus_list` `0-3`, `4-7`, `8-9` | `observed` | [Topology result](../../experiments/2026-09-02-mainline-mt6797-cpu-map/results/runtime-attempt-2-topology-ram-pass-20260902.txt) |
| CPU0 is the boot CPU | `inferred` | Standard single-core preloader/LK boot, then PSCI brings CPU1-9 online |

The vendor SoC `mt6797.dtsi` contains the correct three-cluster `cpu-map` and
the descriptive `clock-frequency` values 1.391 GHz (LL), 1.95 GHz (L), and
2.288 GHz (B). Those properties are loader inputs, not an OPP or voltage
contract. The current mainline board DT gained its own `cpu-map` only with
canonical patch `0482`. See
[`arch/arm64/boot/dts/mt6797.dtsi`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/arch/arm64/boot/dts/mt6797.dtsi)
and the [topology experiment](../../experiments/2026-09-02-mainline-mt6797-cpu-map/README.md).

## 2. Which stage configures which part

The CPU configuration is split across five owners. No single image contains
the whole sequence.

| Stage | Owns | Does not own |
| --- | --- | --- |
| Preloader (eMMC boot region) | Early PLL, MTCMOS, DRAM, PMIC and initial VPROC/VSRAM setup; carries the vendor DVFS domain names | Per-core bring-up; Linux CPU hotplug |
| Planet LK | CPU-node pruning from efuse, `clock-frequency` clamping from the speed bin, final DT and `atag,devinfo` handoff | Cluster/core power-up or frequency policy |
| TEE / ATF (PSCI) | CPU_ON/OFF/SUSPEND, cluster and per-core MTCMOS/reset, initial B PLL/mux/divider, CCI snoop admission, secure BigiDVFS and SRAM-LDO services | Linux scheduler or hotplug policy |
| SCP (TinySys CM4) | Its own core DVFS, IPI, DMA and SPM request path | Application CPU power, clocks, or thermal policy |
| Vendor Linux | HPS hotplug, PPM frequency policy, per-cluster cpufreq, EEM calibration, thermal throttling, A53/L/CCI PLL writes, DA9214 and SRAM-LDO voltage changes, MP2 DCM | Firmware-owned MTCMOS, initial B PLL, CCI snoop |

### 2.1 Preloader

The retained preloader identifies build `20190517-154415`, contains
`Pll init start...Done`, `mtcmos Start..Done!`, `vproc/vsram run as hw
default`, `Set SRAM to 1.1V`, and the `MT_CPU_DVFS_LL/L/B` domain names. This
establishes that it performs initial platform PLL/MTCMOS and initial
processor-rail setup (strings `observed`, behavior `inferred`). Its exact
register sequence was not disassembled, so no individual preloader register
write is claimed here. The runtime consequence is visible: the boot CPU runs
with a valid PLL, DRAM, and rails before Linux.

### 2.2 Planet LK prunes and clamps the CPU tree

LK is not a passive DT appender. `target_fdt_cpus()` in
[`lk/platform/mt6797/atags.c`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/atags.c)
does three CPU-relevant things:

1. It decodes efuse index 3 into per-cluster core counts and efuse index 8
   bit 7 (`mp0_disable`), then deletes every CPU node beyond the enabled
   count. It deletes the matching `/cpus/cpu-map/clusterN/coreM` node too.
2. It clamps each surviving node's `clock-frequency` to the speed-bin maximum
   derived from efuse index 8 (separate big and small fields) only when the DT
   value is higher.
3. It requires `clock-frequency` on every surviving CPU. A missing value makes
   its subnode iterator repeat the first node, which is the previously
   diagnosed pre-Linux non-progress path.

This explains why `possible` and `present` are exactly `0-9` on the unit: the
efuse reports 4/4/2 enabled cores. It also explains why the ten
`clock-frequency` properties are a loader prerequisite for a mainline DT, not
decoration. See the
[LK iterator repair](../../experiments/2026-08-17-mainline-lk-cpu-clock-iterator-repair/README.md).

The raw efuse words for this unit were not separately dumped. The active
operating-point tables let their relevant fields be inferred; see section 4.

### 2.3 TEE / ATF owns the PSCI mechanism

The installed TEE payload identifies itself as `v1.0(debug):df3e3f8`, built
2019-05-17, and implements PSCI v0.2 over SMC with standard IDs. Its own
strings include PSCI affinity, `Enable CPUSYS0/1`, CPU power-on/off, CCI
snoop control, big ARMPLL, iDVFS, SRAM-LDO and MP2 DCM paths. Static analysis
establishes:

| Operation | Secure-owned behavior |
| --- | --- |
| `CPU_ON` (`0xc4000003`) | MP2 cluster-top power/reset, B PLL/mux/divider, per-core MTCMOS/reset, internal bus protection, CCI snoop admission |
| `CPU_OFF` / last-core teardown | Target enters WFI; a controlling CPU's `AFFINITY_INFO` request performs the hardware teardown |
| BigiDVFS | PLL frequency, SRAM-LDO, enable/disable, software-request handshake via `0xc20003b8`, `0xc20003bf`, `0xc20003b0`, `0xc20003b1`, `0xc20003c1` |
| Secure register access | Read `0xc200035f`, write `0xc200035e`, limited to the `0x1022xxxx` window |

The A72 `CPU_ON` arguments are MPIDR `0x200`/`0x201`, the standard
`secondary_entry` physical address, and context zero. A mainline provider must
not program the firmware-owned initial PLL, cluster MTCMOS, per-core reset, or
CCI snoop registers itself. The exact ABI and call-site audit are in the
[A72 firmware/power contract](../../experiments/2026-07-22-a72-firmware-power-contract/README.md)
and [secure CPU-off attribution](../../experiments/2026-08-05-a72-secure-cpu-off-attribution/README.md).

### 2.4 SCP has no application-CPU role

The retained SCP image contains only the TinySys loader, FreeRTOS, DMA, IPI,
SPM-request, and SCP-local DVFS modules (`drivers/CM4_A/mt6797/dvfs/src/dvfs.c`,
`scp_ipi.c`, `dma.c`). Its DVFS service controls the SCP core's own clock and
voltage. It contains no application CPU cluster, PSCI, or thermal trip code.
This closes the recurring question of whether the SCP is the missing CPU8/9
power owner: it is not. The same conclusion is recorded in
[thermal management](mt6797-thermal-management.md#6-firmware-roles).

### 2.5 Vendor Linux CPU firmware

Two different pieces of "firmware" run in the application subsystem:

- **CSPM PCM DVFS firmware.** `mt_cpufreq_hybrid_fw.h` embeds
  `pcm_dvfs_v0.2_160125_02` (hardware-governor build) or
  `pcm_dvfs_v0.1_160131_02` (software-request build). The kernel copies the
  selected image into 12 KiB CSRAM at `0x0012a000`, kicks the CSPM engine, and
  services its events. The live Gemian unit reports `enable_cpuhvfs=1` and
  `enable_hw_gov=0`, so the hardware-governor policy is disabled; the kernel
  still loads and services a PCM image. The exact compiled image (the `v0.1`
  software-request or `v0.2` hardware-governor build) is not identified by
  that flag alone. The PCM code touches the CSPM/DVFSP window (`0x11015xxx`),
  MCUMIXED mux `0x1001a270`, and the B-PLL area `0x102224xx`; it is not
  executed by the SCP.
- **Secure BigiDVFS/iDVFS.** The B cluster's frequency, SRAM-LDO, and adaptive
  voltage loop are secure services. `mt_idvfs.c` enables them with the current
  B frequency and rail values, then the kernel requests percentages through
  ATF.

Both are vendor mechanisms. A mainline clock/OPP provider must not load the
vendor PCM image or call BigiDVFS without its own ownership and rollback
contract.

## 3. Power, clock, and voltage topology

```
CPU0-3  (LL)  -- ARMPLL0 (0x1001a204) --+
CPU4-7  (L)   -- ARMPLL1 (0x1001a214) --+-- VPROC1: DA9214 BUCKA (0xd7)
CCI           -- ARMPLL2 (0x1001a224) --+   VSRAM_L: INFRACFG_AO LDO
                                            (0x10001f98/f9c/fa0)

CPU8-9  (B)   -- B PLL / iDVFS (ATF)   --- VPROC2: DA9214 BUCKB (0xd9)
                                            VSRAM_B: secure SRAM LDO
                                            (0x102222b0/b4)
```

### 3.1 Clock registers

All three A53/CCI PLLs and the shared divider live in MCUMIXED at
`0x1001a000`. The vendor kernel serializes every write through the DVFSP
hardware semaphore at `0x11015440` (SEMA3, MCU/FH), with a 2 ms bounded
acquisition. ATF, SPM, and the kernel are documented competing owners.

| Domain | PLL CON1 | Mux field in `0x1001a270` | Divider field in `0x1001a274` |
| --- | --- | --- | --- |
| B (A72) | ATF-owned `0x102224a0` | bits 1:0 | bits 4:0 |
| LL (CPU0-3) | `0x1001a204` | bits 3:2 | bits 9:5 |
| L (CPU4-7) | `0x1001a214` | bits 5:4 | bits 14:10 |
| CCI | `0x1001a224` | bits 7:6 | bits 19:15 |

The A53/CCI PLL word uses the vendor DDS/PCW form
`(MHz << 14) / 26` with bit 31 as the change strobe. A frequency change first
switches the domain to MAINPLL, writes the new PLL word, waits 20 us, then
switches back to the ARMPLL. Divider encodings are `8` for divide-by-1, `10`
for divide-by-2, and `11` for divide-by-4.

The B cluster does not use that direct write path. `mt_cpufreq.c` uses
`BigIDVFSFreq()` percentages; ATF programs the B PLL, post-divider and mux.
The readable live tuple is `armplldiv_muxsel=0x55`,
`armplldiv_ckdiv=0x08`, `big_pll_pcw=0xb9b13b14`,
`big_pll_enable_posdiv=0x00ff1101`, decoded as 750 MHz.

### 3.2 Regulators and SRAM tracking

The two DA9214 bucks are not interchangeable:

| Rail | DA9214 register | Consumers | Control |
| --- | --- | --- | --- |
| VPROC1 | BUCKA voltage `0xd7`, 7-bit VSEL, 300 mV + code x 10 mV | LL, L, and CCI | Vendor cpufreq changes voltage only; the CPU path does not enable/disable BUCKA |
| VPROC2 | BUCKB voltage `0xd9`, same encoding | A72 cluster | Vendor A72 path enables BUCKB at `0x5e[0]`, waits 1 ms, then clears external-buck isolation |

The vendor DT names BUCKB `vproc-big`. This confirms the rail mapping that the
earlier DA921x record left open. It is a software and board-description
mapping; the physical pin voltage has not been measured.

VSRAM is a separate internal LDO per side:

- VSRAM_L for LL/L/CCI is programmed in INFRACFG_AO at
  `0x10001f98`-`0x10001fa0`; the vendor code enables the LDO group and rounds to
  2.5 mV PMIC steps, clamping below 900 mV.
- VSRAM_B for the A72 cluster is programmed only by the secure
  `BIGIDVFS_SRAM_LDO_SET` service; the handler writes calibration at
  `0x102222b4` and selector state at `0x102222b0`.

The vendor voltage loop enforces `VSRAM >= VPROC`, a nominal 10 mV difference,
a 30 mV maximum difference, VSRAM 1.0-1.2 V, and VPROC <= 1.2 V. It raises
VSRAM before VPROC and lowers VPROC before VSRAM. These are vendor safety
constraints, not an upstream OPP contract.

### 3.3 A72 external preparation and MP2 control

The vendor `cpu_power_on_buck()` sequence is the only public description of
the external half of A72 bring-up:

1. Release MP2 cluster-top reset: SPM `0x10006218` bit 0.
2. Ordering read of B-PLL register `0x102224a0`.
3. Assert the TOPRGU PWRAP reset (`SWSYSRST` bit 11).
4. Enable DA9214 BUCKB (`0x5e[0]=1`) and wait 1 ms for a hotplug transition.
5. Clear `CPU_EXT_BUCK_ISO` bits 1:0 at SPM `0x10006290`.
6. Deassert PWRAP reset; wait 240 us.
7. Request 1.1 V from the secure SRAM-LDO service; wait 240 us.
8. Issue standard PSCI `CPU_ON`.

After a successful or reconciled `CPU_ON`, vendor Linux toggles MP2
synchronous DCM at `0x10222274` bits 6:0. It owns only the external
preparation and DCM; ATF owns everything between the isolation clear and the
secondary's first instruction.

The vendor off path clears BUCKB and calls a SRAM-LDO disable function that is
a no-op in the captured build. It does not restore isolation, MP2 reset, PLL,
or DCM. That missing inverse is why mainline CPU8/9 admission remains
experimental and fail-closed.

### 3.4 CPU status and power registers

| Function | Register | Meaning used by the project |
| --- | --- | --- |
| CPU power status | SPM `0x10006188` / `0x1000618c` | CPU8 bit 7 in the first word, CPU9 bit 6 in the second; vendor on-state is their intersection |
| MP2 cluster-top control | SPM `0x10006218` | bit 0 reset release, bits 1-4 isolation/power/clock, bits 5-6 SRAM isolation |
| MP2 core 0/1 control | SPM `0x10006240` / `0x10006244` | per-core reset, isolation, power-on, clock and SRAM fields |
| External buck isolation | SPM `0x10006290` | bit 1 B-side, bit 0 L-side |
| MP2 synchronous DCM | MCUCFG2 `0x10222274` | bits 6:0; vendor ON/OFF is a two-write toggle |
| PWRAP SPI reset | TOPRGU `SWSYSRST` | bit 11, keyed `0x88000000` RMW |

These are observation and ownership facts, not permission for a mainline
driver to write them. Only the external-preparation subset has a reviewed
forward contract.

### 3.5 Frequency and voltage transition paths

There are two vendor paths, and the live unit uses the second:

| Path | When used | Behavior |
| --- | --- | --- |
| Manual kernel sequence | `enable_cpuhvfs=0` or CPUHVFS kick failure | Kernel writes PLL/mux/divider and DA9214/VSRAM selectors directly; with `ENABLE_IDVFS` the B cluster instead requests a percentage through ATF |
| CPUHVFS/PCM | `enable_cpuhvfs=1` (live unit) | `set_cur_freq_hybrid()` asks the CSPM PCM for a target OPP; the PCM performs the sequence and returns the selected voltage |
| Secure iDVFS | B voltage loop with `ENABLE_IDVFS`; enabled at runtime (`idvfs_mode=1`) | ATF adjusts B PLL/VPROC2/VSRAM_B in closed loop; the vendor status surfaces both CPUHVFS and iDVFS on the live unit |

The manual sequence remains the clearest statement of the ordering the
firmware and any future mainline provider must preserve:

- **Raising frequency:** raise VSRAM_L and VPROC1 to the target first, then
  change the PLL/mux and divider, then reprogram CCI.
- **Lowering frequency:** change the PLL/mux and divider first, reprogram CCI,
  then lower VSRAM_L and VPROC1.
- **Within a voltage change:** raise VSRAM before VPROC; lower VPROC before
  VSRAM. The vendor loop steps in 10 mV units to keep
  `VSRAM - VPROC` between 10 and 30 mV.
- **CCI coupling:** each LL/L OPP change computes a new CCI OPP from the same
  VPROC1 target. CCI is not left at an arbitrary independent frequency while
  the CPU clusters move.
- **Settling:** PLL change 20 us, post-divider 2 us, PMIC up/down delay from
  the vendor formula with a 25 us minimum, A72 buck enable 1 ms, and the A72
  SRAM-LDO points 240 us apart.

For the B cluster neither live path ends in a direct AP voltage write:
`idvfs_set_cur_volt_extbuck()` returns zero in iDVFS mode, and in CPUHVFS mode
`set_cur_volt_hybrid()` is also a no-op because the controller owns the
sequence. The offline reconstruction resolves the layering:

- **CPUHVFS PCM** sequences the OPP: it writes the B control/PCW/monitor
  interface, the PMIC path and the L-side SRAM LDO, and coordinates cluster
  on/off.
- **ATF BigiDVFS** owns the B PLL enable/post-divider and the secure SRAM
  selector.
- **AP iDVFS** runs the adaptive B voltage/frequency loop while the cluster is
  online; the retained dmesg shows it enabled immediately before cluster2 on
  and disabled immediately after cluster2 off.

This is why the B OPP table's voltage column is a policy input, not a value
the AP kernel writes on this unit. The remaining unknown is the external
actor that enables/disables iDVFS and the exact arbitration when both layers
touch the B PLL/rail. See the
[ownership reconstruction](../../experiments/2026-10-31-mt6797-vendor-cpu-policy-re/results/pcm-idvfs-ownership.md).

No mainline provider implements either path. The current mainline clock
backend is read-only, and there is no writable CPU regulator or OPP table.

### 3.6 How Gemian observes core voltage

Gemian does **not** measure VPROC or VSRAM with a rail ADC. The PMIC
auxiliary ADC channels cover battery, charger, thermal and accessory inputs;
there is no VPROC/VSRAM channel. The vendor stack calls its readbacks
"voltage", but they are readbacks of the commanded regulator/LDO code:

| Domain | Readback source | What it actually reports |
| --- | --- | --- |
| VPROC1 (LL/L/CCI) | CSPM `V_CURR`, or DA9214 register `0xd7` when CPUHVFS is unavailable | PMIC voltage code; `300 mV + code x 10 mV` for the DA9214 path |
| VPROC2 (A72) | CSPM `V_CURR`, or DA9214 register `0xd9` when CPUHVFS is unavailable | PMIC voltage code, including the selector last written by ATF's iDVFS |
| VSRAM_L | `CPULDO_CTRL_0/1/2` at `0x10001f98`/`0x10001f9c`/`0x10001fa0` | LDO enable and selector code, converted through the PMIC code table |
| VSRAM_B | Secure SRAM-LDO selector at `0x102222b0` bits 3:0 | LDO selector; returns a stored value when both A72s are offline |
| CPUHVFS state | CSPM `SW_RSV3`/`SW_RSV4`/`SW_RSV5`/`SW_RSV6` at `0x11015614`, `0x11015618`, `0x1101561c`, `0x11015620` | `V_CURR` bits 14:8 and `VS_CURR` bits 23:16, the controller's applied PMIC codes |
| A72 frequency | B PLL PCW and post-divider through ATF | PLL setting, not a rail measurement |

The calling APIs and their semantics:

- `mt_cpufreq_get_cur_volt()` returns the result of the domain's
  `get_cur_volt` callback, i.e. one of the readbacks above. It does not issue
  an ADC conversion.
- `get_cur_volt_extbuck()` performs an I2C read, retries while the decoded
  value is the minimum code, and returns zero on failure. The caller treats
  zero as invalid.
- `get_cur_volt_sram_l()` requires the LDO enable field to be `0xff`, checks
  that the two duplicated selectors agree, and `BUG_ON()`s on mismatch.
- `cpuVoltsampler_func` / `mt_cpufreq_setvolt_registerCB()` is a notification
  hook. It receives the OPP-table voltage, not a measurement, and no in-tree
  registrant was found in the inspected Gemian source.
- EEM's detector is a silicon speed/process/temperature monitor used to adjust
  the voltage table. It is not a voltmeter, and `eem_cur_volt` reports the
  selected table value.

Consequences:

- A correct VSEL readback proves only that the controller register holds the
  expected code. It cannot detect regulator output error, board IR drop, a
  stale readback, or a rail that never reached the requested value.
- The A72 secure path can change VPROC2/VSRAM_B without the AP writing the
  selector; reading it back through `0xd9` is indirect observation of ATF's
  last setting.
- The vendor accuracy is therefore bounded by the regulator/LDO tolerance and
  the selector-to-voltage formula. Any claim about the physical rail requires
  an external measurement at a test point, which this project has not made.
- The mainline protected-clock observer and read-only DA921x provider can read
  the same register state, but they do not turn it into a calibrated voltage
  measurement either.

### 3.7 How an A53 frequency change is made

The Gemian source sets the A53 cluster clocks in three stages (`mt_cpufreq.c`
`set_cur_freq()`, `freqhopping/mt6797/mt_freqhopping.c`). Each is `source`
confidence unless a mainline result is linked.

| Stage | Register | What it does |
| --- | --- | --- |
| PLL | CON1 `0x1001a204` (LL) / `0x1001a214` (L): PCW bits 20:0, post-divider bits 26:24 (`0` /1, `1` /2, `2` /4), bit 31 change strobe | VCO = PCW x 26 MHz / 2^14; the vendor computes PCW as `(MHz << 14) / 26` |
| Cluster divider | `0x1001a274`: LL bits 9:5, L bits 14:10 | Code `8` /1, `10` /2, `11` /4; `0` also reads as /1 |
| Mux | `0x1001a270`: LL bits 3:2, L bits 5:4 | `1` ARMPLL, `2` MAINPLL |

- **PCW changes go through the MCU frequency-hopping controller**, not a CON1
  write. MCU FHCTL sits at MCUMIXED + `0xf00`: `HP_EN` `+0x0`, `CLK_CON`
  `+0x4`, `RST_CON` `+0x8`, `SLOPE0` `+0xc`, then per PLL `n` (`0` LL, `1` L,
  `2` CCI) `CFG`, `UPDNLMT`, `DDS`, `DVFS`, `MON` at `+0x34 + 0x14n` onward.
  The vendor copies CON1's PCW into `DDS`, sets `CFG` to `0x5`, `SLOPE0` to
  `0x6003c97`, sets the PLL's `HP_EN` bit, writes the target to `DVFS`, polls
  `MON` every 10 us (up to 1 ms), writes `MON` back into CON1 and clears
  `HP_EN` and `CFG`. The PLL slews without the cluster leaving it. Its init
  sets each `CLK_CON` bit, pulses `RST_CON` and clears `CFG`, `UPDNLMT`, `DDS`.
- **A post-divider change moves the cluster to MAINPLL for 2 us**: set TOPCKGEN
  `CLK_MISC_CFG_0` (`0x10000104`) bits 5:4 to `3`, mux to `2`, write the
  post-divider with the strobe, wait 2 us, clear bits 5:4, mux back to `1`.
- **Order**: a larger post-divider or cluster divider is applied before the
  hop and a smaller one after it, so the cluster never passes above both
  endpoints. Divider changes need no mux switch.
- **Which dividers**: for every point in the SB and FY tables, the vendor's
  choice is the smallest total division that puts the VCO between 1050 and
  2028 MHz, with up to /2 of it in the post-divider (checked against all 64
  LL/L entries).
- **Shared access**: every MCUMIXED access holds DVFSP hardware semaphore 3 at
  `0x11015440` after writing `0x0b160001` to CSPM `0x11015000`; ATF takes the
  same semaphore to change the A72 fields of the mux and divider registers.
  MCU FHCTL reads may return zero once after a write, so the vendor reads
  every word twice, repeats a zero result, and verifies writes up to three
  times.
- **Sync DCM**: MCUCFG `SYNC_DCM_CONFIG` (`0x10220744`) has one byte each for
  CCI (bits 6:0), LL (14:8) and L (22:16): enable, a 5-bit divider (an idle
  cluster's clock is divided by up to divider + 1) and an update toggle. The
  vendor sets the divider to `MHz / 70` (at most 31) before each frequency
  drop and after each rise, so an enabled divider never exceeds MHz / 70; its
  generic DCM-on path writes divider 3 for all three. On the mainline station
  the firmware leaves `0x00070707`, all three enabled at divider 3, which
  satisfies the vendor rule for any clock of 210 MHz or more
  ([A53 cpufreq A1](../../experiments/2026-11-07-mt6797-a53-cpufreq/README.md#a1)).

On the mainline station the firmware leaves LL at 897 MHz (PCW `0x114000`,
post-divider /2, cluster divider /1), L at 1274 MHz (`0x0c4000`, /1, /1), CCI at
629.5 MHz and VPROC1 at 1.00 V; see the
[one-read protected snapshot](../../experiments/2026-08-23-mainline-protected-clock-first-dmesg-call/results/runtime-attempt-1-pass-20260823.txt)
and the [read-only DA921x provider](../../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/results/runtime-attempt-1-success-20260817.txt).
The [A53 cpufreq experiment](../../experiments/2026-11-07-mt6797-a53-cpufreq/README.md)
drives this sequence from mainline; its attempt A3 measured every LL and L point
it reached within 5 % of the requested rate.

## 4. Per-unit operating points

The vendor source contains four OPP groups (FY, SB, M, L), selected by efuse
function code, with a second date-code split (1221/0119) and an optional
TT-segment rewrite for the B cluster. The live unit's selected tables reveal
its class without a raw efuse dump:

| Domain | Live table top | Live table bottom | Selected source group | Live top voltage |
| --- | --- | --- | --- | --- |
| LL | 1,547,000 kHz | 221,000 kHz | SB (CPU level 1) | 1.17 V |
| L | 2,002,000 kHz | 325,000 kHz | SB | 1.17 V |
| B | 2,587,000 kHz (TT) | 338,000 kHz | SB + date code 0119 + TT segment | 1.16 V |
| CCI | 988,000 kHz | 169,000 kHz | SB | 1.16 V |

The corresponding base (pre-EEM) source tables top out at 1.20 V for
VPROC1/VPROC2; the CCI table's 988 MHz top also uses that 1.20 V base
selector. The live values are lower because EEM has applied per-unit
calibration. The B cpufreq table's top two entries
(2.587/2.431 GHz) are the TT-segment rewrite; the PPM table still reports the
unrewritten 2.522 GHz top. That discrepancy is a vendor policy-view
difference, not two different PLL settings.

Inference from the selected tables: the unit's efuse function-code low nibble
is 4 (SB plus TT) and the date-code field is at least 7 (0119). This is
`inferred`, not a read of the raw efuse words. A bounded read-only
`atag,devinfo` dump would close it; no such capture is retained.

In the selected B table, default index 13 is 845 MHz; that is also the
frequency observed before and after the bounded A72 runs. The vendor
`interactive` governor and PPM determine the rest dynamically.

### 4.1 EEM and thermal coupling

EEM/PTP adjusts each cluster's voltage table from efuse calibration and its own
detector. The live Gemian capture shows separate `EEM_DET_2L`, `EEM_DET_L`,
`EEM_DET_BIG`, and `EEM_DET_CCI` detectors (banks 4, 3, 0, 5) and per-OPP
calibrated values. At or below 33 C the vendor code adds 62.5 mV. Thermal
throttling produces a milliwatt power budget through PPM, which then limits
OPP indices; it does not directly write a frequency. See
[thermal management](mt6797-thermal-management.md) for the sensor, trip,
cooling, and firmware boundary.

### 4.2 Live per-OPP voltage table

The following are the EEM-calibrated pairs reported by the one retained
Gemian policy capture, in OPP order. Frequencies are kHz and voltages are mV.
They are unit-specific observations, not board constants. The raw capture is
private; the non-identifying policy summary is in the
[Gemian CPU/scheduler experiment](../../experiments/2026-07-21-gemian-cpu-scheduler-policy/README.md).

| Index | LL (CPU0-3) | L (CPU4-7) | B (CPU8-9) | CCI |
| --- | --- | --- | --- | --- |
| 0 | 1547000 / 1170 | 2002000 / 1170 | 2587000 / 1160 | 988000 / 1160 |
| 1 | 1495000 / 1150 | 1950000 / 1150 | 2431000 / 1180 | 975000 / 1150 |
| 2 | 1443000 / 1140 | 1885000 / 1120 | 2327000 / 1100 | 936000 / 1130 |
| 3 | 1391000 / 1110 | 1820000 / 1100 | 2262000 / 1080 | 910000 / 1120 |
| 4 | 1339000 / 1090 | 1755000 / 1090 | 2223000 / 1070 | 884000 / 1100 |
| 5 | 1274000 / 1070 | 1703000 / 1060 | 2158000 / 1060 | 845000 / 1080 |
| 6 | 1222000 / 1050 | 1625000 / 1040 | 2093000 / 1040 | 819000 / 1070 |
| 7 | 1118000 / 1000 | 1495000 / 1000 | 1885000 / 990 | 754000 / 1030 |
| 8 | 1014000 / 960 | 1352000 / 950 | 1677000 / 930 | 676000 / 990 |
| 9 | 897000 / 920 | 1209000 / 900 | 1495000 / 890 | 611000 / 950 |
| 10 | 806000 / 880 | 1092000 / 850 | 1378000 / 860 | 533000 / 900 |
| 11 | 715000 / 840 | 962000 / 820 | 1131000 / 820 | 481000 / 870 |
| 12 | 624000 / 810 | 832000 / 790 | 1001000 / 800 | 416000 / 840 |
| 13 | 481000 / 800 | 650000 / 790 | 845000 / 800 | 325000 / 820 |
| 14 | 338000 / 790 | 468000 / 790 | 676000 / 800 | 234000 / 790 |
| 15 | 221000 / 770 | 325000 / 770 | 338000 / 800 | 169000 / 770 |

Three properties matter for anyone reusing this:

- These are post-EEM values; the source base tables are up to 30 mV higher at
  the top OPP.
- The B table is not monotonic at the top: index 1 (2.431 GHz) shows 1.18 V
  while index 0 (2.587 GHz) shows 1.16 V. That is the TT-segment override
  carrying its own voltage, not a general voltage/frequency rule.
- The CCI and LL/L columns share VPROC1; the B column is VPROC2. A transition
  in one column can therefore change the shared rail seen by another.

### 4.3 Vendor base table for the selected speed bin

Before EEM calibration, the selected SB/0119 group in the vendor source is:

| Index | LL (CPU0-3) | L (CPU4-7) | B (CPU8-9) | CCI |
| --- | --- | --- | --- | --- |
| 0 | 1547000 / 1200 | 2002000 / 1200 | 2522000 / 1200 | 988000 / 1200 |
| 1 | 1495000 / 1190 | 1950000 / 1190 | 2392000 / 1170 | 975000 / 1190 |
| 2 | 1443000 / 1170 | 1885000 / 1170 | 2327000 / 1160 | 936000 / 1170 |
| 3 | 1391000 / 1150 | 1820000 / 1150 | 2262000 / 1150 | 910000 / 1150 |
| 4 | 1339000 / 1140 | 1755000 / 1140 | 2223000 / 1140 | 884000 / 1140 |
| 5 | 1274000 / 1130 | 1703000 / 1130 | 2158000 / 1130 | 845000 / 1130 |
| 6 | 1222000 / 1100 | 1625000 / 1100 | 2093000 / 1110 | 819000 / 1100 |
| 7 | 1118000 / 1070 | 1495000 / 1070 | 1885000 / 1080 | 754000 / 1070 |
| 8 | 1014000 / 1040 | 1352000 / 1040 | 1677000 / 1040 | 676000 / 1040 |
| 9 | 897000 / 1000 | 1209000 / 1000 | 1495000 / 1000 | 611000 / 1000 |
| 10 | 806000 / 970 | 1092000 / 970 | 1378000 / 980 | 533000 / 970 |
| 11 | 715000 / 940 | 962000 / 940 | 1131000 / 930 | 481000 / 940 |
| 12 | 624000 / 900 | 832000 / 900 | 1001000 / 900 | 416000 / 900 |
| 13 | 481000 / 850 | 650000 / 850 | 845000 / 880 | 325000 / 850 |
| 14 | 338000 / 800 | 468000 / 800 | 676000 / 850 | 234000 / 800 |
| 15 | 221000 / 770 | 325000 / 770 | 338000 / 800 | 169000 / 770 |

On this unit the TT-segment override replaces B index 0 with 2,587,000 kHz
(inheriting the 1.20 V base selector) and index 1 with 2,431,000 kHz at
1.18 V, before EEM adjusts them to the live values in section 4.2. The source also contains FY, M and L groups and the
1221 date-code variants; they are different speed bins and are not reproduced
here because the live unit does not select them.

## 5. Bring-up, idle, and hotplug behavior

### 5.1 A53 cores

CPU0 is the boot core. CPU1-3 (LL) and CPU4-7 (L) are brought online by generic
PSCI `CPU_ON` with the DT release address `0x40000200`. ATF contains the
CPUSYS0/1 cluster enable paths and owns the cluster MTCMOS and reset
sequencing. Mainline CPU0-7 serviceability is established; the exact A53
MTCMOS sequence has not been audited to the same depth as MP2.

### 5.2 A72 cores

CPU8/9 use the same PSCI conduit but add the external-preparation boundary in
section 3.3. The observed vendor CPU8 up path took about 6.0 ms and included
BUCKB 0->1, SPM reset/isolation readbacks, TOPRGU assert/deassert, matching
raw/mapped PSCI identities, secondary-online publication, DCM enable, and
stable secure sentinels. The down path took about 5.2 ms and observed the
online mask clear, BUCKB 1->0, DCM disable, restored SPM state, and an HPS-down
end. This is one vendor cycle, not a mainline provider or a safe inverse. See
the [first natural cycle](../../experiments/2026-08-02-gemian-a72-first-cycle-latch/README.md).

### 5.3 Idle states

The vendor DT describes two PSCI idle states for every CPU:

| State | PSCI suspend parameter | Entry / exit / residency |
| --- | --- | --- |
| Core power-down (bit 16 set; not retention) | `0x0010000` | 600 / 600 / 1200 us |
| Cluster power-down | `0x1010000` | 800 / 1000 / 2000 us |

The vendor kernel only ever requests `0x1010000`, and only after it has
kicked an SPM PCM program. The secure firmware treats both parameters as
power-down: it prepares the core (and the cluster, for the second), then waits
in an EL3 `wfi` loop until the SPM cuts power. Neither state is safe without
that program; see the
[power-management assessment](../../experiments/2026-11-06-gemini-power-management/README.md#the-firmware-side).

The vendor kernel additionally exposes `dpidle`, `soidle3`, `soidle`, `mcidle`
and `slidle` through its own idle driver. These depend on SPM/PCM firmware.
Mainline does not enable them; their PSCI suspend semantics and resume
behavior are unproven on this board. The firmware's suspend path, the A53
retention it already applies in WFI, and the vendor's program loading and
entry conditions are in [MT6797 SPM sleep](mt6797-spm-sleep.md). CPU hotplug
is separate from idle: HPS
offlines whole cores, while the idle states retain or power down clusters
without changing the online mask.

### 5.4 Vendor scheduler and hotplug policy

Gemian uses downstream HMP/HMP+, HPS, PPM, private DVFS and EEM, not EAS. The
live policy surfaces below are the kernel defaults; the normal Android init
does not write them, while the scenario table in section 5.6 can override
them at runtime.

- HPS enabled, up threshold 95%, three samples; down threshold 85%, one
  sample; heavy-task and rush boost enabled; input boost 2 CPUs; suspend
  handling enabled.
- PPM enabled in `Performance` mode with three cluster roots and HICA states
  `LL_ONLY`, `L_ONLY`, `4LL_L`, `4L_LL`.
- HPS obtains cluster masks through `arch_get_cluster_cpus()`, so its
  `0-3`, `4-7`, `8-9` model follows the DT topology rather than hard-coded
  logical ranges.
- HPS advances its local per-cluster count even when `cpu_up()` fails, so its
  tuples are policy evidence, not proof of completion.

The vendor boot line contains `maxcpus=5`, but `possible`/`present` stay
`0-9`; the online mask moved naturally from `4-5` to `0-1` to CPU0 alone in a
read-only capture. This is HPS policy, not a topology limit.

### 5.5 Cluster activation and frequency scaling are separate decisions

The cleanest way to read the vendor stack is:

```
load / TLP / heavy-task data
        |
        +--> PPM + HICA: per-cluster OPP limits and preferred cluster state
        |        |
        |        +--> mt_cpufreq: CPUHVFS/PCM, or manual PLL + rail sequence
        |
        +--> HPS: total target core count -> per-cluster target core count
                 |
                 +--> cpu_up()/cpu_down() -> generic hotplug -> PSCI
                          |
                          +--> ATF: cluster/core power, reset, CCI
                          +--> mt_cpufreq notifier: first/last CPU OPP handling
                          +--> CPUHVFS cluster-on/off notification
```

**Cluster activation (HPS).** HPS computes one system-wide target core count
from load and policy, then distributes it root-cluster first and fills the
remaining clusters in order, respecting each cluster's base and limit. It runs
a power-up pass before a power-down pass; within a cluster it brings up the
lowest-numbered offline CPU first and takes down the highest-numbered online
CPU first. The root cluster is forced to keep at least one CPU. The big
cluster is forced to zero when the efuse/heavy-task condition disables it.

HPS does not power a cluster directly. A cluster becomes active when its first
CPU passes generic `cpu_up()`; it powers down when its last CPU passes
`cpu_down()`. PSCI and ATF perform the hardware power/reset/CCI work. The
cpufreq notifier observes the cluster boundary: first CPU online establishes a
valid/boost OPP, last CPU offline drops LL/L to the minimum OPP, and the B
cluster is left to its secure/iDVFS handling. CPUHVFS is also notified at
cluster off/on so the PCM does not run a transition against a cluster that is
entering or leaving power-down.

**Frequency scaling (PPM + mt-cpufreq).** PPM/HICA owns the per-cluster OPP
limits and the preferred cluster usage state (`LL_ONLY`, `L_ONLY`, `4LL_L`,
`4L_LL`). HPS feeds it load/TLP data and calls `mt_ppm_main()` before the
hotplug action. `mt_cpufreq` then applies the resulting OPP through CPUHVFS or
the manual path, with EEM-calibrated voltages. HPS never writes a PLL or a
regulator, and PPM never calls `cpu_up()`/`cpu_down()`.

This split explains the observed behavior: the system can collapse to CPU0 at
idle through HPS while PPM independently keeps CPU0 at the lowest OPP, and it
can raise frequency on the currently online cluster without bringing another
cluster online. It also means a mainline implementation can adopt a standard
governor for frequency before implementing any HPS-like hotplug policy.

The offline reconstruction in the
[vendor CPU policy experiment](../../experiments/2026-10-31-mt6797-vendor-cpu-policy-re/results/ppm-hica-model.md)
now fixes the state limits and transition rules:

| State | LL | L | B |
| --- | --- | --- | --- |
| `LL_ONLY` | 1-4 cores, full range | 0 cores | 0 cores |
| `L_ONLY` | 0 cores | 1-4 cores, min 1.352 GHz | 0 cores |
| `4LL_L` | 1-4 cores | 0-4 cores | 0-2 cores, max 1.5 GHz |
| `4L_LL` | 0-4 cores | 1-4 cores | 0-2 cores, max 1.5 GHz |

The main transitions use load > 380, TLP 400, a 20-point delta, four-sample
holds, and an eight-sample LL-maximum hold for `LL_ONLY -> L_ONLY`. Heavy-task
input can override the load branch. This is the policy mechanism; the runtime
trajectory under a specific workload is still not traced.

### 5.6 On-device policy configuration

The vendor stack is not configured by one file. The effective order is:

```text
LK command line (maxcpus=5)
  -> kernel defaults (PPM Performance, HPS 95/85, EEM tables)
  -> /vendor/etc/perfservscntbl.txt (scenario core/freq/HPS overrides)
  -> /vendor/etc/perfservapplist.txt (per-app minimums)
  -> /vendor/etc/.tp/thermal.conf (trips/coolers -> PPM power budget)
  -> cpusets in /init.mt6797.rc
```

| File | Role |
| --- | --- |
| `/init.mt6797.rc` | Cpuset assignment and proc/sysfs permissions; does not set HPS/PPM values |
| `/vendor/etc/perfservscntbl.txt` | Scenario minimum cores/frequencies, HPS thresholds, root cluster, PPM big limit, VCORE |
| `/vendor/etc/perfservapplist.txt` | Per-app CPU minimum |
| `/vendor/etc/.tp/thermal.conf` | CPU trip at 110 C reset, adaptive coolers at 58/57 C |
| `/vendor/etc/.tp/.thermal_policy_00..03` | Alternative thermal policy sets |
| `/meta_init.project.rc`, `/factory_init.project.rc` | Disable HPS and force CPU0-1 online for meta/factory modes |

These are vendor/Android filesystem paths used by the Android LXC that Gemian
runs for hardware support. The audited native Debian side has no equivalent
CPU-policy files; its `repowerd` only exposes display/suspend and a
performance-booster scenario hook.

The normal cpusets are:

```text
foreground          0,2-9
foreground/boost    0,2-9
background          0,2-3
system-background   0,2-7
top-app             0-9
```

The scenario table is the main runtime policy. Examples:

| Scenario | Minimums / overrides |
| --- | --- |
| Touch, frame update | 3 cores, 1.287 GHz; frame update HPS up 80/down 65 |
| App switch | cluster0 0 cores / 2.0 GHz; cluster1 4 / 2.5 GHz; cluster2 3.0 GHz; VCORE 3 |
| Package/process/game launch | cluster1 4 / 2.5 GHz; cluster2 2 / 3.0 GHz; PPM big limit 0 |
| Gallery boost | cluster1 2 / 2.5 GHz; cluster2 2 / 3.0 GHz |
| Gaming | rush/heavy boost off; HPS up 80/down 70; root cluster 0; cluster2 max cores 0 |

The 2.5/3.0 GHz requests exceed the live L/B tables and are clamped by PPM.
The thermal layer produces cooler actions and PPM power budgets, not direct
frequency writes. Meta/factory modes are the only files that set an explicit
CPU online mask (CPU0-1); normal boot leaves the mask to HPS.

None of the audited userspace files or the public device-tree init rules
mentions `idvfs`/`dvt_test`; the iDVFS enable/disable trigger is not in that
set. See
[userspace candidates](../../experiments/2026-10-31-mt6797-vendor-cpu-policy-re/results/userspace-candidates.md)
and [thermal management](mt6797-thermal-management.md#7-userspace-policy-android).

## 6. Current mainline state

| Area | State | Evidence |
| --- | --- | --- |
| CPU0-7 A53 serviceability | Online and accounting on the current baseline; not full CPU support (no cpufreq, idle, thermal, or coherency stress) | [A53 sweep](../../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md) |
| Three-cluster `cpu-map` | Implemented by canonical patch `0482`; live 4+4+2 topology and dual-A72 RAM integrity pass | [Topology result](../../experiments/2026-09-02-mainline-mt6797-cpu-map/README.md) |
| CPU8/9 admission | Experimental, fail-closed by default; both cores online, exact affinity, accounting, CPU9 down/restore, and bounded RAM integrity demonstrated | [Lifecycle gate](../../experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/README.md) |
| CPU8/9 on the station | Opt-in `mt6797-a53-station-a72` profile: both online from a module on two boots, correct hashes over 25 min beside Wi-Fi and audio traffic, firmware's fixed 750 MHz. Not default, loaded by hand, all ten CPUs not loaded at once | [All ten cores](../../experiments/2026-11-01-mt6797-all-cores/README.md) |
| A72 frequency/thermal observation | Read-only observer proved LL 897 MHz, L 1274 MHz, B 750 MHz, CCI 629.5 MHz and ~53.5 C across one bounded run; the thermal comparison was later rejected on a separate boot | [Frequency pass](../../experiments/2026-09-04-mt6797-a72-frequency-observation/results/zero-divider-runtime-pass-20260904.txt), [thermal rejection](../../experiments/2026-09-04-mt6797-a72-frequency-observation/results/cold-rise-runtime-thermal-rejected.txt) |
| CPU clock backend | Read-only MCUMIXED owner and protected-clock/BigiDVFS backends bind; no writable OPP or cpufreq | [Live resource map](mt6797-live-resource-map.md#cpu-dvfs-thermal-idle-and-suspend) |
| DA921x | Two read-only providers bind; one same-value write/readback proved; no active rail or rollback | [DA921x boundary](da921x-i2c6-a72.md) |
| Idle, suspend, cpufreq/OPP, CPU cooling | Not implemented. Thermal trips exist on the station, shown armed only | [Support matrix](../HARDWARE_SUPPORT.md) |

Mainline deliberately does not copy the vendor HMP/HPS/PPM policy. The durable
transferable items are the core/cluster topology, the firmware ownership split,
and the rail/clock register map. Static capacity, OPP, energy-model, idle and
thermal values must come from measured mainline contracts, not from the vendor
tables above.

### 6.1 Can a standard Linux governor drive CPU frequency?

Not with the current package. The A53 runtime profiles explicitly disable
`CONFIG_CPU_FREQ` and `CONFIG_CPU_IDLE`; the legacy `full` profile inherits
`CONFIG_CPU_FREQ=y` and `CONFIG_ARM_MEDIATEK_CPUFREQ=y` from arm64 defconfig,
but the MT6797 has no matching CPU clock/OPP provider, so no policy appears.
The governor is not the missing piece; the provider stack is.

A standard `schedutil`, `ondemand`, or `performance` governor can drive these
clusters once the following exist:

| Requirement | Current state |
| --- | --- |
| Writable per-cluster clock provider | Missing; only a read-only MCUMIXED owner exists |
| OPP tables from calibrated data | Missing; vendor tables are not an upstream contract |
| `regulator_set_voltage()` for VPROC1/VPROC2 | Missing; DA921x is read-only apart from one same-value probe |
| VSRAM tracking and CCI coupling | Missing; needs coupled regulators or a custom `target_index` |
| A72 BigiDVFS clock backend | Missing; needs a reviewed SMCCC interface |
| Thermal cooling device and calibrated trips | Missing |
| `CONFIG_CPU_FREQ` and an energy model | Disabled in A53 runtime profiles; inherited but unusable in the legacy `full` profile |

Two useful boundaries:

- HPS is **not** required for frequency scaling. A standard governor only
  selects an OPP for online CPUs; core hotplug is a separate policy. Keeping
  CPU0-7 online with `schedutil` is a valid intermediate target.
- The vendor HMP/PPM policy must not be ported as governor data. The standard
  framework can use the topology and measured OPPs, but the vendor capacities,
  HICA states, and HPS thresholds are not mainline inputs.

A defensible order is: prove MCUMIXED/DVFSP ownership, add LL/L/CCI clocks,
add a static per-unit OPP table, add the regulator and VSRAM/CCI tracking, then
enable a standard governor. B-cluster frequency remains a separate secure
backend and should not block A53 scaling. This is a design boundary, not an
implemented feature.

The first step is in the [A53 cpufreq experiment](../../experiments/2026-11-07-mt6797-a53-cpufreq/README.md):
an LL/L clock provider that follows the vendor sequence of section 3.7, and
cpufreq-dt with schedutil over the vendor points that need no more than the
firmware's 1.00 V, with no regulator or CCI change. It passed on one boot
from modules loaded by hand
([A3](../../experiments/2026-11-07-mt6797-a53-cpufreq/README.md#attempt-a3-2026-11-07)).

## 7. Gap register

### Closed by this consolidation

| Gap | Resolution |
| --- | --- |
| Which regulator supplies the A72 cluster? | DA9214 BUCKB (`0xd9`, VPROC2), enabled at `0x5e[0]`; BUCKA (`0xd7`, VPROC1) supplies LL/L/CCI |
| Do all A53 clusters share a rail? | Yes, LL/L/CCI share VPROC1 and VSRAM_L |
| Does the SCP control application CPUs? | No; its DVFS is local plus IPI/SPM services |
| Does LK always pass all ten CPU nodes? | No; it prunes from efuse and clamps `clock-frequency` |
| Which firmware owns B PLL/MTCMOS/reset/CCI? | ATF/PSCI, not Linux and not SCP |
| What is the vendor "CPU firmware"? | CSPM PCM in CSRAM; the built image is `pcm_dvfs_v0.1_160131_02`, not SCP code |
| How does PPM/HICA choose cluster states and limits? | Full offline reconstruction: policy order, state limits, thresholds, holds and client callbacks |
| What is the PCM vs iDVFS split? | Layered, not alternative: PCM sequences OPP/frequency/coarse voltage; ATF/iDVFS owns the B secure PLL/SRAM and adaptive loop |
| Which on-device files set CPU policy? | `perfservscntbl.txt` for scenarios, `perfservapplist.txt` per app, `thermal.conf` for trips/coolers, `init.mt6797.rc` for cpusets; meta/factory override HPS and the online mask |
| Why does mainline keep CPU8/9 offline by default? | The external rail/isolation sequence has no proven safe inverse and the secure path is not represented in mainline |

### Still open

| Gap | Why it matters | Discriminating evidence needed |
| --- | --- | --- |
| Raw efuse words for this unit | The exact function/date/speed-bin values are inferred from selected tables | One read-only `atag,devinfo` dump (indices 3, 8, 22, 61) |
| Physical rail voltages and currents | Software selectors are not a measurement; BUCKA/BUCKB load mapping is inferred | Board-level measurement during a controlled transition |
| Exact preloader CPU/PLL register sequence | Only strings and outcomes are established; the offline pass could not fix the load map/xrefs | Dedicated loader-format study with a confirmed load base |
| A53 cluster MTCMOS sequence | Strings and dispatcher shape are known; the exact CPUSYS0/1 sequence is not decoded | Full ATF dispatcher audit plus synchronized A53 hotplug observation |
| Safe A72 CPU_OFF and rollback beyond isolation clear | Vendor inverse is incomplete | Reviewed provider with transaction-local pre-state and readback |
| B PLL/mux/divider cross-boot stability | One bounded sample only | Repeated read-only snapshots across cold boots |
| External iDVFS enable/disable trigger | In-tree call sites are `#if 0`; the selected 721-file userspace corpus and device-tree init rules contain no `idvfs`/`dvt_test` reference | Read-only process and `/etc`/`/usr` inspection around one natural B transition |
| Cycle-accurate PCM/iDVFS arbitration on B | Both layers can touch the B PLL/rail in one transition | Read-only trace of PCM status, iDVFS registers, BUCKB and SRAM-LDO |
| Runtime HICA trajectory | State limits and rules are known; the historical sequence under load is not | Read-only load/TLP/state sampling |
| cpufreq/OPP, idle, suspend, CPU cooling | No mainline policy exists | Separate measured provider and thermal acceptance gates |
| General hotplug, coherency stress, longer A72 load | Only bounded experiments exist | New experiment admission; do not repeat identical artifacts |

## 8. Implementation constraints

- Do not copy vendor HMP/HPS/PPM/EEM policy into mainline; use standard
  scheduler, cpufreq, OPP, idle, and thermal frameworks once their providers
  exist.
- Do not write ATF-owned B PLL, cluster/per-core MTCMOS, core reset, or CCI
  snoop registers from Linux.
- Keep one owner for MCUMIXED and CSPM, and honor the DVFSP semaphore for any
  shared clock access.
- Treat VPROC1, VPROC2, VSRAM_L and VSRAM_B as separate rails with their own
  enable, voltage, readback and rollback contracts.
- Keep DA921x consumers and CPU8/9 disconnected until the explicit rail and
  admission gates pass.
- Preserve console, keyboard, USB, CPU0-7, I2C5/AP-DMA, DVFSP handoff and
  reboot at every step.
- Any A72 write at or beyond external-isolation clear is one-way until a
  proven inverse exists; retain power, fault, do not retry, and rely on the
  independently proven watchdog/native-reset recovery.

## 9. Evidence index

- Vendor source equivalent: [Gemian Linux 3.18 `59e00a91`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467),
  especially
  [`mt6797.dtsi`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/arch/arm64/boot/dts/mt6797.dtsi),
  [`mt_cpufreq.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c),
  [`mt_idvfs.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c),
  [`mt_cpufreq_hybrid.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c),
  [`mt_cpufreq_hybrid_fw.h`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid_fw.h),
  [`mt_dcm.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_dcm.c),
  [`mt_eem.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_eem.c),
  [`mt_idle_mt6797.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/spm_v2/mt_idle_mt6797.c),
  [`mt_hotplug_strategy_main.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_main.c),
  and [`psci.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/arch/arm64/kernel/psci.c).
- Planet LK [`atags.c`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/atags.c).
- Planet device tree `planet-community/android_device_planetcom_geminipda`
  commit `8f7cd432`: `rootdir/init.mt6797.rc`, `rootdir/meta_init.project.rc`,
  `rootdir/factory_init.project.rc`, `configs/.tp/thermal.conf`.
- Planet vendor tree `planet-community/android_vendor_planetcom_geminipda`
  branch `cm-14.1`: `vendor/etc/perfservscntbl.txt` and
  `vendor/etc/perfservapplist.txt`.
- [Gemian CPU and scheduler policy](../../experiments/2026-07-21-gemian-cpu-scheduler-policy/README.md)
  and its private capture summary.
- [Vendor CPU policy and PCM/iDVFS offline reconstruction](../../experiments/2026-10-31-mt6797-vendor-cpu-policy-re/README.md).
- [A72 firmware and power contract](../../experiments/2026-07-22-a72-firmware-power-contract/README.md).
- [Secure CPU-off attribution](../../experiments/2026-08-05-a72-secure-cpu-off-attribution/README.md).
- [First natural CPU8 cycle](../../experiments/2026-08-02-gemian-a72-first-cycle-latch/README.md).
- [CPU8/9 target-register capture](../../experiments/2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt).
- [Three-cluster topology and dual-A72 RAM integrity](../../experiments/2026-09-02-mainline-mt6797-cpu-map/README.md).
- [A72 hotplug lifecycle gate](../../experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/README.md).
- [A72 frequency observation](../../experiments/2026-09-04-mt6797-a72-frequency-observation/README.md).
- [LK CPU clock iterator repair](../../experiments/2026-08-17-mainline-lk-cpu-clock-iterator-repair/README.md).
- [A53 sweep](../../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md).
- [MT6797 live resource map](mt6797-live-resource-map.md).
- [MT6797 thermal management](mt6797-thermal-management.md).
- [DA921x, I2C6, and Cortex-A72](da921x-i2c6-a72.md).
- [Firmware boundary](firmware.md).
