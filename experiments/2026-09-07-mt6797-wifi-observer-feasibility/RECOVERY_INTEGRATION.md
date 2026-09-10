# Recovery integration decision

Design checkpoint, 2026-09-10. Use the historical twelve-second watchdog
window as the proposed hard cutoff for one minimal-startup attempt. Do not
increase it to accommodate native waits, and do not describe it as a proven
completion budget. This selects a design direction, not a candidate, restart
authorization or a new use of the consumed recovery-only artifact.

## A cutoff does not require bounded worker completion

The [native controller assessment](CYCLE_CONTROL.md#controller-route-and-operation-timeout)
establishes that a four-second WMT wait does not cancel its worker. The
[DMA assessment](DMA_HOOKS.md#selected-deadline-and-idle-exits) also identifies
a return with the HIF lock retained. Therefore a software timer, joined worker,
descriptor close or ordinary WLAN teardown cannot own emergency recovery.

The watchdog must already be armed before the first connectivity initializer
with resource effects. The remaining time includes initialization, responder
interaction, one WLAN-on request, a joined load result, and at most one WLAN-off
request. If the attempt does not finish before hardware expiry, recovered
partial records are an incomplete attempt. Neither a successful syscall nor
the reset itself upgrades them to a successful lifetime observation. A cutoff
before the required observations must change the acquisition design; it does
not authorize repeating the same image or extending the timeout automatically.

## Historical ownership is insufficient for this candidate

Inspected public source:
[`mtk_wdt.c` at Gemian revision `59e00a9144d782e148332009a835b99c43382467`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c),
SHA-256 `816e82eddf63d2bf9366b84ff238b3ff305c7929bea3bd694a229c0294acd6bc`.
These are source observations, not executed paths or an exhaustive caller audit.

| Baseline function | Effect relevant after takeover |
| --- | --- |
| `mtk_wdt_set_time_out_value()` | Writes LENGTH under the register lock. |
| `mtk_wdt_mode_config()` | Can clear ENABLE or change reset/interrupt mode under that lock. |
| `mtk_wdt_enable()` | Can clear ENABLE independently of a reload. |
| `mtk_wd_suspend()` | Calls mode configuration with watchdog enable false, then restart. |
| `mtk_wd_resume()` | Can restore the saved timeout and ordinary mode, then restart. |
| `wdt_arch_reset()` | Directly reloads and changes MODE on its separate reset path. |

The historical [low-level takeover patch](../2026-08-02-a72-recovery-only-discriminator/patches/0002-diagnostic-add-exclusive-TOPRGU-recovery-owner.patch)
adds its ownership check to `mtk_wdt_restart()` only. It does not add checks to
the other mutations above. Its [kicker-side patch](../2026-08-02-a72-recovery-only-discriminator/patches/0003-diagnostic-run-bounded-watchdog-pstore-gate.patch)
disables ordinary kicking and CPU hotplug, which does not by itself exclude
suspend, resume or direct mode changes. The earlier scoped runtime result is
preserved; it does not prove exclusivity during this different workload.

Before implementation, the selected configuration and complete caller audit
must either exclude each competing mutation or provide serialization that
refuses it after takeover. Checking a flag before acquiring the register lock
is insufficient to exclude a caller that already passed the check. Include
direct reset, retention and request-routing writes in that audit; the table
is not the complete TOPRGU ownership surface. Do not patch only suspend and
declare the watchdog exclusive.

The [ordinary setter correction](RECOVERY_SETTERS.md) now implements locked
refusal for timeout, mode, enable and ordinary reload changes. The other
ownership paths above remain unresolved.

## Retention callers: preserve the existing configuration exclusion

The [retained-build review](results/recovery-retention-exclusion.json) narrows
the unlocked DRAM-retention concern. A full-tree source-name search locates the
native `mtk_rgu_dram_reserved()` calls in the watchdog API wrapper, with its
client calls in `mrdump_hw.c` and `mrdump_setup.c`. The pinned mrdump Makefile
selects the former only for MT6570/MT6757, and the latter only with
`CONFIG_MTK_AEE_MRDUMP=y`. Neither selection holds in the retained MT6797
configuration. Its compiler log contains no compilation of either caller.
The symbol map still contains the watchdog wrapper and low-level function;
unused entry points have not been removed from the kernel.

Keep that exclusion in the experimental candidate and verify its final
configuration and complete build inputs before takeover. No retention guard
patch is selected on the basis of these inactive callers. The independent
`CONFIG_MTK_MRDUMP_KEY=y` and `CONFIG_MTK_AEE_IPANIC=y` settings are not evidence
that full mrdump is selected, and this decision does not disable those features.

The review rechecks the already pinned source revision, config, compiler log
and symbol-map hashes; it is not a new kernel build or runtime observation.
An added client, changed configuration, loadable module or indirect access not
covered by this source-name search invalidates the exclusion. Minimal userspace
and module isolation remain required; the API's presence means this is not a
general kernel guarantee that retention cannot change after takeover.

## Exclude the CPU-idle route at boot

Require `cpuidle.off=1` in the experimental candidate's effective command line,
before any connectivity activity. Use the existing boot parameter rather than
adding a second idle-policy implementation or changing the running Gemian
system. This is a candidate requirement; no current image was modified.

The pinned [configuration](../2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config)
enables MT6797, CPU idle, the MTK idle governor and the watchdog kicker.
The same source revision's power and cpuidle Makefiles select `spm_v2` and
`cpuidle-mt67xx_v2.o`. The latter's `mt_soidle3_enter()` calls
`soidle3_enter()`, whose MT6797 implementation calls `spm_go_to_sodi3()`.
In [that implementation](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/base/power/spm_v2/mt_spm_sodi3p0.c#L393),
the kicker-enabled MT6797 branch calls `wd_suspend_notify()` before entry
and `wd_resume_notify()` afterward. `wd_api.c` connects these callbacks to the
watchdog suspend/resume functions above. Their names therefore do not restrict
them to an explicit userspace system-suspend request. Whether idle selection
would actually choose this state during a particular attempt is unmeasured.

The existing [cpuidle implementation](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/cpuidle/cpuidle.c)
exposes the read-only `off` parameter and makes `cpuidle_select()` return
`-ENODEV` when set. The scheduler then takes its default idle path;
ARM64 `arch_cpu_idle()` calls `cpu_do_idle()`, whose pinned implementation is
`dsb sy; wfi; ret`. This excludes the framework's selected SODI3 entry without
requiring a busy loop. It does not prove physical clock behavior, watchdog
continuity, exclusion of direct SPM callers or suppression of idle notifiers.

Before takeover, verify the built configuration, effective boot arguments and
the actual cpuidle `off` parameter. A missing or false value is a refusal.
System suspend, direct reset, notifier effects and the remaining watchdog
mutators still need their own exclusion or ownership proof. Boot-time exclusion
of this one path must not be promoted to complete recovery isolation.

## Live parameter check and panic restart exclusion

Two bounded read-only checks on 2026-09-10 restored contact with the known-good
Gemian endpoint. The [sanitized observation](results/recovery-live-parameters.json)
records the same boot identity across both invocations, the expected MT6797X
model, Linux `3.18.41+` on ARM64, Debian 9 and systemd. The parameter check
pinned that boot identity before reading and required it again afterward.
The live CPU-idle `off` parameter was readable and zero. This establishes a
usable software preflight observation; it does not validate the proposed
candidate or attribute the installed kernel to a source revision.

The live panic timeout was one second. In the separately pinned
[`kernel/panic.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/kernel/panic.c#L182),
a nonzero timeout reaches `emergency_restart()` after any positive delay.
The existing `panic` boot parameter controls that value. Require `panic=0`
and verify `/proc/sys/kernel/panic` is zero before experimental takeover.
This excludes that automatic panic-restart branch; it does not exclude panic
notifiers, explicit software restart, SysRq or other direct reset callers.
The controller must still exclude those competing paths or account for them.

Neither parameter was written on the device. No service, interface, radio,
watchdog, partition or boot state was changed. The read-only checks establish
access and current parameter values only; Wi-Fi and recovery runtime validation
remain outstanding. They do not consume or authorize a new boot2 session.

## Controller ordering to implement

1. Prepare the fixed minimal filesystem, private firmware identities and
   responder inputs without initiating connectivity. Establish candidate
   identity, capture storage availability and watchdog readiness.
2. Begin attributable persistent capture, then perform the reviewed watchdog
   takeover. No connectivity effect is allowed on a capture or arm refusal.
   Failure after hardware ownership is claimed must not restore the kicker.
3. Record verified arm readback before invoking connectivity initialization.
   Keep CPU hotplug and all competing watchdog mutators excluded until reset.
   The historical delayed-work trigger is not selected.
4. Run the existing single-attempt initialization and responder sequence, then
   the selected WLAN request sequence. The first error ends normal requests;
   no cleanup retry or presumed DMA release follows a returned error.
5. Preserve completed or partial records. A completed cycle also leaves the
   hard cutoff armed; no disarm/reload path is part of this proposed experiment.
6. After reset, require changed-boot known-good Gemian identity and retrieve
   the exact capture before classifying the result or selecting further work.

The [capture/arm backend](RECOVERY_GATE.md) now implements the first takeover
join as an unselected built-in function, with no trigger or connectivity call.
The [controller initialization entry](CONTROLLER_INIT.md) now calls that backend
before the native initializer chain and preserves each named return value.
The remaining controller stages, full watchdog caller/configuration audit,
shared-buffer/reset isolation, complete linking and candidate-specific recovery
review remain open. The owner must approve the exact radio and timed-restart
session before it runs, as required by [safety policy](../../docs/SAFETY.md).
No watchdog, radio, service, partition or device state was changed for this
assessment. No hardware deadline or recovery behavior was measured.
