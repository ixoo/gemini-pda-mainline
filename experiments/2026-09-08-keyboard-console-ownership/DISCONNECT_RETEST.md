# Corrected disconnect test

Status: **passed; evidence preserved; changed-ID Gemian return confirmed**.
The sequence below is consumed and does not authorize a repeat.
The [correction](DISCONNECT_FIX.md) follows the
[failed attended result](DISCONNECT_RESULT.md), which remains unchanged.

## Frozen inputs and distinguishing observation

Use the unchanged candidate in [validation.json](validation.json), raw boot
`7dfc3b1f771a12b8e711f699cf8fcfd2678aedc15bc9d8bcc98554f9c6654cdb`,
with the existing verified console baseline and reviewed-supplemental dependency
in [session-result.json](session-result.json). Current dependency and source
closure checks passed. The installed image itself needs no rebuild.

The separately delivered monitor package is now:

- Revision: `18a5882d55f11450dd049c7a6bbc2c6d1731359f`.
- Inventory: `89a9765b72b55b47c9e7ed973ceb175cbfab5623749be12a2739ee9c8f4e7657`.
- Monitor: 66,672 bytes, `105c3544ce69b095271c11b12b939f11a7172dc8ca3bb009c96426dec1413470`.
- Harmless probe: 66,760 bytes, `dfbff43d49bbe0473ffd44fb97e568a01df611b358351f43c9656438acf4b19d`.

The hypothesis is that output-pipe polling detects the lost SSH client even
when the harmless child is quiet, and explicit kernel-thread classification
allows a complete process scan. Require the original cancellation, reaping,
timing and empty-reader conditions. Another deadline result fails; it is not
accepted merely because cleanup stays bounded.

## Deployment and finite sequence

The guarded installer uses the fresh fixed receipt
`a53-keyboard-disconnect-deployment-2`, leaving the first receipt untouched.
Its locally validated derivation is
`b118ccebdf87593d9b4e751ed4b963859d371aa5f90d8112d39e6dc9d06aad17`.
Only the receipt namespace changed. Eleven host installer tests, candidate
validation, generated Bash syntax and ShellCheck passed. At the attended
handoff, revalidate logical boot2 and full-partition identity, skip a match,
and shut down cleanly before the owner's physical selection.

Use the finite sequence and limits in the original
[protocol](NEXT_SESSION.md#admission-and-finite-sequence) with fresh admission
IDs and the updated package above. A single guarded identity connection must
exclude both the dependency's prior boots and this predecessor's mainline
`37696b51-071c-4bdb-a708-fd83b76a3423` and recovered Gemian
`21748845-bc80-4536-b67c-84f7bb16c74f`. Confirm the actual readable screen,
prepare the exact binding offline with current sources, and publish it before
one two-second deliberate disconnect and one 30-second export. No keyboard
capture, extra process scan or proof retry is included.

If strict export refuses before files arrive, preserve its local output and
admit one separate 30-second read-only export of the four fixed regular files,
using the identity, RAM, ownership, size and final same-boot checks exercised
in the predecessor. This preservation action grants no scan or cancellation
pass, changes no source files, and makes no remote-shell termination guarantee
from the host deadline. On incomplete preservation, retain RAM and stop before
recovery. Do not substitute the historical native-preserver bootstrap.

Disable the consumed binding, preserve/seal the logger once under its original
600-second lifetime / 2 MiB cap, and recover only after unique evidence is saved.
Use the reviewed single native request and authenticated changed-ID Gemian
confirmation. Pass advances later keyboard preparation; cancellation, scan or
transport failure requires diagnosis before another physical test.

## Attended handoff

On 2026-09-09, the owner reported readiness for boot selection. The primary
integration coordinator took exclusive device custody. The exact installer
derivation above passed local validation, then verified known-good Gemian boot
`21748845-bc80-4536-b67c-84f7bb16c74f`, stable power, and live-GPT boot2
`/dev/mmcblk0p30` (`179:30`), separate from root (`179:29`). Both full-partition
checks matched padded candidate
`7d9eb0e20f145594ba5b9e56bbb809998c813d2517ce2f43b17074828459ea2a`;
the installer skipped writing and confirmed clean shutdown by unreachability.
The strict deployment receipt parser passed. Private receipt SHA-256:
`e5224624699a0fa0978fc7726415bdad3d9dee44a7af53c059c6507f5e04e1f2`.
No new backup, automatic reboot, or mainline test occurred. The next action is
one owner boot2 selection with USB connected and an immediate screen report.

## Attended result

The owner selected boot2 and confirmed the readable baseline screen. One guarded
authenticated connection established fresh boot
`fe849250-5d28-4f67-88db-cc3e38413dcd`. The actual dependency, current source
closure and corrected package passed preparation. The boot-specific binding was
published at `19258bd5` before the single proof and is now disabled.

The semantic verifier accepted the complete proof: the monitor reported
`forward-close-or-stall`, TERM at 7 ms, KILL at 87 ms and reap at 89 ms, with
no identity loss or lateness. The independent export completed in 1.207 seconds
with exit 0 and empty stderr. The complete scan covered 95 processes and
28 descriptors, with no matching reader or surviving test process. All four
probe files and the seven required evidence members were preserved. No fallback
preservation, extra scan or retry was needed. Exact sanitized fields and receipt
hashes are in [disconnect-retest-result.json](disconnect-retest-result.json).

The logger was sealed once and exported completely: 121,113 bytes, 1,746 records,
sequence zero through explicit seal. Only afterward did the guarded native
recovery request run once. Its complete frame passed the existing parser;
authenticated Gemian `3.18.41+` returned as
`1128b013-25b3-4e9c-9a94-398df98c2471`, different from both prior boots.
Raw captures and process identifiers remain private.

This is one passing disconnect/reader-release observation, not keyboard key
coverage or a transferable same-boot prerequisite. Prepare the finite keyboard
session next; its fresh boot must establish its own runtime prerequisites.
The earlier failed result remains unchanged. No kernel rebuild or keyboard
capture occurred. Candidate/dependency/package checks, semantic proof validation,
log/recovery parsers and repository publication checks passed.
