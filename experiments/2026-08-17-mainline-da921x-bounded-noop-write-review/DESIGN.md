# Gate-6 DA921x bounded no-op design

## Decision

The least invasive candidate transaction is one same-value write to the
disabled Buck B output's unselected voltage register:

```text
primary address 0x68
one write message [0xda, 0x46]
VBUCKB_B 0x46 -> 0x46
no retry and no second write
```

This is a design result, not permission to implement or execute the write.
Four blockers in [`contract.json`](contract.json) keep the result fail-closed.

## Why this register and value

The named unit's repeated identity transcript observed `BUCKB_CONT` `0x5e =
0x00`, `VBUCKB_A` `0xd9 = 0x46`, and `VBUCKB_B` `0xda = 0x46`. The later
read-only provider independently reported Buck B disabled with selector 70,
which is 1.00 V in the public legacy-family table.

The manufacturer's DA9213/DA9214/DA9215 register contract defines:

- `BUCKB_CONT` bit 0 as enable, bit 4 as A/B voltage selection, bits 2:1 as
  GPI enable control, and bits 6:5 as GPI voltage selection;
- `VBUCKB_A` at `0xd9` and `VBUCKB_B` at `0xda`, with selector `0x46`
  representing 1.00 V; and
- `CONTROL_A` `0x56` bit 7 as `V_LOCK`, which must be clear before host writes
  to `0xd0..0x14f` can be meaningful.

Consequently, the exact observed `0x5e = 0x00` means Buck B is disabled,
directly controlled, and selects `VBUCKB_A`. `VBUCKB_B` is therefore the
unselected setting. Writing its existing full byte back unchanged avoids a
selector change, slew-mode change, rail enable, GPI policy change, and voltage
transition. The transaction uses the direct primary-address register window
and must never access `PAGE_CON`.

Public source: Renesas, [DA9213/14/15 Datasheet, revision 03.61][datasheet].
The experiment relies only on the register definitions above; it does not use
manufacturer policy code.

[datasheet]: https://www.renesas.com/en/document/dst/da92131415-datasheet

## Exact preflight

All checks occur under the root I2C adapter lock and one valid Linux
generation/cookie lease. Any mismatch ends the attempt before the write.

1. Require the exact parent identity and `maxcpus=8`, with CPUs 0--7 online and
   CPUs 8--9 offline.
2. Require no regulator consumer, setter, CPU request, suspend transition, or
   provider-owner transition.
3. Require an independently reviewed firmware-writer exclusion for the whole
   transaction window. The current stopped-receiver handoff and Linux lease do
   not yet satisfy this condition.
4. Read full bytes at `0x56`, `0x51`, `0x5e`, `0xd9`, and `0xda`. Require
   `CONTROL_A & 0x80 == 0`, `BUCKB_CONT == 0x00`, and both selector bytes equal
   `0x46`. Retain the full `CONTROL_A` and `STATUS_B` bytes for post-comparison.
5. Require the I2C6 transfer ledger to account for every earlier transfer and
   to show no foreign or write-shaped transaction.

No `PAGE_CON`, event, enable, consumer, CPU, or voltage-setting operation is
permitted during preflight.

## One allowed transaction

With every preflight still true, send exactly one I2C message to address
`0x68`, length two, payload `[0xda, 0x46]`. Accept only a return value of one.
There is no retry. A short, timed-out, or ambiguous completion enters the fault
path and never emits an inverse or compensating write.

The same-value write deliberately makes rollback an identity condition: the
starting state is the requested state. It does not claim to prove a usable
voltage setter or an electrical transition.

## Readback and recovery

After exact completion, read `0xda` immediately and after the predeclared
settle interval. Both reads must return `0x46`. Re-read `0x56`, `0x51`, `0x5e`,
and `0xd9`; require full-byte `CONTROL_A` and `STATUS_B` equality, `0x5e =
0x00`, and `0xd9 = 0x46`. I2C6 accounting must contain one and only one
register-data write with the exact payload.

Keep CPUs 8--9 offline and use the already-proven native reboot path. Changed-
boot-ID Gemian recovery must find the exact boot2 candidate unmounted and
unchanged. Any postcondition mismatch is a failed Gate-6 attempt, not a reason
to send another regulator write.

## Blockers and next discriminator

The contract is not implementation eligible because:

- mainline cannot yet invoke or replace the historical `SEMA_I2C_DRV`
  firmware pause lease, so exclusion of other I2C6 writers is not closed;
- the native controller has runtime proof for the fixed pointer/read shape,
  not this one-message two-byte write shape;
- Gate 5 counted 20 I2C6 transfers while the explicit identity and observer
  paths account for 18; the remaining two must be attributed; and
- `V_LOCK`, `STATUS_B`, and the complete direct-register preflight have not
  been observed on the exact serviceable mainline path.

The authoritative ordered follow-up and its exit criteria remain solely in
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
