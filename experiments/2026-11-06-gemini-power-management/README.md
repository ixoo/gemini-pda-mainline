# Experiment: what the Gemini needs for battery-efficient power management

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-06-gemini-power-management` |
| Status | `running`: assessment done; R1, R1b, R2 run; S1 passed on the P2 image (s2idle entered and resumed, RTC and power-key wakes); gadget reattach fix 0633 compile-checked; CPU policy shown on lid close; R3 not run |
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

**Fix: [0633](../../patches/proposals/0633-usb-mtu3-reconnect-after-a-suspend-taken-with-a-susp.patch).**
Such a suspend is now treated as a disconnect: the pullup goes down, the
gadget driver is told, and the connection's runtime PM reference is
dropped. At resume the pullup goes up again when the gadget wants it, which
is what the manual soft-connect cycle did. Compile-checked with `W=1`; built
in, so it needs an image.

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
