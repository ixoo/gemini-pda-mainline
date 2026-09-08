# MT6397 RTC alarm interrupt-enable correction

Status: incomplete compile-preparation checkpoint, 2026-09-08. This is a
standalone unsigned upstream fix, not MT6351 RTC enablement or a boot candidate.

## Problem and change

The RTC compatibility audit found an independent bug in
`mtk_rtc_irq_handler_thread()` at Linux commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. The handler writes `IRQ_EN` using
a value derived from `IRQ_STA`, although these registers represent different
state. For example, `IRQ_EN=0x000d` (alarm, one-shot and low-power enables)
and alarm-only status `0x0001` produce `IRQ_EN=0x0000`, losing the other bits.
Conversely, low-power status can set its enable bit when it was disabled.

The [single patch](../../patches/upstream-4d7d9486/rtc/0001-rtc-mt6397-preserve-interrupt-enables-on-alarm.patch)
clears only the alarm enable through a masked update of `IRQ_EN`, under the
existing mutex. The example now preserves `0x000c`. Notification, IRQ return
behavior and the write trigger after successful modification are retained.
A failed enable-register read or write does not issue the trigger. The fix
does not add retries or claim recovery from a bus failure.

This corrects existing-chip driver behavior needed before any MT6351 reuse.
The separate [RTC source correction](../2026-07-11-mt6351-pmic-recovery/results/rtc-source-audit-20260908.md)
still owns the unresolved reload semantics. Neither that uncertainty nor
MT6351 binding/core work is hidden in this patch.

## Reproduction and evidence

[Source inputs](source-inputs.json) pin the inspected upstream driver, header,
configuration, maintainer entry and checkpatch files. Individual files were
retrieved from the public revision or the already validated Buildbox prepared
source for the same revision. Overlapping RTC files matched byte for byte.
No Linux source tree is stored in this repository.

The [focused test](test-alarm-mask.py) compiles the actual handler against a
small register/IRQ fixture. It covers independent status and enable values,
unrelated bits, no pending alarm, failed status reads, failed enable reads,
and failed enable writes. The unchanged upstream handler compiles but fails
the enable-preservation assertion; the corrected handler passes 160 cases.
The fixture models transport and locking, not real interrupt timing or PMIC
write-latch behavior.

```sh
python3 experiments/2026-09-08-mt6397-rtc-irq-fix/test-alarm-mask.py \
  /path/to/prepared/linux/drivers/rtc/rtc-mt6397.c
KERNEL_PROFILE=mt6397-rtc-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6397-rtc-compile ./scripts/buildbox fetch-package
```

The named profile selects only this patch against the manifest-pinned source
and explicitly enables the upstream RTC driver. Existing profiles retain
their exact definitions and selected patch bytes/order. It adds no Gemini DT.
Buildbox compilation and package validation are pending at this checkpoint.
Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded; that exclusion
does not establish submission readiness. Repository checks are required before
publication. No device access, alarm programming or kernel boot was performed.

## Upstream boundary

The pinned `MAINTAINERS` entry names the RTC subsystem and
[Alexandre Belloni's tree](https://git.kernel.org/pub/scm/linux/kernel/git/abelloni/linux.git/).
A targeted public search found the existing status-to-enable assignment and
its historical review, but no matching fix; this is not an exhaustive
mailing-list or maintainer-tree check. Recheck overlap and run maintainer
discovery against the final series before submission.

The change was prepared independently from upstream source during this audit.
Its synthetic archive author makes no DCO certification. Actual authorship
and truthful certification must be resolved before sending. No message was
sent. Remove the local patch after an equivalent upstream fix is included in
the project's selected baseline.
