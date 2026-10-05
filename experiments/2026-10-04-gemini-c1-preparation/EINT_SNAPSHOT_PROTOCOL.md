# EINT5 read-only snapshot protocol (C1-5)

Status: draft for coordinator review, 2026-10-07. Reader patch c1/0012
implemented; no candidate or device action yet. A software-triggered EINT is not part of this protocol.

## Question

C1-3 and C1-4 showed GPIO66 following the lid while EINT5 never fired. The
[EINT5 analysis](README.md#eint5-after-c1-4-offline) leaves three candidates:
EINT5's configuration registers do not hold what the driver wrote, its status
bit never sets, or the status sets but the handler never runs. One snapshot of
EINT5's bits in the controller registers, lid open and closed, separates them,
with the working PMIC line (EINT176) as the control.

## Why a new kernel

The C1 kernels have `CONFIG_DEVMEM` off, so no userspace tool can read the
controller. Enabling `/dev/mem` would expose writable physical memory, which is
far more than this needs. Instead, a C1-only, default-off patch adds one
root-only, read-only debugfs file that performs exactly the reads below and
nothing else.

## Resource

The EINT controller is the `eint` region of the MT6797 pinctrl node,
`0x1000b000`, size `0x1000`, in the mainline `mt6797.dtsi` used by the C1 DTB
and in the booted C1 DTB. The public vendor DT places its EINT controller at the
same address. The reader uses the pinctrl driver's own mapping of that region;
it maps nothing new.

## Reads

Register offsets are mainline `mtk_generic_eint_regs`, which match the public
vendor driver's table. Port 0 holds EINT0–31 (EINT5 is bit 5); port 5 holds
EINT160–191 (EINT176 is bit 16). Each read is one 32-bit `readl`.

| Register | Port 0 | Port 5 | Routine reader |
| --- | --- | --- | --- |
| status | `0x000` | `0x014` | mainline handler on every interrupt |
| mask | `0x080` | `0x094` | mainline `mtk_eint_get_mask()`; vendor dumps |
| sensitivity | `0x140` | `0x154` | mainline `mtk_eint_can_en_debounce()` |
| polarity | `0x300` | `0x314` | vendor `mt_eint_get_polarity()` on every trigger record |
| soft trigger | `0x200` | `0x214` | vendor `mt_eint_get_soft()` |
| domain enable | `0x400` | `0x414` | vendor domain debug read |

Plus one debounce-control word for EINT4–7 at `0x504` (EINT5 is byte 1), read by
mainline `mtk_eint_debounce_process()`. That is 13 reads per snapshot.

Read semantics: status is not cleared by reading; both drivers clear it with a
separate write to the acknowledge register at `0x040`, which the reader never
touches. The other registers are configuration registers that the drivers
read back routinely. No set, clear or acknowledge alias is read or written.
This rests on the public mainline and vendor drivers; no register document was
consulted for this protocol.

## Sequence

On the C1-4 package plus only the reader patch (c1/0012, file
`/sys/kernel/debug/mtk-eint-snapshot`), otherwise the same candidate
composition; identify it by boot2 SHA-256 and package inventory, since the
release string is unchanged:

1. Confirm boot identity, release and USB SSH; mount debugfs read-only if
   needed.
2. Lid open: read the snapshot file once, GPIO66's line in
   `/sys/kernel/debug/gpio`, and `/proc/interrupts`.
3. Owner closes the lid and keeps it closed: the same three reads.
4. Owner opens the lid: the same three reads.
5. Save `dmesg`, seal, return through the reviewed recovery.

Budget: three snapshots, 39 register reads in total, one lid cycle, no writes,
no retry, no event capture needed.

## Decision branches

- **EINT5 status sets on a lid change, mask clear, count still 0.** The bit is
  latched but never dispatched; review the parent chain and handler for port 0
  offline. A software trigger would not add information.
- **Status never sets; sensitivity edge, polarity opposite the pin level, mask
  clear.** The pad signal does not reach the EINT block in GPIO mode. Next is
  the EINT pin function (mode 1, `EINT5`) or a separately reviewed software
  trigger.
- **Mask set, sensitivity level, or polarity equal to the pin level.** The
  driver's configuration does not stick; diagnose `mtk-eint` set-type and
  unmask offline.
- **EINT176 bits inconsistent with its working interrupt.** The reader or the
  offsets are wrong; stop and recheck before interpreting EINT5.
