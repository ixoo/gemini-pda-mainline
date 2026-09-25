# MT6797 TOPRGU restart: upstream readiness

Review date: 2026-09-25. Status: **hold submission; no new device candidate**.
This assesses the restart topic separately from the infracfg reset series.
The historical [Candidate AB result](../2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt)
supports one prompt TOPRGU restart on the named PDA, with no broad repeatability
claim. The later [minimal candidate](README.md#runtime-result) changed priority
from 255 to 130 and removed MT6797-specific mode writes during watchdog start
and adoption. Its one boot passed startup but refused the restart request
because the live ramoops backend was not established. It supplied no hardware
comparison of 130 against 255 or of the narrower mode policy.

## Current upstream dependency

At mainline master `165768bb70265b5c38cf0b73fafd75be235f8b14`, the
[MediaTek watchdog driver](https://github.com/torvalds/linux/blob/165768bb70265b5c38cf0b73fafd75be235f8b14/drivers/watchdog/mtk_wdt.c)
still sets restart priority 128, has no explicit `mediatek,mt6797-wdt` match
data, and retains the existing software-reset callback. Its source SHA-256 is
`75980000791cad302a15451642a2ce5a2dbd7748b52f52942233d4705e1f3593`.
The official watchdog maintainer tree's `watchdog-next` head
`8b5a9f09037e3c372c4e9f2fbda85fcfbf5ea5f0` has the same priority and no
explicit MT6797 match in its inspected driver; that file's SHA-256 is
`41b864a2db9fa466d8454bc3f7127e8cd46240824f0dfcfa2627275a8c6b06f2`.
These are file checks, not a complete merge or mail-review search.

Local [patch 0087](../../patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch)
sets priority through `mt6797_data`, which [patch 0081](../../patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch)
introduced along with separate firmware auto-start behavior. Patch 0087 is
therefore not a standalone current-upstream topic. Conversely, the 255-priority
runtime result cannot certify a new 130-priority patch or removal of the
earlier start/adoption writes. With both handlers registered, current
priorities place PSCI's [priority-129 handler](https://github.com/torvalds/linux/blob/165768bb70265b5c38cf0b73fafd75be235f8b14/drivers/firmware/psci/psci.c)
before the watchdog's priority-128 callback.

## Decision

Keep both local experiments and their one-device limits intact. First resolve
the [ramoops backend refusal](RAMOOPS_DIAGNOSIS.md) or prepare a distinct,
equally attributable log path. Then select a new, reviewed candidate only if
its observation distinguishes priority/mode behavior that would change the
upstream implementation. The consumed minimal artifact is not a retry target.
Before a submission, derive a coherent current-base topic containing the
required MT6797 match and restart semantics, compile it through Buildbox, and
obtain actual human authorship and DCO certification. No local patch, profile,
candidate or device queue changes follow from this source review alone.
