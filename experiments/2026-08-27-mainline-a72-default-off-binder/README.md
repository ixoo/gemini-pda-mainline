# Mainline CPU8 complete default-off binder

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-default-off-binder` |
| Status | exact interface audit complete; binder contract frozen; implementation pending |
| Subsystem | CPU8 admission, transition owners, PSCI, and generic hotplug lifecycle |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-27 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, complete default-off physical binder |

## Question or hypothesis

Can the proven executor, recovery watchdog, retained ledger, platform-effect
owner, DA921x provider, SRAM owner, MT6797 admission, and lifecycle callbacks
be joined without duplicating ownership or allowing an unrecorded physical
effect?

## Provenance and environment

- Parent repository commit:
  `010fe5781bd18f21a23c91476389fa6e80343570`.
- Canonical series: 384 entries through `0395`.
- Canonical series SHA-256:
  `739dac63e4db1ca606df8cb7518351078a742368787443e93e8dc5d18055c4f9`.
- Manifest SHA-256:
  `57169050ce518a74b1ff04d87ebbe17794fa4684536472f6a5a1aa5c20c20c19`.
- Exact Buildbox prepared-source state:
  `9d03c2ebbde4792b9db0a136c4a12e95c4343e47fb283f413a4acd7fd6f311c0`.
- Build backend for later implementation: Buildbox only.
- Boot path and target partition: none in this phase.

Exact source identities and bounded interface findings are recorded in the
[source interface map](results/source-interface-map-20260827.txt).

## Safety assessment

This phase was a read-only audit of the exact Buildbox source. It performed no
build, MMIO, retained-RAM write, watchdog takeover, regulator or secure call,
PSCI request, CPU operation, device access, boot-image construction, partition
write, reboot, or shutdown.

The MT6797 CPU-boot callback still returns `-EAGAIN`; both lifecycle callbacks
remain unset; the membership owner still refuses admission; there is no binder
arm caller or binder Device Tree node; and no boot candidate is selected.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the repair, ownership, admission, device
  lifetime, lifecycle, and test boundaries.
- [`contract.json`](contract.json) records the exact machine-readable audit and
  selected implementation order.
- [`scripts/validate.py`](scripts/validate.py) validates the frozen record.

## Audit result

Direct glue is rejected. The individual owners are sound, but five boundary
repairs are required before they can safely form a physical path:

1. make regular executor checkpoints fallible and require a terminal retained
   commit, so a ledger error cannot be ignored before a hardware effect;
2. admit only one membership-owned CPU8 token instead of trusting caller
   Booleans, while keeping CPU9 and every unarmed request closed;
3. hold immutable references to the watchdog, platform-state, and BigiDVFS
   supplier devices, resolved by an unarmed default-off binder device;
4. expose a narrow binder API so arm64 does not depend on the executor's
   driver-private header; and
5. terminalize the binder before the existing P32 rollback publisher on a
   generic CPU-up failure.

The current executor and watchdog constants both specify 15000 ms. The
watchdog identity remains evidence only; the ledger, platform, provider, SRAM,
membership, and lifecycle records must share one exact generation/cookie pair.

## Selected implementation

Generate two logical patches from this contract:

1. repair the executor's retained-checkpoint contract and test every new
   failure boundary; and
2. add the default-off binder, typed physical adapters, MT6797 lifecycle
   handoffs, focused injected KUnit tests, and a hardware-free profile.

The binder proof adds no late CPU caller and no enabled binder DT node. Its
static validator and sole bounded no-network QEMU run must demonstrate zero
physical calls, zero production CPU requests, zero CPU_OFF, and zero retries.
Only after that proof may a separate device-candidate change add one exact late
caller and one enabled binder node.

## Follow-up

The authoritative ordered next step is
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment
constrains that work to the two hardware-free patches above; it does not admit
a device candidate.
