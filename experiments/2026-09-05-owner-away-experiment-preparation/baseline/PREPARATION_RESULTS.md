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

## Exact session pass and eMMC fixture correction

Revision `e9370067438563fa11685e711f4450168fcf77aa` passed all 61 exact
ARM64 BusyBox session cases, including the vanished-log export regression,
seven bounded-runner checks, ten effect guards and four parser-transport checks.
Its native parser/logger/seal and 25 exact init cases also passed. The eMMC
suite passed 26 of 28 methods; the positive observer and classifier-mutation
methods exceeded the fixture's 30-second ceiling. The run stopped before
compilation, retained bounded diagnostics and removed staging. It produced no
validated package or candidate.

An independent diagnostic from unchanged published revision
`8abd7a0439dd042e15985497fe62531a1c67f89d` reproduced the same two fixture
timeouts. A single positive observer run with a 90-second diagnostic ceiling
completed in 30.515 seconds, with zero exit, no stderr and 923 stdout bytes.
The classifier accepted exactly one 16 MiB read as partial read-integrity
evidence; independent log, serviceability and changed-ID recovery remain
required. The diagnostic staging was removed. This measurement supports a
fixture-only timing correction; it is not package or hardware acceptance.

The exact observer fixture ceiling is now 90 seconds, with the host-mode
ceiling remaining 30 seconds. Explicit timeout regressions retain their
4/6/7-second limits; the actual observer's 20-second read deadline and planned
40-second transport ceiling are unchanged. The harness bounds stdout to
128 KiB, stderr to 16 KiB, cleanup to one second, and diagnostics to short
stream and dispatch tails. Six independent process tests cover timeout,
stream overflow, descendant cleanup and interruption, including after EOF.
Their complete receipt is mandatory in the userspace package and bound to the
published test source. The complete exact eMMC suite must pass before the
next session suite and compilation run.

All six runner methods and eight receipt-refusal methods pass locally; the
receipt checks also pass with Python optimization enabled. Independent review
found no actionable runner issue. Bash syntax, ShellCheck and the common
repository gate pass, including all 189 manifest profiles. The Linux-only
provenance fixture remains part of the forthcoming Buildbox run. No kernel
build, DT/schema, device or runtime acceptance is claimed by these checks.

## Validated userspace package and private candidate

Published revision `e9c028005b88ef8536ecb58c095e8d172253fa12` completed the
Git-fetched userspace Buildbox workflow. All six static ARM64 binaries matched
between two independent build directories. The package passed authentication
against the exact emulated server, native parser/logger/seal checks (15/12/9),
six runner methods, 25 exact BusyBox init cases, all 28 exact eMMC methods
(272.128 seconds), and all 61 exact session cases with ten effect guards and
four parser-transport checks. The Linux artifact-provenance fixture passed
four positive cases and rejected 21 mutations. The validated package was
fetched through the bounded publication-receipt workflow, then independently
validated locally against its complete 23-file inventory and published source.

| Identity | SHA-256 |
| --- | --- |
| Userspace `SHA256SUMS` (22 members) | `dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60` |
| Raw Android-v0 `boot.img` | `a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf` |
| Full 16 MiB `boot2-padded.img` | `a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821` |
| Private `candidate.json` | `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179` |
| Composed `initramfs.img` | `a678c4051204754dbb8043b25d3f61e0e6b4936fc4c92bea012140b9b6687d7a` |

The raw container is 8,722,432 bytes, the initramfs is 3,055,358 bytes with
47 members, and padding is exactly 16,777,216 bytes. Two fresh initramfs and
container assemblies matched. Independent validation confirmed the retained
Image/DT/config, exact member delta, credentials/options, static binaries,
source-bound test receipts, LK fields and zero padding. All 23 real private
candidate mutations were refused; the temporary copy was removed and the
original remained unchanged. The all-zero Git-revision mutation deliberately
produced Git's missing-path diagnostic before its expected refusal.

The guarded installer's default local validation passed Bash syntax and
ShellCheck, with generated installer SHA-256
`c3621fbc7a037708b217551ede8f6ec5d9317529084f1876e784d195dcaa5b22`.
It made no connection or device change. Package, candidate and host credentials
remain private below ignored artifacts; the candidate contains a private host
key and must not be published. The build staging and disposable authentication
fixtures were removed. The historical kernel was neither rebuilt nor changed.

Construction is complete, but session readiness remains preparing pending
coordinator review of the candidate and corrected host evidence handling below. There is no
physical admission, deployment, boot, live pidfd/VT/evdev evidence or support
claim for this candidate.

## Host evidence snapshot correction

Independent review of the dependent packet drafts exposed a verify-then-read
race. The same pattern was reproduced in the baseline finishing helper: an
observation manifest bound to a CPU0–9 failure could be followed by replaced
CPU0–7 stdout after inventory verification, and preparation accepted the
replacement. Rechecking the same sequence before dispatch does not bind the
parsed bytes to the admitted manifest. The host-only correction retains
hash-verified bytes for classification and binds returned collector preparation
inputs to that snapshot. Original admission, deployment and candidate bytes
must match the snapshot; prior authentication, log export and native recovery
commands, process records and results are all parsed from bound snapshots.
No target shell, userspace package or candidate bytes changed.

All 47 host session methods pass normally and with Python optimization enabled:
40 existing methods plus seven deterministic race regressions, including
replacement after inventory or snapshot acquisition and changed collector
preparation inputs. The corrected finishing helper has SHA-256
`f6fc5cf6a73518385af714b4f8566e32e4b231338cf231b0204d0b5aa96564a0`.
Admissions must pin this corrected source. The generated seal and recovery
identities retain their exact-shell validation from the successful package.

After integration, all 47 session methods passed again and the existing private
candidate independently revalidated without reconstruction. The common
repository gate passed, including all 189 manifest profiles. The Linux-only
provenance gate had already passed in the successful package build; no kernel,
DT/schema or device test was added for this host-only correction.
