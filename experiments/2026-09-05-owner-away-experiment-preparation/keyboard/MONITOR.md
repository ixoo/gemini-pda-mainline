# Minimal keyboard monitor: source-only handoff

This implements the direct-child reduction from
[CAPTURE_DELIVERY_DECISION.md](CAPTURE_DELIVERY_DECISION.md). The production
entry unconditionally refuses. No runtime admission, executable delivery,
candidate change, backend build or device operation is enabled. The retained
observer, its protocol and the first authenticated baseline are unchanged.

## Source and contract

[monitor.c](monitor.c) starts only
`/bin/keyboard-observe --capture eventN 13 MINOR`; numeric arguments must be
canonical and bounded. Its internal caller must provide the already verified
private RAM parent and actual admission. That caller is deliberately absent.
There is no CLI path, command string or production fixture selector that enables
the engine. Merely moving or compiling this source cannot enable the default
entry. The existing baseline/metadata/reader-exclusion/delivery prerequisites
remain unset; fixture directories do not assert any of those real facts.

The engine consumes one `keyboard-attempt` directory before fork and exclusively
creates `observer.stdout`, `observer.stderr` and `monitor.status`. The child's
stdout/stderr point directly at retained files. Its regular-file limit is
lowered to at most 96 KiB, including any smaller inherited limit; the parent
never raises the existing limit. Nonempty stderr refuses. There is no second
event/VT byte-accounting implementation, pipe-to-file tee, descendant tracker,
process-group signal, keepalive or shell. The input observer still owns its
existing event limits and restoration behavior.

One bounded `pread`/nonblocking stdout write per loop forwards already-retained
bytes. Partial writes advance only by bytes actually forwarded; closed or full
forwarding pipes refuse and start cancellation. The monitor never waits for a
pipe EOF to infer child exit. Linux `close_range`, using the libc platform
header's syscall number, closes all extra child descriptors before the fixed
exec; unsupported calls refuse. No handwritten syscall or signal-frame ABI is
introduced. The non-Linux host fixture uses its explicitly bounded fd range.

The sole parent uses `waitid(WNOWAIT)` and never signals after `waitpid` releases
the child identity. Loss of wait ownership refuses further numeric-PID signals.
TERM/KILL/reap targets are 210/214/215 seconds from the monitor's monotonic start;
cancellation shortens the grace/reap interval within the same final deadline.
Actual signal/reap times, errors, missed deadlines, child status and retained/
forwarded byte counts are recorded. An unreapable kernel task is an inconclusive
deadline violation, not a promise userspace can force arbitrary kernel progress.

The RAM status is insufficient for acceptance. A separate outer process result
must also be zero. Cancellation after status writing returns nonzero; restoring
default signal dispositions before the final check makes a still-later signal
terminate the process instead of silently setting a flag after that check.
Status/output sync failures and final overruns likewise withhold success.
`normal-lifecycle-only` says nothing about actual keyboard behavior: complete
observer framing/restoration, its existing classifier, postflight, log capture,
private-output preservation and recovery remain required. Preservation of these
new files is not implemented by the kmsg-only export.

## Host checks and limits

[monitor-fixture.c](monitor-fixture.c) compiles the same engine with short
300/380/500 ms deadlines and only built-in harmless children. It has no exec
path to the observer and opens no input/VT device. The fixture verifies that an
intentionally inherited fd is closed and stdin is replaced by `/dev/null`.
[test-monitor.py](test-monitor.py) compiles with native Apple Clang 21.0.0,
`-Os -Wall -Wextra -Werror`, under the managed ignored artifact root. Every case
retains the monitor PID with `WNOWAIT` until any required fixture-group cleanup
finishes; production code never uses these group signals.

Eleven test methods passed in 1.807 seconds. They cover normal exact retention/
forwarding and one-shot refusal; INT/TERM/HUP/PIPE; ignored TERM followed by KILL
and reaping; closed child output while still alive; forwarding close/stall;
nonzero exit and stderr; an inherited 512-byte file ceiling that is not raised;
and cancellation both before and after final default-signal restoration.
Ordinary cases also run under the 128 KiB inherited file limit. No actual
evdev/VT ioctl, ARM64 Linux executable, SSH disconnect or full-duration timing
test ran. These host results cannot establish those target boundaries.

The first host run failed in the test harness's unconditional signal of an
already terminal group; the monitor's completed child had been reaped. Darwin
returned EPERM. The harness now recognizes that completed two-process fixture
and still cleans incomplete cases while retaining the monitor identity. A
filtered local process check subsequently found no remaining fixture processes;
no temporary fixture files or binaries remain. That failed run is not counted
as passing lifecycle evidence.

## Size and provenance proposal — review before a Buildbox window

**Delivery admission is at most 131,072 bytes for the complete linked executable.**
No ARM64 size has been measured and deliverability is not claimed. Measuring the
tiny disabled `main` after dropping the unused engine would be invalid: every
size-test link must retain `keyboard_monitor_run` with
`-Wl,-u,keyboard_monitor_run`, and its link map must confirm that full engine.

The retained userspace package pins the existing cross compiler and linker:

| Input | SHA-256 |
| --- | --- |
| Debian `aarch64-linux-gnu-gcc` 12.2.0-14 | `c7b8890354c8ddc0364addfeb8968597e197627bd1e338fb6ed705b578803846` |
| `aarch64-linux-gnu-ld` | `e09a889c78a75e73ed096c9fa28905599e6813298b9ac839d10b02ffa96e7b08` |

No suitable smaller library has retained provenance in this packet. Do not
assume that a tool installed on a builder is an admitted input. The concrete
new-library proposal is [upstream musl 1.2.6](https://www.openwall.com/lists/musl/2026/03/20/1),
built with that same compiler, rather than a new compiler or handwritten
freestanding ABI. Its official release archive was inspected in memory only:

| Proposed input | Bytes / SHA-256 |
| --- | --- |
| [musl-1.2.6.tar.gz](https://musl.libc.org/releases/musl-1.2.6.tar.gz) | 1,082,499 / `d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a` |
| Archive `COPYRIGHT` | `b870108ec5e7790e9f9919064f1b9421d62d5f9b0e6c230c6adf7ea2da62e97b` |
| Archive `configure` | `aa6574f8049f80f3b0a464bc20ab377a57bc0d3464478ac7ccb500f10002cd78` |
| Archive `tools/musl-gcc.specs.sh` | `ef7baf50ae403b3bf40c7403754daac024de9acf3c83e9b7b4cb9f80eaead343` |

These are HTTPS download byte pins, not a claim of verified release signatures.
The archive's MIT license and attribution must accompany any later retained
linked artifact. No musl source tree/library has been installed, built or added
to the repository/candidate. This new input requires the coordinator's review
before a window; its potentially smaller result remains an unmeasured proposal.

The exact bounded compile plan, after input and window review, is:

1. Use the assigned Buildbox locks and a clean Git-fetched published source
   revision. Check free space and the existing compiler/linker pins. Record the
   compiler's resolved `cc1`, `libgcc`, assembler, archiver, strip tool and package
   identities; stop on unexplained input drift. Reuse an existing matching
   admitted musl library if available; otherwise verify the archive above and
   build one static library in a managed temporary directory with immediate
   cleanup traps. Retain no second kernel/source tree.
2. For musl, configure with `CC=aarch64-linux-gnu-gcc`,
   `CROSS_COMPILE=aarch64-linux-gnu-`, `--target=aarch64-linux-musl`,
   `--disable-shared`, `--enable-wrapper=gcc` and a managed private `--prefix`.
   The inspected upstream configure/specs support this existing-compiler wrapper;
   musl supplies startup, headers, signal ABI and libc. No system installation.
3. Link the unchanged source through that prefix's `musl-gcc` using
   `-std=c11 -Os -static -ffunction-sections -fdata-sections -Wall -Wextra -Werror`
   and `-Wl,--gc-sections,-u,keyboard_monitor_run`, with a retained link map and
   deterministic source/build prefix mappings. Build two independent object/link
   outputs against the one library. Check AArch64 ELF, no interpreter or dynamic
   dependency, retained engine, matching replicas and the final stripped file
   size at most 131,072 bytes. Stop on excess; do not raise file limits or substitute
   a dynamically linked artifact. Record exact library/header/tool/source/output
   hashes and the license; remove temporary builds after evidence capture.
4. Only within that same explicitly assigned execution scope, use separately
   compiled harmless fixtures to check exact Linux child fd closure, WNOWAIT,
   cancellation and forwarding. Real production durations need a separate
   reviewed harmless 202/210/214/215-second fixture; the scaled host tests do not
   supply that result. A source/ABI/size failure stops before target delivery.

Actual executable RAM location, transport byte/readback checks and runtime
admission remain the existing independent gates. No `/run` mount change,
limit increase, first-baseline retest, observer replacement or boot is proposed.


## Runnable userspace package path

[build-monitor.sh](build-monitor.sh) now implements the bounded compile path.
The existing [userspace dispatcher](../baseline/scripts/buildbox_userspace.py)
selects it with `--keyboard-monitor`; `--keyboard-monitor --fetch-only REVISION
MANIFEST_SHA256` retrieves an already validated package without compiling again.
The normal userspace selection is retained. The same dispatch and userspace
locks serialize work. Only a clean published worker revision is eligible.

After coordinator source review and an assigned userspace window, invoke:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/buildbox_userspace.py --keyboard-monitor
```

One invocation has a 1,200-second remote compilation/validation ceiling within
the existing 1,800-second dispatch ceiling. It checks at least 512 MiB free,
verifies compiler/linker and archive/member pins, configures/builds one private
static musl library, and links two independent full-engine outputs. The checked
map and defined symbol precede stripping; AArch64, static linkage, byte equality,
and the 131,072-byte limit are required. The actual full-engine binary must also
return the exact disabled-entry refusal under QEMU and the inherited file limit.

The existing 11-method fixture suite accepts explicit compiler/QEMU/work-root
inputs for this build. It exercises the Linux branch under ARM64 QEMU with
scaled deadlines and no real input/VT device. QEMU incompatibility or any failed
case stops publication; no target success is inferred from the native host run.
Full-duration timing remains outside this invocation and requires its own review.

The package retains source/archive hashes, resolved tool hashes and package
versions, all installed library/header/wrapper hashes, link map, test results,
exact stripped size, and repository, musl and GCC notices. Compiler/linker and
musl pins are the reviewed proposal above; additional resolved tool identities
are captured for review, not silently described as previously admitted pins.
Temporary source/build/fixture directories are cleaned on success or failure;
failed compiler/test logs use a finite per-revision diagnostic destination.
Only the validated package is fetched through the existing checked extractor.

Local validation: all 11 native fixture methods pass; two routing tests cover
both package kinds and fetch-only behavior with mocked transports and the real
package extractor. Python parsing, shell syntax, ShellCheck (including both
embedded dispatcher scripts), and whitespace checks pass. No backend execution,
ARM64 compile/QEMU result, size measurement or device action is claimed yet.

## Integration review

Project Planning reviewed the disabled production entry, direct-child lifecycle,
fixture source and test harness at `89d4ece6`. Independent native host execution
passed all 11 test methods in 1.745 seconds. This accepts the source-only handoff;
Linux behavior, complete timing, size and delivery remain unmeasured.

The proposed musl 1.2.6 input is accepted for preparing the bounded build: the
integrator checked the primary release announcement, independently matched the
official archive's exact size/hash and all three member pins above, and reviewed
its license. An initial default-address connection timed out; a bounded IPv4
fetch succeeded. Only in-memory archive inspection occurred. Retained linked
artifacts must include applicable copyright/license notices, including notices
for linked third-party portions; preserve the full archive COPYRIGHT record.
No Buildbox window or target execution is granted by this input review.

## Build tooling integration review

Project Planning reviewed `dd6ebd84` and the focused main-branch proposal from
`3b3f8474`. Independent native execution passed all 11 monitor methods; routing
tests cover both package kinds, both allowed branches and early refusal of an
unlisted branch. Shell syntax and ShellCheck pass. The original source review
above is preserved. This accepts a bounded Buildbox userspace measurement of
the full retained engine, the pinned musl input and the scaled ARM64 fixtures.
Production entry remains disabled, and this is not device delivery admission.

The assigned invocation uses `--keyboard-monitor --branch main` from the clean
published integration revision. The existing backend window is free; no kernel
build or source copy is selected. Host free space was approximately 86 GiB; the
builder independently requires 512 MiB before extraction. Publication and fetch
must finish before changing the integration checkout. A failed run remains
evidence for review, not permission for an automatic retry.
