# Clock-backend entry ledger

## Status

The predecessor probe/gate candidate produced an exact changed-cycle
`neither`: neither observer record survived and neither protected transport
was reached. The linked initcall order is clock backend, BigiDVFS backend, then
observer. This non-identical, zero-protected-call successor is in generation.

## Question

Does the exact serviceability kernel reach clock-backend driver registration
and the first operation of its probe when only that backend DT node is enabled?

## Hypothesis and unique evidence

The candidate keeps the exact kernel baseline, serviceability initramfs,
Gemini base DT, ramoops reservation, eight-A53 policy, two-write ceiling, and
all CPU/owner closures. Its derivative DT enables only the protected-clock
backend. It does not instantiate the observer, leaves the BigiDVFS backend
disabled, and makes zero protected calls.

Two fixed records reuse retained slots 173 and 174:

1. `driver-init`, immediately before clock-backend platform-driver
   registration;
2. `probe-enter`, as the first clock-backend probe operation.

Both use the exact Gemini compatibility, exact ramoops reservation and size,
`ramoops` compatibility, `no-map`, exact prefix, empty-slot, payload-before-
metadata, and full-readback gates. There is no clear, overwrite, or retry.

## Decision table

| Recovered evidence | Interpretation | Decision-changing next action |
| --- | --- | --- |
| neither | Clock driver init was not reached, or the shared safety/mapping/write path refused | Move to the last proven earlier init stage or split the shared safety predicates |
| `driver-init` only | Registration began, but matching/probe entry was not established | Audit platform-device population, registration return, and exact compatible matching |
| `driver-init` + `probe-enter`, no serviceable runtime | Clock probe began; failure is at or after its first operation | Split allocation, resource mapping, and clock acquisition without adding a protected read |
| both records plus exact serviceable runtime | Read-free clock-backend probe completed | Close this prerequisite and isolate BigiDVFS probe separately |
| malformed, duplicate, or foreign record | Attribution failed | Reject without boundary inference |

## Safety and build contract

- At most two short writes target only the same otherwise-unused retained-RAM
  zones under the standing diagnostic authorization.
- There is no protected read, secure call, MMIO read/write, clock enable,
  storage operation, CPU request, owner registration, retry, reset, reboot, or
  power operation in the new runtime path.
- The clock probe retains only its existing allocation, resource-map, clock-
  handle, lock-init, and driver-data operations.
- Patch generation and compilation run only on Buildbox from a clean pushed
  commit and the integrity-verified managed source through canonical `0324`.
- The generated patch uses a synthetic, non-certifying experiment author with
  no DCO sign-off and is not submission-ready.

## Next action

Generate, review, and canonically admit one patch and isolated profile. Then
build and independently validate an exact Android-v0/16 MiB candidate before
any device action. Repository-wide ordering remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
