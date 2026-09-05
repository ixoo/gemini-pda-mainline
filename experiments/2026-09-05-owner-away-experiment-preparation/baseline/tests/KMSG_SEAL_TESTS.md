# Fixed logger seal request

[`kmsg-seal.c`](../src/kmsg-seal.c) accepts no arguments and emits no success
output. Exit zero means that one `SIGTERM` request was sent to the fixed
baseline logger. The caller must separately verify the candidate helper and
logger digests, complete sealed log/status, and recorded zero logger exit
status. This helper does not itself certify capture completion.

The helper reads only the root-owned, non-group/world-writable regular
`/run/a53/kmsg-pid` file. Its complete contents must be one canonical decimal
PID greater than one and no larger than `INT_MAX`, followed by a newline.
The size and complete read must agree; at most 16 read calls are allowed,
including interrupted calls. The candidate executable is a protected regular
file at `/bin/kmsg-capture`.

It obtains a process descriptor with `pidfd_open(pid, 0)`, holds it while opening
the kernel's `/proc/<pid>/exe` reference, and compares that regular file's device
and inode to the held candidate file. The only signal operation is
`pidfd_send_signal(pidfd, SIGTERM, NULL, 0)`. An unsupported syscall, missing
process, unreadable or mismatching executable, or unsuccessful signal request
refuses. There is no numeric-PID signal fallback or caller-selected path.

The process descriptor prevents PID reuse after it is obtained from redirecting
the signal to another process. The kernel interface is documented in
[`pidfd_open(2)`](https://man7.org/linux/man-pages/man2/pidfd_open.2.html) and
[`pidfd_send_signal(2)`](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html).
The baseline's one-shot logger and protected PID-file construction remain
prerequisites: a process descriptor does not authenticate who originally wrote
a PID file, and it does not freeze a process's executable. The reviewed logger
does not exec another program; candidate files and session state must remain
quiescent under the custodian's ownership.

[`test-kmsg-seal.py`](../test-kmsg-seal.py) compiles the production helper's
unchanged main inside the [syscall fixture](kmsg-seal-harness.c). Open/read/stat,
close and both pidfd syscalls are replaced with strict in-memory operations.
No real PID file, `/proc` executable or process descriptor is opened and no host
signal is delivered. An undefined-symbol audit rejects actual syscall, kill or
file-I/O linkage before the test executable runs. Explicit model guards remain
active under `-DNDEBUG`, and temporary products are cleaned from a private
managed child directory.

Local validation passed eight methods covering 35 scenarios:

- matching executable with one signal, short reads and interrupted reads;
- stale pidfd plus a replacement `/proc` process with a matching executable,
  where signaling the original dead process returns `ESRCH` and delivers nothing;
- unavailable pidfd operations, missing process, denied or unexpected signal result;
- different executable inode/device, nonregular executable and missing `/proc` entry;
- directory, PID-file and candidate ownership/mode/type refusals and PID symlink refusal;
- zero, PID one, negative, leading-zero, extra-line, overflowing, unterminated,
  whitespace-bearing, empty and size-changing PID contents;
- read error, a bounded EINTR storm, and refusal of all command arguments.

Run with `python3` from the repository; `KMSG_TEST_WORK_ROOT` optionally selects
the existing managed temporary parent. Each scenario has a five-second host
deadline. Cross-compile the standalone helper through the baseline's existing
two-replica static AArch64 userspace build using the same C11/warnings flags as
the capture helper. Linux syscall constants are required at compile time;
there is deliberately no compatibility implementation for older kernels.

These are modeled control-flow tests, not executions of the shipped AArch64
helper or demonstrations of live-kernel pidfd semantics. Those results and the
combined seal/capture acceptance remain separate evidence gates. A failed or
interrupted seal attempt must not cause an automatic second signal request.
