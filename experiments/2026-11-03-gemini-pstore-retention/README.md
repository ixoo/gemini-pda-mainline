# Experiment: what pstore's -28 means, and which restarts keep the record

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-03-gemini-pstore-retention` |
| Status | `running`: T1 passed on boot `7978f9ea`; the fix is live on boot `fccba04c`; T2 not run |
| Subsystem | `fs/pstore`, ramoops on the reserved `0x44410000` range |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-03 to 2026-11-04 |
| Investigator(s) | project session |
| Tracking issue | none |

## Question

[Bluetooth T5c](../2026-11-02-gemini-bluetooth/README.md) logged
`pstore: backend (ramoops) writing error (-28)` on an Oops, and `/sys/fs/pstore`
was empty after the restarts that followed T5 and T5c. Does ramoops fail to
record crashes on the station, or is the record lost some other way?

## The -28 is not a failed record (read from the code)

Read in the prepared `series-a53-station` source. The series' `ram.c` changes are
config-gated ledgers, and the write path below is upstream's. [T1](#t1-result)
confirmed it on the device.

- `pstore_dump()` in `fs/pstore/platform.c` loops `while (total < kmsg_bytes)`,
  writing one part each pass. `kmsg_bytes` is
  `CONFIG_PSTORE_DEFAULT_KMSG_BYTES`, 10240 in the station config.
- `ramoops_pstore_write()` in `fs/pstore/ram.c` accepts only part 1:
  `if (record->part != 1) return -ENOSPC`. Its comment says this is deliberate,
  so a report isn't split across records.
- One part is at most `bufsize`, 4084 bytes with `record-size = 0x1000` (0x1000
  less the 12-byte zone header). So `total` is below 10240 after part 1, part 2
  runs and gets `-ENOSPC`, and `pstore_dump()` reports the first non-zero result.
- Part 1 can't be what returned -28. Its other `-ENOSPC` is `!cxt->dprzs`, but
  with no dump zones `PSTORE_FLAGS_DMESG` stays clear and `pstore_dump()` is never
  registered. A failed header returns `-ENOMEM`, not -28.

So every crash prints this line on this geometry, and part 1 has been stored in
RAM when it does. It explains no missing record.

**Record size is not the problem, and stays as it is.** `oops_exit()` dumps after
the end-of-trace marker, and the dump keeps the newest log that fits. T5c's Oops,
from the first fault line to that marker, is about 2.4 KB of text and about 3.1 KB
with syslog prefixes, so it fits in 4084 bytes with some earlier context. A longer
trace or module list would lose its start from that record, but the 64 KiB console
record still holds it. Changing `record-size` would also move the dmesg zones away
from the layout Gemian reads ([baseline](../../docs/hardware/gemini-gemian-baseline.md#exact-active-ramoops-layout)).

## Fix

`pstore.kmsg_bytes=2048` on the station command line, in
`configs/gemini-a53-station-wifi.fragment`. It removes the false error and nothing
else:

- `kmsg_bytes` only bounds that loop. The buffer and the stored part don't change.
- `kmsg_dump_get_buffer()` copies whole records, so part 1 falls short of 4084 by
  less than one log line, about 1 KB at most. Part 1 therefore always reaches 2048
  and part 2 never runs. If the whole log is shorter, the loop ends on no more data.
- The command line is the right place: the Kconfig value has a prompt only under
  `CONFIG_EXPERT`, which is off, and `CONFIG_CMDLINE_FORCE` is on.

It is built-in configuration, so it waits for the next image. Until then the same
effect is available at run time with `mount -t pstore -o kmsg_bytes=2048`.

## Why the records were empty

The custodian mounted pstore before each read, so these are real empty results.
`/init` does not mount it.

| Restart | Reader | Result |
| --- | --- | --- |
| Gemian `reboot`, 2026-09-11, returned `wdt_by_pass_pwk` | Gemian | marker [retained](../2026-09-07-mt6797-wifi-observer-feasibility/RETENTION_RESET_COMPARISON.md) |
| Watchdog return, 2026-08-29, Gemian-derived candidate | Gemian | console and pmsg [retained](../2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt) |
| Station busybox `reboot`, boot `eda50de3` | Gemian | console record [retained](../2026-10-30-mainline-dev-station/README.md), ending at `reboot: Restarting system` |
| Esc hold, 2026-09-11, returned `power_key` | Gemian | marker [lost](../2026-09-07-mt6797-wifi-observer-feasibility/RETENTION_CONTROL.md) |
| Esc and side key after T5's hang, boot `fcb98505` | station | empty |
| After T5c's Oops, boot `0633cf9d`; the owner reported "device rebooted on boot2", method not stated | station | empty |

Even with no crash record, a surviving console record should have appeared.
`loglevel=4` lets only levels 0-3 reach it, but T5c's boot had logged 9 such lines
before the Oops, and T5c itself should have left its Oops there too.

**Inference:** the key restart does not preserve this RAM. That's three negatives
and no positive, one with an unstated method, and none on a controlled comparison
with one station image. The earlier record stops short of naming where the loss
happens, and so does this one: it could be DRAM contents or the zone header, and a
reader sees only an absent record. T1 and T2 make the comparison.

**Limits this leaves:**
- A hang recovered with the keys leaves no record, under any pstore setting.
- The station's `panic=0` and lack of `panic_on_oops` mean an Oops never restarts
  by itself, so T5c's Oops was in RAM only until the owner's restart.
- `CONFIG_SOFTLOCKUP_DETECTOR` and `CONFIG_HARDLOCKUP_DETECTOR` are off, so nothing
  turns a silent hang into a panic.
- `loglevel=4` keeps info-level context out of the console record.

## Test (predeclared)

Through the device custodian, one at a time, T1 first. No radio is needed: nothing
Wi-Fi or Bluetooth is loaded. Each uses one physical restart and one owner boot2
selection. Neither is repeated with the same image.

**Before each:** stable power; verify station identity and boot ID; no other test
running; mount pstore if unmounted and preserve whatever it holds; generate a fresh
UUID; `echo "<3>pstore-retention <test> <uuid> <boot>" > /dev/kmsg` and confirm one
match in `dmesg`; `sync`; `mount -o remount,ro /mnt/data`. If the remount fails,
stop and report which process holds it.

### T1: a crash record survives a warm restart

Can run on the current image, which also tests the -28 claim: the current image
still has the 10240 default.

**Hypothesis:** the panic path writes a dmesg record although it reports -28, and a
TOPRGU/PSCI warm restart keeps it for the next boot.

1. Record `/sys/module/pstore/parameters/kmsg_bytes`.
2. Tell the owner to be ready to hold the side key, since a plain restart lands in
   Gemian.
3. `echo 10 > /proc/sys/kernel/panic; echo c > /proc/sysrq-trigger`. This panics
   with `sysrq triggered crash`, dumps with `KMSG_DUMP_PANIC` through the same loop,
   and restarts after 10 s through the ordinary restart chain.
4. On the next boot, verify the boot ID changed, mount pstore, and copy it to
   `artifacts/` privately. Report only: file names and sizes, whether the marker is
   in `console-ramoops-0`, whether `sysrq triggered crash` is in `dmesg-ramoops-0`
   and in the console record, and whether `writing error (-28)` is in the console
   record. Extract only the tokens `androidboot.bootreason`, `boot_reason` and
   `mrdump_ddrsv` from `/proc/device-tree/chosen/bootargs`, which also holds a
   device identifier.

| Observation | Meaning | Next |
| --- | --- | --- |
| dmesg record with the panic, console record with the marker | Warm restart keeps the crash record; the code reading holds | T2 |
| As above, and `-28` in the console record | The false error shown directly | T2; the fix is confirmed on the next image |
| Console record only, no dmesg record | The dump failed in a way the code reading missed | Stop; offline, no T2 |
| Empty | This warm restart lost it, unlike Gemian's | Stop; read boot reason, compare with `eda50de3`'s `reboot`; no T2 |
| Landed in Gemian | Not a failure | Read it there, it uses the same layout; Gemian's tree differs, so name it in the record |
| No restart within 60 s | Panic restart does not work here | Owner recovers with the keys; record it; T1 says nothing on retention |

#### T1 result

Run by the custodian on boot `7978f9ea`, image `8f2c1167`, `kmsg_bytes` 10240, radios
down, `/mnt/data` read-only. The next boot was `3fb07fd4`, same image; the owner held
the side key and reports "restarted on boot2". I checked the private copy under
`artifacts/station-work-44/pstore-t1/private/` against the custodian's report.

**Observed:**
- `dmesg-ramoops-0`, 4049 bytes, starts `Panic#1 Part1` and holds the marker and
  `sysrq triggered crash`. There is no second dmesg file.
- `console-ramoops-0`, 1593 bytes, holds the marker, the panic, and
  `pstore: backend (ramoops) writing error (-28)`, followed by `Rebooting in 10 seconds..`.
- `androidboot.bootreason=wdt_by_pass_pwk`, `boot_reason=4`, `mrdump_ddrsv=yes`.

**This shows:** the record is stored even though -28 is reported, and this warm restart
keeps both records for the next station boot. It's the table's second row.

**Limits:**
- One run, and through a panic. An Oops takes the same loop with `KMSG_DUMP_OOPS`, but
  that dump hasn't been read back. T5c's Oops was still lost.
- `wdt_by_pass_pwk` followed a software panic restart with the side key held, so that
  token doesn't name a key press or a watchdog bite.
- It says nothing yet about the key restart, which is T2.

### T2: does the key restart keep this RAM

Only after T1 retained. Same image and reader as T1, so only the restart differs. No
crash is needed: the marker is enough.

1. After the common steps, the owner holds Esc and the side key until it restarts,
   and selects boot2. PMIC register `0x02b6` read `1201` on boot `fcb98505`: one-key
   long-press reset, at the 11 s from
   [0530](../2026-11-03-gemini-pmic-keys/README.md).
2. Collect as T1.

| Observation | Meaning | Next |
| --- | --- | --- |
| Empty, reason `power_key` or similar | The key restart does not keep it, on one image against T1 | Record as a durable fact; hangs need another route |
| Marker retained | It does keep RAM from a healthy system | T5 and T5c's emptiness needs another explanation; offline |

### On the next image with the fix

From the first boot: `/sys/module/pstore/parameters/kmsg_bytes` reads 2048. The -28
line can then only be checked on the next real crash; no separate crash is warranted
for a message.

**Result:** on boot `fccba04c`, image `96338704`, it reads 2048, as the custodian
reports. No crash has happened on this setting, so the -28 line's absence is not
observed yet.

## What this enables, if T1 passes

Before a test that might Oops, `echo 1 > /proc/sys/kernel/panic_on_oops; echo 10 >
/proc/sys/kernel/panic` would turn an Oops into a warm restart that keeps the record,
with no image change. A silent hang needs more: a hardware watchdog bite, which the
August return suggests would keep RAM. Neither is designed or tested here.
