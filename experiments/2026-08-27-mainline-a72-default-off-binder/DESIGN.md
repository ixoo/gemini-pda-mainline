# CPU8 default-off binder contract

## Fixed boundary

The binder joins already tested owners; it does not reimplement their hardware
operations. It remains default-off, accepts CPU8 only, and cannot manufacture
the A72 membership owner's bootstrap, ready token, physical-prefix result, or
current-boot authority. The hardware-free binder milestone adds no `cpu_up()`,
`add_cpu()`, Device Tree enable, boot candidate, or device action.

The later device candidate is the only phase allowed to add one late built-in
caller. That caller must first produce the exact current-boot admission inputs,
arm one membership-owned CPU8 token, and make one `CPUHP_ONLINE` request. CPU9,
CPU_OFF, retries, and userspace triggers remain unavailable.

## Required interface repairs

### Retained checkpoints

The executor's current checkpoint callback is `void`, while both retained-ledger
entry points return errors. Direct glue would therefore continue into hardware
after a failed durable checkpoint. Before physical binding, regular checkpoints
must become fallible and the binder must begin the ledger before watchdog
takeover. Every terminal path must attempt one terminal ledger commit.

A failed before/after checkpoint follows the executor's existing boundary:
before isolation it rolls back only exact provider/P27 ownership, while at or
after the isolation attempt it retains power for watchdog reset. A failed
terminal commit must demote a would-be success to a retained post-isolation
fault; it can never be reported as a proved CPU8 success.

### Admission

The existing membership hook returns `-EOPNOTSUPP` even when the owner is
`AVAILABLE`. The binder may open that gate only for one armed CPU8 token that
the membership owner still owns, for target `CPUHP_ONLINE`, with tasks not
frozen, CPU8 offline, and CPU9 offline. It derives the executor's
`token_exact` and `prefix_complete` facts from that owned record; no caller may
pass either as an unchecked Boolean.

Absent, unarmed, stale, duplicate, CPU9, wrong-target, or frozen-task requests
retain the current veto. The binder proof itself supplies no production arm
caller and makes no CPU request.

### Device lifetime

One built-in platform binder owns stable references to exactly three bound
suppliers resolved from explicit phandles: the MT6797 watchdog, A72
platform-state source, and BigiDVFS backend. Probe defers until all suppliers
are bound, verifies the registered DA921x provider separately, and publishes
only an immutable `READY` context. Probe performs no hardware operation and
does not arm an attempt.

The binder is a built-in `bool`, has no remove-time transition path, and is
absent or disabled in the base Gemini Device Tree. It calls each supplier only
through its exported typed API and validates the complete returned structure.

### Architecture boundary

Arm64 must not include the executor's driver-private header. A narrow public
binder API owns the executor and exposes only preflight, validate, CPU boot,
secondary-complete, full-complete, and failure handoffs. The MT6797 operation
table uses those functions only when the default-off binder option is selected;
otherwise its existing `-EAGAIN` boot veto and no-op lifecycle slots remain.

The CPU-boot handoff is the sole CPU_ON issuer and delegates exactly once to
`cpu_psci_ops.cpu_boot(8)`. The successful secondary and full-completion hooks
remain at the proven arm64/generic locations. The generic failure handoff must
terminalize the binder before the existing P32 rollback publication runs.

## Physical callback mapping

The binder context carries one attempt identity and the typed result from each
owner:

1. `checkpoint`: mutable transition ledger, with propagated error;
2. `watchdog_arm`: exact 15-second MT6797 recovery takeover;
3. `p27_acquire` / `p27_release`: serialized platform-effect owner using the
   attempt handle and complete result validation;
4. `provider_acquire` / `provider_release`: existing membership/provider
   wrappers and exact generation/cookie handle;
5. `isolation_clear`: serialized platform-effect owner with the held provider;
6. `sram_enable`: one 1.1 V BigiDVFS request carrying the same identity;
7. `cpu_on`: one delegation to the generic PSCI CPU boot operation;
8. `secondary_complete`: the first proven lifecycle handoff, with no private
   wait or second timeout;
9. `ipi_proof`: one synchronous CPU8 call after generic CPUHP completion; and
10. `dcm_update`: the serialized platform-effect owner with CPU8 online and
    CPU9 offline.

The watchdog identity is evidence, not the attempt identity. Platform,
provider, SRAM, ledger, membership, and lifecycle records all use one
generation/cookie pair. Compile-time checks keep the executor and watchdog
recovery timeouts equal.

## Lock and failure order

Generic CPU hotplug remains the outer lifecycle owner. The binder serializes
its one attempt, then enters only the individual supplier locks through their
public APIs. It never holds a supplier lock while calling a different supplier.
The provider registry remains the provider's serialization point.

Before isolation, rollback is provider release followed by P27 release. At or
after the isolation attempt, no provider release, P27 inverse, isolation/SRAM
inverse, CPU_OFF, or retry is permitted. Any protocol, readback, lifecycle,
IPI, DCM, or retained-record ambiguity remains armed for watchdog reset.

## Hardware-free proof

The focused KUnit suite must inject all external operations and prove exact
success order, every ordinary and terminal checkpoint failure, every owner
response corruption, pre-isolation inverse order, post-isolation retention,
one CPU_ON, admission refusal, stale/duplicate lifecycle handoffs, failure
before P32 publication, CPU9 absence, and zero CPU_OFF/retry.

Static validation must prove that the binder profile has no late CPU caller,
enabled binder DT node, physical test backend, or device-candidate profile.
The sole bounded QEMU run uses no network and cannot prove an MT6797 hardware
effect.
