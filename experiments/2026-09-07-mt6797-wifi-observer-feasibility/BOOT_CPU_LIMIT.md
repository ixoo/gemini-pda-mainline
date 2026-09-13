# Native export diagnostic initial CPU limit

Status: the later [owner selection](#later-owner-selection) yielded a retained
preflight pass and a stop while waiting for the host request. Known-good Gemian
is confirmed and its retained console preserved. USB export remains incomplete.
Both reported selections are consumed; the first
[observation result](#device-observation) remains inconclusive. The preceding
[HPS-off session](HPS_BOOT_POLICY.md#device-result) is consumed and remains a
CPU-online refusal.

## Cause boundary and correction

That boot observed HPS disabled and CPU0–4 online. Its early command line and
initial SMP log had already wrapped out of the retained console, so the exact
boot-limit cause remains an inference. The
[historical LK handoff](../../docs/hardware/gemini-gemian-baseline.md#boot-handoff-and-storage-boundary)
and the freshly checked source explain a narrow candidate correction.

At LK revision `f4988d74bb70a0a15d7f362f412afba7e7fcda46`, the non-FPGA
[default command line](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/mt_reg_base.h)
ends in `maxcpus=5`. The pinned `mt_boot.c` appends the boot image's command
line afterward, then passes the resulting string as bootargs. Its append
function adds a space and the complete string, without removing repeated keys;
overflow of its 1,024-byte buffer is a refusal. No bootloader rewrite is needed.

The selected native kernel parses early arguments in order. Each `maxcpus`
handler calls `get_option()` with `setup_max_cpus`; a later nonzero value
replaces the earlier one. Linked ARM64 inspection confirms that destination
in the actual 47-patch kernel. `smp_prepare_cpus()` and `smp_init()` apply the
result to initial CPU activation. HPS later makes remaining CPUs present,
but its disabled hotplug algorithm does not supply the missing online CPUs.
The [receipt](results/maxcpus8.json) pins all inspected sources and binary input.

The [assembler](build-export-container.py) now appends `maxcpus=8` only for
`export-return`. [Startup](startup.py) requires exactly the ordered values
`5`, `8`, refuses `nosmp` and `nr_cpus`, then retains the HPS-zero and actual
CPU0–7 checks. Missing, reversed, repeated or additional limits refuse at
`boot-cpu-limit`. An eight-CPU argument never substitutes for the online mask.
The return path can preserve this new refusal stage without extra log records.

The changed hardware effect is initial native activation of A53 CPUs 5–7
before driver initialization, through the existing CPU-on implementation.
The kernel bytes, HPS default-off change, A72 refusal, PPM/EEM, idle policy,
frequency/voltage tables and recovery path remain as previously reviewed.
Startup makes no hotplug write. This remains a private native diagnostic;
neither a passed CPU check nor successful export demonstrates Wi-Fi support.

## Exact candidate and validation

Cycle `54efed5a-f015-4a0e-bd83-f59a0fa31097` reuses the Buildbox kernel from
`aa404d3e65fabff058269cde55631214ff0fb042`, SHA-256
`4fc02b373433bba5ca2ee8dc00990ea8698ad2d817ed7f7aa2e9fc7e08cda06b`.
The new filesystem has 723 members; only startup and session metadata change.
The compact runtime and private inputs match. Session SHA-256 is
`da877f7b2cfb49e9cd3c5d98fb03909d18047e35ea050cd4433cf1b22fb34779`.
The complete native container remains 16,300,032 bytes, with 477,184 bytes spare
in boot2. Padded SHA-256 is
`d9334cba2f6ca5870d7004ecbf8c01b4e47b8004e00db3178f5098bdb4f6fb9d`.

All 26 startup, five bridge and fourteen stream tests pass on the host. The
exact packaged ARM64 Python passes the startup and bridge tests with hardware
effects and restart injected. These include nine invalid argument sequences
and a five-CPU refusal despite correct arguments. Container reconstruction
matches exactly and rejects seventeen container and six input mutations.
Full fetched-package inventory/checksums, native header/load-address and
reserved-memory checks pass. No kernel rebuild or DT change was needed.

The private installer differs from the reviewed HPS installer only in five
exact identity substitutions; inverse comparison, shell syntax and ShellCheck
pass. Fresh inspection verified preceding Gemian boot
`0b7bd62b-20b3-4e28-aa9b-3ff92455678d` with systemd running. Publication and
hosted checks precede installation. The installer must recheck live GPT,
inactive non-root boot2, power, predecessor and full-partition readback, then
shut down cleanly. No fresh backup or alternative partition is selected.

## One physical session

Hypothesis: overriding the inherited five-CPU limit establishes CPU0–7 with
HPS disabled, allowing the unchanged export to reach its next stage. The
decision-changing observations are the exact argument preflight, actual online
mask, then either acknowledged export or the next attributable refusal.

Reuse the [export-return protocol](EXPORT_RETURN.md#changed-startup-and-finite-effects)
and all of its finite effects and recovery limits. There is one physical
selection, at most 21 shell and eight Python records of at most 192 bytes,
one immutable 65,536-byte snapshot read, one request/frame/acknowledgement
within the shared 60-second transport deadline, and one normal return request.
The host watcher and return collector each have 180-second windows; the latter
reads one retained console payload of at most 65,536 bytes. There is no capture
clear, WMT request, firmware load or WLAN cycle.

After verified installation and owner readiness, take the pre-selection USB
inventory and arm both exact-session collectors before requesting the physical
boot. The sole custodian preserves all outputs and verifies a changed-boot
Gemian return. A snapshot plus matching preserved marker passes export; a
snapshot alone proves preservation only. A caught refusal selects the next
correction. Missing attribution/return preserves uncertainty and does not
permit an unchanged retry or an alternate recovery action. Standing project
authorization covers this reviewed test; physical selection remains the owner
action.

## Verified installation

The correction was published at `2c900749683cb5e0c621da9b66915b9989559156`.
Local repository checks and the
[hosted Linux checks](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34724331096)
passed. The [deployment receipt](results/maxcpus8-deployment-20260912.json)
records installation in the same verified preceding Gemian boot.

Live GPT resolved boot2 as `179:30`, distinct from root `179:29`, with the
reviewed device guard passing before the write. All three gates saw a present,
healthy battery at 89% without external power, meeting the existing 80%
unpowered threshold; each sample pair matched. The predecessor was the exact
consumed HPS-off image. The installer wrote, synced and flushed the selected
image, required matching full-partition checksums, and independently read back
and byte-compared the entire partition on the host. No fresh backup was made.

After evidence was preserved, `systemctl poweroff` closed SSH with status 255
and the authenticated endpoint became unreachable. The installer completed
successfully. No automatic reboot, physical selection or collector invocation
occurred during installation. The finite observation windows were left unused
for the owner-readiness handoff.

## Device observation

The owner subsequently reported starting boot2 and an apparent restart toward
Gemian. Neither collector was armed before that selection. The exact return
collector was then invoked once, from approximately `23:15:53` to `23:18:53 UTC`
on 2026-09-12. Its 180-second window ended with status 1 after 25 failed SSH
connections to the known-good Gemian endpoint. No invocation authenticated;
no boot ID, OS identity, return marker or console payload was obtained.

One passive USB inventory taken after selection showed one MediaTek parent
and no export-descriptor parent. This cannot identify the running OS or boot
stage, establish an earlier USB state, or substitute for the missing
pre-selection inventory. The USB watcher and receiver were never invoked;
no request or acknowledgement was sent. The frozen runtime classifier was not
run because there is no console capture receipt to classify.

The [observation receipt](results/maxcpus8-runtime-20260912.json) records the
consumed selection and collector window, zero console reads, and private
evidence hashes. CPU0–7 establishment, export progress and normal recovery
remain unverified. An apparent restart is an owner observation, not proof of
a caught startup refusal or a kernel crash. Keep device custody reserved while
the visible state is clarified; do not repeat this image, rearm the expired
window or request another recovery action from this timeout alone. No new
candidate or device action was selected.

## Later owner selection

The owner subsequently reported readiness, another boot2 start and return to
Gemian. This second selection occurred before collectors were armed. No new
image was installed and no third selection was requested. The
[separate result](results/maxcpus8-owner-selection-2-20260913.json) preserves the
original timed-out observation unchanged.

One bounded identity probe verified running Gemian, boot
`db6b8120-0d47-4d05-9519-665e4aa74663`. The existing console-preservation command
then read one 65,524-byte payload, with the same Gemian identity before and
after. Its SHA-256 is
`2d4175301dea331073a8ad9b170759e3ce776dfe27285cc65014771ccfc397d9`.
Raw streams, commands and process records were synced and read back privately;
analysis ran in the RE VM. No recovery request or partition access occurred.

The console contains one matching cycle return marker for candidate boot
`48b970d5-dc39-4fba-91fb-663c4afb11fc`. The `python=preflight status=passed` stage at
2.640675 kernel seconds follows the exact argument, HPS-zero, actual CPU0–7,
kernel-configuration and process-isolation checks in the pinned startup source.
This establishes the CPU-limit correction for that native diagnostic boot.
The following USB-ownership marker proves that the one complete immutable
PMSG snapshot read returned; the host-request marker follows gadget setup and
opening its ACM terminal. It does not prove host enumeration or configuration.

Host-request waiting began at 2.826459 seconds and stopped at 62.888514 seconds.
The matching `outcome=stopped` marker at 62.891427 seconds is followed by the
normal kernel restart message. No listed fault token occurs after that marker.
The 60.062055-second interval matches the shared 60-second transport deadline;
with no host receiver/request, timeout is the supported explanation. The exact
exception class is absent from the retained log, so it remains an inference.

No snapshot-send or host-preservation marker is present. No host request or
acknowledgement was sent, and the snapshot was not saved on the host. The normal
return may change the PMSG header; this unavailable snapshot is not a successful
preservation result. No capture clear, WMT request, firmware load or WLAN cycle
is reached by this export-only path.

The immediately preceding Gemian boot was not observed before this second
selection. The candidate marker and current Gemian boot differ, but the full
preceding/candidate/returned triplet is unavailable. Do not retroactively assign
this console to the first timed-out selection. The ring starts with a partial
record and does not preserve the early boot arguments. A single later USB
inventory found no export parent; it says nothing about earlier enumeration.

Current device uncertainty is resolved and custody can be released. Export
remains the next distinguishing measurement: prepare a fresh finite session
with an observed preceding Gemian boot, pre-selection USB inventory and both
collectors armed before the owner's physical action. Do not weaken the CPU
gate, rebuild unchanged kernel inputs or repeat another uncollected boot.
