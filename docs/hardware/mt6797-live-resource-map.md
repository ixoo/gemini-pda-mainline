# MT6797 live resource map for mainline

This is the implementation-facing map of the Gemini's running MediaTek 3.18
device tree. It records resources that can seed Linux 7.1.x SoC nodes and
driver data while separating reusable hardware facts from vendor bindings.

Current build note (2026-07-14): the 77-patch package
`linux-7.1.3-gemini-6116c9e7da3f` is the current Image/DTB baseline; older
package links are historical build evidence. The current SPI
working series adds patches 0072–0073 and produces
`linux-7.1.3-gemini-c2feb465d6c6` (74 patches). Its disabled-node contract and
focused binding/package validation are recorded in the [SPI patch validation](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt).
Any `current-71` result names retained below are historical package records;
the current 74-patch package provenance is in the [integration result](../../experiments/2026-07-13-kernel-integration/results/mainline-74-patch-current-20260714.txt)
and its LK packaging is in the [current 74-patch candidate result](../../experiments/2026-07-12-boot-contract-recovery/results/mainline-74-lk-candidate-current-20260714.txt).
The latest 77-patch Image/DTB package is
`linux-7.1.3-gemini-6116c9e7da3f`; its private LK-compatible wrapper and
parser hashes are in the [77-patch candidate result](../../experiments/2026-07-12-boot-contract-recovery/results/mainline-77-lk-candidate-diagnostics-current-20260714.txt).
It remains untransferred and unbooted.
The older subsystem audits remain valid content evidence because patches
0072–0073 only add disabled SPI support. The current LK FDT/reservation decision is recorded
in the [fixup audit](../../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md).
The current package's linked-in/module-only ownership boundary is in the
[77-patch driver coverage audit](../../experiments/2026-07-13-driver-coverage-audit/results/driver-coverage-current-77-package-20260714.txt),
the first-boot dependency graph is in the [current first-boot audit](../../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-77-package-20260714.txt),
and the packaged DT passes the [current merged-schema validation](../../experiments/2026-07-14-first-boot-probe-audit/results/gemini-dtb-schema-current-72-package-20260714.txt).
The current 74-patch first-boot rerun and all-three-board schema result are
[`first-boot-probe-audit-current-74-package-20260714.txt`](../../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-74-package-20260714.txt)
and [`mt6797-dtb-schema-bounded-current-74-20260714.txt`](../../experiments/2026-07-14-first-boot-probe-audit/results/mt6797-dtb-schema-bounded-current-74-20260714.txt);
they preserve the same built-in UART/PWRAP/MT6351/MSDC chain while covering
the SPI additions.
The built-in UART/PSCI/timer/GIC/eMMC/watchdog handoff contract is checked by
the [current static handoff closure](../../experiments/2026-07-13-mainline-handoff-closure/results/handoff-closure-current-72-package-20260714.txt).

## Evidence chain

The strongest evidence is the read-only 2026-07-11 capture from the running
Gemian device. Its raw, sanitized output is private and Git-ignored at
`artifacts/device-inventory/20260711-live/device-tree-v5.txt`. The collector and
phandle decoder are committed in the hardware-inventory experiment.

Three public GPL source trees provide provenance and register semantics:

- the exact Gemian 3.18 source at commit
  [`d388d350cb2dda8f23b99be6fa5db9628896e87f`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/d388d350cb2dda8f23b99be6fa5db9628896e87f),
  including the running DT's CMDQ, display-mutex, and display-path contracts;
- Planet/Gemini 3.18 source at commit
  [`c5b0be85017ad0c599725e8273842efdbecdd88a`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/tree/c5b0be85017ad0c599725e8273842efdbecdd88a),
  including `aeon6797_6m_n.dts`, the MT6797 MSDC driver, and M4U port data;
- the partial Gemini 4.9 port at commit
  [`c65b8b5592a462041dce0d3058dc4e5f831704ce`](https://github.com/NotKit/kernel-4.9-geminipda/tree/c65b8b5592a462041dce0d3058dc4e5f831704ce),
  which describes UART0, MSDC0, PMIC wrap, MT6351 rails, and experimental M4U
  integration.

The live tree matches the `aeon6797_6m_n` naming, model, addresses, and
peripheral layout. Public source remains secondary evidence: it can contain
unused alternatives, board-family defaults, downstream hacks, and changes not
present in the running image. The display investigation found exactly such an
inactive alternative in the live root tree, so runtime binding takes priority
over node presence.

The 4.9 board DTS enables UART0 and internal eMMC only. It carries a dummy
40 MHz PMIC-wrap clock and vendor M4U code. It is valuable archaeology, not a
mainline-ready DTS and not proof that its untested nodes work.

## Core resource table

GIC interrupt numbers below are SPI numbers. `LOW` and `HIGH` are the trigger
polarity encoded by the vendor tree; they still require runtime validation
before upstream submission.

| Block | Register windows | IRQ | Live clock/resource evidence | Linux 7.1.x consequence |
| --- | --- | --- | --- | --- |
| PMIC wrapper | `0x1000d000` + `0x1000` | 178 HIGH | 26 MHz PMICSPI mux/AP gate; infracfg reset ID 64 | Master/slave regmap exists; the local series adds the reset provider and complete SoC node |
| EINT | `0x1000b000` + `0x1000` | 170 HIGH | 192 channels, 172 GPIO mappings, 16 hardware-debounce channels | The local series restores pinctrl EINT data/resource and virtual PMIC/built-in inputs |
| UART0–3 | `0x11002000`–`0x11005000` + `0x1000` each; vendor UART0–3 also describe AP-DMA windows | UART SPIs 91–94; vendor DMA IRQs 108–115 | `INFRA_UART0`–`INFRA_UART3`; vendor UART0 has `INFRA_AP_DMA`; live `ttyMT0` console and four `mtk-uart` ports | Linux 7.1.3 `8250_mtk` reuses the 16550/PIO path and standard `mediatek,mt6797-uart` binding; keep the vendor VFIFO/DMA windows disabled until channel/IRQ ownership is recovered |
| SPI0–5 | `0x1100a000`, `0x11012000`, `0x11018000`–`0x1101b000` + `0x1000` each | SPIs 122, 131–135 LOW | `CLK_TOP_MUX_SPI`/`syspll3_d2` parent and `INFRA_SPI`/`SPI1`–`SPI5` gates; vendor pad macros 0/1 | Patches 0072–0073 now map the recovered register/timing layout to Linux `spi-mt65xx` `mt6765_compat` (enhanced 16-bit timing, pad selection, mandatory TX, extended DMA) and add six disabled DT nodes with standard three-clock descriptions. SPI1 wiring is recovered as GPIO234–237 (`SPI1_*_B`), but the vendor DT's empty default plus explicit GPIO/SPI function switching is not yet reducible to a proven static mainline pinctrl state. Runtime transfer remains unproven. See the [SPI reuse audit](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mt6797-controller-reuse-20260714.txt), [SPI1 pinctrl contract](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi1-pinctrl-contract-20260714.txt), and [patch validation](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt) |
| Hall/lid input | GPIO66; no MMIO block | EINT5, level-low initial | Pinctrl pull-up; debounce `0xfa00` (64 ms); vendor switch class `hall`, shared `ACCDET` EV_SW | Standard `gpio-keys` `EV_SW/SW_LID` candidate; verify polarity, debounce units, and wake policy before enabling |
| Toggle input | GPIO93; no MMIO block | EINT16, level-low initial | Pinctrl pull-up; debounce `0x7d000` (512 ms); vendor source labels the board node `anti-tamper`, emits F9/F10 pulses, and exposes switch class `switch` | Do not copy Android switch class; identify physical function, then choose a standard EV_SW or key policy |
| TOPRGU watchdog | `0x10007000` + `0x1000` | 137 EDGE_FALLING | Vendor WDK keepalive; application TOPRGU bark line global IRQ169 | Linux 7.1.3 generic `mtk_wdt` is protocol-compatible; Candidate M proved basic no-IRQ registration and a 31-second timeout reset with automatic Gemian return, while SPI137 bark/pretimeout remains untested |
| M4U | `0x10205000` + `0x1000` | 156 LOW | seven SMI larbs; 15 vendor clock/domain handles | Add MT6797 IOMMU platform data, binding, port header, SMI relationships, and DTS |
| CMDQ/GCE | `0x10212000` + `0x1000` | 152 LOW normal; 153 LOW vendor secure path | `infra_gce` ID 10, 136.5 MHz, gated when idle; live normal IRQ activity | Local binding/header and standalone mailbox provider use the 16-thread MT8173 register/address fallback; expose only normal SPI152 |
| USB 1 | `0x11200000` + `0x1000`; SIF `0x11210000` + `0x1000` | 73 LOW | infra ICUSB and SSUSB reference clocks | Standard MUSB-like core, but distinct MT6797 USB11 SIF/PHY, `0xa0`/`0xa4`/`0xa8` level-1 IRQ block, six-endpoint host contract, and two-clock glue; reuse MUSB core only after the USB11 boundary is modeled |
| AFE | `0x11220000` + `0x10000` | 151 LOW | upstream binding already names eight clocks and audio power domain | Add SoC node using `mediatek,mt6797-audio`; only `0x000`–`0x84c` is used by the upstream regmap |
| CONSYS/WMT | `0x18070000` + `0x200`; AP RGU `0x10007000` + `0x100`; TOPCKGEN `0x10000000` + `0x2000`; SPM `0x10006000` + `0x1000` | 284/285 LOW | `SCP_SYS_CONN`; VCN18/VCN28/VCN33 BT/VCN33 Wi-Fi; dynamic 2 MiB no-map reserve | New MT6797 consys power/clock/reset/firmware owner; keep disabled until ownership and protocol are specified |
| WMT Wi-Fi HIF | `0x180f0000` + `0x1100` | 283 LOW | `INFRA_AP_DMA` (`wifi-dma`) | Proprietary gen2 cfg80211/MAC over MT6797 AP-DMA; not an MT76-compatible MAC; new firmware/HIF boundary required |
| BTIF | `0x1100c000` + `0x1000`; TX `0x11000a00` + `0x80`; RX `0x11000a80` + `0x80` | 130/116/117 LOW | `INFRA_BTIF` and `INFRA_AP_DMA`; consys BGF wake uses SPI 284 | Reuse Linux STP/H:4 and HCI layers where proven; add an MT6797 BTIF/DMA transport, not `/dev/stpwmt` |
| MSDC0 | `0x11230000` + `0x10000` | 79 LOW | `CLK_INFRA_MSDC0` | Add MT6797 data to `mtk-sd`, then internal eMMC DTS |
| MSDC1 | `0x11240000` + `0x10000` | 80 LOW | `CLK_INFRA_MSDC1` | Add microSD only after pinctrl, rails, and voltage switching are modeled |
| USB 3 | `0x11270000`, `0x11280000`, `0x11290000`, each `0x10000` | MUSB 127 LOW; xHCI 126 LOW | vendor node combines dual-role and host views | Strong MTU3/xHCI reuse candidate: split MTU3 `mac = 0x11271000 + 0x3000`, `ippc = 0x11280700 + 0x100`, and xHCI child `mac = 0x11270000 + 0x1000`; add MT6797 clock/rail/PHY/role data after validation |
| Mali-T88x/T880-family | `0x13040000` + `0x4000` | job 264 LOW; MMU 263 LOW; GPU 262 LOW | Runtime ID `0x0880`; 700 MHz DT target; 13 vendor clock/domain handles | Panfrost core model is reusable; MT6797 CCF/SCPSYS/reset/OPP integration remains disabled and unverified |
| MMSYS | `0x14000000` + `0x1000` | 232 LOW | upstream MT6797 MMSYS clock provider exists; retained active routing state | Local 29-route table, 64 resets, and GCE tuple; do not reuse the vendor aggregate `dispsys` ABI |
| Display mutex | `0x1401f000` + `0x1000` | 202 LOW | MM power domain; no dedicated clock; live vendor IRQ activity | Local binding, dedicated module/SOF data, and standalone provider; DRM consumers remain separate |

## Clock, MFG power, and reset-provider contract

The live platform exposes `10001000.scpsys`, `10001000.infracfg_ao`, and
`13000000.g3d_config`. The vendor SCPSYS node has three register tuples:
infracfg at `0x10001000`, SPM at `0x10006000`, and infra at `0x10201000`.
The Linux 7.1.3 generic SCPSYS binding intentionally maps the SPM tuple as
the controller's `reg` resource and obtains the `0x10001000` infracfg window
through its `infracfg` syscon phandle. This is equivalent resource ownership,
not a silicon address discrepancy; the third infra window is not needed by
the generic bus-protection API yet.

The vendor MFG power hierarchy is `mfg_async` → `mfg` → `mfg_core0` through
`mfg_core3`. Status bits in the SPM `PWR_STATUS`/`PWR_STATUS_2ND` registers are
13, 12, 11, 10, 9, and 8 for those six domains. Main control registers are
`0x334`, `0x338`, `0x340`, `0x344`, `0x348`, and `0x34c`. Unlike the other
MT6797 domains, the MFG and core SRAM power-down fields and acknowledgements
share a separate `MFG_SRAM_CON` register at `0x33c`: MFG uses control bits
1:0/ack bits 17:16 and cores 0–3 use control bit 8 with ack bits 20–23. The
generic Linux driver currently assumes control and acknowledgement fields
are in the same register, so a small offset-aware extension is required
before these domains can be represented safely. The vendor MFG routine does
not execute its defined bus-protection mask in the actual path; no bus-protect
bit is inferred here.

The vendor `g3d_config@13000000` provider exports one `MFG_BG3D` gate with
set/clear/status offsets `0x4`/`0x8`/`0x0` and `mfg_sel` as its parent. Base
Linux 7.1.3 already has the parent clock IDs but no MT6797 MFG provider. A normal
MediaTek set/clear gate with a disabled-only `g3d_config` node is the reusable
mainline shape; the vendor power-gate ABI is not copied. Live debugfs reports
the MFG PLL/gate tree at 500.5 MHz and the 52 MHz/infra MFG gates at 156 MHz,
but all MFG power gates were idle during capture.

Patches 47–50 implement this boundary without enabling a consumer: the
generic SCPSYS driver gains separate SRAM control/ack offsets and the
evidence-backed MFG/core hierarchy, while a normal `mt6797-mfgsys` gate
provider and disabled DTS node expose `MFG_BG3D`; the final patch also keeps
the vendor-required `mfg_52m` preclock prepared during MFG power sequencing.
The prior 53-patch Linux 7.1.3 series, including the disabled RT5735 VSEL0
provider, disabled BMI160 candidate, and board-specific TOPRGU watchdog IRQ,
compiled successfully in the VM as package
`linux-7.1.3-gemini-9d32920801da`; that historical patchset had SHA-256
`9d32920801dae5415e5e685e76337e7a442c64588fadb84f37aafc0be618f5f5`.
The previous 69-patch series added the generic FUSB301 Type-C controller,
disabled MT6797 thermal/AUXADC variant, disabled MT6797 Panfrost and DPI
boundaries, and source-derived disabled MT6797 T-PHY/MTU3/xHCI USB3 topology
on top of the FAN49101 regulator and AW9523/matrix-keypad candidates, plus
compile-tested MT6797 USB11 MUSB match data and binding support; its patchset
SHA-256 is
`e632d05762cec3b22d45bcf4e48cb56a19ccffe7e0e413f6ced8c97d7d5f5f37`.
The previous target DTB, bindings, FUSB301/FAN49101 driver objects, existing
STK3310 sensor object, MT6797/MT6351 ASoC objects, USB3 binding examples, and
the focused USB11 MUSB object checks validate; the complete package build passed as
`linux-7.1.3-gemini-e632d05762ce`; its complete checksums and 119-DTB
manifest are recorded in the
[69-patch integration result](../../experiments/2026-07-13-kernel-integration/results/mainline-69-patch-build-current-20260713.txt).
The merged kernel configuration hash is
`01f1ce5e6f1a64d29d72e3e01c88cbe0a8f769a10b226f0b79cbbc4d92206b59` and
includes `CONFIG_STK3310=m`, `CONFIG_SND_SOC_MT6797=m`, and
`CONFIG_SND_SOC_MT6797_MT6351=m` without Gemini sensor or audio-card nodes.
The earlier 69-patch keyboard DTB, binding/schema, and focused object-build
evidence remains in
[`mainline-keyboard-dtb.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-keyboard-dtb.txt).
The FAN49101-specific validation is in
[`fan49101-mainline-validation.txt`](../../experiments/2026-07-12-charger-power-recovery/results/fan49101-mainline-validation.txt).
These are build results only, not runtime power-on evidence.

The current 72-patch working series adds the USB11 MUSB match data, a
PIO-first Kconfig selection, and the disabled USB11 MUSB/T-PHY topology. Patch
0067 also permits the one-entry `interrupt-names = "device"` tuple observed in
the MT6797 USB3 contract; the generated full schema now validates the Gemini
DTB without the earlier short-tuple warning. Its focused DTB/object checks and
complete package build pass. The reproducible
artifact is `linux-7.1.3-gemini-c2d9eea95daa`, with current source, patchset,
config, Image, Image.gz, and Gemini-DTB SHA-256 values recorded in the
[current package validation](../../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-c2d-reconciliation-20260714.txt),
and 119 validated DTBs. The current package also carries an LK-compatible
`Image.gz`; complete evidence is in the
[current LK-compatible integration result](../../experiments/2026-07-12-boot-contract-recovery/results/mainline-72-lk-candidate-current-20260714.txt).

The SPM debugfs endpoint names vendor PCM images for suspend, SODI, deep-idle,
and vcorefs. Only names and sizes are retained in the private capture; no
firmware contents or redistribution rights are assumed. See the
[clock/power/reset recovery experiment](../../experiments/2026-07-12-mt6797-clock-power-reset-recovery/README.md)
for the method and sanitized values.

The vendor AFE aperture is 64 KiB, while Linux 7.1.3's binding example uses
4 KiB. The upstream driver limits access to `AFE_MAX_REGISTER = 0x84c`, so a
4 KiB resource covers its current register set. Preserve the discrepancy as a
review question rather than silently copying either size.

## CPU topology, PSCI, and architectural timer

The live flattened DT exposes ten CPUs: Cortex-A53 nodes at MPIDRs `0x000`–
`0x003` and `0x100`–`0x103`, and Cortex-A72 nodes at `0x200` and `0x201`. All
use `enable-method = "psci"` and the firmware release address `0x40000200`.
The descriptive DT frequencies are 1.391 GHz, 1.950 GHz, and 2.288 GHz for the
three groups; they are not an OPP/voltage contract. The PSCI node is
`arm,psci-0.2` over SMC with the standard SMCCC IDs `0x84000001` through
`0x84000004`.

The architectural timer is `arm,armv8-timer`, with GIC PPIs 13, 14, 11, and 10
and a 13 MHz counter frequency. The running downstream kernel selects
`arch_sys_counter` and `arch_sys_timer`; MT6797 `cpuxgpt` IRQs are separate
vendor timers. Linux 7.1.3's generic PSCI and `arm_arch_timer` implementations
therefore match the observed contract and do not need a new CPU/timer driver.

The downstream DT also names vendor idle states with PSCI parameters
`0x00010000` and `0x01010000`. They depend on MT6797 SPM/PCM firmware and remain
disabled in the local mainline description until a booted kernel proves their
semantics. The global downstream CPU masks were observed to disagree
transiently with per-CPU sysfs and `/proc/stat`; this is recorded as a reporting
contradiction rather than a stable CPU-count fact.

Candidate N supplies the first mainline runtime result for a secondary core on
this unit. With boot-time `maxcpus=1` retained, the live Linux CPU1 `of_node`
resolved to `/cpus/cpu@1`; one standard hotplug request returned success.
Kernel lines identify GICv3 redistributor index 1 in region 0 and MPIDR `0x1`
with MIDR `0x410fd034` (Cortex-A53). The online mask changed from `0` to `0-1`,
two early `/proc/stat` samples showed advancing CPU1 accounting, and CPU1
remained online through the last 25-second marker before watchdog recovery.
This establishes generic PSCI reuse for that one CPU_ON path in one run, not
repeatability, boot-time SMP, CPU2–9, stress, coherency, DVFS, idle, or thermal
behavior. See the [Candidate N runtime record](../../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt).

See the [CPU/PSCI/timer recovery experiment](../../experiments/2026-07-13-cpu-psci-timer-recovery/README.md)
and its [source validation](../../experiments/2026-07-13-cpu-psci-timer-recovery/results/mainline-cpu-psci-timer-validation.txt).

## CPU DVFS, thermal, idle, and suspend

The live device has a ten-CPU topology (`possible=0-9`, `present=0-9`) with
CPUs 0 and 1 online during the 2026-07-12 capture. The vendor cpufreq ABI is
per-CPU (`/sys/devices/system/cpu/cpu*/cpufreq`), but CPU0 and CPU1 both report
`affected_cpus=0 1`, `related_cpus=0 1 2 3`, and driver `mt-cpufreq`. The
sampled LITTLE policy is `interactive`, with a 16-entry 221--1547 MHz table,
current limits 624--1547 MHz, and a reported 1000 ns transition latency.
Vendor `/proc/cpufreq` diagnostics expose separate LL, L, B, and CCI tables;
the frequency/voltage table contents are calibration-dependent and remain in
the private capture rather than this document. A fresh 2026-07-14 capture
found no standard `cpufreq/policy*` directories and recorded the active
vendor interface under `/proc/cpufreq`; its instantaneous states were LL
1014 MHz, L 325 MHz, B 845 MHz, and CCI 611 MHz. Existing dmesg shows live
LL/L/B/CCI transitions, and an earlier bounded probe observed CPU 4 online,
so the online mask is dynamic rather than a topology description. See the
[runtime CPU-policy result](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/runtime-cpu-policy-20260714.txt).

The Planet MT6797 source implements a complete DVFS path in `mt_cpufreq.c`,
`mt_cpufreq_hybrid.c`, EEM/PTP, and the MT6797 PLL provider. It has three CPU
clusters (LL, L, and B) plus CCI, with function-code efuse index 22 and
date-code efuse index 61 selecting four table levels; a B-cluster TT segment
can rewrite the top entries. The source directly accesses LL/L/CCI PLL
windows at `0x200`/`0x210`/`0x220`, a backup PLL window at `0x230`, and divider
selects at `0x270`/`0x274`; the B cluster uses a special BigiDVFS path.
DA9214/ext-buck and SRAM tracking enforce
`Vsram >= Vproc`, a 10--30 mV difference, and 1000--1200 mV Vsram limits while
frequency hopping and CCI coupling are in flight. The live table is therefore
calibration evidence, not a board OPP table.

The CPU clock registers are not ordinary freely-owned MMIO. The vendor
frequency-hopping source maps MCUMIXED `0x1001a000` and serializes every access
through the DVFSP/CSPM hardware semaphore at `0x11015000 + 0x440`, including
local-IRQ masking and a 2000 µs timeout. Its comments identify ATF, SPM, and
the kernel as competing owners. The B-cluster PLL, post-divider, SRAM-LDO, and
control operations instead go through secure BigiDVFS SMCCC services. This
makes a direct writable CCF mapping unsafe; a dedicated MT6797 CPU-clock
backend is justified even though the generic MediaTek PLL math and cpufreq/OPP
framework remain reusable. The source-derived field map and staged ownership
plan are in the [CPU clock backend source design](../../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend.md) and the [current 72-patch source audit](../../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend-current-72-20260714.txt).

The vendor EEM/PTP block is active calibration logic for the same CPU domains.
BIG/L/2L/CCI detectors use banks 0/3/4/5 and INIT01/INIT02/MON phases to turn
efuse and hardware VOP results into mutable 16-entry voltage tables. Thermal
offsets, VMIN/VMAX clamps, and `recordTbl` caps are applied before the vendor
calls `mt_cpufreq_update_volt*()`. This is why a static downstream OPP table
cannot be treated as the final voltage contract.

The optional hybrid DVFSP path maps `CSPM` at `0x11015000`, a 12 KiB CSRAM
window at `0x0012a000`, and runs an embedded PCM instruction array behind the
vendor `mediatek,mt6797-dvfsp` node. This is a vendor firmware/register ABI,
not a Linux `firmware-name` contract. Do not copy the PCM array or enable
guessed OPP voltages.

Suspend and deep-idle add a separate vendor firmware boundary. The SPM v2
`mt_spm.c` implementation maps the vendor `mediatek,sleep` block together
with MT6797 topckgen, infracfg, mcucfg, apmixed, efuse, thermal, DDRPHY,
vcorefs, and system-CIRQ nodes; its dynamic PCM path can call
`request_firmware`. `mt_spm_vcorefs_mt6797.c` contains another embedded
vcore-DVFS PCM image. `mt_idle_mt6797.c` only enters dpidle/soidle/mcidle after
multimedia clock, power-domain, and PLL checks pass, and the MT6797 dpidle
hooks change PMIC-wrapper state plus MIPID/MIPIC/MDPLLGP/SSUSB 26 MHz clocks.
These paths are not equivalent to naming a generic PSCI idle state, so the
mainline series leaves them disabled and does not redistribute the embedded
or dynamically loaded images.

The vendor DT resource nodes are:

| Block | Register windows | IRQ | Vendor resources | Mainline status |
| --- | --- | --- | --- | --- |
| thermal controller | `0x1100b000 + 0x1000` | SPI 78 LOW | `INFRA_THERM` (`therm-main`) | Linux 7.1.3's generic `auxadc_thermal` bank architecture is reusable; patch 0057 supplies MT6797 timing, valid-mask, buffer, IRQ/protection, and conversion data. `CONFIG_MTK_SOC_THERMAL=m` now packages the module, but the DT resource remains disabled pending calibration and runtime safety evidence |
| thermal AUXADC | `0x11001000 + 0x1000` | SPI 74 | `INFRA_AUXADC` (`auxadc-main`) | Reuse the generic `mt6577_auxadc` register-shape layer as a candidate for channel 11 and the clock contract; the packaged module is present, but keep the node disabled until the indirect thermal-controller path is implemented and validated |
| EEM/PTP calibration | `0x1100b000 + 0x1000` (shared with thermal controller) | SPI 129 LOW | `MFG_BG3D`, `SCP_SYS_MFG`, `INFRA_THERM` | no MT6797 EEM/SVS match; Linux SVS phase/error and OPP-adjustment patterns are reusable, but MT6797 EEM register, efuse, clock/power, and DA9214 contracts need a dedicated variant/provider; do not add an independent overlapping MMIO node |
| DVFSP/CSPM | `0x11015000 + 0x1000`; CSRAM `0x0012a000 + 0x3000` | SPI 161 LOW | `INFRA_I2C_APPM` (`i2c`) | no mainline driver or binding |

The TOPRGU watchdog is a separate always-on safety resource at
`0x10007000`. The vendor DT and live flattened tree agree on `GIC_SPI 137`
with falling-edge polarity; the vendor kernel reports this as global IRQ169
(`mt_wdt`) with zero events in the sample. The vendor WDK emits an external
watchdog keepalive about every 20 seconds, but it does not expose Linux's
standard watchdog core or `/dev/watchdog`. Linux 7.1.3 already implements the
same register keys, timeout conversion, restart sequence, and reset-controller
shape through `mtk_wdt`; the Gemini board DTS patch only adds the missing bark IRQ to the
board node. The private WDK, SPM request bits, modem watchdog routes, and
reset policy remain evidence, not mainline ABI. See the [watchdog recovery
experiment](../../experiments/2026-07-12-mt6797-watchdog-recovery/README.md)
and its [mainline design result](../../experiments/2026-07-12-mt6797-watchdog-recovery/results/mt6797-watchdog-mainline-design.md).
The Linux probe may write `WDT_LENGTH` and reload `WDT_RST` if firmware left
TOPRGU enabled, so a first mainline probe is state-changing until a quiescent
handoff is proven; see the [probe safety audit](../../experiments/2026-07-12-mt6797-watchdog-recovery/results/watchdog-probe-safety-audit-20260713.txt)
and the [current 72-patch boot-policy audit](../../experiments/2026-07-12-mt6797-watchdog-recovery/results/mainline-watchdog-current-72-policy-20260714.txt).
The current config also sets `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`, which
keeps a firmware-running timer pinged before userspace takes over.

Candidate L runtime evidence showed that `/dev/watchdog0` was still absent
about five seconds into its external-init discovery loop. This does not make
the vendor/live falling-edge description invalid: the exact mainline tree
inherits MediaTek SYSIRQ, whose driver programs the polarity inverter and
translates falling edge to rising for the parent GIC. The optional bark mapping
and request remain unproven, however, and `mtk_wdt_probe()` returns before
watchdog registration if that request fails.

Candidate M kept L's exact kernel and omitted the optional IRQ only in its
diagnostic DTB. Its surviving `console-ramoops` proves that the live omission
survived LK, `10007000.watchdog` successfully bound to `mtk-wdt`,
`/dev/watchdog0` appeared with a 31-second timeout and no pretimeout interface,
and one userspace handoff ping armed the timer. The durable sequence reached
30 seconds after the handoff and the owner observed an automatic return to
Gemian; Gemian then reported `wdt_by_pass_pwk`, `powerup_reason=reboot`, and
both PMIC watchdog-reboot flags set. This establishes the basic single-stage
TOPRGU timeout/reset path and strongly isolates the optional IRQ-bearing path
as L's registration blocker. It does not identify the request errno or prove
SPI137 polarity, bark, or pretimeout delivery. Retain the basic watchdog for
early recovery and investigate the optional bark path separately only when it
has a decision-changing consumer. See the [registration audit](../../experiments/2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt)
and [Candidate M runtime record](../../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt).

Candidate N retained that no-IRQ watchdog path, armed it before requesting
CPU1 online, and stayed observable through 25 seconds with CPU1 online before
the owner observed an automatic, unaided return. Gemian again reported
`wdt_by_pass_pwk` and `powerup_reason=reboot`; unlike M, both PMIC
watchdog-reboot fields were zero. Preserve this as a reset-reason propagation
discrepancy. The exact N `mtk-wdt` trace, its end near the nominal expiry
interval, the automatic return, and the watchdog-class boot reason together
still attribute recovery to the tested TOPRGU path. See the
[Candidate N runtime record](../../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt).

The live kernel enumerates 13 vendor thermal zones, all with
`mode=disabled` and `policy=backward_compatible`. `mtktscpu` was about 25.1 °C
and `mtktsbattery` 23.0 °C; `mtktspa=-127.0 °C`, `mtktsdram=2 m°C`, and
`mtktsimgsensor=-275.0 °C` are invalid/sentinel readings. The thermal IRQ is
global line 110, corresponding to vendor SPI 78, with zero count in the
sample. The live proc calibration fields were present and calibration was
enabled; the numeric gain/offset/temperature/ID/slope/VTS values remain in
the private capture and are intentionally not reproduced here.

The vendor source maps six logical banks to five sensor inputs: BIG/TS_MCU1,
GPU/TS_MCU4, SOC/TS_MCU2+TS_MCU3, CPU-L/TS_MCU2, CPU-LL/TS_MCU2, and
MCUCCI/TS_MCU2. It extracts gain, offset, calibration temperature, ID, slope,
and five VTS offsets from efuse words at `0x10206180`, `0x10206184`, and
`0x10206188`, then applies an ID-dependent integer raw-to-temperature formula.
The controller selects banks through `PTPCORESEL`, samples `TEMPMSR0..3`, and
uses AUXADC channel 11 plus indirect valid/voltage data. This is a distinct
thermal-controller/AUXADC contract rather than a generic IIO ADC-only path.

See the [MT6797 thermal recovery experiment](../../experiments/2026-07-13-mt6797-thermal-recovery/README.md),
its [source validation](../../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-source-validation.txt),
and the [current 72-patch package policy audit](../../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt),
and the disabled-only [resource patch](../../patches/v7.1.3/0046-arm64-dts-mediatek-mt6797-add-disabled-thermal-dvfsp-resources.patch).

CPU0 exposes vendor cpuidle states `dpidle`, `SODI3`, `SODI`, `MCDI`, `slidle`,
and `rgidle`/WFI. Only WFI had non-zero usage in the sample. The vendor DT
uses PSCI suspend parameters `0x0010000` and `0x1010000`; mainline currently
has the generic PSCI node but no MT6797 idle-state description. `/sys/power/state`
reports `freeze mem`, but no suspend was attempted. Recurring vendor logs say
DP/SODI3/SODI did not enter and show dpidle/soidle block counters, which is
evidence of vendor gating rather than proof that generic `mem` is safe.

Linux 7.1.3's generic ARM64/PSCI topology is reusable. Its MediaTek cpufreq
driver has no `mt6797` match and expects standard CPU/intermediate clocks,
regulators, and OPP bindings. Its voltage-tracking and clock-reparenting
helpers are useful above a proven MT6797 backend, but the direct PLL/mux,
efuse/date calibration, CCI, and DA9214 contract justify an MT6797 variant or
new driver if they cannot be represented by the generic data path. Linux also
has an MT6797 CCF provider for main/universal and peripheral PLLs, but its
current source exposes no ARMPLL definitions, CPU muxes, or CCI PLL clock;
adding only a cpufreq compatible would therefore leave the `clk_set_rate()`
path without a vendor CPU clock owner. Linux 7.1.3 also has a generic
MediaTek SVS provider with NVMEM calibration and
`dev_pm_opp_adjust_voltage()` support, but it matches only newer SVS SoCs and
does not cover the MT6797 EEM register/resource contract. Its generic
AUXADC and AUXADC-thermal drivers likewise have no `mt6797` match. The generic
AUXADC-thermal bank, shared-sensor, and calibration architecture can represent
the recovered topology, but MT6797 needs explicit variant data for its `0x2c`
valid mask, `0x492` filter, `0x30d` poll value, APMIXED buffer, IRQ/protection
path, and ADC-OE conversion. An unrelated SoC's calibration data must not be
reused. The current local boundary packages a disabled MT6797 thermal variant
and the generic AUXADC module; it still records only disabled DT resources.
A future chipset-specific cpufreq, thermal, or SPM driver must start disabled
and preserve explicit voltage,
calibration, and firmware safety boundaries. See the
[cpufreq/DTS API gap](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-cpufreq-dt-gap.md), the
[CPU/DVFS recovery experiment](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md)
and its [source-level mainline design result](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mt6797-pm-mainline-design.md),
the [CPU-DVFS source validation](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-cpufreq-source-validation.txt),
the [EEM/PTP calibration contract](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/eem-calibration-contract.md),
the reproducible [contract analyzer](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/scripts/analyze-mt6797-pm-contract.sh),
its disabled-only [patch 46](../../patches/v7.1.3/0046-arm64-dts-mediatek-mt6797-add-disabled-thermal-dvfsp-resources.patch),
and the historical 72-patch [PM validation](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-validation.txt).

## Sensors and IIO boundary

The live Gemini exposes the sensor bus as I2C1 at `0x11008000` (controller SPI
85, `INFRA_I2C1` and `INFRA_AP_DMA`). The physical-node names and vendor binding
state are:

| Address | Live node/name | Vendor driver state | Mainline interpretation |
| --- | --- | --- | --- |
| `0x30` | `msensor_mmc3530` | unbound | MMC3530 candidate; Linux 7.1.3 has no matching driver |
| `0x48` | `alsps` | vendor `stk3x1x` | STK3X1X-named ALS/proximity path; the upstream STK3310-family register model is a reuse candidate, but product/revision and board resources remain unverified |
| `0x5f` | `humidity` | unbound | Humidity candidate; vendor source calls it HTS221, while mainline uses `st,hts221` |
| `0x68` | `gsensor_bmi160` | vendor `bmi160_acc` | BMI160-compatible software path; static probe rewrites the client address to `0x69`; confirm the physical chip before selecting the upstream node |
| `0x69` | `gyro_bmi160` | vendor `bmi160_gyro` | Second vendor client in the legacy split; its probe also forces `0x69`, so do not infer a second physical chip |
| `0x6a`, `0x6b` | alternate `gsensor`/`gyro` | unbound | Vendor fallback nodes, not evidence of additional parts |
| `0x77` | `barometer` | unbound | Barometer candidate; vendor source calls it BMP280, while mainline uses `bosch,bmp280` |

The vendor kernel has no IIO devices and reports `CONFIG_IIO` unset. Its sensor
HAL instead creates misc/input classes for physical and fused logical sensors.
The vendor DTS separately lists LSM6DS3, BMI160, STK3X1X, MMC3530, BMP280, and
HTS221 configuration candidates; those descriptions must not be treated as
chip identity for every address. Public Gemian hardware notes also report
early X25 units with BMI160 instead of LSM6DS3, so the IMU choice is a board
variant question. Mainline should model one standard IMU per physical chip
after a safe identity probe.

The recovered probe code makes the address split explicit: both vendor probe
functions store `0x69` into the Linux `i2c_client.addr` field before their
register transactions. The gyro path validates an ID in `0xd0`–`0xd3`; the
accelerator path reads register `0x00` but does not visibly reject a mismatch.
This is software-path evidence only; the normalized disassembly is in the
[vendor IMU probe record](../../experiments/2026-07-12-sensor-iio-recovery/results/vendor-imu-probe.txt).

The current 72-patch package selects IIO and packages the BMI160, LSM6DSX, and
STK3310-family modules. Its Gemini DTB contains only a disabled BMI160 child
with the recovered mount matrix and no IRQ or supply properties; no STK3X1X,
LSM6DS3, MMC3530, BMP280, or HTS221 consumer is present. See the [current
sensor package audit](../../experiments/2026-07-12-sensor-iio-recovery/results/mainline-sensors-current-72-package-20260714.txt).

A fresh 2026-07-14 read-only capture reproduces the same eight I2C1 client
addresses and the same `stk3x1x`, `bmi160_acc`, and `bmi160_gyro` bindings. It
still exposes no IIO device; the legacy metadata remains direction 7 with
accelerometer/gyroscope event devices 5/6 and gyroscope status `0x69`/`V1.0`.
The private capture is mode-0600 under `artifacts/`; the sanitized comparison
is [`live-sensors-repeat-20260714.txt`](../../experiments/2026-07-12-sensor-iio-recovery/results/live-sensors-repeat-20260714.txt).

Linux 7.1.3 already provides `BMI160_I2C`, `BMP280_I2C`, `HTS221_I2C`, and an
LSM6DS3-family IIO driver, plus the closest MEMSIC `MMC35240` magnetometer
driver and an STK3310-family light/proximity driver. Patch 52 adds IIO configuration and a disabled-only standard
`bosch,bmi160` node at `0x69` with the recovered mount matrix. It intentionally
does not guess the two supplies or GPIO65 interrupt electrical mode. Static HAL disassembly shows that the legacy userspace decoder only
scales ABS X/Y/Z values; it does not apply that transform. Recover the
kernel-side `sign[]`/`map[]` matrix before writing a mainline `mount-matrix`;
the recovered table resolves direction 7 to
`sign={-1,-1,-1}`, `map={1,0,2}` (`out=(-raw_y,-raw_x,-raw_z)`), equivalent to
`mount-matrix = "0", "-1", "0", "-1", "0", "0", "0", "0", "-1"`.
The recovered BMI160 data paths apply the sign/map before the legacy
input-event boundary, so this is not a HAL-only convention.
The vendor STK3X1X register header and read-only kernel disassembly match the
upstream STK3310-family state/control, threshold, flag, data, and product-ID
(`0x3e`) model. The vendor ID test is broader than the upstream explicit ID
list, and the live product/revision bytes are not safely captured. Prepare the
existing `STK3310` module, but do not add a generic `sensortek,stk3x1x` alias or
enable a board node until the ID, VDD/VIO rails, and GPIO88/EINT11 contract are
verified. If those differ, add a chip-specific driver; MMC35240 reuse remains
unjustified. Virtual step, rotation, gesture, and fusion nodes remain userspace
policy. See the [STK3310 reuse audit](../../experiments/2026-07-12-sensor-iio-recovery/results/stk3310-reuse-audit.txt).

The captured HAL maps `m_alsps_misc` to input event 4, `m_acc_misc` to event 5,
and `m_gyro_misc` to event 6 through `*devnum` files. It then reads standard
Linux input events; no userspace I2C access is required for the vendor ABI. The
binary symbol table exposes STK3X1X and BMI160 register-level code but no
MMC3530 implementation, which is negative evidence against treating the
`0x30` DT node as a working magnetometer.

The normalized HAL event and scaling evidence is in the [axis contract](../../experiments/2026-07-12-sensor-iio-recovery/results/hal-axis-contract.txt).

The complete read-only capture, vendor-source audit, and Linux 7.1.3 file list
are in the [sensor/IIO recovery experiment](../../experiments/2026-07-12-sensor-iio-recovery/README.md).

## Storage

### Live controller description

| Property | MSDC0 / eMMC | MSDC1 / microSD |
| --- | --- | --- |
| Address | `0x11230000` | `0x11240000` |
| IRQ | SPI 79 LOW | SPI 80 LOW |
| Clock | `CLK_INFRA_MSDC0` (ID 33) | `CLK_INFRA_MSDC1` (ID 35) |
| Bus width | 8 | 4 |
| Maximum frequency | 200 MHz | 200 MHz |
| Media | non-removable | removable, card detect GPIO/EINT 67; vendor GPIO flags 0 and `cd_level = 1` |
| Advertised modes | MMC high speed, HS200 1.8 V, HS400 1.8 V | downstream source advertises SD high speed and SDR12/25/50/104 |
| Pinctrl | vendor inline pad settings | `default` and `insert_cfg`, plus downstream speed-specific drive settings |

The public 4.9 Gemini port enables MSDC0 with the same address, IRQ, 8-bit bus,
200 MHz ceiling, and eMMC modes. This is useful corroboration for an initial
read-only root/storage milestone. Its MSDC1 clock reference incorrectly points
at the MSDC0 gate, whereas the live tree resolves MSDC1 to clock ID 35; prefer
the live value.

The MT6797 register layout is not the older MT6795 variant currently present in
Linux 7.1.3. Vendor definitions show:

- a 12-bit clock divider and clock-mode bits at 20–22;
- `MSDC_PAD_TUNE0` at `0xf0` and `MSDC_PAD_TUNE1` at `0xf4`;
- separate `MSDC_PAD_TUNE0`/`MSDC_PAD_TUNE1` fields and downstream automatic
  tuning, including an HS400-specific path;
- a nominal 33-bit DMA mask in the downstream driver, but every GPD, BD, and
  payload address is truncated to 32 bits and SUPPORT64G is never enabled.

This makes the newer `mt6779_compat` shape a useful comparison, but it is not a
drop-in match. On MT6797, offset `0x228` is eMMC block length rather than the
newer FIFO configuration register, and the vendor map has no enhanced-RX
register at `0x64`. The local compatibility record consequently enables the
12-bit divider, asynchronous FIFO, and data tuning while leaving stop-clock
fix, enhanced RX, busy-check, and 64G DMA disabled.

A source-audited live snapshot confirms MSDC0 at 200 MHz, 8-bit MMC HS400 and
1.8 V signaling. Its PATCH_BIT1 bit 7 is set, SUPPORT64G is clear, the DMA high
address register is zero, and PAD_TUNE0 is active. MSDC1 had no card, a zero
clock, and powered-off IOS state. These results prove the vendor performance
ceiling but do not justify enabling HS200/HS400 on the first mainline boot. See
the [MSDC recovery experiment](../../experiments/2026-07-12-mt6797-msdc-recovery/README.md).

Downstream power code identifies the rail relationship:

- eMMC uses `VEMC`, nominally requested at 3.0 V with device-specific PMIC
  calibration;
- microSD card power uses `VMCH`, nominally 3.0 V;
- microSD I/O uses `VMC`, switching between 3.0 V and 1.8 V.

Therefore mainline `vmmc-supply`/`vqmmc-supply` wiring depends on real MT6351
regulator support. A fixed-regulator shortcut would lose voltage switching and
can be unsafe. The first MSDC0 test should cap the bus to a conservative mode
until the VEMC selector and calibration behavior are understood.

The local Gemini board DTS now wires eMMC `vmmc` to VEMC and `vqmmc` to the
fixed 1.8 V VIO18 rail. The latter is consistent with the live 1.8 V IOS state,
VIO18 being enabled, and established MediaTek eMMC board wiring, but remains a
hardware inference rather than a schematic-confirmed net name. It is marked
always-on initially because the vendor storage code never controls it and
other unmodeled consumers may share the rail. MSDC0 is capped at 25 MHz with
no high-speed capability flags for the first boot.

The source hashes, compatibility-field decisions, and bring-up gates are
recorded in the [MT6797 MSDC mainline design](../../experiments/2026-07-12-mt6797-msdc-recovery/results/mt6797-msdc-mainline-design.md).

The current 72-patch Linux 7.1.3 series still carries the MT6797 MSDC
compatibility record and conservative Gemini eMMC node. It builds `Image`, all
arm64 DTBs, and the new `mt6797-gemini-pda.dtb` as the checksum-clean package
`linux-7.1.3-gemini-c2d9eea95daa`.
The complete package checksums and DTB manifest are recorded in the
[current integration result](../../experiments/2026-07-13-kernel-integration/results/mainline-72-patch-current-20260714.txt).
The storage-specific source/object validation is in
[`mainline-msdc-current-c2d-reconciliation-20260714.txt`](../../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-c2d-reconciliation-20260714.txt),
with the current source-contract, probe-safety, and pinctrl audits linked from
the [MSDC recovery record](../../experiments/2026-07-12-mt6797-msdc-recovery/README.md).
This remains build and source-contract validation only and has not been
flashed or booted.

The storage probe itself is not passive. Linux `mtk-sd` enables clocks, resets
and programs the controller before calling `mmc_add_host()`; the MMC core then
powers up and schedules eMMC identification. `set_ios()` may change VEMC and
VIO18 through the MT6351 regulator framework, and voltage switching may select
the UHS pinctrl state. The current 25 MHz/no-HS board policy is conservative
but does not eliminate those ownership transitions. The complete classification
and source hashes are in the [MSDC probe-safety audit](../../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-probe-safety-audit-20260714.txt).

The same live DT describes an RT9466 at I2C0 `0x53`, including a
`primary_charger` label and charge-current/voltage limits, but that device is
unbound. The running charger driver is BQ25890 at `0x6b`, named
`sw_charger` with the vendor compatible `mediatek,sw_charger`; I2C0 `0x70` is
named `buck_boost` and is bound to FAN49101. An old `bq24261@6b` node is also
present under a different DT path, but it is an alternative description at the
same address. This is a concrete warning that an enabled-looking vendor node
can be an inactive board alternative: the RT9466 settings and stale BQ24261
node are not evidence for the populated charger.

Linux 7.1.3 already has a BQ25890 power-supply driver and binding, so the
standard core can be reused once the exact silicon ID, interrupt, battery and
system-rail wiring, and conservative charge limits are proven. The refreshed
2026-07-13 capture and source comparison show that the vendor register map is
the standard 21-byte BQ25890 window, but the vendor presence check only reads
register `0x03`; it does not prove a BQ part number. Linux additionally checks
the `0x14` part/revision fields and rejects unknown devices. The bounded
[BQ25890 reuse audit](../../experiments/2026-07-12-charger-power-recovery/results/bq25890-reuse-audit-20260713.txt)
records this distinction. Linux's
FAN53555 regulator is not a safe name-based substitute for FAN49101: the
vendor source identifies manufacturer register `0x40` as `0x83`, reads die ID
register `0x41`, and programs VOUT register `0x01` with a 603 mV base, 12.826
mV steps, and bit 7 as enable. Patch 0055 adds a dedicated
`onsemi,fan49101` regmap driver/binding and a disabled I2C0 `0x70` node. Its
probe is read-only and requires manufacturer `0x83`; the post-recovery vendor
probe logged manufacturer `0x83` and die ID `0x06`, but reset/control semantics,
mainline die-ID handling, rail ownership, and safe readback still need
board-level evidence before enabling it. The bounded
[FAN49101 register contract](../../experiments/2026-07-12-charger-power-recovery/results/fan49101-register-contract.txt)
records the source hashes and safe bring-up gates. The fresh vendor identity
capture is in
[live-charger-battery-recovery-20260714.txt](../../experiments/2026-07-12-charger-power-recovery/results/live-charger-battery-recovery-20260714.txt),
and the candidate's build and schema results are in
[FAN49101 validation](../../experiments/2026-07-12-charger-power-recovery/results/fan49101-mainline-validation.txt).
The vendor battery meter
and charger interface remain private HALs; they must be replaced by standard
power_supply plus IIO/fuel-gauge interfaces rather than copied wholesale. See
the [charger/fuel-gauge recovery experiment](../../experiments/2026-07-12-charger-power-recovery/README.md)
and its [mainline design result](../../experiments/2026-07-12-charger-power-recovery/results/mt6797-charger-mainline-design.md).

The current 72-patch package carries `bq25890_charger.ko`, `fan49101.ko`,
generic `bq27xxx` battery support, and `max17042_battery.ko`, but its Gemini
DTB leaves the charger controller and FAN49101 child disabled and contains no
BQ25890, RT9466, battery, or fuel-gauge consumer. The package therefore
establishes reusable code boundaries, not runtime support. The exact config,
module hashes, DT status checks, and repeated-run evidence are in the
[current charger package audit](../../experiments/2026-07-12-charger-power-recovery/results/mainline-charger-current-72-package-20260714.txt).

## PMIC wrapper, MT6351, and EINT

A source-audited wrapper read returned HWCID `0x5140` and SWCID `0x5120`,
confirming an MT6351 E2 rather than merely repeating its DT label. The full
method, regulator fields, RTC layout, and MFD plan are in the
[MT6351 recovery experiment](../../experiments/2026-07-11-mt6351-pmic-recovery/README.md).

The wrapper's real clock candidates are `CLK_TOP_MUX_PMICSPI` and
`CLK_INFRA_PMIC_AP`; both report 26 MHz live. The partial 4.9 port's dummy
40 MHz wrapper clock is not hardware evidence. Linux 7.1.3 already contains
MT6797 wrapper register data and the MT6351 16-bit slave regmap. Its pwrap data
requires a reset, while the upstream MT6797 infracfg driver registers none.
Historical code establishes simple reset banks at `0x120`, `0x124`, and
`0x128`, with pwrap at linear ID 64 (bank 2 bit 0). The local series now adds
that reset provider and a pwrap node with the recovered clocks, reset, SPI178,
and an MT6351 child whose level-high interrupt is EINT176.

The PMIC external signal follows pseudo-GPIO262 to EINT176, level high with a
1000 microsecond downstream debounce request. GPIO262 is outside the physical
GPIO0–261 range and must never be programmed as a normal pin. The EINT block's
parent is GIC SPI170. The decoded map also confirms GPIO67→EINT6 for microSD,
GPIO85→EINT8 for touch, and GPIO88→EINT11 for the light/proximity candidate.
The repeated decoder check is recorded in the [2026-07-14 EINT map
recheck](../../experiments/2026-07-12-mt6797-eint-recovery/results/eint-map-recheck-20260714.txt):
only the v5 capture contains the full decoded property, and its 172 entries
match the current Linux header; earlier inventory captures are negative
evidence rather than alternate maps.

The live EINT node also describes built-in EINT186 on alternate mux modes of
GPIO61, GPIO93, GPIO107, and GPIO181, plus four optional direct-to-GIC routing
slots targeting SPIs 206–209. No captured consumer uses the direct-routing
extension. The mainline summary-IRQ path therefore does not need to reproduce
that optional optimization for initial support.

This changes the dependency boundary: MT6351 MFD/IRQ support cannot work until
MT6797 EINT support exists. The local implementation uses the MediaTek core's
existing virtual-GPIO mechanism for EINT176 and EINT186 and leaves the physical
GPIO register ranges capped at 261. The subsequent local MFD patch adds the
confirmed four-bank, 64-source flat interrupt domain; regulator and board work
can now consume it instead of relying on fixed-regulator approximations. The
regulator series adds all nine bucks and 30 unique LDO controls. A mechanical
check ties every descriptor to the exact vendor register map, while live raw
reads prove the six reversed LDO selector tables and distinguish hardware
ON/sleep-controlled bucks from software-direct bucks.

The current 72-patch Linux 7.1.3 artifact compiles the MT6351 regulator and
MT6397 MFD/IRQ objects with `W=1`, passes the focused MT6351 regulator binding
check, and places the two eMMC rail consumers under the regulator container;
this remains source/schema validation only. The exact artifact, hashes, and
E2-only revision gate are recorded in the
[current MT6351 package validation](../../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-72-validation-20260714.txt),
the [MT6351 recovery record](../../experiments/2026-07-11-mt6351-pmic-recovery/README.md),
and the [probe-safety audit](../../experiments/2026-07-11-mt6351-pmic-recovery/results/mt6351-probe-safety-audit-20260714.txt).

Probe safety is a separate boundary: pwrap probe enables its clocks and writes
wrapper watchdog/timer/interrupt state even when firmware initialization is
already complete; an uninitialized wrapper also resets and reconfigures the
serial slave. MT6351 MFD probe masks all four PMIC interrupt-enable banks before
creating its IRQ domain. These are intentional ownership transitions, not
read-only identity checks. The packaged `mt6797-gemini-pda.dtb` contains
`pwrap`, `pmic`, and `mt6351regulator` with no `status` property, so all three
are enabled by the implicit Device Tree default and will be probed on a
mainline boot. The first mainline PMIC test therefore needs a non-primary boot,
external recovery, and before/after captures of wrapper state and PMIC masks.
See the [MT6351 probe-safety audit](../../experiments/2026-07-11-mt6351-pmic-recovery/results/mt6351-probe-safety-audit-20260714.txt).

The vendor pinctrl source itself is not a complete EINT map: it marks ordinary
pins `NO_EINT_SUPPORT` and leaves its EINT offset structure commented. The
dedicated MT6797 map and controller data are therefore a new mainline data
restoration, not a nearby-SoC driver reuse. See the [EINT/pinctrl recovery
experiment](../../experiments/2026-07-12-mt6797-eint-recovery/README.md) and its
[mainline design result](../../experiments/2026-07-12-mt6797-eint-recovery/results/mt6797-eint-mainline-design.md).

The buck analog readback is Gray-coded. Decoding it exactly matched the active
selector bank on all nine rails. This also exposed incorrect vendor diagnostic
voltages for five hardware-controlled bucks: that diagnostic always read the
inactive direct selector. VPA is a separate vendor defect—the hardware field is
six bits, so the confirmed 6.25 mV formula reaches 0.99375 V, not the generic
1.39375 V claimed by an unused 128-entry descriptor. These observations define
driver mechanics only; they do not establish safe OPP, coupling, ramp, or
suspend policy.

## M4U and SMI topology

The downstream M4U table describes one multimedia M4U with seven larbs. Larb 0
routes through M4U slave 1; larbs 1–6 route through slave 0. The vendor
translation-fault ID is `(larb << 7) | (port << 2)`. Mainline DT port IDs should
use the standard MediaTek `MTK_M4U_ID(larb, port)` encoding, not the fault ID.

| Larb | Ports | Functional clients |
| ---: | ---: | --- |
| 0 | 0–7 | primary OVL/RDMA/WDMA, 2-layer OVL, primary MDP RDMA/WDMA/WROT, fake |
| 1 | 0–9 | video decoder MC/PP/UFO/VLD/prediction/tile clients |
| 2 | 0–13 | camera output/statistics/raw clients |
| 3 | 0–14 | video/JPEG encoder and decoder clients |
| 4 | 0–3 | MJC motion/DMA clients |
| 5 | 0–9 | secondary OVL/RDMA/WDMA, overdrive, secondary MDP, fake |
| 6 | 0–9 | camera image input/output and DPE DMA clients |

The live driver binds `10205000.m4u` at Linux IRQ188, corresponding exactly to
SPI156. It had handled zero interrupts at capture and exposes no IOMMU groups.
All nine topology clocks are prepared once but gated, normally at 325 MHz; no
separate M4U block clock is exposed. See the
[M4U/SMI recovery experiment](../../experiments/2026-07-12-mt6797-m4u-smi-recovery/README.md).

The M4U register contract selects upstream generation-1 invalidation offset
`0x38`, legacy IVRP encoding, reset/non-standard AXI handling, and the generic
`2 << 4` translation-fault protection selection. A dedicated MT6797 record
must omit both `HAS_BCLK` and the MT8173-specific fault-protection flag. A
read of always-on INFRACFG_AO `0xf00` returned `0x6d403a00`; bit 13 is set and
directly confirms that the 4-GiB remapping path is active. The SMI larbs use
their bitmap MMU-enable register
at `0xfc0`; SMI common initializes bus selection to `0x1554`, encoding one
two-bit field per larb. Linux 7.1.3 has no MT6797 M4U/SMI matches or
`mt6797-larb-port.h`, so copying MT6795's five-larb records is unjustified.

Live M4U control reads close the remaining initialization ambiguity. Offset
`0x38` is `3`; AXI and DCM-disable are zero; write-length bit 5 is clear;
control is `0x22`; and the older coherence, separate in-order-write, and
table-walk registers at `0x80`/`0x84`/`0x88` are `3`/`0`/`0`. The local
platform record therefore enables upstream write-throttling handling and a
dedicated legacy-misc path that reproduces those three vendor writes.

Linux 7.1 also omitted the CAM gate block at `0x1a000000` and MJC gate block at
`0x12000000`. The local clock patches add their seven and six public vendor
gates respectively; both new objects pass a `W=1` build. This closes the clock
dependency for describing larb2 and larb4, but does not yet establish runtime
M4U support.

The local IOMMU/SMI patches add a mechanically verified 71-port header,
dedicated M4U and SMI records, and a complete disabled SoC topology. The port
checker matches every name and larb/port tuple to the exact downstream table
and reports 63 ports on vendor slave 0 and eight larb0 ports on slave 1. Both
driver objects build with `W=1`; focused bindings and all MT6797 DTBs validate.
The complete 25-patch series also builds and packages with checksum-clean
provenance. Runtime remains unknown because the new fabric nodes are disabled.

The source-level check is reproducible with the [M4U/SMI contract
analyzer](../../experiments/2026-07-12-mt6797-m4u-smi-recovery/scripts/analyze-mt6797-m4u-smi-contract.sh)
and its [mainline design result](../../experiments/2026-07-12-mt6797-m4u-smi-recovery/results/mt6797-m4u-smi-mainline-design.md).
The analyzer preserves an important generation distinction: MT6797's M4U
larb MMU-enable register is `0xfc0`, matching Linux's MT8167 helper; the
nearby MT8173 helper uses `0xf00` and is not interchangeable.

The Mali GPU is absent from this M4U port list and exposes its own MMU IRQ.
Panfrost must not receive an MT6797 M4U `iommus` property without new evidence.

## Camera and SENINF boundary

The live vendor system identifies the active camera path as
`sp5509mipirawsls` (`/proc/AEON_CAMERA1`); `/proc/AEON_CAMERA0` reports
`non_sensor`. The runtime wrappers are `2-002d` (`camera_main`), `2-0072`
(`camera_main_af`/`MAINAF`), `3-000c` (`camera_sub_af`/`SUBAF`), `3-0036`
(`camera_sub`), and `8-0036` (`camera_main_hw`). Platform consumers are
`1a040000.kd_camera_hw1`/`image_sensor`, `1a040000.kd_camera_hw2`/
`image_sensor_bus2`, and `seninf0`–`seninf7`. These wrapper addresses and
modaliases describe vendor plumbing, not the sensor's physical address or
register identity.

The live I2C adapter topology maps the wrapper buses to `i2c2=0x11013000`,
`i2c3=0x11014000`, and `i2c8=0x11009000`. No pre-existing sysfs client object
was present at candidate sensor addresses `0x20` or `0x28` on buses 2, 3, or 8;
the collector only checked object existence and issued no I2C transaction. The
absence is therefore consistent with a dynamically created vendor client, not
evidence for or against either physical address.

The Planet vendor DTS supplies camera clocks and `vcama`/`vcamd`/`vcamaf`/
`vcamio`, with board pin groups for camera reset GPIO32/33, power-down GPIO28/29,
and rail GPIO73/254. The pinned vendor tree also contains a monolithic
`camera_isp.c` implementation: twelve private platform-compatible nodes cover
IMGSYS/DIP/CAMSYS/CAMTOP/CAM A/B and six CAMSV windows, while the legacy
initialization path explicitly maps SENINF0–3 and uses inner IMGSYS offsets for
additional receiver state. Its DTS declares CAMTOP/CAM A/B and CAMSV IRQs
247–249 and 252–257 (level-low), and its source configures camera output/raw
M4U ports on larb2 plus image/DPE ports on larb6. Six CAMSV register/IRQ nodes
but only CAMSV0–2 clocks and configured M4U ports are an unresolved source
discrepancy; do not enable by node count. The private `/dev/camera-isp`
ioctl/mmap ABI is evidence only, not a mainline interface. See the [MT6797
camera pipeline contract](../../experiments/2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md).

The live capture has not yet established which sensor address, CSI-2 lane
count/link frequency, mode table, orientation, or AF actuator is fitted. A
bounded disassembly of the immutable vendor-kernel ELF recovers the SLS probe
transaction: 300 kHz, register `0x0f16`, raw ID `0x0556`, and candidate write-ID
bytes `0x40`/`0x50` (7-bit `0x20`/`0x28`). These are candidate design inputs,
not proof of the populated address or board sequencing; no streaming or
camera-register write was attempted.

The same ELF contains shared resource labels for `vcamd_sub`, `vcamaf`,
`vcama_sub`, `vcama_main2`, `vcamd_main2`, `vcamio_sub`, `vcamio_main2`, and
cam0/cam1/cam2 reset, power-down, and camera-LDO pin states. The vendor
`kdCISModulePowerOn` path is table-driven, so these labels do not recover the
exact SP5509 rail/reset order or module mapping.

Linux 7.1.3 contains a generic OV5675 V4L2 sensor driver and MT6797 camera
clock data, but no SP5509 driver and no matching MT6797 SENINF/CSI/CAM/CAMSV/ISP
media pipeline. The correct mainline boundary is therefore a new SP5509
sensor driver/binding plus a new MT6797 pipeline integration, reusing existing
clock, SMI/IOMMU, power, and reset providers only where the recovered contracts
match.
See the [camera recovery experiment](../../experiments/2026-07-13-camera-recovery/README.md)
and its [source-validation result](../../experiments/2026-07-13-camera-recovery/results/mainline-camera-source-validation.txt).
The [SP5509 ELF validation](../../experiments/2026-07-13-camera-recovery/results/sp5509-vendor-elf-validation.txt)
records the bounded symbol/disassembly evidence.
The staged [mainline camera design boundary](../../experiments/2026-07-13-camera-recovery/results/mt6797-camera-mainline-design.md)
maps these vendor objects to the standard V4L2/media-controller pieces still
needed.

## CMDQ/GCE contract

The Global Command Engine at `0x10212000` is live and actively executes the
Gemian display command queue. Its `mtk_cmdq` handler is registered as Linux
IRQ184, exactly SPI152 plus the GIC SPI base, and had handled 3,427 interrupts
across the reported CPU columns. The `infra_gce` clock is infracfg ID 10 at
136.5 MHz; it is unprepared and disabled at an idle sample and was observed
enabled during a source-audited status read, confirming activity-based gating.

The downstream DT also lists SPI153, but the vendor source requests it only
for an optional proprietary secure-world configuration. That interrupt is not
registered on this Gemian build. Mainline's GCE mailbox binding accepts one
interrupt and must describe only normal-world SPI152; secure display support
is a separate architecture problem, not a second upstream mailbox IRQ.

MT6797 has 16 threads with an active-low `0xffff` normal IRQ bitmap, a
0x80-byte thread stride, slot-cycle value `0x3200`, and direct unshifted
32-bit command-buffer addresses. Threads 12–14 are reserved by the vendor
stack for secure primary display, secondary display, and MDP. These mechanics
match Linux 7.1's MT8173 GCE platform record exactly: 16 threads, address
shift zero, and no software global-control fields. The local DTS therefore
uses `mediatek,mt6797-gce` with `mediatek,mt8173-gce` as its fallback rather
than adding duplicate mailbox driver data.

The vendor driver dynamically replaces logical event-enum values with SoC
values from DT. Mechanical comparison recovers 26 subsystem selectors and
112 event macros and matches 141 numeric properties across the pinned source,
running DT, and local header. MT6795's header cannot be reused: OVL0 SOF is 10
instead of 11, mutex0 stream EOF is 58 instead of 52, and DSI0 TE is 70
instead of 2. Live history confirms primary display on thread 0/priority 4,
primary memory output on thread 4, trigger loop on thread 7/priority 2, ESD
checks on thread 6, and screen capture on thread 3. See the
[CMDQ/GCE recovery experiment](../../experiments/2026-07-12-mt6797-cmdq-gce-recovery/README.md),
its [source contract analyzer](../../experiments/2026-07-12-mt6797-cmdq-gce-recovery/scripts/analyze-mt6797-cmdq-contract.sh),
and [mainline design result](../../experiments/2026-07-12-mt6797-cmdq-gce-recovery/results/mt6797-cmdq-mainline-design.md).

The local provider is enabled because GCE is an independent infrastructure
mailbox and requires no multimedia power domain or consumer to probe. No
display or other client is attached yet. The mailbox object passes `W=1`, the
binding validates, and all three MT6797 DTBs pass the focused schema check.
The complete checksum-clean package is
`linux-7.1.3-gemini-daf0521e6e67`, derived from patch-set SHA-256
`daf0521e6e677586719b3dc3bae05f5f1dc1c41bb58f6d89d2085e6e109be390`;
mainline runtime remains untested.

## MMSYS routing and reset contract

MT6797's MMSYS router occupies `0x14000000`–`0x14000fff`. Its display route
registers span `0x034`–`0x0a0`; two active-low 32-bit software-reset banks are
at `0x140` and `0x144`. The retained active Gemian dump reports both reset
banks as `0xffffffff`, and the local Linux record exposes them as 64 linear
reset IDs. The complete aperture is reachable by GCE through
`SUBSYS_1400XXXX`, offset zero, size `0x1000`; mailbox channels remain deferred
until a DRM consumer's thread and priority are independently established.
The panel `LCM_RST_B` output at `0x150` is separate from those two banks and is
not represented by the 64 linear reset IDs. The active vendor callback writes
0/1 to it directly; treating it as software-reset ID 64 would be incorrect.

The source-defined graph has five MOUT registers, five output selectors, and
twelve input selectors. Linux 7.1 can express 29 high-level routes. Each route
through vendor-only `OVL0_VIRTUAL` or `PATH0` is collapsed into multiple
`MMSYS_ROUTE()` writes for the adjacent Linux component pair; the generic core
already executes every matching entry. Routes involving `SPLIT0` and the
dual-DSI pseudo-component remain unsupported because the current DDP component
enum has no corresponding ID. They belong to the inactive R63419 dual-panel
alternative, not the Gemini's observed single-DSI path.

The source-audited `mtkfb` ring buffer retained this active path after the
display later entered sleep:

```text
OVL0-2L -> OVL1-2L -> OVL0 virtual -> COLOR0 -> CCORR -> AAL ->
GAMMA -> OD -> DITHER -> RDMA0 -> PATH0 -> UFOE -> DSI0
```

The decisive route values are OVL0/OVL1 output selectors `1`/`1`, virtual OVL
input `2`, OVL0/COLOR0 MOUT/SEL `1`/`1`, DITHER MOUT `1`, RDMA0/PATH0/UFOE
selectors all zero, and UFOE MOUT/DSI0 SEL `1`/`0`. The local checker matches
22 register offsets, all 29 collapsed routes, the 12 writes needed by this
active high-level chain, both reset banks, and the GCE tuple against the exact
Gemian and Linux trees. The full 32-patch series builds as
`linux-7.1.3-gemini-b2a58d835666`, with patch-set SHA-256
`b2a58d835666dc2a3bd5fa4cea4d218f654ced21ac4cc686d3ec457da7faea04`.

See the [MMSYS routing recovery experiment](../../experiments/2026-07-12-mt6797-mmsys-routing-recovery/README.md).

## Primary DRM component contract

The retained active display state distinguishes the real blocks from the
routing pseudo-components. Its primary hardware chain is OVL0, OVL0-2L,
OVL1-2L, COLOR0, CCORR, AAL, GAMMA, OD, DITHER, RDMA0, bypassed UFOE, and DSI0.
`OVL0 virtual` and `PATH0` exist only in the MMSYS routing model. At the latest
screen-sleep snapshot, all thirteen relevant gates remained prepared; every
rate-bearing gate reported 325 MHz. OVL0, both OVL-2L blocks, RDMA0, AAL, and
DSI0 also have registered live interrupt handlers at SPIs 213, 215, 216, 217,
223, and 229 respectively.

OVL uses the MT8173 register generation: layer addresses begin at `0xf40`, the
layer stride is `0x20`, and GMC fields are eight bits. MT6797 additionally
requires the data-path `LAYER_SMI_ID_EN` bit, as does upstream MT8167. OVL0 has
four layers while the two OVL-2L blocks have two usable layers each. The live
format word `0x010020ff` is upstream DRM `ABGR8888`: MT8173 ARGB8888 encoding,
byte swap, and alpha enable. RDMA0 uses the MT8173 generation too, including
its memory address at `0xf00`; the live FIFO field encodes 512 16-byte units,
establishing an 8 KiB FIFO.

COLOR begins at the MT8173 `0xc00` window. The remaining fixed functions use
the older register family, but unavailable proprietary implementation details
matter. In particular, Linux 7.1 unconditionally writes AAL output size at
`0x4d8`, while the complete retained MT6797 AAL register definition contains
no such register. A dedicated MT6797 data flag must suppress that write before
AAL is attached. The live `AAL_CFG=0x16` is vendor PQ policy, not a safe
upstream default. Patches 35–36 implement the missing-register guard and relay
default. CCORR uses 2.10 coefficients because the retained hardware fields are
12 bits; it remains in relay until a DRM CTM is installed. GAMMA exposes its
single 512-entry 10-bit LUT but also defaults to relay. OD stays in relay so
its internal dither does not compete with the exact-match separate DITHER
block. UFOE is physically present but its live `START=0x4` selects bypass.
DSI0 is a four-lane, burst-video MT8173-generation host with a retained 435 MHz
MIPI TX clock. Its command queue begins at `0x200`, VM command control begins at
`0x130`, and it lacks the newer shadow and size-control registers.

The MIPI-TX aperture shares MT8173 offsets but not its field layout. MT6797
places pre-divider at bits 3:2, post-divider at 6:4, and S2Q divider at 13:12;
the upstream MT8173 operations would instead write two TX-divider fields and a
post-divider across bits 9:1. MT6797's bandgap selector packing differs too.
The live clock/data lane words retain four-bit resistance trim at bits 11:8,
and the native sequence deliberately preserves those trim and bandgap voltage
fields. It uses divider ratios 1/2/4/8/16 over 50 MHz–1.25 GHz and pulses the
PCW-change register at `0x60` after PLL enable.

Patches 33–36 add the proven OVL/OVL-2L/RDMA and fixed-function compatibles
and platform data; they intentionally add no DT consumers. The 36-patch series
packages as `linux-7.1.3-gemini-dbe7c5051964`, patch-set SHA-256
`dbe7c505196402e7ed2cdd237da93b2b850d4de6df2dbb39a4a14a8fc3359a97`.
Patches 37–39 add a native DSI host record and MT6797-specific PHY clock
operations while retaining the common MediaTek host and PHY frameworks. The
contract checker matches the host offsets, native PLL fields, divider policy,
calibration preservation, PCW latch, and two compatibles. No DSI consumer is
attached, and runtime support remains untested. Both schemas, focused `W=1`
objects, and the full build pass. The 39-patch package is
`linux-7.1.3-gemini-3adec95a16dc`, derived from patch-set SHA-256
`3adec95a16dcc4882c6092961757dc46fe5167ed2c4a5bf3fc76eca37ab946e8`;
every exported manifest entry verifies at
`artifacts/20260712T133346Z/gemini-pda/linux-7.1.3-gemini-3adec95a16dc`.
Patch 40 adds disabled SoC-level MIPI-TX0 and DSI0 nodes with the recovered
addresses, SPI 229, MM power domain, DSI0 MM/interface clocks, PHY link, and
empty input/output graph ports. Both focused node schemas and the self-contained
MT6797 EVB/X20 DTBs pass; no display consumer or panel is enabled.
Patches 41–42 register the recovered 12-component primary path with the shared
MediaTek DRM master and add disabled SoC nodes for OVL0, both OVL-2L engines,
RDMA0, COLOR, CCORR, AAL, GAMMA, OD, DITHER, and UFOE. Explicit `ovl-2l0` and
`ovl-2l1` aliases preserve distinct DRM component IDs. The nodes use the exact
SPIs 213/215–217/221–227, native multimedia clocks, larb0/larb5 M4U ports, MM
power domain where permitted by the bindings, and GCE windows. All ten focused
schemas and all three canonical MT6797 DTBs pass; every node remains disabled
and no board graph is attached.
Patch 43 extends the shared NT36672E panel framework with the Gemini mode,
165 retained panel-register writes, provisional `outp`/`outn` supplies, and
descriptor-selected power/reset/suspend delays. Its board-specific compatible
has a dedicated binding, but no panel consumer is enabled and the binding does
not assert a TPS65132 identity. The full 43-patch package is
`linux-7.1.3-gemini-9b11c7717287`, from patch-set SHA-256
`9b11c7717287ddc4f4e80ef3f3ae993974a30439679896cef8e67ada97008593`;
all manifest entries verify in
`artifacts/20260712T153052Z/gemini-pda/linux-7.1.3-gemini-9b11c7717287`.
See the [DRM component recovery experiment](../../experiments/2026-07-12-mt6797-drm-component-recovery/README.md),
its [source contract analyzer](../../experiments/2026-07-12-mt6797-drm-component-recovery/scripts/analyze-mt6797-drm-contract.sh),
[current package validation](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt),
and [mainline design result](../../experiments/2026-07-12-mt6797-drm-component-recovery/results/mt6797-drm-mainline-design.md).

## Display mutex contract

The live display-mutex device is `1401f000.mm_mutex`, using the downstream
`mediatek,mm_mutex` compatible and a 4 KiB register aperture. Its handler is
Linux IRQ234, exactly SPI202 plus the GIC SPI base, level-low, and had handled
3,888 interrupts at the first snapshot. Neither the live debug clock tree nor
the complete MT6797 clock provider contains a mutex gate. The mainline record
must therefore use the existing no-clock path and attach the block to
`MT6797_POWER_DOMAIN_MM`.

The exact Gemian source defines ten hardware handles. The DDP manager allocates
handles 0–3, and handle 4 is reserved for a separate overlay software trigger.
Interrupt enable/status are at `0x000`/`0x004`; each handle has a 0x20-byte
stride with enable at `0x20`, acquire/status at `0x24`, reset at `0x28`, module
mask at `0x2c`, and SOF/EOF at `0x30`.

The positive module map is contiguous but MT6797-specific:

| Bit | Component | Bit | Component |
| ---: | --- | ---: | --- |
| 10 | OVL0 | 19 | CCORR |
| 11 | OVL1 | 20 | AAL |
| 12 | OVL0-2L | 21 | GAMMA |
| 13 | RDMA0 | 22 | OD |
| 14 | RDMA1 | 23 | DITHER |
| 15 | OVL1-2L | 24 | UFOE |
| 16 | WDMA0 | 25 | DSC |
| 17 | WDMA1 | 26 | PWM0 |
| 18 | COLOR0 |  |  |

Bits 2:0 of the SOF register select single/DSI0/DSI1/DPI0 as 0/1/2/3. Bits
8:6 independently encode EOF with the same values. The vendor video-mode path
selects both, making DSI0 `0x41`, DSI1 `0x82`, and DPI0 `0xc3`. The upstream
MT6795/MT8173 data cannot substitute because it lacks MT6797's two-layer
overlays, CCORR, DITHER, and DSC placement.

The GCE reaches this aperture through `SUBSYS_1401XXXX` (ID 2), offset
`0xf000`, size `0x1000`. Mutex0 and mutex1 stream-EOF events are 58 and 59.
The mechanical checker matches all 17 module tuples and the SOF/EOF, register,
IRQ, power, and GCE properties between the pinned Gemian source and local Linux
7.1 support.

Patches 28–30 add the dedicated compatible, platform record, and standalone
SoC node. Strict patch checks, the binding, all three MT6797 DTBs, and the mutex
object with `W=1` pass. The full 30-patch build is the checksum-clean package
`linux-7.1.3-gemini-a5336f4954ff`, derived from patch-set SHA-256
`a5336f4954ff0ac1c50a47b5ef9a008bf40f4d6d2f5afe5b69f86bc54d0ad345`
and configuration SHA-256
`0f98f03129508907261efaa6f1b195799313530628505e319d48427105ac385f`.
The packaged Image SHA-256 is
`802e760203e3c279db2b70d77bbeaf3aea84ea7074bfb68d945646ffcb819144`
and Gemini DTB SHA-256 is
`9ee924dddda8cd32e10b6b6768d991747ddeef8cea0ce763685b7f5af668ef8f`.
CMDQ, its mailbox, MMSYS, and the mutex driver are all built into the Image.

In the current Linux 7.1.3 package, the DRM/DSI/PHY implementations are
module-only (`mediatek-drm.ko`, `panel-novatek-nt36672e.ko`, and
`phy-mtk-mipi-dsi-drv.ko`). The packaged Gemini DTB keeps DSI, PHY, OVL,
fixed-function, and DPI nodes disabled and has no panel consumer. The mutex
node is implicitly enabled, but its Linux probe only maps the aperture and
obtains its clock; it does not perform initial display register writes. See
the [display/input package audit](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt)
and [current display package validation](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt).

Direct physical reads are not a viable fallback on the running firmware:
DEVAPC rejected every root `devmem` access to this block and every returned
zero is invalid. That probe was stopped and removed from the collector. The
source-audited vendor debug callback uses the driver's mapping safely, but the
display domain was powered off at the immediate capture. A later
source-audited `mtkfb` read recovered its retained active boot-time dump:
mutex0 was enabled with module mask `0x05fcb400` and SOF/EOF `0x41`. The mask
decodes exactly to OVL0, OVL0-2L, RDMA0, OVL1-2L, COLOR0, CCORR, AAL, GAMMA,
OD, DITHER, UFOE, and PWM0, independently confirming both the component map
and DSI0 video-mode encoding.
See the [display-mutex recovery experiment](../../experiments/2026-07-12-mt6797-display-mutex-recovery/README.md).

## Display register chain

All display component windows are 4 KiB:

| Component | Address | SPI |
| --- | ---: | ---: |
| OVL0 / OVL1 | `0x1400b000` / `0x1400c000` | 213 / 214 |
| OVL0-2L / OVL1-2L | `0x1400d000` / `0x1400e000` | 215 / 216 |
| RDMA0 / RDMA1 | `0x1400f000` / `0x14010000` | 217 / 218 |
| WDMA0 / WDMA1 | `0x14011000` / `0x14012000` | 219 / 220 |
| COLOR / CCORR / AAL | `0x14013000` / `0x14014000` / `0x14015000` | 221 / 222 / 223 |
| GAMMA / OD / DITHER | `0x14016000` / `0x14017000` / `0x14018000` | 224 / 225 / 226 |
| UFOE / DSC / SPLIT | `0x14019000` / `0x1401a000` / `0x1401b000` | 227 / 228 / none |
| DSI0 / DSI1 / DPI0 | `0x1401c000` / `0x1401d000` / `0x1401e000` | 229 / 230 / 231 |
| MM mutex | `0x1401f000` | 202 |

The running display selects the compiled-in
`aeon_nt36672_fhd_dsi_vdo_x600_xinli` LCM, not the root device tree's R63419
node. Debugfs reports 1080x2160, one DSI interface, video mode with CMDQ, and
`DISP_OPT_USE_DEVICE_TREE=0`; the kernel configuration applies physical
rotation 90 degrees. Source correlation recovers one DSI0 link, four lanes,
RGB888 burst video mode, and these downstream timings:

| Axis | Sync | Back porch | Active | Front porch |
| --- | ---: | ---: | ---: | ---: |
| Horizontal | 10 | 42 | 1080 | 42 |
| Vertical | 3 | 15 | 2160 | 10 |

The LCM requests a 440 MHz downstream DSI PLL setting, drives the dedicated
`LCM_RST_B` output through MMSYS offset `0x150` and pin 180's `LCM_RST`
function, enables positive/negative panel bias with GPIOs 60/251, and programs an
LP3101-named controller at I2C1 address `0x3e`. Its initialization and power
contract is documented in the
[panel-recovery experiment](../../experiments/2026-07-11-gemini-panel-recovery/README.md).
Live pinctrl debug on the named device shows GPIO60 claimed by `aeon_gpio` in
GPIO mode, while GPIO180 and GPIO251 are unclaimed by gpiolib. This matches the
vendor's direct reset/bias callbacks but does not establish that a mainline
GPIO-reset sequence is electrically interchangeable.
The exact panel module and controller suffix are not independently identified
because the kernel-side vendor ID callback does not perform a read.

Linux 7.1's existing NT36672E driver is the correct framework candidate but
not a compatible data set. A mechanical comparison finds 167 Gemini commands,
234 upstream-variant commands, 69 overlapping page/register addresses, and
only four exact command/payload matches. Both use pages 10/20/21/24/25/26/27;
the upstream variant additionally writes 2a/2c/f0. Patch 43 extends that shared
driver with the Gemini mode, 165 panel-register writes, descriptor-selected
supplies and delays, while preserving the existing variant defaults. The
compatible and panel consumer remain disabled until the LP3101 bias provider,
reset equivalence, and panel identification are verified.

The `LP3101` bias name is itself contradicted by available primary
documentation. LowPowerSemi describes LP3101 as a fixed ±5.5–5.9 V DFN-12
charge pump, and its LP3101A datasheet exposes EN rather than I2C. The Gemini
shim instead matches Linux's TPS65132 protocol exactly: address `0x3e`, VPOS
and VNEG selectors at `0x00`/`0x01`, `0x0f` mapping to 5.5 V, and two output
enable GPIOs. This raises protocol confidence to high while leaving chip
identity unknown. No `ti,tps65132` compatible should be added without a board
marking, schematic, verified compatible part, or controlled measurement.

The vendor DSI helper also selects packet type by command ID: values below
`0xb0` use DCS packet IDs, while `0xb0` and above use generic packet IDs. The
Gemini descriptor preserves that boundary in a dedicated write helper rather
than sending the entire table through DCS. The pinned-source audit and current
module-inclusive artifact record this explicitly in the
[packet-semantics result](../../experiments/2026-07-11-gemini-panel-recovery/results/nt36672-packet-semantics-20260714.txt)
and [panel validation](../../experiments/2026-07-11-gemini-panel-recovery/results/mainline-panel-current-72-validation-20260714.txt).

At the inferred 54.05 Hz diagnostic rate, the 1174-by-2188 totals imply a
138.839 MHz pixel clock and Linux's host would request 833.033 Mbit/s. The
retained PHY reports about 870 Mbit/s, a 4.44% difference. This inference is a
test target, not permission to add a rate quirk: first light must log the PHY
rate and externally verify refresh before changing the common host formula.

The R63419 root node is a complete but inactive 1440x2560 dual-DSI command-mode
alternative requiring lane swaps, UFOE left/right mode, SPLIT, and both DSI
hosts. It must not drive Gemini implementation decisions unless a distinct
hardware variant is proven to select it.

The first DRM target should reproduce the retained primary path through the
two-layer overlays, COLOR/CCORR/AAL/GAMMA/OD/DITHER, RDMA0, UFOE, DSI0, and
the MM mutex, with M4U enabled only for the exact larb0 ports as their DMA
consumers are attached. A simpler RDMA0-to-DSI0 diagnostic route is
source-supported, but is not evidence that UFOE can be omitted from normal
Gemini operation. Writeback, SPLIT, DSI1, and vendor session ioctls are not
required for first light.

## External-display bridge boundary

The live DT contains I2C3 `0x39` (`sii9022_hdmi`) and I2C3 `0x50`
(`siiedid`), but both clients are unbound. Vendor platform names
`soc:sii9022`, `soc:sii9022_hdmi`, and `soc:mhl@0`, plus `/dev/hdmitx`, are
private declarations and do not establish a populated connector. The only
captured HPD line, `EINT_HDMI_HPD-eint`, had zero counts and no bridge/EDID
probe message was present.

The Planet DTS includes `sil9024a.dtsi` under the `sii9022` wrapper. Its
source-derived board states use reset GPIO57, HPD/EINT GPIO62/EINT1, a 1.2 V
enable GPIO247, DPI GPIO39–54, and an `mhl_12v` supply. The pinned vendor tree
also contains the matching `drivers/misc/mediatek/hdmi/sil9024/` source. Its
source/ELF audit checks indexed ID `0x9022` and TPI ID byte `0xb0` at register
`0x1b`, matching Linux `sii902x`; exact board population and connector remain
unresolved. See the [bounded ELF validation](../../experiments/2026-07-13-external-display-recovery/results/sil9022-vendor-elf-validation.txt).

Linux 7.1.3 already has the standard `sii902x` DRM bridge and binding for
`sil,sii9022`; its probe checks chip-ID byte `0xb0` at register `0x1b`, obtains
`iovcc`/`cvcc12` supplies and an optional reset/HPD IRQ, and requires graph
ports. The vendor reset is much longer (20/50/20 ms), enables GPIO247 as a
1.2 V rail, and uses a separate EDID client; these are board-integration
differences, not evidence for a new chip driver. Do not bind the vendor
compatible or expose `/dev/hdmitx` in mainline by string similarity. See the
[external-display recovery experiment](../../experiments/2026-07-13-external-display-recovery/README.md)
and its [source validation](../../experiments/2026-07-13-external-display-recovery/results/mainline-external-display-source-validation.txt).

The bridge also requires a DPI producer. Vendor DPI0 is at `0x1401e000` with
SPI231 and the same register sequence represented by Linux `mtk_dpi`; vendor
power-on enables `DISP1_DPI_MM_CLOCK` and `DISP1_DPI_INTERFACE_CLOCK` and
selects `TVDPLL_D2/D4/D8/D16`. Linux 7.1.3 already exposes the matching
MT6797 TVDPLL, MM/interface gates, and MMSYS RDMA/UFOE/DSC-to-DPI0 routes.
Patch 60 adds a conservative `mtk_dpi` platform-data match and patch 61 adds
only a disabled, unconnected `dpi0` node. Its factor table is source-derived
but inferred, while DPI pinmux, reset/rails, bridge graph, HPD, audio, and
external-monitor mode-setting remain unverified. See the [DPI source
validation](../../experiments/2026-07-13-external-display-recovery/results/mainline-mt6797-dpi-source-validation.txt).

## Input and display brightness contracts

The focused live capture is the [input and backlight recovery
experiment](../../experiments/2026-07-12-input-backlight-recovery/README.md).
Its raw output remains private at
`artifacts/device-inventory/20260714-input-live/input-backlight.txt`.

The current Linux 7.1.3 package is checked in
[`mainline-display-input-current-72-package-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt),
with the earlier focused validation in
[`mainline-input-current-71-validation-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-input-current-71-validation-20260714.txt).
It includes the AW9523, matrix-keypad, display-PWM, PWM-backlight, DRM/DSI/PHY,
and NT36672E panel modules, but selects no Novatek touchscreen driver; the
I2C5/keyboard, display-PWM, all eleven display components, DSI, and MIPI-TX
nodes remain disabled, with no touchscreen, panel, or standard backlight
consumer in the DTB. This is package evidence only; mainline input,
brightness, and display runtime remain untested.

### Touchscreen

The populated touchscreen is an I2C child at bus 4 (`0x11011000`), address
`0x62`, with runtime name `cap_touch` and vendor driver `NVT-ts`. The physical
I2C node only contains the vendor-compatible string `mediatek,cap_touch`,
`reg`, and `status`. The interrupt, reset, and power wiring is instead split
into the vendor pseudo-node `/soc/touch@`:

| Signal | Vendor evidence | Mainline consequence |
| --- | --- | --- |
| IRQ | GPIO85 muxed to EINT8; live `cap_touch` interrupt activity | Put an explicit `interrupts-extended` on the I2C child once the EINT provider is enabled |
| Reset | GPIO68, with separate output-low/output-high pinctrl states | Convert to a standard `reset-gpios` property; verify polarity and settle timing |
| Power | pseudo-node `vtouch-supply` phandle | Identify the actual rail and use named regulator supplies on the I2C child |
| Logical input | virtual `mtk-tpd`, `phys=input/ts`, multitouch ABS events | The mainline I2C driver should register the input device directly; no vendor virtual-node ABI should be copied |

The vendor source is a broad NT36xxx implementation with trim-ID probing,
DMA-I2C transfers, firmware-update work, gestures, and framebuffer display
notifications. Linux 7.1.3 already has a small `novatek-nvt-ts` driver with
`novatek,nt36672a-ts`, parameter discovery, two regulators, reset GPIO, and
standard multitouch reporting. A fresh filtered vendor probe log records trim
bytes `00 00 03 72 66 03`, PID `0x0101`, and firmware `0x05`/bar `0xFA`; the
bytes match masked trim-table entry 8 and select the NT36772 event map
`0x11e00`. This identifies the live family, but does not prove that the
upstream driver's NT36672A register protocol or the alternate `0x01` target
address is compatible. A separate NT36772 backend/data variant remains the
correct mainline boundary.

The pinned vendor `trim_id_table` is a useful discriminator: it contains
eleven masked signatures—eight entries using the NT36772 map, plus NT36525,
NT36870, and NT36676F maps—but no NT36672A entry. The immutable vendor-kernel
ELF independently preserves the same table bytes and memory-map pointers.
Since the vendor probe rejects an unmatched trim ID, the successful live
`NVT-ts` binding and the focused log both prove the NT36772 entry matched. The
sanitized identity record is
[`nvt-live-trim-identity-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt).
The vendor sequence resets the controller and writes xdata selectors, so it is
state-changing but non-firmware activity—not a strictly read-only probe. The
remaining identity/driver gate is transport validation, not family discovery.
Patch 0075 records a disabled-by-default separate NT36772 backend boundary;
its focused object/module and binding checks pass, while the logical `0x01`
transport, rails/reset, event path, and runtime suspend behavior remain gates.
See the [boundary check](../../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt).

The live device-tree also carries a static `novatek-mp-criteria-nvtpid` child
under the I2C node. A property-only read reports 18 X channels, 30 Y channels,
four key channels, and configuration sizes 18/32/4. The arrays are retained in
the input experiment's `touch-mp-criteria.txt`; they describe manufacturing
test mappings and must not be mistaken for a live trim-ID result.

The vendor transport is also not a string-compatible variant of the upstream
driver. Its source targets address `0x62` for hardware reset commands and
`0x01` for bootloader/firmware/event transfers; the transfer helpers assign
that target directly to `i2c_msg.addr`, so `0x01` is not a second DT client.
Trim probing performs reset `0x69`, software idle `0xa5`, xdata selection
`0x01f6`, and a six-byte read at command `0x4e`. The NT36772 event buffer is
`0x11e00`; firmware information is read at event offset `0x78` and project ID
at `0x9a`. Runtime reports ten slots, pressure up to 1000, and swaps X/Y while
reversing the resulting Y axis. This requires a protocol backend or a new
NT36xxx driver, not merely a new OF compatible on `novatek-nvt-ts.c`.

The source-level comparison is reproducible with the experiment's
[`analyze-nvt-contract.sh`](../../experiments/2026-07-12-input-backlight-recovery/scripts/analyze-nvt-contract.sh)
and its hashed decision record
[`linux-nvt-compare.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/linux-nvt-compare.txt).
The binary/source parity and bounded probe disassembly are recorded in
[`linux-nvt-elf-validation.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/linux-nvt-elf-validation.txt)
and reproduced by
[`analyze-nvt-vendor-elf.sh`](../../experiments/2026-07-12-input-backlight-recovery/scripts/analyze-nvt-vendor-elf.sh).
The current 2026-07-14 normalized source and ELF rechecks are
[`nvt-source-validation-current-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-source-validation-current-20260714.txt)
and [`nvt-elf-validation-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-elf-validation-20260714.txt);
the source rerun was byte-identical on a second invocation.

The vendor configuration enables a delayed firmware-update worker and requests
the private `novatek_ts_fw.bin` image. The pinned source requires a 118,784-byte
image and validates version bytes at offsets `0x1a000`/`0x1a001`. Mainline must
keep firmware update opt-in and disabled by default; the image remains
Git-ignored and is documented only by the firmware-inventory experiment.

Do not use the vendor `/proc/NVTflash` node as that probe. Although its mode is
0444, the vendor read handler interprets the caller's buffer as an I2C command
and a clear high bit selects a write. The focused collector therefore never
opens it; future identity work needs a source-audited instrumented path.

A metadata-only endpoint inventory confirms that the bound `4-0062` client has
no attribute files and the `NVT-ts` driver directory exposes only
`bind`/`uevent`/`unbind`; `/proc/NVTflash` is the sole apparent identity
surface. The sanitized negative result is
[`nvt-identity-surface-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-identity-surface-20260714.txt).

A prior bounded live check still resolves `4-0062` to `cap_touch`/`NVT-ts`,
with `mtk-tpd` and active EINT8 activity, but `/dev/i2c-4` is absent and no
trim-ID line appears in that sampled dmesg. The private 2026-07-14 capture is
`artifacts/device-inventory/20260714-input-live/input-backlight.txt`; the
sanitized repeat and interrupt-counter comparison are in
[`live-input-repeat-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/live-input-repeat-20260714.txt).
See also the [sanitized live identity attempt](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-identity-attempt.txt).

The later focused filtered-dmesg capture retains the probe lines, including
trim `00 00 03 72 66 03`, and the vendor's delayed firmware-helper/checksum
messages. It is recorded separately so the negative earlier sample remains
traceable; the collector did not open `/proc/NVTflash`, access I2C, or request
firmware.

The same vendor display-notifier path couples touch power to panel state:
`LCD ON Notify` precedes `NVT-ts nvt_ts_resume`, and `LCD OFF Notify` precedes
`nvt_ts_suspend`. Mainline should express this as regulator/reset/runtime-PM
ordering where possible, not as a copied framebuffer notifier.

### AW9523 keyboard expander

The keyboard expander is I2C bus 5 (`0x1101c000`), address `0x5b`, runtime
name `aw9523_key`, bound to the vendor `Integrated keyboard` driver. The board
uses GPIO58 for expander shutdown/reset and GPIO87 muxed to EINT10 for its
interrupt; the live EINT line is active. Vendor source configures eight P0
row inputs, seven P1 column outputs, enables P0 interrupts, and rescans the
matrix at 100 Hz. Its static row/column table is the primary source candidate
for the Gemini key symbols and Linux key codes, but the live image's
capability bitmap does not match it for the Fn position. Keep that distinction
explicit until the exact binary build is identified.

Linux 7.1.3's `pinctrl-aw9523` already covers the AW9523/AW9523B silicon as a
GPIO and IRQ expander, and its binding includes a keyboard-matrix example.
Patch 0054 now supplies a disabled-only `gpio-matrix-keypad`/matrix-keymap
consumer, translated keymap, GPIO58 reset, GPIO87/EINT10 interrupt, and
expander pinctrl states. Do not create a second AW9523 silicon driver merely
to preserve the vendor's polling implementation; choose IRQ versus bounded
polling as a board-consumer policy. The candidate's GPIO-range mapping,
row/column polarity, timing, and wake policy remain hardware gates.
The vendor probe reads chip-ID register `0x10` and requires `0x23`, then uses
software-reset register `0x7f` value `0x00`; this confirms the source-level
AW9523 identity, but the live chip-ID byte was not retained in the sanitized
kernel-log capture.
The derived 8-by-7 row/column table is retained in the experiment's
[`keyboard-keymap.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt).
The source-level silicon comparison and remaining consumer gates are recorded
in [`aw9523-mainline-design.md`](../../experiments/2026-07-12-input-backlight-recovery/results/aw9523-mainline-design.md).
The current source recheck is
[`aw9523-source-validation-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/aw9523-source-validation-20260714.txt).
The passive capability contradiction and build-date comparison are in
[`live-keyboard-capability-compare-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/live-keyboard-capability-compare-20260714.txt).

### Display PWM/backlight

The running device exposes no `/sys/class/backlight` entry. It does expose a
vendor `lcd-backlight` LED-class node, but the actual display path logs
`disp_pwm_set_backlight_cmdq(id = 0x1, level_1024 = ...)` and gates the display
PWM at zero. The display PWM platform node is `0x1100f000+0x1000`, vendor
compatible `mediatek,pwm_disp`; its registers are enable `0x00`, commit `0x08`,
control/divider `0x10`, and period/high-width `0x14`. The panel init writes DCS
`0x51, 0xff` once, while runtime brightness changes are PWM log events. The
ordinary four-channel infrastructure PWM at `0x11006000` is a separate block.

Linux 7.1.3's `pwm-mtk-disp` already implements the matching register/commit
shape under the nearest MT8173 data record. The vendor CCF source maps
`DISP_PWM` to exactly one `INFRA_DISP_PWM` gate; its separate
`DISP_MTCMOS_CLK` handle powers the display domain and `MUX_PWM` selects the
parent source. The local MT6797 extension therefore adds a distinct
compatible and makes the secondary `mm` clock optional, rather than inventing
a second MT6797 display clock. A standard `pwm-backlight` consumer is still
required. The panel consumer remains disabled until that graph and the panel
bias/reset rails are verified.

The vendor board entry selects `led_mode = 5` with `pwm_config = <0 0 0 0 0>`.
In the vendor mux table source selector 0 is the ULPOSC/29 MHz path and the
divider is zero; this is a source-level starting point, not a measured
panel-safe PWM period.

The packaged `pwm-mtk-disp.ko` and `pwm_bl.ko` objects are present, but the
MT6797 display-PWM node is disabled and no standard backlight consumer is
present. Do not treat the vendor LED-class name as proof of a Linux
`pwm-backlight` graph; the current package and configuration evidence is in
the [display/input package audit](../../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt).

## GPU

The live node reports a Mali-T860-compatible Midgard block at `0x13040000`,
three standard interrupts in job/MMU/GPU order, and a 700 MHz vendor clock
target. The bound vendor driver identifies the hardware as `Mali-T88x MP4
r1p0`, product ID `0x0880`, with four shader-core masks. The DT's T860 string
is therefore a generic/vendor label rather than the complete silicon identity.
The clock list contains MFG, four core power-domain handles, muxes, and
infrastructure gates. It has no supply, reset, OPP table, or M4U reference.

The live vendor DVFS table is efuse/function-code selected (table type 12 in
the capture) and exposes 900, 780, 610, 520, 442.5, 365, and 238 MHz entries.
The sample sat at 238 MHz with vendor voltage control disabled. `mt_gpufreq`
directly programs MFGPLL/parking-PLL paths and couples VGPU/PMIC, thermal, and
PBM limits, so neither the 700 MHz DT target nor the procfs voltage numbers are
safe initial Linux OPPs.

The board-level vendor DTS supplies an external RT5735 regulator at I²C7
address `0x1c` and also contains a separate `vgpu_buck@0x60` candidate. The
live inventory identifies RT5735 as bound and `vgpu_buck` as unbound. The
vendor `mt_gpufreq.c` build selects `VGPU_SET_BY_EXTIC`; the RT5735 path checks
product ID `0x10`, programs VSEL registers `0x10`/`0x11`, uses bit 7 as the
enable flag, and encodes voltage in a 7-bit field. This is not the MT6351
`buck_vgpu` rail and is not interchangeable with Linux's FAN53555 driver
without an identity and register-compatibility proof. Its vendor init also
maps a GPU-LDO window at `0x10001000` and configures the external buck, so the
regulator and GPU-frequency policy must remain separate from the generic
Panfrost core driver.

The dedicated [RT5735 VGPU recovery experiment](../../experiments/2026-07-12-rt5735-vgpu-recovery/README.md)
records the product-ID, VSEL0, enable, discharge, and linear-voltage contract
without performing an I²C write.
Patch 51 adds the corresponding standard regulator provider and keeps the
Gemini node disabled; it does not attach the GPU consumer or change the rail.

Linux 7.1.3 Panfrost already has generic `arm,mali-t860` and `arm,mali-t880`
Midgard matches and discovers the product ID from the GPU registers. This
supports reusing Panfrost's core driver rather than creating a new MT6797 Mali
register driver. The base Linux platform gap was that MT6797 SCPSYS instantiated
`mfg_async` but not the vendor MFG/four-core domain set, and had no
`mfgsys`/G3D `MFG_BG3D` clock provider in its base DTS. Local patches 47–51
provide the generic hierarchy, separate SRAM offsets, MFG gate, required 52 MHz
preclock, and RT5735 boundary. Patches 0058–0059 add explicit MT6797 Panfrost
platform data for `core0`--`core3` and a disabled node with the live register,
interrupt, clock, and VGPU references. The generic binding remains permissive
for one to five power domains so existing MediaTek Midgard platforms retain
their behavior; the MT6797 four-domain contract is in the platform data. The
minimum CCF, reset, regulator, and OPP sequence is unverified. The current
72-patch package audit confirms `panfrost.ko` and the providers are packaged,
but the GPU, MFG clock, and RT5735 consumers remain disabled and the GPU node
has no OPP, reset, or M4U property. See the [current package audit](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mainline-panfrost-current-72-package-20260714.txt)
and [Panfrost source contract result](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mainline-panfrost-mt6797-source-validation.txt).
The recovered MT6797 M4U port table has no GPU client and the GPU has its own
MMU IRQ, so do not add an `iommus` property by analogy.

The pinned Gemian source snapshot contains generic Arm Mali Midgard/Kbase
`mali-r12p0` sources and the configured `mali-r12p1` tree. The exact MT6797
platform sources are present under `platform/mt6797/`: `mtk_config_platform.c`
maps five compatible nodes and requests ten clocks, `mtk_kbase_spm.c` owns the
optional DVFS GPU PCM path, and `mali_kbase_core_linux.c` calls
`mtk_platform_init()` during probe. The bound vendor ELF correlates with those
source calls. The captured autoconf omits `CONFIG_MTK_GPU_SPM_DVFS_SUPPORT`,
and the ELF does not request optional GPU-PM/AP-DMA clocks, so the SPM files are
source evidence rather than proof of an active runtime feature. The source
`kbase_platform_early_init` defers until an external FAN53555/RT5735 controller
is ready; power-on/off wraps VGPU state around the MFG clocks; and
`mtk_debug_mfg_reset` writes the mapped G3D config offset `0x0c`, high then low,
with a source-level `udelay(1)`. The ELF `0x10c7` immediate is the ARM64
`__const_udelay` encoding of that delay. Treat this as ABI evidence rather than
source to copy; the absence of a reset property in the vendor Mali node still
does not prove that no reset or firmware handshake exists. See the [vendor ELF
analysis](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mali-vendor-analysis.txt).

For mainline, start with one conservative clock, the verified SCPSYS hierarchy,
and the external `VGPU` regulator. Do not use 700 MHz as an initial OPP. Add
per-core domains or resets only as required by the Panfrost binding and proven
by controlled power-on tests. Keep the node disabled until that platform work
is complete; see the [GPU/Panfrost recovery experiment](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/README.md).

## Connectivity and WMT

The live Gemian image identifies the combo through two naming layers. Android
properties select `CONSYS_MT6797` and chip ID `0x6797`; `/proc/driver/wmt_aee`
reports internal label `MT279`, ROM `E1`, branch `W1715MP`, and patch date
`20180307`. The latter matches the date/version text in the installed WMT
ROMv3 headers. Keep these as separate observations rather than assuming that
the labels are interchangeable silicon IDs. The complete read-only capture,
source audit, and static userspace ELF audit are in the
[connectivity/WMT recovery experiment](../../experiments/2026-07-12-connectivity-wmt-recovery/README.md).

The vendor `consys@18070000` node is `mediatek,mt6797-consys` and owns four
windows: `0x18070000 + 0x200` (connection MCU configuration),
`0x10007000 + 0x100` (AP reset), `0x10000000 + 0x2000` (top clock generator),
and `0x10006000 + 0x1000` (SPM). Its level-low SPIs 284 and 285 are BGF and WDT
interrupts. The node consumes `SCP_SYS_CONN` and four PMIC rails:
`vcn18`, `vcn28`, `vcn33_bt`, and `vcn33_wifi`. The Planet board DTS adds
four pinctrl states for GPIO69, the GPS LNA control: initialization low,
runtime high, and runtime low. `WMT_SOC.cfg` says `wmt_gps_lna_pin=0` and
`wmt_gps_lna_enable=0`, which is a configuration distinction, not a physical
population proof.

The Wi-Fi child is a vendor HIF/DMA engine, not a self-contained upstream
wireless MAC: `wifi@180f0000` uses one `0x1100` window, SPI 283, and the
`INFRA_AP_DMA` clock. The live Planet DTS has no second DMA window. A generic
Gemian reference tree contains an alternate second window and `hardware-values`
property; those values are rejected for Gemini until live evidence supports
them. The vendor dmesg contains `HIF-SDIO` traffic and the platform driver is
`mt-wifi`, while the public Linux 7.1.3 tree has no `mediatek,wifi` or MT6797
WMT/SDIO Wi-Fi driver (its `btmtksdio` code is Bluetooth-only and targets
different chips). The source audit shows a full proprietary gen2
cfg80211/MAC stack over an MT6797 AP-DMA HIF, not an mt76-compatible MAC; a
new Wi-Fi firmware/HIF boundary is required unless a separately documented
upstream protocol implementation is found. Do not bind `mt76` by
compatible-string similarity. A fresh read-only repeat observed `wlan0` up
with carrier and cumulative BTIF TX/RX DMA activity while `mtk_wmt` owned the
shared CONSYS resources; this confirms active vendor use without proving a
mainline protocol. See the [2026-07-14 repeat](../../experiments/2026-07-12-connectivity-wmt-recovery/results/live-connectivity-repeat-20260714.txt)
and the [current package boundary](../../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-package-20260714.txt).

Bluetooth uses a separate MediaTek BTIF block: `0x1100c000 + 0x1000`, TX DMA
at `0x11000a00 + 0x80`, and RX DMA at `0x11000a80 + 0x80`, with SPI 130/116/117
and `INFRA_BTIF`/`INFRA_AP_DMA` clocks. The vendor IRQ table reports active TX
and RX DMA lines. Its printed IRQ indices include the GIC offset, so they must
not be compared directly with DT SPI numbers. Linux 7.1.3's `btmtkuart.c` and
`btmtksdio.c` contain reusable MediaTek STP/H:4 framing, WMT, HCI, and SDIO
ownership patterns, but `btmtkuart` expects serdev and `btmtksdio` only matches
newer MT7663/MT7668/MT7921/MT7902 IDs with a five-byte header and 256-byte
blocks. Gemini's active BTIF path and vendor 0x6628/0x6630/0x6632 function-2
SDIO contract therefore still need a new transport/consys owner. The correct
future boundary is a standard HCI device behind a proven BTIF transport,
reusing STP/H:4 framing and firmware helpers where the wire contract matches,
not a permanent `/dev/stpwmt` ABI. The BTIF register, DMA, SDIO, and STP
comparison is recorded in the [connectivity mainline design](../../experiments/2026-07-12-connectivity-wmt-recovery/results/mt6797-connectivity-mainline-design.md).

GNSS is represented by vendor `mediatek,gps` and `mediatek,gps_emi-v1` nodes,
`mtk_agpsd`, `/dev/stpgps`, and the combo ROMv3 patch. The second ROMv3 image's
strings include GNSS/geofence/FLP code. The static userspace audit additionally
shows an ARM32 SUPL/TLS daemon with local `agpsd2`/`agpsd3` sockets and matching
32/64-bit `gps.mt6797.so` HAL exports, so this is not a serial GNSS device
boundary. Linux 7.1.3's `gnss-mtk` driver is a serial `globaltop,pa6h`
consumer with `vcc`/`vbackup`, so it is not a direct match. Ownership and
message routing must be established before adding a standard GNSS interface.
FM is likewise separate: MT6631 configuration, coefficient, and patch files
accompany a vendor `/dev/fm` and FM-I2S path; no MT6631 FM driver is present
upstream.

The vendor reserved-memory node `consys-reserve-memory` is dynamically
allocated, `no-map`, 2 MiB in size and alignment, within the physical range
`0x40000000`–`0xc0000000`. The same live FDT also has a dynamic 16 MiB
`scp_share` reservation, a `0x16000`-byte SPM reservation, and two 4 KiB
dummy-read guards. The fixed map additionally names a `0x7ff80000/0x80000`
log-store region that is not marked `no-map`. These are evidence of
firmware/transport scratch contracts, not generic RAM. They must remain
reserved in a mainline boot image until ownership and placement are understood;
the observed `0xbfa00000` CONSYS address must not be treated as a stable
hard-coded allocation. The current board DT preserves the five pre-LK dynamic
reservation contracts but deliberately does not carry a fixed post-LK log-store
or mblock snapshot: retained LK appends those allocations after checking for
overlap. The [LK FDT audit](../../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md)
and [range audit](../../experiments/2026-07-13-memory-carveout-recovery/results/mainline-memory-range-audit-20260713.txt)
report no static post-LK overlap. A second live capture reproduced
the fixed ranges and all five dynamic nodes, but still exposed no dynamic
addresses; this is recorded in the [repeat capture](../../experiments/2026-07-13-memory-carveout-recovery/results/live-memory-repeat-20260713.txt).
It is not a second boot, so cross-boot placement stability remains unproven.
See the [memory carve-out recovery experiment](../../experiments/2026-07-13-memory-carveout-recovery/README.md)
for the sanitized capture and Linux 7.1.3 comparison.

## Cellular modem CCCI/CLDMA

The live Gemian kernel exposes two CCCI domains: MD1 (major `237`) with
`ccci_*`, `ttyC0`–`ttyC3`, and 18 `ccmni` network ports, and MD3/C2K (major
`236`) with `ccci3_*` and eight `cc3mni` ports. Platform resources include the
MT6797 CLDMA aggregate at `0x10014000`, AP/MD CLDMA windows at
`0x10219000`/`0x1021a000`, AP/MD CCIF windows at
`0x10209000`–`0x1020c000`, and the C2K/MD-to-MD CCIF windows at
`0x1020b000`/`0x10211000`/`0x10213000`. The live DT reports CLDMA capability 6,
MD1 shared memory `0x100000`, and a separate C2K shared-memory size `0x400000`.
CLDMA and CCIF interrupt counters are nonzero, but no modem node was opened
and no handshake or radio operation was attempted.

This is a vendor CCCI/CLDMA ABI over APB memory-mapped windows and firmware-
owned shared memory, not the PCIe/DPMAIF transport implemented by Linux
7.1.3's `t7xx`. The source-level backend contract is an 8+8 CLDMA queue
fabric, packed 16-byte 36-bit descriptors, an 8+8 CCIF queue/ring path, a
16-byte CCCI wire header, and staged EMI-MPU/remap ownership. A mainline
implementation therefore needs a new MT6797 transport/backend for rings,
channels, handshake, reset, shared-memory layout, and ownership. Linux's
generic `wwan_port_ops`/`wwan_create_port`/`wwan_port_rx` boundary and standard
TTY/netdev interfaces may be reused above that transport; the vendor
`/dev/ccci*` character/ioctl ABI should not be carried forward. Keep
modem/CCCI nodes disabled until dynamic reservations and firmware ownership
are resolved; see the [modem/CCCI recovery experiment](../../experiments/2026-07-13-modem-ccci-recovery/README.md)
and its [MT6797 CCCI contract](../../experiments/2026-07-13-modem-ccci-recovery/results/mt6797-ccci-mainline-contract.md).

The current `linux-7.1.3-gemini-c2d9eea95daa` package makes this boundary
explicit: `wwan.ko` and MHI WWAN helper modules are present, while `t7xx`,
RPMSG, QMI/MBIM, and CCCI/CLDMA transports are absent. The packaged Gemini
DTB retains only the two `no-map` CCCI reservations (`md1` and shared memory)
and has no active modem transport node. This is build/package evidence, not a
mainline modem runtime result; see the [current package audit](../../experiments/2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-package-20260714.txt).
The 2026-07-14 read-only topology capture is byte-identical to the prior
capture; the sanitized comparison is in
[`live-ccci-repeat-20260714.txt`](../../experiments/2026-07-13-modem-ccci-recovery/results/live-ccci-repeat-20260714.txt).

## Audio

The live Gemian system has one `mt-snd-card` ALSA card with 31 PCM device
numbers. The endpoint list includes ordinary multimedia playback/capture plus
FM I2S, TDM debug, headphone impedance, modem voice, Bluetooth voice, ANC,
hostless, and routing paths. Enumeration is not evidence that the Gemini's
speaker, microphone, headset, or external amplifier was exercised; the
normalized capture and safety boundary are in the [audio AFE recovery
experiment](../../experiments/2026-07-12-audio-afe-recovery/README.md).
The current Linux package check is recorded in
[`mainline-audio-current-72-package-20260714.txt`](../../experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-72-package-20260714.txt):
the AFE, MT6351 codec, and MT6797 machine modules are packaged, but the AFE
node is disabled and the DTB has no machine-card/codec graph. The earlier
71-patch validation remains linked in
[`mainline-audio-current-71-validation-20260714.txt`](../../experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-71-validation-20260714.txt).
This is build evidence only, not a claim that ALSA can probe on Gemini.

The vendor AFE node is `mediatek,audio` at `0x11220000 + 0x10000`, SPI 151
level-low, with an `audiosys` one-cell clock provider. Its enabled
`mt_soc_dl1_pcm` child uses a 4 KiB view of the same base and the same vendor
interrupt, then requests 28 clocks covering AFE/DAC/ADC gates, APLL tuners,
SCP and infrastructure audio clocks, muxes, PLL dividers, and APMIXED APLL1/
APLL2. The live IRQ table prints `Afe_ISR_Handle` as vendor IRQ 183; retain
that naming discrepancy until the vendor virtual/GIC mapping is decoded.

Linux 7.1.3 already contains the exact chipset families: `mt6797-afe-pcm`
matches `mediatek,mt6797-audio`, `mt6351-sound` is an MFD codec child, and
`mt6797-mt6351` is the machine driver. The mainline AFE driver requests seven
named clocks, while the existing text binding lists eight and includes
`mtkaif_26m_clk`; resolve this driver/binding mismatch before converting the
binding to YAML or adding an enabled board node. The local MT6351 MFD patch
already registers the sound cell. In the current MFD core, an exact matching
child with `status = "disabled"` suppresses that cell, while an absent child
still leaves a name-matched `mt6351-sound` platform device. The Gemini board
therefore currently has no standard codec child or machine-card phandle graph.
The source hashes and reuse boundary are recorded in the [MT6797 audio design](../../experiments/2026-07-12-audio-afe-recovery/results/mt6797-audio-mainline-design.md).
The normalized 2026-07-14 source recheck is
[`audio-source-validation-20260714.txt`](../../experiments/2026-07-12-audio-afe-recovery/results/audio-source-validation-20260714.txt).

Do not copy the vendor pseudo-nodes (`mt_soc_codec_63xx`, modem/Bluetooth/FM
PCM, or ANC) into the mainline DT. Keep the existing disabled-only AFE resource
node as the first boundary, then recover analog widgets, jack detect,
amplifier GPIOs, and supply dependencies before adding a machine-card graph.
Keep modem and Bluetooth voice transports separate from the local analog card.

## USB

The device exposes two distinct controller descriptions and two FUSB301 I2C
devices, one for each Type-C port. The downstream USB3 node shares register
windows between MUSB dual-role and xHCI views. The complete live capture and
source audit are in the [USB/Type-C recovery experiment](../../experiments/2026-07-12-usb-typec-recovery/README.md).

The fresh bounded read-only capture (Linux `3.18.41+`, SHA-256 recorded in
[`runtime-usb-typec-20260714.txt`](../../experiments/2026-07-12-usb-typec-recovery/results/runtime-usb-typec-20260714.txt))
reproduces USB1's `musb11_dts`/`musbfsh` binding and idle root hub, USB3's
`musb-mtu3d` binding, and an unbound USB3 xHCI child. Both FUSB301 I2C clients
are bound, but the vendor kernel exposes no Type-C, USB-role, or PHY class
devices. A later battery-recovery capture is indexed in
[`runtime-usb-typec-battery-recovery-20260714.txt`](../../experiments/2026-07-12-usb-typec-recovery/results/runtime-usb-typec-battery-recovery-20260714.txt):
both vendor probes logged Device ID `0x12`; FUSB301A on I2C0 obtained GPIO64/
EINT IRQ `0x183`, while FUSB301 on I2C1 attempted IRQ 0 and failed `-EINVAL`.
The same boot reported USB1 slew calibration timeout and missing USB3
`iddig_init` pinctrl. These are vendor observations, not evidence that the
disabled mainline nodes are safe to enable.

USB1 is `mediatek,mt6797-usb11` at `0x11200000 + 0x1000`, with a second SIF
window at `0x11210000 + 0x1000`, SPI 73 level-low (Linux IRQ 105 in the live
capture), and clocks `infra_icusb`/`sssub_ref_clk`. The vendor `musbfsh` child
owns the only USB root hub observed while idle; no accessory was attached.
USB3 is `mediatek,usb3` at three `0x10000`
windows (`0x11270000`, `0x11280000`, `0x11290000`); its MUSB and xHCI views
use SPI 127 and SPI 126 respectively, both level-low. The ID-detection child
uses GPIO181/EINT186, level-low, with the vendor debounce tuple `GPIO181, 0`.

The SuperSpeed PHY is `mediatek,usb3_phy` with five named clocks
(`ssusb_bus_clk`, `ssusb_sys_clk`, `ssusb_ref_clk`,
`ssusb_top_sys_sel_clk`, and `ssusb_univpll3_d2_clk`). The vendor driver
prepares the first four and uses hardcoded MT6797 PHY banks and tuning writes;
the same tree also contains an optional A60810 operator. Its active project
path does not expose a normal DT `reg` resource: SIF2 contains SPLLC/FM and
the U2/U3 banks at `0x000`/`0x100`/`0x800`/`0x900`/`0xa00`/`0xb00`/`0xc00`,
while IPPC reset/power is in the separate SIF window at `+0x700`. The full
source comparison and reuse/new-driver boundary are in the [MT6797 T-PHY
design record](../../experiments/2026-07-12-usb-typec-recovery/results/mt6797-tphy-mainline-design.md).

Two FUSB301-compatible controllers are bound at I2C0/`0x25` (`fusb301a`) and
I2C1/`0x25` (`fusb301`). The post-recovery vendor probe logs show both return
Device ID `0x12`; only the I2C0 FUSB301A path obtains a valid GPIO64/EINT IRQ
(`0x183`), while the I2C1 path reports GPIO/IRQ zero and `request_irq -22`.
Vendor board glue drives switch/role signals at GPIO70,
GPIO71, GPIO72, and GPIO94; the pseudo-node interrupts include a GPIO64/EINT
path and a separate `fusb300-eint`. The exact physical-port mapping is still
unknown. The public [onsemi FUSB301 datasheet](https://www.onsemi.com/download/data-sheet/pdf/fusb301-d.pdf) and [FUSB301A datasheet](https://www.onsemi.com/download/data-sheet/pdf/fusb301a-d.pdf)
defines register address `0x01` as the device-ID register with reset signature
`0x12`; the fresh vendor probe logs now provide that returned ID for both
clients.
It also documents autonomous `SS_SW` orientation output and an open-drain `ID`
sink-detection output, which may explain the vendor GPIO64/USB1 and redriver
glue without proving the physical connector mapping. The vendor FUSB301
interrupt/state implementation is incomplete and does not expose a Type-C
class or role-switch contract. The vendor kernel also has no I2C character
device (`CONFIG_I2C_CHARDEV` is unset) or FUSB301 register export; the vendor
readback is recorded in the [battery-recovery USB/Type-C capture](../../experiments/2026-07-12-usb-typec-recovery/results/runtime-usb-typec-battery-recovery-20260714.txt);
the older bounded identity-attempt result remains historical.

Patch 0056 adds a generic, disabled-board `onsemi,fusb301`/`onsemi,fusb301a`
Type-C controller driver and binding. It validates the public ID, programs the
documented mode/current/interrupt registers from a connector child, and
reports attach, partner type, BC current, and CC orientation through the
standard Type-C class. It deliberately does not own VBUS or the SuperSpeed
redriver GPIOs, and no Gemini FUSB301 DT node is added. A 2026-07-13 review
also makes probe reject a missing IRQ before unmasking and restores neutral
Type-C roles on detach; the exact register/API comparison is in the
[FUSB301 register contract audit](../../experiments/2026-07-12-usb-typec-recovery/results/fusb301-register-contract-20260713.txt).

Linux 7.1.3 contains generic MediaTek MTU3, MUSB, and T-PHY drivers, but MTU3
bindings do not list MT6797 and T-PHY has no MT6797 data. The USB3 controller
register offsets do match Linux MTU3/xHCI when the vendor's shared windows are
split into a candidate MTU3 `mac = 0x11271000 + 0x3000`, `ippc =
0x11280700 + 0x100`, and xHCI child `mac = 0x11270000 + 0x1000`. This is a
source-derived resource decomposition, not a runtime-tested DT. Reuse the
MTU3/xHCI controller code and add explicit MT6797 compatible, clock, rail,
PHY, and role data; do not copy the vendor three-window nodes into mainline.

USB1 is a narrower reuse case than USB3, not a new-MUSB-core case. Source
comparison shows the vendor USB11 MAC/FIFO/DMA register protocol and level-1
bits match Linux MUSB/Inventra; its six-endpoint, 8-KiB FIFO configuration can
be represented with Linux MUSB data. The distinct USB11 SIF/PHY, two-clock
contract, host policy, polarity register, and save-current/recover sequence
still require targeted MT6797 glue/PHY work. The source-level controller
comparison and reuse/new-driver boundary are in the [MT6797 USB design
record](../../experiments/2026-07-12-usb-typec-recovery/results/mt6797-usb-mainline-design.md),
with the refreshed contract evidence in
[`usb1-contract-validation-20260713.txt`](../../experiments/2026-07-12-usb-typec-recovery/results/usb1-contract-validation-20260713.txt).
The generic SSUSB T-PHY v1 bank layout is not sufficient unchanged for USB11:
the USB11 `SIF + 0x800` child fields are a close V1 match, but its shared
FMREG/calibration bank, bias controls, and vendor save-current/recover sequence
differ. The captured vendor config disables ICUSB, so the active USB11 helper
writes meter controls at SIF `+0xf00` (not generic V1 `+0x100`) and then takes
the source's unconditional timeout fallback, programming slew value `4`;
`MTK_DT_USB_SUPPORT` would skip the helper entirely. Linux's existing
`mediatek,eye-src = <4>` path skips its generic calibration and programs the
same fixed slew field, so it is the preferred first implementation boundary.
Reuse the common T-PHY V1 field helpers through an explicit USB11 variant; do
not run generic calibration or copy opaque power writes. The
USB11 PHY comparison is in
[`usb1-phy-v1-comparison-20260713.txt`](../../experiments/2026-07-12-usb-typec-recovery/results/usb1-phy-v1-comparison-20260713.txt).
The vendor USB3 MUSB child is bound in
the idle capture, but its xHCI child has no driver link or observed xHCI IRQ;
this is a runtime observation, not proof that xHCI is unusable.

The T-PHY source audit shows broad V1 register compatibility and a shared
SIF2/per-port bank topology. Patches 0066–0068 add an explicit MT6797 V1
compatible, MTU3/xHCI matches, and a disabled DT resource split; patches
0069–0070 add the USB11 MUSB match data plus a disabled USB11 MUSB/T-PHY
topology using the existing V1 child mapping and fixed `eye-src = <4>` escape.
The focused binding examples and all MT6797 DTBs pass. This remains a compile-time
candidate: a named-device boot must still prove clock, reset, PHY, and role
ownership. A new MT6797 PHY driver is valid if the two-SIF contract cannot be
represented cleanly. A generic compatible or vendor tuning table must not be
enabled by guess.

Patch 0069 extends the existing MUSB glue with MT6797 USB11 match data rather
than forking the MUSB core: it selects `infra_icusb`/`sssub_ref_clk`, six
endpoints, non-multipoint mode, `ram_bits = 11`, and the recovered 512-byte
single-buffer FIFO layout. The binding and object compile, but the USB11
compatible and DT node remain disabled until the separate T-PHY, PIO, VBUS,
and role contracts are verified. Patch 0070 supplies the disabled DT parent at
`0x11210000`, U2 child at `0x11210800`, USB1 MAC at `0x11200000`, IRQ 73, and
the two recovered clock IDs. The focused evidence is in
[`usb1-musb-mainline-validation-20260713.txt`](../../experiments/2026-07-12-usb-typec-recovery/results/usb1-musb-mainline-validation-20260713.txt).

A separate Linux 7.1.3 probe-safety audit confirms why those nodes remain
disabled. The MUSB glue probe enables parent clocks, runtime PM, and a child
device; child initialization powers and initializes the PHY, writes controller
interrupt/power state, requests the IRQ, and registers an HCD. T-PHY probe is
mostly resource setup, but its init/power callbacks are stateful clock,
calibration, and register operations. The current USB11 glue has no VBUS
callback and the DT node declares neither a VBUS supply nor a role switch, even
though `dr_mode = "host"`. Treat host mode as an unproven policy rather than an
enablement contract. The first runtime candidate should be device-only gadget
serial or an explicitly reviewed VBUS owner; do not enable USB11, its T-PHY,
Type-C, or VBUS path before that boundary is closed. The source hashes and
anchors are in the [USB11 probe-safety audit](../../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb11-probe-safety-audit-20260713.txt),
generated by its [audit script](../../experiments/2026-07-12-usb-typec-recovery/scripts/audit-mainline-usb11-probe-safety.sh).

The source-level FUSB301 comparison and remaining driver gates are recorded in
the [FUSB301 mainline design record](../../experiments/2026-07-12-usb-typec-recovery/results/fusb301-mainline-design.md)
and the [2026-07-13 register/API audit](../../experiments/2026-07-12-usb-typec-recovery/results/fusb301-register-contract-20260713.txt).
The candidate's current full-build, object, and binding provenance is in the
[current FUSB301 validation result](../../experiments/2026-07-12-usb-typec-recovery/results/fusb301-current-validation-20260713.txt).
The current USB/T-PHY/FUSB301 source recheck is in the
[USB validation result](../../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-validation.txt).
The exact current 74-patch package boundary and repeated audit are in the
[current USB package result](../../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-74-package-20260714.txt).
The 71-patch disabled USB3/USB11 T-PHY topology and focused schema/DTB validation is
in the [USB3 topology result](../../experiments/2026-07-12-usb-typec-recovery/results/mt6797-usb3-topology-validation-20260713.txt).
The PHY bank comparison and reuse/new-driver boundary are recorded in the
[MT6797 T-PHY design record](../../experiments/2026-07-12-usb-typec-recovery/results/mt6797-tphy-mainline-design.md).

Before writing DT:

1. correlate each FUSB301 instance, ID/VBUS interrupt, and drive-VBUS GPIO with
   the physical left/right connector;
2. identify which connector maps to USB1 versus USB3;
3. establish PHY register generation and the two-SIF resource contract against
   the generic T-PHY helpers without writing tuning registers;
4. bring up one port in device-only mode with gadget serial;
5. add host and role switching only after VBUS polarity and current control are
   verified.

## Immediate patch boundaries

The evidence supports separate upstream series rather than one board patch:

The current 71-patch local series represents the first platform boundaries
through MFG power/clock, the disabled RT5735 regulator provider, the disabled
BMI160 candidate, the board-specific TOPRGU watchdog IRQ, the disabled
AW9523/matrix-keypad candidate, the disabled FAN49101 regulator candidate,
the generic FUSB301 Type-C controller candidate, the disabled MT6797
thermal/AUXADC variant, and the disabled MT6797 Panfrost/DPI display producer
candidates, plus the disabled MT6797 T-PHY/MTU3/xHCI USB3 topology and
compile-tested USB11 MUSB glue, in
[`patches/series`](../../patches/series). It has a checksum-clean full build
and a Gemini boot artifact; no mainline image has been flashed or booted.

1. MT6797 infracfg reset controller and binding IDs.
2. MT6797 EINT data, mappings, pseudo-line handling, and SoC resource.
3. MT6797 pwrap SoC node with real clocks/reset and MT6351 child.
4. MT6351 MFD/IRQ support, including its four flat status/enable banks.
5. MT6351 regulator support sufficient for VEMC/VMCH/VMC and safe storage
   sequencing.
6. MT6797 MSDC compatible data and SoC nodes, tested at conservative timing.
7. Gemini DTS with serial console and MSDC0 only, preserving reserved memory.
8. MT6797 M4U/SMI data and port binding header.
9. MT6797 CMDQ/GCE provider, subsystem selectors, and event header.
10. MT6797 display-mutex binding, dedicated module/SOF data, and SoC provider.
11. MT6797 MMSYS routing/reset data; DRM components follow one at a time,
    then the independently verified panel.
12. MT6797 Mali compatible/power description, independent of M4U.
13. MT6797 AFE resource node; patch 45 is disabled-only while the codec and
    machine graph remains gated on analog wiring and clock-name review.

USB, cpufreq/thermal/suspend, connectivity, modem, and camera should remain
separate projects so they cannot destabilize the serial-plus-storage baseline.
