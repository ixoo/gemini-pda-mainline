# Authenticated A53 preparation evidence

State: **preparing; no selected/deployed new candidate and no device access**.
This record owns chronology, exact construction identities and rejected paths.
It does not update hardware support or order project work.

## Historical input audit

The [foundation audit](BASELINE_AUDIT.md) validates the retained package and
candidate in place against immutable historical Git inputs: 646 package files,
12 candidate files, 505 ordered patches, eleven fragments and all 38 inherited
initramfs members. The runtime-proven Image, composed DT and resolved config
are unchanged. Current similarly named profiles do not reproduce that package.
The exact BusyBox was independently found in its checksum-pinned public Ubuntu
package; [provenance](BUSYBOX_PROVENANCE.md) records the limits of that finding.
No kernel source tree was copied or rebuilt for this userspace delta.

## First published userspace attempt

Revision `9923aed57d2743eed7e4ac234ab4bc61e2db7dd9` ran the Git-fetched isolated
userspace build on Buildbox. Both static ARM64 replicas and authentication steps
completed, but final eMMC test setup failed before any observer fixture ran.
The first dispatcher retained only stdout; its cleanup removed redirected test
logs. No validated package was published or fetched and no candidate was built
from this attempt. An exact unchanged-Git diagnostic rerun recovered the cause:
QEMU lookup rejected the installed static-emulator path.

That diagnostic run passed all 25 exact BusyBox shell/app-inventory cases.
Its `ulimit -f` unit is 512 bytes, so the candidate's inherited `ulimit -f 256`
is a 128 KiB regular-file ceiling. Pipes and SSH output need the independent
host capture bounds. The fixture mocks effectful hardware operations; it does
not boot init or execute Linux VT/evdev ioctls.

The eMMC review also found that timing a non-exec shell can leave its reader
child alive after the deadline. The observer now times `dd` directly and records
its status outside that timed process. The exact-mode regression fixture must
both stop a directly timed emitter before later output and demonstrate the old
shell's surviving output. Canonical QEMU executable lookup and a refusal fixture
are included. Neither fix is a hardware result.

## Failure diagnostics and exact package recovery

The dispatcher now preserves combined build output locally and bounded selected
remote failure logs. Keys, full source trees and private authentication fixtures
are excluded from diagnostics. Build staging remains disposable; failure is not
an excuse to retain a second source/build tree.

A successful package publishes an exact revision-to-manifest receipt under the
isolated Buildbox root before announcing success. After transport loss, use:

```sh
bash experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/run-buildbox-userspace.sh \
  --fetch-only "$PUBLISHED_REVISION" "$PUBLISHED_MANIFEST_SHA256"
```

This path never runs a build. It verifies the remote publication receipt,
manifest, every member and repository revision; validates the transferred exact
inventory; reuses an already matching local package; and rejects corruption.
A per-revision transfer lock permits cleanup only of the fixed managed
`.fetch-userspace` partial directory. Symlinks, foreign owners and unexpected
file types refuse. Failed build logs and existing verified exports are retained.
If success was published but its stdout was lost, inspect the exact remote
`published/<revision>` record read-only to obtain the manifest identity. Do not
choose a package by timestamp or rebuild to recover a lost download.

Thirteen local transfer/refusal fixtures pass. Transfer output is capped at
32 MiB while streaming, and archive members are inspected incrementally. They cover partial cleanup without log
loss, linked/unmanaged state, archive traversal/links/duplicates, changed hashes,
missing/extra inventory, revision mismatch, verified package reuse, oversized
transfer refusal, timed-out process cleanup and interruption after stdout closes. They do
not simulate an actual network outage. Publication or build failure before a
valid publication receipt remains a failed build requiring review.

## Additional offline gates

The syscall-injected logger harness runs the unchanged capture loop, parser and
seal code against bounded in-memory fixtures. Eleven test methods cover 47
modeled scenarios including signal draining, sequence gaps, deadline, byte cap,
partial writes, atomic publication errors and restart refusal. Symbol checks
prevent accidental host device I/O. These are not real Linux signal-scheduling,
filesystem or device tests.

The first-baseline collector, guarded installer and finishing session tools have
separate refusal/interruption suites. Exact counts, the next published build,
validated package/candidate hashes and any remaining exclusions are appended
only after their checks complete. [SESSION.md](SESSION.md) defines the handoff
and physical budget; no preparation result itself requests a boot.


## Retained kernel process-handle interface

The already checksummed historical `System.map` has SHA-256
`07bf653ea74c2bae7e8747430d346b98aed850f3b24cf400a68db9612b6a7035`.
It contains `__arm64_sys_pidfd_open` at `ffff800080061ed8` and
`__arm64_sys_pidfd_send_signal` at `ffff800080052b54`. The exact resolved config
has `CONFIG_ARM64=y`, `CONFIG_64BIT=y` and `CONFIG_PROC_FS=y`. This establishes
that the retained kernel includes these syscall handlers and procfs; it is not
an on-device pidfd execution result. The helper still refuses unsupported,
denied, exited or mismatched processes and has no numeric-PID fallback. Its
only signal effect is one SIGTERM sent through the verified process handle;
separate logger exit/status checks determine seal acceptance.
