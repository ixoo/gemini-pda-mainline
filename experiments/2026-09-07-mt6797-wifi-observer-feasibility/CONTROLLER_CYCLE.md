# Recorded single-cycle controller

The unselected [kernel patch](patches/controller-cycle/0001-wmt-gate-the-captured-controller-cycle-on-recorded-c.patch)
and [userspace controller](cycle-controller.py) connect initialization, fixed
transport setup, one responder and a WLAN ON/OFF pair. The controller has no
standalone run command; an admitted minimal-startup candidate must supply its
verified inputs and invoke it. No such candidate exists yet and this code has
not run on the PDA.

## Sequence and failure behavior

`run_cycle()` checks the selected kernel release, ARM64/64-bit little-endian
ABI, single-threaded Python caller, detector descriptor and current boot ID.
It then requires the read-only detector query `COMBO_IOCTL_CAPTURE_ABI`,
`_IO('w', 10)` (`0x770a`), to return protocol version `0x57464301`. This query
does not initialize drivers, consume the recovery attempt or write capture.
The original detector returns zero for unknown commands, so zero is explicitly
refused before initialization rather than mistaken for the new interface.
The query identifies this disposable interface, not complete build provenance.
The controller verifies the two retained common-patch files on a read-only filesystem
before takeover. Its 96-byte input is cycle ID (16), candidate SHA-256 (32),
boot UUID (16, canonical UUID byte order), and input-manifest SHA-256 (32).
Release/identity comparisons are checks against caller inputs, not kernel
attestation or proof of complete filesystem provenance.

The caller remains responsible for authenticating the candidate and complete
input manifest, freezing every common/WLAN firmware lookup and configuration
file, excluding alternate providers and consumers, and establishing capture
storage and recovery admission. Checking two files does not satisfy those
broader prerequisites. The existing live Gemian system is not this startup
environment.

The software deadline starts before `COMBO_IOCTL_CAPTURE_INIT` and allows no
more than twelve seconds. That request performs the existing recorded
capture/recovery takeover and initializer chain. Only a zero result allows
opening and identifying `stpwmt`, then configuring scalar `0x23` through
`WMT_IOCTL_SET_STP_MODE`. Initialization/configuration errors end normal work.
The watchdog remains armed, including after successful completion.

The controller polls for an older pending command without consuming it and
refuses one. It forks exactly one responder using the already checked patch
metadata. The child signals readiness through a private pipe and runs the
existing one-command responder. Its reply deadline is at most 1500 ms from
before the fork, capped by the original total deadline. The parent requires
readiness and a live child before requesting ON. This does not guarantee that
the child cannot subsequently fail or be descheduled; the kernel reply guard
and failure checks remain necessary.

ON and OFF execute on the same parent task, with the fixed scalar arguments
`0x80000003` and `3`. After successful ON, the parent requires the child's
successful reply report and reaps that exact child with a zero exit status.
Only then does it issue OFF. Thus descriptor closure or a readiness message
cannot substitute for responder completion. Every reported failure or expired
deadline prevents the next normal request. Failure cleanup only closes local
descriptors and nonblockingly reaps an already exited child; it never kills,
replaces, retries, disarms or restarts. A stalled operation or child remains
subject to the original hardware cutoff. Software checks do not bound blocking
syscalls or cancel kernel workers.

## Native gates and records

Under `CONFIG_MTK_A72_RECOVERY_DISCRIMINATOR`, transport setup requires active
capture, consumes one atomic attempt and accepts only full-width argument
`0x23` with no earlier HIF readiness. Entry recording must succeed before
changing transport state. Configuration and recording errors fail capture.
The prior four-second worker wait remains unchanged.

Kind 13, transaction zero, has three little-endian 32-bit fields: stage
(1 entry, 2 return), fixed argument `0x23`, and signed native result. Entry
result is zero. The two records add 256 bytes after the complete initializer
prefix. The native writer and host writer both accept the new kind.

The existing request entry/return observers now return their acceptance result.
Ordinary builds ignore it and retain their native request behavior. The
experimental ioctl refuses a function call before effects unless transport is
ready, capture is active, and the request observer accepts its exact argument,
task and stage. Its returned success also requires accepted request completion.
The existing firmware/request witness therefore rejects ON's successful
no-load shortcut, missing image completion, reset invalidation, lost records
and failed worker/waiter attribution. These checks do not suppress independent
native reset paths or all other WMT controls; actor/resource isolation remains
a candidate prerequisite.

After accepted OFF completion, the ioctl writes producer terminal 1 and checks
that write's result. This uses the existing reserved terminal slot and adds no
new recovery operation. Failed or incomplete captures cannot return controller
success merely because the native function returned zero.

## Recovered classification and tests

`check_controller_cycle()` in the [decoder](capture-records.py) requires the
independently expected cycle/candidate/boot/input identity, exact raw-zone
header and clean unused tail, successful recovery/initializer/transport prefix,
and a complete terminal immediately after successful OFF. It composes the
existing request, firmware-read/image, eight payload/DMA, EMI, ordinary-stop
and removal-wait checks. The removal waits must lie inside the OFF worker
interval. The result describes recorded observations; it does not establish
firmware execution, buffer immutability, task quiescence or reset/resource
isolation.

The [native fixture](test-controller-cycle.py) executes the detector query,
both WMT ioctl cases, the request observer and slot writer with injected
worker/firmware events.
It covers wrong order/task/arguments, setup failures, successful ON without an
image, reset/timeout/error results and all 22 lost records in its scoped stream.
It does not execute actual initializers, queues, firmware or hardware.
The [process tests](test-cycle-controller.py) use real fork/pipe/exit/wait
operations with socket-backed fake WMT calls. OFF verifies that the exact child
has already been reaped; ON, responder, exit and OFF failures have no retry.
Startup tests separately verify preparation before takeover and failure ordering.
The twelve existing responder tests also pass.

The [classifier tests](test-controller-classifier.py) construct a synthetic
complete stream and reject every missing/repeated record, misplaced removal
waits, failed/misordered transport, incomplete terminals and a rejected-access
tail. Synthetic completeness is not native execution evidence. The existing
23 decoder and nine writer tests pass. The six-file patch replays/reverses
exactly and passes strict Checkpatch with the existing archive exceptions.

The [source receipt](results/controller-cycle-sources.json) pins all six
parents/outputs. The existing Buildbox checker accepts `COMMIT --controller-cycle`:
it composes the 31-patch DMA-map-error source, two transport patches, historical
low-level recovery ownership, setter correction, recovery gate, controller
initialization and this patch, then targets complete detector, WMT-device,
WMT-library and ramoops objects. Complete kernel linking, minimal filesystem packaging,
capture zero-state preparation, remaining isolation and an exact owner-approved
radio/timed-recovery session are still required before device validation.
