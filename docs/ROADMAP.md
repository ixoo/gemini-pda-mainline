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

Keep one integration owner and at most three active implementation/research work
items. Each item has one owner, a frozen parent, a bounded scope, a handoff and
an upstream exit. These are staffing limits, not extra approval gates. Start
with upstream preparation, A53 serviceability and Wi-Fi support; the integrator
reviews their handoffs. Keyboard/storage protocol preparation stays with the A53
worker. Offline power work continues
when it can resolve a supported interface or measurement dependency. Unassigned work is not running.

| Workstream | First bounded deliverable | Can proceed independently | Hardware or integration dependency |
| --- | --- | --- | --- |
| Integration and lab | Shared checks, immutable packages, one active deployment path, baseline registry | Tooling fixtures, documentation and review | Serialize manifest/series integration and shared Buildbox mutations |
| A72 and power | Resolve a supported measurement or production-ownership contract; completed V4 is not a repeat queue item | Source/math review, fake-hardware tests, ownership design | Exact experiment admission; broader load waits for defensible thermal observation/protection gates |
| Upstream preparation | Extract and review a minimal MT6797 infracfg reset topic from the corrected implementation | Authorship audit, dependency reduction, binding review, maintainer-target discovery | Truthful certification, focused compile/schema checks and existing exact runtime evidence before submission |
| A53 serviceability | Specify and freeze an integration baseline and a ten-cold-boot regression protocol | Authenticated USB userspace, keyboard test plan, log separation, read-only storage tests | One scheduled device slot; persistent writes and power-off need their own reviewed protocols |
| Wi-Fi | Specify shared CONSYS/EMI/AP-DMA ownership and implement the gen3 AHB command/firmware contract | Protocol/resource analysis, retained-capture calibration research, implementation and refusal fixtures | First mainline session needs a frozen recoverable baseline and attributable logs; no dependency on A72 completion or all ten cold boots |
| Display, touch and GPU | Map the minimal DRM/panel dependency graph and resolve panel/backlight ownership | Compare current upstream bindings, documented resources and historical evidence | Shared clocks/resets/PMIC reviewed with power; GPU load waits for power/thermal prerequisites |
| Bluetooth, GNSS, FM, audio and sensors | Produce protocol/resource and firmware-rights decisions for each component | Identity matching, transport feasibility and upstream reuse research | Separate subsystem profiles and later runtime slots; no assumed vendor-ABI compatibility |
| Cellular and cameras | Identify upstream transport/pipeline feasibility and the irreducible blockers | Public interface, resource, licensing and existing-effort research | Shared-memory/crash isolation and radio or imaging-specific safety review before hardware work |
| Standard boot and distribution | Define normal package/update/rollback consumption of the integration baseline | Packaging and retained-loader contract review | Reliable storage/recovery; loader replacement is separately admitted |

Wi-Fi is a first-class usable-system requirement and an active workstream,
not deferred peripheral polish. Its owner defines the shared connectivity
power/firmware interface with the integration owner; Bluetooth and GNSS must
not independently mutate that contract. The evidence must establish the exact
transport and firmware protocol before choosing reuse or a new family driver.
Neither a vendor node name nor a compiled MT76 module establishes a match.

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
links. The [work item template](../project/WORK_ITEM.md) is the handoff contract.
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

Complete the next admitted storage observation when the owner is available;
keyboard capture preparation proceeds independently. Keep physical-start requests
in Project Planning and require the selected candidate's verified deployment
and clean-shutdown handoff. Wi-Fi progresses kernel integration and its shared
resource/firmware contract in parallel, with physical observations chosen to
resolve explicit blockers. If the owner is unavailable, leave the exact session
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

The remaining preparation order is:

1. **Preserve the accepted baseline foundation:** reuse its exact candidate,
   authenticated userspace, logging and reviewed recovery closure. Repair only
   an identified invalidated prerequisite; a similarly named newer profile is
   not a replacement for recorded inputs. Do not spend a boot on another marker.
2. **Wi-Fi:** compile the connected transfer components through the actual Linux
   interfaces, then complete a validated whole-image plan and shared EMI/AP-DMA
   ownership. Identify the retained calibration record's producer, restoration
   path and board/firmware applicability before admitting the first mainline
   bring-up. Keep ordinary section submission distinct from firmware execution;
   missing EMI ownership must not become a success flag or skipped section.
   Use the [Wi-Fi contract](hardware/mt6797-wifi.md) and existing private captures.
   Host fixtures and compile-only adapters do not establish usable Wi-Fi. The
   build-selected detector ioctl is the established kernel-side producer of
   `do_connectivity_driver_init` and returns its integer aggregate. The exact
   retained loader statically supplies a property/query-derived normalized
   scalar after cleanup, then logs and discards the init result; this vendor
   compatibility path neither forces an actual runtime `0x6797` value nor
   defines a mainline ABI. The accepted
   [standard interface/error design](../experiments/2026-09-06-mt6797-mainline-connectivity-interface-design/README.md)
   made the first slice an effect-free passive CONSYS descriptor plus opaque
   WLAN client binding. That [accepted implementation](../experiments/2026-09-06-mt6797-consys-passive-boot/README.md)
   passed Buildbox, guarded boot2 deployment and one authenticated runtime
   observation: the client reached `BOUND` generation 1 with all seven effect
   counters zero. Its boot and collection budgets are consumed; do not repeat
   it or promote the result to usable Wi-Fi. Before another candidate, define
   and validate shared CONSYS/EMI/AP-DMA ownership and an effect-bearing failure
   lifetime, while later lifecycle work still resolves actual final linkage
   plus an explicit gen3 teardown
   edge. The exact retained reconstructed ELF cannot supply the required ranges:
   all four target symbols have zero size and its synthesized `GLOBAL` binding
   does not prove original strength. The first reconstruction-provenance
   attempt recovered provisional Kallsyms neighborhoods, but its parser
   internally performed an unadmitted architecture-signature classification;
   none of those intervals is an input to later analysis. Before further
   disassembly, repeat the bounded tuple audit through an explicitly frozen
   AArch64 parser method that prevents architecture guessing, or obtain
   original sized-symbol evidence. See the [bounded unresolved result](../experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/README.md)
   and [excluded parser attempt](../experiments/2026-09-06-vmlinux-to-elf-symbol-provenance/README.md).
   Exit order must not be inferred by reversing initialization, and the vendor
   WMT ioctl must not be copied merely to run the retained loader.
3. **Keyboard coverage:** finish coherent capture admission, finite owner key
   sequence, classification and complete private evidence export. Reuse the
   measured monitor and retain the full-duration timing obligation; inert binary
   delivery alone is not a device test. Its runtime gate needs the first baseline
   USB/console pass, not all ten cold boots.
4. **Read-only eMMC regression:** finish the fresh-session handoff against the
   actual OS/transport and execute the prepared bounded read when physical
   selection is available. Preserve prior inconclusive connections; a failed
   local USB prerequisite must not consume a device observation. Its runtime gate
   needs baseline serviceability and reviewed recovery, independently of keyboard
   completion. Persistent-root writes remain separate.

Protocol work across these items can proceed concurrently within the three-worker
limit. Wi-Fi has its own worker; keyboard and storage remain with serviceability. Items with unverified
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

For accepted offline work, use the event-driven
[workflow improvement loop](../project/WORKFLOW_IMPROVEMENT.md). Its sanitized
ledger measures first-review acceptance, rework, escalation and observed cost;
it may propose a reversible future-task settings experiment but cannot reorder
this roadmap, resume paused work or authorize a build or device session.

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
gate.

## Upstream delivery gate

Prepare the corrected infracfg reset topic first because its resource semantics
are shared by thermal and PMIC serviceability and have focused test evidence.
Check current upstream and related Gemini efforts for overlap before new
implementation. Review the final coherent change rather than submit the
historical fix-on-fix chain. Confirm the appropriate current maintainer tree and binding conventions;
obtain genuine author certification before sending. TOPRGU restart is the next
candidate topic for independent readiness assessment, not an automatic combined
series.

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
