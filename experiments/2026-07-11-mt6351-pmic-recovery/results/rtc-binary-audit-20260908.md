# Retained Gemian RTC read-path audit, 2026-09-08

This private RE-VM analysis confirms the reload writes in the retained
Gemian boot kernel and identifies additional behavior that a match-only
MT6351 RTC patch would not reproduce. No device connection or hardware
operation was performed. These are compiled-code findings, not observations
of transactions on a running device.

## Identity and method

The [binary receipt](rtc-binary-receipt-20260908.json) identifies the retained
boot image, its decompressed kernel and the reconstructed ELF. The boot-image
checksum matches the active-boot capture in the historical
[vendor provenance](vendor-kernel-provenance.txt). This is the captured boot
kernel, not the different installed-package image listed in that provenance.
It does not establish the device's current boot identity.

The Android header selects an 8,429,825-byte kernel payload at page size 2048.
Decompressing its first gzip member produces the exact retained `Image`;
the remaining 130,745 bytes are the appended DTB. The reconstructed ELF's
entire `.kernel` section also equals that `Image`. Every instruction byte
in the seven inspected function spans was checked against the verified
image. Span hashes include trailing alignment instructions where present.
Private disassembly remains in the RE VM; no binary or disassembly is published.

GNU AArch64 objdump 2.42 was used with `--disassemble=SYMBOL` for the symbols
listed in the receipt. The public MT6797 `mt_rtc_hw.h` header in the
[source receipt](rtc-source-inputs-20260908.json) names the decoded registers;
the instruction immediates independently establish their addresses.

## Compiled time-read sequence

`rtc_ops_read_time()` calls `hal_rtc_get_tick_time()` while holding the vendor
RTC spinlock with interrupts saved. The latter helper:

1. Reads BBPU at `0x4000`, ORs the returned 16-bit value with `0x4320`
   (key plus RELOAD), and writes it back through `pwrap_write()`.
2. Writes `1` to WRTGR at `0x403c`, then calls `rtc_busy_wait()`.
3. Calls `rtc_get_tick()`. That reads `RTC_INT_CNT` at `0x4202`, followed by
   seconds, minutes, hours, day of month, month and year at `0x400a`,
   `0x400c`, `0x400e`, `0x4010`, `0x4014` and `0x4016`. It does not read the
   day-of-week register in this helper.
4. Reads BBPU again and performs another key-plus-RELOAD write. There is no
   WRTGR write or busy-wait call between this second BBPU write and the next
   counter read.
5. Reads `0x4202` again. If the second counter is less than the first, it
   calls `rtc_get_tick()` once more; otherwise it returns the first tuple.

This selects the public source's `RTC_INT_CNT` branch, not its alternative
seconds-only rollover check. The header defines the counter at base plus
`0x202` and names an `0x7ff` mask; the compiled reads return the low 16 bits
without applying that mask. No counter frequency or physical latch behavior
is inferred from these constants.

## Additional callback effect

After converting the tuple to a timestamp, the compiled time callback tests
the sign bit. Its negative-time branch replaces the returned tuple with the
default date and calls `hal_rtc_set_alarm()`. That function calls the alarm
time writer, then ORs `0x5` into IRQ_EN at `0x4004` and issues the write
trigger. Thus the fallback can program and enable an alarm; it is not merely
a software adjustment to the returned time. This branch is present in the
captured binary. There is no evidence here that it ran during any capture.

## Implementation consequence

The [collector correction](rtc-source-audit-20260908.md) is supported by
the retained binary, beyond the initial source comparison. Keep ordinary
Gemian time reads outside the default read-only collector.

MT6351 RTC integration still needs an explicit decision about the two reload
writes, trigger ordering and counter-based rollover detection. `0x4202` also
lies outside the historical `0x4000`–`0x403f` RTC resource. A variant using
that counter must represent its resource ownership; extending a match table
does not do so. The present evidence neither proves that upstream's simpler
read sequence fails nor validates it on MT6351. Do not copy the vendor's
alarm-programming fallback into a time-read operation.

Validation was offline image/ELF byte comparison and bounded disassembly
review, followed by repository publication checks. No kernel patch, build,
device test or new boot candidate was produced by this audit.
