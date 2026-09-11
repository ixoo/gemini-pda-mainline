# Console retention across different reset paths

Status: reset-path audit completed; one normal-restart comparator prepared, not executed.
It requires separate owner approval for its marker write and restart. The
[completed Esc control](RETENTION_CONTROL.md) remains a negative result.

## Evidence from the returned boot

Bounded read-only inspection verified Gemian boot
`5257ff6d-7ca3-470f-b1da-24eeb93f48e3` before and after each query, with Linux
`3.18.41+`, MT6797X, Debian 9 and running systemd. The standard pstore service
was not installed under systemd 232; four conventional archive directories
were absent. Inspection of 251 regular startup/configuration files, totalling
215,878 bytes, found no `pstore`, `ramoops`, `ram_console` or `last_kmsg` match.
The eight roots covered systemd units, tmpfiles, init scripts and installed
initramfs hooks/scripts; 127 nonregular entries were skipped. This narrows
standard userspace removal, without excluding other processes or contents
unique to the booted initramfs. No archive or pstore payload was read.

The same boot's arguments report `boot_reason=0`,
`androidboot.bootreason=power_key` and `mrdump_ddrsv=yes`. The bounded log query
found no separate DRAM-preservation status message. The last argument is not
treated as proof that memory survived this reset. Raw command lines remain
private because they contain a device identifier; only these three tokens are
published. The userspace audit and reset-metadata programs have SHA-256
`d045203a694c66640357b9702117db2e32ec91fe988edebc3170690048ebdf18`
and `be7a0d22031f5ee48ed6b3ace8829b3eefcf42898551bde6dcf256bf06bd1f51`.

The [earlier same-version watchdog return](../2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt)
recovered both console and deliberately written PMSG records. It used a
different Gemian-derived candidate and reset path; it cannot establish Esc
retention. The [pstore source audit](../2026-08-28-a72-target-register-capsule/results/retention-path-audit-20260828.txt)
also distinguishes saving an old ring from clearing its new active instance.
An empty returned directory does not locate the loss.

## Compiled reset and preservation paths

Private RE-VM analysis reused the exact retained
[Gemian kernel](../2026-09-08-mt6351-keys-preparation/RESET_BINARY.md#identity-and-method)
and [preloader](../2026-09-08-mt6351-mfd-upstream-preparation/VCN33.md).
The [span receipt](results/retention-reset-paths-20260911.json) pins the inspected
instructions. The reconstructed ELF's complete kernel section equals the
retained Image, and every decoded AArch64 instruction was byte-compared with
that Image. Fixed Thumb branches, bit tests and address literals were checked
against the pinned preloader payload. No firmware was executed.

The kernel registers `mtk_arch_reset_handle` at priority 128. Its ordinary
null-command path selects mode 1 and reaches `wdt_arch_reset` through the
actual callback-table pointer and `wd_sw_reset`. The mode update clears
`0x59` and sets `0x22000014`, preserving the existing DRAM-reserve bit 7.
It invokes `pmic_pre_wdt_reset`, then writes software-reset key `0x1209` to
TOPRGU offset `0x14`. The separate `mtk_rgu_dram_reserved` function can set or
clear bit 7; the ordinary reset function does not establish that bit itself.
These are compiled facts, not current register values or proof that this
captured kernel is the executing binary.

The retained preloader's call at `0x214300` enters the policy at `0x20b58c`.
That policy first reads TOPRGU mode bit 7 at `0x10007000`; a clear bit takes
the reserve-disabled branch. Otherwise it tests bit 16 at `0x10007508`, using
the compiled success/failure diagnostic strings to identify that result.
The successful branch tests bit 17 at the same address, identified by the
self-refresh diagnostics, for at most three attempts. Thus the inspected
preservation path is conditional on several observations. No value of those
fields was read from the device, and their state during the Esc control is
unknown. This does not prove that Esc power-cycled DRAM or identify a clearing
instruction.

## Prepared comparator

The combination of a confirmed `power_key` return, a conditional preservation
path and an earlier positive watchdog result justifies changing the reset
method while keeping healthy Gemian and its console writer/reader. It does
not justify another unchanged export-kernel boot or a DRAM-control write.

The comparator is fixed to the returned boot above and control UUID
`8142a374-220c-447e-8707-f509425d0079`. After owner approval and saving open
work, reuse the Esc control's identity, console-level, descriptor and unique
log-match guards for exactly one 137-byte ASCII write to `/dev/kmsg`:

```text
<11>wifi-retention-v1 control=8142a374-220c-447e-8707-f509425d0079 boot=5257ff6d-7ca3-470f-b1da-24eeb93f48e3 stage=before-normal-restart
```

The final newline is included. Preserve the successful marker receipt, then
arm the same 180-second changed-boot collector before requesting the restart.
After rechecking the old boot, exact marker and client identity, sync once and
issue `/bin/systemctl reboot` once, with no force option or special boot target.
The inspected regular nonsymlink client identifies as systemd 232 and has
SHA-256 `b7247b969b7d4c2d6c2bfe05082315bbacad17bd831b6ff71f7a0e829b980e98`.
Its preflight made no device write. Ordinary Gemian shutdown/restart effects
are part of the requested approval; no direct register or partition operation
is added.

The prepared programs reuse the existing marker and collector, changing only
the fixed boot/control identity and marker stage. Their SHA-256 identities are:

| Program | SHA-256 |
| --- | --- |
| Marker | `8803b869840cd8b83df74e286f93d5e68767ffd1dc81f972d05b793055ec0287` |
| Collector | `7b2baa9a622e4910787f5fedd7115d8ccf6ec66efeeb480e5d9422ba41178a72` |
| Restart request | `c3a4b412b4c1ee582d192242270a7556e0bf551e7f252508be073eadf7017507` |

Their syntax and exact substitutions were checked; the restart request was
reviewed without executing it. They remain private. Changed or mismatched
preflight identity stops the control. A partial write, ambiguous restart
result or timeout preserves evidence and permits no retry, force restart,
Esc hold or alternative recovery action.

Require changed-boot known-good Gemian and stable before/after identity, then
read `console-ramoops` at most once and at most 65,536 bytes, or record absence
without a payload read. Analyze retained bytes in the RE VM and leave Gemian
running. Classify against this exact control and preceding boot:

- Exact marker recovered: one normal-restart retention pass, supporting a
  reset-path distinction; still no export-kernel entry claim.
- Record present without marker: inspect the retained window for truncation
  or filtering; do not call the marker recovered.
- Record absent: normal restart also failed to expose a record; stop relying
  on this console recovery path and require an independent observation before
  another export candidate.
- Missing return, unstable identity or incomplete collection: inconclusive;
  preserve evidence and await owner direction.

No kernel build, marker write, restart or new physical test was performed by
this preparation. Repository checks validate publication, not retention.
