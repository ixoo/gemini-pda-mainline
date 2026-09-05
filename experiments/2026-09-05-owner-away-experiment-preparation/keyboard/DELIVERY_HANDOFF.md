# Exact disabled-monitor delivery adapter

[delivery.py](delivery.py) verifies the accepted package manifest
`7eb7313217d0efe306b33a8bd7f90a4e782c7d0931ce71362b2de0ce8a33767f`
from revision `75636670d933b9231f36fddf2ce876801568f64e` through the existing
package verifier. It additionally pins the 66,672-byte monitor and all three
license notices. It reads the retained package in place, without duplicating it.

The generated fixed shell first checks the admitted boot, candidate member
hashes and existing RAM guards. It additionally requires the existing root to
be executable, writable rootfs/ramfs/tmpfs, no submount under its fixed delivery
path and no existing path or symlink. Only then does exclusive creation of
`/a53-keyboard-delivery` consume the delivery claim. It writes exactly four
base64-decoded files, checks each length and full checksum, and makes only the
new disabled binary executable. Each file fits the unchanged 128 KiB ceiling.
No candidate member is replaced; /run's noexec state and mounts are unchanged.
Partial delivery stays preserved after failure. There is no cleanup or retry.

This closes package selection and fixed byte delivery generation, not capture
admission. The binary's production main still refuses and is never invoked by
this script. `execute()` unconditionally refuses before any I/O. No callable
transport or device permission was added. Delivering an inert binary now would
provide no keyboard observation and is not proposed as a device action.

## Exact admission boundary for subsequent integration

An eventual delivery admission must pin this source, the generated command,
the accepted package and binary, candidate/deployment and prerequisite closure,
the actual new boot, exclusive custody, stable power and one delivery attempt.
A future enabled entry is a different binary and requires explicit source/build
review; this adapter deliberately refuses it until its pins are reviewed.
Do not treat a successful byte delivery as actual input metadata, reader
exclusion, tty1 ownership, naturally exited console worker or owner acceptance.
The retained observer and classifier remain unchanged. Their map verification,
current resource metadata and complete private capture/export contract must be
wired before production admission; the kmsg exporter cannot preserve keyboard
files by itself. This adapter has no fallback for any missing predicate.

## Bounded full-duration harmless fixture plan

Use the existing monitor fixture and one managed Buildbox test directory in a
separately assigned window. An isolated fixture-only compile switch must select
the production 210/214/215-second constants without changing production monitor
bytes. Its built-in child should mark the 202-second observation boundary and
then ignore TERM, allowing the existing monitor status to measure actual TERM,
KILL and reap times. Retain the monitor identity with the current WNOWAIT harness
until child/group cleanup finishes. Keep a 225-second outer observation bound;
expiry is a failure requiring verified cleanup, not proof of hard termination.
No observer exec, input/VT device, SSH session, keepalive or hardware is needed.

That fixture result can establish full-duration userspace timing only. Actual
Dropbear disconnect behavior and device input/restoration remain distinct
integration boundaries. Do not run another size build or source tree solely to
repeat the already accepted scaled fixture evidence.

## Validation performed

The actual accepted package passed complete inventory/checksum/revision checks.
The generated script for the retained candidate passed bash syntax and ShellCheck;
SC2016 was excluded solely for intentional single-quoted awk field expressions
in the reused guards. Changed monitor/license bytes refuse. Three permanent
refusal fixtures check disabled execution before I/O and malformed inputs before
source loading. No generated shell was executed, no RAM delivery occurred, and
no backend or device connection was made for this work.
