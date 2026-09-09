# Disconnect and kernel-thread scan correction

The [attended result](DISCONNECT_RESULT.md) exposed two independent problems.
This change preserves that failed result and changes no cancellation acceptance
rule, observation deadline, PID ownership or keyboard-capture admission.

## Quiet output

The monitor checked its output connection only while forwarding new retained
bytes. The harmless child emits one startup marker and then stays quiet. Once
that marker had been forwarded, closing the reader caused no further write and
therefore no broken-pipe indication; the child reached the existing deadline.

The local regression now closes the read end **after receiving the marker**.
It reproduced `reason=deadline` on the original code. The older close fixture
could close before the first forwarded byte, so it did not cover this case.
The monitor now performs a zero-timeout poll of its output descriptor before
the no-new-bytes return. Error, hangup or invalid-descriptor events use the
existing forwarding-failure cleanup path. Writable readiness itself changes
nothing; the existing loop sleep and all timing limits remain.

The revised quiet-child fixture requires forwarding failure, early TERM and a
reaped child within the original bound. It passes locally with the correction.
This is a closed-pipe regression, not proof of how Dropbear delivers closure on
the PDA; that remains the distinguishing observation of a new device test.

## Kernel threads

A root observation in the RE VM confirmed that `/proc/2/exe` is a symlink but
`readlink` fails with ENOENT, with empty command line and zero descriptors.
That reproduces a real Linux counterexample to the exporter's symlink check.
It does not attribute the prior PDA refusal to a particular process.

Linux 7.1.3 `fs/proc/array.c:task_state()` reports the `Kthread` field from
`PF_KTHREAD`; its definition is in `include/linux/sched.h`. The exporter now
requires exactly one `Kthread: 0` or `Kthread: 1` record from each process's
status. Only an explicitly identified kernel thread omits the executable-link
lookup. Every task still undergoes the command and descriptor checks. Missing
or malformed type information and userspace executable errors remain refusals.
The seven new scan cases cover valid kernel/user tasks, the failing magic-link
model, a kernel-thread input descriptor, and missing, duplicate or invalid type
records. They execute the generated scan block rather than a rewritten model.

Local validation: 13 monitor tests and eight disconnect tests passed. The
separately delivered ARM64 monitor/probe must be rebuilt and validated on
Buildbox before a new admission. The kernel, initramfs and installed boot2 image
are unchanged. The previous package cannot validate the changed monitor source.
