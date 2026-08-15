# Read-only transition-owner registration design

## Goal

Publish exactly one authoritative MT6797 state owner only when the existing
vendor lifecycle and the existing calibrated mainline source describe the same
immutable observation. This is a state-reporting boundary, not a voltage or
frequency control path.

## Ordered prerequisites

1. Preserve the 64-bit table epoch end to end. A source epoch must never be
   silently narrowed to 32 bits.
2. Preserve `owner_handle`, `transition_handle`, and the complete provenance
   object in the assembled state snapshot.
3. Require the vendor provider bridge to call `read_provenance()` for the exact
   sampled source and cross-check its variant, epoch, calibration handle,
   generation, owner handle, and transition handle against the source snapshot
   and identity.

Every prerequisite is a separate logical patch.

## Registration gate

A later registration entry point may proceed only when:

- the vendor lifecycle is bound and its mainline writer owner is registered;
- the vendor provider bridge returns a complete, provenance-validated review
  snapshot;
- the calibrated provider returns and revalidates one complete state snapshot;
- the calibrated owner identity is valid;
- generation, owner handle, transition handle, variant, table epoch, and
  calibration handle match across all views;
- the handoff registry is empty and the arbitration object has no active hold
  or latched fault.

Any failure returns without registering. Teardown must unregister the state
owner before writer removal, source invalidation, provider exit, or resource
owner detach.

## Explicit non-goals

- no regulator or clock setter;
- no DA921x register-data write;
- no I2C6 firmware-lease implementation;
- no PCM image start or firmware request;
- no CPU hotplug, CPU_ON, CPU_OFF, or CPU8/CPU9 admission;
- no platform-driver auto-registration;
- no Device Tree default enablement;
- no device boot in this compile-review phase.
