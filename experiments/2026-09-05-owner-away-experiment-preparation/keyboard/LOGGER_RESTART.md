# Same-boot keyboard logger restart

The owner requested restarting logging instead of rebooting after preparation
and waiting exceeded the original 240-second boot-age gate. At preparation time, the keyboard
capture had not started on boot `e3a29c80-4948-4ef8-893a-cfbef0cd4918`.
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
source closure changes. At that preparation point, no keyboard capture claim had been consumed on this boot.

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

## Explicit retry after an incomplete capture

The first restarted-logger capture stopped during prompt two after 64 event
records, including modifier repeats. The observer reported console restoration;
the monitor reaped it after 21,504 ms. The owner reported pressing the wrong
buttons in order and explicitly requested a retry without rebooting. Capture
and logger exports were retained. The logger SSH connection closed remotely
after 60.702 seconds with exit 255; the independent seal still verified terminal
state and complete sequence-zero coverage (1,746 records, 121,076 bytes).
This is an incomplete keyboard attempt, not a passing regression.

[retry.py](retry.py) prepares that explicit continuation. It verifies the prior
export, restored observer and reaped monitor, current console identity and reader
exclusion, and every delivered binary, license and capture-file digest. It moves
the completed delivery directory to a fresh UUID-named RAM archive and verifies
the digests again. The logger restart separately verifies the sealed log and
archives the prior clock with its files. Existing archives and seal claims stay
intact. Partial failures are retained and never automatically retried.

The admission retains its same-boot prerequisite identity and adds an explicit
`runtime.retry_id`; capture/export records live below its separate `retries`
directory. The existing monitor exclusively creates the new attempt directory.
Every launch retains the full identity, map, resource, reader, event and deadline
gates. An owner retry request does not imply that the previous sequence passed.
A fresh UUID alone does not archive or remove any device state.

For the held logger SSH connection, use `ServerAliveInterval=15` and
`ServerAliveCountMax=3` to avoid an otherwise silent connection. Its existing
620-second host and 600-second logger limits remain. This is a response to the
observed silent-connection closure, not proof of its cause. Require actual
connection completion and the independent seal before accepting the next log.
No kernel rebuild, partition write or reboot is required.
