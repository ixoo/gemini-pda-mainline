# Read-only I2C6 attribution and DA921x preflight design

## Fixed parent and changed boundary

The parent is the exact Gate-5 profile
`da921x-lk-clock-readonly-provider`, which booted as
`7.1.3-gemini-da921x-lkro` with 20 successful I2C6 transfers and zero
register-data writes. This child changes only observation:

- patch `0283` retains a bounded description of the first 32 I2C6 adapter
  calls on the access-controlled instance; and
- patch `0284` attributes provider reads by phase and performs two fixed
  read-only passes over `0x56`, `0x51`, `0x5e`, `0xd9`, and `0xda`.

It adds no DT change, writable provider operation, consumer, firmware-owner
claim, retry, register-data write, or CPU request.

## Transfer ledger

Each entry stores only message count, the address/flags/length of at most two
messages, the first byte of message zero, and the final adapter return value.
For this experiment that first byte is the register pointer. A second payload
byte is never retained. The ledger is static, capped at 32, cannot trigger an
I2C operation, and reports overflow rather than wrapping.

Every acceptable runtime entry has the fixed pointer/read shape:

```text
message 0: address 0x68 or 0x69, flags 0, length 1, pointer byte
message 1: same address, I2C_M_RD, length 1
adapter return: 2
```

The exact 30-entry expectation is in [`contract.json`](contract.json). Entries
0--13 are the two identity passes. Entries 14--15 test the source-based
inference that provider registration queries enable state once for each buck.
Entries 16--19 are the explicit observer. Entries 20--29 are two complete
preflight passes. Any other sequence, shape, result, count, or overflow keeps
the attribution blocker open.

## Preflight

The provider records completed reads in three phases: registration, observer,
and preflight. After the existing four-read observer, the preflight reads:

| Register | Meaning | Runtime acceptance |
| --- | --- | --- |
| `0x56` | `CONTROL_A` | full byte stable; `V_LOCK` bit 7 clear |
| `0x51` | `STATUS_B` | full byte recorded and stable |
| `0x5e` | `BUCKB_CONT` | exact `0x00` |
| `0xd9` | `VBUCKB_A` | exact `0x46` |
| `0xda` | `VBUCKB_B` | exact `0x46` |

All five bytes must match across both passes. The resulting `safe_prestate`
flag is only a read-only classification. It does not close firmware ownership,
prove a write transport, or authorize the no-op transaction.

## Decision boundary

An exact pass can close only design blockers B3 (transfer attribution) and B4
(live preflight). B1 (firmware-writer exclusion) and B2 (native two-byte write
shape) remain blocking by construction. CPU8 and CPU9 remain offline. The
authoritative ordered follow-up is owned by
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
