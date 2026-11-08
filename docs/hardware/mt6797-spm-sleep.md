# MT6797 SPM sleep: firmware, programs and vendor entry

Scope: how the vendor stack takes the MT6797 below WFI. It covers the secure
firmware's suspend path, the A53 retention it already applies, the SPM's PCM
programs and how the vendor kernel loads and runs them, and the entry
conditions of deep idle, SODI and SODI3. The decisions built on it, and the
proposed Route A stages, are in the
[cpuidle record](../../experiments/2026-11-07-mt6797-cpuidle/README.md#the-vendor-sequence-reverse-engineered-2026-11-08).

None of this is mainline support. No SPM program has run on mainline.

| Field | Value |
| --- | --- |
| Device | Named Gemini PDA development unit (MT6797X) |
| Last verified | 2026-11-08 (static analysis; no device access) |
| Secure firmware | The unit's `tee1`, TF-A `v1.0(debug):df3e3f8`, disassembled privately in the RE VM |
| SPM programs | The unit's Gemian `system.img`, `/vendor/firmware/pcm_*.bin`, analysed privately |
| Vendor source | Gemian Linux 3.18 [`59e00a91`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467), `drivers/misc/mediatek/base/power/` (`spm_v2/`, `include/spm_v2/`, `cpuidle_v1/`), read as evidence only |
| PCM decoder | The public, GPL [mt8173-pcm-tools](https://git.paulk.fr/mt8173-pcm/mt8173-pcm-tools.git) by Paul Kocialkowski; it decodes part of the instruction set |

Vendor-source statements are what the vendor code does, not measurements.
"Observed" below means seen in the binaries or in a recorded device read;
"inferred" means reasoned from them.

## 1. The secure firmware's suspend path

The platform power operations table of `tee1` has the usual TF-A v1.0 shape:
standby, on, off, suspend, on-finish, suspend-finish, system off and reset.
**Observed** in the suspend handler, for a power-down `CPU_SUSPEND`:

1. A platform check returns early unless the request is a power-down at the
   highest affinity level that is actually going off.
2. MCUCFG `MP0_MISC_CONFIG3` (`0x1022003c`) bit 12 is set. That is the
   AArch64 reset-state bit for **cluster 0 core 0** only.
3. The core's `CPUECTLR_EL1` (`S3_1_C15_C2_1`) retention field, bits 2:0, is
   cleared, and the core's "SPARK" retention is switched off (see §2).
4. It spins, unbounded, until the core's bit in SPM `CPU_RET_STATUS`
   (`0x100061e4`) clears, that is until the core has left retention. For a
   running core this is immediate.
5. It programs the warm-boot entry point.
6. For a cluster-level request (`0x1010000`, with the rest of the cluster
   already off): GIC CPU interface off, cluster out of CCI coherency, some
   context saved, and MCUCFG `MP0_CACHE_CONFIG` (`0x10220000`) bit 4
   (`L2RSTDISABLE`) cleared so the L2 resets. Only the cluster 0 register is
   written.

Then the generic PSCI code flushes and waits in `dsb; wfi` forever. The
suspend handler writes **no** SPM register. Suspend-finish undoes steps 3 and
6 and re-enables retention.

**Inferred:**

- The power cut and the wake are entirely the SPM program's job. Without a
  running program that powers the core off on WFI and back on at a wake, the
  core never leaves EL3.
- Only CPU0 can usefully suspend. Steps 2 and 6 handle core 0 of cluster 0
  and nothing else, although the vendor ships `_by_mp1` programs for CPU4.
- There is no per-core (MCDI-like) or cluster-off idle path that works
  without the SPM, and no SiP call for SPM, sleep or wake sources. This
  confirms the earlier pass. A standby `CPU_SUSPEND` is a plain `wfi` in EL3.

**Correction to earlier text.** The firmware does write SPM `PWR_CON`
registers, in its `CPU_ON` power-up sequence (`MP0_CPUn_PWR_CON` and the
cluster words) and in the `CPU_OFF` teardown. The
[power-management record](../../experiments/2026-11-06-gemini-power-management/README.md#the-firmware-side)'s
"nothing in the secure firmware writes an MTCMOS or SPM power control" holds
for suspend only.

## 2. A53 retention ("SPARK") is already on for CPU1-7

**Observed in `tee1`:**

- Every A53 that `CPU_ON` powers up ends with SPARK enabled. The firmware
  sets the core's LDO retention field (6 bits per core, set to `0x3f`) in
  MCUCFG `0x10221c00` (cluster 0) or `0x10223c00` (cluster 1), then the core's
  enable bit in `0x10221c04` or `0x10223c04`.
- The on-finish handler sets `CPUECTLR_EL1` retention to 1, so the core
  enters retention after a short time in WFI.
- `CPU_OFF` and the suspend handler clear both.

**Inferred:** on the mainline station, CPU1-7 already drop into hardware
retention in WFI. CPU0, which no `CPU_ON` brought up, probably does not. The
C0 reads fit this: `CPU_RET_STATUS` read `0x000000F6` (cores 1, 2 and 4-7)
while `CPU_IDLE_STA` showed seven A53s in WFI and one running. If CPU3 ran
the read, CPU0 sat in WFI without retention. The reads that would settle it
are proposed as stage S0 in the record.

Consequence: per-core power-down would save less over WFI than a plain-WFI
comparison suggests, because idle A53s are already retained.

## 3. The SPM program files

The vendor kernel loads nine programs with `request_firmware` (names from
`mt_spm.c`, MT6797 branch). On the unit they are in Gemian's `system.img`
under `/vendor/firmware/`, next to the Wi-Fi files
[`firmware-get`](firmware.md#getting-them-from-the-owners-own-device) already
reads:

| File | Bytes | Code words | SHA-256 |
| --- | --- | --- | --- |
| `pcm_suspend.bin` | 7,378 | 1,822 | `d6e8a0b8851e78e95891c995605ffbf210eade56583b14cf6b4a67e7d770f4e0` |
| `pcm_suspend_by_mp1.bin` | 7,382 | 1,822 | `f8b9e333423d5d051302072cb853d50ab4e13a8528b407b9efdc92fe28648807` |
| `pcm_deepidle.bin` | 6,723 | 1,657 | `e9066110b607379cd73560804bf195f2cd9ea1e799f130f5638c09c446eedcd8` |
| `pcm_deepidle_by_mp1.bin` | 6,727 | 1,657 | `36267de8a55699de516d61b1d9e64591a2b7d4f187d3460cfa93c81b3e1e4cf6` |
| `pcm_sodi.bin` | 6,423 | 1,583 | `dda8cca1e110d57137afb8ef4957da758c19d38db45ea2bb30bc7133cc122ae4` |
| `pcm_sodi_by_mp1.bin` | 6,427 | 1,583 | `8649d6db309753fd017bcd778568e093af623bc0f4acc2a20efa8c8d4c775ffd` |
| `pcm_vcorefs_lpm.bin` | 8,261 | 2,037 | `b756fb01239ea5d857d01e0516a86a12b41ddf4fa04006297fef93e6b1a4c3c3` |
| `pcm_vcorefs_hpm.bin` | 8,085 | 1,993 | `c0f676003ffa69341402f29a58a1d1d753fd1035d3a52f5cc7306f305412e584` |
| `pcm_vcorefs_ultra.bin` | 8,087 | 1,993 | `a52ea060d30110a52c18d31ab70b3b9600c90d67287a1acb83ebbd41c1966730` |

These are hashes of one unit's files, as in [firmware.md](firmware.md). The
files are proprietary MediaTek firmware and are not redistributed.

**Format (observed, and matching the loader in `mt_spm.c`):** a 16-bit word
count `n`; `n` 32-bit PCM instructions; a descriptor of `u16 size, u8 sess,
u8 replace, u16 addr_2nd, u16 reserved` and sixteen 32-bit event vectors;
then a NUL-terminated version string. Every file has `size = n`, `sess = 2`,
`replace = 0` and `addr_2nd = 0`. The six sleep programs carry twelve
non-zero event vectors. The three VCORE-DVFS programs carry none: they are
the resident DVFS program, not sleep programs.

**What each sleep program touches (observed, from address-shaped constants
in the code; a static scan, not an execution trace):**

| Block | `suspend` | `deepidle` | `sodi` |
| --- | --- | --- | --- |
| SPM CPU power: `MCUSYS_PWR_CON` `0x200`, `MP_TOP_PWR_CON` `0x204`, `CPU_EXT_BUCK_ISO` `0x290`, `CPU_PWR_STATUS(_2ND)` | yes | yes | yes |
| Cluster `MP0/MP1_CPUSYS_PWR_CON` `0x210`/`0x214` | both | both | the online CPU's own only |
| Core `MP0_CPU0_PWR_CON` `0x220` (`_by_mp1`: `MP1_CPU0_PWR_CON` `0x230`) | yes | yes | yes |
| DRAM PHY `DPY_PWR_CON` `0x31c`, `DPY_CH1_PWR_CON` `0x3b8` | yes | yes | yes |
| Infra `IFR_PWR_CON` `0x318` | yes | no | no |
| `SYSRAM_CON`/`SYSROM_CON` `0x350`/`0x354` | yes | yes | no |
| Mailboxes and status (`SPM_SW_FLAG`, `SPM_SW_RSV_*`, `SPM_BSI_D*_SR`, `PCM_TIMER_OUT`, wake status) | yes | yes | yes |
| INFRACFG_AO: `INFRA_TOPAXI_PROTECTEN` `0x10001220`, clock gates `0x10001080`-`0x1000108c`, `0x100010a4`-`0x100010ac` | yes | partly (no `0x88`/`0x8c`) | `0xa8`/`0xac` only |
| TOPCKGEN `0x10000004`, `0x10000044`, `0x10000048` and APMIXED `0x1000cf38`, `0x1000cf4c` | yes | yes | yes |

Each program powers exactly one core, CPU0, or CPU4 in the `_by_mp1` file.
The vendor picks the file by `cpu / 4` of the one online CPU, and requires
`cpu % 4 == 0` (§5). `CPU_EXT_BUCK_ISO` is the word the
[A72 module](mt6797-cpu-clusters.md#33-a72-external-preparation-and-mp2-control)
clears before CPU8 returns, so any SPM sleep leaves the A72 cluster needing
that preparation again. `INFRA_TOPAXI_PROTECTEN` is also written by mainline
SCPSYS.

**What the flags turn off** (`sleep_def_mt6797.h`, `SPM_SW_FLAG`): bit 0
disables CPU power-down, bit 1 infra power-down, bit 2 DRAM PHY power-down,
bits 3 and 4 VCORE DVS and DFS, bit 5 DRAM deep power-down, bit 6 bus clock
off, bit 7 modem-infra power-down, bit 16 SYSRAM sleep, bit 18 the
"segment 2" variant, bit 19 the vendor's thermal-check bypass. By default the
programs gate the 26 MHz request (`SRCCLKENA`), put DRAM in self-refresh,
power the DRAM PHY down, lower VCORE through the PMIC wrapper and drop the
SoC's resource requests. The suspend program also powers infra down. What a
program does beyond the registers listed cannot be read without a full
decoder.

**Event vectors:** each non-zero vector packs a program address in bits
31:16, an "immediate" bit 7, a "resume" bit 6 and an event number in bits
5:0 (`EVENT_VEC` in `mt_spm_internal.h`). The kernel writes all sixteen to
`PCM_EVENT_VECTOR0`-`15` (`0x10006040`-`0x1000607c`); the program enables
them itself (`PCM_EVENT_VECTOR_EN`, `0x080`).

**The decoder.** The public PCM tools decode NOP, logic with immediate,
loads, stores, jumps, calls and returns; much of each MT6797 program is
outside that subset. Writing a new program is still not feasible.

## 4. How the vendor kernel loads and runs a program

**At boot** (`spm_register_init`): `POWERON_CONFIG_EN` (`0x000`) ←
`0x0b160001`; `SPM_POWER_ON_VAL1` (`0x008`) ← `0x00015820`; the PCM is reset
and left with `PCM_CON0` ← `0x0b16000c`, `PCM_CON1` ← key with event lock,
SRAM isolation, SRAM sleep and MIF APB enable; `PCM_IM_PTR`/`LEN` ← 0;
`SPM_CLK_CON` gets bits 2, 3, 6, 12, 16 and 27; the wake mask is set to its
default; IRQs are masked and cleared. Writes to `POWERON_CONFIG_EN`,
`PCM_CON0` and `PCM_CON1` carry the key `0x0b16` in bits 31:16. The files are copied into the
`mediatek,spm-reserve-memory` carveout, `0x2000` bytes per program, by index
(suspend, suspend MP1, three VCORE-DVFS, SODI, SODI MP1, deep idle, deep idle
MP1). The station DT reserves the same carveout.

**At each entry** (`spm_go_to_sleep`, `spm_go_to_dpidle`, `spm_go_to_sodi`),
on the last online CPU with interrupts off:

1. PMIC wrapper phase: the 16 command slots `DVFS_ADRn`/`DVFS_WDATAn` at
   `0x1000d10c + 8n`/`0x1000d110 + 8n` get the phase table (§6).
2. Mask every GIC interrupt except the SPM's (SPI 180, level low); clone
   edge-triggered ones into SYS_CIRQ (`0x10204000`, SPI 72-291).
3. `__spm_reset_and_init_pcm`: reset the PCM (`PCM_CON0` ← `0x0b168004`,
   wait for `PCM_FSM_STA & 0x7fffff == 0x48490`, then `0x0b160004`,
   `0x0b16000c`); program `PCM_CON1`; clear software interrupt 0.
4. `__spm_kick_im_to_fetch`: `PCM_IM_PTR` ← the program's physical address,
   `PCM_IM_LEN` ← `size - 1`, then pulse `IM_KICK` (bit 1) in `PCM_CON0`. The
   instruction memory fetches the program from DRAM. With 4 GB mode on
   (INFRACFG_AO `0x10001f00` bit 13), an address in
   `0x40000000`-`0xbfffffff` is given to the SPM plus `0x40000000`.
5. `__spm_init_pcm_register`: copy `SPM_POWER_ON_VAL0` and `_VAL1` into the
   PCM's `r0` and `r7` through `PCM_REG_DATA_INI` and a pulse of
   `PCM_PWR_IO_EN` bits 16 and 23.
6. The sixteen event vectors.
7. `__spm_set_power_control` from the scenario's `pwr_ctrl`:
   `SPM_AP_STANDBY_CON` (`0x014`), `SPM_SRC_REQ` (`0x0b8`), `SPM_SRC_MASK`
   (`0x0bc`), `SPM_SRC2_MASK` (`0x0c0`), `SPM_CLK_CON` bit 6, and every
   `WFI_EN` word (`0x540`-`0x55c` for the A53s, `0x560`/`0x564` for the A72s)
   set to 1.
8. `__spm_set_wakeup_event`: `PCM_TIMER_VAL` (32 kHz ticks), timer enable in
   `PCM_CON1`, `SPM_WAKEUP_EVENT_MASK` ← the complement of the wake sources,
   `SPM_IRQ_MASK` so that only the PCM-return interrupt reaches the GIC.
9. `__spm_kick_pcm_to_run`: both pause masks ← `0xffffffff`;
   `PCM_REG_DATA_INI` ← 0; `SPM_SW_FLAG` ← flags; `SPM_SW_RSV_0` ← scenario
   data; infra DCM lock (`SPM_CLK_CON` bit 5); `PCM_PWR_IO_EN` ← `r0`/`r7`
   enables (`0x81`); pulse `PCM_KICK` (bit 0) in `PCM_CON0`.
10. The CPU goes down (§5.1), the program runs, and a wake event ends it. The
    program raises the PCM-return interrupt, which wakes the CPU.
11. Read the wake status (`SPM_SW_RSV_0` as `r12`, `SPM_WAKEUP_STA`,
    `PCM_REG13_DATA`, the BSI words); clear (`SPM_CPU_WAKEUP_EVENT` ← 0, wake
    mask ← all ones, IRQ mask and status, software interrupts); replay CIRQ;
    restore the GIC masks and the PMIC wrapper phase.
12. On MT6797 the vendor then re-kicks the same program with
    `RUN_COMMON_SCENARIO` so it continues as the resident VCORE-DVFS program.
    Mainline runs no resident program, so a mainline loader would instead
    reset the PCM back to its boot state.

### 4.1 The two ways the CPU can go down

`spm_trigger_wfi_for_sleep` and `spm_trigger_wfi_for_dpidle` branch on flag
bit 0:

- **CPU power-down (the vendor default):** `mt_cpu_dormant()` saves the core
  timer and context and calls `cpu_suspend(2)`, which is PSCI `CPU_SUSPEND`
  `0x1010000`. The firmware does §1 and waits in `wfi`. The program powers
  the core and cluster off, and on a wake powers them on; the core restarts
  at the warm-boot entry.
- **CPU stays powered (`SPM_FLAG_DIS_CPU_PDN`):** the kernel sets `ACINACTM`
  (bit 4) in `MP0_AXI_CONFIG` (`0x1022002c`) and `MP1_AXI_CONFIG`
  (`0x1022022c`), and `0x11` in `MP2_AXI_CONFIG` (`0x1022220c`). The deep-idle
  file does this through the SiP register write `0xc200035e`; the suspend file
  writes the words directly. It executes `wfi` at EL1, then restores the three
  words. No PSCI call is made. The vendor used this for FPGA bring-up
  and keeps it as a `LEGACY_SLEEP` build option for deep idle. That the
  programs implement it is inferred from those code paths; it has not been
  seen to work on silicon.

### 4.2 What Linux must leave the SPM in

| Path | Required state before the CPU goes down | If it is missing |
| --- | --- | --- |
| `CPU_SUSPEND` `0x0010000` (core) | A running program that powers that one core off on WFI while others run | None exists for MT6797 (the MCDI program targets another SPM map), so the core stays in EL3 for good |
| `CPU_SUSPEND` `0x1010000` (cluster) on CPU0 with CPU1-9 off | The suspend, deep-idle or SODI program loaded and kicked, `WFI_EN` set for CPU0, flag bit 0 clear, wake mask set, the PCM-return interrupt unmasked, `PCM_PWR_IO_EN` `0x81` | CPU0 stays in EL3 for good; only a force-off recovers |
| `wfi` at EL1 with flag bit 0 set | The same, with flag bit 0 set and `ACINACTM` set on the three clusters | If the program never returns, CPU0 sits in WFI with every other interrupt masked: a hang, recovered by force-off |
| Plain WFI, today | The PCM idle | — |

The C0 reads already show the PCM idle on mainline: `PCM_FSM_STA` read
`0x02848490`, whose low 23 bits are the vendor's reset value `0x48490`;
`PCM_CON0` held only the clock enable; `PCM_IM_PTR` and every `WFI_EN` were 0.

## 5. Vendor entry conditions

### 5.1 Common

- Exactly one CPU online, and it is CPU0 or CPU4. `num_online_cpus() == 1`
  and `cpu % 4 == 0`. Hotplug must not be in progress.
- The program files are loaded.
- No connectivity lock (`idle_conn_lock`) and no SPM user (`idle_spm_lock`,
  VCORE-DVFS in progress).
- Next timer far enough away: deep idle and SODI 2 ms, SODI3 5 ms. The local
  timer's remaining time is copied into APXGPT GPT4 (`0x10008000`, SPI 169)
  before entry, so the APXGPT wake (`R12` bit 4) fires the tick. After the
  wake the local timer is reprogrammed with what was left.

### 5.2 Per state (`mt_idle.c`, `mt_idle_mt6797.c`)

| Condition | Deep idle | SODI | SODI3 |
| --- | --- | --- | --- |
| Display power domain (`PWR_STATUS` bit 3) | off | may be on (command-mode panels need it off) | may be on |
| ISP, VDEC, VENC, MFG, MJC domains | off | off | off |
| Display clocks (`DISP0`, `DISP1` groups) | all off | the listed ones off | the listed ones off |
| Display PWM on the low-power oscillator (TOPCKGEN `0x10000050` bits 2:1 non-zero) | — | — | required |
| UNIVPLL and MSDCPLL | — | — | off |
| Infra gates off, `INFRA_SW_CG_1_STA` (`0x10001094`) | SPI0, CPUM, DISP_PWM, AP_DMA, L2C_SRAM | SPI0, CPUM, AP_DMA, L2C_SRAM | as SODI, plus the audio bus clock |
| Infra gates off, `INFRA_SW_CG_0_STA` (`0x10001090`) | ICUSB, I2C0-3, PWM_HCLK, PWM1-4, PWM, UART1-3 | same | same |
| Infra gates off, `INFRA_SW_CG_2_STA` (`0x100010b0`) | I2C4, I2C_GPUPM, the I2C2/I2C3 IMM and arbiter gates, I2C5, SSUSB_REF, SPI1, ANC_MD32 (both), AES_TOP1, SSUSB_BUS, SPI2-5, IR TX, SSUSB_SYS, VAD wrapper | same | same, plus bits 26 and 27 (the audio 26 MHz gates) |
| `I2C_APPM` gate | off | off | off |
| MSDC clocks (the vendor's SD status) | off | off | off |
| UART0 | allowed; the kernel hands it to the SPM before entry | same | same |
| Uptime | — | — | over 30 s |

The vendor masks call these registers `INFRA0`/`INFRA1`/`INFRA2` with
`INFRA0` at `0x94`. The names above are mainline `clk-mt6797` names, matched
by register and bit.

**Suspend** checks none of this. The vendor's `mem` suspend enters with
CPU0 alone (`cpu / 4` picks the file) and lets the program gate what is
gateable, with the masks in §6 deciding which outside requests it honours.

### 5.3 Which conditions a mainline station can meet

| Condition | Mainline station | Evidence |
| --- | --- | --- |
| One CPU online, CPU0 | **Met for suspend:** `mem` suspend takes CPU1-9 offline itself. **Met while dark:** `backlight-policy` leaves only CPU0 | Kernel behaviour; [P2f](../../experiments/2026-11-06-gemini-power-management/README.md) |
| Program files | Present in the unit's `system.img`; a loader can read them as `firmware-get` does | §3 |
| ISP, VDEC, VENC, MFG off | ISP and MFG off; VDEC, VENC and MJC are not under genpd and their state was not read | [R2](../../experiments/2026-11-06-gemini-power-management/README.md#r2-result-2026-11-06) |
| Display domain off (deep idle) | Not shown: blanking was not observed to power `DIS` down | Unknown |
| Infra gates | **Not met today:** R2 found SPI0-5, IR TX, I2C2/3, PWM1-4, UART1-3, ICUSB and others enabled with no user | R2; fixed only by P3's clock owners or a boot without `clk_ignore_unused` |
| I2C0-3 gates idle | Mainline `i2c-mt65xx` gates its clocks between transfers; the 8.5 Hz I2C polling seen in R1b keeps one busy at times | Inferred |
| UNIVPLL, MSDCPLL off (SODI3) | **Not met:** the eMMC runs from MSDCPLL | R2 |
| Display PWM on the low-power oscillator (SODI3) | Not configured | Inferred |
| Next timer over 2 ms | Often; CPU0 still took about 68 timer interrupts a second in R1b | R1b |
| APXGPT as the wake timer | No APXGPT node in the upstream `mt6797.dtsi` | — |
| SYS_CIRQ | Upstream `irq-mtk-cirq` has the same v1 register layout, but has no MT6797 match entry or node | Upstream source |

So suspend needs none of the idle conditions, while deep idle and SODI need
the clock work of P3 first.

## 6. PMIC side

**Wrapper phase tables** (MT6797 branch of `mt_spm_pmic_wrap.c`; MT6351
register addresses; voltage code `(µV - 600000) / 6250`):

| Slot | Suspend phase | Deep-idle phase |
| --- | --- | --- |
| 0-6 | `VCORE_CON5` (`0x060a`) ← 1.0, 0.983, 0.967, 0.950, 0.933, 0.917, 0.900 V (`0x40`, `0x3e`, `0x3b`, `0x38`, `0x36`, `0x33`, `0x30`) | same |
| 7 | `VCORE_CON6` (`0x060c`, sleep voltage) ← 0.6 V (`0x00`) | `TOP_CON` (`0x0204`) bit 3 set (`SRCLKEN_IN2` normal) |
| 8 | `SMPS_ANA_CON9` (`0x044a`) bits 9:8 ← 3 (`VSLEEP_SEL` 0.6 V) | `TOP_CON` bit 3 clear (`SRCLKEN_IN2` sleep) |
| 9 | `VCORE_CON5` ← 0.775 V (`0x1c`) | same |
| 10, 11 | `BUCK_VSRAM_PROC_CON4` (`0x06a8`; `CON5`, `0x06aa`, on PMIC revision `0x5140`) ← 1.0 V, 1.1 V (`0x40`, `0x50`) | same |
| 12, 13 | `VCORE_ANA_CON7` (`0x045c`) bit 1 set / clear (VCORE low-IQ) | same |
| 14 | `VCORE_CON6` ← 0.7 V (`0x10`) | unused |
| 15 | `SMPS_ANA_CON9` bits 9:8 ← 0 | unused |

Slots 8, 12, 13 and 15 are written as read-modify-write of the live PMIC
register. The program issues the slots itself; the kernel only loads them.

**VCORE sleep voltage.** If efuse word `0x44` bit 31 is set, the vendor
sets the sleep voltage to 0.7 V, `VSLEEP_SEL` to 0, and adds flag bit 19,
which tells the program to skip its temperature checks. Without that efuse
bit it picks 0.7 V or 0.6 V from the thermal ADC against its 0 and 70 °C
thresholds, and leaves the program to wake periodically and check the
temperature.

**Static PMIC sleep modes**, applied once per mode change
(`spm_pmic_power_mode`): `BUCK_VCORE`, `VS1`, `VS2` and `VGPU` (`CON0` at
`0x0600`, `0x0664`, `0x0678`, `0x0614`) go to hardware control with sleep
voltage enabled, following `SRCLKEN0`. LDOs `VUSB33`, `VIO28`, `VLDO28`,
`VIO18`, `VA18` and `VA10` go to low-power mode on `SRCLKEN0`; the oscillator
goes to hardware mode (`TOP_CON` bit 6); `VSRAM_PROC` gets a 0.7 V sleep
voltage on PMIC revision `0x5140`. Around each entry the vendor also sets
VGPU low-IQ (`VGPU_ANA_CON7` bit 1) and the power-good force bits
(`STRUP_CON4` bit 15, `STRUP_CON6` bit 9). The vendor calls also set each
regulator's enable bit, which would switch on a rail mainline keeps off. A
mainline loader must not copy that part.

## 7. Wake sources

`SPM_WAKEUP_EVENT_MASK` bits (`pcm_def_mt6797.h`): 0 PCM timer, 1 SCP
watchdog, 2 keypad, 3 AP watchdog, 4 APXGPT, 5 CONN2AP, 6 EINT, 7 CONN
watchdog, 8 CCIF0, 9 low battery, 10 SCP, 13 PCM watchdog, 14-15 USB, 16 C2K
watchdog, 17 secure EINT, 18 CCIF1, 19 UART0, 20 audio, 21 thermal, 22
SYS_CIRQ, 24 debug power request, 25 modem watchdog, 26 CLDMA, 27 SEJ. Vendor
suspend uses `0x0f47c5e7`; deep idle adds APXGPT and audio and drops the
debug request.

## 8. Figures the vendor material implies

The vendor code contains no current figures for these states. What it implies:

- **Under 10 mA in suspend.** The vendor fuel gauge treats less than 10 mA of
  system current while suspended as the condition for trusting the battery's
  open-circuit voltage (`SUSPEND_CURRENT_CHECK_THRESHOLD`). That is the
  vendor's expectation for a phone on this platform, not a Gemini board
  measurement.
- **VCORE from 0.90-1.0 V to 0.6-0.7 V** in suspend, and to 0.775 V in deep
  idle and SODI, with the 26 MHz request, DRAM and DRAM PHY, the PLLs and
  (in suspend) infra off, and the main LDOs in low-power mode.
- **Retention already in WFI** for CPU1-7 (§2), so per-core power-down would
  add little over today's WFI.

Measured so far on mainline: 111 mA blanked, about 96 mA with only CPU0
online ([R1b](../../experiments/2026-11-06-gemini-power-management/README.md#r1b-result-2026-11-06)).
Between 96 mA and the vendor's "under 10 mA" lie board loads the SPM cannot
reach, plus what clock gating (P3) removes anyway. Only a measurement splits
them.
