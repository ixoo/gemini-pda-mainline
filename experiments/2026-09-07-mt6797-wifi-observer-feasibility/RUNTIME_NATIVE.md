# Native Gemian runtime compatibility check

Hypothesis: the [packaged ARM64 runtime](RUNTIME.md) can execute the controller's
userspace dependencies and mocked process protocol on Gemian's Linux 3.18.41+.
The distinguishing observation is native execution on that kernel, which the
Buildbox QEMU check cannot supply. This is not the connectivity observation boot.

Use the verified `runtime.tar.gz` with SHA-256
`7ff2ebf4153d8055f92f3baa1c550a3376b913e680162de60a3557ca2d855294`.
The [smoke body](native-runtime-smoke.sh) also runs the unchanged seven
controller and twelve responder tests already pinned by the
[runtime receipt](results/runtime-package.json). Their real system calls cover
fork, pipes, poll, socket pairs and child reaping. All WMT requests, device
opens and firmware preparation in those fixtures are mocked.

## Bounded execution

First verify the known-good Gemian model, OS, kernel, boot identity, execution
account and available tools. Require at least 512 MiB available memory and
160 MiB free in the existing executable `/dev/shm` tmpfs. Create one private
mode-0700 directory there; verify transferred checksums before extracting the
runtime as the ordinary account. Include only the archive, the two fixtures
and the smoke body. No package installation or maintainer script runs.

The host's existing `timeout`, `nice`, `taskset` and `chroot` launch the test:
20 seconds total, a two-second termination grace, nice level 19, CPU0 affinity,
and the ordinary account's numeric UID/GID with no supplementary groups.
Privilege is dropped before the packaged BusyBox shell or Python executes.
The smoke body additionally limits CPU time to six seconds per process,
virtual memory to 256 MiB, open files to 64, and core dumps to zero.

The temporary root has no device nodes, firmware, `/dev`, `/proc`, `/sys`,
`/run` or `/init`. The launch checks absence of device nodes. The smoke body
checks the absent virtual/device paths, non-root identity, empty supplementary
groups, CPU0 affinity, ARM64/64-bit little-endian
ABI, selected kernel release, SHA-256 and a progressing monotonic clock before
running the two fixture programs. No connectivity ioctl reaches hardware.
No service stop, radio request, CPU hotplug/policy change, watchdog operation,
partition write, reboot or boot selection is part of this check.

Retain output and status in the private RAM directory, retrieve them before
cleanup, and verify the same boot identity afterward. Remove only that uniquely
created directory once its evidence is preserved. A lost connection leaves
its evidence for retrieval; it does not authorize restart or another test.

## Decision branches

A pass establishes this native userspace execution scope. Minimal startup,
firmware lookup layout, capture preparation, kernel actor/reset isolation and
exact radio/timed-recovery admission remain outstanding. A failure preserves
its actual stage and output; diagnose the runtime, test or launch failure
before changing inputs or repeating. An unchanged artifact is not repeated
merely to obtain a pass.

## Observed result, 2026-09-10

The [native receipt](results/runtime-native.json) records a pass: Python 3.11.2
executed without an emulator, all ABI/hash/clock/privilege/affinity/isolation
checks passed, and the seven controller plus twelve responder tests passed.
The complete test invocation took six seconds by the host integer-second clock.
Its exit status was zero, with the same known-good Gemian boot identity before
testing, afterward and after cleanup. The exact test log was retrieved and its
SHA-256 verified before the temporary RAM directory was removed.

This resolves native execution of the scoped userspace operations on the
observed Linux 3.18.41+ baseline. It does not establish the experimental kernel
ABI, actual connectivity behavior, firmware execution or recovery timing.
