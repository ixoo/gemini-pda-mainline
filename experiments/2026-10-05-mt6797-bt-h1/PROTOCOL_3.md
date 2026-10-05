# C3-3 protocol: HCI Reset with task-0 TX fixed

Status: draft for coordinator review, 2026-10-06. No candidate is composed and
no device action has been taken under this protocol.

C3-2 under [PROTOCOL_2.md](PROTOCOL_2.md) is consumed; see
[RUNTIME_2.md](RUNTIME_2.md). It showed that the ROM answers WMT Bluetooth
function-on within the vendor wait, and that every task-0 command failed in
preparation before reaching the wire. This is a new artifact and a new boot.

## Hypothesis and unique observation

With task-0 TX preparation fixed by patch 0114, the ROM answers HCI Reset,
Read Local Version and Read BD_ADDR on STP task 0 after function-on, without a
ROM patch or calibration (H1 second half, and H2). The unique observation is
the first task-0 reply on the wire.

## Artifact

| Item | Value |
| --- | --- |
| Profile | `mt6797-a53-wifi-common-init-compile` |
| Commit | `cd06b7f54e1987d89344d0bcacd6995cd4410e54` |
| Package inventory | `c7d36be7532c66fc604a97e52524f4e2c3afda15a9d7e4f7d83f2911a079a8fc` |
| Release | `7.1.3-gemini-a53-wmt-versions`, inherited |
| Built board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734` |
| Builder | buildbox-3; remote validation, fetch and local checksums passed |

The only kernel difference from C3-2 is patch 0114. Identify the boot by the
candidate's boot2 SHA-256 and this inventory, not by the release string.

## Everything else as PROTOCOL_2

Candidate composition, DT changes, the sequence, waits and budgets, failure
behaviour, evidence and recovery gates are exactly those of
[PROTOCOL_2.md](PROTOCOL_2.md), with this package. The composed DTB is
therefore expected to match C3-2's (`c8e1b98c…`), and the RAM root stays
byte-identical to the parent. One `wmt_negotiate` write, no retry.

Expected counters for a passing step, if the classifier checks them. TX is the
command frame (payload plus 6) plus an optional 4-byte host ACK. RX is the reply
frame (payload plus 6) plus the chip's 4-byte ACK unless it is piggybacked, so
frames is 1 or 2.

| Step | Payload out / in | TX | RX |
| --- | --- | --- | --- |
| BT-on, BT-off | 6 / 5 | 12 or 16 | 11 or 15 |
| HCI Reset | 4 / 7 | 10 or 14 | 13 or 17 |
| Read Local Version | 4 / 15 | 10 or 14 | 21 or 25 |
| Read BD_ADDR | 4 / 13 | 10 or 14 | 19 or 23 |

## Decision branches

- **Negotiation fails.** Regression of the control; stop, Bluetooth void.
- **BT-on fails.** C3-2 showed it working; treat as a regression and diagnose
  offline before any further boot.
- **All five steps pass.** H1 and H2 hold. Bluetooth can proceed ahead of
  common init with a real HCI driver over task 0.
- **HCI Reset times out at 2 s after a good BT-on.** H1's second half is not
  demonstrated. Inspect the raw frames and link counters offline; Bluetooth
  then follows common initialization.
- **HCI Reset returns an unexpected event.** Keep the bytes private and decode
  them offline before any further boot.
- **Any step fails in preparation (zero TX).** A host-side bug; fix offline.
- Unexpected heat, power or recovery behaviour: follow
  [SAFETY.md](../../docs/SAFETY.md).
