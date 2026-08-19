# Experiment: mainline I2C6 firmware-writer transaction window

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-18-mainline-i2c6-firmware-writer-transaction-window` |
| Status | `source-designed-awaiting-build` |
| Subsystem | MT6797 SCP, stopped DVFSP, and I2C6 ownership |
| Device variant | Planet Gemini PDA, MT6797 named development unit |
| Date(s) | 2026-08-18 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 blocker B1 |

## Question or hypothesis

Does SCP reset control remain asserted not only before the stopped-DVFSP
handoff, but at both edges of every exact read-only I2C6 transaction admitted
by that handoff in the same boot?

## Provenance and correction

- Runtime-proven functional parent: `da921x-lk-clock-readonly-provider`.
- Failed-closed observation parent:
  `da921x-i2c6-firmware-writer-attestation`.
- New profile: `da921x-i2c6-firmware-writer-transaction-window`.
- Planned release: `7.1.3-gemini-i2c6-fwtxn`.
- Canonical source delta: patch `0287` after frozen patch `0286`.
- The source-backed correction and original failed result are preserved in the
  [parent contract correction](../2026-08-18-mainline-i2c6-firmware-writer-attestation/results/runtime-attempt-1-contract-correction-20260819.txt).
- Builds are permitted only through Buildbox from an exact clean pushed
  commit. No native VM build is permitted.

## Safety assessment

The successor performs read-only SCP checks before and after each existing
I2C6 lease. It preserves the proven read-only provider, enables the bounded
entry ledger, and makes no firmware, Device-APC, I2C, regulator, or CPU write.
A nonzero SCP reset value before a transaction prevents it; a nonzero value at
exit faults all later transfers. The mainline SCP driver and DT node remain
disabled, CPUs 8--9 remain excluded, and the original profile retains its
frozen predicate unless the new option is explicitly selected.

## Unique evidence and decision branches

The exact candidate must record in one boot:

1. two pre-handoff reset-control samples equal to zero;
2. the inherited stopped-DVFSP handoff reaching ready;
3. exactly 20 complete, attributable read-only provider transactions;
4. exactly 20 reset checks at transaction entry and 20 at exit, all zero;
5. zero ledger overflow, write-shaped, foreign-address, or failed entries;
6. zero DA921x register-data writes with CPUs 8--9 offline; and
7. one native return to changed-identity Gemian only after capture.

A complete pass closes B1 only when combined with the exact retained
LK/ATF/TEE/SCP audits, the disabled mainline SCP path, and the same-boot
stopped-DVFSP validation. Any reset mismatch, missing edge check, ledger
mismatch, handoff failure, unexpected transfer, or serviceability loss keeps
B1 open. It does not authorize B2, a DA921x write, or CPU8/CPU9.

## Associated code

- [`contract.json`](contract.json) freezes the exact observation and decision
  boundary.
- Canonical patch:
  `patches/v7.1.3/0287-soc-mediatek-guard-I2C6-transfer-window-with-SCP-reset.patch`.
- Isolated fragment:
  `configs/gemini-i2c6-firmware-writer-transaction-window.fragment`.
- [`scripts/validate.py`](scripts/validate.py) validates the source/profile
  boundary and unsafe mutations before Buildbox submission.

## Procedure

1. Validate patch `0287`, its isolated config, manifest profile, contract, and
   canonical series position.
2. Commit and push the clean source boundary, then build only the new profile
   on Buildbox and fetch only its validated package.
3. Construct and independently validate one checksum-pinned Android-v0
   candidate using the unchanged attestation DT windows.
4. Install only to live-GPT logical `boot2`, require a full-partition readback,
   and shut the device down cleanly.
5. Pre-arm the checksum-pinned USB/netcat observer, boot `boot2` once, capture
   the full contract, and return natively only after a structurally valid
   observation.

## Current conclusion

Source design only. B1 remains open. B2, every Gate-6 write, and CPU8/CPU9
admission remain closed.
