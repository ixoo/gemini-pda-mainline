# Phase A runtime 2: calibration answered with data the matcher refused

Status: consumed, 2026-10-07. The laptop device custodian ran one boot of
candidate 2 under [PROTOCOL.md](PROTOCOL.md). The raw log contains RF
calibration data and stays private; no calibration byte is reproduced here.
Recovery ran through the reviewed no-scan failure path. The custodian confirmed
changed-boot Gemian (boot ID `1155ba09-cca5-4823-8e30-c23beffb347d`) and a
passing A53 regression.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `7cfd2852e3e4fe60e2aef74da3e2fce74f325712d0ba0e859a42b1c713ca423e` |
| Candidate receipt SHA-256 | `72fe89659e3ad0bd9bd9f7a2fa516a85051634ab8820eba5b6ed758500c1af28` |
| Mainline boot ID | `5956f283-3513-47e1-9d6d-3b56f4fa620f` |
| Complete sealed log (custodian) | 137876 bytes, SHA-256 `04ea47b6519ba1ecd005f054850fc74371d4b33dbfe09308ee4ef8b5f777d794` |
| Pre-seal capture analysed here | 133927 bytes, SHA-256 `cca623283a2a5edf82a27078f9ea7575387f55a7ebade38042c2e6691586c3c9` |

The analysis used the earlier pre-seal capture, a prefix-length copy taken
before the session sealed the log. Every line cited here is in it; the sealed
log is the authoritative record.

## Observations

- WMT preparation and negotiation passed, and both ROM patches were accepted:
  the digest fix from [runtime 1](RUNTIME_1.md) worked.
- Steps 0–280 completed: DLM and clock writes, both ROM patch downloads with
  their resets, LTE coexistence and both PA rails on.
- Step 281, RF calibration, failed with `-EPROTO`: `tx=11 rx=392 services=51
  frames=2`, both rails on, link counters `1/0/0/7`. No continuation, WLAN
  readiness line or scan followed.

## Cause

The 392 received bytes are two well-formed STP frames:

| Frame | Bytes | Content |
| --- | --- | --- |
| ACK | 4 | peer acknowledgement of the command |
| Task 4 data | 388 | 4-byte header with a valid checksum, 382-byte WMT payload, 2-byte CRC |

The WMT payload is an event with opcode `0x14` and a length field of 378 that
matches its body. The body is calibration data. The step table expected the
six-byte form `02 14 02 00 00 01`, and the shared event matcher requires an
exact length, so it refused the frame before acknowledging it.

The pinned vendor driver explains the difference. Its init-script loop reads
only the six expected bytes of this event. It skips the comparison for opcode
`0x14`, commented "workaround RF calibration data EVT, do not care this EVT",
and its transmit path flushes the WMT receive queue before the next command.
So the vendor driver also discards the calibration data.

Inference: calibration ran and returned data. This boot does not show what the
firmware does with that data or whether calibration is correct.

## Fix

Patch [0121](../../patches/proposals/0121-soc-mediatek-accept-the-MT6797-RF-calibration-data-event.patch)
adds one mode to the shared matcher: with an expected length of zero, it admits
a WMT event of any size up to the frame limit whose own length field equals the
received length. Only the calibration step uses it, with the two-byte prefix
`02 14`; every other step keeps its exact match. The whole frame is consumed
and acknowledged, which matches the vendor's read-then-flush outcome.

- [test-calibration-event.c](test-calibration-event.c) feeds synthetic framed
  events through the real receive path. It accepts the runtime-2 shape, the
  vendor's two-byte form and the largest frame. It refuses a length field off
  by one in either direction and a wrong opcode, and shows that the old exact
  contract refuses the runtime-2 shape.
- [test-common-init.c](test-common-init.c) now expects the calibration step's
  two-byte prefix and variable length.
- The task-routing, BT H1 and Bluetooth HCI fixtures still pass on the changed
  headers. The older link-state fixture does not build with or without this
  change, because it predates a header it now needs.

Steps 282–284 have not yet run on hardware: PA rails off and the antenna-mode
command.

## Build

Input `097c113c` builds on buildbox-2 for Phase A and on buildbox-3 for
Bluetooth HCI. Both pass remote validation, fetch and local checksums with no
new warning, and both carry 0120 and 0121.

| Profile | Package inventory |
| --- | --- |
| Phase A | `3013daa602ace85689f1d3e0fb495124cbb984a2284cdfac37eb7a36385afe97` |
| Bluetooth HCI | `8e805a79f23fe197a917629fe2ae28e80f72e31c955f02086b741689564cc1cb` |

The Phase A DTB is unchanged (`07b097d5…`). The builder now pins this package.
This run's receipt is kept as
[results/runtime-2-candidate.json](results/runtime-2-candidate.json), and both
receipt slots are reset for candidate 3. The installer's predecessor is the
runtime-2 candidate `7cfd2852…`.

The classifier's calibration fields were also corrected. The driver dumps the
first raw bytes received for calibration, which are STP framing rather than
the WMT event, and a dump can span several lines. The old classifier read
exactly one line and compared it with the vendor status bytes, so it reported
zero bytes for a split dump and could never have matched. It now joins
contiguous dump lines and reports the capture size, ACK frames, data task and
event size from the frame header. It keeps no event byte and adds no scan gate.
