# Experiment: 2026-10-03 overall project review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-03-project-review` |
| Status | `completed` (offline review; no build or device action) |
| Subsystem | Whole project: plan, patch layer, evidence, process |
| Device variant | Project Gemini (Gemian image identifies 4G UK 6M15BS/X600) |
| Date(s) | 2026-10-03 |
| Investigator(s) | Claude (owner-requested review) |
| Related | [Wi-Fi audit](../2026-10-03-mt6797-wifi-audit/README.md), [corrective review](../2026-09-05-project-corrective-review/README.md), [roadmap](../../docs/ROADMAP.md) |

## Question

Where does the project really stand after three months, what is solid versus
assumed, which turns were wrong or risky, and what order of work gets the most
working hardware soonest? The answer sets the
[current plan](../../docs/ROADMAP.md#current-plan-2026-10-03-review) in the
roadmap. This review read the repository at commit `7fad4cb` plus the open
issues and the project threads. It did not inspect the device, Buildbox,
private captures or retained firmware.

## Numbers that frame the review

| Measure | Value | Why it matters |
| --- | --- | --- |
| Experiments since 2026-07-11 | 519 | About six per day; most are one boot or one offline checkpoint each |
| Experiments on A72, DA921x, DVFSP, I2C6 | 213 | Result: isolated-profile evidence only, nothing in the default profile |
| Experiments on Wi-Fi and CONSYS | 104 | Result: firmware runs, WMT link alive, zero frames received |
| Patches under `patches/v7.1.3` | 547 | 83,000 added lines against the pinned kernel |
| Patches whose filename names a diagnostic, ledger, observer, A72, DA921x, pstore or similar | about 260 of the 505 in the accepted A53 foundation series | Half of every booted kernel is instrumentation |
| Patches with a synthetic `From:` author (`example.invalid`, `noreply@`) | 412 of 547 | Not submittable upstream as they stand |
| Manifest profiles | 270 | One per question asked of the device |
| Boots of the default `full` profile | 0 found | The product configuration has never been tested |
| Upstream series sent | 0 | One prepared fix (clock ID allocation) was pre-empted by a public patch |
| `docs/ROADMAP.md` | 1,234 lines; the Wi-Fi item alone spans about 500 | The plan is buried in chronology |
| Open issues last updated before 2026-09 | 30 of 31 | The tracker does not reflect state |

## What is solid

These have identity-gated runtime evidence, usually repeated across many boots.

- **The lab loop.** Guarded `boot2` installation with full readback, owner
  physical selection, authenticated USB Ethernet collection, sealed-log
  preservation, A53 regression and changed-boot Gemian return. Dozens of
  cycles, no brick, no lost known-good path. This is the project's main asset
  and the reason risky Wi-Fi work has been safe.
- **The A53 development system.** Linux 7.1.3 boots from retained LK with
  console, AW9523 keyboard, USB gadget Ethernet with key-authenticated SSH,
  native TOPRGU restart, watchdog, all eight A53 cores, PMIC wrapper with
  MT6351 core and selected regulators, and bounded eMMC access.
- **Wi-Fi up to firmware-ready.** CONN power-on, delayed chip ID `0x0279`,
  CONMCU reset release, EMI region policy and copy, HIF section download,
  START, firmware-ready WCIR, capability query, mac80211 wiphy, station
  interface and completed passive scans on 2.4 GHz and channel 40.
- **WMT over BTIF/STP is alive.** In three boots on 2026-10-03 mainline got a
  matching default-query event, completed mandatory set-options and the
  full-STP switch with peer credit and host ACK, and read the chip register
  `0x80000008` as `0x0279`. No earlier mainline boot had spoken to WMT.

## What is inferred or assumed

- **Why no frame arrives.** The Wi-Fi audit's primary finding, that the vendor
  WMT common power-on (ROM patch download, RF calibration with both PA LDOs,
  coexistence settings) has never run on mainline and sits upstream of every
  receive gate sampled, is an inference from source order plus the symptom.
  It is the best hypothesis available and the next boots test it. It is not
  yet proven.
- **ROM patch applicability.** The two retained ROM files match the files
  Gemian installs, and Gemian's log selects chip `0x0279`, HW/ROM `0x8a00`,
  revision E1. Mainline has measured only the chip register; the HW and ROM
  reads are still unmeasured.
- **The default configuration works.** Nothing booted with the `full`
  profile. Every runtime claim rests on a 505-patch foundation series that
  carries the diagnostics. Whether a clean board description boots is unknown.
- **Clock and regulator state.** Every booted profile passes
  `clk_ignore_unused` and `regulator_ignore_unused`, so the hardware runs in
  whatever state LK left it. Native display, GPU and power management all
  need those crutches removed, and nothing has yet measured what breaks when
  they go.
- **Board facts carried from vendor hints.** Panel identity (NT36672 versus
  SSD2092), fuel gauge location (MT6351 internal) and several GPIO roles come
  from vendor source, bsg100 or owner-held documents, not from this unit.

## What went wrong or is risky

1. **The A72 and DA9214 workstream consumed the most effort for the least
   usability.** 213 experiments and roughly 190 patches established isolated
   dual-A72 execution and a read-only external regulator contract. None of it
   is in the default profile and none of it is needed for a usable device:
   eight A53 cores run the development system fine. Default-profile A72
   support, cpufreq and thermal protection remain open and are blocked on
   measurement contracts nobody can currently supply. The roadmap already
   released that slot; the plan now parks it explicitly.
2. **One question per boot has become the method.** Each step is a new
   format-patch with a one-shot `mediatek,one-shot-*` property (11 distinct
   selectors so far), a new profile, a Buildbox build, candidate construction,
   guarded deployment, owner selection and recovery. The seven receive-path
   sampling boots in early October each moved one firmware RAM word further
   back and each answered "prerequisite present, zero frames". The cost of a
   boot, not the difficulty of the kernel work, now sets the project's pace.
3. **The roadmap no longer states a plan.** The Wi-Fi item is a 500-line
   chronology of consumed boots, duplicated in the support matrix row. The
   documents violate their own rule that experiments own chronology and the
   roadmap owns order. A new contributor or session cannot find the next step
   without reading everything.
4. **Upstream is not happening.** The project's first principle is "upstream
   is the product", but 412 of 547 patches carry synthetic authors, 37 carry
   synthetic sign-offs, no series has been sent in three months, and a public
   MT6797 patch pre-empted the one fix that was ready. Sitting on patches
   loses them. The remedy is a real human author/reviewer and small topics,
   and a check of the kernel's current rules for disclosing assisted
   contributions before sending.
5. **Diagnostics live in generic kernel code.** 39 pstore, 16 kobject and
   several netlink/uevent patches instrument core subsystems to observe the
   board. They will never go upstream and they are in every booted kernel.
   They are not wrong as a bring-up tactic, but they must stay out of the
   product profile.
6. **The battery is a lab risk.** Mainline does not charge. The 2026-09-12
   inspection saw 31 % and "Not charging". Every boot drains the pack and
   only Gemian time restores it. Charger telemetry is both a usability item
   and lab insurance, which raises its priority.
7. **The tracker is stale.** All issues except #34 were last touched on
   2026-07-11. Issue #34 is still labelled P0 although the audit downgraded it
   to a watch item. Either the issues reflect state or they should be closed
   in favour of the roadmap.
8. **Process prose outlived the process.** Worktree conventions, three worker
   slots, `codex/` branches and agent-routing pilots remain in the roadmap
   although AGENTS.md declares them historical.

## Recommended order

The ordering rule: first finish the one chain that unlocks a whole family of
hardware (CONSYS common init unlocks Wi-Fi, Bluetooth, GNSS and FM), then
protect the lab (charging), then the two usability blockers (power keys and
RTC, native display), then reuse. Steps marked **(local)** need Julien's
machine because Buildbox and the device are not reachable from cloud sessions.

### Phase A: first received frame

1. **Measured HW/ROM reads** (offline, then one boot **(local)**). Extend the
   proven chip read to `0x80000000` and `0x80000004`, check each reply
   independently, and refuse an unrecognised tuple. Decision: the retained
   ROM pair applies, or it does not.
2. **Common-init executor** (offline). Implement ordered ROM patch download
   (`1_1` before `1_0`), WMT reset, the selected DLM and MCU-clock writes,
   both PA LDOs on (VCN33-BT and VCN33-Wi-Fi), the RF calibration command and
   its event, PA LDOs back, coexistence settings. Crystal trim and co-clock
   stay out, as the startup follow-up found. Build it as one re-triggerable,
   stage-by-stage executor driven from userspace over the existing USB SSH,
   with the finite budgets enforced by the runner script, so one boot can run
   stage N, inspect, and run stage N+1. Stop adding one-shot selectors.
3. **One boot** **(local)**: common init, then the existing START and one
   channel-40 passive scan. Decision: nonzero firmware management count or a
   BSS, or still zero. If zero, the same boot should be able to try the
   remaining vendor differences one at a time, starting with the active scan
   Gemian actually performs.
4. **Bluetooth HCI reset as the independent check** (offline design now, same
   boot if the executor allows). After common init, one HCI reset and version
   read over the STP BT channel proves the common init without depending on
   Wi-Fi RF. It also starts the Bluetooth path for free.

### Phase B: usable Wi-Fi

5. Association through mac80211 host MLME, bounded traffic over PIO, then
   packet DMA and interrupts, then unbind and restart without a fault (which
   also closes #34). "Usable" means WPA2 association, DHCP, ping and an SSH
   session over Wi-Fi held for ten minutes, on the default profile.
6. Fold the 44 `series-a53-wifi-*` profiles and their one-shot proposals into
   one CONSYS/WMT owner, one WLAN driver and one profile. Delete the retired
   diagnostics from the series rather than carrying them.

### Phase C: offline work that needs no boot (start now, in parallel)

7. **Charger board description.** Disabled BQ25896 node on I2C0 `0x6b` with
   conservative limits from the existing mainline design, IRQ line left to
   the first read-only inspection, watchdog handling decided.
8. **PMIC basics.** Finish the MT6351 keys long-press policy, the RTC reload
   question and a reviewed power-off path, as the After Wi-Fi section lists.
9. **Two upstream submissions with a real author.** Julien reviews, takes
   authorship responsibility and signs off the MT6797 infracfg reset topic and
   one of the two small fixes (BQ25890 IRQ preflight or MT6397 RTC wake
   errors). Check the kernel's current process documentation on assisted
   contributions first. The point is to start the review clock and learn the
   maintainers' expectations before the large CONSYS work arrives.
10. **Consolidate the documents.** Cut the roadmap to the plan and the gates;
    move the Wi-Fi chronology into the Wi-Fi hardware record or the audit
    experiment; cut the support-matrix Wi-Fi row to its current claim; drop
    the historical process sections; close or retitle the stale issues in one
    pass. This is a documentation-only change and needs no build.

### Phase D: device sessions after the first frame

11. **Charger telemetry boot** **(local)**: probe only, read voltage, current
    and status, leave charging in loader state. Then a reviewed charging
    enable. This protects every later session.
12. **A clean-profile boot** **(local)**: the `full` profile, or a new
    `gemini-dev` profile with the board description and no diagnostics, once,
    to learn whether the product configuration boots at all. This is
    decision-changing because every later upstream claim depends on it.
13. **Power keys, RTC, power-off** **(local)**: one combined packet.
14. **Display** in the order the After Wi-Fi section already gives: read-only
    PWM clock and panel/bias identity trace, then backlight, then DSI/panel,
    with touch after the panel.
15. **Bluetooth, then GNSS**, reusing the common init from Phase A.
16. Lid, microSD, USB roles, audio, sensors, GPU as the After Wi-Fi section
    orders them. Cellular and cameras stay research only.

### Parked

- A72 default integration, cpufreq and thermal protection: no new boots until
  a measurement contract exists and the items above are done. Keep the
  evidence; stop extending the patches.
- DA9214 external regulator beyond the read-only contract: it serves the A72
  rail and waits with it.
- Receive-path firmware RAM sampling (proposal 0085 and successors): only if
  Phase A step 3 still shows zero frames after the vendor differences are
  exhausted.
- Replacing LK or the preloader: unchanged, a separate project.

## Process changes that follow

- One device question per boot is no longer acceptable as the default. A
  candidate should carry a runner-driven, re-triggerable executor; a new
  kernel is for new code, not for the next value of a diagnostic address.
- Diagnostic patches stay in named profiles and leave the series when their
  experiment is consumed. The accepted foundation series should shrink.
- Every new patch has a human author who can certify it, or it is marked
  experiment-only and never a submission candidate.
- The roadmap states the plan in under 200 lines. Chronology goes to
  experiments, facts to `docs/hardware/`, claims to the support matrix.

## Limitations

This is a repository and thread review. It did not run a build, touch the
device, inspect private captures or verify the vendor source quotations in
the Wi-Fi audit beyond their consistency with the repository's own records.
Counts come from filenames and metadata and are approximate where stated.
The primary Wi-Fi hypothesis remains an inference until Phase A step 3 runs.
