# Roadmap

Deliver full Gemini PDA support through maintained upstream Linux interfaces,
with ordinary distribution updates and an independently bootable recovery path.
A capability is complete when its host support is in a released upstream kernel
and passes a named regression protocol. A build is not hardware support, and an
experiment result is not released support.

This file states the order of work and nothing else. The
[support matrix](HARDWARE_SUPPORT.md) owns runtime claims, the
[experiments index](../experiments/README.md) owns chronology and exact
candidates, and [`docs/hardware/`](hardware/README.md) owns durable facts. Keep
this file under 200 lines; move anything else to an experiment record.

The order below was rewritten on 2026-11-04 from the
[release readiness audit](RELEASE_READINESS.md) and the follow-ups in each record.
The owner can reorder it, and any step named as an owner decision waits for one. The
[version it replaces](https://github.com/ixoo/gemini-pda-mainline/blob/754af5b7/docs/ROADMAP.md),
which stopped at October's boot queue and Wi-Fi throughput series, stays in Git. The
reviews behind the earlier order are the
[2026-10-03 project review](../experiments/2026-10-03-project-review/README.md) and the
[2026-10-05 consolidation](../experiments/2026-10-05-repository-consolidation/README.md),
which also keeps the [earlier roadmap](../experiments/2026-10-05-repository-consolidation/ROADMAP_2026-10-04.md).

## Where we stand (2026-11-04)

- **Working method.** The [station](../experiments/2026-10-30-mainline-dev-station/README.md)
  is the working system: a RAM root on `boot2`, written from itself with full readback,
  then a power-off and the owner's selection. New drivers iterate as modules.
- **Boots to a usable shell on one unit.** Native console, keyboard, lid, USB SSH, speakers
  and headphones, the charge guard and the thermal trips are all at boot on the station.
  Wi-Fi starts by itself and joins as WPA2-PSK.
- **Modules loaded by hand.** Touch, Panfrost, A72s, Bluetooth A2DP, sensors, front camera,
  LEDs and the GNSS host. [The matrix](HARDWARE_SUPPORT.md) has each one's limits.
- **Release.** The owner declared [v1](RELEASE_READINESS.md): everything working so far, with limited testing, at the user's own risk. Profile `mt6797-a53-release` and a public RAM root have
  [booted once](../experiments/2026-10-30-mainline-dev-station/README.md#first-boot-of-the-release-image-2026-11-04).
  No one else can install or build it yet.
- **Not started.** Suspend and cpuidle. No upstream submission.
- **Started.** cpufreq for the A53 clusters at the firmware's voltage: schedutil and CPU
  cooling [pass on one boot](../experiments/2026-11-07-mt6797-a53-cpufreq/README.md#attempt-a3-2026-11-07)
  from modules loaded by hand.

## Current order of work

<a id="current-plan-2026-10-03-review"></a>
Each boot is a reviewed experiment with its own validated candidate, finite
budgets and stop conditions under the [safety rules](SAFETY.md).

### 1. After v1

The owner shipped v1 on 2026-11-04 as it stands. Its [known gaps](RELEASE_READINESS.md#known-gaps-in-v1)
come next as tester need shows: first the first install and a published kernel package. Those
that change boot files go in one image. The persistent root has an agreed
[design](../experiments/2026-11-06-gemini-arch-root/README.md): Arch Linux ARM, systemd-native,
iwd and sway, developed on microSD first, with its first steps in order.

Owner decisions there: Gemian's root read-only or one dedicated directory, the country protocol,
how the optional modules are offered, and a second unit.

### 2. Power

cpufreq and power governors are the important gap the owner named. Suspend, cpuidle
and cpufreq decide battery life and heat. Only A53 cpufreq has started: the
[A53 cpufreq experiment](../experiments/2026-11-07-mt6797-a53-cpufreq/README.md) scales both
clusters at the firmware's 1.00 V with schedutil and CPU cooling, and passed on one boot from
modules loaded by hand. Loading it at boot after a longer run under heat, then voltage
scaling, CCI and the A72s follow it.
[Power accounting](../experiments/2026-11-01-gemini-power-accounting/README.md) is a design
proposal only. The [CPU clusters document](hardware/mt6797-cpu-clusters.md#61-can-a-standard-linux-governor-drive-cpu-frequency)
holds the defensible order for frequency scaling, starting with the A53s. The
[power-management assessment](../experiments/2026-11-06-gemini-power-management/README.md)
holds the per-driver suspend and runtime-PM state and the ordered plan for s2idle,
wake sources and cpuidle, starting with read-only measurements.

### 3. Small device checks already written down

None of these needs new design. They go with the next convenient boot.

- [LEDs](../experiments/2026-11-04-gemini-aw9120-leds/README.md#follow-up): caps lock as the
  default trigger on the next image, step 9, and two open questions.
- [Bluetooth T15](../experiments/2026-11-02-gemini-bluetooth/README.md#t15-prepared-where-the-signal-goes-on-a-walk):
  where the signal goes on a walk, with the owner's phone as the control.
- [pstore T2](../experiments/2026-11-03-gemini-pstore-retention/README.md#t2-does-the-key-restart-keep-this-ram):
  whether the key restart keeps RAM.
- [Keys](../experiments/2026-11-03-gemini-pmic-keys/README.md#analysis): whether Esc reaches the
  console as a key.
- [Display](../experiments/2026-11-02-gemini-native-display/README.md#after-the-review-fixes):
  the lid on the current image, a bind behind a closed lid, and the battery run.
- [Wi-Fi baseline on a booted image](../experiments/2026-11-01-mt6797-wifi-booted-baseline/README.md):
  written, and the owner said "Not now".

### 4. Each subsystem's next step

Independent of each other, in no fixed order. Each record owns the detail.

| Subsystem | Next, from its record |
| --- | --- |
| [A72](../experiments/2026-11-01-mt6797-all-cores/README.md#follow-up) | CPU capacity, idle power, a longer soak, then loading at init, each its own owner decision |
| [GPU](../experiments/2026-11-02-mali-t880-first-job/README.md#follow-up) | A cap under real heat; VGPU and the LDOs off at idle; clocks above 520 MHz are a separate decision |
| [Display](hardware/display-panel.md) | Linux's own panel init; a compositor on Panfrost; the [review items](../experiments/2026-11-02-gemini-native-display/README.md#what-stands-before-upstream) |
| [Camera](../experiments/2026-11-04-gemini-camera-receiver/README.md#what-this-does-not-show) | An application; an SMI driver; M4U in place of the bypass; ruling out stray writes |
| [Audio](hardware/mt6351-accdet.md) | Headset classification and buttons; the earpiece; other rates |
| [Touch](../experiments/2026-11-02-gemini-touchscreen-module/README.md#follow-up) | Positions on screen, a panel power cycle, suspend |
| [Sensors](../experiments/2026-10-06-gemini-i2c1-sensors/README.md#limitations) | The IMU's interrupt, buffered capture, suspend |
| [Bluetooth](hardware/mt6797-bluetooth.md#open-questions) | Range first; then a voice bridge to ALSA; a public userspace for release |
| [GNSS](../experiments/2026-11-01-gemini-gnss-link/README.md) | Open sky, which decides whether a position is reachable on mainline |
| [Charging](../experiments/2026-11-02-gemini-kernel-charge-guard/README.md) | A real charge reaching the limit; charge flow after a resume |
| [microSD](../experiments/2026-11-05-gemini-microsd/README.md#follow-up) | Works on the station at UHS SDR104 with exFAT, hotplug and at boot; eMMC at HS400 (one boot; writes and repeat boots open); suspend |
| USB host and role switching | Right-port host works with modules loaded by hand (full and high speed, PIO). Left-port host failed its first test: the boost gave no VBUS and switching back to device needed a replug. DMA, loading at boot and detach handling open. [Hardware page](hardware/usb-c.md), [record](../experiments/2026-11-05-gemini-usb-c/README.md) |
| Modem | Feasibility only. A safe transport and regulatory boundary come first |

### 5. Upstream

Owner action throughout: real authorship, a truthful DCO and the choice of targets.

- [The series as it stands](RELEASE_READINESS.md#code-quality) can't be reviewed. The proposed
  cut is a release profile first, then deleting what's off, then about 60-80 patches by area,
  SoC foundation first and A72 last.
- Small topics already prepared: the [MT6797 infracfg reset](../experiments/2026-09-05-mt6797-infracfg-upstream-preparation/README.md),
  the [BQ25890 IRQ preflight](../experiments/2026-09-12-bq25890-irq-preflight/README.md), the
  [MT6397 RTC wake errors](../experiments/2026-09-08-mt6397-rtc-irq-fix/README.md) and the
  [TOPRGU restart](../experiments/2026-09-06-mt6797-toprgu-minimal-restart/UPSTREAM_READINESS.md).
  Check the kernel's current rules on assisted contributions first.
- [Review findings](RELEASE_READINESS.md#upstream-blockers-from-the-patch-review) to resolve
  in each topic.

## Phase B: usable Wi-Fi

The ordered path from the station's Wi-Fi to daily use by any owner is the
[daily-use plan](WIFI_DAILY_USE_PLAN.md). Phases 1 and 2 passed and phase 3 is part done. The
owner parked that testing on 2026-11-01, apart from the baseline above. What remains
is 2.4 GHz transmit, security modes beyond WPA2-PSK, rekey, the idle disconnect, power saving
and `ip link down`.

## Rules of the road

- One question per boot is not the default. A candidate carries a
  runner-driven, re-triggerable executor; a new kernel is for new code.
- New drivers start as `=m` and load by hand until proven. Boot-time protections stay
  built in. Batch changes that need a new image.
- Diagnostics live in named profiles, default off, and leave the manifest when
  their experiment is consumed. Profiles are retired, not accumulated.
- Every new patch has a human author who can certify it, or it is marked
  experiment-only. `check-repository` rejects new synthetic sign-offs.
- Every experiment directory has a README, and new records state a
  controlled status. The [index](../experiments/README.md) is generated and
  checked by `check-repository`.
- Before a boot, state its hypothesis, unique observation and decision
  branches. Do not repeat identical artifacts.

## Parked

DA9214 beyond the read-only contract. Receive-path firmware RAM sampling
(proposal 0085). Wi-Fi DMA and transmit aggregation. Loader and preloader replacement.

## Gates

<a id="a53-development-system-release-gate"></a>
- **A53 development-system release.** Ten attributable cold boots per the
  [cold-boot protocol](../experiments/2026-09-09-standard-kernel-package/A53_COLD_BOOT_PROTOCOL.md):
  CPU0–7, console and log capture, keyboard, authenticated USB, CPU8/9 offline.
  Not a daily-driver, storage-reliability or thermal claim. Not yet run.
<a id="upstream-delivery-gate"></a>
- **Upstream delivery.** Real author, truthful DCO, focused compile and schema
  checks, the right maintainer tree and binding review.
- **Device safety.** `boot2` only, verified live identity, full readback,
  clean shutdown, owner physical selection; see [safety](SAFETY.md).

## Milestones

The right-hand column is how far each has got, read from the matrix. It isn't an acceptance.

| Milestone | Acceptance outcome | Furthest along |
| --- | --- | --- |
| M0: lab | Tested recovery, exact provenance, enforced safe tooling, automated checks | In daily use |
| M1: boot | Ten attributable cold boots; RAM, topology, timers, interrupts, PSCI, watchdog checked; loader mutations documented | Cold boots not run |
| M2: headless system | Safe PMIC, RTC, restart, power-off; bounded storage; USB administration; Wi-Fi association and traffic; charger telemetry | Each shown on one unit |
| M3: input and ports | Keyboard incl. wake and LEDs; lid; microSD hotplug; both USB ports and roles | Keyboard, lid, LED module, microSD hotplug; no USB host |
| M4: local interaction | Native DRM, panel, backlight, repeated modesets, calibrated multitouch | Native console; touch uncalibrated; panel adopted from the loader |
| M5: power | Validated OPP transitions, thermal trips and cooling, charging protection, suspend and wake | Charge guard and armed trips only |
| M6: peripherals | GPU, audio, Bluetooth, GNSS, FM and sensors through upstream interfaces; explicit firmware boundaries | All local; FM has no result |
| M7: distribution | Released host support, standard artifacts, maintained loader path, distro packaging, tested updates | Not started |
| Full variant coverage | Cellular and cameras on equipped variants, or explicit feasibility and rights blockers | Front camera from modules; no modem |

Issue seeds #1–#30 on GitHub, untouched since July, were closed on 2026-10-05
in favour of this file; their links stay stable.

## Historical anchors

Older records link to sections of the pre-consolidation roadmap. Their content
is in the [historical roadmap](../experiments/2026-10-05-repository-consolidation/ROADMAP_2026-10-04.md)
under the same headings.
<a id="parallel-work-that-does-not-block-the-a72-sequence"></a>
<a id="parallel-delivery"></a>
<a id="owner-away-progress"></a>
<a id="after-wi-fi-remaining-driver-gaps"></a>
<a id="shared-dependencies"></a>
<a id="ordered-gaps"></a>
<a id="ordered-gates"></a>
<a id="0-repair-the-profile-series-invariant"></a>
<a id="2-implement-and-validate-an-isolated-profile"></a>
<a id="6-prove-one-bounded-writable-operation"></a>
<a id="7-bring-up-cpu8"></a>
<a id="8-validate-cpu9-and-the-complete-cluster"></a>
