# DA921x read-only observer design

## Runtime record

An isolated `REGULATOR_DA9213_LEGACY_OBSERVER` option depends on the existing
resource-only provider and is disabled by default. After the fixed identity
transcript and both descriptor registrations succeed, it invokes the same
`get_voltage_sel`, `list_voltage`, and `is_enabled` operations that the
provider exposes and emits one `da921x-observer-v1` record containing:

- 14 completed identity reads;
- two registered descriptors;
- four attempted and four completed provider state reads;
- selector, derived microvolts, and enable state for Buck 0 and Buck 1; and
- zero register-data writes.

The first message of each existing combined I2C read writes only the register
pointer. `register_data_writes` means a transfer carrying a register value to
change device state; the driver has no such transfer or helper.

## Failure and lifecycle

The observation is valid only after all four state reads succeed. Any negative
operation result, out-of-range selector, non-Boolean enable result, incomplete
identity count, or incomplete provider count rejects the observation and fails
probe. It never publishes a partial record.

The observer registers one devres cleanup action before either provider. The
later regulator devres entries therefore release first. The final action
invalidates the observation and reports whether it is cleaning a failed probe
or a normally bound device. It performs no inverse hardware operation because
the observer never changes hardware state.

## Hardware-free tests

A separate KUnit object uses only a fake semantic-read callback. It covers:

1. the exact successful two-buck record;
2. failure at each of the four read positions with bounded attempt/completion
   counts and no partial validity;
3. rejection before any read when identity or provider counts are incomplete;
4. rejection of invalid semantic values; and
5. observation invalidation and provider-count clearing during cleanup.

## Non-goals

- no regulator setter, consumer, constraints, or supply relationship;
- no page selector, write/readback, vote, rollback, or transition owner;
- no DVFSP, clock, firmware, PSCI, CPU hotplug, or CPU8/CPU9 action;
- no claim about rail ownership or resume behavior.
