# C3-2 runtime: Bluetooth function-on answered; HCI Reset never sent

Status: consumed, 2026-10-06, under [PROTOCOL_2.md](PROTOCOL_2.md). The laptop
device custodian ran one attended boot with no retry. Figures are from its
report; the sealed log and raw bytes stay private on the owner's machine.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `7b578dbf3c4aa0128fe66c0a9b22d27cae253761463e8742bd0edb269dc93083` |
| Candidate receipt SHA-256 | `6609379e44c01686fc91fca1b3321f499aec3c5804ae0d43cd1d8bffd6a8f56b` |
| Package | commit `025b2667`, inventory `adda8f2de1ec2a3ad157676eb2103673e8e79d5f711d862a30aef829c62ca111` |
| Mainline boot ID | `1ef35a98-0335-4a61-a3b4-9723ed3bbc2e` |
| Sealed log SHA-256 | `07de04652433a5797593d24288cedac1bf69c5d8b15521f578df8cd0bf9a1ab0` |
| Gemian boot ID after recovery | `6f79c14b-c85a-40b6-96f2-067d48fe07a6` |

## Kernel observations

- **Control passed.** At 59.853187 s: `one-shot WMT negotiation: result=0
  phase=5 clocks-held=1`.
- **BT-on succeeded.** `bt-on: result=0 tx=16 rx=15 services=4 frames=2`. The
  chip returned the WMT function-on event within the 2 s wait. Sixteen bytes
  sent are the 12-byte command frame plus the 4-byte host ACK; fifteen received
  are the 11-byte event frame plus the chip's 4-byte ACK.
- **HCI Reset was never sent.** At 60.679917 s: `one-shot BT H1: result=-22
  completed=1/5 vcn33-bt-held=1 tx-seq=2 rx-seq=2 peer-ack=1 local-ack=1`. The
  HCI Reset record shows `result=0 tx=0 rx=0 services=0 frames=0`: preparation
  returned `-EINVAL` before any exchange. This is neither an HCI success nor a
  device timeout. No later step ran.
- **Wrap-up.** The A53 regression passed, the log is complete, and the reviewed
  native recovery returned to Gemian on a changed boot running `3.18.41+`.

The laptop's C3 classifier rejected the BT-on counters and the extra ACK as
out of bounds. That is a classifier finding about its expected counts, not a
kernel observation, and is kept separate here.

## Interpretation

H1's first half holds: without a ROM patch or calibration, the ROM answers WMT
Bluetooth function-on within the vendor's wait. The 600 ms deadline in
[runtime 1](RUNTIME_1.md) was the reason that boot saw no event. Whether the
ROM answers HCI Reset on task 0 is still untested.

## Cause and fix

`wmt_full_tx_init()` validated every outgoing frame with the WMT-only decoder,
which refuses frames for any other task. Every task-0 command therefore failed
in `mt6797_stp_task_prepare()` with `-EINVAL`. The earlier
[host test](test-bt-h1.c) covered receive routing only, not TX preparation.

Patch [0114](../../patches/proposals/0114-soc-mediatek-accept-non-WMT-frames-at-full-STP-TX-init.patch)
validates with the shared full-STP decoder and keeps the WMT size limit. The
new [prepare test](test-bt-h1-prepare.c) compiles the real I/O header. It
prepares HCI Reset on task 0 from C3-2's post-BT-on link state, checks the
encoded task, sequence and ACK, and confirms WMT still prepares and GPS is
still refused. It fails on the old code and passes with 0114. The twelve
existing transport fixtures still pass.

```sh
# headers from a prepared source with 0114 applied, plus empty linux/*.h stubs
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
   -fsanitize=address,undefined -I"$d" test-bt-h1-prepare.c -o "$d/t"
setarch "$(uname -m)" -R "$d/t"
```

The next Bluetooth boot needs a candidate rebuilt with 0114 and a reviewed
protocol. This candidate is not repeated.

## Rebuilt package

Buildbox compilation on buildbox-3, remote package validation, fetch and all
local checksums pass for input `cd06b7f5`, with no new warning. Package
inventory: `c7d36be7532c66fc604a97e52524f4e2c3afda15a9d7e4f7d83f2911a079a8fc`.
The board DTB is unchanged (`07b097d5…`).
