# DA921x provider-state export design

## Returned record

The record is deliberately raw and narrow: ABI, valid bit, CONTROL_A,
STATUS_B, BUCKB_CONT, VBUCKB_A, VBUCKB_B, and a zero reserved field. It does not classify rail ownership or infer transition eligibility. The later
transition owner must combine it with the platform-state source and its own
complete owner tuple.

## Registry boundary

The snapshot operation is optional because existing synthetic providers prove
acquire/release behavior without a physical-state reader. The dispatcher
clears the destination before registry lookup, holds the existing registry
mutex across the callback, validates the complete returned record, and copies
it only on success. No provider, no callback, malformed output, and callback
failure are distinct fail-closed returns with an all-zero destination.

## DA921x acquisition

The production callback takes the endpoint mutex and then one root-adapter
lock. With retries forced to zero, it executes two five-register scans through
the existing transport helper. It does not loop, sleep, write, retry, or touch
PAGE_CON. A mismatch is transient `-EAGAIN`, not a guessed state. The callback
uses local accounting objects so the provider lifecycle and its retained fault
state cannot be changed by observation.

## Preserved closures

This source adds no consumer, sysfs interface, device-tree enable, A34 caller,
lifecycle opener, hotplug hook, PSCI call, CPU_ON, CPU_OFF, boot candidate, or
device action. It cannot by itself make CPU8 eligible.
