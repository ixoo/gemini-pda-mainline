# Roadmap

This roadmap describes the current decision path and milestone exits. Detailed
candidate history, build identities, runtime logs, and rejected branches belong
in the [experiment index](../experiments/README.md), not here.

## Immediate objective: a safe legacy DA921x provider boundary

The current critical path is the external regulator dependency for the MT6797
Cortex-A72 pair.

| Boundary | Current state | Consequence |
| --- | --- | --- |
| Recoverable development boot | Linux 7.1.3 candidates boot from non-primary `boot2`; console, keyboard, USB gadget shell, and native reboot are available. | Preserve this serviceability set as a mandatory gate. |
| Cortex-A53 cluster | CPU0–7 can be online together. | Keep this baseline fixed while regulator work proceeds. |
| I2C6 ownership | DVFSP handoff and shared AP-DMA ownership are understood well enough for the fixed native path. | Do not disturb the working I2C5/AP-DMA owner. |
| I2C6 transfer | Native packed/FIFO one-byte pointer plus one-byte read is proven for the fixed diagnostic shape. | Do not generalize this to arbitrary transfers or writes. |
| Legacy board contract | The fixed `0x68`/`0x69` tuple is stable and DA9213/DA9214/DA9215-compatible. | The read-only board-contract gate is closed; unique silicon identity remains open. |
| Linux regulator provider | The upstream DA9211/A-family probe is incompatible and no suitable legacy provider is active. | Implement a genuine legacy-family contract instead of emulating it in the A-family probe. |
| Cortex-A72 | CPU8 and CPU9 remain offline; rail ownership, rollback, resume, and the full power sequence are unproved. | Keep both CPUs disconnected until the provider gates below pass. |

The durable technical boundary is in
[DA921x, I2C6, and Cortex-A72](hardware/da921x-i2c6-a72.md). The exact
completed diagnostic is in its
[experiment record](../experiments/2026-07-28-da9214-gauss/README.md) and must
not be repeated unchanged.

## High-level path to the project goal

The project goal is a maintainable, upstream-derived Linux system for the
Gemini PDA, not merely a kernel that reaches userspace once. The critical path
is:

1. close the real-compatible DA921x event/serviceability regression without
   weakening the established console, keyboard, USB, CPU0--7, or recovery
   baseline;
2. prove the identification-only legacy DA921x driver can bind, perform its
   fixed read-only contract, and unbind cleanly;
3. finish the regulator, DVFSP, SPM, SRAM-LDO, clock, reset, suspend/resume,
   and rollback ownership audit;
4. register a passive regulator provider while all writable operations and
   consumers remain disconnected;
5. prove one reviewed, bounded write/readback/rollback operation with CPU8 and
   CPU9 still offline;
6. bring up CPU8 with checkpoints and fail-closed rollback, then validate CPU9
   and the complete cluster separately; and
7. complete the persistent-storage, native display/touch, keyboard/USB,
   battery/charging/thermal, suspend, peripheral, and distribution-integration
   milestones around that safe power foundation.

Reusable bindings and drivers move upstream continuously throughout this
sequence. Each local patch has a deletion condition tied to an accepted
upstream version; the end state must not require a permanent Gemini platform
fork.

Work on eMMC, logging, keyboard coverage, USB roles, display/touch, and other
independent subsystems may proceed in parallel only when it preserves the
fixed DA921x/A72 experiment baseline. The immediate critical chain is:

`event regression -> read-only DA921x bind -> passive provider -> bounded write -> CPU8 -> CPU9`

## Ordered gates

### 0. Repair the profile-series invariant — complete

The manifest debt recorded by the
[profile-series invariant audit](../experiments/2026-07-28-profile-series-invariant-audit/README.md)
was repaired on 2026-07-29. The superseded legacy-readonly and active-A72
profiles are no longer selectable, their historical experiment inputs remain
available as evidence, and the kernel wrapper now enforces the invariant
across every manifest profile before selecting one.

The default and fixed board-contract diagnostic profiles were preserved
unchanged. Rejected legacy/provider/A72 patches were not added to the canonical
series. Any useful part of that historical work still requires a new reviewed
logical patch.

Exit met: every selectable manifest profile satisfies the
canonical-subsequence policy and the invariant is enforced automatically.

### 1. Specify the legacy-family driver — complete

The [legacy-family driver and binding contract](../experiments/2026-07-29-da921x-legacy-driver-contract/README.md)
was completed on 2026-07-29.

It specifies a separate identification-only driver for the non-A
DA9213/DA9214/DA9215 programming model. The initial Gemini variant:

- claims only the fixed direct `0x68` and `0x69` addresses;
- accepts only the exact observed tuple through two fixed seven-read passes;
- has no DA9211/A-family fallback, paged regmap, `PAGE_CON`, device-ID,
  register-data write, provider, IRQ, consumer, or A72 path; and
- gives failed probe, unbind, shutdown, suspend, and resume zero hardware
  transactions.

The complete successful probe trace is a
[machine-readable 14-transfer contract](../experiments/2026-07-29-da921x-legacy-driver-contract/probe-contract.json);
every failure trace is a strict prefix. Ownership, constraints, error
handling, cleanup, unbind, and resume behavior are defined in the
[design review](../experiments/2026-07-29-da921x-legacy-driver-contract/DESIGN.md).

Exit met: the contract relies on the public manufacturer register model and
upstream subsystem interfaces rather than vendor policy code, and every
probe-time transaction is statically enumerable.

### 2. Implement and validate an isolated profile — complete

The [legacy identification-only integration](../experiments/2026-07-29-da921x-legacy-bind/README.md)
was completed offline on 2026-07-29. Canonical patches `0123`–`0125` add the
binding, driver, and board description as separate logical changes, selected
only by the `da921x-legacy-bind` profile.

The static validator proves the fixed `0x68`/`0x69` tuple and exact fourteen
reads, and rejects representative retrying, write-bearing, wrong-address, and
provider-bearing mutations. The binding and focused Gemini DT checks pass.
Checkpatch reports no code checks; the patches remain intentionally
non-submission-ready because author DCO certification and maintainer review are
still outstanding.

Exit met: two fresh out-of-tree Linux 7.1.3 assemblies produced byte-identical
`Image`, `Image.gz`, configuration, `System.map`, and Gemini DTB. Both packages
pass provenance, checksum, image-boundary, and experiment validation with the
same source, patchset, and configuration identities. No device was accessed.

### 3. Probe, bind, and unbind only — open after pre-serviceability failure

The first hardware candidate after the completed read-only diagnostic tested
only the isolated driver lifecycle, not a regulator action. Its first boot
failed before recoverable serviceability and automatically returned to Gemian
with watchdog-block-class reset tokens but no attributable pstore record. It
therefore produced no lifecycle evidence and must not be repeated unchanged.

Hypothesis:

> A dedicated legacy-family driver can match the fixed tuple, bind, and unbind
> without a register-data write or loss of the known-good serviceability
> baseline.

Unique attributable evidence:

- exact driver match and lifecycle log;
- fixed tuple read through the isolated driver path;
- I2C counters and a write oracle proving zero register-data writes;
- unchanged CPU0–7, CPU8/9-offline, I2C5/AP-DMA, DVFSP, console, keyboard, USB,
  and reboot state.

Decision:

- success permits the resource-only provider gate;
- a tuple mismatch stops at chip/board identification;
- a transfer or lifecycle failure stays an I2C/driver issue;
- any unexplained serviceability regression blocks provider work.

This boot also provides independent-boot repeatability of the tuple without
repeating the completed diagnostic.

The next diagnostic preserved the exact Gate 3 kernel, oracle, initramfs, and
I2C6 controller description while disabling only the new DA921x DT child. Its
first boot was serviceable: USB, console, keyboard, CPU0--7, handoff, and fatal
log gates passed while no `0x68` client existed and every I2C6 transfer/oracle
counter remained zero. This implicates the enabled child’s automatic
creation/probe path but does not distinguish client creation, early probe
timing, or the fourteen-read logic.

The post-serviceability discriminator kept the child enabled, linked the
identification driver only as a manual-path module, and preserved the exact
Gate 3 DT. Attempt 1 grey-screened and rebooted before USB/netcat
serviceability, so the module was never loaded. Returned Gemian confirmed the
exact boot2 checksum; pstore was empty. This rules out neither enabled-client
creation nor a module-enabled kernel/configuration effect and provides no
fourteen-read probe result.

The exact-current-kernel child-disabled derivative was serviceable on attempt
1. USB, console, keyboard, CPU, handoff, and zero-counter gates passed. No
DA921x code was resident or loadable automatically. This rules out the
module-enabled kernel/configuration boundary and implicates the enabled
DT-client path before driver execution.

The exact serviceable artifact was preserved and used to build the next
discriminator: the child is enabled with its resource contract unchanged, and
only its compatible is replaced by diagnostic non-matching value
`dlg,da9214-unbound`. The candidate passed all offline gates, was installed to
live-GPT-resolved `boot2`, passed an independent full-partition byte
comparison, and left the device powered off.

The first selected boot was serviceable. The enabled `1-0068` client existed
with the unmatched compatible, the unchanged resource contract, and no bound
driver. USB, console, keyboard, CPU, handoff, and fatal-log gates passed while
all I2C6 transfer/oracle counters remained zero and no DA921x code was
resident. This rules out generic client creation and the unchanged resource
contract as sufficient causes; the failure boundary is specific to the real
compatible/modalias path.

The module-file discriminator restores `dlg,da9214-legacy` on the exact
module-profile kernel while using the exact Gate 3 initramfs with no module
file or loader path. It passed all offline gates, was installed to
live-GPT-resolved `boot2`, passed an independent full-partition byte
comparison, and left the device powered off.

The first selected boot white-screened and rebooted before console or
USB/netcat serviceability. Returned Gemian and the full boot2 checksum
confirmed the exact candidate; pstore was empty. Because the initramfs
contained no module or loader path, this places the boundary before module
availability and driver execution.

Exact-source audit found no real-compatible string or match table in the
kernel Image. The DA921x driver is module-only, the uevent helper is disabled,
and the module-free initramfs has no listener. The early string-dependent
paths that remain are the compatible-derived I2C client name and the OF
modalias uevent.

The name-only discriminator preserves the exact kernel and module-free
initramfs while disabling the DT child. It passed all offline gates, was
installed to live-GPT-resolved `boot2`, passed an independent full-partition
byte comparison, and left the device powered off.

The first selected boot was serviceable and every pre-creation gate passed.
The one permitted `new_device` write was rejected because the inherited
initramfs mounts sysfs read-only. No client was created, no driver bound, and
all I2C/oracle counters remained zero. This is safely inconclusive about the
name/I2C-modalias path.

The second selected boot used the same exact artifact with the new bounded
RW-window observation path. The helper created one name-only
`da9214-legacy` client, restored sysfs read-only immediately, and verified that
the client had no OF node and no bound driver. USB/netcat and the complete
serviceability baseline survived while every I2C/oracle counter remained zero.
This rules out the compatible-derived client name and I2C modalias as
sufficient causes. The failure boundary is now the real-compatible OF node or
its OF modalias uevent path.

The OF-modalias suppression candidate preserved the real-compatible OF child,
client name, resources, OF-node attachment, module-free initramfs, and
zero-activity baseline while replacing only the add-event OF modalias with the
already-exonerated I2C fallback. It was fully serviceable. The real-compatible
client remained unbound, all I2C/oracle counters remained zero, and native
reboot returned Gemian. This rules out real-compatible OF-node instantiation
itself and isolates the unsafe boundary to adding that OF modalias to the I2C
device uevent environment.

The private-insertion discriminator generated the exact 38-byte modalias,
inserted it as one terminated `MODALIAS=` entry in a bounded private
`kobj_uevent_env`, validated the complete layout and bytes, discarded it, and
emitted only the safe I2C fallback. Its first selected boot was fully
serviceable with the real client unbound and every I2C/oracle counter at zero;
native reboot returned Gemian. This proves environment insertion mechanics
safe and places the remaining boundary at the real OF entry's presence during
event emission.

The real-environment rollback discriminator inserted and validated the exact
OF `MODALIAS=` entry in the actual device event, restored the original pointer,
indices, and exact 48-byte target buffer range, then added only the safe I2C
fallback. Its first selected boot was fully serviceable with the real client
unbound, every I2C/oracle counter at zero, and native reboot back to Gemian.
This proves transient real-environment mutation safe and, combined with the
earlier unsuppressed reset, isolates the remaining boundary to the OF entry
remaining present during event emission.

The first pre-dispatch candidate remained fully serviceable with the real
client unbound and every I2C/oracle counter at zero, but its required success
marker was absent. It suppressed the target event through the fail-closed
validation error path, so it does not yet prove the asserted complete layout.
Source audit identified the rejected assumption: the normal I2C uevent path
appends `MODALIAS=i2c:da9214-legacy` after the exact OF modalias, and `SEQNUM=`
therefore makes ten entries rather than nine.

The selected next discriminator must validate both exact modalias entries in
the complete ten-entry event, suppress only transport, and convert the target
event to a successful return before normal cleanup. This changes the observed
error-return behavior rather than merely adding marker text. Serviceability
with the exact success marker isolates the reset to broadcast or receiver
handling; a reset implicates complete assembly or successful cleanup. It
remains driver- and transfer-free. Provider work remains blocked.

That discriminator is now represented by the named
`da921x-dual-modalias-pre-dispatch-suppression` profile. Its exact runtime gate
requires the ordered OF and I2C modaliases, numeric sequence entry, successful
return, normal cleanup, zero hardware activity, and the complete established
serviceability baseline. It passed offline validation and exact boot2
deployment, but its first selected boot white-screened and rebooted before
console or USB/netcat serviceability. Returned Gemian confirmed the exact
boot2 checksum, a changed boot ID, a watchdog-class reset reason, and empty
pstore. No validation marker survived, so this is a failed serviceability
result rather than proof that the intended successful checkpoint executed.

Source inspection confirms that `device_add()` ignores this uevent return
value. The next discriminator must therefore preserve exact ten-entry
validation and transport suppression while removing the immediate printk and
publishing the validation state through an independent read-only observation
path available only if the boot remains serviceable. A surviving exact state
isolates the removed printk; another reset rules it out without repeating an
identical artifact. Provider work remains blocked.

### 4. Finish the ownership and rollback audit

In parallel with driver work, use the working Gemian environment and recovered
binaries to capture one natural, synchronized CPU8 transition:

- external buck state before, during, and after the transition;
- voltage and enable operations, including page/address semantics;
- iDVFS/DVFSP, SPM, SRAM-LDO, clock, CCI, DCM, and TOPRGU ordering;
- error paths and inverse/rollback sequence;
- CPU9 differences;
- suspend/resume owner and firmware interaction.

Exit: observations and inference are separated, every required writer has one
owner, and a failed step has a bounded rollback path.

### 5. Register a resource-only provider

Register the provider with all consumers disconnected and writable operations
disabled or unreachable.

Required evidence:

- provider registration performs no register-data write;
- current selector, enable, and constraint reporting is internally consistent;
- bind/unbind and failed-probe cleanup preserve the original state;
- console, keyboard, USB, I2C5/AP-DMA, CPU0–7, and native reboot remain intact.

Test resume in a separate experiment; a successful boot does not establish
resume ownership.

Exit: a provider can exist without changing hardware state.

### 6. Prove one bounded writable operation

Do not reach this gate until the register-write transport, constraints, and
rollback sequence have been reviewed.

The first writable test must:

- keep CPU8 and CPU9 disconnected;
- request one predeclared no-op or bounded state transition;
- read back the exact affected state;
- restore the starting state or execute the reviewed rollback;
- stop immediately on any mismatch;
- retain an independent reboot/recovery path.

Exit: one exact write/readback/rollback protocol passes. This is not yet A72
support.

### 7. Bring up CPU8

Request CPU8 only after the external provider, SPM/SRAM, clocks, CCI, PSCI,
error handling, and recovery sequence are all represented.

The candidate must have a single CPU8 request, strict checkpoints before and
after each power step, a bounded timeout, and a fail-closed rollback. CPU9
remains offline and is tested later as a separate hypothesis.

Exit: CPU8 reaches an attributable online checkpoint, executes a bounded
coherency/accounting test, and can be offlined or safely recovered.

### 8. Validate CPU9 and the complete cluster

After CPU8 is repeatable, test CPU9 separately, then validate:

- CPU topology and cache/CCI coherency under load;
- clock and reset ownership;
- OPP and cpufreq tables with conservative voltage bounds;
- idle states and hotplug;
- thermal protection and throttling;
- suspend/resume;
- scheduler behavior using upstream energy-aware and capacity mechanisms.

Do not transplant vendor HMP, HPS, or PPM policy as the mainline scheduler
design.

Exit: both A72 CPUs pass repeated boot, stress, hotplug, thermal, and suspend
protocols without regressing the A53 or serviceability baseline.

## Parallel work that does not block the A72 sequence

Work on these areas may proceed independently when it does not alter the fixed
A72 experiment baseline:

- harden eMMC access and a persistent development root filesystem;
- separate kernel logs from the interactive console;
- complete keyboard function-key, Page Up/Page Down, modifier, rollover, and
  wake testing;
- replace loader-retained display output with native DRM/panel/backlight
  ownership;
- validate USB role switching and both physical ports;
- upstream reusable MT6797 bindings and drivers as their evidence closes.

## Milestones

Milestones are not strictly serial. The project currently has useful pieces of
M0–M3 while working through an M5 dependency; none is complete merely because
one diagnostic candidate passed.

### M0 — Safe reproducible lab

Outcome: reversible experiments with traceable artifacts.

Exit criteria:

- recovery and protected partitions are documented and tested;
- build, configuration, DTB, initramfs, and packaging inputs are pinned;
- device-writing tools reject ambiguous or active targets;
- hardware facts record provenance and confidence;
- every local kernel patch has an upstream target and deletion condition.

### M1 — Current-mainline boot

Outcome: a current upstream-derived arm64 kernel repeatedly reaches an
observable initramfs from a named non-primary target.

Exit criteria:

- kernel and `/init` execution have attributable evidence;
- RAM, reserved memory, timer, interrupts, PSCI, watchdog, and CPU topology are
  checked;
- bootloader DT and command-line mutations are documented;
- at least ten consecutive cold boots complete without observed corruption;
- required generic and board changes are on a public upstream path.

### M2 — Persistent headless system

Outcome: an ordinary distribution can be administered without UART.

Exit criteria:

- PMIC, required regulators, RTC, restart, and power-off are safe;
- eMMC and partition constraints pass repeated I/O and recovery tests;
- USB gadget networking provides normal remote administration;
- charger and battery telemetry use conservative standard interfaces;
- clean restart and power-off preserve storage.

### M3 — Keyboard and USB serviceability

Outcome: built-in input and external ports provide a stable recovery and use
path.

Exit criteria:

- full keyboard map, modifiers, rollover, wake, LEDs/backlight, and lid/power
  buttons have named tests;
- microSD insertion, I/O, removal, and suspend behavior pass;
- both USB-C paths and supported roles are documented;
- repeated USB hotplug and role transitions pass.

### M4 — Native display and touch

Outcome: a locally interactive system using upstream DRM/KMS and evdev.

Exit criteria:

- MT6797 display dependencies and graph use reviewed bindings;
- the exact panel initializes through a DRM panel driver;
- backlight and power sequencing survive repeated cycles;
- framebuffer console or simple DRM output is reliable;
- calibrated multitouch input works.

### M5 — Mobile-grade power

Outcome: safe battery-powered operation.

Exit criteria:

- regulator and PMIC relationships are correct;
- CPU OPPs and voltage transitions are validated incrementally;
- thermal sensors and conservative trip points protect the SoC and battery;
- runtime PM, idle, suspend, and wake pass repeated tests;
- charging protection remains active during suspend;
- power baselines and limitations are published.

### M6 — Daily-driver peripherals

Outcome: major non-cellular peripherals use upstream subsystems.

Exit criteria:

- audio routing and jack behavior are documented;
- Mali works with Panfrost or has a precise upstream blocker;
- Wi-Fi, Bluetooth, and GNSS have a maintainable firmware boundary;
- supported sensors use standard IIO/input interfaces;
- runtime PM and suspend regressions are covered.

### M7 — Standard boot and distribution integration

Outcome: a distribution consumes the support without a Gemini platform fork.

Exit criteria:

- board DT and generic/MT6797 changes are merged or on an accepted path;
- standard Image, DTB, and initramfs artifacts use a maintained loader;
- boot and recovery choices are owner-controlled;
- one general-purpose distribution uses its normal arm64 packaging flow;
- remaining local patches are only time-bounded upstream backports;
- upgrade and rollback pass.

## Stretch work

Cellular, cameras, external display, and replacement of retained early firmware
do not block the main milestones. Cellular work must first establish shared
memory, crash isolation, firmware ownership, regulatory constraints, and a
maintainable standard userspace interface.

## Cross-cutting upstream workflow

Every milestone follows the same loop:

1. identify existing binding and driver support;
2. reproduce behavior with the least risky discriminator;
3. implement the smallest generic change;
4. validate on Gemini and, where possible, another MT6797 device;
5. submit to the appropriate upstream maintainers;
6. track review revisions and accepted commits;
7. remove the local patch after the containing upstream baseline is selected.
