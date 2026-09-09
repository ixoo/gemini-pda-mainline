# One-request responder prototype

[respond-once.py](respond-once.py) implements the metadata/command participant
using Python 3.7 or later and standard libraries. It is an offline-tested
prototype, not an admitted device program. Userspace packaging and the
controller/capture/recovery protocol remain unfinished.

The program accepts an inherited descriptor and verifies its character-device
identity through sysfs as `stpwmt`. It requires the reviewed Linux 64-bit
little-endian ioctl layout. It does not open a WMT device or configure HIF,
request power, load WLAN, stop services or perform recovery.

Before announcing readiness, it requires a read-only firmware filesystem and
uses the [retained-file checker](check-retained-patches.py) to verify both exact
files and their ordered metadata. A read-only view is not proof that another
mount or actor cannot replace underlying files, or that firmware lookup will
select this directory. The controller must freeze the complete lookup layout
and exclude other command consumers and firmware providers.

One poll and one complete bounded read must yield exactly `srh_patch`.
The program compares the queried chip and full cached firmware version with
explicit controller inputs, publishes the count followed by two 264-byte
records, checks each ioctl result and writes exactly `ok` once. Unknown
commands, unexpected poll events, identity mismatches and publication failures
end the participant without an acknowledgement. Short writes are not retried.
Failure can follow partial metadata publication or a reply write; it does not
mean that no effects occurred. Descriptor close is not shutdown.

The absolute monotonic deadline has at most 1500 ms remaining at readiness.
The future controller must anchor it before its single WLAN-on request and
prove there is no older pending command. Checks occur between operations; the
program cannot prevent descheduling or a blocking syscall from crossing the
deadline. The test explicitly demonstrates a reply completing after expiry:
the participant reports failure, but the write has already happened. Therefore
this prototype does **not** yet satisfy the no-late-reply admission contract.
A kernel-side acceptance/expiry safeguard or an equally attributable protocol
is still required; a userspace timer is not a substitute. A successful return
only says `reply-written`, with kernel acceptance explicitly left to capture.

The inspected timeout path in `wmt_ctrl_ul_cmd()` returns before the selected
SoC patch-download loop. The metadata-free helper is reached by the final-patch
free operation, not by that timeout branch. This inspection did not establish
the suspected timeout/free race. It also supplies no general concurrency or
future-request safety proof. The existing single-attempt patch removes one
internal retry source; the controller must still exclude other actors.

[Twelve mocked-transport tests](test-respond-once.py) pass: exact record layout
and order, command rejection, expiry, poll failure, chip/version mismatch,
publication errors (including the second record), and short/late writes.
They execute no device read, ioctl or write. The checker refactor also passed
against both private retained files in the RE VM. No firmware is redistributed.
The [kernel startup patches](OPENMTTOOLS.md#complete-source-file-compilation)
retain their separate compilation evidence; this prototype adds no kernel ABI
or upstream support claim.
