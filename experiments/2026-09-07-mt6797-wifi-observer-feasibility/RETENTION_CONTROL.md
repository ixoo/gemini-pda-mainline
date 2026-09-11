# Known-good Gemian console-retention control

Status: incomplete; the owner approved the control and the marker was written
once. The return watch expired without a qualifying changed boot; the owner's
physical-reset observation is pending. Do not repeat the marker or restart.
No boot2 image is selected by this control. The [second export attempt](EXPORT_ATTEMPT_2.md)
returned to Gemian without a console record, leaving kernel entry and log
retention unresolved.

## Question and decision

Can a single ordinary kernel-log marker, confirmed in working Gemian before
an owner-controlled Esc restart, be recovered afterward through console-ramoops?
This tests the observation path independently of the unproven export kernel.

- An exact recovered marker establishes one successful use of this recovery
  path on known-good Gemian. It does not prove retention on the failed boot.
- An absent record or marker shows that this control did not preserve the
  confirmed message through that path. It does not locate where it was lost;
  inspect retention, filtering and recovery before depending on marker absence.
- A write/preflight failure stops before the physical step. A partial read,
  identity mismatch or missing Gemian return is inconclusive; preserve evidence
  and request no retry.

## Fixed operation

The prepared control uses preceding Gemian boot
`8876d666-547d-4538-9387-8c46819ca5cf` and control UUID
`cdc90407-c6d2-40f5-9c61-049594af8e73`. A changed boot invalidates preparation.
Its sole write is this ASCII line, including the final newline, to `/dev/kmsg`:

```text
<11>wifi-retention-v1 control=cdc90407-c6d2-40f5-9c61-049594af8e73 boot=8876d666-547d-4538-9387-8c46819ca5cf stage=before-esc
```

The write is exactly 126 bytes, requests LOG_USER/error, and uses the existing
[native console path](BOOTSTRAP_DIAGNOSTICS.md#existing-logging-path). It contains
no firmware, calibration, personal identifier or private exception text.
The private marker program has SHA-256
`6d70cb1769ee773fbace44aa2f6e2a13e3e57882128fb57a282de38c68fdd16b`.

Immediately before writing, require authenticated root on the exact Gemian
boot, MT6797X, Linux 3.18.41+ aarch64, running systemd, console level at least 4,
and the enabled writable `pstore-1` console. Require the marker absent from the
current log. Open the nonsymlink kernel-log node with `O_NOFOLLOW`, verify the
opened descriptor is character device `1:11`, and make one write attempt. A
short write is terminal. Confirm the exact marker appears once in current
`dmesg`, recheck the UUID and flush filesystem writes once. This confirms log
acceptance, not direct readback of the persistent ring.

## Owner action and one collection

After explicit approval for this marker write and restart, the owner saves open
work. Complete and preserve the marker receipt before requesting the physical
step. Arm the prepared return collector, then ask the owner to hold only Esc,
release at the first vibration/restart indication, and stop after at most twelve
seconds. No second hold, alternate buttons, power-off fallback or boot2 selection
is part of this control. A timeout never authorizes another restart.

Watch the known-good LAN endpoint for at most 180 seconds. Require a new,
nonzero, internally consistent boot UUID and exact Gemian OS/model/userspace
identity. With the same return UUID checked before and after, require pstore
mounted and read `console-ramoops` once if present, with a 65,536-byte maximum.
An absent record produces an explicit absence receipt without a payload read.
The collector fixes the second export attempt's AND-list existence-check
ambiguity by using separate checks and an explicit absent-record branch.
Its SHA-256 is
`343fdd2e88fd3558a88c4ccb49ae4045c56ed7b007c9eabe2eb46b31da8cefb9`.

Keep all raw logs and receipts private and inspect retained bytes in the RE VM.
Match the exact control UUID and preceding boot UUID; a marker from the returned
Gemian boot is not a retention pass. No log is cleared. No partition, radio,
calibration, regulator, clock, watchdog setting or USB configuration is changed.
Leave returned Gemian running and record the owner's actual reset observation.

## Execution checkpoint, 2026-09-11

The owner approved this control. An authenticated preflight confirmed the exact
preceding boot and Gemian identity. At `23:17:23 UTC`, the pinned marker program
completed its one 126-byte write, found exactly one matching line in the current
kernel log, rechecked the boot UUID and completed its filesystem sync. It issued
no restart.

The pinned collector was armed before the physical Esc instruction. Its
180-second watch terminated without a qualifying changed-boot Gemian identity.
It made zero console payload reads. The marker receipt and watch diagnostics
remain private; the owner's actual reset observation is still pending.

The result is incomplete: neither successful retention nor loss of a confirmed
marker across a confirmed restart is established. The marker-write budget is
consumed. Preserve the current state and obtain the owner's observation before
deciding how to finish collection; do not rerun either program or request another
restart automatically.
