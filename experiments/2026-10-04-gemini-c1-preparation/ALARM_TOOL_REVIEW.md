# RTC alarm tool and cleanup review

Offline review, 2026-10-04. Kernel source is the exact bounded-RTC build input
`45143bfc`; the callback successor is recorded separately in the
[alarm-enable receipt](results/rtc-alarm-enable.json). No device, candidate or
RTC operation was performed. This review does not admit an executable protocol.

## Kernel cleanup gap and successor

The selected `mtk_rtc_ops` supplies `set_alarm` but no `alarm_irq_enable`.
`RTC_AIE_OFF` dispatches to `rtc_alarm_irq_enable()`, which may remove the class
alarm timer before discovering the missing callback and returning `-EINVAL`.
`rtc_alarm_disable()` also skips hardware disable when the callback is absent.
File release deliberately leaves alarms alone. Therefore removing a software
timer or closing the device is not evidence that the physical alarm was cancelled.
`RTC_WKALM_SET` with enabled=false is not a substitute: it removes the class timer
but does not call the driver's disabled `set_alarm` branch in this core path.

The successor registers the standard callback, using the same alarm/one-shot
mask and write trigger as `set_alarm`. It preserves unrelated interrupt bits,
returns transport errors and reports failures because the core's void cleanup
helper discards its result. It adds no driver retry. One `RTC_AIE_OFF` can cause
two callback invocations when removing the sole enabled timer: timer cleanup,
then the explicit enable/disable delegation. The new fixture reproduces the
old missing-callback failure and checks the actual delegation/disable functions
against a modeled single-timer removal path. It does not execute the full
kernel timer queue or prove physical cancellation.

The callback also runs after normal one-shot expiry through core timer work,
adding operations to a path that previously skipped hardware disable. Those
operations belong in the eventual candidate budget, even when the IRQ handler
already cleared the alarm bit. Callback success alone cannot prove that the
write trigger physically latched, and a failed result is not permission to retry.

## Retained ram-root tool inventory

The unchanged installed version candidate's initramfs is
`059c62f7e3dca63df72cd94c1ad0af312834323e17f755838801e836aa6c5f6e`.
A checksum-verified archive inventory and version-marker inspection found
`bin/busybox`, 1,914,704 bytes, SHA-256
`52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`,
with `BusyBox v1.36.1 (Ubuntu 1:1.36.1-6ubuntu3.1)`. There is no separate
`rtcwake` or `hwclock` archive member, and no `rtcwake` name string was found
in that binary. No applet was executed; this does not certify the complete
applet inventory or match the Ubuntu-patched binary to upstream source.
It supplies no admitted alarm executable for C1.

## BusyBox 1.36.1 source behavior

The public [upstream source archive](https://busybox.net/downloads/busybox-1.36.1.tar.bz2)
has SHA-256 `b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314`.
Only two files were retained privately for source review:

| File | SHA-256 |
| --- | --- |
| `util-linux/rtcwake.c` | `0de9065a361d44793a7a018a54b602423cd74d7f7a1fadaf60c2cf39c783b70d` |
| `util-linux/hwclock.c` | `8f72c7660bc19217d930e3085abe5c47d9f808379bd88c68744b4be20f3afd7d` |

The following facts describe that public source, not a verified runnable
applet in the retained candidate:

- The default mode is standby, so omitting `-m on` would request system sleep.
- Without explicit `-u`/`-l`, it consults adjtime. The selected device and clock
  interpretation must therefore be explicit in any future use.
- A relative request uses RTC time plus seconds plus one; `-s 10` requests
  approximately eleven seconds, not exactly ten.
- For a near-term alarm, `setup_alarm()` calls `RTC_ALM_SET` followed by
  `RTC_AIE_ON`, rather than a single `RTC_WKALM_SET`.
- It calls global `sync()` after programming. This effect is not an RTC read.
- Mode on repeatedly reads the RTC file until an alarm flag arrives, with no
  built-in monotonic deadline. A read error breaks the loop, after which it
  still attempts disable and returns success if that disable succeeds.
- Normal completion calls `RTC_AIE_OFF`. Fatal ioctl errors or external process
  termination do not guarantee reaching that call; file close does not cancel
  the alarm. An external timeout alone therefore does not provide cleanup.

Consequently, the earlier unqualified `rtcwake -m on -s 10` suggestion is not an
admitted finite test. Before choosing a tool, require a pinned executable and
source/configuration provenance, an explicit device and time interpretation,
one finite wait with separate event/error classification, and checked cleanup
on both success and failure. Refuse an inherited enabled/pending alarm before
replacement; cached class state alone may not describe malformed or rejected
hardware alarm state. Do not silently clear such an alarm to make a test pass.

The RTC class can inherit a future hardware alarm at registration and core work
can program later queued timers. The final review must account for those paths,
the single-timer assumption, the added disable callback operations and failure
behavior. Preserve the driver/core error log and exact IRQ/event evidence;
neither a successful tool exit nor an increased clock value proves alarm delivery
or cancellation. This review adds no tool installation, wake policy, clock write,
raw PMIC/RTC access, radio action or automatic recovery.
