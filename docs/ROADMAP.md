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
with power, upstream preparation and serviceability; the integrator completes
infrastructure and reviews their handoffs. Unassigned work is not running.

| Workstream | First bounded deliverable | Can proceed independently | Hardware or integration dependency |
| --- | --- | --- | --- |
| Integration and lab | Shared checks, immutable packages, one active deployment path, baseline registry | Tooling fixtures, documentation and review | Serialize manifest/series integration and shared Buildbox mutations |
| A72 and power | Finish corrected thermal regression; decide the measurement dependency | Source/math review, fake-hardware tests, ownership design | Exact experiment admission; broader load waits for defensible thermal observation/protection gates |
| Upstream preparation | Extract and review a minimal MT6797 infracfg reset topic from the corrected implementation | Authorship audit, dependency reduction, binding review, maintainer-target discovery | Truthful certification, focused compile/schema checks and existing exact runtime evidence before submission |
| A53 serviceability | Specify and freeze an integration baseline and a ten-cold-boot regression protocol | Authenticated USB userspace, keyboard test plan, log separation, read-only storage tests | One scheduled device slot; persistent writes and power-off need their own reviewed protocols |
| Display, touch and GPU | Map the minimal DRM/panel dependency graph and resolve panel/backlight ownership | Compare current upstream bindings, documented resources and historical evidence | Shared clocks/resets/PMIC reviewed with power; GPU load waits for power/thermal prerequisites |
| Connectivity, audio and sensors | Produce protocol/resource and firmware-rights decisions for each component | Identity matching, transport feasibility and upstream reuse research | Separate subsystem profiles and later runtime slots; no assumed vendor-ABI compatibility |
| Cellular and cameras | Identify upstream transport/pipeline feasibility and the irreducible blockers | Public interface, resource, licensing and existing-effort research | Shared-memory/crash isolation and radio or imaging-specific safety review before hardware work |
| Standard boot and distribution | Define normal package/update/rollback consumption of the integration baseline | Packaging and retained-loader contract review | Reliable storage/recovery; loader replacement is separately admitted |

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

### One device queue

The named Gemini is a serial resource. The current thermal task owns its active
experiment until it records a completed or blocked handoff. Other workers may
prepare candidates and protocols offline but may not install, collect consuming
observations or change the device session concurrently.

Each queued item supplies an exact validated candidate, hypothesis, action
budget, distinguishing evidence, recovery path and decision map. The custodian
selects one ready item, records the cycle and publishes its result before the
next item can proceed. Existing standing boot2 authorization is preserved; a
queue entry is neither new authorization nor a reason to ask again.

A device result may serve several workstreams only when they share the exact
relevant inputs and the protocol measures each claimed behavior. An unrelated
passing boot or package is not a substitute. Do not bundle multiple
boot-critical changes merely to save a physical cycle.

### Progress measures and review cadence

At each integration review, record: accepted/released upstream topics, local
topics awaiting review, regression passes on exact inputs, unresolved shared
blockers, and why each consumed boot changed a decision. Track rejected and
inconclusive outcomes too. Patch, build and document counts are not progress
measures. Review priorities weekly or when a decisive result changes a
workstream's dependencies; no timer or automation is created by this plan.

## A53 development-system release gate

A53 integration proceeds independently of complete A72 suspend support. Start
from a named runtime-proven serviceability candidate and audit its required
kernel/DT/config inputs before defining a new frozen manifest profile. Do not
silently promote an old experimental profile or the moving `full` default.

The first acceptance protocol requires ten attributable cold boots, preserved
recovery, CPU0-7 identity, console/log capture, keyboard input and authenticated
USB administration. Keep CPU8/9 offline and retain the protocol's existing
power/load bounds. Then add bounded read-only eMMC checks, explicitly admitted
persistent-root I/O and validated orderly restart/power-off as separate steps.
No daily-driver, storage-reliability or thermal-protection claim follows merely
from the ten-boot gate.

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
| M2: headless system | Safe PMIC/regulators/RTC/restart/power-off, bounded repeated storage I/O, authenticated USB administration, battery/charger telemetry and preserved filesystems |
| M3: input and ports | Keyboard map/modifiers/rollover/wake/LEDs/lid/buttons; microSD I/O/hotplug; both USB ports and supported roles with regression tests |
| M4: local interaction | Native DRM graph/panel/backlight, repeated modeset/power cycles, reliable console and calibrated multitouch |
| M5: power | Validated rail/OPP transitions, defensible thermal trips/cooling, charging protection, idle/runtime PM/suspend/wake and published power baselines |
| M6: peripherals | GPU, audio, connectivity and sensors through standard upstream interfaces, explicit firmware boundary and PM coverage |
| M7: distribution | Reviewed/released host support, standard artifacts and maintained loader path, ordinary distro packaging, tested updates/rollback and only time-bounded backports |
| Full variant coverage | Cellular and camera support on equipped variants, explicit feasibility/rights blockers, shared-memory isolation and subsystem-specific acceptance |

Earlier [issue seeds](../project/BACKLOG.md) retain stable tracking links. Their
open state alone is not a lack-of-progress signal: upstream acceptance remains
the completion condition. Publish reviewed milestone updates to the tracker as
coordination permits; this Git roadmap is the authority for ordered next steps.
