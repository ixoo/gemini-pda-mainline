# Native diagnostic HPS startup policy

Status: source correction and startup refusal tests complete; full kernel build
and device validation are outstanding. No new boot candidate is selected here.

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

Build the 47-patch composition through the existing
[Buildbox lane](FULL_KERNEL.md), then inspect the linked HPS default and its
unchanged worker/algorithm path. Freeze new kernel/session/container identities
before selecting another physical export-return session. That session must
demonstrate disabled HPS, a passed CPU0–7 preflight and either the next
attributable failure or a complete acknowledged export. Preserve its normal
return evidence. A successful compile or an HPS log alone does not pass those
runtime checks.
