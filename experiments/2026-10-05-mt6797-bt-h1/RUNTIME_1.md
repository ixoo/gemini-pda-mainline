# C3 runtime 1: Bluetooth H1 not demonstrated

Status: consumed, 2026-10-06. The laptop device custodian ran one attended
boot under [the protocol](PROTOCOL.md), with no retry. Figures are from its
report; the sealed log and raw bytes stay private on the owner's machine.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `e49ebd34ee6e390ad26d62019b67824bd50bd1afcffe53bceb65915cc68f7682` |
| Release | `7.1.3-gemini-a53-wmt-versions` |
| Mainline boot ID | `4aa1e231-68b8-48a0-85ed-a863cad08280` |
| Sealed log SHA-256 | `5231d3710685c70de9d656f5a61754c22b593705d51303748192a20916cfc505` (1912 records, 135214 bytes) |
| Gemian boot ID after recovery | `c45ebb76-e126-40f2-a4df-ef8bf8b1a137` |

## Observations

- **Preparation.** Region 19 gave two identical preimages, and the WMT
  clear-prefix and suffix readback passed.
- **Control passed.** `one-shot WMT negotiation: result=0 phase=5
  clocks-held=1`. The full exchange sent 15 bytes and received 20, in five
  services and two frames. The link was at TX/RX sequence 1/1 and peer/local
  ACK 0/0 before Bluetooth.
- **Bluetooth stopped at step one.** `one-shot BT H1: result=-110
  completed=0/5 vcn33-bt-held=1 tx-seq=2 rx-seq=1 peer-ack=1 local-ack=0`.
  BT-on sent its 12-byte frame and received 4 bytes in two services: a bare
  ACK of that frame, and no function-on event. No HCI step ran. VCN33-BT
  stayed on, as designed for a failure.
- **Wrap-up.** The A53 regression passed. The reviewed native recovery ran
  once and Gemian came back on a changed boot.

## Interpretation

The chip acknowledged the BT-on frame at the STP layer, so the task-0 path's
WMT half reached the firmware. The function-on event did not arrive within
the 600 ms deadline.

That deadline was too short to support the protocol's "BT on fails" branch.
The vendor waits `WMT_LIB_RX_TIMEOUT` = 2000 ms for every WMT event, and its
header notes that Bluetooth function-on alone takes about 830 ms on some
phones (`wmt_lib.h` line 70 at the
[pinned vendor revision](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/include/wmt_lib.h#L70)).
H1 is therefore neither demonstrated nor refuted. Dependence on the ROM patch
remains possible, but this timeout does not show it.

## Decision

Do not repeat this candidate. A decision-changing retry needs the vendor's
2 s event wait. If BT-on still produces no event at 2 s, the next step is
Bluetooth after common initialization, which the vendor always runs first.
