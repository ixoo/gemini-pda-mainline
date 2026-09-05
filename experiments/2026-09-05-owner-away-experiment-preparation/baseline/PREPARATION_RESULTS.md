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
32 MiB while streaming, and archive members are inspected incrementally. They
cover partial cleanup without log loss, linked/unmanaged state, archive
traversal/links/duplicates, changed hashes,
missing/extra inventory, revision mismatch, verified package reuse, oversized
transfer refusal, timed-out process cleanup and interruption after stdout
closes. They do not simulate an actual network outage. Publication or build failure before a
valid publication receipt remains a failed build requiring review.

## Additional offline gates

The syscall-injected logger harness runs the unchanged capture loop, parser and
seal code against bounded in-memory fixtures. Twelve test methods cover 47
modeled scenarios including signal draining, sequence gaps, deadline, byte cap,
partial writes, atomic publication errors and restart refusal, plus the symbol
audit's own allowed-hook/refused-I/O cases. Symbol checks
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


## Second published attempt and review corrections

Revision `cfe1279f764d2a0fb8826405de928b85ee5ad501` completed the two static
ARM64 build replicas and fifteen parser cases, then failed before the injected
I/O scenarios ran: the Linux executable symbol audit rejected the compiler's
weak `__gmon_start__` profiling hook. No validated package or candidate was
published. Bounded diagnostics survived both remotely and in the local build
log. The fix narrowly admits known ELF startup hooks while retaining the ban
on real file/device/signal linkage. Platform fixture and exact-shell checks are
moved before compilation, so a setup refusal does not trigger unnecessary
repeated binary builds.

The retained Image's embedded `IKCFG_ST`/`IKCFG_ED` gzip member was independently
extracted in memory and exactly matches the package's `kernel.config`, SHA-256
`194834d90eb2443f4b14ba8f2078ba16fe0c63f69088fcc8c063fe25af01c410`.
Thus the first-baseline collector's expected `/proc/config.gz` payload has a
checked artifact basis; physical execution remains untested.

Independent review also found that the first seal protocol refused a failed or
already-exited logger before exporting its unique partial RAM evidence, while
ordinary recovery could destroy it. That protocol is superseded before any
device use: separate admitted bounded log preservation must retain available
failed/partial records without promoting them to a clean-log pass. Ordinary
recovery requires the preserved export; explicit unsafe/emergency recovery stays
available under its separately recorded narrow admission. No prior first-boot
readiness claim exists to retain through this correction.

The export also requires a canonical logger-exit witness before reading the
first log byte. A logger that terminates only after export starts cannot make
an earlier snapshot complete. The host retains bounded raw stdout, stderr,
process results and parsed file prefixes even when framing or transport fails;
errors, file changes and truncation prevent ordinary recovery admission.

Eight focused package-receipt methods pass with Python optimization both off
and on. Parser, injected I/O, pidfd-seal and exact eMMC reports require their
complete 15/12/9/28-test counts, one well-formed result and no skipped or failed
outcomes. The session-shell receipt binds the complete ordered case inventory.
This closes acceptance of short or malformed test reports without changing
any target binary source.

The corrected session layer passes 40 host methods. The generated shell
protocol passes all 61 host-shell cases with Python optimization enabled, ten
effect-guard misuse checks across optimization levels, and four parser
transport checks. Generated shell syntax and ShellCheck pass. The common
repository gate passes, including all 189 manifest profiles; its Linux-only
artifact-provenance fixture is deferred to the explicit userspace Buildbox
run. These host results do not establish exact ARM64 shell or device behavior.

## Exact-shell fixture timing correction

Revision `d8225b8c7cd00bcec291c9cd8c018ca132524711` passed the Linux parser
(15), injected logger (12), pidfd-seal (9) and exact BusyBox init/app-inventory
(25) checks. Its first exact session case exceeded the harness's eight-second
limit, stopping the build before Dropbear extraction or compilation. Selected
diagnostics were retained and disposable staging was removed. No package or
candidate was published.

One bounded diagnostic reran only that positive case from the unchanged
published Git checkout and checksum-pinned BusyBox. It completed in 14.596
seconds: 68 intercepted/file calls, zero exit, no stderr, 1372 stdout bytes,
and independently parsed complete seal and preservation. The isolated
diagnostic used a 45-second cap and process-group cleanup; its staging was
removed. This identifies emulation/fixture overhead rather than a blocked
operation. The fixture deadline is corrected separately from the unchanged
30-second device export budget. Timeout/flood diagnostics and process-group
cleanup are added to the harness before another exact run.

The corrected harness passes seven focused process tests, including bounded
output, timeout diagnostics, descendants retaining or closing pipes, and
interruption during cleanup after EOF. Three representative host exports
confirm unchanged healthy, failed-but-preserved and timed-out classifications.
The full 61-case exact suite remains mandatory in the next Buildbox package.

## Exact-shell descriptor-opening correction

Revision `8abd7a0439dd042e15985497fe62531a1c67f89d` reached the existing
`log-vanished` exact-shell regression, where export stopped with incomplete
framing and no recovered file block. Native parser/logger/seal and the 25
exact init cases had passed. The build again stopped before compilation;
bounded logs were retained and staging removed, with no published package.

A read-only probe of that same BusyBox explains the host/target difference:
failed redirection on the special `exec` builtin exits BusyBox ash even inside
an `if`. Prefixing it with the shell's `command` builtin makes the open failure
return to its refusal branch. A successful open still retains descriptor 3,
verified separately by an EOF read. Both held-descriptor openings use this
form so an unreadable or vanished source is reported while the remaining
bounded files continue to export. Missing bytes still prevent preservation
acceptance. Exact full-suite validation remains required after this fix.

The corrected source passes the focused healthy/vanished-log host checks and
all 40 session integration methods. The vanished-log regression explicitly
requires later final-status and exit bytes to remain available and is ordered
early in the exact suite. The generated seal identity is now
`43a7391076eaf1cf58fe1773d619e973165680a4e63c01f134bf4bc60edfda34`;
the recovery command and device budgets are unchanged.
