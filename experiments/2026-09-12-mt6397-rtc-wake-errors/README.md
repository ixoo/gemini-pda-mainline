# MT6397 RTC alarm wake error propagation

Status: unsigned upstream-preparation checkpoint; callback regression and
patch style checks pass, kernel compilation pending. This is not MT6351 RTC
or Gemini suspend enablement and selects no device candidate.

## Problem and correction

The existing `mt6397_rtc_suspend()` and `mt6397_rtc_resume()` callbacks ignore
the return values of `enable_irq_wake()` and `disable_irq_wake()`. A failed wake
request is therefore reported as successful to the power-management core. For
example, an IRQ-controller `-EIO` during wake enable becomes a zero suspend
return even though the requested alarm wake configuration was not established.

The [two-line correction](../../patches/upstream-4d7d9486/rtc/0002-rtc-mt6397-report-alarm-IRQ-wake-errors.patch)
returns the corresponding helper result whenever the device may wake. When
wakeup is disabled, each callback still returns zero without touching the IRQ.
The selected core source propagates a suspend callback error through
`dpm_suspend()` instead of marking that device suspended. A resume error becomes
visible to the core; this patch does not implement retry or controller recovery.

The IRQ core already restores its wake-depth counter when the underlying
callback returns an error. This correction neither duplicates that accounting
nor turns a child's successful wake bookkeeping into proof that its parent
PMIC interrupt transport was programmed successfully. The separate MFD
[IRQ/error contract](../2026-09-08-mt6351-mfd-upstream-preparation/IRQ_ERRORS.md)
and MT6351 RTC reload/compatibility work remain unresolved dependencies for
Gemini operation.

## Sources and overlap

[Source inputs](source-inputs.json) pin the driver, IRQ core and device-PM core
at `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, plus the observed RTC maintainer
branches. The callbacks are byte-identical in `rtc-fixes`, `rtc-next` and the
separate `rtc/irqf_no_autoen` branch. Their complete drivers differ elsewhere;
no whole-tree equivalence or current-branch kernel build is claimed.
A targeted public search found no equivalent correction, but is not an
exhaustive public-review search. No upstream message was sent.

The new `mt6397-rtc-wake` profile selects the existing
[alarm-enable correction](../2026-09-08-mt6397-rtc-irq-fix/README.md) followed by
this independent wake fix, in canonical order. It reuses the old compile
fragment and adds only PM/suspend compilation plus a distinct release suffix.
This makes the changed callbacks compile instead of disappearing behind
`CONFIG_PM_SLEEP`. It enables no board or peripheral in a device candidate.
All 206 existing profiles and their effective inputs are preserved.

## Regression and build validation

The [focused regression](test-wake-errors.py) compiles the actual two callback
bodies with small device/IRQ stubs. Sixteen cases cover both callbacks, wake
policy on/off, success and three distinct errors, checking return values,
exact IRQ identity and call counts. The unmodified source compiles and fails
on the first wake-enabled error. The correction passes on the compile base
and all three inspected maintainer sources.

The composed two-patch driver also passes the existing 160-case alarm
status/enable/transport regression on those four source inputs. Strict
checkpatch reports zero errors, warnings and checks with only
`MISSING_SIGN_OFF` excluded. That exclusion is not certification.

```sh
python3 experiments/2026-09-12-mt6397-rtc-wake-errors/test-wake-errors.py \
  /path/to/prepared/linux/drivers/rtc/rtc-mt6397.c
KERNEL_PROFILE=mt6397-rtc-wake ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6397-rtc-wake ./scripts/buildbox fetch-package
```

Compilation must establish built-in RTC and PM/suspend support, both callbacks
in the final symbol map, and a validated immutable package before this
checkpoint is described as built. No alarm, RTC register, suspend, IRQ wake
operation or kernel boot has been requested on the PDA by this work.

## Upstream boundary

Target Alexandre Belloni's RTC tree with linux-rtc and MediaTek review. The
synthetic archive identity has no DCO sign-off; a human must establish actual
authorship and truthfully certify the final contribution. Recheck the source
base, recipients, introducing commit and public overlap at export. Remove this
local patch after an accepted equivalent reaches the selected upstream baseline
and the wake-error regression passes. Keep this logical change separate from
alarm masking, MT6351 support and platform suspend policy.
