# Same-boot keyboard logger restart

The owner requested restarting logging instead of rebooting after preparation
and waiting exceeded the original 240-second boot-age gate. The keyboard
capture never started on boot `e3a29c80-4948-4ef8-893a-cfbef0cd4918`.
Its same-boot disconnect proof and metadata are preserved under admission
`53257257-f01d-4d8a-a2a1-f038457044c0`. The original logger was sealed
successfully, with 1,746 records and 121,076 bytes, before this change.

[restart-logger.py](restart-logger.py) prepares one explicit continuation using
the unchanged installed logger. It verifies the exact boot and executable
identities, RAM-only paths, at least 3 MiB free, no live logger, and the exact
sealed files already preserved on the host. It moves those files and the old
PID record into an exclusively created `keyboard-logger-prior` directory in
RAM, verifies their digests again, and leaves the old seal claim intact.
Nothing is deleted or overwritten. A partial failure retains the archive and
claim and does not automatically retry.

One held SSH connection owns and reaps the new logger. The logger retains its
600-second/2-MiB limits and its requirement to read an unbroken sequence from
zero. A ring gap or expiry remains a failure. The parent records the new PID
and a conservative monotonic start time before announcing startup; interruption
uses the installed pidfd-based seal helper, then waits for the child. The host
connection is capped at 620 seconds, 1 KiB stdout and 16 KiB stderr.

The capture admission explicitly selects `logger_clock: restarted`.
[capture.py](capture.py) still checks the live logger executable/PID and absence
of terminal files. Its start gate now additionally verifies a private regular
clock record matching this boot and logger PID, rejecting malformed, future or
expired times. The 240-second start limit is measured from this fresh logger;
legacy admissions retain their boot clock. Neither capture duration, event/byte
limits, monitor deadlines nor input acceptance changes.

The existing same-boot metadata remains historical metadata at its recorded
collection time. Every launch rechecks input ancestry, capabilities, resource
links, map, console ownership and readers. The unchanged monitor and server
identities and all seven raw disconnect evidence members are independently
revalidated; the earlier proof is not rerun or rewritten when the capture
source closure changes. No keyboard capture claim has been consumed on this boot.

The original proof-only seal remains immutable. After keyboard export, use a
fresh `restarted-log-seal-attempt` claim and preserve the new log separately.
Require a successful new seal and completed logger connection before accepting
log coverage. Recovery remains subject to explicit owner confirmation; this
continuation neither requests a reboot nor writes a partition.

Validation: existing capture and prerequisite fixtures pass, including nine
clock boundary/malformed-record cases. The generated restart shell passes Bash
syntax, ShellCheck (excluding literal-awk and trap-callback false positives),
and ARM64 BusyBox `sh -n` under the retained Buildbox QEMU. These are offline
checks, not a runtime success claim. No binary rebuild is needed.
