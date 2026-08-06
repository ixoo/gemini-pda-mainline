# Mainline I2C6/DVFSP transfer-lease contract

## Purpose

This is the next source-only contract after the ready-gate audit. It closes
the race between the handoff's entry readiness predicate and the lifetime of
one I2C6 transfer. It does not authorize a DA921x register-data write, a
regulator vote, or a CPU request.

Patch `0174` implements this contract and passed the exact pushed Buildbox
compile/package validation. That result is compile evidence only; it does not
prove the vendor firmware semaphore or authorize device validation.

## Existing boundary

The selected profile connects Gemini I2C6 to `dvfsp_handoff`. The MT65xx
adapter checks `mt6797_dvfsp_handoff_require_ready()` before dispatch, and the
provider takes the root adapter lock before calling `__i2c_transfer()`. The
handoff changes permission during suspend/resume and faults on failed
revalidation, but the current readiness check is not held across the transfer
and no transfer generation/token exists.

## Required lease shape

The implementation must be a sleepable, platform-private lease, not a
userspace or regulator-consumer ABI:

1. `begin_i2c6_transfer()` takes the handoff transfer lock, checks both
   `state == READY` and `permission == READY`, rejects an already-active lease,
   increments a monotonic generation, and returns an opaque `{generation,
   cookie}` token while retaining the lock for the transfer lifetime.
2. `end_i2c6_transfer()` accepts only the exact active token, records the
   transfer result, clears the active lease, and releases the lock. A stale,
   missing, or duplicate token is a fault, not a best-effort unlock.
3. Suspend-late and resume-early take the same transfer lock around their
   permission transition and clock/revalidation work. Suspend must wait for an
   active transfer to finish before changing `READY` to `BLOCKED`; resume may
   publish `READY` only after the existing snapshot and clock checks pass.
4. Any handoff state change, PM fault, transfer timeout, or uncertain end
   state fails closed and retains/faults the owner. It must not synthesize a
   DA921x inverse or silently re-arm the token.
5. The lease must cover every I2C6 adapter transfer, including the provider's
   fixed read path, while preserving the existing root-adapter lock ordering.
   The contract must not claim that it implements the vendor `SEMA_I2C_DRV`
   semaphore; that remains a separate evidence requirement.

## Provider ordering

The eventual provider transaction is constrained to:

```text
root adapter lock -> I2C6/DVFSP lease begin -> bounded transaction
  -> complete readback/settle evidence -> lease end -> root adapter unlock
```

The current provider remains read-only and returns `-EOPNOTSUPP` for both
acquire and release. A future writable path cannot proceed from this document
alone: it still needs an attributable DA921x page owner, preserved control
mask, complete post-state readback, and a same-generation rollback owner.

## Rejection and exit criteria

Reject the implementation if it:

- checks only the atomic permission bit;
- releases the lock without matching the generation and cookie;
- lets suspend/resume race an active transfer;
- retries after a timeout or uncertain hardware result;
- adds a page selector or register-data write before the DA921x ownership
  audit closes; or
- claims hardware support from compilation alone.

The contract is implementation-eligible only after static lock-order review,
negative stale-token tests, a clean pushed Buildbox build, and an updated
experiment result. Device validation remains a later gate with CPU8 and CPU9
offline.
