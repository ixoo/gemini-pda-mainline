# Fixed-set debugfs snapshots — review draft

This replaces a boot-triggered collector with a read-triggered diagnostic.
Device experiments, installation and a connected-state capture remain on hold
until the design is reviewed. A build or fixture is not hardware evidence.

## Interface and admission

The interface requires `CONFIG_DEBUG_FS` and `CONFIG_CFG80211_DEBUGFS`. A
missing wiphy debugfs parent disables the interface rather than creating a
global fallback directory. The compile-only profile is `mt6797-a53-wifi-snapshot-compile`. Its parameter
`mac.snapshot_enable` is immutable after boot and defaults to false. Without
that parameter no directory is created. With it, the directory below the
wiphy's debugfs directory is `mt6797_snapshot`:

| File | Access | Meaning |
| --- | --- | --- |
| `gate` | root read/write | Defaults to zero; admits new reads only when one |
| `set` | root read/write | Exact name of a kernel-compiled set |
| `snapshot` | root read-only | Blocking read; little-endian 32-bit words |
| `status` | root read-only | State, collected/total words, last error and generation |

All access additionally requires `CAP_SYS_RAWIO`. There is no arbitrary-address
interface, userspace range, offset, length, mode, or write-value input. File read
sizes select bytes from the result buffer only. Files are nonseekable. A zero-byte
read issues nothing. The public provider is empty: no sets or wire encoder ship
in this patch, and it cannot perform a firmware transaction.

A set is frozen when a read starts. Every set must contain 1–2,048 aligned
32-bit words without arithmetic overflow. Range ordering and overlaps are
preserved. A concurrent snapshot is refused; a selector change during a running
snapshot is refused. A successful later read receives a new generation. Open
readers keep immutable, reference-counted results after a later selection/read.
Admission refusals are returned as syscall errors and do not replace an active
or previously retained result; status identifies its own generation.

The binary contains only the successfully completed query prefix, at most
8,192 bytes. Status is authoritative: a partial read can return bytes while
`last_error` is nonzero. Setting the gate to zero prevents new work but does not
cancel an already admitted read. With the gate off, `snapshot` retrieves the
retained result without issuing another transaction. A signal can interrupt the
reader; it does not silently retry or restart the bounded collection.

## Timeout, failure and lifetime

Each snapshot has a fixed 60-second deadline. A separate timeout worker wakes
the reader even if the normal MAC worker cannot progress. The reader also checks
that same absolute deadline. Late backend completions cannot modify a terminal
buffer. Timeout/failure latches diagnostic poison; toggling the gate does not
clear it or authorize another wire attempt. The completed prefix remains
available with the gate off. A pre-wire diagnostic rejection does not itself
stop an otherwise healthy connection; the backend reports a driver failure only
when the transport/lifetime is poisoned.

Firmware configuration must already be published before admission. The backend
must recheck actual firmware/lifetime ownership before every query. A connected
provider must reject a stopped, disconnecting or poisoned lifetime. The normal
stop/failure paths terminate a waiting snapshot. Removal closes admission before
cancelling work, wakes readers and removes the files; references keep their
buffers/context alive until the last file is released.

## Locking and progress contract

The debugfs thread never holds MAC, RTNL or HIF locks while waiting. The short
snapshot mutex protects admission, status and result publication only. It is
released before calling a backend. Request allocation/reclaim occurs outside
that mutex too. Normal close and the shared terminal path fence the running
state before terminating snapshots, so a racing admission is rejected or caught
by the stop hook before worker cancellation. The ready predicate is memory-only, and the
kick callback schedules work without acquiring a driver lock.

The existing MAC worker services ordinary TX, RX and control/link-loss handling
before one snapshot step. It releases the MAC mutex at the end of every pass.
A pending snapshot schedules the next pass after one jiffy; it does not create
a second command/RX owner or hold the HIF mutex across the dump. The backend
must take/release the existing command mutex for bounded individual operations
and maintain at most one query in flight. A per-query deadline is clamped by the
absolute snapshot deadline and is never renewed by polling.

The wire provider must route ordinary beacons/data through the existing RX and
crypto checks, including while a query is pending. Query replies must be
validated before their companion. Exactly one classified companion and complete
credit reconciliation are required before the next query. An unexpected reply,
second companion, transport anomaly or observed link loss terminates the
snapshot. A timed-out or indeterminate command retains fatal poison; it is not
made reusable by clearing a debugfs flag. Existing resource caps remain in force.

This scheduling structure permits RX/TX/link-loss progress between transactions;
it cannot promise RF delivery or successful firmware behavior. A populated
provider needs actual-source interleaving, credit, deadline and loss fixtures,
plus a separately reviewed connected experiment. No such experiment is run by
this patch. The public empty provider cannot validate a firmware contract.

## Security review points

- No firmware setter or write-value operation exists in the public mechanism.
- The wire backend must encode the read-mode byte as a compiled literal zero,
  with no setter branch, mode argument or userspace override.
- Addresses/counts come exclusively from const kernel tables; selection only
  names one table. The public table is empty.
- The immutable module parameter and default-off runtime gate are independent.
- Configured firmware is mandatory before admission; the backend must enforce
  the stronger live-connection requirements at each query.
- Snapshot bytes are never logged by this mechanism and are cleared on free.
- A snapshot is sequential, not an atomic firmware image. Start/finish times and
  generation in status identify the sample without claiming atomic consistency.

## Validation boundary

The focused set-policy fixture runs against the actual source helper. It covers
ordering, the 2,048/2,049 boundary, overflow, alignment, and unchanged output on
rejected ordinals. Source-wiring checks cover default-off admission, lack of a
binary write method, per-reader retention and backend calls outside the snapshot
mutex. Kernel compilation and filesystem/concurrency behavior are separate
checks; no device test is implied by host fixtures.

## Current review evidence

[Validation record](results/debugfs-snapshot-validation.json): the exact public
input `c78cb892` compiled and its package validated/fetched on Buildbox. Linux
set-policy/source-wiring and repository checks passed. The first compile exposed
the removed `no_llseek` symbol; the corrected null seek handler is paired with
`nonseekable_open`. Strict checkpatch reports zero errors, three warnings and twelve
style checks; style cleanup is outstanding before upstream submission.

The filesystem lifetime/concurrency paths have been source-reviewed, not run in
a test kernel. Device execution and installation remain held for design review.

## Pre-install concurrency follow-up

The actual snapshot.c file operations now have a focused pthread service-shim
stress test, `tests/snapshot-fops-stress.py SOURCE`. It exercises a gate-on
concurrent reader (EBUSY), signal interruption and release of the waiting reader,
open/close without reading during acquisition, generation retention, subsequent
gate-off retrieval, and owner removal with an open reader. ASAN/UBSAN passed100
rounds on Linux. No production code or policy changed for this test.

This does not run mounted debugfs or a real SIGKILL/exit_files path. Debugfs,
uaccess, capability and timer services are simulated; mutexes, waits and signals
are concurrent host primitives. That requested operating-kernel filesystem
corner remains unverified. The available build container cannot load a module
or mount a debugfs test instance. No device experiment or installation was used
to work around the missing host coverage. Existing checkpatch style notes remain.
