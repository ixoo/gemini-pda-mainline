# Keyboard capture admission and combined budget

Status: preparing; the tracked capture binding is disabled with no admission.
The [corrected disconnect test](../../2026-09-08-keyboard-console-ownership/DISCONNECT_RETEST.md#attended-result)
and [current full-duration proof](results/duration-daaa4529/RESULT.md) passed.
This document prepares the existing 20-case capture, not another standalone
marker boot. It does not request physical selection.

## Exact execution boundary

The existing capture tool now checks
[capture-execution-binding.json](capture-execution-binding.json) before any
execution claim or transport. It requires the complete admission to match,
including boot, dependency, source, expected classifier contract, package,
monitor, runtime metadata, custody, duration and same-boot disconnect receipt.
The claim retains the binding digest. Disabled state refuses before the CLI
reads admission/package paths. Dry-run and offline assessment do not enable it.
The full existing prerequisite verifier still runs before every execution.

For a future session, finish preparation using the unchanged candidate and
corrected enabled package from the linked disconnect result. Do not copy its
consumed admission or replace its boot identity. The capture's fresh admission
ID must also identify its fresh disconnect proof and private evidence directory;
otherwise the prerequisite checker refuses. Publish the exact complete binding
only after the actual runtime and owner facts pass. Disable it after the
consumed session, including failure. The file currently grants no execution.

## Combined budget

Retain the existing logger lifetime of 600 seconds and its 2 MiB limit.
Complete offline source/package/command preparation before the owner's boot.
After boot, verify identity and the readable screen, run one same-boot harmless
disconnect proof and export, obtain the input metadata and custody receipts,
then perform one delivery, capture and export. No extra key sequence or retry
is included. The owner follows the existing displayed 20-case protocol.

The existing initial guards require boot age strictly below 240 seconds before
both delivery and capture. From the latest permitted capture start, the maximum
host transport budgets are:

| Phase | Bound | Latest cumulative boot age |
| --- | ---: | ---: |
| Capture, including postflight | 240 seconds | below 480 seconds |
| Separate evidence export | 30 seconds | below 510 seconds |
| Logger seal and export | 30 seconds | below 540 seconds |
| Guarded recovery request | 15 seconds | below 555 seconds |
| Changed-ID Gemian confirmation | 15 seconds | below 570 seconds |

These are bounded execution intervals, not permission to spend the remaining
time on unbounded preparation or owner pauses. The native monitor's own capture
cleanup bound remains 215 seconds; the normal input sequence is 202 seconds.
The 240-second host cap does not prove remote termination after transport loss.
Any incomplete preservation retains unique RAM evidence and gates recovery.
The 600-second logger may also stop earlier at its byte cap; its actual receipt
must establish complete coverage. No thermal samples, CPU/rail changes, storage
operations or concurrent device tests are added.

## Remaining preparation

The classifier contract is still unfilled. Complete the bounded input-metadata
collection and validation path for actual event identity, capabilities, resource
ancestry, map, logger age and reader exclusion. Review the exact generated
capture/delivery/export commands under the candidate's BusyBox. Then freeze the
candidate classifier fields and the complete attended sequence. Fresh runtime
facts and owner confirmation can only be filled after the later physical boot.
Until those steps are complete, keep both capture admission and queue readiness
disabled/preparing. The device remains in known-good Gemian.

Validation for this gate change: seven capture fixtures, six prerequisite
fixtures and eight disconnect fixtures passed, including rejection of changed
session fields before claims/transport. Repository checks passed. No kernel,
userspace build, live input observation or capture was run for this change.
