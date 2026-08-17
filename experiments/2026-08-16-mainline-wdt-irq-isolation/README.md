# Experiment: MT6797 watchdog IRQ isolation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-wdt-irq-isolation` |
| Status | exact one-property candidate independently validated; deployment pending |
| Subsystem | MT6797 TOPRGU watchdog, early platform probe, USB observation |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline serviceability prerequisite to CPU8 work |

## Question or hypothesis

Does the current DT's watchdog `interrupts` property prevent the built-in
MT6797 watchdog driver from taking over the bootloader-armed timer before the
automatic fallback? Keep the exact stopped kernel, initramfs, Android-v0
container, three USB properties, disabled SCP node, watchdog reset-provider
property, and every other DT property unchanged. Delete only
`/watchdog@10007000/interrupts` so the probe follows the exact no-IRQ branch
proven by the serviceable Stage-27 DT.

This is a discriminator, not a conclusion that the IRQ is already proven
wrong. The IRQ-present path performs IRQ mapping and `devm_request_irq()` before
`mtk_wdt_init()` can detect, extend, and ping a running watchdog. The no-IRQ
path skips those possible early failures. If either path reaches
`mtk_wdt_init()`, the driver handles a bootloader-running timer; the property
deletion is selected because it removes the only earlier branch unique to the
stopped DT.

## Provenance and environment

- Exact stopped predecessor is the SCP handoff-node candidate, full boot2
  SHA-256
  `73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7`.
- Exact current kernel package remains repository commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, release
  `7.1.3-gemini-entryled-a`.
- Exact predecessor DT SHA-256 is
  `53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b`.
- Runtime-proven Stage-27 DT SHA-256 is
  `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806`.
- The packaged configuration has `CONFIG_MEDIATEK_WATCHDOG=y` and
  `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`.
- No kernel compilation is needed. No native VM build is permitted or run.

## Safety assessment

The candidate deletes one interrupt description. It adds no register-data
write, watchdog operation, reset request, regulator action, CPU admission, or
storage access. The existing watchdog driver remains enabled and its exact
MMIO/compatible/reset-provider inputs remain present. USB stays
peripheral-only, xHCI stays disabled, SCP stays input-disabled, and CPU8/9
remain offline.

Any installation remains limited to standing-policy logical `boot2` gates:
resolve the live GPT, require the sole inactive and unmounted 16 MiB target,
record but do not back up its predecessor, require stable power, write and
flush only the exact payload, verify a full readback, and shut down cleanly.

## Associated code

- `scripts/build-wdt-noirq-dtb.sh`: source-pinned predecessor derivation plus
  deletion of one exact property with fixed output identity.
- `scripts/build-candidate.sh`: source-pinned deterministic Android-v0
  container assembly around the unchanged kernel and initramfs.
- `scripts/test-candidate.py`: independent layered container, manifest, SCP,
  watchdog, and negative-mutation validation.
- `scripts/install-boot2.sh`: source-pinned guarded logical-`boot2` installer
  with full readback and clean shutdown.
- `scripts/collect-runtime.sh`: source-pinned pre-armed USB/netcat observer
  bound to the exact pre-attempt Gemian boot ID and candidate checksum.
- `results/watchdog-irq-boundary-20260816.txt`: exact built driver branch,
  positive Stage-27 runtime control, timing, and candidate selection.
- `results/offline-candidate-validation-20260816.txt`: immutable candidate
  identities and completed offline gates.
- `results/predeployment-hypothesis-20260816.txt`: unique observation and
  decision map for the single authorized attempt.

Generated candidates remain below the ignored `artifacts/` tree.

## Procedure

1. Re-rank every remaining Stage-27/current difference by the earliest built
   kernel consumer.
2. Compare the exact watchdog probe paths for DTs with and without an IRQ.
3. Bind the no-IRQ path to the positive Stage-27 dmesg and the IRQ-present path
   to the stopped current DT.
4. Derive the predecessor DT twice, deleting only the interrupt property.
5. Assemble twice, pad twice, run all existing LK/container gates, and reject
   independent mutations before any deployment.
6. If every offline gate passes, publish exact identities and perform one
   guarded, pre-armed attempt.

## Observations

The working Stage-27 watchdog node has the same compatible and register range
but no `interrupts`; its exact runtime dmesg shows `mtk_wdt_driver_init()` at
0.965066 seconds, a successful probe at 0.967423 seconds, and a 31-second
watchdog. The stopped current DT adds `interrupts = <0 0x89 2>`.

In the exact selected source, `platform_get_irq_optional()` and
`devm_request_irq()` run before `mtk_wdt_init()`. A positive IRQ installs a
pretimeout and changes the running-watchdog mode; request failure returns before
the driver can extend or ping the timer. With no IRQ, probe proceeds directly
to watchdog initialization. `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y` then makes
the core maintain an already-running timer after registration.

The failed SCP-node attempt showed preloader detach and Gemian enumeration
11.536 seconds apart, with no intervening USB identity. That timing supports a
watchdog discriminator but does not by itself identify the reset source.

An offline prototype deleting only the interrupt property produces a
27,079-byte DTB with SHA-256
`49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa`.
Two deterministic derivations reproduced that DTB and the exact raw and padded
containers. Independent validation passed the inherited 32 LK/container gates,
the arm64 entry-ledger checks, the disabled-SCP contract, the candidate
manifest, and the watchdog contract. Restoring the IRQ or changing
`#reset-cells` was rejected by separate semantic mutation tests.

## Analysis

The DVFSP handoff node is enabled in both DTs and uses the same built driver;
current-only nvmem properties are not read by that driver. Keyboard/I2C5
differences are later serviceability inputs. The watchdog IRQ is the remaining
property that introduces a distinct, potentially failing branch before the
positive control's proven watchdog takeover.

## Conclusion

Selected and validated offline: remove only the watchdog interrupt description
to reproduce the positive control's early watchdog probe path without
restoring unrelated Stage-27 serviceability properties. Exact padded candidate
SHA-256 is
`b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d`.
Hardware behavior remains untested. CPU8 and CPU9 remain closed.

## Follow-up

Publish the exact identity, install it once through the guarded logical
`boot2` workflow, arm the host observer before physical selection, and classify
only changed boot-ID/USB/runtime evidence. The ordered project action remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
