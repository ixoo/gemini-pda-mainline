# RTC collector source correction, 2026-09-08

Offline source analysis found a hardware write hidden behind the original
collector's filtered `/proc/driver/rtc` read. The collector now omits that
interface. No device access or RTC operation was performed for this audit.
Historical captures remain unchanged; they cannot establish absence of RTC
register writes.

## Reproducible source chain

The [input receipt](rtc-source-inputs-20260908.json) pins repository revisions,
paths, byte lengths and SHA-256 digests. Each public input is retrievable as
`https://raw.githubusercontent.com/<repository>/<revision>/<path>`; no
third-party source is included here. The Gemian reference is
`gemian/gemini-linux-kernel-3.18` at
`59e00a9144d782e148332009a835b99c43382467`.

1. `drivers/rtc/rtc-proc.c`, `rtc_proc_show()`, calls `rtc_read_time()` before
   emitting the record. A userspace `grep` cannot suppress that callback.
2. `drivers/rtc/interface.c` dispatches the time read to the driver's
   `read_time` operation. `drivers/misc/mediatek/rtc/mtk_rtc_common.c` assigns
   `rtc_ops_read_time()`, which calls `hal_rtc_get_tick_time()`.
3. `drivers/misc/mediatek/rtc/mtk_rtc_hal_common.c` implements that helper by
   reading BBPU, adding the key and RELOAD bits, writing BBPU, then calling
   `rtc_write_trigger()`. The trigger writes `1` to WRTGR and waits for busy
   completion before the time-counter reads.
4. The RTC Makefiles select the MT6351 implementation for MT6797 and include
   the common implementation above.

This establishes a source-level side effect, not an observation of a physical
transaction on the historical boots. The exact installed Gemian binary was
not matched to this reference during this audit. The source nevertheless
invalidates treating the old access as demonstrably hardware-read-only.

## Retained metadata

The collector retains RTC `name`, `hctosys` and `wakealarm`. In the pinned
Gemian `drivers/rtc/rtc-sysfs.c`, the first two use cached information.
`wakealarm_show()` calls `rtc_read_alarm()`; that public function copies the
RTC core's cached `aie_timer` fields and does not invoke the driver's hardware
alarm callback. This must not be confused with `__rtc_read_alarm()`, which
does invoke that callback. The retained output therefore describes cached
alarm state, not validated hardware alarm programming. This conclusion is
specific to the audited source, not a universal guarantee for other kernels.

## Mainline consequence and limit

At upstream Linux revision `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`,
`drivers/rtc/rtc-mt6397.c` reads the time counters and checks second rollover
without the vendor BBPU reload sequence. The existing register-layout match
does not establish whether MT6351 requires that sequence for a fresh or
coherent sample. Do not promote the historical match-only RTC patch based
on layout alone. Resolve the reload semantics before defining a bounded
hardware validation protocol; this audit adds no RTC node or kernel patch.

Validation: shell syntax and ShellCheck for the edited collector, plus the
repository checks. No kernel build or hardware time/alarm test was run.

The subsequent [retained-kernel binary audit](rtc-binary-audit-20260908.md)
confirms the reload writes in the historical boot kernel and identifies its
selected counter-based rollover path and conditional alarm-programming
fallback. It does not establish current runtime transactions or mainline
compatibility.
