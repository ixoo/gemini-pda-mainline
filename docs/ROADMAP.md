# Roadmap

Deliver full Gemini PDA support through maintained upstream Linux interfaces,
with ordinary distribution updates and an independently bootable recovery path.
A capability is complete when its host support is in a released upstream kernel
and passes a named regression protocol. A build is not hardware support, and an
experiment result is not released support.

This file states the order of work and nothing else. The
[support matrix](HARDWARE_SUPPORT.md) owns runtime claims, the
[experiments index](../experiments/README.md) owns chronology and exact
candidates, and [`docs/hardware/`](hardware/README.md) owns durable facts. The
reviews that set this order are the
[2026-10-03 project review](../experiments/2026-10-03-project-review/README.md),
its [2026-10-04 follow-up](../experiments/2026-10-03-project-review/NEXT_STEPS_2026-10-04.md)
and the [2026-10-05 consolidation](../experiments/2026-10-05-repository-consolidation/README.md).
The roadmap as it stood before the consolidation is kept
[verbatim](../experiments/2026-10-05-repository-consolidation/ROADMAP_2026-10-04.md).
Keep this file under 200 lines; move anything else to an experiment record.

## Where we stand (2026-10-05)

- **Solid.** The guarded `boot2` lab loop (install, full readback, owner
  selection, USB SSH collection, sealed logs, Gemian return). The A53
  development system on Linux 7.1.3: console, keyboard, USB gadget SSH,
  restart, watchdog, CPU0–7, PMIC wrapper, bounded eMMC. Wi-Fi to
  firmware-ready, and WMT alive over BTIF/STP with the chip/HW/ROM tuple
  `0279/8a00/8a00` [measured](../experiments/2026-10-03-mt6797-wmt-versions/README.md).
- **Open.** No Wi-Fi frame received. No charging, power key, RTC or power-off.
  The `full` profile has never booted. No upstream submission. A72 and thermal
  protection are parked.
- **Device.** The last session returned to changed-boot Gemian. Nothing is
  installed to `boot2` awaiting selection. Stock Gemian requests 4.416 V on the
  charger; keep its charging attended.

## Next device boots, in order

<a id="current-plan-2026-10-03-review"></a>
Each boot is a reviewed experiment with its own validated candidate, finite
budgets and stop conditions under the [safety rules](SAFETY.md). Steps marked
**(local)** need the owner's machine and the device.

1. **C1: PMIC, RTC, lid and charger read (local).** Profile
   `mt6797-a53-c1-compile` from the
   [C1 preparation](../experiments/2026-10-04-gemini-c1-preparation/README.md).
   Ten-register PMIC observer ordered before the key child probes; keys child
   with explicit `mediatek,long-press-mode` and `power-off-time-sec`; lid node.
   One short key press, one lid close/open, `rtcwake` 10 s, PSCI power-off with
   the cable detached. C2a rides along: a userspace read-only REG00–REG14
   charger dump with no charger node bound, REG0C read once. Decides the PMIC
   interrupt path, RTC, the power-off baseline and the charger `VREG` value.
2. **C3: Bluetooth HCI Reset on the negotiated STP session (local).** Profile
   `mt6797-a53-stp-task-routing-compile`, the consolidated 0101–0106 chain with
   the AFE resource present
   ([transport record](../experiments/2026-10-04-mt6797-stp-task-routing/README.md)).
   Controls first: repeat the version baseline and the validated full-mode WMT
   query/negotiation; stop on any regression. Then VCN33-BT on, BT function-on,
   HCI Reset, Read Local Version, Read BD_ADDR. Decides Bluetooth H1 and proves
   common init without depending on Wi-Fi RF
   ([Bluetooth record](../experiments/2026-10-04-gemini-bluetooth-re/README.md)).
3. **Phase A: first received Wi-Fi frame (local).** The common-init executor
   (ROM patch download, WMT reset, DLM and MCU clock writes, both PA LDOs, RF
   calibration, coexistence), re-triggerable from userspace over USB SSH, then
   the existing START and one channel-40 passive scan. Decision: nonzero
   firmware management count or a BSS. If zero, try the remaining vendor
   differences in the same boot. Hypothesis and sequence:
   [Wi-Fi audit](../experiments/2026-10-03-mt6797-wifi-audit/README.md).
4. **Clean-profile boot (local).** `full`, or a new board-only profile with no
   diagnostics, once. Decides whether the product configuration boots at all;
   every later upstream claim depends on it.
5. **C2b: charge policy (local).** A named profile binding `bq25890` only
   after the reviewed sequence programs and verifies 4.2 V and 500 mA before
   charging starts. Then the gauge/ADC comparison boot.
6. **Display adoption, then the rest.** simplefb with the MM domain so
   `clk_ignore_unused` can go, backlight, the I2C1 boot (sensors and panel
   bias), microSD and USB host, headphone-first audio, panel, GPU, GNSS after
   proven common init. Cellular and cameras stay feasibility work. The
   per-block detail, shared dependencies and grouped device tests are in
   [After Wi-Fi gaps](../experiments/2026-10-03-project-review/AFTER_WIFI_GAPS.md).

## Offline work now, in parallel

1. Build and validate the C1 candidate on Buildbox. Nothing else gates it.
2. Wire the smallest task-0 Bluetooth path on the drafted STP transport: one
   binding in the existing IRQ owner, a single-event buffer, BT on/off,
   VCN33-BT, HCI Reset, version and BD_ADDR. No `hci_dev`, retransmission
   timers or reset epochs until H1 is answered.
3. The common-init executor, with the AFE stage owned unconditionally; see the
   [common-init review](../experiments/2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md).
4. Charger driver review: every probe and notifier write in the pinned
   `bq25890` driver, and how conservative limits are programmed and verified
   ([charging record](../experiments/2026-10-04-gemini-charging-re/README.md)).
   Then the C2b profile.
5. The MT6351 regulator constraint set (`always-on`, `boot-on`, VCORE off
   limits), keeping `regulator_ignore_unused` until a reviewed boot drops it.
6. **Upstream, owner action.** Pick two small topics, take authorship and sign
   off: the [MT6797 infracfg reset](../experiments/2026-09-05-mt6797-infracfg-upstream-preparation/README.md)
   topic and one fix, either the
   [BQ25890 IRQ preflight](../experiments/2026-09-12-bq25890-irq-preflight/README.md)
   or the [MT6397 RTC wake errors](../experiments/2026-09-08-mt6397-rtc-irq-fix/README.md).
   Check the kernel's current rules on assisted contributions first. The
   profiles `mt6797-infracfg-current-mainline`, `bq25890-irq-compile`,
   `mt6397-rtc-wake` and `mtk-sd-pinctrl-compile` stay for this.
7. The remaining [Gemian session A](../experiments/2026-10-04-gemian-session-a/README.md)
   reads when convenient. They gate none of the boots above.

## Phase B: usable Wi-Fi

Association through mac80211, bounded PIO traffic, packet DMA and interrupts,
then unbind and restart without a fault. Usable means WPA2 association, DHCP,
ping and a ten-minute SSH session on a clean profile. Then one CONSYS/WMT
owner, one WLAN driver and one profile; retired diagnostics leave the series.

## Rules of the road

- One question per boot is not the default. A candidate carries a
  runner-driven, re-triggerable executor; a new kernel is for new code.
- Diagnostics live in named profiles, default off, and leave the manifest when
  their experiment is consumed. Profiles are retired, not accumulated; the
  [consolidation record](../experiments/2026-10-05-repository-consolidation/README.md)
  lists the 12 profiles to keep and the 261 proposed for retirement.
- Every new patch has a human author who can certify it, or it is marked
  experiment-only. `check-repository` rejects new synthetic sign-offs.
- Every experiment directory has a README, and new records state a
  controlled status. The [index](../experiments/README.md) is generated and
  checked by `check-repository`.
- Before a boot, state its hypothesis, unique observation and decision
  branches. Do not repeat identical artifacts.

## Parked

A72 default integration, cpufreq and thermal protection: evidence retained,
patches not extended; the A72 gate history is in the
[historical roadmap](../experiments/2026-10-05-repository-consolidation/ROADMAP_2026-10-04.md#ordered-gates).
DA9214 beyond the read-only contract. Receive-path firmware RAM sampling
(proposal 0085). Loader and preloader replacement. A53 keyboard retests ahead
of Wi-Fi.

## Gates

<a id="a53-development-system-release-gate"></a>
- **A53 development-system release.** Ten attributable cold boots per the
  [cold-boot protocol](../experiments/2026-09-09-standard-kernel-package/A53_COLD_BOOT_PROTOCOL.md):
  CPU0–7, console and log capture, keyboard, authenticated USB, CPU8/9 offline.
  Not a daily-driver, storage-reliability or thermal claim.
<a id="upstream-delivery-gate"></a>
- **Upstream delivery.** Real author, truthful DCO, focused compile and schema
  checks, the right maintainer tree and binding review. The
  [TOPRGU restart topic](../experiments/2026-09-06-mt6797-toprgu-minimal-restart/UPSTREAM_READINESS.md)
  waits on its readiness assessment.
- **Device safety.** `boot2` only, verified live identity, full readback,
  clean shutdown, owner physical selection; see [safety](SAFETY.md).

## Milestones

| Milestone | Acceptance outcome |
| --- | --- |
| M0: lab | Tested recovery, exact provenance, enforced safe tooling, automated checks |
| M1: boot | Ten attributable cold boots; RAM, topology, timers, interrupts, PSCI, watchdog checked; loader mutations documented |
| M2: headless system | Safe PMIC, RTC, restart, power-off; bounded storage; USB administration; Wi-Fi association and traffic; charger telemetry |
| M3: input and ports | Keyboard incl. wake and LEDs; lid; microSD hotplug; both USB ports and roles |
| M4: local interaction | Native DRM, panel, backlight, repeated modesets, calibrated multitouch |
| M5: power | Validated OPP transitions, thermal trips and cooling, charging protection, suspend and wake |
| M6: peripherals | GPU, audio, Bluetooth, GNSS, FM and sensors through upstream interfaces; explicit firmware boundaries |
| M7: distribution | Released host support, standard artifacts, maintained loader path, distro packaging, tested updates |
| Full variant coverage | Cellular and cameras on equipped variants, or explicit feasibility and rights blockers |

Issue seeds #1–#30 on GitHub, untouched since July, were closed on 2026-10-05
in favour of this file; their links stay stable. #34 is a P2 watch item until
Phase B.

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
