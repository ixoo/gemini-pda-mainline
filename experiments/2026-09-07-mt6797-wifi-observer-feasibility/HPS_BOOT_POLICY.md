# Native diagnostic HPS startup policy

Status: one device boot observed HPS disabled, but startup refused CPU0–4 where
CPU0–7 was required. Its normal return to changed-boot Gemian and retained
evidence are verified. The physical-selection budget is consumed; no retry is
selected. See the [runtime result](#device-result).

The [export-return session](EXPORT_RETURN.md#deployment-and-runtime-result)
reached Python and stopped at the required CPU0–7 check. Its retained log also
shows native HPS activity and repeated rejected CPU8 starts. The earlier
assumption that rejecting CPU8/9 implied a stable CPU0–7 set was incomplete:
HPS can remove A53 cores and retry the rejected A72 cores independently.
The exact online list at the failed check was not recorded.

## Source-backed correction

The [source receipt](results/hps-default-off.json) pins the seven inspected HPS
files at the native source commit. They match their original Git bytes in the
46-patch prepared tree. The MT6797 Makefile selects this implementation;
the other HPS versions in the source are not the selected implementation.

HPS starts with `enabled = 1`. Its late initcall starts a worker and timer,
then registers its PPM client. The worker collects load information and calls
the periodic power-policy functions before invoking the hotplug algorithm.
The algorithm's existing `enabled == 0` branch bypasses its core selection and
CPU up/down calls. Disabling the entire HPS service would also remove periodic
PPM work, so that broader change is not selected.

The [five-line patch](patches/hps-default-off/0001-power-start-native-diagnostic-HPS-with-hotplug-disabled.patch)
sets the initial enabled state to zero only under the already selected
`CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR`. Other configurations keep one. This
takes effect before the worker starts and changes no frequency/voltage table,
load collection, timer, PPM call, client registration or restart function.
It appends one logical patch to the existing native input sequence; the earlier
46 entries retain their order and identities. Configuration is unchanged.

This is the existing disabled-hotplug behavior, not a lock around every CPU
API. The inspected drivers/kernel/ARM64 sources contain no caller of the
selected `hps_set_enabled()` API. Its proc control remains writable, but the
isolated PID1 does not write it and refuses other userspace processes. Suspend
and hibernation are not requested; the selected kernel excludes hibernation
and CPU isolation. The HPS suspend/restore callbacks, EEM's CPU8 operations,
generic hotplug interfaces and earlier initialization remain distinct paths.
CPU8/9 retain the existing PSCI refusal. No general hotplug or thermal-protection
claim follows from this change.

Startup now reads the existing `proc/hps/enabled` value and requires zero before
checking CPU0–7. Both remain refusals; startup does not repair the state or
request a CPU transition. If the CPU list differs, it emits one additional
record only when that value is at most 32 characters and contains a numeric
CPU-list form. Other input values and exception text remain unlogged. This
record occurs before the failed preflight returns, so it stays within the
existing eight-record Python budget and 192-byte record limit.

## Validation and next decision

The patch applies to the exact prepared native source. Its original source
headers declare GPL version 2. The patch is assistant-generated experiment
work with no DCO certification and is not an upstream submission.
The host and exact packaged ARM64 Python pass 24 startup and five bridge tests,
including refusal of active HPS and rejection of nonnumeric or oversized CPU
values from diagnostic output. Restart and hardware effects are injected.

The [Buildbox lane](FULL_KERNEL.md) and linked comparison below establish the
compiled correction. The selected physical export-return session must
demonstrate disabled HPS, a passed CPU0–7 preflight and either the next
attributable failure or a complete acknowledged export. Preserve its normal
return evidence. A successful compile or an HPS log alone does not pass those
runtime checks.

## Validated build and selected session

The [receipt](results/hps-default-off.json) binds the successful Buildbox build
at `aa404d3e65fabff058269cde55631214ff0fb042`. All eleven remote and fetched
package files match the validated checksum inventory. The configuration is
byte-identical to the 46-patch build; source integrity and absence of unresolved
symbols passed. The same 69 section mismatches and suppressed compiler-warning
limitation remain. The hosted repository checks passed.

RE-VM GDB and ELF inspection locate `hps_ctxt.enabled` at offset 32 in its
1,232-byte object and confirm the initial value changes from one to zero.
The complete worker, hotplug algorithm and restart-wrapper functions are
byte-identical. Other allocated-data differences are accounted for by prepared
source-path strings, 44 debug descriptors whose line numbers increase by five,
and kernel/vDSO build IDs. All other allocated sections with stored bytes match.
This is a static
comparison, not evidence that the device preserves its online CPUs.

The selected cycle is `8e78b74b-ba3a-4ca1-9bc1-0d9fc8635a88`, using the
47-patch kernel SHA-256 `4fc02b373433bba5ca2ee8dc00990ea8698ad2d817ed7f7aa2e9fc7e08cda06b`.
The archive has 723 members; only `startup.py` and session metadata differ from
the preceding export-return filesystem. Its pinned runtime and private inputs
match. The 16,300,032-byte native container preserves the load addresses, ARM64
header and reserved-memory layout, reconstructs exactly, and rejects all 17
container and six input mutations. Its padded partition SHA-256 is
`9eb59c31f27fd20e7b911797259eef301c8ce5146fd905482f63512034a1b9f3`.

This session reuses the [export-return procedure](EXPORT_RETURN.md#changed-startup-and-finite-effects)
and its exact effect budgets, save acknowledgement, normal-return gates and
limitations. It adds only the disabled-HPS preflight and the bounded numeric
CPU-list failure record described above. No capture clear, WMT request,
firmware load or WLAN cycle is selected.

The hypothesis is that disabling native HPS hotplug before its worker starts
leaves CPU0–7 online long enough for the unchanged export to run. One physical
selection must establish HPS zero and a passed CPU preflight, then either a
complete acknowledged export or the next attributable failure. If preflight
still stops, preserve its stage and any admitted CPU-list record before choosing
the next correction. If the host receives a snapshot without a preserved
return marker, claim preservation only. No return or attribution leaves the
remaining startup/recovery uncertainty unresolved and does not permit an
identical retry.

Fresh read-only inspection confirmed known-good Gemian boot
`a1efb6e0-4c7e-43f6-9b56-0ba6086bd8c2`. The installer reuses the reviewed device
guard with only exact candidate, manifest, artifact, evidence-directory and
preceding-boot substitutions. It must recheck live GPT, identity, inactivity,
power and full-partition readback, then shut down cleanly. Arm both existing
collectors for this new session before the owner selects boot2 once. The
standing project authorization covers this reviewed test and normal return.

## Initial installation power refusal

The candidate was published at `0acadbf83ce56ae8403810dd6054a6fac48e29d3`.
Its first installation attempt stopped at the initial power gate, before
candidate upload, partition writing or shutdown. A subsequent bounded read
with matching Gemian boot identity found a present, healthy battery at 34%,
status `Not charging`, with AC, USB and wireless external-power values all zero.
The existing installer requires at least 80% on battery alone, or at least 40%
with external power. Those requirements remain unchanged. The owner has been
asked to connect the charger; proceed only after the ordinary live gates pass.
At that refusal, boot2 retained its predecessor and no physical selection occurred.

## Verified installation

The [deployment receipt](results/hps-off-deployment-20260912.json) records the
subsequent successful installation on 2026-09-12. The same known-good Gemian
boot was verified. Live GPT resolved boot2 as `179:30`, distinct from root
`179:29`; the reviewed guard passed before the write. The battery was present
and healthy with external power, at 43% during the probe and 44% during write
and post checks. Each pair of power samples was stable.

The predecessor checksum was `3064aeba166c06da72b7d22cd72ae75b8790ca1c6307f04eeb70a108e1d4bff5`.
The installer wrote the selected padded image, synced and flushed it, and
required matching full-partition checksums. A separate complete host readback
matched the candidate both by checksum and byte comparison. No fresh backup
was created. After evidence preservation, clean poweroff returned zero and
the authenticated endpoint became unreachable.

At installation completion, the PDA was off with the selected candidate
installed. Collectors had not been started, to preserve their finite windows
for physical selection. Installation itself consumed no physical selection.

## Device result

The owner reported one boot2 selection followed by a return to Gemian on
2026-09-12. The [runtime receipt](results/hps-off-runtime-20260912.json) binds
the candidate boot `0f3f0336-f69b-4a5d-971d-86c705288b22` to the exact cycle
above and the verified installed image. HPS logged `hps_ctxt.enabled: 0`.
Python passed the HPS preflight, then recorded `observed-0-4` and stopped at
`sys/devices/system/cpu/online`. It emitted the attributable `outcome=stopped`
return marker at 2.767004 seconds; normal restart followed at 3.117558 seconds.
The authenticated Gemian collector verified a new boot,
`0b7bd62b-20b3-4e28-aa9b-3ff92455678d`, with systemd reporting `running`.

One bounded console read preserved 65,524 bytes. The retained ring starts in a
partial record around 1.606 seconds, so neither the effective boot arguments
nor initial SMP activation survived. One CPU8 refusal remains before HPS
starts. The retained pre-return portion contains one warning and two call-trace
headings; no panic, BUG or kernel-fault token was found. The portion after the
return marker contains none of those fault tokens. These bounded observations
establish the caught refusal and normal return, not a warning-free kernel boot.

The owner selected boot2 before the collectors were armed. The return collector
ran afterward; the host USB inventory was also taken afterward. No pre-selection
USB inventory, watcher invocation, receiver request, acknowledgement or saved
application snapshot exists. Startup stopped before importing the USB exporter
or reading the application snapshot, so the missing receiver does not explain
this CPU preflight failure. No WMT request, firmware load or WLAN cycle occurred
through the diagnostic action. Raw console and USB inventory remain private.

HPS was disabled at initialization and preflight, but CPU0–7 was absent. The
[historical LK handoff](../../docs/hardware/gemini-gemian-baseline.md#boot-handoff-and-storage-boundary)
supplied `maxcpus=5`. The selected native source's `smp_prepare_cpus()` and
`smp_init()` honor that limit; later `hps_cpu_init()` marks the remaining CPUs
present without itself bringing them online. CPU0–4 therefore fits an initial
five-CPU limit left in place when HPS hotplug is disabled. This is a source-backed
inference: the lost early log prevents proving the effective limit or whether
CPUs 5–7 were ever online in this boot.

Next resolve that boot-limit and initial-activation boundary before changing
the candidate or admitting a new measurement. Do not weaken the online-mask
check or repeat this unchanged image. The one physical selection and console
read are consumed; leave the verified Gemian system running.
