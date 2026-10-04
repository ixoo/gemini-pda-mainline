# REG06 adapter ownership and passive successor

The [receipt](results/charger-adapter-review.json) combines bounded static
Gemian metadata with two matched retained-binary semaphore spans. It advances
[transport review](REG06_TRANSPORT_REVIEW.md); no charger transaction was added.

## Static live mapping

On unchanged Gemian boot `c52cec49-a635-45c3-af32-aba3b95b4c1c`, release
`3.18.41+`, client `0-006b` names `sw_charger` and binds `bq25890`. Its uevent
maps to `/soc/i2c@11007000/sw_charger@6b`; the resolved sysfs parent agrees.
Adapter name is `mt-i2c`. The live controller DT supplies ID zero, 400 kHz,
clock divisor ten, main/DMA clocks, I2C range `0x11007000/0x1000` and DMA range
`0x11000100/0x80`. AP/GPU power-management, PMIC, DCM, push-pull and buffer-mode
flags are absent. These are static inputs, not a direct read of controller fields.

The first packet refused on the absent client `of_node` link after identity and
binding checks; its stdout was empty. A revised packet used the reviewed uevent
mapping and exact proc-DT node, checked binding/uevent again, and completed in
0.551 seconds with no stderr. Both private packets are retained with hashes.
Neither packet accessed charger registers, MMIO, power telemetry or boot storage.

## SCP effects and failure ownership

With SCP support enabled, adapter ID zero invokes semaphore flag two, selecting
bit five. The matched acquisition helper first reads that bit; if clear, it
writes the bit and executes at most 5,000 read/test/write iterations. One helper
call therefore has a conservative maximum of 5,001 reads and 5,001 writes to
the SCP semaphore register. The outer controller loop can call it 101 times,
yielding at most 505,101 acquisition reads and writes. Release adds at most two
reads and one write. These finite counts do not establish elapsed-time bounds.

There are two failure-attribution gaps. The last helper write has no subsequent
readback before failure, so failure alone does not prove the bit remains clear.
Also, the outer loop calls acquisition when its counter is already zero: if
that final call acquires, the outer return still reports failure and the master
returns before release. This is a control-flow finding, not an observed device
failure. Do not infer successful cleanup from `-EBUSY` or retry a failed
observation to repair ownership.

## Selected implementation

The matched CV configuration path already reads REG06 before its fixed write,
and the existing session log establishes recurring setter calls. Capture one
of those existing bound-driver reads after an explicit diagnostic arm. This
replaces the proposal to submit an additional observation request; it preserves
the requirement for an attributable REG06 byte at one instant.

Keep the hook default-off. Consume one arm before the matching driver request;
associate its exact message pointer with controller metadata while ownership
is held, and retain one terminal result. Accept a value only when the request
shape and controller identity match, the path is FIFO/WRRD, completion is set,
ACK/NACK is absent, FIFO count is exactly one and the helper reports success.
Suppress the value for every other outcome. A later unlocked controller
snapshot is insufficient. Do not add an I2C request, alter policy writes,
retry settings or the inherited semaphore/reset path, or rearm in the same boot.

This observation describes the register before that policy update's write.
It does not prove the following write succeeded, continuous CV behavior, cell
chemistry or safe charging. C2a's full register map remains a separate gate.

Next implement the small driver/controller hook and verify result ownership,
refusal, error and short-FIFO cases before Buildbox compilation and candidate
admission. Its admission must distinguish diagnostic-added effects from the
inherited normal policy traffic. There is no executable or boot candidate yet.
