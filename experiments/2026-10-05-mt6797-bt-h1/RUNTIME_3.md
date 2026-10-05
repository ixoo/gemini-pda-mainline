# C3-3 runtime: bounded Bluetooth HCI exchange passes

Status: consumed, all pass, 2026-10-06, under [PROTOCOL_3.md](PROTOCOL_3.md).
The laptop device custodian ran one attended boot with exactly one trigger and
no retry. Figures are from its report; the sealed log, raw replies and the
controller address stay private on the owner's machine.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `24599d428af5f90605fa4c6cc067034a725df76533fb86250ad0c3d0465d547b` |
| Candidate receipt SHA-256 | `71c86e010f0bb60b27c98e5e7dd06a00988b1307a810e4b73e5625a2eed4f90c` |
| Package | commit `cd06b7f5`, inventory `c7d36be7532c66fc604a97e52524f4e2c3afda15a9d7e4f7d83f2911a079a8fc` |
| Mainline boot ID | `f1694fbe-d8cc-42db-90ee-a24c7fb00a72` |
| Sealed log SHA-256 | `865c3a2b510e3109457362becb70ffcc678d545cdd2ef97aaa33db1b87ca7d7f` |
| Gemian boot ID after recovery | `d23cc7f8-4b6e-498a-922d-f5753394d76b` |

## Observations

- **Control passed.** `one-shot WMT negotiation: result=0 phase=5
  clocks-held=1`.
- **Bluetooth passed.** `one-shot BT H1: result=0 completed=5/5
  vcn33-bt-held=0 tx-seq=6 rx-seq=6 peer-ack=5 local-ack=5`. VCN33-BT was
  switched off after the successful BT-off.

| Step | Result | TX | RX | Services | Frames |
| --- | --- | --- | --- | --- | --- |
| BT-on (WMT) | 0 | 16 | 15 | 4 | 2 |
| HCI Reset (task 0) | 0 | 14 | 17 | 5 | 2 |
| Read Local Version (task 0) | 0 | 14 | 25 | 6 | 2 |
| Read BD_ADDR (task 0) | 0 | 14 | 23 | 5 | 2 |
| BT-off (WMT) | 0 | 16 | 15 | 4 | 2 |

Every count matches one command, one reply and two separate ACKs, the upper
bound in the protocol's table. The laptop's corrected classifier checked the
replies and counters and accepted the run.
- **Wrap-up.** The A53 regression passed. The reviewed native recovery
  returned to Gemian on a changed boot, independently confirmed as `3.18.41+`
  on Debian 9.13.

## Conclusions

H1 and H2 hold for this unit and power lifetime. Without a ROM patch or RF
calibration, after full-mode negotiation, the ROM:

- answers WMT Bluetooth function-on and function-off;
- answers HCI Reset, Read Local Version and Read BD_ADDR on STP task 0, with
  successful Command Complete events.

The version and address values are private. The reviews in
[RUNTIME_1](RUNTIME_1.md) and [RUNTIME_2](RUNTIME_2.md) explain the 2 s wait
and the task-0 TX fix that this pass depends on.

## Limitations

- No `hci_dev` is registered; the commands come from a fixed in-kernel
  sequence, not from BlueZ.
- No scan, inquiry, pairing, connection, ACL or SCO traffic was tested.
- No power saving, wake pulse, retransmission or reset recovery exists.
- One boot on one unit; not repeated.
- The sequence is an experiment-only one-shot diagnostic, not upstream code.

## Next

A small `hci_dev` over task 0, reusing `btmtk_set_bdaddr` and the H:4 receive
helper, per the [Bluetooth record](../2026-10-04-gemini-bluetooth-re/README.md).
It needs long-lived IRQ ownership and a receive queue on the shared STP link.
