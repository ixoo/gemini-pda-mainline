# Roadmap

## Goal and completion

Deliver full Gemini PDA support through maintained upstream Linux interfaces,
with ordinary distribution updates and an independently bootable recovery path.
Full coverage includes CPU/power, storage, input, both USB ports, display/touch,
GPU, audio, connectivity, sensors, cameras and cellular on equipped variants.
A capability is complete when its required host support is in a released
upstream kernel and passes a named regression protocol. An explicit firmware
boundary or unresolved feasibility blocker must remain visible; it is not a
completed feature.

Useful releases are incremental. Cellular, cameras and replacement of early
firmware do not delay delivery of already supportable components, but their
feasibility is investigated early rather than hidden indefinitely as stretch
work. Replacing retained preloader/secure firmware remains a separate project.

The [support matrix](HARDWARE_SUPPORT.md) owns present runtime claims.
[Experiments](../experiments/README.md) own exact candidates, chronology and
rejected branches. The pre-consolidation roadmap is retained through an
[immutable history reference](../experiments/2026-09-05-project-corrective-review/results/roadmap-history.json).
Historical instructions never select a new boot.

## Current plan (2026-10-03 review)

The [overall project review](../experiments/2026-10-03-project-review/README.md)
owns the reasoning behind this order. Where it differs from older text below,
this section wins. Steps marked **(local)** need Julien's machine, because
Buildbox and the device are not reachable from cloud sessions.

### Review of work landed after the plan rewrite (2026-10-04)

Source and commit-level review of `1fc7fc0..fcca630` against this plan and the
`2026-10-04-gemini-*-re` records. No build, boot or device access was part of
this review; the texts below that it corrected are marked in place.

**Done (draft, compile-checked, no hardware result).**
The [follow-up review](../experiments/2026-10-03-project-review/NEXT_STEPS_2026-10-04.md)
recorded five corrections to this plan. The CONSYS AFE stage was joined into
the [common-init review](../experiments/2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md)
and drafted as patches 0101–0102 ([AFE preparation](../experiments/2026-10-04-mt6797-afe-preparation/README.md)):
eleven writes after the MCU ACR update and before reset release, behind an
optional `afe` resource that no board DT carries yet. The shared STP transport
was drafted as 0103–0106: task-aware framing ([0103](../experiments/2026-10-04-mt6797-stp-task-framing/README.md)),
one shared sequence/ACK window ([0104](../experiments/2026-10-04-mt6797-stp-link-state/README.md)),
then an ACK-credit correction and task routing before credit commitment
([0105–0106](../experiments/2026-10-04-mt6797-stp-task-routing/README.md)).
Host fixtures and Buildbox compilation pass for 0101–0106; the
[task-routing receipt](../experiments/2026-10-04-mt6797-stp-task-routing/results/validation.json)
records the validated build of input `fcca630d`. The installed version-read
candidate is now consumed: [one checked tuple](../experiments/2026-10-03-mt6797-wmt-versions/results/runtime-1.json)
passed with sealed evidence, A53 regression and changed-boot Gemian recovery.

**What changed or was invalidated.**

- *Charger first boot.* `linux,read-back-settings` makes the upstream driver
  skip the DT limits, and `linux,skip-reset` makes probe enable charging. The
  planned "4.2 V / 500 mA" node would therefore not enforce either limit
  (follow-up review, correction 1). Step 2 and boot C2 below are corrected.
- *Bluetooth before common init* is a hypothesis, not a finding: Bluetooth
  H1 has medium confidence. The AFE join adds a reason for caution: five of the eleven AFE writes are named `BT_RX`/`BT_TX`
  settings, written by the vendor before every MCU release. HCI Reset is ROM
  command handling and should not need them, but the first Bluetooth boot
  should carry the AFE stage so it matches the vendor power-on order.
- *GNSS AFE item is done offline.* The AFE stage is common power-on, not a
  GNSS step; GPS H2 is now owned by the common-init owner.
- *Gemian session A is not uniformly passive.* Logs, live DT and sysfs come
  first; PMIC, I2C and MMIO register reads need a reviewed access path each
  (follow-up review, correction 4). The AFE window read (A11) is only safe
  while CONSYS is powered, so take it with Wi-Fi on or drop it.
- *Power-off.* Boot C1 first measures the existing PSCI power-off with the
  cable detached; `mt6351-pwrc` is added only if that fails (PMIC H2).

**Risky or wrong in the new work.**

1. *Transport generality is running ahead of evidence.* Four transport
   patches exist and none has run on hardware; the READMEs name retransmission
   storage, timers, reset epochs and client lifetime as next. None of those
   is needed to decide Bluetooth H1. Stop generalizing at what boot C3 needs.
2. *0106 changes the hardware-proven full-mode WMT path.* Negotiation and
   its full-mode query now use the new routing and link code. The checked
   pre-negotiation version-read path bypasses that code; its installed
   candidate still awaits measurement. Retain the version read as a power,
   BTIF and AFE baseline, then repeat the previously validated full-mode
   WMT query/negotiation as the router control before Bluetooth. Stop on a
   regression and compare with the corresponding prior candidate before
   more transport work.
3. *0105 corrected part of 0104.* The [consolidation](../experiments/2026-10-04-mt6797-stp-task-routing/README.md#consolidation-after-validation)
   now folds both into corrected 0104, removing the known-wrong intermediate.
   Replay preserves the validated source. Out-of-window ACK behavior remains
   source-derived, not observed.
4. *Delivery before credit differs from the vendor order.* A refused packet
   is left for firmware retransmission, which has never been observed. Keep
   C3 to single command/response exchanges so no refusal can occur.
5. *Profile growth.* One draft added four chained compile-only profiles, each
   a full 580-line series copy (113 series files at review). After Buildbox
   validation, the AFE, task and link intermediates were retired; only
   `mt6797-a53-stp-task-routing-compile` remains from that chain.
6. *AFE is gated on the `wmt_query` diagnostic property.* Acceptable for the
   draft; the common-init executor must own the AFE stage unconditionally
   rather than through another DT-selected mode.
7. *The Wi-Fi-independent offline items have not started.* Nothing landed for
   the PMIC keys policy, the charger correction or the lid node, which gate
   boot C1, the cheapest boot that does not depend on Wi-Fi.

**Adjusted next steps (offline, in order).**

1. Complete: Buildbox validation of original 0105–0106, source-identical
   consolidation of 0104+0105, and retirement of intermediate compile profiles.
   The historical build receipt retains its original input identity.
2. Prepare boot C1 using the [integration audit](../experiments/2026-10-04-gemini-c1-preparation/README.md):
   key error/duration fixes pass host, Buildbox and focused binding checks;
   corrected RTC and gpio-keys now also pass host and Buildbox/package checks
   in the consolidated C1 compile profile. The MFD IRQ lifetime, mask,
   acknowledgement and wake-recovery corrections now replay and pass focused
   host tests and Buildbox/package checks on that foundation. The
   [observation review](../experiments/2026-10-04-gemini-c1-preparation/OBSERVATION_REVIEW.md)
   found unbounded RTC counter retries and unreported IRQ transport
   failures. The bounded-read and IRQ-diagnostic successors now pass host
   regression and C1 Buildbox/package checks. The
   [alarm-tool review](../experiments/2026-10-04-gemini-c1-preparation/ALARM_TOOL_REVIEW.md)
   found a missing standard alarm-disable callback; its successor passes host
   regression and C1 Buildbox/package checks. Next offline: select a finite alarm
   tool with checked cleanup, finish inherited-alarm admission and callback
   effect budgeting, and resolve per-register semantics
   for the ten-register PMIC observer before creating
   a candidate. The key node still needs an explicit long-press policy from an
   attributable live `TOP_RST_MISC` observation; the lid node remains disabled.
   The installed identity candidate is consumed. Complete the reviewed Gemian
   baseline before C1 short-key/lid/awake-alarm and PSCI power-off tests. C2a's read-only
   REG00–REG14 charger dump needs its separate access review, including REG0C
   fault-history consumption, with no charger node bound. No device operation is scheduled while the owner is unavailable.
3. Wire the smallest Bluetooth path for C3: one task-0 binding in the existing
   IRQ owner with a single-event buffer, BT function-on/off and VCN33-BT over
   the existing WMT client, HCI Reset, Read Local Version and Read BD_ADDR.
   No `hci_dev`, retransmission timers or reset epochs until H1 is answered.
4. Continue the common-init executor (Phase A step 2) with the AFE stage owned
   unconditionally.
5. Charger driver review: every probe and notifier write in the pinned
   `bq25890` driver and how conservative limits get programmed and verified
   before charging can start; then the C2b profile.

**Adjusted device order.** 0) Complete: the installed version-read candidate
measured `0279/8a00/8a00` and returned to changed-boot Gemian.
1) Gemian session A, logs and live DT first, then reviewed register reads.
The [charger log/DT subset](../experiments/2026-10-04-gemian-session-a/README.md)
is collected; session A is incomplete. The
[matched-boot setter audit](../experiments/2026-10-04-gemian-session-a/CHARGER_CV_BINARY.md)
shows computed-only logs followed by fixed `0x24` write requests with discarded
results. The [REG06 access review](../experiments/2026-10-04-gemian-session-a/REG06_ACCESS_REVIEW.md)
rejects shared sysfs/dump paths and finds I2C-dev disabled. The
[transport review](../experiments/2026-10-04-gemian-session-a/REG06_TRANSPORT_REVIEW.md)
finds unchecked FIFO completion and controller/DMA failure resets. The
[adapter review](../experiments/2026-10-04-gemian-session-a/REG06_ADAPTER_REVIEW.md)
confirms static I2C0 ownership and SCP effects. Next implement a default-off
observation of one existing policy REG06 read with same-operation completion/count
evidence, adding no charger request; byte/status alone is insufficient.
2) Boot C1 with C2a riding on it. 3) Boot C3 (Bluetooth, AFE resource
present, version baseline followed by full-mode WMT query/negotiation
control). 4) Phase A step 3 Wi-Fi common-init boot when the executor exists. 5) Boot C2b, charge policy. Then C4 onward as
listed below.

**Phase A: first received Wi-Fi frame.**

1. Measured HW/ROM register reads with independent reply checks, then one
   boot **(local)** to settle ROM-pair applicability.
2. A re-triggerable common-init executor driven from userspace over USB SSH:
   ordered ROM patch download, WMT reset, selected DLM/MCU-clock writes, both
   PA LDOs on, RF calibration, PA LDOs back, coexistence. No crystal trim or
   co-clock. No new one-shot selectors.
3. One boot **(local)**: common init, existing START, one channel-40 passive
   scan. Decision: nonzero firmware management count or BSS, or still zero;
   if zero, try the remaining vendor differences in the same boot.
4. One HCI reset and version read over the STP Bluetooth channel as the
   Wi-Fi-independent proof of common init.

**Phase B: usable Wi-Fi.** Association through mac80211, PIO traffic, packet
DMA and interrupts, unbind/restart without a fault (closes #34). Usable means
WPA2 association, DHCP, ping and a ten-minute SSH session on the default
profile. Then fold the `series-a53-wifi-*` profiles into one owner, one
driver and one profile, and delete retired diagnostics from the series.

**Phase C: offline now, in parallel.** The 2026-10-04 reverse-engineering
records settled the open questions from source; the
[After Wi-Fi](#after-wi-fi-remaining-driver-gaps) section now lists the
concrete patches per block. Start with its steps 1, 2 and 6: the MT6351 keys
node with an explicit long-press policy, the regulator constraint set, the
charger driver review (the DT limits are not enforced in read-back mode; see
the review above), and the smallest task-0 Bluetooth path on the drafted STP
transport. The CONSYS AFE stage (GPS H2) is drafted as 0101–0102; the
`mt6351-pwrc` power-off cell waits for the PSCI baseline from boot C1. Two
upstream submissions with a real author and sign-off (infracfg reset plus one
small fix), after checking the kernel's current rules on assisted
contributions; cut this roadmap to the plan and move chronology to
experiments; close or retitle the stale issues.

**Phase D: device sessions.** Not all of these wait for the first frame.
The [After Wi-Fi](#after-wi-fi-remaining-driver-gaps) section groups every
device test the records ask for into one read-only Gemian session (its first
item is the charger `VREG` safety check), the attended actions inside it, and
an ordered list of mainline boots **(local)**. Boots 1 to 3 (PMIC, charging and
lid packet; charger probe; Bluetooth HCI reset on the already negotiated STP
session) need nothing from the Wi-Fi order and can be scheduled now; one
clean-profile boot **(local)** with no diagnostics still belongs early, to
learn whether the product configuration boots; display adoption, I2C1,
microSD/USB, audio, panel and GPU follow in that section's order; GNSS waits
for proven common init.

**Parked.** A72 default integration, cpufreq and thermal protection; DA9214
beyond the read-only contract; receive-path firmware RAM sampling (proposal
0085); loader replacement. Keep the evidence, stop extending the patches.

## A72 and thermal decision (2026-09-04, historical)

Isolated dual-A72 execution, topology, CPU9 down/restore and one integrated
frequency/thermal/bounded-load result are established. They do not establish
cross-boot thermal repeatability, protection, unrestricted hotplug, suspend or
default-profile support. Frequency observation is no longer the unresolved
first-read gate.

The [corrected V4 thermal regression](../experiments/2026-09-04-mt6797-thermal-snapshot/results/v4-runtime-pass.txt)
passed its bounded no-workload observation contract. That session's snapshot
budget is consumed; no additional read, workload or identical repeat is selected.
The pass establishes the corrected observation path only. Earlier integrated
thermal comparison rejections remain unchanged.

Physical-versus-conversion-history causality remains blocked on an independent
measurement or a supported acquisition-timing contract. The existing source and
timing audit supplies neither; another output-only boot cannot resolve it.
Reopen that question only with a reviewed discriminating contract. Release this
physical investigation slot and advance the ready upstream-preparation and A53
serviceability work below; offline power/thermal ownership work may continue.
The experiment owns exact candidate identities, chronology and any future
admission. A newer build or this roadmap cannot authorize a repeat.

Do not expand load, relax limits or add samples merely to turn the old comparison
into a pass. CPU/RAM/frequency correctness, controlled thermal repeatability and
actual thermal protection have separate acceptance protocols. The
[arithmetic audit](../experiments/2026-09-04-mt6797-thermal-snapshot/V4_CONVERSION_AUDIT.md)
and [passive-observation decision](../experiments/2026-09-04-mt6797-thermal-snapshot/PASSIVE_DISCRIMINATOR_DECISION.md)
explain why the V4 correction does not resolve the larger transient.

## Immediate corrective gate

Before new work relies on shared infrastructure:

1. enforce Buildbox-only automatic selection and immutable validated packages;
2. use block-device identities for mounted/root/holder refusals in the active
   installer, with deployment refusal fixtures and exact observation-shell tests;
3. run the common repository gate and applicable Linux provenance fixtures;
4. preserve the active kernel/profile/candidate inputs while correcting tooling;
5. block submission of synthetic certifications and inventory their historical
   debt without rewriting evidence or inventing authorship.

The [corrective-review record](../experiments/2026-09-05-project-corrective-review/README.md)
records actual implementation and validation. A newly added guard is not proof
that an old installer has adopted it. Historical installers remain evidence,
not the starting point for unreviewed deployments.

<a id="parallel-work-that-does-not-block-the-a72-sequence"></a>
## Parallel delivery

Prioritize upstream preparation, A53 serviceability and Wi-Fi support.
The order for non-Wi-Fi gaps once Wi-Fi lands is in
[After Wi-Fi](#after-wi-fi-remaining-driver-gaps).
Keep keyboard/storage preparation with A53 work. Offline power work continues
when it can resolve a supported interface or measurement dependency.

| Workstream | First bounded deliverable | Can proceed independently | Hardware or integration dependency |
| --- | --- | --- | --- |
| Integration and lab | Shared checks, immutable packages, one active deployment path, baseline registry | Tooling fixtures, documentation and review | Serialize manifest/series integration and shared Buildbox mutations |
| A72 and power | Resolve a supported measurement or production-ownership contract; completed V4 is not a repeat queue item | Source/math review, fake-hardware tests, ownership design | Exact experiment admission; broader load waits for defensible thermal observation/protection gates |
| Upstream preparation | Extract and review a minimal MT6797 infracfg reset topic from the corrected implementation | Authorship audit, dependency reduction, binding review, maintainer-target discovery | Truthful certification, focused compile/schema checks and existing exact runtime evidence before submission |
| A53 serviceability | Specify and freeze an integration baseline and a ten-cold-boot regression protocol | Authenticated USB userspace, keyboard test plan, log separation, read-only storage tests | One scheduled device slot; persistent writes and power-off need their own reviewed protocols |
| Wi-Fi | Add the missing WMT common power-on (BTIF/STP, ROM patch, RF calibration) before WLAN start and obtain the first received management frame; see the [Wi-Fi audit](../experiments/2026-10-03-mt6797-wifi-audit/README.md) | Vendor power-on sequence mapping, read-only Gemian confirmation, BTIF/STP/WMT implementation and fixtures | Two decision-changing boots (WMT round trip, then calibrated scan); no dependency on A72 completion or all ten cold boots |
| Display, touch and GPU | Map the minimal DRM/panel dependency graph and resolve panel/backlight ownership | Compare current upstream bindings, documented resources and historical evidence | Shared clocks/resets/PMIC reviewed with power; GPU load waits for power/thermal prerequisites |
| Bluetooth, GNSS, FM, audio and sensors | Produce protocol/resource and firmware-rights decisions for each component | Identity matching, transport feasibility and upstream reuse research | Separate subsystem profiles and later runtime slots; no assumed vendor-ABI compatibility |
| Cellular and cameras | Identify upstream transport/pipeline feasibility and the irreducible blockers | Public interface, resource, licensing and existing-effort research | Shared-memory/crash isolation and radio or imaging-specific safety review before hardware work |
| Standard boot and distribution | Define normal package/update/rollback consumption of the integration baseline | Packaging and retained-loader contract review | Reliable storage/recovery; loader replacement is separately admitted |

The [standard package/loader contract](../experiments/2026-09-09-standard-kernel-package/README.md)
separates normal versioned kernel/DTB/initramfs files from retained-LK container
construction and guarded boot2 selection. Current Gemian initramfs hooks supply
no inspected LK deployment step. Select a persistent-root/distribution and its
filesystem update/rollback protocol before implementing that adapter; no package
installation or automatic slot writer is admitted by the source review.
The [Debian ARM64 userspace evaluation](../experiments/2026-09-09-standard-kernel-package/DEBIAN_USERSPACE.md)
now provides a verified 119-package off-device archive and a passing
[VM container lifecycle](../experiments/2026-09-09-standard-kernel-package/DEBIAN_RUNTIME.md).
It identifies missing service isolation in the tested A53 configuration.
The [A53 service-facilities profile](../experiments/2026-09-09-standard-kernel-package/A53_SERVICE_FACILITIES.md)
now freezes the exact tested patch foundation and compiles the missing
namespace/BPF facilities. Its [exact-kernel QEMU test](../experiments/2026-09-09-standard-kernel-package/A53_DEBIAN_QEMU.md)
passes Debian service isolation, IPv4 filtering and orderly virtual filesystem
shutdown. Confirm distribution/storage inputs before creating a persistent-root
candidate; none of this is a PDA distribution boot result.
The separate [A53 RAM regression image](../experiments/2026-09-09-standard-kernel-package/A53_RAM_REGRESSION.md)
paired that kernel with the accepted authenticated environment. Its
[first board session](../experiments/2026-09-09-standard-kernel-package/results/a53-service-ram-runtime-20260925.json)
brought up CPU0–7, authenticated over USB and preserved a complete sealed log;
an independent read-only check confirmed changed-boot Gemian return. The
consumed host runner remains inconclusive because its first return timeout used
an unrecognized CRLF ending; the narrow classifier correction now passes focused
fixtures. Do not repeat the same boot. Review the remaining serviceability
gates before selecting the ten-cold-boot protocol or persistent-root work.

The independent [MMC voltage-switch error fix](../experiments/2026-09-09-mtk-sd-pinctrl-errors/README.md)
returns failed pin configuration to the MMC core. Its isolated Buildbox compile
and injected regression pass; it changes no device candidate or voltage policy.
Truthful certification and upstream review remain required. MT6797 controller
data and microSD rail/card-detect validation remain separate work.

The independent [BQ25890 IRQ lookup correction](../experiments/2026-09-12-bq25890-irq-preflight/README.md)
rejects missing or deferred interrupt resources before charger initialization.
Its isolated Buildbox compile and injected regression pass. Human review and
truthful certification remain required; Gemini charging limits, IRQ wiring and
mainline operation are still unresolved despite its matching BQ25896 identity.

The independent [MT6397 RTC wake-error correction](../experiments/2026-09-12-mt6397-rtc-wake-errors/README.md)
reports failed alarm IRQ wake requests to the power-management core. Its isolated
Buildbox compile includes both suspend callbacks, and the wake/alarm regressions
pass. Human certification remains required; MT6351 compatibility, parent PMIC
interrupt errors and Gemini suspend validation remain separate dependencies.

The [MSDC1 input-enable topic](../experiments/2026-09-09-mt6797-msdc1-input-enable/README.md)
adds the source-backed six-pin IES map and passes isolated Buildbox compilation.
It activates no board state. Schmitt direction semantics, shared drive fields,
pad bias tuning and PMIC trim ownership remain separate before microSD admission.

The independent [Schmitt refusal correction](../experiments/2026-09-09-mtk-pinctrl-schmitt-refusal/README.md)
prevents unavailable SMT fields from causing a direction write before failure.
Its host regression and isolated Buildbox compile pass. Supported-request
direction policy and the MT6797 SMT map remain separate upstream-review work.

The [MSDC1 drive-field topic](../experiments/2026-09-09-mt6797-msdc1-drive/README.md)
now maps CMD, shared DAT0–3 and CLK using the correct selector scale and existing
callbacks. Compilation, encoding and focused binding checks pass; bias tuning,
PMIC trim and the board's pad/power transition remain unresolved before use.

The [MSDC1 pull-field topic](../experiments/2026-09-09-mt6797-msdc1-pull/README.md)
adds the three pull controls after an advanced-pull error-propagation fix.
Compilation and host checks pass. Explicit resistor selections, API write order
and disable-state differences must be respected in the future board protocol;
this topic does not resolve the remaining pad/power ownership.
The [composed pinctrl sequence](../experiments/2026-09-09-mt6797-msdc1-pull/COMPOSITION.md)
now combines input-enable, drive and pull support with both error fixes;
both updated profiles compile. Board pad/power admission remains separate.
The [power-state follow-up](../experiments/2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md)
shows that retained off requests only clear bookkeeping, while normal regulator
updates preserve trim fields. Establish actual entry trim and rail transitions
before using that retained behavior as the basis for a card-power protocol.

The current [display architecture refresh](../experiments/2026-09-07-mt6797-display-upstream-architecture/README.md)
found no local 0028–0044 subset with both a truthful current resource contract
and a real consumer/test story. Display PWM is the smallest likely unlock, but
the local one-handle evidence does not resolve upstream's mandatory `main` +
`mm` clocks. Before any implementation, separately admit a bounded observation
of consumer and parent clock identity, rate-source/gate ownership and MM-domain
lifetime; missing attribution preserves the current two-clock contract.

The independent [clock allocation fix](../experiments/2026-09-08-mt6797-clock-id-allocation/README.md)
repairs the slot-count contract in four existing MT6797 providers and passes
Buildbox compilation. A [public MT6797 patch](https://lists.openwall.net/linux-kernel/2026/09/21/1197)
now covers the same bounds defect with dummy ID-0 gates, whose lookup behavior
differs from the local patch. Hold duplicate submission; follow upstream review
and validate the selected baseline before deleting the local fix. The
[submission packet](../experiments/2026-09-08-mt6797-clock-id-allocation/SUBMISSION.md)
records the overlap and its limits. Historical
camera or multimedia additions still need their own consumer-ownership review.

The current [audio architecture refresh](../experiments/2026-09-07-mt6797-audio-upstream-architecture/README.md)
identifies one smaller independent upstream topic: adapt local patch 0064 into
a true MT6797 AFE text-to-YAML conversion, deleting the superseded text binding
and preserving all eight ordered clock consumers. The
[conversion draft](../experiments/2026-09-08-mt6797-afe-schema/README.md) now passes
focused schema checks and its compiled example against the pinned upstream
baseline; maintainer agreement and truthful authorship/certification remain
unresolved. Only after that schema is accepted should patch 0045 be adapted as
a disabled SoC-node follow-up with the current power-header include and
unit-address ordering. Do not add or enable an MT6351 codec or machine card: the project's older package supplied the missing
MFD parent/cell through local patches 0008/0010, while official current upstream
does not, and Gemini's analog routes remain unestablished.

The [MT6351 MFD preparation](../experiments/2026-09-08-mt6351-mfd-upstream-preparation/README.md)
separates the existing MT6328 domain correction from MT6351 support. Its
isolated thirteen-patch core/regulator topic passes compilation and focused tests;
the unchanged bindings retain their schema validation. IRQ domains and wake
references have managed cleanup. Legacy wake masks are programmed after child
suspend requests, and failed suspend programming attempts all-bank restoration
before returning an error. The topic enables no Gemini board or unrelated PMIC
children and is not a device candidate. Runtime IRQ transport failures now
have bounded diagnostics, but persistent-fault recovery remains unproved.
The shared MT6358-family initializer now keeps mutable interrupt state per
device, with probe-failure and second-device teardown regression coverage.
Next resolve the
[shared VCN33 output/control contract](../experiments/2026-09-08-mt6351-mfd-upstream-preparation/VCN33.md).
Attributable hardware evidence and truthful authorship/certification remain
required before promoting this unsigned topic.

The independent [MT6351 key topic](../experiments/2026-09-08-mt6351-keys-preparation/README.md)
adds chip data and MFD IRQ resources after two generic transport-error fixes.
Its isolated compile and focused schema checks pass; no Gemini key node is
enabled. The [duration correction](../experiments/2026-09-08-mt6351-keys-preparation/RESET_POLICY.md)
converts seconds to the documented hardware selector and rejects unsupported
durations. Before board admission, establish an explicit long-press recovery
policy: the upstream
default disables hardware long-press reset, including the second key function
even with only a power-key child. Physical key, wake and suspend behavior
remain later runtime gates.

The current [cellular architecture refresh](../experiments/2026-09-07-mt6797-cellular-upstream-architecture/README.md)
confirms that generic WWAN ports and netdevs are reusable only above a future
proved transport. PCIe `t7xx`, RPMsg-WWAN and the current MediaTek SCP remoteproc
driver do not match MT6797's APB CLDMA/CCIF and shared-memory ownership. Admit no
driver, binding or shared framing helper yet. The
[MD1 memory handoff audit](../experiments/2026-09-07-mt6797-cellular-upstream-architecture/MEMORY_HANDOFF.md)
resolves host branching: loader readiness still permits shared-remap and staged
MPU writes, and the host callbacks provide no reservation-release contract.
The [Gemian handoff observation](../experiments/2026-09-07-mt6797-cellular-upstream-architecture/GEMIAN_HANDOFF.md)
now joins one boot's v2 loader metadata, reported image header and actual
reservation/shared-layout map. The [retained-loader tail audit](../experiments/2026-09-07-mt6797-cellular-upstream-architecture/LOADER_TAIL.md)
corroborates a deferred-reclamation mechanism consistent with the extra 32 MiB,
without proving the actual boot's tags or a safe release. Next resolve the
loaded-image digest, runtime tail attribution, secure MPU acceptance and
shared-region release authority.
The [retained-firmware join](../experiments/2026-09-07-mt6797-cellular-upstream-architecture/RETAINED_FIRMWARE.md)
pins matching retained header fields and component container digests; it leaves
the executing bytes unproved and exposes a one-byte ARM7 component whose purpose
must be resolved before defining a loadable firmware bundle.
The [retained modem MPU paths](../experiments/2026-09-07-mt6797-cellular-upstream-architecture/SECURE_MPU.md)
establish region-7/13 lock-denial and store behavior; current acceptance and
ownership remain unproved because the host wrapper discards the secure result.
The [cellular feasibility record](../experiments/2026-10-04-gemini-cellular-re/README.md)
adds the AP-side power, PLL and release sequence, shows that LK already loads
and protects MD1 before a mainline kernel runs, separates the HS1 milestone
(no file server, NVRAM, SIM or radio) from HS2, and names a read-only mainline
boot (LK tags, SPM status offsets, boot-status registers) as the cheapest first
experiment. SIM and RF stay modem-internal; voice audio maps onto the existing
MT6797 AFE PCM DAIs.
Do not repeat unchanged OS metadata for those gaps. Missing attribution preserves
the stop; queue/DMA, framing/channel and full boot/crash teardown remain later gates.

Wi-Fi is a first-class usable-system requirement and an active workstream,
not deferred peripheral polish. Its owner defines the shared connectivity
power/firmware interface with the integration owner; Bluetooth and GNSS must
not independently mutate that contract. The evidence must establish the exact
transport and firmware protocol before choosing reuse or a new family driver.
Neither a vendor node name nor a compiled MT76 module establishes a match.
The [gen3 offload review](../experiments/2026-09-08-mt6797-wlan-offloads/README.md)
selects mac80211 as the preferred design target because authentication,
association and receive reordering are host responsibilities in the inspected
source. Translated RX still needs an explicit reorder owner; this choice
admits no driver activation and does not resolve the shared HIF lifetime stop.

The Wi-Fi delivery sequence is a reviewed resource/firmware contract, bounded
bring-up and enumeration, standard cfg80211 scanning and authenticated station
association, then bounded bidirectional traffic and recovery tests. Stable
reconnect, power management and coexistence remain explicit later acceptance.
An upstream host driver using locally supplied retained firmware is an accepted
path; fully open firmware is not a prerequisite. Separate technical and runtime
blockers from blob distribution rights, and do not stall independent development
solely because the latter are unresolved. Private network credentials and device
calibration never enter Git. Queue a physical test only when its distinguishing
observation and effect budget are ready. Prefer a bounded Gemian inventory when it can distinguish the transport
without a new kernel or boot2 cycle; audit retained firmware/vendor source in
parallel. Source and protocol implementation proceed alongside A53 work now.

The [registry](../project/workstreams.json) records owners, scopes and evidence
links.
The [upstream topic inventory](../project/upstream-topics.json) separates review
preparation from certification and public submission.

When a worker waits for a build, hardware, rights or maintainer feedback, move it
to the next ready offline item. Prefer work that removes a dependency shared by
several subsystems, then a small upstream-ready topic, then the next useful
system capability. Avoid opening another diagnostic framework to fill waiting
time. Run an early feasibility sweep for display, connectivity, cellular and
cameras before committing large implementation effort to their assumed design.

### Integration contract

- Use one small Git worktree per active work item and a `codex/` topic branch.
  No worktree contains a Linux tree. The integrator owns `kernel/manifest.json`,
  canonical series ordering and roadmap edits; workers submit proposed deltas.
  Freeze the integration checkout from build submission through package fetch;
  workers continue only in their own worktrees during that window.
- Freeze explicit patch/config inputs for active baselines before an unrelated
  canonical extension could change them. Verify every existing profile's
  effective input before and after integration. Historical invalid profiles
  remain unavailable as foundations.
- Do not independently edit shared clock/reset/PMIC/DT contracts. Agree the
  interface and its owner first; dependent implementations can then run in
  parallel against the same contract and fake-hardware fixtures.
- Handoffs include exact revision, changed paths, dependencies, focused checks,
  evidence/limitations and the proposed upstream topic. A new owner can resume
  without reading a long task conversation.
- Run fast host checks on each change. Kernel changes use focused tests and
  explicit Buildbox builds, reusing matching managed sources and build outputs.
  Rebuild for changed inputs or unresolved evidence, not for prose or markers.
- Integrate small coherent topics; keep diagnostic interfaces default-off and
  removable. Record tested integration revisions separately from topic results.

### Device-test cadence

When the owner and device are available, prioritize the next reviewed,
decision-changing device session over extending an already sufficient offline
test suite. The integrator closes concrete deployment defects and the custodian
runs the admitted test promptly; host-test completion is not a runtime result.
After each session, preserve and classify evidence before choosing the next
change. Do not repeat identical artifacts merely to maintain a testing cadence.

Use the existing [authenticated baseline outcome](../experiments/2026-09-05-owner-away-experiment-preparation/baseline/ATTENDED_OUTCOME.md)
and [supplemental recovery review](../experiments/2026-09-05-owner-away-experiment-preparation/baseline/RECOVERY_WITNESS_REVIEW.md)
as the separately scoped prerequisites for keyboard and read-only storage work.
Do not repeat that baseline merely to activate a dependent item. Before asking
for a new physical cycle, establish the actual OS and appropriate transport;
follow the [transport reference](../experiments/2026-09-05-owner-away-experiment-preparation/emmc/TRANSPORT_REFERENCE.md)
when a USB connection is absent. A relayed boot report does not replace live
identity or establish that a different OS is unreachable.

The keyboard milestone is owner-accepted, and the bounded eMMC read has its
own completed observation. Preserve their limitations without scheduling the
consumed tests again. Require the next selected candidate's verified deployment
and clean-shutdown handoff. Wi-Fi progresses kernel integration and its shared
resource/firmware contract, with physical observations chosen to resolve
explicit blockers. If the owner is unavailable, leave the exact session
packet ready and continue independent work; do not make all workers wait for boot2.

### Owner-away progress

Owner availability must not become the project's global critical path. While a
physical boot is unavailable, workers continue source and binding research,
small upstream-topic preparation, implementation, host/fixture tests, authorized
Buildbox builds, candidate packaging and review. Existing private dumps and
Gemian live inspection are also available under the standing
[inspection policy](SAFETY.md#standing-gemian-inspection-authorization); a reviewed
return to Gemian can support discovery without an owner-selected boot2 cycle. Finish the blocked item's
handoff, then move to independent work. Waiting device items do not occupy one
of the three active worker slots.

Keep a short look-ahead of up to three fully prepared, decision-useful device
items when the evidence supports them. This is a ceiling, not a quota: do not
build speculative variants to fill it. More ideas may remain as cheap protocol
or source research. Reuse frozen baseline inputs and prepared Buildbox sources;
retain only artifacts needed by open items and verified recovery.

The owner prioritizes usable mainline Wi-Fi before further A53 keyboard or
storage development. Preserve the accepted A53 boot/recovery foundation for
Wi-Fi tests, but do not turn its ten-cold-boot release series into a prerequisite
for the first Wi-Fi bring-up. The current preparation order is:

1. **Preserve the accepted baseline foundation:** reuse its exact candidate,
   authenticated userspace, logging and reviewed recovery closure. Repair only
   an identified invalidated prerequisite; a similarly named newer profile is
   not a replacement for recorded inputs. Do not spend a boot on another marker.
2. **Wi-Fi:** use the compiled transfer components and validated whole-image
   plan to implement a retained shared CONSYS/EMI owner and a complete firmware
   executor. The first firmware load can use PIO; AP-DMA needs its own owner
   before packet DMA is enabled. The retained local calibration record has an
   identified producer family and remains a viable input candidate. Validate
   its envelope, board/firmware pairing and actual application at the normal
   command boundary; do not require its complete restoration history or
   non-default RF bytes as a universal bring-up prerequisite. Keep ordinary
   section submission distinct from firmware execution; missing EMI ownership
   must not become a success flag or skipped section.
   The [regulatory configuration boot](../experiments/2026-10-01-mt6797-regulatory-config/results/runtime-1.json)
   now proves supported configuration PIO submission under a cfg80211 owner
   and one CONSYS-bound mac80211 wiphy after capability, bounded debug drain
   and private-record preparation. The [counter probe](../experiments/2026-10-01-mt6797-tx-status/results/runtime-1.json)
   stopped before configuration. The [header successor](../experiments/2026-10-01-mt6797-tx-status-header/results/runtime-1.json)
   identified an unsolicited sleepy notification. The [boot-sleepy successor](../experiments/2026-10-01-mt6797-boot-sleepy/results/runtime-1.json)
   now admits its exact layout, retains driver ownership, completes configuration
   and witnesses consumable post-configuration TC4/free-pool counters. The [TC4 successor](../experiments/2026-10-01-mt6797-tc4-reconcile/results/runtime-1.json)
   now demonstrates bounded matched credit return and retained pending counts
   for that pair. The [passive-scan successor](../experiments/2026-10-01-mt6797-passive-scan/results/runtime-4.json)
   now creates a standard station-type interface, completes one firmware scan
   through iw and witnesses runtime credit return, but receives no BSS result.
   Its 2.4 GHz-only advertisement omits the band used by the [known-good
   connection](../experiments/2026-10-01-mt6797-passive-scan/results/band-context-4.json).
   The [non-DFS 5 GHz successor](../experiments/2026-10-02-mt6797-passive-scan-5g/results/runtime-1.json)
   now exposes permitted channel 40 and completes an ordinary passive scan,
   again without management packets or BSS output. The single
   [500 ms timing observation](../experiments/2026-10-02-mt6797-passive-scan-dwell/results/runtime-1.json)
   completed after 513501 us with returned credit and normal broadcast submission,
   but still no management frame or BSS. Changed-boot Gemian returned with carrier
   at 5200 MHz. Nominal command timing is consistent; actual RF dwell and tuning
   remain unverified. The [firmware-counter observation](../experiments/2026-10-02-mt6797-passive-scan-count/results/runtime-1.json)
   completed with version 3 management count zero and no host frame or BSS.
   Prioritize channel setup and receive paths before that firmware processing
   point; zero does not prove radio silence or a filter cause. The
   [tuning-sample result](../experiments/2026-10-02-mt6797-scan-tuning-sample/results/runtime-1.json)
   matched the requested band/channel software state in both sample pairs before
   completion, with management count zero and no host frame or BSS. Prioritize
   receive enabling, filtering and preprocessing before that counter in the
   selected contract; caches do not prove RF tuning or calibration application.
   The [Gemian reference](../experiments/2026-10-02-gemian-passive-scan-reference/README.md)
   returned three recent channel-40 BSS entries from one requested-passive scan.
   Probe-response metadata and the pinned vendor passive-support setting leave
   actual passive equivalence unverified; its associated state and default dwell
   differ. Do not infer mainline beacon reception or add probe transmission from
   this reference. The [early-receive diagnostic](../experiments/2026-10-02-mt6797-scan-rx-sample/README.md)
   completed all four replies before DONE, with both earlier statistic bytes
   zero in both pairs, ordinary management count zero and no host frame or BSS.
   The complete log was preserved and changed-boot Gemian recovery passed.
   This does not support observed early processing bypassing a later count gate.
   The [receive-mode diagnostic](../experiments/2026-10-02-mt6797-scan-mode-sample/README.md)
   completed with mode 5 at both sampled instants and zero dispatcher bytes,
   ordinary management count and BSS results. Changed-boot Gemian recovery
   passed. The selected prerequisite holds at those instants; prioritize
   earlier receive queue/descriptor admission and receive enabling/filter
   ownership. Mode continuity, byte wrap/reset and unsampled intervals remain
   unresolved. Do not force the mode word.
   The [native receive-pool diagnostic](../experiments/2026-10-02-mt6797-scan-pool-sample/README.md)
   completed with a valid head and all 32 objects free at both non-atomic
   sample pairs, while management count and BSS remained zero. Evidence was
   sealed and changed-boot Gemian recovery passed. Deprioritize pool depletion
   at the sampled instants; trace descriptor arrival and receive enabling/filter
   ownership. Continuous availability, initializer execution and indirect query
   effects remain unresolved. Do not turn pool observations into RF counts.
   The [event admission trace](../experiments/2026-10-02-mt6797-scan-pool-sample/results/receive-event-admission-analysis.json)
   identifies a masked pending bit-3 route and two ordinary-RAM raw snapshots.
   The [2026-10-03 Wi-Fi audit](../experiments/2026-10-03-mt6797-wifi-audit/README.md)
   finds that no mainline boot has run the vendor WMT common power-on over
   BTIF/STP: ROM patch download, RF calibration with the PA LDOs and coexistence
   precede WLAN start in the pinned source. The [startup follow-up](../experiments/2026-10-03-mt6797-wifi-audit/STARTUP_FOLLOWUP.md)
   finds crystal trimming disabled and Gemian co-clock disabled; retain enabled
   DLM and actual build-conditional branches rather than assuming every setting. That gap
   sits upstream of every receive gate sampled so far. **Current Wi-Fi order:**
   (a) map the vendor power-on sequence against mainline, offline;
   (b) confirm in Gemian, read-only, that those steps ran on this device;
   (c) [completed default-query round trip](../experiments/2026-10-03-mt6797-wmt-default-query/results/runtime-2.json):
   matched 16-byte event, two IRQ entries, retained clocks, complete preservation
   and confirmed Gemian return; [completed checked negotiation](../experiments/2026-10-03-mt6797-wmt-negotiate/results/runtime-1.json)
   now proves mandatory set-options, full-STP event, peer credit and host ACK;
   the [installed ROM pair and version review](../experiments/2026-10-03-mt6797-wifi-audit/ROM_APPLICABILITY.md)
   now attributes both installed files, but checked chip/HW/ROM reads must precede
   negotiation in the complete owner. Resolve the inconsistent register-read
   event length, exact applicability, DLM/register contracts and checked
   calibration results before selecting the remaining common-init owner;
   (d) one boot adding ROM patch, WMT reset, RF calibration and coexistence
   settings before the existing START and one channel-40 passive scan.
   Park the unfinished cached event-mask diagnostic (proposal 0085); revisit it
   only if (d) still shows zero firmware management frames. Do not repeat the
   consumed lifetimes. Establish management
   reception, then continue runtime receive/event ownership,
   credit recycling and packet lifetime toward association and bounded traffic.
   Submission status alone
   does not prove firmware application or effective runtime RF restrictions.
   The consumed one-shot candidate is not a repeat test.
   Use the [Wi-Fi contract](hardware/mt6797-wifi.md) and existing private captures.
   Host fixtures and compile-only adapters do not establish usable Wi-Fi. The
   build-selected detector ioctl is the established kernel-side producer of
   `do_connectivity_driver_init` and returns its integer aggregate. The exact
   retained loader statically supplies a property/query-derived normalized
   scalar after cleanup, then logs and discards the init result. A later
   [read-only Gemian boot-log observation](../experiments/2026-09-05-mt6797-wifi-contract/results/gemian-wifi-init-20260925.json)
   records an actual `0x6797` init argument and zero gen3 WLAN init result in
   one boot; this vendor path does not define a mainline ABI or prove every
   component's success. The accepted
   [standard interface/error design](../experiments/2026-09-06-mt6797-mainline-connectivity-interface-design/README.md)
   made the first slice an effect-free passive CONSYS descriptor plus opaque
   WLAN client binding. That [accepted implementation](../experiments/2026-09-06-mt6797-consys-passive-boot/README.md)
   passed Buildbox, guarded boot2 deployment and one authenticated runtime
   observation: the client reached `BOUND` generation 1 with all seven effect
   counters zero. Its boot and collection budgets are consumed; do not repeat
   it or promote the result to usable Wi-Fi. Before another candidate, define
   and validate shared CONSYS/EMI/AP-DMA ownership and an effect-bearing failure
   lifetime, while later lifecycle work still resolves an explicit gen3
   teardown edge. A later
   [one-boot passive SPM snapshot](../experiments/2026-09-25-mt6797-consys-status/results/runtime-20260925.json)
   found both CONN power-status bits off in two late-init reads with a complete
   log and no effect call. The same log records this boot's 2 MiB no-map
   CONSYS reservation at `0xbfa00000..0xbfbfffff`. These observations remove
   the live-powered-state and unknown-allocation branches for that boot, but
   do not prove exclusive handoff, remap/EMI ownership or safe
   activation. Do not repeat that candidate; the next device gate must measure
   a new ownership premise. An attended
   [shared-handoff snapshot](../experiments/2026-09-25-mt6797-consys-handoff/results/runtime-20260926.json)
   then captured a complete authenticated log: CONN remained off, but both
   bus-protection status bits were clear, the common remap was disabled, and
   EMI selector bit 13 was set. The device returned to Gemian. This refuses
   adoption of an already protected/mapped shared handoff; it does not prove
   the cold-off state is faulty. Next resolve actual writer exclusion and the
   serialized protection/remap/power sequence before firmware effects, rather
   than repeating either passive image. A
   [compile-validated SCPSYS failure latch](../experiments/2026-09-26-mt6797-conn-fault-retention/README.md)
   avoids post-request prerequisite cleanup after an opted ON error. An
   [isolated CONN domain-data proposal](../experiments/2026-09-26-mt6797-conn-domain-data/README.md)
   now selects it only for compile validation. A later
   [fault-query proposal](../experiments/2026-09-26-mt6797-conn-fault-retention/README.md)
   lets the future owner check that latch even when genpd skips a callback;
   the owner still needs rail/reset sequencing and must call the query before
   every hardware use. A later [compile-only SPM preamble](../experiments/2026-09-26-mt6797-conn-spm-register-control/README.md)
   links the selected CONN key write before ON/OFF register work; it is not a
   boot candidate and does not settle retained-firmware writers or shared
   rail/reset ownership. A later
   [accepted-A53 source replay](../experiments/2026-09-26-mt6797-conn-spm-register-control/README.md#accepted-a53-source-integration-gate)
   applies all seven provider proposals cleanly to its Linux 7.1.3 source,
   but its selected configuration disables SCPSYS. Enabling the legacy
   provider as-is would activate other MT6797 domains during probe. Resolve
   that registration/consumer behavior before making a boot candidate; source
   portability alone does not admit a device test. A
   [child-domain provider comparison](../experiments/2026-09-26-mt6797-conn-spm-register-control/README.md#child-domain-provider-comparison)
   finds that the newer provider can avoid unrelated probe activation, but
   its original default-off check and ON-error cleanup cannot retain a safe
   CONN state. Isolated, compile-validated
   [initial-OFF admission](../experiments/2026-09-26-mt6797-modern-provider-off-admission/README.md),
   [fault retention](../experiments/2026-09-26-mt6797-modern-provider-fault-retention/README.md)
   and [checked status polling](../experiments/2026-09-26-mt6797-modern-provider-status-errors/README.md)
   proposals now address those provider prerequisites. The
   [isolated MT6797 CONN data](../experiments/2026-09-26-mt6797-modern-conn-data/README.md)
   selects the flags and links in a compile-only profile. A later
   [modern-provider fault query](../experiments/2026-09-26-mt6797-modern-provider-fault-query/README.md)
   exposes the retained error to a future owner. The
   [modern CONN SPM preamble](../experiments/2026-09-26-mt6797-modern-provider-spm-preamble/README.md)
   is selected only in that compile profile. The modern provider already
   disables the domain clock before reset; an
   [opted CONN OFF-order patch](../experiments/2026-09-26-mt6797-modern-provider-off-order/README.md)
   instead clears the primary power request before the secondary one, as the
   retained CONN routine does. The
   [A53 integration build](../experiments/2026-09-26-mt6797-modern-conn-data/A53_INTEGRATION.md)
   now links these provider proposals with the accepted service foundation;
   its Gemini DTBs are unchanged. No child DT, query client or shared owner is
   present; this is not a device candidate. The built-source attach audit
   also shows that one ordinary `power-domains` reference would power CONN
   before the owner's platform probe can prepare VCN rails and CONMCU reset;
   the owner needs an explicit deferred attachment design. A
   [pinned-source child-population audit](../experiments/2026-09-26-mt6797-modern-conn-data/A53_INTEGRATION.md#staged-child-population-in-the-pinned-source)
   identifies a parent that prepares the shared resources before creating a
   child with the ordinary CONN domain reference. Implement that parent with
   retained failure lifetime and prove the child/owner binding before any
   effect-bearing boot. A [checked OFF query](../experiments/2026-09-26-mt6797-modern-provider-off-query/README.md)
   now compiles with that A53 provider and rejects ON, mixed, read-error and
   latched-fault states; it does not prove child quiescence or an exclusive
   handoff, so it cannot alone authorize outer-rail cleanup. A
   [checked ON query](../experiments/2026-09-28-mt6797-conn-on-query/README.md)
   provides the matching dual-status and retained-fault gate for a future
   powered owner after runtime resume; no client calls it yet. A later
   [A53 Wi-Fi core integration build](../experiments/2026-09-26-mt6797-a53-wifi-core-integration/README.md)
   links the private HIF and whole-image components with the modern CONN
   provider, but still has no shared owner, firmware executor or active child.
   A later [focused configuration build](../experiments/2026-09-26-mt6797-a53-wifi-core-integration/README.md#focused-wireless-configuration)
   removes the unrelated WLAN vendor selections while preserving the private
   core and standard wireless stack. A [passive CONSYS owner
   slice](../experiments/2026-09-27-mt6797-consys-owner/README.md) now has a
   [successful authenticated device probe](../experiments/2026-09-27-mt6797-consys-owner/results/passive-runtime-1.json):
   it bound the boot reservation and claimed the shared remap word through the
   kernel resource tree. It has no remap write or shared power/EMI sequence.
   A [second authenticated boot](../experiments/2026-09-27-mt6797-consys-rails-passive/results/runtime-1.json)
   then bound real MT6351 VCN18, VCN28 and VCN33-Wi-Fi handles without changing
   rail state; its log and service phases completed, and a supplemental read-only
   probe confirmed the changed-boot Gemian return after the automatic return
   watcher rejected a transient `Host is down` message. This consumes the
   passive rail gate, not rail sequencing or usable Wi-Fi. A
   [compile-only firmware preparation build](../experiments/2026-09-27-mt6797-wifi-firmware-prepare/results/build.json)
   now links `request_firmware()` to the complete MTKE plan while retaining
   its immutable input, but has no runtime caller or WLAN child. The
   [retained-image C check](../experiments/2026-09-27-mt6797-wifi-firmware-prepare/results/retained-plan.json)
   accepts the actual four-section image yet refuses executable views without
   an EMI owner. A [passive CONMCU reset binding boot](../experiments/2026-09-27-mt6797-consys-reset-passive/results/runtime-1.json)
   confirmed that the shared owner acquired the TOPRGU bit-12 handle without
   operating it. Its complete log, A53 service regression and changed-boot
   Gemian return passed. A later [passive modern CONN provider boot](../experiments/2026-09-27-mt6797-conn-provider-passive/results/runtime-1.json)
   registered one CONN child after its initial-OFF guard, preserved a complete
   log, passed the A53 service regression and returned to a new Gemian boot.
   A [passive owner-domain association boot](../experiments/2026-09-27-mt6797-conn-domain-link-passive/results/runtime-1.json)
   then attached the manager without requesting power and passed its explicit
   checked-OFF query; one provider and one owner record, the complete log, A53
   regression and changed-boot Gemian Wi-Fi return passed. A following
   [read-only VCN28 boot sample](../experiments/2026-09-27-mt6351-vcn28-boot-observe/results/runtime-1.json)
   found `0x1a60` after the checked-OFF query, with on-control clear and both
   source fields 3; its complete log, A53 regression and changed-boot Gemian
   Wi-Fi return passed. This establishes one initial register value, not the
   physical inputs or exclusive writer handoff. A later
   [guarded power probe](../experiments/2026-09-28-mt6797-wifi-power-probe/results/runtime-1.json)
   confirmed one CONN ON transition with CONMCU reset held. The following
   [delayed chip-ID probe](../experiments/2026-09-28-mt6797-wifi-chip-id-delay/results/runtime-1.json)
   read zero after 30 microseconds and `0x0279` after a requested 20-ms wait
   in one complete, regression-passing mainline boot, then returned to
   carrier-up Gemian. This supports a settling interval in that boot, not a
   minimum delay or repeatability. It does not establish reset release,
   shared writer/EMI ownership, firmware execution or mainline Wi-Fi. A
   [powered EMI read](../experiments/2026-09-28-mt6797-wifi-powered-emi/results/runtime-1.json)
   then found nonzero region-1 control and zero region-18/19/23 ranges after
   the delayed `0x0279` in one complete, regression-passing boot; changed-boot
   Gemian Wi-Fi return also passed. This validates a point-in-time powered
   empty-range premise, not writer exclusion or effective CONSYS/AP protection
   domains. A subsequent [gated reset-release boot](../experiments/2026-09-28-mt6797-wifi-reset-release/results/runtime-1.json)
   set MCU ACR bit 18 and released CONMCU reset once; chip ID remained `0x0279`
   with CONN ON. Its complete sealed log and changed-boot Gemian carrier return
   passed, but the collector was not armed before boot2 selection and the prior
   clean shutdown was unconfirmed. A subsequent [gated HIF startup candidate](../experiments/2026-09-28-mt6797-wifi-hif-probe/README.md)
   was built, validated, installed to boot2 with full readback, and cleanly shut
   down. Its first finite watch ended at MediaTek `20ff` without a mainline route
   or kernel log. The owner later reported boot2 started; a second watch began
   after that report and saw the same `20ff` stage without a transition or route.
   These were host-stage limits, not HIF results. A later powered-off,
   [prearmed mainline boot](../experiments/2026-09-28-mt6797-wifi-hif-probe/results/runtime-1.json)
   reached the authenticated collector: IOEx/IORx changed from `00/00` to
   `02/02`, and WCIR read `0x00100279`. Its complete sealed log, A53 regression,
   reviewed recovery and independent changed-boot Gemian Wi-Fi carrier check
   passed. The passive WLAN child also accepted the staged image's four-section
   plan in that boot. This validates one pre-firmware HIF path and live image
   acquisition, not usable mainline Wi-Fi.
   A later [one-shot mainline EMI policy probe](../experiments/2026-09-28-mt6797-emi-set-probe/results/runtime-1.json)
   reached the same power/reset/HIF gates and received zero status with matching
   direct region-18 readback for both temporary `0xb6da28` and final
   `0xb6da2d` requests. It transferred no firmware. That closes the secure
   request/readback question for this boot; build the owned complete-section
   transaction next, retaining the firmware source, mapping and powered
   resources through any failed copy or later execution. A repeat of the
   policy-only candidate has no decision value. Effective bus permissions,
   master-domain routing, external-writer exclusion and any future firmware
   fetch remain unproved.
   The following [bounded mainline EMI-copy probe](../experiments/2026-09-28-mt6797-emi-copy-probe/results/runtime-1.json)
   copied and read back both pinned EMI sections (396,688 bytes), then sealed
   region 18 with matching status and direct readback. Its full log, A53
   regression and changed-boot Gemian Wi-Fi return passed. The one-shot image
   is consumed. AP copy is no longer the blocking question; the next executor
   must submit both ordinary HIF sections and test firmware start under retained
   shared ownership. CONSYS fetch permissions and actual execution remain
   unproved until that distinct test.
   The [first firmware-start runtime record](../experiments/2026-09-28-mt6797-firmware-start-probe/results/runtime-1.json)
   shows successful driver ownership, both ordinary CONFIG/PDA sections and
   one START submission, followed about 0.58 seconds later by a fatal CPU7
   workqueue NULL-pointer panic. Persistent RAM recovered the result after
   the host collector failed; no WLAN-ready result was logged. Stop START
   testing and do not replay this image. Resolve the invalid workqueue pool
   and the region-19/23/shared-memory ownership and protection gap before a
   distinct, reviewed candidate. The temporal association does not establish
   that WLAN firmware wrote the invalid pointer.
   A subsequent [read-only Gemian region-19 memory sample](../experiments/2026-09-29-mt6797-region19-live-reference/results/runtime-1.json)
   found the neighboring 512 KiB window populated and changing on two pages
   over ten seconds with WLAN carrier. This makes its missing mainline
   initialization a concrete source/runtime difference, not an explanation
   yet for the workqueue fault or proof of the required contents. Preserve
   any diagnostic records before a future clear.
   A [passive mainline region-19 boot](../experiments/2026-09-29-mt6797-region19-mainline-observe/results/runtime-2.json)
   then found 267 nonzero bytes across 110 pages before CONN power or firmware
   activity; its complete log and A53 regression passed. The changed-boot
   Gemian return had 54,453 nonzero bytes across 54 pages in the same window
   with Wi-Fi carrier. The selected WMT source protects that 512 KiB window,
   programs the shared remap and clears only its first 343 KiB. Attribute and
   preserve those contents before designing an owned initialization sequence;
   the separate-boot counts do not establish a writer or explain the START
   panic.
   A [subsequent passive private-export boot](../experiments/2026-09-29-mt6797-region19-private-export/results/runtime-1.json)
   captured two identical 512 KiB reads in one mainline boot. Private RE-VM
   analysis found 370 isolated single-bit bytes across 117 pages and zero WMT
   print-buffer header words, unlike the populated header in the separate
   Gemian control boot. Its complete log, A53 regression and changed-boot
   carrier-up Gemian return passed. Treat the WMT control window as requiring
   explicit owned initialization; neither these bits nor the missing header
   attribute the earlier workqueue panic. Continue static ownership and
   workqueue analysis before any new firmware START candidate.
   A [one-shot WMT memory setup](../experiments/2026-09-29-mt6797-region19-wmt-memory/results/runtime-1.json)
   subsequently returned secure status zero and read back region 19 and the
   shared remap in one mainline boot with CONN held off. A same-boot private
   before/after read proved the first 343 KiB cleared and the rest of the
   512 KiB window unchanged. The initial sysfs write never reached the kernel
   because `/sys` was read-only; a bounded temporary remount admitted the
   single actual store and was restored to read-only. The complete log, A53
   regression and changed-boot Gemian return passed. This closes the
   AP-visible WMT initialization gap, but neither establishes effective CONN
   permissions nor explains the earlier workqueue panic. The later
   [WMT-prepared START](../experiments/2026-09-29-mt6797-wmt-before-start/results/runtime-3.json)
   admitted the exact region-19 state, released reset, completed both EMI and
   ordinary section transfers, and read WCIR ready after one START. Its full
   log, A53 regression and changed-boot Gemian return passed with no repeat
   of the workqueue panic. This is one firmware-ready diagnostic, not proof
   of the earlier panic's cause or of packet networking. Radio commands and
   DMA remained held. The next steps are an owned normal command/event path,
   calibration applicability, packet-DMA address and lifetime admission, and
   a bounded interface/association/traffic protocol. The region-23 overlap
   and effective master permissions remain unproved.
   A same-boot admission gate is required for every active firmware executor;
   an earlier boot's zeros cannot authorize an EMI write. A
   [passive mainline EMI read](../experiments/2026-09-27-mt6797-emi-boot-observe/results/runtime-1.json)
   returned zero for region-18/19/23 range and policy registers in a
   complete, regression-passing boot. The returned carrier-up Gemian boot
   reported those regions programmed. Do not adopt an assumed inherited
   protection state: design an owned region-18/19 transaction and validate its
   readback and failure lifetime before firmware execution. A later
   [24-region mainline census](../experiments/2026-09-27-mt6797-emi-range-census/results/runtime-1.json)
   supplied the missing same-boot secure-read positive control: 12 range words
   were nonzero while regions 18, 19 and 23 were zero. After a changed-boot
   Gemian return with WLAN carrier, 20 of 24 range words matched; regions 18,
   19, 22 and 23 were programmed only in that separate Gemian snapshot.
   Pinned Gemian source assigns region 22 to separate SCP shared memory and
   labels permission domain 2 `CONN`; neither is an authenticated writer trace
   or effective master routing. The census rules out a uniformly zero
   mainline read response but does not establish an effective policy or
   permission to copy Gemian's protection settings. A
   [retained-image read-path check](../experiments/2026-09-27-mt6797-emi-range-census/results/retained-read-service.json)
   confirms the 24 census offsets take direct register reads in that image,
   while the region-23 policy offset uses a cached word. The executing secure
   firmware's runtime identity, master-domain routing and region-23 overlap rule still
   need validation. A [read-only owner preflight](../experiments/2026-09-28-mt6797-emi-owner-preflight/README.md)
   reconfirmed both persistent TEE slots match the retained EMI-service image
   and found the live Gemian GPS EMI option disabled; its apparent shared-remap
   write is also compiled out in the pinned source. This narrows identity and
   Linux-writer uncertainty without proving the executing secure image or
   granting an EMI write. The
   [read-only Gemian EMI reference](../experiments/2026-09-26-mt6797-emi-active-reference/results/runtime.json)
   confirms the vendor-requested region-18/19 ranges and permission values in
   a boot where WLAN carrier was observed later, but also shows broad region 23
   overlapping both. A [one-use, non-blocking EMI watchpoint](../experiments/2026-09-28-mt6797-emi-watchpoint/results/runtime.json)
   on a later carrier-up Gemian boot produced no hit during one second of
   connected idle traffic, then restored every observed register. That window
   cannot identify the master; do not repeat it unchanged. A successor must
   observe an attributable firmware-load or active data interval. Use the
   exact reference for the private owner design; determine effective
   master routing and overlap applicability before choosing mainline protection
   policy. The [retained boot-chain pass](../experiments/2026-09-26-mt6797-emi-active-reference/README.md#retained-boot-chain-routing-pass)
   located preloader device-APC field writes and AP-DMA's separate per-channel
   domain control, but neither assigns the CONSYS master or resolves the EMI
   overlap. The accepted no-database parser run
   establishes original ordinary-global `T` linkage for all four required wrapper/init/exit targets
   and conservative next-distinct-symbol inspection envelopes. The later
   retained-instruction observer/checker line is owner-closed without semantic
   execution and must not be resumed as another offline repair loop. A bounded
   [stock Gemian observer check](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/README.md)
   found no live kprobe or function-tracing path for the required lifetime
   evidence. A [boot2-tested Gemian reference kernel](../experiments/2026-09-26-gemian-wifi-reference/results/runtime-1.json)
   now provides function and function-graph tracing, disabled by default, and
   records co-clock mode zero plus successful raw EMI secure-call returns in a
   working WLAN boot. A [single direct WMT off/on trace](../experiments/2026-09-26-gemian-wifi-reference/results/trace-wmt-cycle-1.json)
   captured WLAN remove/probe and image mapping/load helper calls with Bluetooth
   still on and no selected common-block power call. Carrier returned, but a
   new cfg80211 removal warning occurred because the associated interface still
   held a `current_bss` reference at unregister. The later
   [v2 stop cycle](../experiments/2026-09-26-gemian-wifi-reference/results/trace-wmt-stop-v2-1.json)
   first disconnected, then observed one successful firmware power-control
   command, WCIR ready clear and completed worker waits without another warning;
   carrier returned. A separate [bounded DMA-path trace](../experiments/2026-09-26-gemian-wifi-reference/results/trace-dma-presence-v2-1.json)
   confirmed live WLAN DMA configuration/start calls. These results narrow the
   earlier [retained-evidence audit](../experiments/2026-09-07-mt6797-wifi-retained-lifetime-audit/README.md):
   [post-carrier DMA records](../experiments/2026-09-26-gemian-wifi-reference/results/runtime-v5-return-1.json)
   then observed one RX and one TX idle poll with EN clear before unmap in a
   working Gemian boot. Both records followed link-ready by about one
   millisecond. A later [authenticated-window observation](../experiments/2026-09-26-gemian-wifi-reference/results/runtime-v6-return-1.json)
   recorded the same first-poll EN-clear result in each direction after a
   root-only trigger, about 51 seconds after link-ready. The records remain
   window-attributed rather than tied to an individual SSH packet. The exact
   v6 source also shows that its DMA interrupt-poll timeout returns before
   logging, so each record implies an HIF0 interrupt-flag bit-0 read set
   before acknowledgement and the EN-clear poll. The driver does not write
   STOP in this compiled path. This is a source-derived inference, not a
   captured interrupt-register value; stale flags and external STOP/FLUSH/
   reset remain possible. Programmed register addresses, data delivery,
   effective EMI arbitration remain unresolved. A later
   [single-use v8 last-client trace](../experiments/2026-09-26-gemian-wifi-reference/results/trace-shared-off-v8-1.json)
   observed HCI close release BT's WMT vote, WLAN off invoke common CONSYS
   power-off, both SPM CONN status bits clear, and the reverse power-on path
   restore WLAN carrier and Bluetooth. This narrows shared sequencing in the
   vendor reference but does not prove exclusive mainline handoff, firmware/
   DMA quiescence or safe rail/reset release. A [v7 read-only PMIC sample](../experiments/2026-09-26-gemian-wifi-reference/results/runtime-v7-return-1.json)
   found VCN28 control bit 3 set after the working Gemian hardware-mode request;
   both source-clock selection fields read 3. The physical clock/control
   truth table and shared ownership remain open. A
   [v8 reset readback](../experiments/2026-09-26-gemian-wifi-reference/results/runtime-v8-return-2.json)
   observed TOPRGU CONMCU reset bit 12 set after the vendor assert request and
   clear after release in a working Gemian boot. Physical reset behavior,
   exclusive ownership and safe mainline sequencing remain unproved. The
   [same-boot 4G/DMA join](../experiments/2026-09-26-gemian-wifi-reference/results/4g-mode-v6-dma-join.json)
   finds the positive early 4G selector and later mapped host addresses below
   4 GiB while the selected HIF start path issues unconditional ADDR2 bit-32
   set writes; it does not identify the effective bus alias or select a DMA
   address policy. Resolve shared-owner admission and an effect-bearing failure
   lifetime before another mainline firmware candidate. The first firmware
   load may use PIO;
   validate AP-DMA ownership before enabling packet DMA. Do not replay the
   consumed Gemian radio or DMA cycles merely to repeat this observation.
   See the
   [retained-ELF boundary](../experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/README.md),
   [accepted database boundary](../experiments/2026-09-06-vmlinux-to-elf-kernel-db-provenance-v2/README.md)
   and [accepted Kallsyms provenance](../experiments/2026-09-06-vmlinux-to-elf-symbol-provenance-v3/README.md).
   The [native export-return diagnostic](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/EXPORT_RETURN.md)
   reached full PID1 startup and preserved its CPU-online refusal through a
   normal return to Gemian. The [native HPS correction](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/HPS_BOOT_POLICY.md)
   passed its disabled-HPS check but still refused CPU0–4 in place of CPU0–7,
   preserving the failure through normal return. The validated
   [initial CPU-limit correction](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/BOOT_CPU_LIMIT.md)
   overrides LK's five-CPU default and requires both exact arguments and actual
   CPU0–7. Its first reported physical selection has an
   [inconclusive return observation](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/BOOT_CPU_LIMIT.md#device-observation):
   the late return collector obtained no authenticated identity or log. A
   [later owner selection](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/BOOT_CPU_LIMIT.md#later-owner-selection)
   preserved the CPU0–7 preflight pass and a stop after 60 seconds waiting for
   the unarmed host receiver. The later pre-armed
   [USB Ethernet session](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_ETHERNET_SESSION.md)
   also passed preflight and started its listener, but never enumerated USB;
   its stopped marker and changed-boot Gemian return are preserved. The
   [connection correction and physical test](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_ETHERNET_CONNECT.md#physical-test-result)
   also ended without enumeration. Earlier readiness-loop messages did not
   recur. The [bounded late diagnostic's retained result](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_ETHERNET_DIAGNOSTICS.md#retained-physical-result)
   now establishes readiness and cable-false decisions, with no controller
   start recorded. The [charger-detection result](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_CHRDET_DIAGNOSTICS.md#retained-physical-result)
   and [read-status diagnostic](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_CHRDET_ERRORS.md#retained-physical-result)
   are now preserved. The latter reached controller start, but its host receiver
   did not arm. The later
   [bounded export session](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_CHRDET_ERRORS.md#second-session-physical-result)
   had collectors armed before physical selection but recorded an early host
   branch and no device-controller start. The
   [selected role trace](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_ROLE_TRACE.md)
   narrows that branch to internal ID-pin state. Its two later physical boots
   took the device branch and recorded no instrumented role writer; the active
   writer of the earlier host state remains unidentified. The second boot
   established an attributed USB Ethernet route, one acknowledged 64 KiB
   export and normal Gemian return. The exported region was entirely zero and
   lacked the capture header, so it contains no Wi-Fi producer evidence. The
   [linked-producer audit](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/results/cycle-producer-boundary.json)
   confirms the kernel entry points exist; the selected export-only startup
   never invoked the detector capture path. The
   [selected AP-DMA audit](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/results/shared-resource-boundary.json)
   narrows channel overlap but finds a shared clock and unchecked WLAN HIF
   clock/mapping admission. The compile-only
   [HIF admission patch](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/HIF_ADMISSION.md)
   now links and refuses missing mapping or clock acquisition before native
   SDIO open. The [DMA clock refusal](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/DMA_CLOCK_ADMISSION.md)
   also links and returns before HIF command setup if the selected CCF clock
   enable fails. The [failed-probe PALDO balance](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/PALDO_FAILURE_BALANCE.md)
   links and exercises cleanup or retained refusal after an ordinary WLAN
   probe error; it does not settle shared rail ownership. The
   [AP-DMA alias audit](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/results/ap-dma-alias-audit.json)
   corrects the first I2C channel to `0x11000100` and finds a selected CMDQ
   mapping of the whole AP-DMA block. Dynamic CMDQ access, shared ownership
   and a complete failure lifetime remain. A bounded
   [CMDQ-off build attempt](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/CMDQ_ISOLATION.md)
   compiled after a one-line SMI fix but failed final link across built-in
   display, power and imaging clients; the successful 56-patch build inputs
   were restored. CMDQ cannot be excluded by configuration alone.
   A [headless submission gate](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/CMDQ_SUBMISSION_GATE.md)
   now links and refuses new CMDQ tasks before dispatch in the captured
   build. Its [first boot-only host window](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/results/cmdq-gate-boot-window-1.json)
   saw no export gadget or verified Gemian return. A
   [later physical selection](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/results/cmdq-gate-boot-window-2.json)
   proved exact mainline userspace, preflight and normal Gemian return. Its
   retained USB diagnostic selected the ID-pin host branch before a cable
   sample or device-controller start; export still failed. A
   [source-pinned voltage boot](../experiments/2026-09-07-mt6797-wifi-observer-feasibility/USB_ID_VOLTAGE.md)
   then measured the existing getter at 28 mV during that decision and again
   returned normally to Gemian. This explains the selected software branch,
   but not the low reading's physical cause or ADC readiness. The returned
   Gemian boot reported USB and AC offline; independent port-power evidence is
   still needed before changing USB role policy. CMDQ task execution, GCE
   hardware-idle admission and radio behavior remain unverified.
   Resolve those paths, then package and validate the `cycle` action with
   shared ownership, post-reset capture preservation
   and a finite radio-effect protocol before another physical Wi-Fi test. No
   role override, detection-policy change or weakened CPU check is supported
   by the evidence.
   Exit order must not be inferred by reversing initialization, and the vendor
   WMT ioctl must not be copied merely to run the retained loader.
3. **Preserve the bounded eMMC result:** the [closed session](../experiments/2026-09-05-owner-away-experiment-preparation/emmc/PAUSE_SESSION_PREPARATION.json)
   completed its one 16 MiB read, matched the installed image, and preserved the
   controller log with zero targeted errors. Changed-ID Gemian return was
   confirmed separately; the native recovery transport remains inconclusive
   and the aggregate remains incomplete. Its read/log budgets are consumed.
   Do not execute the superseded preparation handoffs or repeat this read as
   pending work. Broader storage reliability and persistent-root writes require
   a distinct measurement and their own admission.

The [twenty-step keyboard capture](../experiments/2026-09-05-owner-away-experiment-preparation/keyboard/COVERAGE_TEST.md#attended-result)
remains accepted for its stated scope. Its release-order limitation and the
[A53 focused-mode refusal](../experiments/2026-09-09-standard-kernel-package/results/a53-keyboard-method-trial-20260925.json)
remain recorded. One [focused A53 reader image](../experiments/2026-09-27-a53-focused-keyboard/README.md#device-deployment)
was installed with full readback and clean shutdown. Its
[physical observation](../experiments/2026-09-27-a53-focused-keyboard/results/runtime-1.json)
reached both input windows but captured no key events or console bytes; no
physical-key pass or hardware failure follows. Complete logs and changed-boot
Gemian return were preserved. The session is closed, and no further A53
keyboard test is selected ahead of Wi-Fi. Items with unverified
candidate or protocol inputs remain planned/preparing. Conditional items have
frozen validated inputs and await only an explicit runtime result predicate.
The cumulative ten-cold-boot release gate remains distinct; schedule
its attributable cycles around useful compatible tests without silently changing
inputs or increasing action budgets. Upstream work consumes no device slot.

The [preparation record](../experiments/2026-09-05-owner-away-experiment-preparation/README.md)
owns these initial hypotheses and missing evidence. The
[queue inventory](../project/experiment-queue.json) reports readiness and links
to experiment-owned [session packets](../project/DEVICE_SESSION.md); it contains
no executable action and does not choose priority independently of this roadmap.

### One device queue

The named Gemini is a serial resource. Before changing its session, identify its
custodian and obtain the current experiment's handoff; a completed observation
is not permission to reclaim an uninspected device. Completed V4 observations
must not be repeated merely because the owner returns.

An item is **ready** only when its exact candidate and protocol are frozen,
applicable build/package/container and shell/refusal checks pass, dependency
predicates are satisfied, and capture/classification/recovery are prepared.
**Conditional** means offline preparation is complete but a named runtime
predicate remains. **Preparing** and **planned** are not ready for an owner
session. Only an installed, readback-verified selected item can be marked
**waiting-owner-boot**; record that deployment in its experiment.

One custodian selects one ready item, using the roadmap order and actual
readiness. The existing guarded boot2 installation and clean-shutdown policy
applies, including its standing authorization when the known-good OS is
reachable. Stage only that selected candidate; never replace a staged candidate
with another queued image before its result or explicit supersession is recorded.
Physical boot2 selection remains the owner's action for each required cycle.

Centralize physical-start requests in the integration task recorded in the
workstream registry. Send one **Ready for boot2 — action needed** session card
after the selected image has a verified installation/readback and clean-shutdown
receipt, with queue state **waiting-owner-boot**. Include physical steps,
expected screen/USB behavior, required interaction and stop/recovery conditions.
Link the owning session packet and avoid repeating an unchanged request. A
preparation or compile result cannot substitute for that deployment receipt.

When the owner returns, present one session card: the exact physical action,
expected screen/USB behavior, approximate owner time if known, any key presses
or cable changes, and stop/recovery instructions. Use the already prepared
capture and classifier once identity and admission checks pass. Record pass,
failure or inconclusive evidence and reconsider dependencies before selecting
the next item. A queue is not a blind batch runner or permission to reboot.

If the owner becomes unavailable mid-session, stop at the protocol's defined
safe boundary; do not hold a stress/load test open or restart a consumed observer.
Release the worker to offline work. Notify about a new actionable session or
changed requirement, not repeated unchanged requests for physical selection.

Invalidate readiness when relevant candidate/protocol inputs change, required
results are withdrawn, an observation budget is consumed, or new evidence
supersedes the hypothesis. Preserve old receipts. A failed prerequisite blocks
its dependents while independent ready items remain available. Recheck physical
identity, partition state, power and recovery at deployment time; preparation
cannot freeze those observations.

One boot may serve several workstreams only when the exact relevant inputs,
measurement interference, ordering and combined finite budget were reviewed in
advance. Keep the per-test evidence attributable, abort affected dependents on
failure, and never bundle multiple boot-critical changes merely to save a cycle.

### Progress measures and review cadence

Regular device validation is an explicit owner priority. At each integration
review, assess the next useful hardware regression and advance its preparation;
after a meaningful hardware-facing change, run the admitted device protocol at
the next available owner session before claiming runtime support. Record the
exact inputs, real-device result and any issue it exposed. Host tests and
compilation do not replace this check. Use the single custodian and existing
session budgets, and continue independent offline work while physical selection
is unavailable. A cadence requirement does not authorize blind repeat boots or
reusing a consumed observation budget.

At each integration review, record: accepted/released upstream topics, local
topics awaiting review, regression passes on exact inputs, unresolved shared
blockers, and why each consumed boot changed a decision. Track rejected and
inconclusive outcomes too. Patch, build and document counts are not progress
measures. Review priorities weekly or when a decisive result changes a
workstream's dependencies. Scheduled continuations are managed separately in
the app and use this roadmap; the document itself is not a scheduler.

## After Wi-Fi: remaining driver gaps

This section orders the non-Wi-Fi gaps. It was rewritten on 2026-10-04 from
the eleven source-only reverse-engineering records under
`experiments/2026-10-04-gemini-*-re/` (charging, display, PMIC basics,
Bluetooth, GPS, lid/microSD/USB, audio, sensors, GPU, cellular, camera); each
record owns its facts (F) and ranked hypotheses (H), and this section only
orders them. It does not change the Wi-Fi order above and admits no device
test; each runtime step still needs its own reviewed experiment. Steps marked
**(local)** need Julien's machine, because Buildbox and the device are not
reachable from cloud sessions. Everything else is offline patch, schema or
documentation work that can start now.

Ranking rule, unchanged in spirit: first the item that protects the battery
and the lab, then the shared foundations (PMIC interrupt path, CONSYS task
demultiplexer, I2C1), then the two usability blockers (charging, native
display), then the blocks that ride on finished foundations, grouped so that
one boot or one Gemian session answers several records at once.

### Safety first

1. **Charger regulation voltage discrepancy.** The public Gemian source
   writes a fixed `VREG` of `0x24` (4.416 V) while the 2026-07-14 live capture
   read back 4.336 V ([charging F11, H10](../experiments/2026-10-04-gemini-charging-re/README.md#part-2-hypotheses-ranked-by-value-per-device-minute)).
   If the running binary matches the public source, the stock kernel is
   over-charging a 4.35 V cell. One read-only Gemian kernel-log check of the
   periodic `[bq25890 reg@]` dump (REG06) decides it **(local)** and should be
   the first item of the next Gemian session. The
   [passive successor](../experiments/2026-10-04-gemian-session-a/README.md)
   found selector `0x1f` / 4.336 V selection logs, no REG06 dump, a zero
   high-voltage DT flag and an 800 mA AC policy cell. The
   [matched-boot binary audit](../experiments/2026-10-04-gemian-session-a/CHARGER_CV_BINARY.md)
   proves computed-only logging followed by fixed `0x24` (4.416 V nominal)
   VREG write requests; errors are ignored and hardware readback remains
   unresolved. Review a bounded attributable REG06 read next. Until then, avoid long unattended
   charge sessions under Gemian. On mainline, the first charger observation
   is a userspace read-only register dump with no charger node bound. The
   upstream driver ignores DT limits under `linux,read-back-settings` and
   enables charging under `linux,skip-reset`, so binding it is a separate,
   reviewed charge-policy stage that must program and verify `VREG` 4.2 V and
   `IINLIM` 500 mA before charging starts. Pump Express, OTG boost and VBUS
   role changes stay out (charging H3, H4, H9).
2. **Battery floor during mainline sessions.** Mainline has no low-battery
   protection and relies on the PMIC hardware UVLO alone
   ([PMIC H10](../experiments/2026-10-04-gemini-pmic-basics-re/README.md#part-2-hypotheses-ranked-by-value-per-device-minute)).
   Keep mainline sessions on external power or above the vendor's 3.4 V first
   threshold until the gauge driver (step 3) exists. A mainline power-off with
   the cable attached re-enters LK charging mode and looks like a reboot
   (PMIC H11); judge power-off results with the cable detached.

### Shared dependencies and missing mainline pieces

| Shared piece | Used by | Status after the records | Open item |
| --- | --- | --- | --- |
| MT6351 MFD interrupt domain (0008–0015, 0062) | Power key (EINT176), RTC alarm (IRQ 9), `CHRDET` (46) for cable and USB device-port role, ACCDET jack detection (12/13) | Never exercised on mainline; every record that needs a PMIC interrupt names it | First proof is the power key (PMIC H1); it validates the path for charging H2, audio H5 and lid/USB H2 at once |
| MT6351 regulator constraints | Dropping `regulator_ignore_unused`; VCORE/VSRAM_PROC hardware control, VDRAM, VS1/VS2, modem bucks, VSIM1/2 | Vendor constraint set decoded (PMIC F8–F10, cellular H8) | Offline: write `always-on`/`boot-on` set and keep VCORE off-limits (PMIC H7); drop the flag only in a later reviewed boot |
| Power-off and restart | Every boot's clean shutdown | Restart proven (TOPRGU). Vendor power-off is an RTC BBPU write that bypasses PSCI; mainline PSCI `SYSTEM_OFF` is untested and probably wrong | New: `mt6351-pwrc` MFD cell plus a small `mt6323-poweroff` extension (PMIC H2) |
| CONSYS/WMT owner (BTIF, STP, common init) | Wi-Fi, Bluetooth, GNSS, FM | Drafted 2026-10-04: AFE stage before MCU release (0101–0102); task framing, shared sequence/ACK and task routing (0103–0106). No task-0/2 client wired; no hardware result | 0104+0105 consolidated; wire one task-0 binding for boot C3; executor owns AFE unconditionally |
| Clock and power-domain ownership (`clk_ignore_unused`) | Retained simplefb, display PWM, Wi-Fi, GPU | Display H2 gives the first removal path: a `simple-framebuffer` node carrying the MM domain and root clocks | Missing clocks: `CLK_MM_DSI0_INTERFACE_CLOCK` gate (display F19, H7); `mfg_52m_sel` parent and `INFRA_MFG_VCG` for the GPU (GPU H5) |
| Bus protection and resets | MFG (GPU), MD1 (modem) | Local MFG domain (0047) has no `bus_prot_mask`; vendor asserts INFRA_TOPAXI bits 21/23 and writes GPU SRAM LDO words `0x10001fbc–0xfe4`; TOPRGU `MFG_RST` is not exposed (GPU H1, H2, H4). MD1 domain is absent from mainline (cellular H2) | Offline patches to 0047 and `mtk_wdt`; two Gemian reads decide the LDO words |
| I2C1 (disabled in the board DT) | Panel bias at `0x3e`, BMI160 `0x69`, STK3x1x `0x48`, candidate MMC35240 `0x30` | Pin pair unconfirmed, probably `SCL1_0/SDA1_0` GPIO55/56 (sensors H8) | One Gemian pinmux read, then one boot serves display bias and all sensors |
| EINT controller (0005/0006) | Lid (EINT5), card detect (EINT6), ALS/PS (EINT11), IMU candidate (EINT4), FUSB301 ID (EINT3), toggle (EINT16) | No dedicated consumer accepted yet | Lid (patch 0074 as-is) is the cheapest first consumer and can ride any boot |
| Gauge and ADC | Battery telemetry, temperature, low-battery threshold | Vendor gauge is the MT6351 FGADC coulomb counter plus AUXADC; mainline has no MT6351 ADC or gauge driver (charging F15–F18, F21) | New small IIO driver modelled on MT6357–MT6373 with MT6351 offsets (charging H5) |

### Corrected assumptions

- **Panel identity is settled, not contradictory.** The loader's NT36672 probe
  succeeds only on a real ID read while the SSD2092 probe always succeeds, so
  the live `nt36672` name is a positive identification pending one LK-log read
  (display F2–F4, H1). The SSD2092 variant question remains for other units.
- **Display clock.** The vendor lane rate is 880 Mbit/s; the retained 435 MHz
  is integer truncation and patch 0043's 138.839 MHz mode clock implies
  833 Mbit/s. The mode clock should become 146.667 MHz (display H3).
- **Charger interrupt.** The vendor never uses the BQ25896 `INT` pin; cable
  events come from PMIC `CHRDET`. The upstream driver requires an IRQ at probe,
  so either a real EINT is found or a small driver change is needed
  (charging H1, H2).
- **Power key and reset.** Public Gemian delivers `KEY_ESC`; mainline should
  use `KEY_POWER`. Mainline `mtk-pmic-keys` always writes the reset register,
  so the key node must state the long-press policy explicitly; one register
  read (`TOP_RST_MISC`) decides the value (PMIC F11–F13, H3).
- **RTC reload** is a vendor convention shared with MT6323, which mainline
  already serves; considered answered pending one read test (PMIC H5).
- **Bluetooth may not need common init to start (hypothesis).** The HCI
  parser lives in ROM, so BT-on, HCI Reset and version/address reads may run
  on the already negotiated full-mode STP session before ROM patches or
  calibration (Bluetooth H1, H2, medium confidence). Boot C3 decides it, with
  the AFE stage present.
  `btmtkuart` contributes framing and `btmtk_set_bdaddr` only.
- **GNSS has a userspace cost.** The kernel shape holds (one function-control
  command, GPIO69, a `gnss` device over task 2), but the stock position engine
  is proprietary; whether the receiver speaks NMEA or binary MNL decides if
  mainline GNSS ends at raw frames or at positions (GPS H4, H5).
- **Speaker path.** The stock path is MT6351 line-out plus pulse-enabled
  GPIO243/244 amplifiers; the `0x31` MAX98926 node is unbound in the stock
  kernel. Jack detection is PMIC ACCDET, no AP EINT (audio H1, H2, H5).
- **Sensors.** No controlled rail, no vendor IMU interrupt (GPIO65 is the only
  candidate), ALS/PS on GPIO88, STK `0x11` is a naming problem that
  `sensortek,stk3311` already drives, and the magnetometer is reopened because
  the vendor's unbuilt driver is the mainline `mmc35240` register family
  (sensors H1–H6).
- **GPU.** The missing pieces are specific and small (bus protection, LDO
  words, `mfg_52m` parent, optional reset, regulator timing), the safe first
  operating point is 520 MHz at 1.000 V, and the GPU does not depend on the
  PMIC step (GPU H1–H5, H8).
- **Camera.** The front sensor matches upstream `hi556`; the irreducible
  blocker is the SENINF/CSI-2 programming held in the proprietary HAL
  (camera H1, H4, H5). **Cellular:** the AP-side bring-up is a short register
  sequence over resources mainline mostly names, but no redistributable
  CLDMA/CCCI transport exists anywhere (cellular H1–H4).

### Ordered gaps

1. **PMIC foundation (offline now, one boot).** Patches: `mediatek,mt6351-keys`
   child with `KEY_POWER` and an explicit long-press policy after integrating
   the reviewed key fixes. Preserve PSCI power-off for C1; an `mt6351-pwrc`
   cell and `mt6323-poweroff` extension wait for that baseline to fail.
   Regulator constraint set from PMIC H7 while keeping `regulator_ignore_unused`
   and logging `regulator_summary`; a probe-time read of the ten
   decision-changing PMIC registers (PMIC H8). Needs the `TOP_RST_MISC` Gemian
   read first (PMIC H3, H4). One combined boot **(local)** then covers key
   events, RTC read and alarm, and a power-off attempt with the charger
   detached (PMIC H1, H2a, H5, H6). This boot also carries step 2's `CHRDET`
   count and step 5's lid test.
   Records: [PMIC basics](../experiments/2026-10-04-gemini-pmic-basics-re/README.md);
   earlier topics [MFD](../experiments/2026-09-08-mt6351-mfd-upstream-preparation/README.md),
   [keys](../experiments/2026-09-08-mt6351-keys-preparation/RESET_POLICY.md).
2. **Battery and charging (first usability blocker).** Patches: disabled
   BQ25896 node at I2C0 `0x6b` with the conservative set from charging H3
   (4.2 V first, `ICHG` 512 mA, `IINLIM` 500 mA, `IPRECHG`/`ITERM` 128 mA,
   `SYS_MIN` 3.5 V, `ti,use-ilim-pin`, no Pump Express), `linux,skip-reset`
   and `linux,read-back-settings`, interrupt per charging H1 or a small
   `bq25890` change to accept `CHRDET` plus polling; the pending
   [IRQ preflight fix](../experiments/2026-09-12-bq25890-irq-preflight/README.md).
   Correction (2026-10-04 review): read-back mode skips these DT limits and
   skip-reset enables charging at probe, so the node is bound only in a
   reviewed charge-policy stage that programs and verifies the limits first.
   Device order: Gemian reads (VREG dump, adapter type and PE+ log, live
   `bat_meter` DT; charging H10, H6, H7) **(local)**; `CHRDET` count in the
   step 1 boot (H2); a charger probe boot that dumps REG00–REG14 first and
   reads telemetry unplugged and plugged (H3, H8, H4) **(local)**; a reviewed
   charging enable after that.
3. **Gauge and ADC driver (offline, after step 2's first read).** New MT6351
   AUXADC/FGADC IIO driver (channels BATSNS/ISENSE/VCDT/BATON, `FGADC_CON0`),
   `simple-battery` with design voltages only, and a low-battery threshold
   (charging H5, PMIC H10). First boot compares BATSNS with the charger ADC.
4. **Native display (second usability blocker).** Offline, in dependency order
   ([display Part 3](../experiments/2026-10-04-gemini-display-re/README.md#part-3-what-mainline-needs-beyond-the-retained-simplefb)):
   (a) `simple-framebuffer` node with MM power domain and root clocks so
   `clk_ignore_unused` can go (H2); (b) add the `DSI0_INTERFACE_CLOCK` gate to
   `clk-mt6797-mm` before patch 0040 can probe (H7); (c) rebase and split
   0028–0044 per the [architecture refresh](../experiments/2026-09-07-mt6797-display-upstream-architecture/README.md),
   OF-graph for 0041, display PWM as an MT6797 variant with one `main` clock
   plus the MM domain and a `pwm-backlight` (H8); (d) board nodes: TPS65132
   bias at I2C1 `0x3e` with `outp`/`outn` 5.5 V and enable GPIOs 60/251
   (H5), panel `planet,gemini-pda-nt36672` with `reset-gpios` GPIO180 (H4),
   mode clock 146.667 MHz (H3), no `vddi` (H6), portrait rotation; (e) an
   MT6797 IOMMU/SMI decision for the first OVL/RDMA path. Device order
   **(local)**: Gemian reads of the LK log, bias registers, VIO18/LDO states
   and pin 180 across a display cycle (H1, H5, H6, H4a); simplefb adoption
   boot (H2); backlight boot under simplefb (H8); panel bring-up with a `0xDB`/
   `0xF4` read before any init table (H1, H3, H4, H9). Touch follows the panel
   (H10). Keep the console on simplefb meanwhile.
5. **Small standalone wins (ride other boots).** Lid: enable patch 0074 as-is,
   one attended close/open, no `wakeup-source` (lid H1, H8). microSD: add
   `ldo-vmch`/`ldo-vmc` regulator nodes and an `&mmc1` node (GPIO67
   active-high card detect, `no-1-8-v`, ≤ 50 MHz, pinmux-only pads), read PMIC
   trim fields `0xACE`/`0xAE2` on Gemian first, never port the trim arithmetic
   (H3, H9). USB: device-port role from `CHRDET` through a small `extcon`/
   `usb-conn` consumer so forced B-session (0077) becomes conditional (H2);
   host-port VBUS is GPIO94, whose source a USB meter decides before any
   `regulator-fixed` toggle (H4); FUSB301A ID on GPIO64 as `id-gpios` (H5);
   the toggle on GPIO93 needs an owner observation (H7).
   Record: [lid/microSD/USB](../experiments/2026-10-04-gemini-lid-microsd-usb-re/README.md),
   [microSD contract](../experiments/2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md),
   [VBUS record](../experiments/2026-09-08-usb-vbus-ownership/README.md).
6. **Bluetooth (may start before common init is complete).** Offline: STP task
   framing, shared link state and routing are drafted (0103–0106); next is one
   task-0 binding for boot C3, and only after H1 passes a small
   `hci_dev` over task 0 reusing `btmtk_set_bdaddr` and the H:4 receive helper,
   no vendor sleep parameters at first (Bluetooth H4, H5); `mtk-btcvsd` node
   later (H9). Device: one Gemian read of the `hci0` address decides whether
   mainline must supply a `local-bd-address` (H6) **(local)**; one boot on the
   negotiated full-mode session with VCN33-BT at 3.3 V, function-control BT-on,
   HCI Reset, version and BD_ADDR reads, with the AFE resource present and the
   version baseline and full-mode WMT query/negotiation control (H1–H3, H5)
   **(local)**; the zero-CRC frame and `0xfc6f` probes (H4) only after Reset passes. Coexistence and radio trims come later (H7, H10).
   Record: [Bluetooth](../experiments/2026-10-04-gemini-bluetooth-re/README.md).
7. **GNSS (after proven common init).** The AFE register block is drafted
   in the common-init owner (0101–0102, GPS H2). Offline now: design the
   `gnss` device over task 2 with the GPIO69 pinctrl state and VCN28 from the common power-on
   (H1, H3, H6). Device: the Gemian trace of the first `/dev/stpgps` bytes in
   one stock GNSS session (H4) must precede any mainline GNSS boot, because it
   decides NMEA versus binary MNL (H5); then one boot sending GPS function-on
   and counting task-2 frames (H1) **(local)**. FM stays last.
   Record: [GPS](../experiments/2026-10-04-gemini-gps-re/README.md).
8. **Sensors (first I2C1 boot, shared with display bias).** Patches: enable
   I2C1 on the confirmed pin pair (H8); BMI160 node at `0x69` as in patch 0052
   with the direction-7 mount matrix and no interrupt (H1); `sensortek,stk3311`
   at `0x48` (H4); then `interrupts` GPIO65/EINT4 for the IMU (H2) and
   GPIO88/EINT11 level-low for proximity (H5). Device: Gemian pinmux read of
   GPIO53–60 first; one boot reads accel/gyro/ALS/PS and performs four single
   ID reads (`0x30` reg `0x20`, `0x77` reg `0xD0`, `0x5f` reg `0x0F`) that close
   the magnetometer, barometer and humidity questions (H6, H7) **(local)**. No
   upstream ID-table change for STK `0x11` until the marketed part name is
   known. Record: [sensors](../experiments/2026-10-04-gemini-sensors-re/README.md).
9. **Audio (after step 1's `mt6351-sound` child).** Offline: AFE node, MT6351
   codec child and `mt6797-mt6351` card routed to headphones only, line-out
   muted, amplifier GPIOs untouched (H3); a small MT6351 ACCDET driver modelled
   on `mt6359-accdet` with the F10/F12 parameters (H5); the AFE YAML topic.
   Device: Gemian reads of GPIO243/244 during a low-volume tone, an `0x31`
   probe, ACCDET interrupt counts across a headset plug and the live audio DT
   (H1, H2, H5, H6, H7) **(local)**; then a −40 dB headphone tone and an AIN0
   capture boot (H3, H4) **(local)**. An external-amplifier widget or MAX98926
   node comes only after H1/H2; if H2 wins, an MT6797 I2S DAI becomes its own
   topic. Record: [audio](../experiments/2026-10-04-gemini-audio-re/README.md).
10. **GPU (after display, before sustained load needs thermal).** Patches:
    `bus_prot_mask = BIT(21) | BIT(23)` on the MFG domain in 0047 (H1); an
    infracfg write of the GPU SRAM LDO words before MFG powers on if the
    Gemian read shows reset values (H2); `assigned-clock-parents` for
    `mfg_52m_sel` and `clocks = core (MFG_BG3D), bus (INFRA_MFG_VCG)` (H5);
    MT6797 `mtk_wdt` reset entry and `resets = <&watchdog 2>` (H4); RT5735
    `enable_time` 350 µs and `ramp_delay` (H8); a named profile (not
    `gemini.fragment`) enabling `DRM`, `DRM_PANFROST`, `mfgsys`, `i2c7` and the
    RT5735 fixed at 1.000 V. Device: Gemian reads of the LDO words, `CLK_CFG`
    bits for `mfg_52m_sel` and the decoded devinfo speed bin (H2a, H5, H7)
    **(local)**; one probe-and-power-cycle boot at a fixed 520 MHz with a
    serial console or pstore (H3) **(local)**. DVFS is clock flags plus the
    uncalibrated type-12 table below 780 MHz (H6), after H3 and the thermal
    step (H9). Record: [GPU](../experiments/2026-10-04-gemini-gpu-re/README.md).
11. **Cellular and cameras (feasibility only).** Cellular: a read-only
    observation boot printing the LK `ccci` tags, SPM MD1 status at both offset
    pairs and `MD1_CFG_BOOT_STATS0/1` (cellular H1) **(local)**; a Gemian
    `ccci_dump` read of the CLDMA queue-0 ring (H5) and SIM pinmux/LDO states
    (H8). MD1 domain, PLL replay and boot-vector release (H2–H4) each need their
    own reviewed experiment, and H4 is the first to run proprietary modem code.
    Camera: Gemian log read of the SLS sensor-ID line and `camtg_sel` clock
    summary (camera H1a, H2a); then a mainline `hi556` probe boot reading one
    register with an OF match, 24 MHz PLL entry and PDN GPIO (H1b) **(local)**;
    the receiver path waits for the MT8365 SENINF/CAMSV comparison (H4) and the
    bounded register-window capture during a stock stream (H5).
    Records: [cellular](../experiments/2026-10-04-gemini-cellular-re/README.md),
    [camera](../experiments/2026-10-04-gemini-camera-re/README.md).

### Device tests, grouped by session type

Deduplicated from the eleven records so Julien can batch them. Every test is
bounded and read-only in intent unless marked; none is admitted by this list
and each still needs its reviewed experiment with identity checks.

**A. One read-only Gemian session (known-good LAN SSH).** Order by value.
Take the log, live DT and sysfs items (1, 3, 5, 9, 13's ring) first. Items 7
and 12 change hardware state (OTG attach, slider, camera open) and belong
with group B. PMIC, I2C and MMIO reads (2, 4, 6, 8, 10, 11, 13's pinmux)
each need a reviewed access path; read the AFE window (11) only with CONSYS
powered:

1. Kernel-log `[bq25890 reg@]` dump, REG06 `VREG` (charging H10, safety).
2. `TOP_RST_MISC` `0x2b6` through the bounded `pmic_access` path, read twice
   with another register between (PMIC H3, H4).
3. LK log lines for the NT36672 ID and `we will use lcm` (display H1).
4. I2C1 `0x3e` registers `0x00`, `0x01`, `0x03`, `0xFF` (display H5); live
   pinmux of GPIO53–60 (sensors H8).
5. `hciconfig hci0` / `btmgmt info`, `BT.cfg`, `[HCI-STP]` log (Bluetooth H6).
6. PMIC `0xACE`/`0xAE2` bits 4:0 (microSD H3); GPIO69 state (GPS H6).
7. `/proc/interrupts` `iddig_eint` count across one OTG-adapter attach
   (USB H6); EINT16 count and `switch` state across one slider flip (toggle
   H7).
8. `i2cdetect -y -r 0` restricted to `0x31`, and register `0xFF` if it ACKs
   (audio H1b, H2); GPIO234/235 levels idle (audio H6).
9. Live DT nodes: `bat_meter` and `battery` (charging H7), audio section and
   `accdet` (audio H7), `i2c@11010000` children (GPU H7), `chosen/atag,devinfo`
   words 8, 22, 61 and EEM words, decoded values only (GPU H7).
10. INFRACFG `0x10001fbc–0x10001fe4` with the GPU idle (GPU H2a); `CLK_CFG`
    `0x10000104` bits 2:1 and `clk_summary` for `mfg_52m_sel` (GPU H5).
11. AFE window `0x180b6000+0x100`, 64 words (GPS H2); charger battery log with
    the bundled adapter attached (charging H6).
12. Camera: SLS `ReadOut sensor id` log line after one camera-app open,
    `camtg_sel` in `clk_summary`, `SUBAF` log errors (camera H1a, H2a, H6).
13. Cellular: `/proc/ccci_dump` queue-0 ring (H5); SIM pinmux GPIO126–128/
    155–157 and VSIM1/2 enable bits with and without a SIM (H8).

**B. Attended hardware actions inside that Gemian session** (owner at the
device; each is one short action):

- Display off/on cycle while sampling pin 180 state and MT6351 LDO enable
  states (display H4a, H6, H10).
- Low-volume tone through the stock stack while sampling GPIO243/244 (audio
  H1a); headset plug/unplug while counting ACCDET sources 12/13 and reading
  `switch`/key events (audio H5); record from the headset mic while sampling
  GPIO234/235 (audio H6).
- One stock GNSS session capturing lengths and first 16 bytes of the first
  `/dev/stpgps` writes and reads (GPS H4); this decides the GNSS plan.
- USB meter on the host port with a known hub attached and with nothing
  attached, GPIO94 low (USB H4a); no device write.
- Optional: short GPU load while re-reading `0x10001fbc` (GPU H2a).

**C. Mainline boots** (each a reviewed experiment with its own candidate):

1. **PMIC, charging and lid packet.** Key node, RTC node, lid node (0074),
   MT6351 irqchip visible in `/proc/interrupts`, the ten-register PMIC read,
   `TOP_RST_MISC` read before any write. Attended: one power-key press, one lid
   close/open, one cable plug/unplug (`CHRDET`, `VBATON_UNDET`), `rtcwake` 10 s,
   then the existing PSCI `poweroff` with the charger detached; `mt6351-pwrc`
   only if that fails (PMIC H1, H4, H5, H6, H8, H2a; charging H2; lid H1;
   USB H2). C2a rides here.
2. **Charger.** (a) Read-only REG00–REG14 dump from userspace with no charger
   node bound, unplugged and plugged (charging H3, H8, H4), riding on C1.
   (b) Later, a named profile binding the driver only after the reviewed
   sequence programs and verifies the conservative limits; telemetry, gadget
   idle then enumerated. Gauge driver boot comparing BATSNS with the charger
   ADC follows (H5).
3. **Bluetooth on the negotiated session.** Candidate on the squashed
   0101–0106 chain with the AFE resource present. Controls first: repeat the
   checked version baseline and the previously validated full-mode WMT
   query/negotiation; stop on any regression. Then VCN33-BT on, BT-on,
   HCI Reset, version and BD_ADDR, second Reset after 2 s, BT off (Bluetooth
   H1–H3, H5). The zero-CRC frame and `0xfc6f` probe (H4) wait until Reset
   has passed and their effects are reviewed.
4. **Display adoption and backlight.** simplefb node with MM domain and
   `clk_ignore_unused` removed (display H2); then display PWM plus
   `pwm-backlight` under simplefb with `CON_0`/`CON_1` readback (H8).
5. **I2C1 bus boot.** BMI160, STK3311, bias chip if not read on Gemian, four
   single ID reads at `0x30`/`0x77`/`0x5f`, device flat and on each edge
   (sensors H1, H4, H6, H7; display H5 fallback). Then interrupts (H2, H5).
6. **microSD and USB host.** `&mmc1` with VMCH/VMC, trim and IOCFG_B fields
   read at entry, one known file read (microSD H3, H9); GPIO94
   `regulator-fixed` toggled once with the meter on the port and charger
   unplugged, GPIO64 and FUSB301 status with and without a partner
   (USB H4b, H5).
7. **Audio card.** Headphone-only card, −40 dB tone, AIN0 then AIN2 capture,
   `AUDDEC_ANA_CON0` readback (audio H3, H4, H8).
8. **Panel bring-up.** `0xDB`/`0xF4` DCS read before any init table, PCW
   readback and vblank-derived refresh, two DPMS cycles reading `0x0A`
   (display H1, H3, H4b, H9). Touch probe at `0x62` and `0x53` after.
9. **GPU probe.** Fixed 520 MHz at 1.000 V, `clk_summary` before probe,
   INFRA_TOPAXI bits 21/23 and LDO words read, probe line, one runtime
   suspend/resume cycle; stop on any SCPSYS or TOPAXI timeout (GPU H1–H3).
10. **GNSS first frames** after proven common init (GPS H1, H3).
11. **Cellular observation** (tags, SPM status, boot status; cellular H1) and
    **camera probe** (`hi556` one-register read, I2C3; camera H1b, H6).

Boots 1–3 need nothing from the Wi-Fi order; the installed version-read
candidate has been consumed successfully; boot 4 removes a global flag and should precede
5–9; boot 10 waits for common init. Current order after review: version
read, Gemian A, C1 (with C2a), C3, Wi-Fi common-init boot, C2b.

### Leads from owner-held reference documents

The owner keeps a local set of reference documents that is not in Git: the
public 96Boards X20 (MT6797) functional specification, schematic and BOM,
vendor datasheets (BQ25896, TPS65132, FUSB301A, DA9213/14/15, AW9523B),
2017 MT6351 mailing-list patches, and third-party Gemini notes (Gemian wiki
and bsg100). The SoC and X20 material is marked confidential and most
datasheets have no redistribution grant, so cite them by name only. They are
leads to check against this unit, not facts. Items the 2026-10-04 records
settled from source are dropped here; what remains:

- **Two panel/touch variants are likely.** bsg100 reports I2C4 `0x53`
  answering with nothing at `0x62` on its unit, while the retained 2019
  `novatek_ts_fw.bin` (see the [firmware boundary](hardware/firmware.md)) is a
  Novatek NT36xxx-layout image. Make the touch probe read both addresses with
  touch reset released, and plan the board description for both variants.
- **Panel bias.** The TPS65132 datasheet gives fixed address `0x3e`, VPOS/VNEG
  at `0x00`/`0x01` and a ±5.4 V reset value, consistent with display H5.
- **Charger.** bsg100 reports boost enable on GPIO107 in addition to
  `OTG_CONFIG`; the BQ25896 watchdog reverts settings unless serviced or
  disabled (charging H8); the interrupt is an active-low 256 µs pulse
  (charging H1).
- **Sensors.** The marketed name of the STK `0x11` part may be in the Planet
  BOM notes; it is the discriminator for an upstream ID-table change
  (sensors H4).
- **USB.** GPIO93 (EINT16) has IDDIG as an alternate function; the records
  instead find the toggle there (lid/USB H7). FUSB301A at `0x25` implies its
  address pin is strapped high on both buses.
- **Connectivity.** MT6631 integrates FM; VCN18 feeds Wi-Fi/BT and GPS 1.8 V,
  VCN33 the Wi-Fi/BT 3.3 V supply, VCN28 the FM supply. The retained
  `WMT_SOC.cfg` holds four keys (shared antenna, no firmware GPS LNA pin,
  `co_clock_flag=0`) and no voltage, trim or calibration setting; GPIO69 LNA
  control belongs to the host (GPS H6).
- **GPU.** If the documents cover INFRACFG `0x10001fbc–0xfe4` or the
  `0x180b6000` AFE block, they settle GPU H2 and GPS H2 without a device read.
- **Board differences.** X20 addresses do not carry over: its `0x6b` is an
  MT6313 buck, while the Gemini has a BQ25896 there.

The [workstream registry](../project/workstreams.json) keeps owners; this
section only orders the work. Start now with the offline items of steps 1, 2
and 6 and the Gemian session A; the installed version-read candidate is consumed,
so complete the baseline before scheduling boot C1 (see the 2026-10-04 review under Current plan).

## A53 development-system release gate

A53 integration proceeds independently of complete A72 suspend support. Start
from a named runtime-proven serviceability candidate and audit its required
kernel/DT/config inputs before defining a new frozen manifest profile. Do not
silently promote an old experimental profile or the moving `full` default.

The cumulative development-system release protocol requires ten attributable
cold boots, preserved recovery, CPU0-7 identity, console/log capture, keyboard
input and authenticated USB administration. Keep CPU8/9 offline and retain the
protocol's existing power/load bounds. Separately reviewed keyboard and bounded
read-only eMMC packets may run once their first-baseline-boot dependencies pass;
they need not wait for all ten cycles. Explicitly admitted persistent-root I/O
and validated orderly restart/power-off remain separate steps. No daily-driver,
storage-reliability or thermal-protection claim follows merely from the ten-boot
gate. The [conditional A53 cold-boot protocol](../experiments/2026-09-09-standard-kernel-package/A53_COLD_BOOT_PROTOCOL.md)
defines per-cycle evidence and a stop rule; freeze its candidate and finite
commands only after the first A53 board regression passes.

## Upstream delivery gate

Prepare the corrected infracfg reset topic first because its resource semantics
are shared by thermal and PMIC serviceability and have focused test evidence.
Check current upstream and related Gemini efforts for overlap before new
implementation. Review the final coherent change rather than submit the
historical fix-on-fix chain. Confirm the appropriate current maintainer tree and binding conventions;
obtain genuine author certification before sending. The separate
[TOPRGU readiness assessment](../experiments/2026-09-06-mt6797-toprgu-minimal-restart/UPSTREAM_READINESS.md)
holds restart submission until the current-base MT6797 match/firmware contract
and the inconclusive minimal-candidate runtime result are resolved; it is not
an automatic combined series.

Every topic records target, actual authorship status, dependencies, tests,
public review revision and deletion condition. Keep historical patches and
checksums reproducible; synthetic sign-off debt cannot become a certification
by renaming a person. A metadata check prevents new debt, while the existing
submission blockers remain explicit. Seek maintainer feedback on difficult
ownership/interfaces before building a large implementation around them.

## Ordered gates

These stable anchors preserve earlier links. They summarize the historical A72
sequence; current work order is above and detailed chronology is in experiments.

<a id="0-repair-the-profile-series-invariant"></a>
### 0. Repair the profile-series invariant

Complete for currently selectable profiles; enforce the invariant on every
manifest/series change. Historical quarantine stays in effect. See the
[original audit](../experiments/2026-07-28-profile-series-invariant-audit/README.md).

### 1. Specify the legacy-family driver

The bounded legacy contract is established; general regulator ownership remains
separate. See the [contract](../experiments/2026-07-29-da921x-legacy-driver-contract/README.md).

### 2. Implement and validate an isolated profile

The isolated identification implementation passed its scoped gate. See
[implementation evidence](../experiments/2026-07-29-da921x-legacy-bind/README.md).

### 3. Probe, bind, and unbind only

The read-only identification lifecycle has a positive result. See
[lifecycle evidence](../experiments/2026-08-01-da921x-post-event-lifecycle/README.md).

### 4. Finish the ownership and rollback audit

Evidence supports the bounded isolated transactions. General error recovery,
concurrent rail policy and production power-management ownership remain open;
see [the durable boundary](hardware/da921x-i2c6-a72.md).

### 5. Register a resource-only provider

The read-only provider gate is established. See the
[provider baseline](../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/README.md).

### 6. Prove one bounded writable operation

Complete only for the exact same-value operation. It does not authorize general
writes. See the [result](../experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/README.md).

### 7. Bring up CPU8

Isolated CPU admission/execution is established. Default integration and general
power management remain open; see the [current matrix](HARDWARE_SUPPORT.md).

### 8. Validate CPU9 and the complete cluster

Repeated bounded CPU9 down/restore, topology and integrated execution have
results. General hotplug/stress, thermal repeatability/protection and suspend
remain distinct gates. See [lifecycle evidence](../experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/README.md).

## Milestones

Milestones are not serial prerequisites for preparing independent upstream
changes. Each completes only at its own evidence and upstream boundary.

| Milestone | Acceptance outcome |
| --- | --- |
| M0: lab | Tested recovery, exact provenance, enforced safe tooling, automated checks and upstream-topic ownership |
| M1: boot | Ten consecutive attributable cold boots; RAM, reservations, topology, timers, interrupts, PSCI and watchdog checked; loader DT/command-line mutations documented; generic/board changes publicly reviewed |
| M2: headless system | Safe PMIC/regulators/RTC/restart/power-off, bounded repeated storage I/O, authenticated USB administration, Wi-Fi station association and bounded bidirectional traffic, battery/charger telemetry and preserved filesystems |
| M3: input and ports | Keyboard map/modifiers/rollover/wake/LEDs/lid/buttons; microSD I/O/hotplug; both USB ports and supported roles with regression tests |
| M4: local interaction | Native DRM graph/panel/backlight, repeated modeset/power cycles, reliable console and calibrated multitouch |
| M5: power | Validated rail/OPP transitions, defensible thermal trips/cooling, charging protection, idle/runtime PM/suspend/wake and published power baselines |
| M6: peripherals | GPU, audio, Bluetooth/GNSS/FM and sensors through standard upstream interfaces; Wi-Fi reconnect/coexistence and PM coverage; explicit firmware boundaries |
| M7: distribution | Reviewed/released host support, standard artifacts and maintained loader path, ordinary distro packaging, tested updates/rollback and only time-bounded backports |
| Full variant coverage | Cellular and camera support on equipped variants, explicit feasibility/rights blockers, shared-memory isolation and subsystem-specific acceptance |

Earlier [issue seeds](../project/BACKLOG.md) retain stable tracking links. Their
open state alone is not a lack-of-progress signal: upstream acceptance remains
the completion condition. Publish reviewed milestone updates to the tracker as
coordination permits; this Git roadmap is the authority for ordered next steps.
