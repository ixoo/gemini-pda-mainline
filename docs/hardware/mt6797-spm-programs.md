# MT6797 SPM programs: instruction set and behaviour

Scope: the instruction set of the MT6797 SPM's PCM processor, and what the
nine vendor programs (`pcm_*.bin`) do, step by step. It also covers whether a
project-written suspend program is feasible. The file format, how the kernel
loads programs, the PMIC-wrapper tables, the flags and the wake sources are in
[MT6797 SPM sleep](mt6797-spm-sleep.md). This page does not repeat them.

None of this is mainline support. No SPM program has run on mainline.

| Field | Value |
| --- | --- |
| Device | Named Gemini PDA development unit (MT6797X) |
| Last verified | 2026-11-08 (static analysis; no device access) |
| Programs | The unit's nine files, hashes in [§3 of the sleep page](mt6797-spm-sleep.md#3-the-spm-program-files) |
| Method | A private extended decoder, written for this pass and run in the RE VM, starting from the public [mt8173-pcm-tools](https://git.paulk.fr/mt8173-pcm/mt8173-pcm-tools.git) encodings. It was checked against the vendor kernel's register names (`pcm_def_mt6797.h`, `mt_spm_reg_mt6797.h`, `sleep_def_mt6797.h`), the event-vector descriptors, the kernel's `PCM_REG_DATA_INI`/`pwr_ctrl` set-up and its wake-status reads |
| Not published | Program bytes, disassembly listings and decoder output. They stay private because the programs are proprietary |

"Observed" means read directly from the decoded programs. "Inferred" means
reasoned from them or from how the vendor kernel uses them. Register and bit
names are the vendor kernel's, or mainline `clk-mt6797` names where those
exist.

## 1. Instruction set

### 1.1 Decoding result

Every one of the 12,542 instructions in the nine programs decodes into one of
the classes below. Each class has a structurally consistent encoding,
and every branch target lands on an instruction boundary. The classes are
observed. Their semantics are observed where the vendor names or the
surrounding code fix them, and inferred otherwise (§1.4).

About 89% of the instruction words match a pattern the public decoder knows.
It still mis-decodes branch and call targets above `0x3ff`: 692 of them,
because it uses a 10-bit field where the field is 11 bits. It has no
encodings for register move, add and subtract, ordered compares, the 5-bit
store immediate, register-indirect load or the conditional call.

### 1.2 Machine model

- **Registers:** 32 names in 5-bit fields. `r0`-`r15` are real registers.
  Index 31 reads as zero and discards writes; `nop` is "move zero to zero".
  Indexes 16-30 never appear as registers.
- **Word size and program:** 32-bit instructions, some with one or two
  extension words. Program addresses are word indexes, 11 bits wide.
- **Delay slot:** every jump, call and return executes the next
  instruction. Observed: loops decrement their counter in the delay slot
  (`jnz r2, top` followed by `r2 = r2 - 1`), and the debug-flag routine reads
  `r10`, which the caller sets in the call's delay slot. Where nothing useful
  fits, the slot holds `nop`.
- **Constant one:** each program sets `r1 = 1` first and then builds every
  single-bit mask as `r1 << n`. This is a software convention, not hardware.

### 1.3 Encoding

Common fields: `op` = bits 31:28; `I` = bit 27; `rd` = 26:22; `N` = 21;
`L` = 20; `sh` = 19:15; `rs2` = 14:10; `rs1` = 4:0. Branch target = 15:5.

| `op` | `I` = 0 | `I` = 1 (one extension word unless noted) |
| --- | --- | --- |
| `0` add | `rd = rs1 + (rs2 shift)`; `N` = 1 subtracts | `rd = rs1 + imm` |
| `1` move/load | `rd = rs2 shift` (`rs1` is always zero); `N` inverts | `L` = 0: `rd = imm`; `L` = 1, `rs1` = zero: `rd = mem[imm]`; `L` = 1, `N` = 1: `rd = mem[rs1]` (the extension word is unused and filled with the `nop` pattern) |
| `2`, `3`, `4` ordered compare | not used | `rd = rs1 ⋈ mem[imm]`, with `N` and `L` always set (§1.4) |
| `6` eq | `rd = (rs1 == rs2)`, `N` always set | `rd = (rs1 == imm)` |
| `8` and | `rd = rs1 & (rs2 shift)`; `N` = 1 uses `~(rs2 shift)` | `rd = rs1 & imm` |
| `9` unknown | three uses, all in the VCORE-DVFS programs, combining two flag bits | — |
| `a` or | `rd = rs1 \| (rs2 shift)`; `N` as for `and` | `rd = rs1 \| imm` |
| `c` call | call target; bits 26:22 name an argument register (§1.4) | conditional call: if `rs1` is zero (`N` = 1) |
| `d` jump | unconditional | conditional on `rs1`: `N` = 1 jumps if zero, `N` = 0 if non-zero |
| `e` store | `N` = 0: `mem[rd] = rs1`; `N` = 1: `mem[rd] = ` the 5-bit value in `rs1` | `mem[imm1] = imm2` (two extension words) |
| `f` return | `0xf0000000` only | — |

`shift` means "`rs2` shifted by `sh`, left if `L` = 1, right if `L` = 0". The
programs use it for single-bit work: `r5 = r1 & (r6 >> 6)` tests flag bit 6,
and `r7 = r7 & ~(r1 << 13)` clears bit 13.

Memory operands are 32-bit MMIO accesses on the SPM's bus, which reaches the
SPM, INFRACFG, TOPCKGEN, APMIXEDSYS, the PMIC wrapper's DVFS port, the I2C,
AUXADC and DRAM-controller blocks, and DRAM itself.

### 1.4 Register meanings

| Register | Meaning | Basis |
| --- | --- | --- |
| `r0` | Power I/O word 0: clock-off and PLL-off controls, DRAM PHY controls (`R0_*`) | Observed: every bit the programs flip has a matching `R0_*` name; the kernel seeds it from `SPM_POWER_ON_VAL0` |
| `r1` | Constant 1 | Observed |
| `r2`-`r5`, `r8`, `r9` | Scratch, loop counters, call arguments | Observed |
| `r6` | `SPM_SW_FLAG` low bits (the flags) plus program state in the high bits: bit 26 NFC clock buffer, 27 26 MHz, 28 infra, 29 APSRC, 30 VRF18 and 31 DDREN awake; 23/24 VCORE level; 22 hot sleep voltage chosen; 21 SCP DVFS done | Observed: loaded from `SPM_SW_FLAG`, ORed with `0xfd000000` (sleep programs) and updated by each handler; the kernel reads bits 24:23 as the VCORE state |
| `r7` | Power I/O word 1: resource and handshake outputs (`R7_*`: 26 MHz request, source voltage, PMIC-wrapper sleep, EMI clock-off, bus-master pause, PCM clock select, PCM timer set and clear, wake register selects) | Observed against the `R7_*` names; seeded from `SPM_POWER_ON_VAL1` |
| `r10` | Argument of the debug-flag routine (one `SPM_DBG_*` bit) | Observed |
| `r11` | Argument register of a call. Callees that use it store through it, and every caller has just loaded the target address into the register that the call word names | Inferred; 60 calls name `r3`, 84 name `r10` |
| `r12` | Reads: wake events (`R12_*`) or, with `R7_WAKEUP_EXT_R_SEL`, resource events (`R12EXT_*`). Writes: the wake-event enable mask or, with `R7_WAKEUP_EXT_W_SEL`, the resource-event enable mask | Observed pattern; the mask meaning is inferred from the values written |
| `r13` | Status inputs (`R13_*`): EMI clock-off ack, PMIC-wrapper sleep ack, EMI idle | Observed against the `R13_*` names |
| `r14` | Wait register. A write with bit 29 set stalls for the count in the low bits. Other top-nibble modes (`0x3`, `0x5`, `0x9`, `0xd`) stall for conditions | The delay use is observed (between power-switch steps). The conditional modes and the time unit are inferred |
| `r15` | Return address / program counter. Abort paths store it in `PCM_REG_DATA_INI`, which the kernel reports as the "assert PC" | Inferred |

**Not settled:** the exact predicate of ops 2, 3 and 4. Op 3 behaves as
`≥` in the thermal-period counter, and ops 2 and 4 bound a temperature ADC
reading from below and above. Also not settled: what op 9 computes, what the
conditional `r14` modes wait for, the `r14` time unit, and whether a top-level
`ret` halts the PCM. None of these blocks reading the programs' control flow.

### 1.5 Events

Each non-zero event vector names event `0x20 + k`, where `k` is the
`R12EXT_*` bit index. So the twelve vectors in a sleep program are six
wake/sleep pairs: 26 MHz (`k` 0/1), infra (2/3), APSRC (4/5), VRF18 (6/7),
DDREN (12/13) and the external clock-buffer request for NFC (14/15). The
program picks which ones may fire through `PCM_EVENT_VECTOR_EN`
(`0xf3f3` in suspend and deep idle) and the `r12` resource mask. The SPM
hardware raises them when the merged resource requests (`SPM_SRC_REQ`, masked
by `SPM_SRC_MASK`/`SRC2_MASK` and the CPUs' WFI state) cross a threshold, and
the PCM then runs the handler as a subroutine.

## 2. Program structure

All six sleep programs have the same shape (observed):

1. **Handlers** at the low addresses, one per event vector, each ending in
   `ret`.
2. **Shared subroutines:** MTCMOS on/off sequences, the debug-flag OR into
   `SPM_SW_DEBUG`, the PMIC-wrapper command (write the slot number to
   `SPM_DVFS_CON[3:0]`, then poll bit 31), the EMI clock-off handshake, CPU
   power steps, the I2C write and the thermal check.
3. **Entry at `0x400`,** after `nop` padding: set `r1`, load the flags, clear
   `SPM_SW_DEBUG` and `SPM_SW_RSV_0`, run the sleep entry, enable the events
   and enter the **main loop**.
4. **Main loop:** wait in `r14` for an enabled wake event while resource
   handlers run asynchronously. When the wait ends, call the wake handler of
   every resource that is asleep, in the order 26 MHz, infra, VRF18, DDREN,
   APSRC, NFC clock buffer. Then classify the wake.
5. **Exit:** store the wake reason (`r12`) in `SPM_SW_RSV_0`. Copy
   `SPM_WAKEUP_MISC`, `PCM_TIMER_OUT` and `PCM_EVENT_REG_STA` to
   `SPM_BSI_D0`/`D1`/`D2_SR` (the kernel's `wake_misc`, `timer_out` and
   `event_reg`), set `r11` to a marker and raise software interrupt 0 through
   `SPM_SW_INT_SET`. That is the "PCM return" interrupt that wakes the CPU.

The six handler pairs are the program's real work. They form a dependency
chain. Each handler re-arms only the next events that make sense: after 26
MHz wake, 26 MHz sleep or infra wake; after infra wake, infra sleep, APSRC
wake or VRF18 wake. The chain is 26 MHz ⊃ infra ⊃ {APSRC, VRF18} ⊃ DDREN, and
it is unwound in reverse. Each handler records its `SPM_DBG_*` bit in
`SPM_SW_DEBUG`.

The `_by_mp1` file of each sleep program differs only in the CPU it powers:
`MP1_CPU0` (CPU4) and `MP1_CPUSYS` instead of `MP0_CPU0` and `MP0_CPUSYS`,
with the matching `CPU_PWR_STATUS` bits (11 and 18 instead of 15 and 19). The
code is otherwise identical (observed).

## 3. `pcm_suspend.bin` (`pcm_suspend_v20`), step by step

### 3.1 Entry

| Step | What it does | Skipped by |
| --- | --- | --- |
| E1 | `r6` ← flags \| `0xfd000000` (all resources start "awake"); clear `SPM_SW_DEBUG`, `SPM_SW_RSV_0` | — |
| E2 | Flag 10 (`RUN_COMMON_SCENARIO`): resident VCORE-DVFS mode. PCM clock selects cleared, wake mask = PCM timer, AP watchdog, SCP IRQ; event vectors disabled; straight to the main loop | — |
| E3 | Ungate `I2C_APPM` (INFRA CG2 clear, bit 1); soft-reset I2C6 (`0x1100e050` ← 1); start the PCM timer (`R7_PCM_TIMER_SET`); clear the wake-event mask | — |
| E4 | Wait in `r14` (mode `0xd` if flag 0 is set, `0x5` otherwise; inferred: until the AP is in standby). With flag 0, abort to the exit if a wake event is already pending | — |
| E5 | Bus-master pause masks, then raise `R7_TOP_MAS_PAU_REQ` (pause the masters) | — |
| E6 | Clear `R7_CSYSPWRUPACK` | flag 8, flag 0 |
| E7 | Power down `MP0_CPU0` (`PWR_CON` sequence, then poll for the SRAM ack), `MP0_CPUSYS` (pause-mask staging, then poll), and `MCUSYS` with `MP_TOP`; `CPU_EXT_BUCK_ISO` ← 3; debug `CPU_PDN`. Then re-check for a pending wake (abort to the exit) | flag 0 |
| E8 | Turn the external CPU buck off over I2C6: program the controller (timing, high-speed, I/O config, lengths), send `[0x1d, 0x00]` to slave `0x68`, write INFRACFG `0x10001f98` ← 0, wait | flag 9 |
| E9 | ARM clocks and PLLs off: gate `infra_gce` (CG0 bit 9); `R7_SC_26M_CK_SEL`, `R7_SC_AXI_DCM_DIS`; `ddrphycfg_sel` → parent 0 (TOPCKGEN `CLK_CFG_0` bits 17:16, update bit 2); APMIXED `0xf38` bit 4; `R0` ARM, SMI clock-off and ARMPLL/ARMBPLL stage bits | — |
| E10 | Enable the twelve event vectors, arm the resource events (APSRC, VRF18 and DDREN sleep, plus NFC if flag 20), enter the main loop | — |

### 3.2 Resource handlers (the actual sleep)

| Resource | Sleep handler | Wake handler (reverse) |
| --- | --- | --- |
| DDREN | Ask for the EMI clock-off ack (eight polls of `R13`; on a timeout, undo and report). Then DRAM into self-refresh: APMIXED `0xf4c` bit 4; `R0` DPY mode-switch and DMSUS set; DLL, DLL clock and VREF bits cleared | Leave self-refresh in the reverse bit order, clear `R7_EMI_CLK_OFF_REQ` |
| APSRC (DRAM access) | Pause mask; drop `R7_MD_APSRC_ACK`; EMI handshake; `CLK_CFG_0` bit 8 cleared (memory clock to 26 MHz, inferred); DRAM self-refresh as above; `SPM_PLL_CON` sequence (MEMPLL off, inferred); DRAM PHY power-down of both channels (`DPY_PWR_CON`, `DPY_CH1_PWR_CON`: ISO on, clock off, reset, power off); gate `infra_auxadc` (CG1 bit 10); PMIC-wrapper slot 10 | Slot 11; ungate AUXADC; DPY power-on (ON, ON_2ND, clock on, wait, ISO off, reset released); `SPM_PLL_CON`; DLL/VREF on; `CLK_CFG_0` bit 8 set; `R7_MD_APSRC_ACK` |
| VRF18 | `R7_FREQH_PAUSE_MAIN`; MAINPLL output, stage 2 and stage 1 off (`R0`) | MAINPLL back on stage by stage, with waits |
| Infra | Records the state only | Records the state only |
| 26 MHz | Abort if a wake is pending. PMIC-wrapper slot 12 (VCORE low-IQ on). Unless flag 1: write `0x100a4034` (block not identified; not with flag 17), clear `SPM_SRC_RDY_STA` bit 0, pulse a bit in both DRAM-controller channels (`0x100040f8`, `0x100130f8`, inferred), **power infra down** (`IFR_PWR_CON` off sequence, with SYSROM and SYSRAM to sleep). Unless flag 6: `R0_SC_AXI_CK_OFF`. Then `MD26M_CK_OFF`, the PCM clock to 32 kHz, `R7_IM_SLEEP_ENABLE`, `26M_CK_OFF`, `CKSQ0_OFF`, and finally drop `R7_SRCCLKENO_0` and `R7_SRCVOLTEN`. That releases the 26 MHz clock buffer and lets VCORE fall to its PMIC sleep voltage | The reverse: request 26 MHz and source voltage, wait for it to settle, the PCM clock back to 26 MHz, clocks on, infra power-on (SYSROM/SYSRAM wake), MD32/`0x10229004`-`8` handshake (block not identified), wait for `SPM_WAKEUP_MISC` bit 30 (PMIC-wrapper IRQ ack), slot 13 (low-IQ off). With flag 17 the PMIC-wrapper sleep request/ack is done here |
| NFC clock buffer | `SPM_MDBSI_CON` bit 1 off, external clock-request bits swapped | The reverse |

So the order of the sleep, as the requests drop, is: CPU (at entry) → DDREN
and APSRC (DRAM self-refresh, PHY off, MEMPLL) → VRF18 (MAINPLL) → infra
(state only) → 26 MHz (infra power-down, clocks, the clock buffer and VCORE).
VCORE is not lowered by DVS commands in suspend. The vendor sets flag 3
(`DIS_VCORE_DVS`), which skips slots 10 and 11. VCORE falls because
`SRCCLKENO_0` drops and the PMIC applies its programmed sleep voltage.

### 3.3 Wake classification (main loop)

1. Bring every sleeping resource back up (§2, item 4).
2. **AP watchdog** (`R12` bit 3): set `INFRA_TOPAXI_PROTECTEN` to `0xffff`,
   power both A53 clusters on, wait indefinitely (for the reset).
3. **SCP IRQ** (bit 10): the SCP VCORE-DFS handshake through `SPM_SW_RSV_3`.
   It steps VCORE one PMIC-wrapper slot at a time (down through slots 5-0, or
   up through 1-6), with about 50 dummy reads of both DRAM ranks (`SPM_PASR_DPD_1`/`2` hold their addresses) after each
   step, then returns to the loop.
4. **PCM timer with `SPM_WAKEUP_MISC` bit 19:** a thermal period. If
   `SPM_SCP_MAILBOX` ≥ `SPM_PASR_DPD_3` (inferred predicate), it is a real
   wake. Otherwise it increments the mailbox and, unless flag 19, reads the
   thermal ADC through AUXADC (`0x11001000`), stores it in `SPM_BSI_D1_SR`,
   and picks the sleep voltage: slots 7 and 8 (0.6 V) when the reading is
   inside the `SPM_SW_RSV_2`..`SPM_BSI_D0_SR` window, slots 14 and 15
   (0.7 V) otherwise. It restarts the timer and goes back to sleep.
5. Anything else: exit.

### 3.4 Exit

Unless flag 10: restore the ARM PLLs and clocks (E9 in reverse; `infra_gce`
ungated, `ddrphycfg_sel` → parent 1). Unless flag 9: `0x10001f98` ← `0xff`,
then I2C `[0x1d, 0x01]` to `0x68`, and wait. Unless flag 0: `CPU_EXT_BUCK_ISO`
← 2 and power-up of `MCUSYS`, `MP0_CPUSYS` and `MP0_CPU0`. Gate `I2C_APPM`
(CG2 set, bit 1). `PCM_WDT_VAL` ← `0xf0000`; `R7`: timer stopped,
`CSYSPWRUPACK`, master pause released, watchdog kick. Status backups, then
the return interrupt (§2, item 5).

### 3.5 Inputs that change the path

| Input | Effect in `pcm_suspend` |
| --- | --- |
| Flag 0 `DIS_CPU_PDN` | CPU, cluster and MCUSYS stay powered; `CPU_EXT_BUCK_ISO` is not touched; an early wake check replaces the post-power-down one |
| Flag 1 `DIS_INFRA_PDN` | No infra power-down and none of the DRAM-controller and `0x100a4034` steps in the 26 MHz handlers |
| Flag 2 `DIS_DDRPHY_PDN` | DRAM PHY stays powered (self-refresh still happens) |
| Flag 3 `DIS_VCORE_DVS` | No slots 10/11 in the APSRC handlers, no SCP DFS steps |
| Flag 6 `DIS_BUS_CLOCK_OFF` | AXI clock stays on |
| Flag 8 `KEEP_CSYSPWRUPACK_HIGH` | `CSYSPWRUPACK` stays set |
| Flag 9 `DIS_VPROC_VSRAM_DVS` | No I2C buck write, no `0x10001f98` writes |
| Flag 10 `RUN_COMMON_SCENARIO` | Resident mode: no sleep entry, no PLL restore, no CPU power-up; only timer, AP-watchdog and SCP wakes |
| Flag 17 | PMIC-wrapper sleep request/ack in the 26 MHz handlers instead of the `0x100a4034` writes (the vendor header names this bit `EN_HPM_SODI`) |
| Flag 19 | Thermal ADC check skipped |
| Flag 20 `EN_NFC_CLOCK_BUF_CTRL` | Arms the NFC clock-buffer events |
| Flags 4, 5, 7, 11-16, 18 | **Not tested** by `pcm_suspend` |
| Flags 24, 26-31 | Overwritten by the `0xfd000000` state seed |
| `pwr_ctrl` | Not read by the program. The kernel writes it into the SPM's request and mask registers, which decide when the resource events fire |
| `SPM_SW_RSV_2`, `SPM_BSI_D0_SR`, `SPM_PASR_DPD_3`, `SPM_SCP_MAILBOX` | Thermal window and period counter (§3.3) |

## 4. `pcm_deepidle.bin` (`pcm_deepidle_fpb_v17`)

The same entry, main loop, wake classification and exit as suspend, with
these differences (observed):

- The 26 MHz handlers do **not** switch the 26 MHz clock, infra or the PCM
  clock. 26 MHz sleep issues PMIC-wrapper slots 12 and 8 and sets `MD26M` and
  AXI clock-off. 26 MHz wake issues slots 7 and 13. Slots 7 and 8 here are
  the deep-idle phase: `SRCLKEN_IN2` normal/sleep.
- Infra is never powered down (no `IFR_PWR_CON` writes). The infra handlers
  set and clear `SPM_SRC_RDY_STA` bit 0.
- SYSRAM sleep is done at entry and undone at exit, unless flag 16.
- The I2C buck write at entry and exit (unless flag 9) also saves INFRACFG
  `0x10001f9c` in `SPM_SW_RSV_2` and rewrites `0x10001f9c`/`0x10001fa0`
  (block not identified).
- APSRC, VRF18 and DDREN handlers follow suspend's, with flag 7 and flag 23
  tests added.

So deep idle reaches DRAM self-refresh, the PHY and MAINPLL off, and the
CPU off, but keeps 26 MHz and infra.

## 5. `pcm_sodi.bin` (`pcm_sodi_fpb_v15`)

Screen-on idle. Observed differences from deep idle:

- It loads the VCORE state from `SPM_SW_RSV_5` into `r6` bits 24:23. Flag 15
  (`DIS_SRCCLKEN_LOW`) forces `R7_FORCE_26M_WAKE` and `FORCE_INFRA_WAKE`.
- Only the APSRC and NFC events are enabled. Unless flag 13 (`SODI_NO_EVENT`):
  CG mode (flag 12, or `DUMMY1_PWR_CON` bit 1) enables a second APSRC handler
  pair that gates the DRAM clocks without powering the PHY down. PDN mode
  enables the pair that also powers the PHY down. 26 MHz, infra and VRF18
  stay up.
- One call performs the CPU, cluster and MCUSYS power-down (unless flag 0).
- Flag 14 (`ENABLE_SODI3`) changes two steps inside the APSRC handlers; they
  were not traced in detail.

## 6. The VCORE-DVFS programs (`pcm_vcorefs_lpm/hpm/ultra`)

These are the resident program, not sleep programs (observed): no event
vectors, `PCM_EVENT_VECTOR_EN` ← 0, and one main loop that waits for the CPU
wake-up event, kernel requests in `SPM_SW_RSV_1`, the SCP IRQ or the DVFS
force bits in `SPM_SRC_REQ`. It reports its state in `SPM_SW_RSV_5` and
`SPM_SW_DEBUG` bit 29. It changes the VCORE operating point through
PMIC-wrapper slots and the DRAM frequency through both DRAM-controller
channels (`0x10004000`, `0x10013000` ranges), DDRPHY-side registers and the
EMI. Flags 3, 4, 18, 23 and 24 select its paths. `hpm` and `ultra` differ in
a single constant word. `lpm` has a different DRAM-shuffle sequence.

## 7. Could the project write its own suspend program?

**Size.** A suspend program that copies the vendor's behaviour but
leaves out resident DVFS, SCP DFS, thermal periods and NFC would be roughly
500-700 instructions: entry, CPU path, six handler pairs, the wake loop and
exit. The vendor's is 1,420 instructions in 1,822 words. The instruction set
in §1 is enough to express it, and the format is known.

**Hardware facts it depends on, and how well they are known:**

| Fact | Known from |
| --- | --- |
| Encoding, delay slot, `r0`/`r7`/`r12`/`r13` bit meanings, event numbering | This decode plus the vendor names: good |
| MTCMOS sequences for CPU, cluster, MCUSYS, infra and DPY, and the SYSRAM/SYSROM steps | Readable from the programs and the vendor kernel: good |
| PMIC-wrapper slot mechanism and tables | Vendor kernel: good |
| How the merged resource requests are formed (`SPM_SRC_REQ`/`MASK`, `AP_STANDBY_CON`) | Vendor field names only; behaviour **inferred** |
| What the `r14` wait modes wait for, and the delay unit | **Not known**; the vendor's constants can be reused, not derived |
| DRAM self-refresh and PHY sequence: the order of the `R0` DPY bits, the `SPM_PLL_CON` steps, APMIXED `0xf38`/`0xf4c`, the DRAM-controller pulse | Copied, not understood. The DRAM controller's register meanings are not documented |
| The 26 MHz release (`SRCCLKENO_0`, `SRCVOLTEN`, `CKSQ0`) and its settle times | Copied |
| The unidentified blocks (`0x100a4034`, `0x10229004`-`8`, INFRACFG `0xf98`-`0xfa0`) and I2C buck register `0x1d` | **Not known** |

**What cannot be inferred without vendor documentation:** the DRAM
self-refresh and PHY sequence and its timings; the `r14` condition semantics;
and the purpose of the unidentified registers. A project program would copy
those as opaque constants, which is a derivative of the vendor program, not a
clean-room design. A clean-room path would need either documentation or
measurement-driven experiments on DRAM sleep. A mistake there corrupts DRAM
or hangs the board, recoverable only by force-off.

**Risks.** The PCM has no exception model: a wrong wait or poll hangs it
silently, and the CPU never wakes. DRAM, PHY and VCORE errors fail as
silent corruption or a lock-up. Each attempt needs a device stage. The vendor
program is also tuned against undocumented analogue timings.

**Judgement.** Writing a program is technically possible. A **reduced**
project program that does only the well-understood part (CPU path, 26 MHz,
infra MTCMOS, the PMIC sleep voltage, without DRAM self-refresh) is
feasible and would be original work. It would leave DRAM active, which is
probably where much of the saving is. A full replacement that includes DRAM
self-refresh would in practice reproduce the vendor sequence. It is not
clean-room without documentation that the project does not have. The vendor
program run locally (Route A) remains the way to learn what the saving is,
and that number decides whether the reduced program is worth writing.
