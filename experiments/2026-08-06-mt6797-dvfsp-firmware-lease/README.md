# Experiment: MT6797 I2C6 firmware-owner lease contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-mt6797-dvfsp-firmware-lease` |
| Status | `public hybrid owner source identified; mainline owner and image admission unproven` |
| Subsystem | MT6797 DVFSP/CSPM, I2C6 firmware ownership |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `PARTIAL_HYBRID_OWNER_SOURCE_IDENTIFIED` |

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

The exact retained vendor-kernel ELF and the Candidate AN observer now have a
stronger reconciliation: both use the same CSPM window
(`0x11015000..0x11015fff`) and the same `SW_RSV0..6` offsets, including the
three SW_PAUSE bit-13 words and three FW_DONE bit-15 words. This proves
register-window identity, not receiver authority. Candidate AN disabled I2C6,
did not exercise the pause handshake, observed no FW_DONE response, and left
I2C_APPM ungated, so the external owner gate remains open.

A read-only revalidation of the public Gemian kernel source now identifies the
historical hybrid owner directly. Its `cspm_probe()` maps CSPM and CSRAM under
one owner, obtains the `INFRA_I2C_APPM` clock, and initializes the SW/HW status
windows. Its `cspm_go_to_dvfs()` performs the reset, instruction-memory fetch,
register/event/wakeup setup, CSRAM record initialization, and PCM kick. The
same owner routes `SEMA_I2C_DRV` through the three-word SW_PAUSE/FW_DONE
handshake and paired clock release. The source embeds both governor and
non-governor PCM descriptors; the non-governor `pcm_dvfs_v0.1_160131_02`
descriptor matches the retained vendor ELF and public array identity. The
repository and header are GPLv2, but source attribution, notice propagation,
and mainline image packaging still require an explicit admission step. The complete source identity and line anchors
are recorded in
[`results/public-hybrid-owner-source-20260806.txt`](results/public-hybrid-owner-source-20260806.txt).
This closes historical owner attribution, not the current mainline owner gate:
the handoff still maps only CSPM, has no PCM image residency/start path, and
registers no callback. Vendor `BUG()` and unbounded wait behavior also cannot
be copied directly into a mainline failure/PM path.

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
- [PCM residency/start contract](PCM_START_CONTRACT.md)
- [Static oracle](scripts/oracle.py)
- [Source validation](results/source-validation-20260806.txt)
- [Buildbox validation](results/buildbox-validation-20260806.txt)
- [Initial Buildbox input failure and repair](results/buildbox-failure-20260806.txt)
- [Exact retained vendor-kernel SEMA contract](results/vendor-kernel-sema-contract-20260806.txt)
- [Public hybrid owner source](results/public-hybrid-owner-source-20260806.txt)
- [Buildbox validation after owner-source review](results/public-owner-buildbox-validation-20260806.txt)
- [Current-head full-profile Buildbox resume](results/current-head-full-buildbox-20260806.txt)
- [Receiver register-window identity reconciliation](results/receiver-register-identity-20260806.txt)
- [Retained TEE secure-owner disassembly](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt)
- [Retained SCP local-alias inventory](../2026-08-06-da921x-page-owner-audit/results/scp-alias-inventory-20260806.txt)
- [Patch 0175](../../patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch)
- [PCM start contract result](results/pcm-start-contract-20260806.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-06-mt6797-dvfsp-firmware-lease/scripts/oracle.py
```

## Follow-up

The exact pushed commit `23c793aefaccef36253b37654397199c24a228d1` now passes
the named Buildbox profile and package checksum validation, and the single
validated package has been fetched locally; this is compile-only evidence. The next
hardware-independent gate is an attributable external owner implementing this
protocol, or a reviewed one-way receiver proof that supplies the same
responses. The exact retained vendor-kernel ELF now supplies positive Linux-
side evidence for the contract: user 1 is routed to
`cspm_pause_pcm_running(PAUSE_I2CDRV)`, with three SW_PAUSE bit-13 writes,
three FW_DONE bit-15 polls, the 2 ms bound, and paired release around the
I2C transaction. This confirms the historical caller contract but not the
external firmware receiver owner. The public hybrid source now supplies a
positive historical owner path, but the exact PCM variant, image redistribution
boundary, and a robust mainline adapter remain open; see the
[public hybrid owner source](results/public-hybrid-owner-source-20260806.txt).
The bounded SCP disassembly narrowed likely local aliases to DMA
remap, interrupt, clock, and generic SPM/DVFS paths; it did not identify the
`SEMA_I2C_DRV` owner or a pause/release implementation. See the
[vendor-kernel contract](results/vendor-kernel-sema-contract-20260806.txt) and the
[SCP disassembly result](../2026-08-06-da921x-page-owner-audit/results/scp-owner-disassembly-20260806.txt).
The retained TEE disassembly separately identifies only keyed CSPM control and
secure-semaphore `+0x448` ownership, with no direct PCM restart or
`SW_RSV`/`FW_DONE` lease path; see the
[TEE owner result](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt).
The SCP literal-pool inventory similarly classifies the remaining local
`0x400a…`, `0xa000…`, and NVIC paths without identifying a pause/release owner;
the computed/secure-alias residual remains explicit in the
[SCP alias result](../2026-08-06-da921x-page-owner-audit/results/scp-alias-inventory-20260806.txt).
The observer and vendor ELF also match the receiver register window and exact
pause/status offsets, but no pause/FW_DONE handshake was exercised; see the
[register identity reconciliation](results/receiver-register-identity-20260806.txt).
Until then the DA921x provider remains fail-closed and the Candidate AO/AN
stopped-state or clock-normalization boot must not be repeated.

The PCM start contract is now explicit in
[`PCM_START_CONTRACT.md`](PCM_START_CONTRACT.md). It makes image identity,
CSPM/CSRAM residency, reset/IM/PCM kick order, CSRAM initialization, runtime
lease responses, and fault/resume invalidation prerequisites for registering
the callback. The current mainline handoff satisfies none of the start and
residency requirements, so this result advances the design boundary only and
does not authorize a loader, firmware copy, provider write, build, or device
boot.

The owner-source review itself was validated on Buildbox at pushed commit
`5aced75e948be894fda47ef59a9b41434f02589b` with the dedicated
`a72-p32-rollback` profile; all 180 patches and 119 DTBs passed package
checksums. This is still compile-only evidence: no PCM image was loaded, no
callback was registered, and no device action occurred. See the
[Buildbox result](results/public-owner-buildbox-validation-20260806.txt).
