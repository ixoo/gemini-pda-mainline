# Kernel-log control-flow fixture contract

[`test-kmsg-io.py`](../test-kmsg-io.py) compiles
[`kmsg-io-harness.c`](kmsg-io-harness.c), including the unchanged
[`kmsg-capture.c`](../src/kmsg-capture.c) production `main`, parser, signal
handler, write loop and finalization code. It does not define the parser-only
`KMSG_CAPTURE_NO_MAIN` option. This is a test executable compiled from the same
source, not the shipped AArch64 binary.

The harness replaces effectful syscall calls at compile time. It never forwards
an intercepted call to the host kernel. Only `/run/a53`, `/dev/kmsg`, and the
three declared file names are recognized, as names in an in-memory model.
Unexpected paths, file descriptors, flags, effects or more than 1000 modeled
operations fail explicitly, including with C assertions disabled. The produced
executable's undefined symbols are checked against a small allowlist before
execution, excluding real device/file I/O, signal registration, polling or
clock calls. Host libc is used for memory/string operations, local signal-set
objects, test reporting and process startup only.

The model supplies whole kernel records, `EAGAIN`, `EINTR`, `EPIPE` and other
read failures. It invokes the installed signal-handler function directly at
specified read/poll boundaries; it does not deliver real signals. Its monotonic
clock is virtual, so the 600-second deadline is tested without waiting. Its
file model records exclusive creation, byte writes, synchronization, atomic
no-overwrite publication and cleanup in an independent event trace. Python
checks exact status fields, return values, record/read counts, file-content
fingerprints and ordering. The fingerprints are test comparison checksums,
not artifact identity or authenticity evidence.

The 11 test methods cover 47 distinct scenarios:

| Boundary | Modeled cases |
| --- | --- |
| Capture completion | One record; SIGTERM with two pending records drained before EAGAIN; empty-log refusal |
| Interruptions | SIGINT, SIGHUP, SIGINT then SIGTERM, SIGTERM then SIGINT; read and poll EINTR |
| Continuity | Initial gap, later gap, duplicate, malformed record, EPIPE, POLLERR followed by EPIPE |
| Bounds | Exactly 2 MiB followed by a seal; refusal before writing a record beyond 2 MiB; no next read at the 600000 ms deadline |
| Read/clock/poll failures | EIO, EINVAL, EOF, clock failure/backward movement, poll failure/device loss |
| Writes | Partial/EINTR log and status writes, zero write, partial log then ENOSPC, incomplete status, log/status sync errors |
| Finalization | Kmsg close error; failed or raced final link; partial cleanup and directory-sync errors |
| Evidence retention | Existing log/partial/final, racing final receipt and a second invocation preserve earlier bytes and refuse a new capture |
| Preconditions | Wrong directory owner/mode, non-character device and failed device open |

Run on the host or authorized Buildbox userspace environment:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/test-kmsg-io.py
```

`KMSG_TEST_WORK_ROOT` optionally selects an existing managed directory instead
of `/tmp`; a private temporary child contains only compiled test products and
is removed on success or failure. Each scenario has a five-second host process
deadline. No credentials, actual device nodes, kernel log messages or physical
device access are needed. The existing [parser tests](../test-kmsg.py) remain
separate and cover additional malformed-header and extension cases.

Local macOS validation passed all 11 methods/47 scenarios, the strict native C
compile, host-linkage audit and existing 15 parser methods. A Buildbox rerun and
its immutable package evidence remain the baseline owner's responsibility.

The tests explicitly preserve an important finalization boundary: failed partial
cleanup or directory synchronization can leave a complete `result=pass` content
receipt while the production main returns nonzero. Acceptance therefore needs
both the pinned complete receipt **and a recorded zero helper exit status**.
A missing process outcome cannot become a successful capture merely because
the status file exists. Log finalization must precede any claim that the capture
has ended, and no new observation may start after it has sealed or expired.

These fixtures do not prove Linux `/dev/kmsg` semantics, real signal delivery
and scheduling, actual filesystem atomicity, QEMU syscall behavior, startup
loss on the named board, or the shipped helper's complete execution path.
Those remain distinct candidate/runtime gates. No hardware readiness or support
claim follows from a successful injected-syscall test.
