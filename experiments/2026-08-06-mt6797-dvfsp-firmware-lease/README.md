# Experiment: MT6797 I2C6 firmware-owner lease contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-mt6797-dvfsp-firmware-lease` |
| Status | `source/static complete; Buildbox pending` |
| Subsystem | MT6797 DVFSP/CSPM, I2C6 firmware ownership |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `PARTIAL_FIRMWARE_LEASE_CALLBACK_CONTRACT` |

## Question

Can the missing vendor `SEMA_I2C_DRV` boundary be represented as a strict
private callback protocol without pretending that the Linux generation/cookie
lease is firmware ownership or adding an unreviewed MMIO path?

## Result so far

Patch `0175` defines a default-unregistered, platform-private callback pair.
The request carries ABI/user identity, pause-source `0x2`, `SW_PAUSE` bit 13,
`FW_DONE` bit 15, the vendor 2 ms bound, and the exact Linux transfer
generation/cookie. A successful acquire must echo the identity, return a
nonzero opaque owner handle, report all three pause words and all three
`FW_DONE` words, and only then create the firmware lease. Release requires the
same handle and clears the pause-source and all pause words. Registration
requires both callbacks and cannot be removed while a lease is held.

An absent owner returns a structured `-EOPNOTSUPP`. A malformed refusal,
timeout, state change, stale token, or invalid acquire/release response faults
the handoff; the code never guesses an inverse. No callback is registered by
the patch, and the current provider remains read-only.

This is a protocol boundary, not proof that the stopped one-way receiver is
authoritative for the vendor firmware. The external owner and any firmware
implementation remain unproven.

## Safety and nonclaims

- The patch adds no `readl()`, `writel()`, I2C transfer, regulator operation,
  CPUHP operation, PSCI call, or CPU_ON path.
- There is no Device Tree consumer and no callback registration in the current
  source series.
- The result does not authorize a DA921x page/register-data write, a provider
  vote, a boot candidate, CPU8/CPU9 admission, or device validation.
- The retained Gemian archive and managed reverse-engineering payload remain
  userspace/PCM evidence only; LK/TEE/SCP owner payloads are not present.

## Evidence

- [Protocol design](DESIGN.md)
- [Static oracle](scripts/oracle.py)
- [Source validation](results/source-validation-20260806.txt)
- [Patch 0175](../../patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-06-mt6797-dvfsp-firmware-lease/scripts/oracle.py
```

## Follow-up

The exact pushed commit must pass the named Buildbox profile before the
contract is accepted as compile evidence. The next hardware-independent gate
is an attributable external owner implementing this protocol, or a reviewed
one-way receiver proof that supplies the same responses. Until then the
DA921x provider remains fail-closed and the Candidate AO boot must not be
repeated.
