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

## Current decision

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
   resolve ROM applicability, DLM/register contracts and checked calibration
   results before selecting the remaining common-init owner;
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

This section orders the non-Wi-Fi gaps so work can start as soon as the Wi-Fi
station milestone lands. It reflects the 2026-10-03 survey of the
[support matrix](HARDWARE_SUPPORT.md), the recovery records and the
architecture refreshes linked below. It does not change the Wi-Fi order above
and admits no device test; each runtime step still needs its own reviewed
experiment. Steps marked **(local)** need Julien's machine, because Buildbox
and the device are not reachable from cloud sessions. Everything else is
offline review, design, schema or documentation work that can start now.

Ranking rule: first remove dependencies shared by several subsystems, then
deliver the two usability blockers (battery/charging and native display), then
reuse the finished Wi-Fi connectivity core for Bluetooth and GNSS, then the
remaining peripherals.

### Shared dependencies

| Shared piece | Used by | Relation to Wi-Fi | Open item |
| --- | --- | --- | --- |
| MT6351 MFD, IRQ domain and regulators (0008–0015, 0062) | Wi-Fi rails, power keys, RTC, charger IRQ path, audio codec, microSD rails, touch/panel I/O rails | Every Wi-Fi candidate carries this stack; a change here invalidates Wi-Fi candidates | [VCN33 contract](../experiments/2026-09-08-mt6351-mfd-upstream-preparation/VCN33.md): one voltage selector serves BT and Wi-Fi with no arbitration; [VCN28](../experiments/2026-09-08-mt6351-mfd-upstream-preparation/VCN28.md) on-control sits outside the regulator vote |
| CONSYS/WMT core: power-on, BTIF, STP, WMT common init | Wi-Fi, Bluetooth, GNSS, FM | Built by the Wi-Fi workstream now; [common init](../experiments/2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md) runs RF calibration with the BT PA rail involved | Keep it one owner with per-task STP channels so BT/GNSS consume it rather than re-power the block |
| Clock and power-domain ownership (`clk_ignore_unused`, `regulator_ignore_unused`) | Retained simplefb console, display PWM, Wi-Fi profiles, GPU | All current profiles, Wi-Fi included, rely on both flags | Remove only per consumer, after its clocks and rails have a real owner |
| SPM block `0x10006000` | CONN power status/control (Wi-Fi), display PWM oscillator at `+0x458` ([PWM oscillator](../experiments/2026-09-07-mt6797-display-upstream-architecture/PWM_OSCILLATOR.md)) | Shared with the CONSYS owner | Agree one register owner before a backlight driver writes there |
| EINT controller (0005/0006) | PMIC (EINT176), touch (EINT8), card detect (EINT6), lid (EINT5), Type-C | None | No dedicated EINT consumer acceptance yet; make the first one cheap (lid or card detect) |
| I2C0/I2C1 | Charger, FAN49101, both FUSB301 (I2C0/I2C1); panel bias, BMI160, STK3x1x (I2C1) | None | I2C1 is disabled in the board DT; enabling it serves display bias and sensors together |

### Ordered gaps

1. **PMIC foundation (offline now).** Finish the MT6351 VCN33 arbitration and
   VCN28 control decisions in the
   [MFD topic](../experiments/2026-09-08-mt6351-mfd-upstream-preparation/README.md)
   with the Wi-Fi owner, since BT and Wi-Fi share them. Resolve the RTC BBPU
   reload question in the
   [RTC source audit](../experiments/2026-07-11-mt6351-pmic-recovery/results/rtc-source-audit-20260908.md)
   and write the power-key long-press reset policy in the
   [keys topic](../experiments/2026-09-08-mt6351-keys-preparation/RESET_POLICY.md).
   Then one combined runtime packet **(local)**: power-key events, RTC
   read/set/alarm and a reviewed power-off path. These close the M2 PMIC items
   and give every later boot a clean shutdown.
2. **Battery and charging (first usability blocker).** The charger is a
   BQ25896 on I2C0 `0x6b` ([identity](../experiments/2026-07-12-charger-power-recovery/CHARGER_ID.md));
   upstream `bq25890_charger` matches, so this is board description, not a new
   driver. Missing inputs: the charger IRQ line, conservative charge limits and
   the fuel-gauge source. No separate gauge chip has been found; whether the
   vendor gauge is MT6351-internal is inferred, not recorded. Next steps:
   (a) **(local)** one bounded read-only Gemian inspection for the charger IRQ
   GPIO/EINT, the gauge's register source and live power-supply telemetry,
   without repeating the consumed `0x14` read;
   (b) offline, a disabled BQ25896 node with limits taken from the
   [mainline design](../experiments/2026-07-12-charger-power-recovery/results/mt6797-charger-mainline-design.md)
   and the pending [IRQ preflight fix](../experiments/2026-09-12-bq25890-irq-preflight/README.md);
   (c) **(local)** a first mainline boot that only probes the charger and reads
   telemetry, with charging left in its loader state. Charging control and a
   gauge driver follow as separate steps. Charge state also gates device
   sessions: the 2026-09-12 inspection saw 31 % and "Not charging".
3. **Native display (second usability blocker).** Panel identity is
   contradictory (vendor NT36672 descriptor versus SSD2092 in the
   [bsg100 comparison](../experiments/2026-07-13-bsg100-gemini-linux-comparison/README.md)),
   and the bias chip and reset path are unproved. Keep the console on
   simplefb meanwhile. Next steps, in order:
   (a) **(local)** the already-specified bounded Gemian trace of display PWM
   clocks, parents and MM-domain lifetime from the
   [display refresh](../experiments/2026-09-07-mt6797-display-upstream-architecture/README.md),
   extended to read the panel ID and bias-chip identity read-only;
   (b) offline, rebase and split 0028–0044 per that refresh's verdicts and
   convert 0041 to OF-graph;
   (c) backlight first: display PWM with a truthful clock contract is the
   smallest consumer and makes the screen dimmable under simplefb;
   (d) DSI/panel bring-up **(local)** only after identity and reset are known.
   Touch (vendor NT36772 on I2C4 `0x62`, possibly SSD2092 at `0x53`; see the
   leads below and the [design](../experiments/2026-07-12-input-backlight-recovery/results/nt36xxx-mainline-design.md))
   follows the panel because its suspend/resume is coupled to LCD state and its
   rail is unidentified.
4. **Bluetooth, then GNSS (reuse the Wi-Fi core).** These start the moment the
   WMT common init in the Wi-Fi order is proven, because BTIF, STP, the ROM
   patches and calibration are the same. Offline now: design the STP task
   demultiplexer and channel API, and map the vendor BT and GPS function-on
   sequences against the common init. Upstream shape: a `hci_dev` over the
   shared BTIF/STP channel reusing `btmtk` helpers (`btmtkuart` matches only
   the framing), and a `gnss` device fed by the STP GPS task plus the LNA on
   GPIO69. First runtime test **(local)**: one HCI reset and version read.
   FM comes last; no upstream driver exists and its fitment is unknown.
5. **Small standalone wins (any free slot).** Lid switch (GPIO66/EINT5, patch
   0074) needs one attended transition **(local)** to confirm polarity and
   wake. microSD at 3.0 V needs the VMCH/VMC entry trim from the
   [microSD contract](../experiments/2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md)
   before a card test **(local)**. USB VBUS/role ownership needs one session
   tying connector, role, GPIO94 and the charger boost
   ([VBUS record](../experiments/2026-09-08-usb-vbus-ownership/README.md)).
6. **Audio.** Upstream drivers exist (`mt6797-afe-pcm`, `mt6351`,
   `mt6797-mt6351`). Offline: the AFE YAML topic awaits truthful authorship.
   Before a card: identify the speaker amplifier at I2C0 `0x31` and the jack
   detection wiring **(local, read-only Gemian)**, then a bounded low-volume
   playback test **(local)**. Depends on step 1 for the MT6351 codec child.
7. **Sensors.** BMI160 (I2C1 `0x69`) has an upstream driver; STK3x1x product
   ID `0x11` is not in the `stk3310` table. Enabling I2C1 is shared with the
   display bias chip, so do it once. Rails, interrupts and mount orientation
   need a read-only Gemian check **(local)**. See the
   [sensors refresh](../experiments/2026-09-07-gemini-sensors-upstream-architecture/README.md).
8. **GPU.** Panfrost (Mali-T880) needs the MFG power domains, the RT5735 VGPU
   regulator ([record](../experiments/2026-07-12-rt5735-vgpu-recovery/README.md))
   and safe OPPs. It waits for native display and for thermal protection.
9. **Cellular and cameras.** Unchanged: feasibility work only, per the
   cellular and camera records referenced in the parallel-delivery table.

### Leads from owner-held reference documents

The owner keeps a local set of reference documents that is not in Git: the
public 96Boards X20 (MT6797) functional specification, schematic and BOM,
vendor datasheets (BQ25896, TPS65132, FUSB301A, DA9213/14/15, AW9523B),
2017 MT6351 mailing-list patches, and third-party Gemini notes (Gemian wiki
and bsg100). The SoC and X20 material is marked confidential and most
datasheets have no redistribution grant, so cite them by name only. They are
leads to check against this unit, not facts:

- **Display and touch may be one chip.** A Solomon brochure lists SSD2092 as a
  single-chip display and touch driver. bsg100 reports I2C4 `0x53` answering
  and nothing at `0x62`. If confirmed, it replaces both the NT36672 panel and
  NT36772 touch assumptions, so make the step 3a read check `0x53`.
- **Panel bias.** The TPS65132 datasheet gives fixed address `0x3e`, VPOS/VNEG
  at registers `0x00`/`0x01` and a ±5.4 V reset value, which fits the vendor
  writes. The functional specification places LCM_RST on GPIO180 (EINT105)
  and DISP_PWM on GPIO178.
- **Charger.** bsg100 reports boost enable on GPIO107 in addition to
  OTG_CONFIG. The BQ25896 watchdog reverts settings to defaults unless the
  host services it or disables it, which the charger limits must account
  for. The interrupt is an active-low 256 µs pulse.
- **Fuel gauge.** bsg100 names the MT6351 internal gauge (FGADC registers),
  for which mainline has no driver. Confirm it in step 2a before planning one.
- **Audio jack.** The X20 detects the jack through MT6351 ACCDET. The
  speaker amplifier at I2C0 `0x31` is named in none of the documents.
- **USB.** GPIO93 (EINT16) has IDDIG as an alternate function, a candidate
  for the unidentified second switch. FUSB301A at `0x25` implies its address
  pin is strapped high on both buses.
- **Connectivity.** On the X20 the MT6631 integrates FM, with VCN18 feeding
  the Wi-Fi/BT and GPS 1.8 V supplies, VCN33 the Wi-Fi/BT 3.3 V supply and
  VCN28 the FM supply. That suggests no separate FM chip on the Gemini.
- **Board differences.** X20 addresses do not carry over: its `0x6b` is an
  MT6313 buck, while the Gemini has a BQ25896 there.

The [workstream registry](../project/workstreams.json) keeps owners; this
section only orders the work. When Wi-Fi reaches station association, start
with steps 1 and 2, and begin step 4's offline design in parallel.

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
