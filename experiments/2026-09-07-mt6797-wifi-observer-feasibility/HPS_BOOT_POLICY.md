# Native diagnostic HPS startup policy

Status: source, complete kernel, startup and container checks passed. One new
export-return session is selected below; device execution remains outstanding.

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
