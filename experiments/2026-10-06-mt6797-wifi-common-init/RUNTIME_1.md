# Phase A runtime 1: common init refused its own ROM patch

Status: consumed, 2026-10-07. The laptop device custodian ran one boot under
[PROTOCOL.md](PROTOCOL.md) with these adapters at `7a255dc0`. Figures are from
its report; the sealed log stays private. Recovery runs through the reviewed
no-scan failure path; its confirmation is the custodian's to report.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `c04915b2a8cb7f203b2e746c10f2b0c82da00c7558ec0bd79ac5acd7ea350ac6` |
| Candidate receipt SHA-256 | `169cd7a723fee8f2d969c9dfc43ff2fdb2ce2605a19d0202ee288982c786d521` |
| Mainline boot ID | `135d4939-1076-4120-a794-b17c94abce26` |
| Sealed log | 135149 bytes, SHA-256 `5800bb7d9e26884f8d19cf2eeb143729e860bf5c2c45b5580fd6da2cc4b63185` |

## Observations

- WMT memory preparation and negotiation passed.
- `one-shot WMT common init: result=-22 completed=0/285 bt-rail=0 wifi-rail=0
  link=1/1/0/0`. The link counters are unchanged from negotiation, so no WMT
  command was sent. There was no calibration reply, no continuation line, no
  WLAN readiness line and no scan; the classifier withheld the scan and the
  host ran the no-scan failure session.

## Cause

The driver pins each ROM patch's SHA-256 as a C byte array. The array for
`ROMv3_patch_1_0_hdr.bin` had its last eight bytes mistyped
(`…448cf63080b43cf6` instead of `…448b54365d8cf630`). The retained file
therefore failed the digest check, and common init returned `-EINVAL` before
step 0, exactly as designed for a mismatched patch.

Verified offline against the retained files: both digests otherwise match,
both patches parse with the expected metadata (`0x21`/`00 0a f0` and
`0x22`/`00 09 00`), and all 285 steps build. Nothing reached the chip, so this
result says nothing about the ROM's response to common init.

## Fix, not yet built

- Patch [0120](../../patches/proposals/0120-soc-mediatek-correct-the-MT6797-ROM-patch-1_0-digest.patch)
  corrects the array. It is selected in the common-init, Phase A and Bluetooth
  HCI profiles; the Phase A series applies, and its common-init source now
  passes the digest test.
- [test-rom-digests.py](test-rom-digests.py) compares the driver's arrays with
  the builder's pinned digests. It fails on the built Phase A source and passes
  on the fixed one, so the same typo cannot reach a candidate again.

A new Phase A candidate needs a rebuild with 0120, a new receipt and the owner's
approval; this candidate is not repeated.
