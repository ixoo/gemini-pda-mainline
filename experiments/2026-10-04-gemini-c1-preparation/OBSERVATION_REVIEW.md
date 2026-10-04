# C1 observation review

Offline review of the exact MFD-integrated build input `c2eeeb8a`, 2026-10-04.
The [receipt](results/observation-review.json) pins inspected sources. This is a
protocol draft with unresolved admission gates, not a candidate or device script.
The [roadmap](../../docs/ROADMAP.md) owns implementation order. No device was
accessed and no new kernel build was performed for this review.

## PMIC baseline: transport and register semantics are separate

The existing [ten-entry inventory](results/source-audit.json) contains ten
unique, even addresses within the 16-bit wrapper regmap. The selected
`pwrap_regmap_config16` has no cache selection, so its zero-initialised cache
kind is `REGCACHE_NONE`. It also defines no readable, volatile or precious
register table. Acceptance by that regmap is therefore not read-safety proof.

`pwrap_regmap_read()` returns `pwrap_read()`'s result. For this 16-bit path,
`pwrap_read16()` polls for idle, issues a read command, polls for valid data,
assigns the returned word only after successful completion, and clears valid
state. Each poll has a 10 ms timeout and 10 microsecond interval. An initial
idle timeout may also clear stale valid state before returning the error.
This is an attributable transaction result, unlike Gemian's shared cached
`pmic_access` value. It includes AP wrapper MMIO writes to command/valid-clear
registers; it must not be described as having no hardware effects. No PMIC
register write is issued by this read callback. Poll limits do not bound mutex
waits or scheduling latency.

Before admitting the ten targets, establish each target's read semantics from
applicable register evidence; neither its name nor vendor boot-time writes
proves absence of read-clear, latch or mailbox effects. The retained datasheet
review also leaves exact E2 applicability unresolved. Interrupt status,
clear/set aliases, RTC mailbox and calibration windows remain excluded. All
ten inventory entries remain unadmitted by this review.

A future observer belongs after a successful chip identification and before
IRQ setup and child registration. This labels the result loader-inherited
state after wrapper setup, rather than untouched kernel-entry state. It must
make one ordered read per admitted address, retain address/return/value together,
omit a value on failure and stop immediately at the first error. It performs
no comparison-triggered write, retry, reset or recovery. The maximum is ten
observer reads, separate from wrapper setup and normal driver activity. A
successful mainline sample does not establish current Gemian reset policy.

The [key-policy gate](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md)
remains: current Gemian fields need an attributable transport result and live
identity. The retained intent is not permission to program an eleven-second
one-key reset policy. Keep the key child absent until that gate is resolved.

## RTC: the current time-read callback is not bounded

The selected RTC base is `0x4000`. `__mtk_rtc_read_time()` reads seven counter
words and then seconds again, unlocking and propagating a transport failure.
`mtk_rtc_read_time()` repeats while the last seconds value is less than the
first. It has no attempt limit. A private host execution of the actual outer
function with three rollover pairs followed by a coherent pair succeeds after
four helper calls. This demonstrates the missing bound; it does not demonstrate
that Gemini produces that sequence or that counter shadows are fresh.

Before a bounded observation, cap coherent-counter attempts and report
exhaustion without using an inconsistent time. Regression must cover first,
second and final permitted success, exhaustion, and both bulk/seconds read
errors. Preserve month/weekday conversion and normal rollover behavior. A
userspace deadline alone cannot supply a kernel transaction budget.

RTC class registration also invokes hardware alarm/time readers even with
HCTOSYS and SYSTOHC disabled. `rtc_device_get_offset()` maps the supported time
range in software; it is not a time-setting operation. `rtc_initialize_alarm()`
can inherit an enabled future alarm into the software timer queue. Class/core
alarm operations can read time internally, so the counter bound matters to
alarm preparation too. The first candidate must review inherited alarm state
and core timer behavior rather than assume the RTC is idle at probe.

## Future RTC time and awake-alarm packet

After the installed version measurement and reviewed Gemian baseline, select
an exact validated C1 candidate, identify its boot, RTC parent/driver and IRQ
mapping, and retain the registration log and interrupt counts. Do not assume
`rtc0` or an input event number solely from a prior boot. Keep automatic clock
synchronisation disabled and the system awake throughout this packet.

For freshness, request three class time samples roughly ten seconds apart,
recording monotonic timestamps immediately before and after each read and the
full return status. Stop on the first failure or deadline; no fallback raw
RTC read, vendor RELOAD, clock-setting operation or repeated test follows.
Compare RTC deltas with the measured monotonic intervals, allowing one-second
quantisation and the measured read duration. Frozen/backwards time or deltas
outside that allowance refute freshness/coherence. A constant date offset is
a separate calendar/epoch discrepancy. Agreement supports this boot only;
it does not prove all rollover cases or absence of a RELOAD requirement in
every power state. Gemian time reads have their own admitted RELOAD effects;
no new Gemian `hwclock` read is authorised merely by this draft.

For alarm delivery, first review the exact userspace tool and RTC core path,
including inherited alarms and cleanup. The intended observation is one alarm
about ten seconds ahead while awake, one finite wait, and the attributable
RTC alarm event plus parent/child interrupt deltas. A command exit code or
`since_epoch` value alone does not prove interrupt delivery. Stop on a timeout,
transport error, unexpected IRQ activity or identity change; preserve evidence
and classify the result before another attempt. Do not suspend, reboot, set
wall/RTC time or alter RTC power-on/recovery mailbox fields.

Alarm programming is not read-only: the driver preserves fields while writing
seven alarm words, `AL_MASK`, the alarm/one-shot bits of `IRQ_EN`, then WRTGR
and busy polling. Its handler reads read-clear `IRQ_STA`, reports an RTC alarm,
clears only the alarm-enable bit and triggers that update. The selected handler
still ignores failed enable-bit updates and trigger results; it returns
`IRQ_NONE` on status-read failure without a diagnostic. Account for and report
these failures before claiming that alarm disabling completed. Generic core
work may also reprogram queued timers; a single userspace request is not proof
of exactly one driver invocation. The final effect budget and tool are therefore
still gates, not supplied by the old `rtcwake -m on -s 10` suggestion.

## Future lid event packet

The disabled hall node already specifies GPIO66, active-low `SW_LID`, 64 ms
debounce and no wake source. Enabling it makes gpio-keys request the GPIO as
input, configure debounce/interrupt resources and use the existing pinctrl
state. It is not an inert DT change. `gpio_keys_open()` reports current state,
so an initial close/open-looking report is not evidence of physical movement.

For the eventual candidate, keep suspend-on-close consumers absent, identify
the exact input device and capture its initial switch state. Then perform one
attended close/open within a finite collection window; require `EV_SW/SW_LID`
values 1 then 0 with matching `SYN_REPORT` frames and attributable GPIO IRQ
activity. Distinguish initial state, physical transitions and duplicate/bounce
reports. Stop on missing edges, reversed polarity or unexpected behavior;
do not change polarity/debounce and repeat in the same unreviewed packet.
This measures input events only, not suspend, wake or hinge-angle support.
