# MT6797 A72 physical-source observer design

## Production lifetime

The platform probe obtains and retains bound device references in this order:

1. A72 platform-state source;
2. protected-clock backend; and
3. BigiDVFS backend.

DA921x remains behind its separate provider registry. With all three device
references held, the observer registers one exact callback/context pair, calls
`mt6797_a72_direct_state_snapshot()` exactly once, and unregisters that exact
pair before releasing BigiDVFS, clock, and platform references in reverse
order. Every deferral and error releases the references already acquired.

## Callback order

The public direct compositor supplies the outer CPU-hotplug read lock, A72
transition mutex, and direct-registry mutex. The callback then performs exactly
these six stages, without a loop or retry:

1. `mt6797_a72_platform_state_snapshot()`;
2. `mt6797_a72_provider_snapshot()`;
3. `mt6797_dvfsp_clock_backend_read()`;
4. retained checkpoint 0, `before-bigidvfs` in record 1;
5. `mt6797_bigidvfs_backend_read()` once; and
6. retained checkpoint 1, `after-bigidvfs` in record 2.

The callback clears its destination on entry and every error. It sets direct
source ABI 1 and `valid=1` only after stage 6. The outer compositor performs
its final pristine-owner comparison before publishing direct ABI 2.

## Retained protocol

The mode uses token `GPSQ-20260824-A` and only first-dmesg records 1 and 2. It
reuses the existing qualified writer: both raw headers must be all ones before
the first write; payload, start, size, and signature are committed in order;
the signature is last; barriers order the commit; and a full local readback is
mandatory. There is no overwrite, clear, retry, or third write.

## Hardware-free proof

The focused KUnit suite replaces all five readers, the checkpoint callback,
and the three direct-runtime operations with in-memory fakes. Four cases cover:

1. the exact six-stage success order and final validity;
2. each of the six failure boundaries with an all-zero result;
3. one register, one snapshot, one exact unregister; and
4. register and snapshot failures, including unregister-after-snapshot-error.

QEMU has no Gemini DT nodes and no network. The profile leaves the positive
DA921x provider transaction, firmware-writer window, publisher, A34 evaluator,
and CPU request paths unselected.

## Decision boundary

Passing source generation, canonical replay, Buildbox compile, and all four
KUnit cases permits construction of one guarded device candidate. It is not a
hardware-support claim. Any failed stage remains all-zero and rejects the
candidate; no second device attempt is allowed without a changed hypothesis or
new independent observation path.
