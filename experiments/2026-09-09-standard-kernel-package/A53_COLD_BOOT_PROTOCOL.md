# A53 ten-cold-boot release protocol

Status: **conditional protocol, not a selected device session**. The
[A53 RAM regression](A53_RAM_REGRESSION.md) must first pass on the PDA. Its
candidate completed one guarded installation and one owner-selected boot. The
CPU0–7, authenticated USB and sealed-log observations passed, and a separate
read-only probe confirmed changed-boot Gemian return. The consumed runner's
aggregate remains inconclusive at its return classifier, so the first-regression
pass required here has not been recorded. Decide whether the independent return
confirmation satisfies that prerequisite, and freeze the per-cycle keyboard
method before admitting this series; do not repeat the same boot to replace the
result. This protocol defines what a later ten-boot result must prove; it does
not admit ten physical selections, a persistent-root write or a new power action.

## Frozen input and question

Before the first counted cycle, name one runtime-proven serviceability image,
its full boot2 checksum, kernel/DT/config/initramfs hashes, exact host capture
and recovery tools, and the reviewed keyboard observation method. Keep those
inputs fixed for all ten cycles. A replacement image, changed observation
method or changed boot-critical configuration starts a new series. A matching
full-partition readback after the guarded installation establishes the image;
the image need not be rewritten between cycles.

The question is whether that exact image can start from a genuinely powered-off
PDA ten consecutive times, reach attributable A53 serviceability, preserve its
logs and return to independently bootable known-good Gemian each time. A warm
restart into the image is not a counted cold boot. A black screen alone is not
proof that Linux booted or that the device powered off; combine the owner's
power-state observation with the authenticated boot identities below.

## One counted cycle

1. Verify known-good Gemian's release and fresh boot ID over its established
   LAN SSH path. Check live power, identity and the selected recovery path. A
   reviewed clean Gemian shutdown ends this predecessor boot; the owner
   confirms the PDA is off and physically selects boot2. No command selects
   boot2 or starts the next cycle automatically.
2. Use the admitted direct USB host route and fixed host-key authentication to
   collect one mainline boot ID, exact kernel release and candidate identity,
   CPU0–7 online with CPU8/9 offline, console state and RAM logger health.
   Check the boot ID differs from every earlier counted mainline boot ID and
   from the preceding Gemian boot ID. A network connection without that
   identity is inconclusive.
3. Preserve the complete bounded log before recovery, with the existing
   [authenticated baseline's](../2026-09-05-owner-away-experiment-preparation/baseline/SESSION.md)
   separation, seal, checksum and readback rules. During a separately admitted
   keyboard phase, record one owner key challenge and its attributable Linux
   input event without letting the console interpret it as a command. The
   keyboard method and finite per-cycle budget must be reviewed on the frozen
   image before the series starts; the historical twenty-step result cannot
   substitute for this image's input evidence.
4. Request the reviewed normal return only after evidence preservation and
   live identity checks. Authenticate the changed-boot known-good Gemian
   release and boot ID independently. The request or a USB disconnect alone
   does not prove recovery. That Gemian boot becomes the next cycle's
   predecessor only after a separately checked clean shutdown.

Each cycle owns a distinct private evidence directory and records its physical
start report, preceding Gemian ID, mainline ID, candidate hashes, observation,
keyboard result, log-seal/export result, recovery request and confirmed return.
Publish only sanitized identities, checksums and classifications. Keep raw logs,
credentials and host keys private. Use the existing device-session template to
fix each command's timeout, output cap, action count and stop conditions before
admission; no open-ended watcher or hidden retry is part of this protocol.

## Classification and stop rule

A cycle passes only with an attributable cold start, exact frozen inputs,
CPU/console/authentication and keyboard evidence, complete log preservation and
confirmed changed-boot Gemian return. An explicit wrong CPU state, wrong image,
failed authenticated service or failed keyboard observation is a failure.
Missing identity, absent USB, partial log, uncertain power-off or unconfirmed
return is inconclusive. Neither counts toward ten passes. Preserve the available
evidence and stop the series at the first failed or inconclusive cycle; diagnose
it before any newly reviewed sequence. Never repeat a consumed physical cycle
merely to replace a missing result.

The release gate passes only after ten consecutive passing cycles of the same
frozen image, with ten distinct mainline boot IDs and ten confirmed known-good
returns. The final record must link every cycle and check the series-wide
identity, checksum and budget invariants. This establishes repeatable A53
serviceability under the admitted bounds. Persistent-root I/O, orderly PDA
power-off from mainline, thermal protection, suspend and daily-driver readiness
remain separate gates in the [roadmap](../../docs/ROADMAP.md#a53-development-system-release-gate).
