# MT6797 infracfg reset repair design

## Accepted public IDs

The binding exposes a compact input namespace rather than leaking inferred
hardware-bank positions:

| Public ID | Function | Internal ID | Assert | Deassert | Mask |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | thermal controller | 0 | `0x120` | `0x124` | `BIT(0)` |
| 1 | PMIC wrap | 32 | `0x140` | `0x144` | `BIT(0)` |

The existing MediaTek `rst_idx_map` translates public ID 1 to internal bank 1
bit 0. The descriptor's two base offsets are `0x120` and `0x140`; their
non-contiguous spacing intentionally omits RST1.

## Fail-closed boundary

The generic SET/CLEAR path gains a pure resolver that checks the translated
bank against `rst_bank_nr` before deriving an address. Its output is the only
address and mask passed to `regmap_write()`. The DT index resolver likewise
checks the compact map before returning an internal ID.

This yields three independent refusals:

1. a DT input outside the two-entry map returns `-EINVAL`;
2. the historical linear input 64 is outside that public map;
3. a malformed map entry outside the two physical descriptor banks is rejected
   by the SET/CLEAR resolver before any regmap call.

## RST1 quarantine

Mainline's generic MediaTek header suggests RST1 SET/CLEAR at `0x130/0x134`,
but no exact MT6797 vendor or LK access was found. No RST1 base is present in
the descriptor and its historical inputs are removed from the local binding.
They may return only with an attributable primary source and a separate review.

The same rule applies to the other names inherited from the historical 4.9
header. Their names and bit positions are insufficient proof of a safe reset
transaction.

## Runtime separation

PMIC wrap is the sole current infracfg reset consumer. Changing its public ID
from 64 to 1 preserves source-level DTS use of
`MT6797_INFRA_PMIC_WRAP_RST`, while the map sends it to internal ID 32 and the
correct SET/CLEAR pair. This is the first real reset transaction on that path,
so the production patch is not itself a boot candidate.

The disabled thermal node gains no reset property here. Its later use of ID 0
is conditional on a separate PMIC-wrap serviceability boot and completion of
the remaining thermal/AUXADC ownership gates.
