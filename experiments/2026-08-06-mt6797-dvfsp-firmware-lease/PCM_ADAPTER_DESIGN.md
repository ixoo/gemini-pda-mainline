# Bounded PCM adapter admission design

This is the next source-only gate after the dormant state-owner contract in
patch `0192`. It defines the admission and failure ordering a future mainline
PCM owner must satisfy. It does not select or copy a firmware image, map
CSPM/CSRAM, register a callback, write hardware, or authorize a device boot.

## Preconditions

The adapter cannot become live until all of these independent authorities are
identified and lifetime-managed:

- an exact image identity (SHA-256, target revision, loader domain, physical
  address/length, alignment, cache maintenance, and lifetime);
- the `0192` startup-state owner, with all required cluster fields and a
  nonzero generation sampled under its transition lock;
- one owner for CSPM `0x11015000 + 0x1000`, CSRAM
  `0x0012a000 + 0x3000`, the `INFRA_I2C_APPM` clock, and the protected
  semaphore/EMI boundary; and
- a bounded runtime owner implementing the existing three-word
  `SW_PAUSE`/`FW_DONE` lease contract.

The Linux transfer generation/cookie is not a substitute for the startup-state
generation or firmware owner handle. Each identity must remain separately
bound until the transaction is terminal.

## Admission lifecycle

The only legal forward path is:

```text
UNAVAILABLE
  -> SNAPSHOTTED
  -> RESOURCES_HELD
  -> IMAGE_READY
  -> RESET_INITIALIZED
  -> IMAGE_ACKED
  -> CONTROL_INITIALIZED
  -> RUNNING
  -> LEASE_REGISTERED
```

`SNAPSHOTTED` requires a complete state snapshot for every cluster required by
the start contract. `RESOURCES_HELD` requires one attributable owner for both
memory windows and the clock/semaphore lifetime. `IMAGE_READY` requires the
exact image identity and stable residency. The reset, instruction-memory
acknowledgement, control/CSRAM initialization, and PCM kick are separate
checkpoints so a failure cannot be mistaken for a running owner.

Immediately before each irreversible-looking checkpoint (`IMAGE_KICK`,
`PCM_KICK`, and callback registration), the adapter must revalidate the state
generation and exact image/resource identity. Any mismatch enters `INVALIDATED`
and releases only resources whose ownership is independently confirmed.

`LEASE_REGISTERED` is unreachable until PCM run is acknowledged and the
generation is bound to the runtime owner. A callback cannot be registered from
an image-ready, stopped, or merely observed CSPM state.

## Failure and power-management rules

Every active phase may enter `INVALIDATED` for owner removal, clock/rail
transition, suspend/resume, or a PCM fault. A post-kick uncertainty enters
sticky `FAULTED` rather than guessing an inverse or retrying an unbounded wait.
The start acknowledgement and `SW_PAUSE`/`FW_DONE` lease each have bounded
timeouts; a timeout is a terminal failure for that generation.

Suspend, resume, clock loss, or rail transition invalidates the generation
before a stale callback can reach the firmware owner. Release requires the
same image generation, state generation, Linux transfer token, and opaque
firmware owner handle. A mismatched token is rejected without a hardware
operation.

## Model coverage

`scripts/pcm_adapter_oracle.py` is a deterministic model of this boundary. It
checks the successful ordering and rejects incomplete state, wrong resource
identity, unbound images, premature callback registration, stale generations,
and invalidation during start or lease use. The model is evidence for the
ordering contract only; it is not a substitute for a real protected owner or
hardware validation.

Exit from this gate requires a reviewed implementation of the same lifecycle,
not merely a passing compile. Until then the provider remains fail-closed and
CPU8/CPU9 remain disconnected.
