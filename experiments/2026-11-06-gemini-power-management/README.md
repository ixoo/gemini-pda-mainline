# Experiment: what the Gemini needs for battery-efficient power management

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-06-gemini-power-management` |
| Status | `running`: assessment done; R1, R1b, R2 run; S1 passed on P2 (s2idle with RTC and power-key wakes); gadget reconnects after suspend with no console input on the 0633–0635 image (P5); P6: C, H, K, S pass, 73.3 mA suspended; L2 passed on IRQ 20 with an unbalanced-IRQ warning per row (0672 fixes it, L3 next); AFE reset across suspend confirmed by register reads, fix 0671 compile-checked; mem path: MTU3 (0676, 0681) and thermal (0683) resume fixes pass (U2, T-M); A (0671) and L3 (0672) pass; charger wake 0685/0686: W1 and W2 pass, charger wake works in s2idle; under mem it does not (EINT176 under the SPM program, cpuidle's), no CHRDET storm; Wi-Fi hook specified for the card; CPU policy shown on lid close; R3 not run |
| Subsystem | System suspend (s2idle, PSCI), cpuidle, runtime PM, SCPSYS power domains, clocks, wakeup sources, every station driver |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-11-06 |
| Investigator(s) | Claude (power-management session) |
| Tracking issue | none; [roadmap](../../docs/ROADMAP.md) section 2, Power |

## Question

What does the Gemini need on Linux 7.1.3 for suspend and resume, and for idle
hardware to power down, and what stands in the way? For each driver the station
uses: what it does today, what is missing, and what blocks it. And what did the
vendor do, so the project can choose where to follow it and where to do better?

## Inputs and method

No device access, boot, build or register operation.

- The station kernel as built at `e4e09b1a`: its resolved `kernel.config`, its
  `CONFIG_CMDLINE` and its `mt6797-gemini-pda-station.dtb`, decompiled.
- Linux 7.1.3 with the station series (`patches/series-a53-station`), read for
  `dev_pm_ops`, runtime PM and wakeup calls in every driver the station binds.
- The Gemian GPL kernel, commit `8cfe6596a503612e3332d9c26e292a19525a7f07`
  ([tree](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07)),
  read from Git objects in the RE VM, and the retained Gemian kernel config.
- The retained `tee1` partition (the secure firmware with PSCI), disassembled
  privately in the RE VM; this record keeps only the conclusions.
- Earlier records: [CPU DVFS, thermal, idle and suspend recovery](../2026-07-12-cpufreq-thermal-suspend-recovery/README.md),
  [CPU/PSCI/timer recovery](../2026-07-13-cpu-psci-timer-recovery/README.md),
  [CPU clusters](../../docs/hardware/mt6797-cpu-clusters.md),
  [interrupts](../../docs/hardware/mt6797-interrupts.md),
  [power accounting design](../2026-11-01-gemini-power-accounting/README.md).

## Summary

- **Only s2idle is possible with the installed firmware.** The secure firmware
  is PSCI 0.2 with no `SYSTEM_SUSPEND`, so Linux offers `s2idle` and no
  `deep`.
- **No PSCI idle state below WFI is usable either.** Its `CPU_SUSPEND`
  power-down states only prepare the core and then wait in EL3. On Gemian the
  vendor kernel's SPM PCM program does the real power cut and wake.
- **The station has none of the pieces on.** It has no suspend, no cpuidle
  and no RTC class, and it keeps every loader clock on with
  `clk_ignore_unused`.
- **What saves battery first** is runtime PM, gated clocks and domains, s2idle
  with exact wake sources, and fixing the drivers that have no sleep hook.
- **The charge guard needs a sleep policy first.** Otherwise the charger's
  40 s watchdog restores charging during any suspend.
- **Gemian's own suspend, in the captures we have, never completed.**
  Autosleep aborted on Wi-Fi wakeup sources about eight times a second.

## Where the station stands today

| Setting | Station value | Effect |
| --- | --- | --- |
| `CONFIG_SUSPEND`, `CONFIG_PM_SLEEP` | off | No system sleep of any kind; every driver's sleep callbacks are compiled out |
| `CONFIG_PM` | on | Runtime PM and generic power domains work |
| `CONFIG_CPU_IDLE` | off | Idle CPUs only execute WFI; no PSCI `CPU_SUSPEND` is ever issued |
| `CONFIG_CPU_FREQ` | off | Every A53 stays at the loader's frequency and voltage |
| `CONFIG_RTC_CLASS` | off | No RTC device, so no `rtcwake` and no alarm wake, although the MT6351 RTC driver works ([C1](../2026-10-04-gemini-c1-preparation/README.md#c1-follow-up-boot-2026-10-06)) |
| `clk_ignore_unused` on the command line | present | No unused clock is ever gated; every clock the loader left on stays on |
| `initcall_debug`, `earlycon`, `log_buf_len=8M` | present | Bring-up aids; small cost, but `earlycon` keeps the UART path active |
| `maxcpus=8` | present | CPU8/9 stay off unless the A72 module brings them up |
| `CONFIG_NO_HZ_IDLE`, `HZ=250`, `WQ_POWER_EFFICIENT_DEFAULT` | on | The tick already stops on idle CPUs |
| DT `idle-states` | none | Nothing for cpuidle to use even if built |
| DT broadcast timer | none | Only the per-CPU architected timer; a CPU or cluster power-down idle state needs a timer that keeps running |
| DT `wakeup-source` | none | No device is marked able to wake the system |

## Per-component assessment

"Today" is the station at `e4e09b1a`. Because `CONFIG_PM_SLEEP` is off, every
system-sleep callback named below is compiled out today; it would run once
`CONFIG_SUSPEND` is on. Runtime PM is live.

**State:** `works` = shown on the station; `code` = the driver has the hook but it
has never run here; `missing` = no hook; `blocked` = needs something outside the
driver first.

### Platform

| Component | Today | Suspend / resume | Runtime / idle | Missing | Blockers |
| --- | --- | --- | --- | --- | --- |
| System suspend | `CONFIG_SUSPEND` off | `missing` | — | The option; a wake source; a way to observe a resume without USB | `deep` is impossible with this firmware (see [the firmware side](#the-firmware-side)); s2idle only |
| CPU idle (A53) | WFI only | — | `blocked` | Anything below WFI | **The firmware's power-down states need the vendor's SPM PCM program to cut power and wake the core**; without it the core stays in an EL3 `wfi` loop. Also a broadcast timer (APXGPT) and CIRQ. Hotplug through `CPU_OFF` works today |
| A72 cluster (CPU8/9) | off by default, A72 module optional | `blocked` | `blocked` | Suspend and hotplug ordering with the A72 provider | CPU8/9 bring-up is its own gated line; keep them offline across any suspend test |
| cpufreq | off | — | `missing` | MT6797 cpufreq backend, OPPs, calibration | [CPU clusters §6.1](../../docs/hardware/mt6797-cpu-clusters.md#61-can-a-standard-linux-governor-drive-cpu-frequency); not in scope here, but it decides active power |
| Clocks | `clk_ignore_unused` | — | `blocked` | Gating of unused clocks at late init | Display still needs it ([native display](../2026-11-02-gemini-native-display/README.md)): no MM domain, SMI or IOMMU owner yet; unknown loader-owned users (CONSYS, DVFSP) |
| SCPSYS domains | legacy `mtk-scpsys` (VDEC, VENC, ISP, MM, AUDIO, MFG) plus the local child controller | genpd powers off unused domains at `suspend_noirq` | `works` for AUDIO ([audio reload](../2026-11-01-gemini-audio-reload/README.md)) and MFG (GPU idle off) | MM has consumers only for larbs, PWM and DPI; the display's own domain use is not modelled | Display ownership above; CONN is owned by the CONSYS driver, not genpd |
| Interrupts and wake | GIC, `mt6577-sysirq` polarity, MTK EINT | EINT: `mtk_eint_do_suspend` masks non-wake lines (code); sysirq skips set_wake | — | DT `wakeup-source` on any device; a CIRQ node | s2idle keeps the GIC on, so EINT and GIC wake work without CIRQ; CIRQ matters only for a deeper state |
| PMIC wrapper, MT6351 IRQ | built in | MT6351 IRQ chip keeps a wake mask and arms its parent IRQ in suspend (code) | — | Nothing for s2idle | The vendor pre-programs SPM's PMIC commands for sleep voltages; mainline has no SPM, so VCORE stays at its run level in s2idle |
| Regulators (MT6351) | built in, normal-mode only | no suspend states | LDOs follow consumers | `regulator-state-mem` only matters with a firmware suspend; consumers must drop their LDOs | — |
| Thermal | built in, trips armed | the thermal core stops polling in suspend (code) | — | Nothing for s2idle | A hot device cannot cool by itself while suspended; the 117 °C hardware reset stays armed |
| RTC | driver works, `RTC_CLASS` off | alarm wake in the driver (code) | — | `CONFIG_RTC_CLASS`, `CONFIG_RTC_DRV_MT6397` | None found |

### Storage, USB and power supply

| Component | Today | Suspend / resume | Runtime / idle | Missing | Blockers |
| --- | --- | --- | --- | --- | --- |
| eMMC (`mtk-sd` MSDC0, HS400) | 50 ms autosuspend, clocks gated when idle | `pm_runtime_force_suspend`/`resume`; the MMC core sends sleep or power-off notify (code) | `works` | A resume test at HS400 (re-tune, the 0627 latch settings) | The RAM root keeps the root filesystem off the eMMC, so a failed resume is recoverable |
| microSD (MSDC1, SDR104) | runtime PM as above | as above; card removed or re-detected on resume | `works` | Card-detect wake; VMCH stays on for the detect switch | The detect switch needs VMCH, so "card in slot" costs an LDO while suspended |
| USB device (MTU3, SSH link) | gadget Ethernet | `mtu3_suspend` (code); remote wake needs `mediatek,syscon-wakeup`, which has no MT6797 entry | MTU3 has runtime PM | MT6797 IP-sleep wake registers, if wanted | Suspending drops the host's SSH link; a test cannot rely on it |
| Type-C (FUSB301/301A, local) | interrupt plus status poll | `missing` | — | Stop the poll work in suspend; decide whether a cable event wakes | The left chip keeps its mode across power-off (0624); a suspended role must be left a sink |
| Charger (bq25890 + guard) | guard kicks the 40 s watchdog every 10 s | upstream suspend stops the ADC (code); the guard has no suspend hook | — | A sleep policy for the guard | **In any suspend longer than 40 s the watchdog restores the chip's defaults and charging resumes past the limit.** The guard must set its sleep state before the work stops (see the plan) |
| Fuel gauge (MT6351, local) | reads on demand | `missing` | — | Nothing urgent: the coulomb counter is hardware and keeps counting | — |

### Display, input and indicators

| Component | Today | Suspend / resume | Runtime / idle | Missing | Blockers |
| --- | --- | --- | --- | --- | --- |
| Display/DRM (mediatek, modules) | blanks on lid close and console blank: PWM off, panel asleep, link and gates down | `mtk_drm_sys_prepare`/`complete` suspend and resume the modeset state (code) | DSI and DDP components have runtime PM | A suspend with the panel asleep; restore after resume | The panel is adopted from LK; Linux does not own its reset or bias, so bias stays on through a blank and a full power cycle is unproven |
| Backlight (`pwm-backlight` on `pwm-mtk-disp`) | works | `pwm_backlight_suspend` (code) | — | — | — |
| Touchscreen (NT36672, local) | module, by hand | `missing` | — | Disable the IRQ; ask the controller to sleep | A panel power cycle is untested |
| Keyboard (AW9523 + `gpio-matrix-keypad`, EINT10) | interrupt scan | matrix_keypad arms wake on its row IRQs when `wakeup-source` is set (code) | — | **AW9523's IRQ chip has no `irq_set_wake`**, so the rows cannot pass a wake to EINT10 | A small `pinctrl-aw9523` change forwards wake to its parent IRQ |
| Lid (hall on EINT5, `gpio-keys` + `gemini-lid`) | blanks the display, inhibits the keyboard | `gpio-keys` arms wake with `wakeup-source` (code) | — | `wakeup-source` on the switch; a userspace policy to suspend on close | — |
| Power and home keys (MT6351 keys) | work, Esc wakes the console | `mtk_pmic_keys_suspend` arms the key IRQ for wake when the key has `wakeup-source` (code) | — | `wakeup-source` on the power key | — |
| Indicator LEDs (AW9120, local) | caps lock trigger | `missing` | — | Turn the outputs off or keep only an owner-chosen one in suspend | Each lit LED costs about 3.5 mA |
| Vibrator (`regulator-haptic`) | works | stops the effect and drops the LDO (code) | LDO off after each effect | — | — |

### Audio, connectivity and the rest

| Component | Today | Suspend / resume | Runtime / idle | Missing | Blockers |
| --- | --- | --- | --- | --- | --- |
| Audio (MT6797 AFE + MT6351 codec) | loads at boot; AUDIO domain off when the driver is removed | ASoC core suspends streams (code); the AFE has no system-sleep op | AFE runtime PM exists, but the domain stays on while idle with the driver loaded ([audio boot](../2026-11-01-gemini-audio-boot/README.md)) | Find what holds the AFE active while idle; codec bias in suspend | — |
| Wi-Fi (local `mt6797` mac + HIF + CONSYS) | receive is polled; no 802.11 power save | `missing`; `mac80211` calls `stop` | — | Power save, an adaptive or interrupt-driven receive, a suspend policy | Receive interrupt never asserted ([HIF analysis](../2026-10-13-mt6797-wifi-native-delivery-probe/HIF_TRANSPORT_ANALYSIS.md)); `wlan0` down is one-way until `mac` reloads ([plan](../../docs/WIFI_DAILY_USE_PLAN.md#5-battery)), so for now unload Wi-Fi before a suspend |
| Bluetooth (`btmt6797`) | by hand | `missing` | — | `hdev` suspend hooks; the STP tick stopped in suspend | Shares CONSYS with Wi-Fi, GNSS and FM |
| CONSYS owner (local) | powers CONN on probe | `missing`; runtime PM is used only around probe and remove | — | A suspend that leaves CONN off or idle, or refuses while a client is active | The vendor puts the connectivity firmware to sleep through WMT; that protocol is not mapped |
| GNSS, FM (local) | by hand, off by default | `missing` | — | Refuse or stop in suspend | — |
| Sensors (BMI160, STK3x1x) | modules by hand | STK3x1x has suspend (code); BMI160 has runtime PM only | BMI160 `code` | Nothing for a first test | — |
| Camera (SENINF, CAMSV, hi556) | by hand | `missing` in the local receiver | hi556 has runtime PM | Unload before suspend | SMI clock has no owner |
| GPU (Panfrost) | idle power-off by default | Panfrost system sleep (code) | `works` | — | — |
| I2C, SPI, UART | built in | `mtk_i2c` and `mt65xx` SPI suspend (code); `8250_mtk` suspend (code) | SPI and UART runtime PM | `earlycon` and `initcall_debug` off on a battery image | The DVFSP handoff on I2C6 has no resume story ([DVFSP row](../../docs/HARDWARE_SUPPORT.md)) |
| Watchdog (TOPRGU) | registered | `mtk_wdt_suspend` stops it and resume restarts it (code) | — | — | A suspended kernel must not leave a running watchdog; the driver handles that |

## The firmware side

The secure firmware in `tee1` (the same payload as the
[A72 firmware contract](../2026-07-22-a72-firmware-power-contract/README.md),
a TF-A v1.0-era `psci_afflvl_*` design) was disassembled privately in the RE
VM. Observed:

| Call | Result |
| --- | --- |
| `PSCI_VERSION` | 0.2 |
| `CPU_SUSPEND`, `CPU_OFF`, `CPU_ON`, `AFFINITY_INFO` | implemented |
| `MIGRATE`, `MIGRATE_INFO_*` | stubs (`-1`, type 2) |
| `PSCI_FEATURES` | stub; answers only for `SMCCC_VERSION` |
| `SYSTEM_SUSPEND` (`0x8400000e`, `0xc400000e`) | **not implemented** (`NOT_SUPPORTED`) |
| `SYSTEM_OFF`, `SYSTEM_RESET` | inherited from Arm's FVP port: they write a register of Arm's simulator board, then panic; not functional on MT6797. Linux already restarts through TOPRGU and powers off through the MT6351 RTC |
| SMCCC 1.1 and the Spectre workaround call | present |

`CPU_SUSPEND` takes the original 0.2 `power_state` format. The highest
affinity level is 1 (cluster); level 2 is rejected, so there is no system
state through `CPU_SUSPEND` either. The StateID is ignored. A standby state
(type 0) is a plain `wfi` in EL3. The vendor's two idle parameters decode as:

| Parameter | Meaning | What the firmware does |
| --- | --- | --- |
| `0x0010000` | power-down, core level | Clears the core's retention controls, waits (unbounded) for the core's bit in SPM `CPU_RET_STATUS` to clear, saves the warm-boot entry, flushes L1, then waits in `dsb; wfi; b wfi` |
| `0x1010000` | power-down, cluster level | As above; when the rest of the cluster is already down it also turns off the GIC CPU interface, takes the cluster out of CCI coherency, saves L2 and GIC state, then the same `wfi` loop |

Nothing in the secure firmware writes an MTCMOS or SPM power control, checks
an SPM sleep flag, or touches timers, DRAM or the PMIC on suspend, and no
MediaTek SiP call exists for SPM, sleep, idle, wake sources or the PMIC
wrapper. The power cut and the wake are done by the SPM running the PCM
program that the **vendor Linux kernel** loads. **Inference:** a mainline
kernel that requests either power-down state without that program leaves the
core in the EL3 loop for good, so the earlier records' plan to "begin with
PSCI idle states" must not be followed. Not ruled out from the secure
firmware alone: a hardware mode in SPM that powers a core off on WFI by
itself.

The `CPU_SUSPEND` and system-suspend setup that Linux 7.1.3 performs only for
PSCI 1.0 or later never runs here, which is why the station prints no SMCCC
version line.

**What this firmware allows mainline without SPM code:** WFI idle, s2idle
with devices runtime-suspended, CPU hotplug through `CPU_OFF`, and Linux-side
clock and power-domain gating. It does not allow DRAM self-refresh, the
26 MHz clock or VCORE off, or a system sleep state: those exist only in the
vendor's SPM programs.

## How Gemian does it

Evidence only; nothing from the vendor tree is reused. Paths are relative to
`drivers/misc/mediatek/base/power/` in the Gemian tree unless stated.

**System suspend is Linux-driven SPM, not firmware.** `spm_v2/mt_sleep.c`
registers its own `suspend_ops` for `mem`. On entry the kernel:

1. picks the `pcm_suspend` program (one image for each A53 cluster) that
   userspace had loaded earlier through `/dev/spm` into a no-map carveout
   (`mediatek,spm-reserve-memory`, which the station DT still reserves);
2. loads the PMIC wrapper's 16 "DVFS" command slots with the suspend phase
   (VCORE sleep voltage 0.6 or 0.7 V, VSRAM, low-IQ modes) and writes a few
   PMIC registers directly;
3. masks every GIC interrupt except the SPM's own (SPI 180), clones the
   edge-triggered ones into the SYS_CIRQ latch, and parks the UART;
4. writes the SPM power-control and wake registers and kicks the PCM;
5. calls `cpu_suspend(2)`, which is PSCI `CPU_SUSPEND` `0x1010000` (cluster
   power-down). The SPM program then drops the 26 MHz clock, infra and VRF18,
   puts DRAM in self-refresh, and wakes the core on a wake event.

Resume reads the SPM wake reason, replays CIRQ, restores the GIC and PMIC
phase, and re-kicks the VCORE DVFS program that otherwise runs resident.

**Wake sources** are the SPM mask `0x0F47C5E7`: PCM timer, keypad, CONN2AP
(Wi-Fi and Bluetooth), EINT, the modem and SCP watchdogs, CCIF, CLDMA, the USB
cable bits and SYS_CIRQ. The PMIC (power key, RTC alarm, charger) arrives
through EINT. Vendor EINT has no wake mask: any EINT left enabled wakes the
system. The PCM timer wakes the system periodically for the battery meter
(30 s to 90 min, by battery voltage).

**Deep idle.** The vendor cpuidle driver offers deep idle (screen off, DRAM in
self-refresh, 26 MHz off), SODI and SODI3 (screen on, DRAM in self-refresh),
MCDI (off on Gemian) and WFI. Every non-WFI state is a different PCM program
plus the same `CPU_SUSPEND` `0x1010000`. All of them require exactly one CPU
online and a long list of clocks and power domains off. The DT's other
parameter, `0x0010000`, is parsed but never requested. It is a core
power-down, not the "CPU retention" an earlier record called it.

**What Gemian achieved.** The live kernel has `PM_AUTOSLEEP` and Android
wakelocks, and `repowerd` drives autosleep. In three private captures from
July 2026, taken over Wi-Fi SSH, there were 22 suspend attempts, about one
every 0.13 s. Every one aborted while freezing tasks on a WLAN wakeup source,
and none reached the SPM. In the same captures the vendor's own idle
statistics show deep idle, SODI and SODI3 blocked by a second online CPU or by
clocks, with only WFI used. The battery driver holds a wakelock whenever a
charger is attached, and the USB driver holds one while a cable is in. The
vendor stack can reach a real system sleep only on battery, with USB unplugged
and Wi-Fi quiet. No retained capture shows it doing so.

**Per-driver hooks of note.** The keyboard's IRQ is disabled and the chip shut
down on screen blank or lid close, so keys never wake a blanked Gemian. The
lid's EINT stays armed. The display powers off on framebuffer blank, not in
suspend. The audio driver forces a 26 MHz-on sleep variant while FM, offload or
ANC is active. CONSYS keeps 26 MHz, APSRC and DRAM requests through SPM masks
and wakes through CONN2AP.

## What the project can do better

- **Use s2idle and runtime PM as the base.** The vendor stack thrashes in
  autosleep and in practice runs WFI with the hardware on. A mainline station
  whose idle devices are runtime-suspended, whose domains are off and whose
  unused clocks are gated already gets most of what Gemian got. s2idle stops
  the tick and freezes userspace without any SPM code.
- **Suspend on a decision, not on a race.** Suspend on lid close (and,
  optionally, after an idle timeout with the screen blank), driven by one
  policy in userspace. No wakelocks or autosleep.
- **Exact wake sources.** Mainline EINT has a real wake mask (`irq_set_wake`
  and `mtk_eint_do_suspend`), so only the lid, the power key, the RTC and an
  owner-chosen keyboard wake. Gemian lets any enabled EINT wake it.
- **The keyboard can wake.** Gemian turns the keyboard off on blank. With P2a
  the station can wake from a key while the lid is open.
- **Charging stays right while asleep.** Gemian depends on periodic PCM timer
  wakes for battery work. The guard should instead leave the charger in a
  state that holds without a host (P1c), so suspend never has to wake for it.
- **A deeper state, later, two ways.** Each needs its own design record and an
  owner decision.
  1. A small Linux SPM driver that owns the PMIC wrapper's DVFS slots, the SPM
     wake mask, the APXGPT timer and CIRQ. At runtime it loads the vendor
     `pcm_suspend` program from the unit's own firmware partition, which the
     project does not redistribute. It would then register `mem` suspend
     ops, as the vendor did. It is local-only, not upstreamable, and depends
     on a non-free program.
  2. A secure-firmware port in the shape of upstream TF-A's MediaTek
     platforms, with PSCI 1.0, `SYSTEM_SUSPEND` and the SPM sequence in EL3.
     Linux would then get `deep` and PSCI idle states with no MT6797-specific
     kernel code. It means writing `tee1`, which is outside the current
     approval, and it needs a proven recovery path below the preloader.
- **Hotplug before idle states.** `CPU_OFF` works today. Keeping CPU0 alone
  online when idle, as the vendor's HPS did, is the one CPU-power lever that
  needs no SPM.

## Plan

Small steps in order. Each step that needs the device goes to the custodian as a
reviewed test below; none is run by this record. Steps that change only modules
iterate with `rmmod`/`insmod`; the built-in and DT changes (P1) go in one image.

**Read-only first**

- **R1, measure before changing anything.** Battery-side idle current on the
  station at `current_now`, with the charger held off by the existing guard,
  display blanked, lid open. Three cases: Wi-Fi and Bluetooth unloaded; Wi-Fi
  loaded and idle; Wi-Fi joined and idle. Record `/proc/interrupts` and
  per-thread context switches over the same 60 s, to name what wakes the CPUs.
  Without this number no later step can claim a saving.
- **R2, what `clk_ignore_unused` is holding.** Read
  `/sys/kernel/debug/clk/clk_summary`, `/sys/kernel/debug/pm_genpd/pm_genpd_summary`
  and each device's `power/runtime_status`. The clocks that are prepared and
  enabled with an enable count of zero are the ones the kernel would gate
  without the flag; each needs an owner or a reason before the flag goes.
- **R3, a Gemian figure to compare against.** Bounded read-only on Gemian:
  battery current with the screen off and Wi-Fi off, `wakeup_sources`, the
  autosleep state and the cpuidle `usage`/`time` counters, over one idle
  minute. This is the target the mainline figure is judged against.

**Host-only, then one batched image (P1)**

- **P1a, s2idle with RTC wake.** Turn on `CONFIG_SUSPEND`, `CONFIG_PM_SLEEP`,
  `CONFIG_PM_SLEEP_DEBUG`, `CONFIG_RTC_CLASS` and `CONFIG_RTC_DRV_MT6397`. No
  driver change. `/sys/power/mem_sleep` will offer `s2idle` only.
- **P1b, wake sources in the DT.** `wakeup-source` on the MT6351 power key and
  on the hall switch. Nothing else.
- **P1c, the charge guard's sleep state.** Before suspend the guard either
  leaves charging off with the chip's watchdog disabled (so defaults cannot
  return), or refuses suspend while it is holding a stop with the charger
  attached. Resume re-arms the watchdog and the 10 s work. Without this, a
  suspended device charges past the owner's limit after 40 s.
- **No idle states in P1.** The firmware's power-down states hang the core
  without SPM firmware (see [the firmware side](#the-firmware-side)), so the
  image carries no `idle-states` and no `CONFIG_CPU_IDLE`.

**Modules, iterated on the running station (P2)**

- **P2a,** `pinctrl-aw9523`: forward `irq_set_wake` to its parent interrupt, so
  `gpio-matrix-keypad` with `wakeup-source` can wake through EINT10.
- **P2b,** FUSB301: stop the status poll in suspend and resume it; leave the
  controller a sink (0624's rule).
- **P2c,** AW9120: turn the outputs off in suspend unless an owner-chosen
  trigger keeps one.
- **P2d,** CONSYS owner: refuse suspend while a client (Wi-Fi, Bluetooth, GNSS,
  FM) is active, until a WMT sleep protocol exists. Userspace unloads the
  clients first. This is honest and small; a firmware-sleep path comes later.
- **P2e,** touchscreen: disable the IRQ and send the controller to sleep.

**Then (P3, P4), each its own test**

- **P3, drop `clk_ignore_unused`.** After R2 names the holders and the display
  models its MM clocks; a boot without the flag, with the display, eMMC,
  USB, Wi-Fi and audio rechecked.
- **P4, CPU power-down in idle.** Blocked on the SPM. The secure firmware's
  `CPU_SUSPEND` power-down states only prepare the core and wait in an EL3
  `wfi` loop; the vendor's SPM PCM program cuts the power and wakes the core.
  Two ways forward, each its own design record: a small Linux SPM driver that
  loads the vendor's MCDI/suspend PCM image from the device at runtime (not
  redistributed) and owns the wake mask, the APXGPT broadcast timer
  (`0x10008000` in the vendor DT) and the CIRQ; or the firmware route in P5.
  Before either, the cheaper idle lever is hotplug: offlining idle A53s
  through the working `CPU_OFF` path, as the vendor's HPS did.
- **P5, a deeper system state** is an owner decision, outlined under
  [what the project can do better](#what-the-project-can-do-better).

Not in this plan: cpufreq (its own line in the [CPU clusters](../../docs/hardware/mt6797-cpu-clusters.md)
document), Wi-Fi power save and receive interrupts (the [Wi-Fi plan](../../docs/WIFI_DAILY_USE_PLAN.md#5-battery)).

## Proposed device tests

For the custodian. None has been run.

### R1: idle current and wake sources on the current station

- **Hypothesis:** with Wi-Fi unloaded and the display blanked, the station's
  battery draw is dominated by always-on SoC power, not by wakeups; with Wi-Fi
  loaded, its receive poll adds measurable wakeups and current.
- **Unique observation:** `current_now` averaged over 60 s at 1 s per sample in
  each of the three cases, with the `/proc/interrupts` and context-switch
  deltas for the same window.
- **Method:** with the cable in, the battery reads about −1 mA because the
  charger runs the system from VBUS, and the bq25890 has no input-current ADC
  ([R2 run](#r2-result-2026-11-06)). So the measurement runs unplugged:
  1. a detached script logs `current_now`, `/proc/interrupts` and context
     switches to `/mnt/data` once a second;
  2. the owner unplugs the cable for about 4 minutes, then plugs it back in;
  3. the custodian reads the log after SSH returns.

  The run is read-only. Wi-Fi modules are loaded and unloaded the normal way.
  The Wi-Fi-joined case is a radio action and stays out unless admitted.
  Cutting the input with the charger's HIZ bit would avoid the unplug, but it
  is an unadmitted charger write.
- **Stop:** the script stops itself if the battery falls below 30 % or the
  temperature rises above 45 °C, or on any kernel warning. A lost SSH link is
  expected and is not a stop.
- **Decision:** if the Wi-Fi-loaded case costs more than about 20 mA over the
  unloaded one, the adaptive receive poll moves up the Wi-Fi plan; the
  unloaded figure is the baseline every later step is measured against.

### R2: clock and power-domain census

- **Hypothesis:** a short list of clocks (display MM, CONSYS, DVFSP, UART and
  the loader's leftovers) is all that `clk_ignore_unused` keeps alive.
- **Unique observation:** the `clk_summary` entries with enable count 0 but
  prepared or enabled in hardware, and every genpd with its devices' runtime
  state.
- **Method:** debugfs reads only. **Stop:** none needed beyond a read failure.
- **Decision:** each listed clock gets an owner (a driver or a DT consumer) or
  a recorded reason; P3 waits for that list.

#### R1 result (2026-11-06)

**Setup.** The custodian ran R1 on the same image and boot as R2 (boot2
`55f5d6d6…` from `e4e09b1a`, boot `9a152abb`), untainted before and after.
The cable was unplugged, the display blanked through `fb0/blank`, the lid
open, eight CPUs online and `clk_ignore_unused` in force. One sample a second
was logged to the data partition. The raw logs stay private with the
custodian.

| Case | Samples | Mean battery current | Range |
| --- | --- | --- | --- |
| Wi-Fi loaded, not joined | 52 | −115.3 mA at 4.168 V | −105 to −133 mA |
| Wi-Fi unloaded | 60 | −111.0 mA at 4.160 V | −98 to −136 mA |

- The first 8 samples of the loaded case were excluded: they read the charger
  online at about 0 mA, because the cable briefly reconnected after the
  unplug.
- One −219 mA sample came right after the `rmmod`.
- **The idle floor is about 111 mA, or about 0.46 W.** On the 4268 mAh design
  capacity that is roughly 38 h idle with the display blanked.

**Interrupts per 65 s window** (Wi-Fi loaded / unloaded):

| Source | Loaded | Unloaded |
| --- | --- | --- |
| `arch_timer` (about 220/s across 8 CPUs) | 14183 | 14366 |
| IPI function call | 5487 | 5246 |
| IPI reschedule | 1284 | 1269 |
| I2C `11007000` | 826 | 552 |
| `mmc0` (the log's own writes) | 122 | 110 |

- **Context switches:** the logging shell about 1570 per window, `rcu_preempt`
  about 1185, every kworker under 350.
- **Battery and temperature:** the battery went from 87 to 85 %, the
  temperature from 24.8 to 24.9 °C, and no stop rule was hit. Wi-Fi was
  reloaded afterwards.

**Decision, by the predeclared rule.** Loaded but not joined, Wi-Fi costs
about 4 mA, under the 20 mA threshold. So the adaptive receive poll does not
move up the Wi-Fi plan for the unjoined case. The joined case was not run.

**Analysis.**
- The interrupt load is modest: about 27 timer ticks per CPU each second,
  plus the IPIs.
- The I2C bus at `11007000`, which carries the charger and the right FUSB301,
  takes about 8–13 transfers a second while idle. That is the FUSB301 status
  poll plus the charge guard, and it raises P2b's priority.
- Most of the 111 mA is therefore unlikely to be wakeups. It is more likely
  always-on power: the clocks R2 found running, the AUDIO domain held active,
  VCORE at its run voltage, and eight CPUs idling in WFI rather than
  powered off. R1b separates the CPU share.

**Caveats.**
- The 1 Hz logger and its eMMC writes are part of the load.
- The gauge's averaging window is unknown.
- The report also mentions the A72 cluster as online, while `maxcpus=8`
  allows eight CPUs. Which eight were online should be confirmed on the next
  run.

#### R2 result (2026-11-06)

**Setup:** the custodian ran R2 on station-work-72 (boot2 image `55f5d6d6…`,
built from `e4e09b1a`), boot `9a152abb`. The kernel was untainted and the
command line included `clk_ignore_unused`. The native display was running, and
the Wi-Fi modules were loaded but not joined. The raw census stays private
with the custodian.

**Clocks.**
- Of 231 clocks, 201 read enabled in hardware, and 165 of those have an enable
  count of zero.
- The 165 overstate what is really ungated: dividers and muxes with no gate of
  their own report their parent's state.
- **PLLs running with no user:**
  - TVDPLL, feeding DPI0;
  - VDECPLL, feeding the video decoder;
  - CODECPLL, feeding the encoder, MJC and the MDP, WDMA, WROT and larb4
    clocks;
  - the DSI1 MIPI TX PLL at 880 MHz, although DSI1 is unused;
  - APLL1 and APLL2, with no audio stream playing;
  - MFGPLL, still prepared while the GPU domains are off;
  - the IMGPLL dividers, and the UNIVPLL and SYSPLL trees.
- MSDCPLL is legitimately in use: its `d2` output is the eMMC's HS400 parent.
- **Infra gates on with no user:** SPI0–5, IR TX, I2C2/3, PWM1–4, UART1–3,
  GCE, the modem CCIF, CLDMA and C2K set, the crypto blocks, SCP, ICUSB,
  MSDC2, APXGPT, the device APC and FHCTL.

**Power domains.**
- Only CONN and AUDIO are on.
- AUDIO holds the audio controller in runtime **active** with no stream
  playing. That matches the [audio boot](../2026-11-01-gemini-audio-boot/README.md)
  observation.
- ISP and the MFG domains are off.
- MM, VDEC and VENC do not appear in the genpd summary, so they are not
  under genpd control at all.

**Runtime PM.**
- Active: UART0, the audio controller and the USB controller.
- Suspended: both MSDC hosts, the DRM device, OVL and RDMA.
- 78 platform devices have no runtime PM.

**What this changes:**
- P3 is mainly about owners for unused PLLs. Giving the unused multimedia and
  DSI1 PLLs and the modem, SPI and PWM gates a "gate me" path, or simply a
  boot without `clk_ignore_unused` once the display's MM clocks are claimed,
  is the largest clock-side lever found.
- The audio controller staying active while idle is a driver fix of its own.
- Every one of these is still unmeasured in milliamps, so R1 comes next.

### R1b: what the CPUs and the AUDIO domain cost (proposed)

- **Hypothesis:** offlining CPUs 1–7 through `CPU_OFF` (the working hotplug
  path) and unloading the audio modules (so the AUDIO domain powers off) each
  lower the 111 mA floor measurably.
- **Method:** as in R1, unplugged, with the Wi-Fi modules unloaded. Run three
  60 s windows in one unplug:
  1. the R1 state;
  2. CPUs 1–7 offline through `/sys/devices/system/cpu/cpuN/online`;
  3. the audio modules also removed.

  Restore everything after the replug. Record which CPUs are online at the
  start.
- **Stop:** R1's rules, plus any CPU that fails to come back online.
- **Decision:**
  - If CPU offlining saves more than about 10 mA, an idle hotplug policy
    becomes the first CPU-power step, ahead of any SPM work.
  - If the AUDIO domain saves more than about 5 mA, fixing the idle runtime
    suspend of the audio controller moves ahead of the P2 module fixes.
  - Otherwise both stay where they are, and P3 (clocks) is the next lever.

#### R1b result (2026-11-06)

**Setup.** Same image and boot as R1 (`9a152abb`), untainted throughout,
unplugged, Wi-Fi unloaded, display blanked. Three windows of 60 samples in one
unplug, with the charger offline in all of them. A53 hotplug had no earlier
mainline record, so the custodian flagged it and the owner approved the run
directly. A pre-check with the cable in took CPU7 off and back on, about
30 ms each way, with no warning.

| Window | Mean battery current | Range |
| --- | --- | --- |
| CPUs 0–7 online | −111.2 mA at 4.162 V | −99 to −179 mA |
| CPUs 1–7 offline | −96.0 mA | −80 to −153 mA |
| also audio modules removed (AUDIO domain off) | −96.0 mA | — |

**Interrupts per 65 s window** (base / CPUs off / audio off):

| Source | Base | CPUs off | Audio off |
| --- | --- | --- | --- |
| `arch_timer` | 12516 | 4428 | 4386 |
| IPI function call | 4327 | 0 | 0 |
| IPI reschedule | 724 | 0 | 0 |
| I2C `11007000` | 552 | 564 | 552 |

Every CPU came back online with rc 0. Audio and Wi-Fi reloaded cleanly, with
no warning. The battery went from 87 to 85 % and the temperature from 24.6 to
25.1 °C. The R1 floor reproduced (111.2 against 111.0 mA).

**Decisions, by the predeclared rules.**
- **CPU hotplug saves about 15 mA (14 %), above the 10 mA threshold.** An idle
  hotplug policy becomes the first CPU-power step, ahead of any SPM work.
- **The AUDIO domain saves nothing measurable, under 5 mA.** The audio
  controller's idle runtime-PM fix stays a correctness item, not a power one.

**Analysis.**
- About 96 mA remains with one CPU. That is the always-on SoC and board power
  that only clock gating (P3), VCORE scaling or an SPM state can reach.
- CPU0 alone still takes about 68 timer interrupts a second. The 1 Hz
  logger, the I2C polling (unchanged at about 8.5 transfers a second) and RCU
  account for some of that; the rest is unexplained.

**Proposed policy (P2f).** When the display blanks (console blank or lid
close), take CPUs 1–7 offline; bring them back when it unblanks. It goes in
the station's existing userspace display policy, not the kernel. It needs no
new kernel code: the `CPU_OFF` path is the one R1b used. The owner
chose to add it on 2026-11-06.

**P2f as written (not yet run on the device).** The station's
[`backlight-policy`](../2026-10-30-mainline-dev-station/backlight-policy.c)
runs this policy:
- **Dark** (lid closed or console blanked): it offlines whichever of CPUs 1–7
  are online.
- **Lit:** it brings back only the CPUs it took. A CPU the owner offlined
  stays off.
- **Restart:** on start with the screen lit, it brings all of CPUs 1–7 back,
  since a previous run may have died while dark.
- **A72s:** never touched.
- **No wait on wake:** the writes run in a child process, so a wake does not
  wait the roughly 30 ms each CPU takes.

The program builds with the station's `-static -Wall -Wextra -Werror`. A
throwaway harness drove `cpus()` against a fake sysfs tree in the dev VM and
passed seven cases: start lit or dark, repeat, and a quick dark-then-lit
switch. The release image builds the same program, so it gets the policy
too.

**Acceptance on the device:**
- Lid close and console blank each leave `online` reading `0`.
- Waking restores `0-7`.
- The display still lights within the usual time.
- R1's blanked figure drops to about 96 mA.

### R3: the Gemian comparison

- **Hypothesis:** Gemian with the screen off spends most idle time in the
  vendor's SPM idle states (SODI or deep idle), and its autosleep rarely
  completes while Wi-Fi is up.
- **Unique observation:** battery current with screen off, Wi-Fi off, over 60 s;
  `/sys/kernel/debug/wakeup_sources`; `/sys/power/autosleep`; cpuidle state
  counters before and after.
- **Method:** bounded read-only Gemian inspection over its LAN SSH path, under
  the standing authorization. Gemian is booted only if it is already the
  running system or an investigation boot is due anyway. **Stop:** any write
  prompt, a device not identified as Gemian.
- **Decision:** sets the target figure for the station.

### P1 candidate (written 2026-11-06, compile-checked only)

| Change | What it does |
| --- | --- |
| `configs/gemini-a53-station.fragment` | Turns on `SUSPEND`, `PM_DEBUG`, `PM_ADVANCED_DEBUG`, `PM_SLEEP_DEBUG`, `RTC_CLASS` and `RTC_DRV_MT6397`. `CPU_IDLE` stays off |
| [0628](../../patches/proposals/0628-pinctrl-aw9523-let-an-input-pin-wake-the-system.patch) | AW9523 passes `irq_set_wake` to its parent line. In suspend it also unmasks the armed pins in the chip, because `matrix_keypad` masks its rows before arming them and the IRQ core skips these nested interrupts |
| [0629](../../patches/proposals/0629-arm64-dts-mediatek-gemini-station-name-the-wakeup-so.patch) | Adds `wakeup-source` on the power key and the keyboard matrix, and on the hall switch with `wakeup-event-action` deasserted, so opening the lid wakes and closing it does not |
| [0630](../../patches/proposals/0630-power-supply-bq25890-keep-the-charging-guard-s-limit.patch) | The guard refuses suspend while a charger is attached or the OTG boost is on. On battery it stops its work across the suspend and runs a pass at resume. **Gap:** a charger attached while suspended charges unguarded until resume |
| [0631](../../patches/proposals/0631-usb-typec-fusb301-stop-reading-the-controller-across.patch) | FUSB301 stops its poll or IRQ in suspend and reads the status once at resume |

The three driver objects and the station DTBs were built with `W=1` in the
dev VM against the station configuration plus these options. They produced no
warnings, and the DTB carries the three wake properties. The AW9523 and
bq25890 changes are built in; FUSB301 is a module.

### S1: first s2idle on the P1 image (after P1 is built)

- **Preconditions:** run on battery, since 0630 refuses suspend with the cable
  in. Use the same unplugged method as R1: a detached script with its log on
  the data partition.
- **Staging:** `/sys/power/pm_test` runs it in three steps.
  1. `freezer`: freeze and thaw userspace only.
  2. `devices`: also suspend and resume every device, without idling the CPUs.
  3. Only then a real `rtcwake -m freeze -s 20`, followed by one cycle woken
     by the power key.

  Each step runs once; stop at the first failure.

- **Hypothesis:** with Wi-Fi, Bluetooth, GNSS, FM and camera unloaded, the
  display blanked, the A72s offline, the station enters s2idle and resumes on
  an RTC alarm with eMMC (HS400), microSD, keyboard, display and the USB link
  working.
- **Unique observation:** `rtcwake -m freeze -s 20`, then the PM debug lines
  (`PM: suspend entry`, device timing, `PM: suspend exit`), the wakeup source
  that ended it, and a post-resume read of 64 MiB from the eMMC hashed against
  a pre-suspend read. Then one cycle woken by the power key instead.
- **Logging:** the USB link drops while suspended; the test writes its log to
  `/run` and the custodian reads it after the link returns. pstore keeps the
  kernel log if resume never completes.
- **Stop:** no resume within 60 s (the owner holds Esc for the configured 11 s
  PMIC reset, which has reset an idle station once but is untested on a hung
  kernel), any eMMC error, a charger state other than the guard's, or heat.
  At most three cycles per boot.
- **Decision:** resume works, so measure R1's case suspended; or a named device
  fails resume, which becomes that driver's fix; or nothing resumes, which
  points at the platform (GIC, EINT, timer) and stops the line for review.

#### S1 result (2026-11-06): stopped at step 2, MTU3 refused

**Setup.** The custodian ran S1 on station-work-73, the P1 image: boot2
`99b6d357…`, built from `1c659a42` (without `d28da6fa`). Boot `28323df3`,
untainted.

**Boot checks, all passed:**
- `mem_sleep` read `[s2idle]`;
- `rtc0` is the MT6351 RTC;
- `keyboard-matrix`, `gpio-keys` and the USB controller have wakeup
  attributes;
- the PMIC keys arm their wake from their own suspend callback, so they have
  no `power/wakeup` attribute.

The RTC holds a 2070 date and logs an invalid alarm value at boot; it was not
set for this test.

**The run:** unplugged, A72s offline, Wi-Fi unloaded, display blanked,
`pm_debug_messages` on.

| Step | Result |
| --- | --- |
| 1, `pm_test=freezer` | Passed: `echo freeze` rc 0 in about 5.1 s; a 64 MiB eMMC read hashed the same before and after |
| 2, `pm_test=devices` | **Failed in 0.2 s:** `mtu3 11271000.usb: platform_pm_suspend returns -16`, devices resumed after 5.8 ms. No other device reported an error; the eMMC hash still matched, HS400 held, no warning |
| 3, 4 | Not run, by the stop rule |

The gauge read 86 % before, 80 % at the end of the 20 s run and 86 % after
the replug, so it can't measure windows this short.

**Cause, from the source.**
- `ssusb_gadget_suspend()` returns `-EBUSY` while `mtu->connected` is set.
- Only a disconnect clears that flag, and the MAC sees a disconnect through
  VBUS.
- The station's PHY has `mediatek,force-b-session-valid`, so a removed cable
  never looks like a disconnect. The controller only sees the bus go idle.
- A soft disconnect (`soft_connect`) would not clear the flag.
- Nor would a role switch to "none", which MTU3 maps back to the device role.

**Fix: [0632](../../patches/proposals/0632-usb-mtu3-let-a-suspended-bus-suspend-the-system.patch).**
MTU3 tracks a bus suspend (set on the suspend interrupt, cleared on resume and
reset) and lets the system suspend while it lasts. An active link still
refuses, as before. It is compile-checked with `W=1`, and built in, so it
needs an image.

**Its premise is an inference:** that an unplug raises the U2 suspend
interrupt. That can be checked read-only on the running image: with the cable
out, log the `11271000.usb` count in `/proc/interrupts` and
`/sys/kernel/debug/mtu3/11271000.usb/link-state`.

**Retry options.**
- Retry S1 on the P1 image with a workaround in the script: unbind
  `11271000.usb` from `mtu3` before the suspend and rebind it after the
  replug. Gadget Ethernet then rebinds by itself. The unbind/rebind cycle is
  itself untested on this unit.
- Or wait for an image with 0632.

Both need the owner's go. The owner chose a new image with 0632.

#### S1 on P2 (2026-11-06): s2idle enters and resumes

**Setup.** The custodian ran S1 on station-work-74: boot2 `f5ca7dc6…`, built
from `b5a3d017` (P1 plus 0632 plus the CPU policy). Boot `16188838`, untainted
throughout. Raw logs stay private with the custodian.

**0632's premise held.** Plugged, the controller's interrupt count read 416.
Three seconds after the unplug it read 431, the link state went from `0x12`
to `0x13`, and the UDC still read `configured`. So the unplug arrives as a bus
suspend.

**S1 run:** unplugged, Wi-Fi unloaded, display blanked, CPUs 0–7.

| Step | Result |
| --- | --- |
| 1, `pm_test=freezer` | rc 0, 5.1 s |
| 2, `pm_test=devices` | rc 0; devices suspended in 12.4 ms; MTU3 suspended in 376 µs |
| 3, `rtcwake` +20 s | Entered suspend-to-idle at 150.43 s; woken by IRQ 191 (the PMIC) at 169.71 s; out at 169.95 s; devices suspended in 16.3 ms |
| 4, power key (RTC backup +60 s) | Entered at 192.20 s; woken by IRQ 191 at 193.04 s, about 0.8 s later, when the owner tapped the key; out at 193.27 s |

- Step 4 is consistent with the power key but not proven: the RTC shares
  IRQ 191 and no key event was logged.
- After every step the 64 MiB eMMC read hashed the same, the eMMC stayed at
  HS400, and there was no warning.
- `suspend_stats`: 4 successes, 0 failures.

**This is the first system suspend on this unit with mainline:** s2idle
entered and resumed twice, with an RTC wake and a key wake.

**Not shown:**
- a suspended current figure (the gauge's counter units are unconfirmed);
- a suspend longer than 20 s;
- keyboard and lid wakes;
- Wi-Fi across a suspend.

**CPU policy (P2f), lid test with the cable in.**
- Closing the lid took CPUs 1–7 down within 0.12 s.
- Opening it brought them back within 17 ms, with no "did not go" line.
- The console-blank path was not tested.

**New defect: the gadget did not reattach after resume.**
- After the replug, the UDC read `not attached` and the host saw nothing.
- A second unplug and replug didn't help.
- A `soft_connect` disconnect then connect from the console brought SSH back.

**Cause, from the source.** MTU3's system suspend powers the device IP and
port down, which drops the link and the D+ pullup. Resume powers them on
without restoring either. Before 0632 that suspend ran only while
disconnected; now it can run with a suspended but still connected bus.

**First fix, 0633 v1:** treat such a suspend as a disconnect at suspend time
(pullup down, gadget driver told), then raise the pullup at resume. It was
rejected on P3, below.

#### P3 (2026-11-06): 0633 v1 rejected, suspend aborts

**Setup.** station-work-75: boot2 `f04f8e24…`, built from `012d5dbb`, with
the initramfs identical to P2. Boot `f570bf03`, untainted. The test was:
unplug, wait 5 s, RTC +20 s s2idle, then replug with no console input.

**Result: the suspend aborted in 0.3 s.**
- dmesg showed `pullup D-`, then `ip sleep failed!!!`, `pullup D+`, and
  `platform_pm_suspend returns -16` after the 100 ms wait.
- After the abort the UDC read `not attached`. The eMMC hash still matched,
  with no warning.
- The replug brought SSH back with no console input, but no suspend had
  happened, so it proves nothing about 0633.

**Inference:** on a suspended bus, taking the pullup down changes the line
state, and the IP no longer reaches sleep. On P2, in the same state with the
pullup left alone, MTU3 suspended in 376 µs.

**0633 v2, the patch now in the series (`0633-…`, same name).**
- **Suspend:** exactly as on P2. It only notes that the gadget was connected.
- **Resume, if it was connected:** report the disconnect a VBUS drop would
  have reported, drop the connection's runtime PM reference, take the
  pullup down, wait 10–20 ms, and raise it again.

That is the manual cycle that cured P2, done by the kernel.
Compile-checked with `W=1`; not yet on the device.

**Test (G):** with the cable in and SSH working:
1. Unplug, wait 5 s, run `rtcwake -m freeze -s 20`.
2. Replug with no console input. Pass: within 30 s the UDC reads
   `configured` and SSH returns. dmesg should show `pullup D-` then
   `pullup D+` after the resume, with no `ip sleep failed`.
3. Run it twice.
4. Then one plain unplug and replug with no suspend.

**Stop:** the suspend fails, or SSH is not back 60 s after a replug. In
either case read the UDC state, and the owner recovers with the soft-connect
cycle.

#### P4 (2026-11-06): suspend works, reconnect still fails, and a WARN

**Setup.** station-work-76: boot2 `94a0fc40…`, built from `ddc6a1e2` (0633
v2). Boot `7f43fdde`. Raw logs and an owner photo stay private with the
custodian.

**Suspend:**
- The RTC +20 s s2idle completed: in at 29.57 s, woken by IRQ 191 at
  49.07 s, out at 49.31 s.
- No `ip sleep failed`; the eMMC hash matched.
- 0633 v2's pullup cycle ran at 49.118 s and 49.138 s, with the cable still
  out.

**Reconnect: failed.**
- Right after resume, and still 30 s after the owner's replug with no
  console input, the UDC read `not attached` and the link state `0x0`.
- The soft-connect cycle from the console recovered SSH.

**A WARN (taint 512).**
- At 31.71 s, inside the suspend, `__i2c_transfer()` warned.
- Call chain: the regulator core's late cleanup (`regulator_init_complete_work`,
  queued 30 s after late init) read the bq25890 VBUS regulator over the
  suspended I2C0.
- So any suspend in the first 30 s after boot hits it. It also shows that
  timers and non-freezable work still run during s2idle.

**Cause of the reconnect failure, from the source.**
- MTU3's runtime callbacks power the controller, PHY and clocks down only when
  `device_may_wakeup()`, because nothing else would bring it back.
- But probe calls `device_init_wakeup(dev, true)` unconditionally, so on the
  Gemini, which has no wake path, that check always passes.
- 0633 v2 correctly drops the connection's runtime reference when it reports
  the disconnect. The controller then runtime-suspended (link state `0x0`), and
  a replug could never wake it.
- The manual soft-connect works because MTU3's pullup call starts with
  `pm_runtime_get_sync()`.
- On P2 the reference was never dropped, but the pullup lost in the
  power-down was never restored either. Hence the same symptom.

**Fixes, compile-checked with `W=1`, both built in:**
- [0634](../../patches/proposals/0634-usb-mtu3-power-down-at-runtime-only-with-a-wake-path.patch):
  MTU3 enables wakeup, and with it runtime power-down, only when a wake path
  exists (IP-sleep wakeup or a wakeup IRQ). On the Gemini the controller now
  stays powered and keeps watching the bus. With 0633 v2 this gives:
  - suspend as on P2;
  - at resume, a reported disconnect and a pullup cycle;
  - a replug the controller can see.
- [0635](../../patches/proposals/0635-regulator-core-hold-the-late-cleanup-off-during-a-sy.patch):
  the regulator late cleanup is queued on `system_freezable_wq`, so a suspend
  holds it until resume.

**Test:** test G on an image with 0633–0635. Add one suspend started within
30 s of boot, which must leave no WARN and no taint.

#### P4, second run (2026-11-06): 0634 emulated, inconclusive

**Setup.** Same boot (`7f43fdde`), at about 833 s of uptime, already
tainted. Earlier in that boot the owner had cycled `soft_connect` once.
`power/wakeup` was then set to `disabled`, which is what 0634 sets at probe.

**Result.**
- 5 s after the unplug the UDC still read `configured`, runtime PM was
  active, and `U3D_USB20_OPSTATE` read `0x0`. On every earlier run it had read
  `0x13` (the bus-suspended state) at this point.
- The suspend failed in 16 µs with MTU3 `-EBUSY`: connected, with no bus
  suspend seen.
- The eMMC hash matched, and the plain replug kept SSH.

**Two changes, not separated.** Either the earlier soft-connect cycle or the
disabled wakeup stopped the unplug from showing as a bus suspend. The second
is unlikely: with wakeup disabled the runtime callbacks only return early.
If it was the pullup cycle, then 0633's own resume-time cycle would leave
the next suspend refused. Test G's second cycle checks exactly that.

**Next: a clean boot of P4.** Before any `soft_connect`, set `power/wakeup`
to `disabled`, then run G with the uptime over 40 s. At each step, log:
- the `11271000.usb` interrupt count;
- `U3D_USB20_OPSTATE`;
- runtime status.

**Decisions:**

| Result | Next |
| --- | --- |
| Both cycles pass | 0634 confirmed; build the image from `90333ab1` |
| Cycle 1 passes, cycle 2 is refused with `0x0` after the unplug | A pullup cycle breaks bus-suspend detection, so 0632's premise is not reliable. Fall back to D2 below |
| Cycle 1 shows `0x0` after the unplug | Bus-suspend detection is unreliable even from a clean start. Fall back to D2 |

**D2, the fallback.** MTU3 has no VBUS input it could be fed: its extcon
hook is for host ID only. On this board, 0630 already refuses suspend
whenever the charger sees VBUS, so a suspend that gets as far as MTU3 is
proof the cable is out. D2 would treat a connected gadget at suspend as
unplugged on this board (a DT flag naming the forced session) instead of
waiting for a bus suspend. The resume-time reconnect of 0633 stays.

#### P4 clean boot (2026-11-06): reconnect passes, 0634 confirmed by emulation

**Setup.** P4 (`94a0fc40…`), clean boot `ba596ae6`, untainted from start to
end. No `soft_connect` at any point. `power/wakeup` was set to `disabled` at
45.7 s, which is what 0634 sets at probe. Wi-Fi was unloaded. Raw logs stay
private with the custodian.

| Point | IRQ count | Runtime PM | UDC | `OPSTATE` |
| --- | --- | --- | --- | --- |
| Start | 154 | active | configured | `0x12` |
| G1, 5 s after unplug | 169 | active | configured | `0x13` |
| G1, after resume | 170 | suspended | not attached | `0x3` |
| G1, after replug | 232 | active | configured | `0x12` |
| G2, 5 s after unplug | 278 | active | configured | `0x13` |
| G2, after resume | 279 | suspended | not attached | `0x3` |
| G2, after replug | 336 | active | configured | `0x12` |
| G3, no suspend: unplug, then replug | 391, 448 | active | configured | `0x13`, `0x12` |

**Cycle details.**
- G1 and G2: s2idle for about 20 s each, rc 0, woken by the RTC on IRQ 191.
- Each resume showed `pullup D-` then, 20 ms later, `pullup D+`.
- After each replug the gadget reached `configured` within 0.5 s, and SSH
  returned with no console input.
- The eMMC hash matched both times; `suspend_stats` 2 successes, 0 failures;
  no warning; battery 86 → 84 %.

**Reading.**
- The decision table's first row holds: 0634 is confirmed by emulation, and
  D2 is not needed.
- The second cycle still saw the unplug as a bus suspend, so 0633's
  resume-time pullup cycle does not break detection.
- With wakeup disabled, runtime PM read `suspended` after resume. That is
  only the bookkeeping, since the callback no longer powers anything down.
  The replug brought it back to active by itself.

**Open.**
- After a manual `soft_connect` cycle, the next unplug was not seen as a bus
  suspend for the rest of that boot (P4, second run), and the reason is not
  known. Use the kernel's own reconnect instead of a manual one.
- Not shown on a built image yet: 0634 itself, and 0635 with a suspend in
  the first 30 s after boot (both shown in P5 below).

#### P5 (2026-11-07): 0633–0635 on a built image

**Setup.** Image `station-work-77` from `eea46408` (0633 v2, 0634, 0635),
boot2 SHA-256 `93873a03e576e546bef371495543bec3f065849dd81db2a6c0cc4a1ef87b2d5a`.
One boot, `ae534d13`, for both tests. Only the owner moved the cable; there
was no console input and no `soft_connect` or `power/wakeup` write. Raw logs
stay private with the custodian.

**E: suspend inside the first 30 s (0635).**
- s2idle with an RTC alarm 20 s ahead ran from 13.61 s to 33.50 s, rc 0,
  woken on IRQ 191. The regulator late cleanup's 30 s point fell inside it.
- After resume: taint 0, and no warning, oops or bug in the kernel log. P4
  had the late cleanup's I2C warning at this point.
- Resume showed 0633's `pullup D-` and `pullup D+`. The replug at 36.75 s
  reached `configured` at 36.77 s with no input.
- Limit: the late cleanup prints nothing on this board, so the evidence is
  the missing warning with the suspend spanning 30 s, not a log line.

**G: reconnect with no sysfs write (0634).**
- `11271000.usb` has no `power/wakeup` file at all, so 0634 leaves it not
  wake-capable, as intended.

| Cycle | Suspend | After resume | Replug to `configured` |
| --- | --- | --- | --- |
| G1 | 174.08–193.46 s, rc 0, IRQ 191 | runtime PM suspended, `OPSTATE` `0x3` | 199.82 → 200.34 s, `OPSTATE` `0x12` |
| G2 | 215.26–235.46 s, rc 0 | — | 241.86 → 241.87 s |
| G3 (no suspend) | — | — | reconnected by about 258.6 s, IRQ count 1023 → 1077, SSH works |

- The eMMC hash matched after G1. At the end: taint 0, `suspend_stats` 3
  successes and 0 failures, battery 86 → 82 %, 24.2 °C.
- G3 was marked a stop by the test script, not by a failure. Right after the
  replug the UDC still read `configured` from before the unplug, with an
  unchanged IRQ count and `OPSTATE` `0x13`. The script's next read caught
  the host's reset (not configured), and 0.2 s later the gadget was
  configured again. A replug check should wait for the IRQ count to change
  or for `OPSTATE` `0x12`, not trust `configured` alone.

**Reading.** 0634 and 0635 work on a built image, and the gadget reconnects
after suspend with no console input. The owner's request to stop typing the
disconnect/connect is met on this image.

### P6 (2026-11-08): sleep hooks for the remaining station drivers

The owner asked for every feature that suspend and runtime power management
need, and then a test plan. cpuidle, the SPM, cpufreq and the A72s belong to
their own sessions and are left out here. The five patches below are
compile-checked in the VM (W=1, no warnings). None has run on the device.
All five are modules in the station profile, so a running image built from
the same tree can take them with `rmmod` and `insmod`.

| Patch | Driver | Change |
| --- | --- | --- |
| [0651](../../patches/proposals/0651-Input-novatek-nt36xxx-stop-reporting-across-a-system.patch) | NT36772 touchscreen | Masks its interrupt across the suspend and releases every contact first. The controller is not told to sleep, because its sleep command is not known |
| [0652](../../patches/proposals/0652-leds-aw9120-turn-the-outputs-off-while-the-system-sl.patch) | AW9120 LEDs | `LED_CORE_SUSPENDRESUME`: the LED core sets each LED to 0 before the bus suspends and restores it at resume |
| [0653](../../patches/proposals/0653-soc-mediatek-mt6797-consys-refuse-a-system-suspend-w.patch) | CONSYS owner | Refuses the suspend from `.prepare` while CONN is on |
| [0654](../../patches/proposals/0654-media-mediatek-mt6797-seninf-refuse-a-system-suspend.patch) | Camera receiver | Refuses the suspend from `.prepare` while streaming |
| [0655](../../patches/proposals/0655-ASoC-mediatek-mt6797-mt6351-suspend-the-card-with-th.patch) | Audio card | `snd_soc_pm_ops`, so streams stop and the codec drops its bias for a suspend |

**Why CONSYS refuses instead of suspending.** In code, genpd powers a domain
off at `suspend_noirq` once every device in it has gone through suspend,
whatever their runtime state (`genpd_sync_power_off` compares only the
counts). CONN is not always-on, so with CONSYS loaded a suspend would cut
CONN and lose the connectivity firmware, and nothing restarts it at resume.
`.prepare` runs for every device before any device's suspend, so the refusal
comes before mac80211 has disconnected or stopped anything. It makes no radio
action. Earlier S1, P4 and P5 runs had Wi-Fi unloaded; whether CONSYS itself
was loaded in them is not recorded.

**Covered already, no change.**
- **Keyboard and lid wake:** 0628 and 0629 are in the image since P2, but
  neither wake has run. Tests K and L below cover them.
- **Display:** a suspend with the CRTC on takes the same disable path as a
  blank, which the station already uses on lid close.
- **Others:** the GPU, vibrator, backlight, STK3x1x, MTU3, FUSB301, bq25890,
  RTC and watchdog have sleep callbacks. The BMI160 only needs them while an
  IIO buffer runs.
- **Bluetooth, GNSS and FM** run through CONSYS, so 0653 covers them.

**Left open, with the reason.**
- **Wi-Fi across a suspend** needs a CONN sleep protocol (the vendor's WMT
  sleep) that is not mapped. For now the card unloads `mac`,
  `mt6797-wlan-core` and `mt6797-consys` before a suspend and loads them
  after (see the card list below). This is the radio driver owner's call: it
  is the same unload and reload the station already does by hand, and it
  adds no new radio action.
- **Unused clocks** (R2's PLLs and gates) stay on while `clk_ignore_unused` is
  on the command line. Dropping that flag needs owners for the display's MM,
  SMI and IOMMU clocks and for the loader-owned CONSYS and DVFSP users first.
  That work belongs to the display and clock lines, not to a sleep hook.
- **The audio controller held active while idle:** R1b measured no saving
  from turning the AUDIO domain off. Its register map has no cache, so
  letting it runtime-suspend risks a bus hang on a control access. Left
  as is.
- **Charger attached during a suspend** still charges without the guard
  until the next resume. There are two ways to close it, and both need the
  owner, because they add a charger write class. (a) Turn the bq25890
  watchdog off for the suspend (REG07 bits 5:4 = `00`) and on again at
  resume (`11`, 160 s, or the guard's current setting), and add
  `wakeup-source` to the charger node so a VBUS change wakes the system,
  after which 0630 refuses the next suspend. (b) Add the wake alone. Without
  (a), each 40 s watchdog expiry asserts INT and wakes the system. Neither
  is implemented.

**What the card needs (for the arch-root session).**
- `logind.conf`: `HandleLidSwitch=suspend`, `HandleLidSwitchExternalPower=ignore`
  and `HandleLidSwitchDocked=ignore`. With a charger attached 0630 refuses
  every suspend, so logind would only log failures.
- `sleep.conf`: `MemorySleepMode=s2idle`. `deep` does not exist on this
  firmware.
- A `systemd-sleep` hook. On `pre`, stop the Wi-Fi daemon, unload
  `mac mt6797-wlan-core mt6797-consys` and any Bluetooth, GNSS or FM
  modules, and stop the camera stream. On `post`, load them back. This
  waits for the radio driver owner's agreement.
- The SSH gadget needs nothing: 0633 and 0634 reconnect it.
- The lid switch reports `SW_LID` through `gpio-keys`, so udev tags it as a
  power switch for logind.

**Device tests, in order.** One image from this commit (profile
`mt6797-a53-station-a72`), on battery unless a step says otherwise, Wi-Fi
not joined. Each step's stop rules are the same as S1's: stop on any
warning, oops, taint change, eMMC hash change or failed resume.

| # | Test | Pass |
| --- | --- | --- |
| C | CONSYS loaded (WLAN `mac` unloaded, no join), `echo freeze > /sys/power/state` | `-EBUSY` and "CONN is on, refusing to suspend". No WLAN, STP or CONN message. Then unload `mt6797-consys` and run one 20 s RTC suspend: rc 0 |
| H | Touchscreen and AW9120 loaded, one LED set lit, audio loaded with no stream, `rtcwake -m freeze -s 20` with `regmap_reg_write` tracing on | rc 0. The LED reads the same brightness after resume. Touch reports after resume. `aplay` of a short file plays. The trace lists the writes made (expected: AW9120 only) |
| K | Lid open, blanked, `rtcwake -m freeze -s 120`; at about 20 s the owner presses one key | Resume well before 120 s. `pm_wakeup_irq` is the AW9523 parent EINT, not 191 |
| L | Lid open, `rtcwake -m freeze -s 120`; the owner closes the lid at about 10 s and opens it at about 40 s | Still suspended after the close. Resume at the open, before 120 s. Display and keyboard return |
| S | Suspended current: unplugged, blanked, LEDs off, CONSYS and camera unloaded, CPUs 1–7 offline. Read the fuel gauge's `charge_counter` and the boot-time clock, `rtcwake -m freeze -s 600`, read both again | rc 0, IRQ 191. Mean suspended current = Δ`charge_counter` / Δtime (44.98 µAh per step). Compare with R1b's 96 mA awake. The bq25890 guard restores its state after resume (the 40 s chip watchdog expires inside the 600 s) |
| S2 | As S with CPUs 1–7 online | Only if S is under 60 mA, to see whether the offlining still matters asleep |

**Every write the tests make.**
- **sysfs:** `/sys/power/state` = `freeze`, through `echo` or `rtcwake`;
  `/sys/class/rtc/rtc0/wakealarm` through `rtcwake`, which sets the MT6351
  RTC alarm registers as in S1; `/sys/devices/system/cpu/cpu{1..7}/online`
  = `0` then `1`, as in R1b; one AW9120 LED's `brightness` = `255` then `0`
  (test H); the tracing control files.
- **New in-kernel writes from these patches:** only 0652's. At suspend,
  for each lit AW9120 output `n`: CMDR (`0x61`) = `0xa000 | n << 8`, then
  GCR (`0x01`) = `0x0000` when the last output goes dark. At resume, GCR =
  `0x0001` first, then CMDR = `0xa000 | n << 8 | pwm` with the saved PWM.
  These are the writes the LED driver already makes for sysfs brightness
  changes.
- **0655:** ASoC may power down codec widgets that are still on. With no
  stream, none are expected. Test H's trace records what actually happens.
- **Not a write, but a state change:** in S, the bq25890 watchdog expires
  during the suspend and the chip returns to its defaults (charging enabled,
  with no VBUS). At resume the guard rewrites its admitted settings.

#### P6 result (2026-11-08): C, H, K and S pass; audio breaks across a suspend; a lid close wakes through the keyboard

Run by the device custodian, owner-approved, on image D1 (`station-work-92`, boot2
`09ae90fd…`, which carries 0651-0670; see the
[test plan](../2026-11-08-cpu-power-test-plan/README.md)). Station RAM root, boot
`17a3859e-6b05-4dcb-b27f-3b20f08fd009`, battery 94 % to 87 %. CPU8-9 were taken offline by
hand first, so no suspend ran with the A72s online. Every resume left taint 0, boot2's hash
unchanged and no warning line. Raw logs stay private with the custodian. `rtcwake` is not
in the station's busybox, so each step armed `rtc0/wakealarm` and wrote `freeze` to
`/sys/power/state` itself.

| Test | Result |
| --- | --- |
| C | Pass. With CONSYS loaded and `mac` unloaded, `freeze` failed with `EBUSY` and "CONN is on, refusing to suspend". After unloading `mt6797-consys` and `mt6797-wlan-core`, a 20 s suspend returned 0, woken by IRQ 191 (the PMIC, RTC alarm) after 19.8 s |
| H | Pass except audio. Two 20 s suspends returned 0 (IRQ 191). The AW9120 LED read 255 after resume. Touch reported after resume: 24936 bytes of events, its IRQ (`3-0062`) rose from 18 to 246. The 5 s touch window in the script was too short for the owner, so the touch check is from a separate 90 s capture. **Audio fails after resume**: `aplay` returns an I/O error, and the AFE logs `mtk_afe_pcm_pointer hw_ptr err` at the first stream. Reloading `snd-soc-mt6797-afe` and `mt6797-mt6351` and reapplying `audio-start`'s mixer settings brought playback back (rc 0), so the suspend breaks it |
| K | Pass. One key press woke a 120 s suspend after 23.3 s, through IRQ 25 (`5-005b`, the keyboard expander), not IRQ 191 |
| L | **Fail.** The suspend woke after 2.7 s, as the owner closed the lid, through IRQ 25, the keyboard expander, not the Hall lid line (IRQ 20) |
| S | 600 s suspend, rc 0, woken by IRQ 191 on time. CPU1-7 offline, display blanked, LEDs off, CONSYS and camera unloaded: **mean 73.3 mA** (`charge_counter` −11898 to −24106 µAh over 599.5 s). S2 did not run (S was not under 60 mA) |

**Writes during H's suspend** (`regmap_reg_write` trace, one 20 s cycle): INFRACFG syscon
`0x10001000` 676, PMIC wrapper 71, I2C `5-005b` 60, AW9120 `4-002c` 42, MMSYS syscon
`0x14000000` 26, the SPM power controller 14, bq25890 1. The record expected AW9120 only; the
rest are the framework's clock, power-domain and wake paths, which the trace shows for the
first time.

**Reading.** s2idle on this firmware saves about 23 mA against R1b's 96 mA awake floor:
the SoC stays at run voltage with its clocks as they were, as expected without the SPM. A
lid close cannot drive a suspend on lid close yet, because the keyboard expander wakes the
system as the lid closes. Audio needs a resume path before a suspend can be used with sound.

#### P6 follow-up (2026-11-08): the two failures, from the code

**L: the keyboard wake fires only because the lid closed during the suspend.**
- `matrix_keypad_suspend()` arms the row wakes only while the input device
  is enabled, that is, opened and not inhibited.
- `gemini-lid` inhibits the keyboard when `SW_LID` reports closed. A suspend
  entered with the lid already closed therefore arms no keyboard wake.
- 0628 then leaves every AW9523 pin masked, and only the Hall line (IRQ 20,
  on the opening edge) can wake the system.
- In L the suspend began with the lid open, so the rows were armed. The lid
  closing pressed keys against the screen side, and IRQ 25 woke the system
  as the matrix should.
- That is a different flow from suspend on lid close, where logind reacts
  to the close, so the keyboard is already inhibited when the suspend starts.

So no kernel change is proposed. If a suspend begun with the lid open is
woken by a lid close, the resume finds the lid closed, `gemini-lid` inhibits
the keyboard, and logind sees the close and suspends again. That costs one
short wake.

Test **L2** replaces L:
- Load `gemini-lid` and close the lid. The log must say "keyboard
  inhibited".
- Write `freeze` with a 120 s alarm.
- The owner opens the lid at about 40 s.
- **Pass:** no wake before the open; the wake comes at the open on IRQ 20,
  not 25 and not 191; the keyboard is restored and the display returns.
- **Fail and stop:** a wake on IRQ 25 with the lid closed.

**Audio: genpd resets the AFE.**
- The AFE takes a runtime PM reference at probe and keeps it, so it is
  never runtime suspended.
- genpd still powers the AUDIO domain off at `suspend_noirq`: it compares
  only the count of suspended devices with the count in the domain. That
  happens with or without 0655.
- The AFE comes back from reset while the driver takes it for configured,
  hence `hw_ptr err`.
- The H trace's 14 SPM writes fit one domain power-off and power-on. The
  other domains were off or unloaded: MFG idle off, CONN unloaded.

[0671](../../patches/proposals/0671-ASoC-mediatek-mt6797-set-the-AFE-up-again-after-a-sy.patch)
fixes it the way mt8173 does: the AFE's DAI component gets the common
`mtk_afe_suspend()` and `mtk_afe_resume()`. These are called through 0655's
card ops. They stop the AFE before the suspend and set up its interrupt and
memory interface defaults again after it. No register list is needed,
because every AFE control is a DAPM control, which DAPM writes again at the
next stream. The patch is a module, compile-checked only.

Test **A**:
- On an image or module set with 0671, load audio, apply `audio-start`'s
  mixer settings and play a short file.
- Run a 20 s RTC suspend, then play the same file with no reload and no
  mixer change.
- **Pass:** rc 0 both times, with no `hw_ptr err`.
- New writes: the AFE's own runtime suspend and resume, which are
  `AFE_DAC_CON0` (AFE on bit cleared), `AFE_IRQ_MCU_CLR` = `0xffff`,
  `AFE_IRQ_MCU_EN`, `AFE_MEMIF_HDALIGN`, `AFE_MEMIF_MSB` and
  `AFE_CONN_24BIT`, plus the audio clock gates. The driver makes the same
  writes at probe and on every runtime transition.

**What the H trace's writes are.** All of them are explained by code paths
that already run on the station, and none is a new class:
- **INFRACFG (676):** infra clock gates. `mtk-i2c` enables and disables its
  clock around every transfer, and the AW9120, AW9523 and bq25890 traffic
  of a cycle is mostly I2C. The AUDIO domain's bus protection adds a few.
- **SPM (14):** the AUDIO domain off and on, as above.
- **PMIC wrapper (71):** the RTC alarm, the PMIC interrupt wake masks and
  the regulator and key state on suspend and resume.
- **`5-005b` (60):** the AW9523. 0628 unmasks the armed rows and restores
  the mask, and the keypad stops and restarts its column scan.
- **AW9120 (42):** 0652, as listed in P6.
- **MMSYS (26):** display clock gates from the DRM suspend and resume of an
  already blanked pipe.
- **bq25890 (1):** the charging guard's resume pass (0630).

#### L2 and the AFE register reads (2026-11-08)

Run by the device custodian, owner-approved, on D1, RAM root, boot
`e79a664d…`. `mac`, `mt6797-consys` and `mt6797-wlan-core` were unloaded.
Raw logs stay private with the custodian.

**AFE across one 20 s suspend** (rc 0, IRQ 191), read before and after:

| Register | Before | After |
| --- | --- | --- |
| `PWR_STATUS` | `0x2B00005C` | `0x2B00005C` (AUDIO, bit 24, on) |
| `AUDIO_PWR_CON` | `0x3330000D` | `0x3330000D` |
| `AUDIO_TOP_CON0` | `0x87FD4078` | `0x80FD4038` |
| `AFE_DAC_CON0` | `0x08000001` | `0x00000000` |
| `AFE_CONN3` | `0` | `0` |
| `AFE_ADDA_DL_SRC2_CON0` | `0x83001802` | `0x0F000000` |

- The domain is on again after resume, but the AFE's registers are back at
  their reset values. `aplay` then fails with `hw_ptr err`.
- This is 0671's premise, now observed. Test A still needs an image or
  module set carrying 0671.

**L2: pass, but with a warning per keyboard row.**
- The lid closed and `gemini-lid` inhibited the keyboard (rc 0).
- `freeze` with a 120 s alarm. The owner opened the lid, and the system
  woke after 45.2 s on IRQ 20 (Hall). The keyboard was restored (rc 0).
- No wake came while the lid was closed. That shows an inhibited keypad
  arms no row wake.
- Right after the wake, eight `Unbalanced enable for IRQ 225`…`232`
  warnings appeared, one per row, from `enable_irq()` in
  `matrix_keypad_scan()`. Taint went to 512.

**Why the warnings appear (from the log order and the code).**
- `gemini-lid` restored the keyboard at 769.400 s, from work on the
  non-freezable system workqueue. That was before the keypad's own resume
  (769.455 s) and the AW9523's (769.450 s).
- The uninhibit opened the keypad, and its scan enabled the row
  interrupts.
- `matrix_keypad_resume()` then found the device enabled and started it a
  second time. The second scan enabled the rows again, which gave one
  warning per row.
- The first scan also read the expander before the expander's resume.
- This happens on every lid-open wake, so it would hit suspend on lid
  close every time.

[0672](../../patches/proposals/0672-Input-gemini-lid-apply-the-lid-only-after-a-system-r.patch)
queues `gemini-lid`'s work on `system_freezable_wq`. A lid change seen
during a suspend or resume then applies once tasks are thawed, after every
device has resumed, and the keypad is started once. A close before a
suspend still applies at once. A close inside the freeze window applies
after the next resume, and logind then suspends again. The patch is a
module, compile-checked only. No change to `matrix_keypad` is needed:
its suspend and resume are balanced when nothing changes the inhibit
during the resume.

Test **L3**:
- Repeat L2 on 0672.
- **Pass:** the wake on IRQ 20, "lid open, keyboard restored 0" logged
  after the resume completes, no warning, taint unchanged, and a key works
  after the open.

#### Second mem suspend refused by MTU3 (2026-11-08)

Reported by the device custodian from the SPM mem path (0667) on D1, on
battery with the cable out: boot 3 retry in the
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md). Raw log
private.

**What the log shows.**
- The first `mem` suspend resumed. At resume 0633 cycled the pullup
  (`pullup D-`, then `pullup D+` 17 ms later), so the gadget had gone into
  that suspend still marked connected after an unplug.
- The next `mem` suspend came 0.5 s after that resume. MTU3 waited the
  full 100 ms, logged "ip sleep failed!!!", and returned -EBUSY.

**Reading.**
- The second suspend found the gadget pulled up and not connected: no
  host had reset it since the cycle.
- With a session that an unplug then suspended, as in P5, the IP sleeps.
  Pulled up with no session since, it does not, at least not within
  100 ms.
- The s2idle tests never had this case. P5's suspends each began from a
  suspended session, and P6's were not preceded by a reconnect cycle.
- Why the IP needs a session to sleep is not known.

[0676](../../patches/proposals/0676-usb-mtu3-drop-the-pullup-for-a-suspend-taken-with-no.patch)
handles it:
- A suspend taken while the gadget is pulled up with no host session takes
  D+ down first and puts it back at resume.
- For a device that is not pulled up, the driver already skips the IP
  sleep wait and powers the PHY and clocks down.
- A bus-suspended session keeps its pullup, as in P5.

MTU3 is built in, so 0676 needs an image. It is compile-checked only.

Test **U**:
- On battery with the cable out, start with the gadget enumerated, then
  unplug.
- Run three suspends in a row, 0.5 s apart, by the path under test (`mem`
  or `freeze`), each with a 20 s RTC alarm.
- **Pass:** all three return 0. The second and third log `pullup D-` at
  suspend and `pullup D+` at resume. Then replug, and SSH returns with no
  console input.
- On the `mem` path, also check that the SPM's wake report is unchanged
  from the first suspend. The IP is now powered down without having
  reported sleep, and whether the SPM program cares is not known.
- New writes: only MTU3's own pullup control (`mtu3_hs_softconn_set`), as
  0633 already makes.

#### No USB after a replug following mem suspends (2026-11-08)

Reported by the device custodian on D3, which carries 0676: item 1 of the
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md), boot
`1d20d160`. Raw logs private.

**Observed.**
- The gadget was enumerated, then unplugged. Five `mem` suspends followed,
  all rc 0, so 0676 removed the refusal.
- The first resume ran 0633's cycle (`pullup D-`, then `D+`). Each later
  suspend logged `pullup D-` (0676), and each resume logged the PHY's
  "forcing valid B-device session", then `pullup D+`.
- At the replug the host saw nothing. The UDC read `not attached` and
  `bq25890` online 1.
- There was no MTU3 or PHY log line after the last resume, at the replug or
  later.
- A second replug, a `soft_connect` cycle and a role write did not recover
  it. A reboot did.

**Reading from the code (not yet measured).**
- MTU3's resume sets only the power-down bits, the interrupt enables and
  the pullup. It assumes the controller's other registers survived.
- s2idle keeps them: P5's replugs after the same cycle worked.
- If the SPM `mem` program powers the SSUSB block or its PHY down, the
  gadget's speed and endpoint setup, the IPPC port settings and the U2 PHY
  tuning (set by `phy_init`, which resume does not run again) are all at
  reset values.
- In OTG mode a `soft_connect` cycle does not run `mtu3_start()` again, and
  a role write to the current role does nothing. That fits the failed
  recovery.
- This is the leading hypothesis. Which registers are lost decides the
  fix, so no patch yet.

**Proposed read-only check (test R-USB).**

Read these 32-bit registers at four points:
1. gadget enumerated;
2. after the unplug;
3. after one `mem` resume with the cable out;
4. after the replug.

The registers:
- **MAC** at `0x11271000`, offsets `0x0004` `0x0084` `0x0100` `0x0800`
  `0x0850` `0x2404` `0x240c` `0x2418` `0x2460`;
- **IPPC** at `0x11280700`, offsets `0x00` `0x04` `0x08` `0x10` `0x50`
  `0x98`;
- **U2 PHY** at `0x11290800`, offsets `0x000` `0x014` `0x018` `0x020`
  `0x030` `0x068` `0x06c` `0x080`.

These are reads only. MTU3's clocks are on after every resume, because
its runtime suspend does nothing without a wake path (0634).

Control: the same unplug, one `freeze` suspend, then a replug, on D3. A
reconnect there makes the failure `mem`-specific.

**Decision.**
- **Only MAC and IPPC reset:** run the device controller's start sequence
  again at resume when the reset is detected.
- **PHY also reset:** run `phy_exit` and `phy_init` around the PHY power
  cycle on that path.
- **Nothing reset:** the cause is elsewhere, so look at the line state and
  the interrupt path.

**`i2c 4-0020: Unbalanced pm_runtime_enable!`** (boot `54c9d47b`, once in
about nine cycles):
- `4-0020` is the hi556 camera sensor's I2C client. No driver was bound:
  the `i2c` prefix is the bus name, which is printed when no driver is
  bound.
- The hi556 probe defers on the camera receiver's clock before it touches
  runtime PM, and the receiver was unbound too.
- So the warning comes from neither driver nor from these patches. Its
  source is not known. It is a one-line warning with no taint.

#### R-USB result and the fix (2026-11-09)

Read by the device custodian on D3, boot `6dbf6d59`: the
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md),
"D3 R-USB". Raw log private.

- **`freeze` control:** the disconnect cleared only MAC `0x0084` and
  `0x0800`. At the replug the gadget was configured at once, and every
  register read its reference value again.
- **After `mem`:** all nine MAC registers read 0.
  - IPPC `0x00` went from `0x00011000` to `0x00011001`: the IP software
    reset is asserted.
  - IPPC `0x10` went from `0x01003D0F` to `0`: no clock status.
  - IPPC `0x50` went from `0xC8` to `0x4D`: the U2 port disabled and
    selected for the host, its reset value.
  - The U2 PHY's eight registers were unchanged.
- That is the record's first decision branch: the MAC and IPPC are reset,
  and the PHY is kept.

[0681](../../patches/proposals/0681-usb-mtu3-set-the-device-up-again-when-suspend-reset-.patch):
- At resume, when the software reset reads asserted, MTU3 takes the IP out
  of reset and repeats probe's device setup: the device reset, then the
  port enable and selection (`mtu3_device_enable`, which turns `0x4D` back
  into `0xC8`), then the CSR defaults and the speed.
- The existing resume then powers the device on, enables its interrupts
  and restores the pullup (0633 or 0676).
- A host-side setup after such a reset is not done.
- MTU3 is built in, so 0681 needs an image. Compile-checked only.

Test **U2**, on an image carrying 0681:
- On battery, enumerate the gadget, then unplug.
- Run two `mem` suspends, then replug.
- **Pass:** each resume logs "IP was reset in suspend, setting it up
  again"; IPPC `0x00` reads `0x00011000` and `0x50` reads `0xC8` after
  resume; the replug reaches `configured` with no console input and SSH
  returns.
- Repeat once with the cable in at suspend. 0630 refuses that suspend, so
  nothing should change.
- New writes: MTU3's own probe-time setup writes to its IPPC and MAC,
  which probe already makes at every boot.

#### Thermal zone lost after a mem resume (2026-11-09)

Reported by the device custodian from cpuidle item 4: `station-work-95`,
boot `b7dba389`, one 30 s `mem` suspend through `mt6797-spm-sleep`, rc 0.
Every later read of `soc-thermal` failed with ENODATA for about 430 s,
until power-off. Raw logs private.

**Reading (from the code).**
- `mtk_read_temp()` returns `THERMAL_TEMP_INVALID` when no bank has a
  valid sample, and the core turns that into ENODATA. So after the resume
  the banks stopped producing samples.
- The likely cause: the `mem` path cut the power of the thermal
  controller or the AUXADC. The SSUSB IP was reset the same way (R-USB).
- The driver has no sleep callbacks.
- The hardware thermal reset compares the same samples, so it most likely
  had no input either. That is a safety gap, not only a reporting one.
- The cpuidle session's interim rule covers it until a fix runs: no
  lid-close suspend outside tests, and no SPM module at boot.

[0683](../../patches/proposals/0683-thermal-drivers-mediatek-auxadc_thermal-set-MT6797-u.patch):
- At resume, if any MT6797 bank has no valid sample, close the setup
  transaction and run it again, as probe does: clocks, controller reset,
  APMIXED buffer, AUXADC channel and banks, up to a valid first sample.
- Then arm the hardware reset again if it was armed, with probe's checks.
- s2idle keeps valid samples, so it is untouched.
- The thermal core polls no zone until every device has resumed.
- The thermal driver is built in, so 0683 needs an image. Compile-checked
  only.

Test **T-M**:
- On an image with 0683, record `soc-thermal` and the "hardware thermal
  reset armed" line with its `REQ_MODE` at boot.
- Run one 30 s `mem` suspend.
- **Pass:** the resume logs "thermal banks lost their state in suspend,
  setting them up again" and a new "hardware thermal reset armed" line
  with the same `REQ_MODE`; `soc-thermal` reads a plausible value within
  1 s and stays readable for 5 min.
- **Fail and stop:** "not set up again" or "not armed again".
- New writes: the driver's probe-time setup (the APMIXED `TS_CON1`
  buffer, the AUXADC channel, the bank registers and the TOPRGU thermal
  route), which every boot already makes.

#### T-M and U2 pass (2026-11-10)

Run by the device custodian on `station-work-96` (boot2 `86322507…`, which
carries 0681, 0682 and 0683), boot `53187f71`. Two 30 s `mem` suspends on
battery, then a replug. Record:
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md),
commit `8b1ba929`. Raw logs private.

- **T-M (0683): pass.**
  - Both resumes logged "thermal banks lost their state in suspend,
    setting them up again".
  - Both re-armed the hardware reset at 117000 mC, against the boot
    baseline `REQ_MODE=0x003c0003`.
  - `soc-thermal` stayed readable from 1 s after each resume through a
    10 min window, at 21.5–24.8 °C. There was no ENODATA.
- **U2 (0681): pass.**
  - Both resumes logged "IP was reset in suspend, setting it up again".
  - After the replug the UDC was configured within 1 s.
  - IPPC, MAC, `bq25890` and FUSB301 were back at their pre-unplug values.
  - So the charger saw this replug. The earlier missed replug (R-USB) did
    not recur, and its cause is not established.
- No fault line, and taint 0.
- U2's cable-in step was not run. It is not needed: on D3 the guard
  (0630) already refused a `mem` suspend with the cable in.
- **Display:** a resume turns the panel on through fbcon's resume pan.
  That belongs to the display line.
- **Still to run:** test A (0671, audio after a suspend) and L3 (0672, no
  keypad warning after a lid-open wake).

#### Test A and L3 pass (2026-11-10)

Run by the device custodian on `station-work-96`, boot `53187f71`: s2idle,
on battery, with `mt6797-spm-sleep` unloaded. Record: the
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md),
"station-work-96 Test A and L3", commit `afb0bc24`. Raw logs private.

- **A (0671): pass.**
  - The first playback returned 0. A 20 s RTC suspend returned 0. The
    second playback returned 0 with no reload and no mixer change.
  - There was no `hw_ptr err`.
  - That suspend woke on IRQ 25, the keyboard expander, not the RTC.
  - The kernel log has "lid closed, keyboard inhibited" just after that
    resume, so the lid was closed during the suspend. That fits the
    keys-against-the-screen wake already explained under L: the suspend
    was begun with the lid open.
- **L3 (0672): pass.**
  - The lid was closed first ("keyboard inhibited 0"), then a suspend with
    a 120 s alarm. The owner opened the lid at 28.6 s, and it woke on
    IRQ 20.
  - "lid open, keyboard restored 0" came after the device resume, at
    "Restarting tasks". There was no "Unbalanced enable" warning, and
    taint stayed 0.
  - Key A reported a press and a release afterwards. USB was configured
    after the replug.
- **Guard:** with the cable in, an s2idle suspend was also refused
  ("guard: charger attached, refusing to suspend", -EBUSY). That is 0630's
  design: any suspend is refused while a charger is attached, whatever the
  sleep state.

#### Owner decisions: charger wake, Wi-Fi across a suspend (2026-11-10)

Relayed by the device custodian, in the owner's words:
1. "If a charger is plugged during a suspend, the device should wake up."
2. "wifi unload/reload during a suspend is ok."

0630's refusal to start a suspend with a charger attached stays as it is.

**Charger wake (0685, 0686).**
- The `bq25890` has no interrupt line here (its driver polls it). The
  left port's FUSB301 is polled, and the right port is source-only. So
  neither can wake the system.
- The MT6351's own charger detection can, through its CHRDET interrupt
  (hwirq 46). The PMIC interrupt already wakes the system for the power
  key and the RTC.
- [0685](../../patches/proposals/0685-mfd-mt6397-give-the-MT6351-fuel-gauge-the-charger-de.patch)
  passes CHRDET to the fuel gauge cell.
- [0686](../../patches/proposals/0686-power-supply-mt6351-fuel-gauge-wake-on-a-charger-att.patch)
  requests it, reports a battery-supply change from it and makes it a
  wakeup interrupt.
- After such a wake, the charger's resume pass applies the guard, and
  0630 refuses the next suspend while the charger stays attached.
- This takes the owner's option without the watchdog write: no charger
  register is written. Both are built in, so they need an image.
  Compile-checked only.
- Whether CHRDET follows VBUS on this board is not yet shown. Test W1
  decides it.
- New writes: the PMIC interrupt controller sets the CHRDET enable bit,
  INT_CON2 (`0x02ce`) bit 14, through its standard enable. It clears that
  interrupt's status bit in INT_STATUS2 (`0x02e4`) when the interrupt
  fires.

**Wi-Fi across a suspend: what the card needs (for the arch-root
session).**

A `systemd-sleep` hook, for example
`/usr/lib/systemd/system-sleep/gemini-radios`:
- **`pre`:** stop the Wi-Fi daemon (`iwd`) and any Bluetooth service.
  Then unload, in this order, skipping modules that are not loaded:
  `mac`, `btmt6797`, `gnss-mt6797`, `radio-mt6797`, `mt6797-consys`,
  `mt6797-wlan-core`.
  - `mt6797-wlan-core` returns EAGAIN while `mt6797-consys` is loaded.
    The custodian measured this on `station-work-96` and `-97`, boot
    `56832cd1`.
  - Bluetooth, GNSS and FM use CONSYS's exported calls, so they go before
    it. That order is from the code and is untested.
  - The card's hook (gemini-base 32, card-27) uses this order.
- **`post`:** load back the modules that were loaded before, in
  `wifi-start`'s proven boot order (`mt6797-wlan-core`, `mt6797-consys`,
  `mac`). Then start the daemons that were running. The card's hook
  (card-26, `cbdbb676`) does this.
- Record what was loaded in `pre`, so that `post` restores only that. A
  radio the user had off stays off.
- Without the hook, 0653 refuses every suspend while CONSYS is loaded,
  so logind's suspend fails safely and nothing breaks.

With the earlier card items: `HandleLidSwitch=suspend`,
`HandleLidSwitchExternalPower=ignore`, `HandleLidSwitchDocked=ignore`.
`MemorySleepMode` follows what the cpuidle session makes the station
default; s2idle until then.

**Device tests.**
- **W1 (awake, decides CHRDET):** on battery, read the `chrdet` line in
  `/proc/interrupts`. Plug a charger and wait 5 s, then unplug and wait
  5 s. **Pass:** the count rises at the plug, at least.
  `power/wakeup` of the fuel gauge device reads `enabled`.
- **W2 (s2idle):** on battery, with CONSYS unloaded, suspend with a 120 s
  alarm. The owner plugs the charger at about 20 s. **Pass:** the system
  wakes well before 120 s on the PMIC interrupt (191). The guard logs
  the charger, and the next suspend attempt is refused (0630).
- **W3 (`mem`):** as W2 on the SPM `mem` path. This also needs the PMIC
  interrupt in the SPM wake mask, which the cpuidle session owns.
- **R-W (Wi-Fi hook, once the card has it):** with Wi-Fi joined, close
  the lid, wait 60 s, then open it. **Pass:** the hook unloads the
  modules, the suspend returns 0, and Wi-Fi rejoins after the open with
  no manual step. One join only, under the existing rejoin rules.

#### W1–W3 on station-work-97 (2026-11-10)

Run by the device custodian, boot `56832cd1` (from `bca6ccc6`). Record:
the [CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md),
"station-work-97", commit `3190ed4d`. Raw logs private. At boot the fuel
gauge's wakeup read `enabled`, and CHRDET is virq 209.

- **W1: pass.** CHRDET counted 2 → 3 at the plug and → 4 at the unplug.
  It follows VBUS on this board.
- **W2: pass.** In s2idle with a 120 s alarm, the owner plugged in at
  about 20 s. The suspend ended at 24.2 s, woken by IRQ 191. The next
  suspend was refused by the guard (0630). MTU3 also refused it, with
  the host session live.
- **W3: woke on the charger.**
  - The SPM reported `r12=0x40`, the EINT event, and `raw=0x40`.
  - `timer_out` was `0x001d4850`. In the timer wakes it equals the
    programmed time in 32 kHz ticks (`0x000f0088` for 30 s), so it reads
    as the time asleep: 58.6 s.
  - So the SPM slept 58.6 s and woke on the EINT. Either the plug came at
    about 58 s, or an earlier CHRDET edge did not wake it.
  - `loops=2` is one extra WFI exit before the PCM-return check, as when
    the EINT also reaches the GIC. Timer wakes show `loops=1`. Nothing
    suggests the SPM re-entered.
  - **Owner's answer: the plug came at about 20 s.** So under `mem` the
    plug did not wake the station; a later EINT event did, about 38 s
    after the plug. The custodian records W3 as not passed.
  - s2idle woke within about 4 s of the plug (W2), so the CHRDET child,
    the MT6351 interrupt chip and the EINT176 arming work. The delay is
    specific to the `mem` path, the SPM side, which the cpuidle session
    owns.
  - Two `mem`-side explanations fit, and one read separates them:
    (1) the PMIC's interrupt line was already asserted at entry, by a
    pending, unhandled status bit, so the plug made no new edge for the
    SPM's EINT event; (2) EINT176's detection or debounce does not run
    under the SPM program until something else re-triggers it. Read the
    MT6351 `INT_STATUS0`–`3` (`0x02e0`–`0x02e6`) and `INT_CON0`–`3`
    through the PMIC wrapper's regmap debugfs just before writing
    `mem`. Any status bit set that is also enabled points to (1).
- **Open: CHRDET counted 4 → 47 between W1 and W2's resume.**
  - W1's plug and W3's plug added 1 and 2. The extra 43 came somewhere in
    that window, which also held the 0684 display step and a `mem`
    suspend with the cable out. The run did not sample the count often
    enough to place them.
  - A storm while plugged would mean repeated wakes or wasted interrupt
    work. Decision: sample the count each second through a plug, 60 s
    attached and idle, and an unplug. Steady while attached is fine. A
    climb while attached needs a fix in the interrupt handling.

#### CHRDET trace and timed W3 (2026-11-10)

Run by the device custodian on `station-work-97`. Record: the
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md),
"station-work-97 CHRDET trace and timed W3", commit `d77d3feb`.

- **No CHRDET storm.** The 4 → 47 jump was the script's: it summed
  fields 2–9 of the `/proc/interrupts` line. With CPUs 1–7 offline, only
  CPU0's column is printed, so the sum took in the hwirq number 46.
- Sampled each second with every CPU online: one count per plug and per
  unplug, and none during 60 s attached.
- **W3 fails, and not on the PMIC side.**
  - With the plug timed at 21 s, the SPM slept the full 120 s
    (`timer_out=0x003c0088`, `r12=0x41`, `loops=2`).
  - MT6351 `INT_STATUS0`–`3` read `0000`, and `INT_CON2` read `0x4000`
    (CHRDET enabled), both right before and right after the suspend. So
    no PMIC line was held at entry.
  - That is explanation (2): EINT176's detection under the SPM program.
    It belongs to the cpuidle session, which has the wake line.
- The charger wake therefore works in s2idle (W2) and not yet in `mem`.
  Nothing in 0685 or 0686 needs to change.

#### First lid-close suspend on the card root (2026-11-12, unplanned)

Reported by the device custodian: card-32 Arch root, `station-work-112`,
boot `8990918b`. logind suspended on a lid close during an audio
measurement, on battery. Raw logs private.

- The s2idle suspend returned, and the root on microSD stayed rw.
  `mmcblk1` resumed with no I/O error.
- The radio sleep hook unloaded Wi-Fi and reloaded it, and Wi-Fi rejoined
  about 4 s after the resume.
- `aplay` was running across the suspend. PipeWire's restart then logged
  16 `hw_ptr err`, which is the running-stream case the audio session
  set aside (test A covered only an idle card). It is passed to the
  audio line.
- **Battery current after the resume: open.**
  - The same measurement state read 150.6 mA before the suspend and
    284.5 mA after it, steady over the following minutes and across every
    audio state of the second run.
  - The gauge was not stuck. `current_now` changes once per FGADC latch,
    about every 5 s, so five equal samples in a row are normal.
  - The cause is not known. Candidates are anything that the resume or
    the hook left on: Wi-Fi joined where it was not before, the panel or
    backlight lit by the resume, the audio path held up by the broken
    stream, or a clock or domain left running.
- Check (reads only), before a suspend and 60 s after its resume, in the
  same state:
  - battery current;
  - `bl_power` and brightness, and `fb0` blank;
  - Wi-Fi link state;
  - `/sys/kernel/debug/clk/clk_summary` and `pm_genpd/pm_genpd_summary`;
  - runtime PM status of the audio, display and USB devices;
  - two `/proc/interrupts` reads 10 s apart.

  The difference between the two sets names the cause.

- **Owner's observation:** "I think the screen was blank, but the
  backlight was on". The image carried 0684.
- **Reading from the code:** `gemini-lid` turns the backlight off at a
  close and on at an open, whatever the display was doing. The display
  had been blanked for the measurement before the lid closed. So the open
  lit the backlight behind a sleeping panel. That fits the observation
  and the size of the rise.
- [0755](../../patches/proposals/0755-Input-gemini-lid-light-the-backlight-on-open-only-if.patch)
  records at the close whether the backlight was lit, and the open turns
  it back on only then. A display blanked before the close stays dark
  until its own unblank, by DPMS or the console. `gemini-lid` is a module.
  Compile-checked only.
- **Test BL** (with the owner's go-ahead, the root being on microSD):
  1. Blank the display.
  2. Close the lid and let logind suspend.
  3. Open the lid.

  **Pass:** `bl_power` still reads off and the battery current is back at
  its pre-suspend level within 60 s. A second run with the display lit
  before the close must come back lit.

## Analysis

- **Firmware facts are from disassembly; the hang is an inference.** The
  PSCI version, the missing `SYSTEM_SUSPEND`, the affinity limit and the
  terminal `wfi` loop are observed. That a core never returns without the PCM
  program is inferred from the code: it is the only path out of the loop, and
  the vendor always kicks the SPM first. The source review alone had guessed
  the opposite (a cluster power-down without the SPM might be harmless).
  Disassembly overrides that guess, and the plan treats the states as unsafe.
- **Any saving is a hypothesis until R1.** No idle current has been measured
  on the station or on Gemian. The plan's order rests on hardware that is
  known to be on: the loader's clocks, the AUDIO domain while idle, the Wi-Fi
  poll, LEDs, the UART and VCORE at its run voltage. None of these has a
  measured share.
- **The Gemian practice result is biased.** The captures were taken over
  Wi-Fi SSH, which keeps the Wi-Fi wakeup sources busy. A screen-off Gemian on
  battery may sleep properly. R3 measures that case.
- **Some driver entries are from source only.** Where the table says `code`,
  the hook has never run on this unit.

## Conclusion

`inconclusive` until the read-only steps run. On this firmware the reachable
target is s2idle plus runtime PM and gated clocks and domains. CPU idle below
WFI and any system sleep state need the SPM, either through a Linux SPM driver
that loads the vendor program or through a replaced secure firmware; both are
owner decisions. The first actions are R1, R2 and R3. Then comes one batched
image (P1: suspend and RTC options, two wake sources, the charge guard's sleep
state), followed by module fixes for the drivers that have no sleep hook.

## Follow-up

- Correct the idle-state labels in [CPU clusters §5.3](../../docs/hardware/mt6797-cpu-clusters.md#53-idle-states)
  (done with this record).
- Hand R1–R3 to the device custodian.
- After R1–R3, open the P1 image as its own record with its own candidate.
