# REG06 transport and completion review

Successor to the [access review](REG06_ACCESS_REVIEW.md). The
[receipt](results/charger-transport-review.json) pins six instruction spans in
the same retained matched boot kernel and three prepared source files. This
review changes the observer design; it adds no implementation or device action.

## Short request and retry budget

The selected vendor controller is `i2c-mtk.c`, not generic `i2c-mt65xx.c`.
Its active source branch combines the helper's same-address one-byte pointer
write and one-byte read into one WRRD transaction. The hardware routine selects
FIFO when both lengths are at most eight. The comment saying “always use DMA”
is stale for this case: the coherent DMA allocation serves as a staging buffer,
but the short successful path does not start the DMA engine. Controller clocks,
including the DMA clock, are still managed by the normal master path.

The matched probe installs timeout 200 jiffies and retries 1. The retained
configuration has HZ=100. The core repeats only `-EAGAIN`, allowing at most two
master calls under that setup. The selected master returns its message count
or `-EBUSY`, `-EINVAL`, `-ETIMEDOUT`, or `-EREMOTEIO`; those errors do not trigger
that core retry. Atomic adapter-lock refusal can return `-EAGAIN` before any
master call, but a normal driver observation is sleeping-context work.

The hardware wait uses the adapter timeout. This is not a two-second total
operation deadline: charger mutex, adapter rt_mutex, controller mutex, clocks,
and hardware-semaphore helpers sit outside that wait. For bus IDs zero and one,
the outer SCP acquisition loop can call its helper 101 times, not 100: the
helper is evaluated before the remaining-count condition. Its nested cost and
the actual charger adapter/resource flags need review before admission.

## A successful helper return is insufficient

After an IRQ without the checked ACK/NACK errors, the short receive path extracts
the four-bit FIFO byte count and drains exactly that many bytes. It does not
compare the count with the requested length. Zero count skips the drain; the
master can still return two and the charger helper can report success. The
staging byte may then retain the pointer value `0x06` copied for the write phase.
This is a reachable control-flow case, not an observed device malfunction.

The IRQ handler also sets the stop flag after recording interrupt status. The
normal return path checks error bits but does not explicitly require the
transaction-complete bit. Thus a local byte plus helper return fixes sysfs-cache
ownership but does not establish the desired physical completion evidence.

The successor needs same-operation completion status and FIFO count, captured
while the controller owns that exact request. Accept a REG06 value only with
one received byte, completion set, no ACK/NACK error, the expected FIFO/WRRD
path and successful helper return. Do not obtain this evidence by a second
register read or a later unlocked snapshot. Keep instrumentation default-off
and scoped to the observer; do not change unrelated charger policy or global
adapter retry settings.

## Failure effects and remaining admission

Both wait timeout and ACK error invoke controller reinitialization: I2C soft
reset, I/O/timing reprogramming and DMA warm reset. After a five-microsecond wait,
nonzero DMA enable state reaches a kernel BUG. Conditional AP power-management
semaphore exhaustion has a separate BUG path. FIFO success does not remove
these DMA/reset effects from the admitted failure envelope.

Next resolve the bound charger adapter and nested semaphore behavior, then
prepare the observer's result ownership, consumed entry, refusal and failure
cases. Review its transport/reset effects explicitly before a clean pushed
Buildbox compile and candidate admission. No charger read, new boot, kernel
build or installation occurred in this audit. Latched REG06 remains unknown.

## Verification

All instruction words across the six spans match the pinned Image; the complete
ELF kernel section equals that Image. Source revision and file hashes are pinned
separately, and configuration establishes HZ. Public output contains independently
described facts and hashes only. Binary analysis ran in the RE VM; raw source,
disassembly and firmware remain private. These checks establish the examined
implementation, not live binding, hardware behavior or successful recovery.
