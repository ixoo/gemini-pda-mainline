# Mainline CPU8 complete default-off binder

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-default-off-binder` |
| Status | QEMU exposed owner-test stack overflow; test-only repair generation pending |
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
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) admits only the validated
  binder profile package and runs one 45-second QEMU `virt` guest with no NIC.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires all 47
  membership, executor, and binder results plus the expected post-test rootfs
  panic boundary.
- [`scripts/generate-owner-stack-fix-on-buildbox`](scripts/generate-owner-stack-fix-on-buildbox)
  generates one test-only follow-up from the exact full-series source after the
  first runtime attempt exposed oversized membership-owner fixtures.

## Audit result

Direct glue is rejected. The individual owners are sound, but seven boundary
repairs are required before they can safely form a physical path:

1. make regular executor checkpoints fallible and require a terminal retained
   commit, so a ledger error cannot be ignored before a hardware effect;
2. admit only one membership-owned CPU8 token instead of trusting caller
   Booleans, while keeping CPU9 and every unarmed request closed;
3. hold immutable references to the watchdog, platform-state, and BigiDVFS
   supplier devices, resolved by an unarmed default-off binder device;
4. expose a narrow binder API so arm64 does not depend on the executor's
   driver-private header;
5. terminalize the binder before the existing P32 rollback publisher on a
   generic CPU-up failure; and
6. add one exact post-proof membership success publication, because the current
   owner never commits CPU8 membership outside bootstrap and test seeding.

The current executor and watchdog constants both specify 15000 ms. The
watchdog identity remains evidence only. Ledger, platform, SRAM, membership,
and lifecycle records share the membership transaction identity; the provider
lease has its own exact generation/cookie handle, linked by the owner proof.

## Selected implementation

Generate five logical patches from this contract:

1. repair the executor's retained-checkpoint contract and test every new
   failure boundary;
2. add membership-owned admission, CPU_ON consumption, publication,
   finalization, clean rejection, and four real-owner KUnit cases;
3. add the closed DT binding without a base DT node;
4. add the default-off binder, typed physical adapters, and MT6797 lifecycle
   handoffs; and
5. add five injected binder KUnit cases and the hardware-free profile.

The binder proof adds no late CPU caller and no enabled binder DT node. Its
static validator and sole bounded no-network QEMU run must demonstrate zero
physical calls, zero production CPU requests, zero CPU_OFF, and zero retries.
Only after that proof may a separate device-candidate change add one exact late
caller and one enabled binder node.

## Buildbox compile result

The exact repaired revision `0f5a1d709ee2ff8d103aa762d44e1e2ae4e6a080`
passed the `a72-default-off-binder-kunit` build and package validator on
buildbox. The realized configuration selects exactly the membership-owner,
executor, and binder KUnit options and keeps `HOTPLUG_SPLIT_STARTUP` disabled.
The new binder production and test objects compiled without a binder-specific
warning. The full log retains inherited diagnostics: 44 compiler-warning lines
in older membership/DVFSP sources, 12 `ranges_format` DTC warnings, and one
patch whitespace warning. Exact identities and the warning breakdown are in
the [compile evidence](results/buildbox-compile-0f5a1d70.txt).

The built package is intentionally not a boot candidate. It has no late CPU
caller and no binder DT node, and it has not been written to any device.

## First QEMU result

The first actual 45-second, no-network QEMU run reached the 30-case membership
owner suite, then exposed the compiler's inherited large-frame warnings as a
real arm64 kernel-stack defect. Seventeen cases faulted while clearing local
40--75 KiB fixtures, three small cases passed, and one further case failed only
after the preceding faults had corrupted shared owner state. The guest then
panicked with `Kernel panic - not syncing: kernel stack overflow` before the
remaining owner cases, executor suite, or binder suite could run.

The raw log remains a private ignored artifact; its sanitized identity and
classification are in the [runtime rejection evidence](results/kunit-qemu-stack-overflow-0f5a1d70-20260828.txt).
This is a test-only blocker, not evidence about the physical CPU8 path. The
next revision moves every large owner observation, transaction, and snapshot
into one KUnit-managed per-case fixture. A new exact package will receive one
new bounded run; a physical candidate remains a separate later change.

## Follow-up

The authoritative ordered next step is
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment
constrains that work to the five hardware-free patches above; it does not admit
a device candidate.
