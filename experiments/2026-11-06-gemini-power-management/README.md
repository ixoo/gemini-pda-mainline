# Experiment: what the Gemini needs for battery-efficient power management

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-06-gemini-power-management` |
| Status | `planned`: source, binary and configuration assessment done; no build, boot or device access; the first steps below are read-only |
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
- **Method:** read-only, except the charge guard's existing admitted stop. No
  module load other than the Wi-Fi modules' normal load and unload.
- **Stop:** battery below 30 %, temperature above 45 °C, any kernel warning,
  or the SSH link lost.
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

### S1: first s2idle on the P1 image (after P1 is built)

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
