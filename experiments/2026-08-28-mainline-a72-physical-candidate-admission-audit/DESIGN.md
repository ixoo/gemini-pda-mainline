# CPU8 derived admission and one-shot controller design

## Rejected direct graph

The existing dormant API graph cannot be used by a production caller:

```text
caller must supply A36.watchdog_owned=1
                    |
                    v
publish P17/P18 -> add_cpu(8) -> binder ledger_begin -> watchdog_takeover
```

The required ownership appears only at the right edge, after the assertion on
the left. Moving watchdog takeover left would also place it before the retained
ledger, contradicting the binder's proven recovery order.

`begin_up()` has a second cycle: it mints the generation/cookie and validates a
caller-supplied A36 record containing the same generation/cookie within one
call. Only a fixture that predicts the initial owner state can provide it.

## Fixed ownership boundary

The physical controller supplies no admission Booleans and no transaction
identity. It owns only orchestration and one atomic consumed flag. The
membership owner derives and binds its own record from typed inputs:

- one exact composed physical-source snapshot captured while its source is
  registered;
- one exact A34 replay classification whose private replay value is zero;
- the immutable architecture READY token returned by
  `arm64_get_late_cpu_ready_token()`; and
- the live CPU topology and owner state revalidated under existing locks.

The new owner entry returns a transaction only after P31, entry validation,
token minting, derived A36 validation, and identity binding all succeed. The
same task must publish P17/P18 and call `add_cpu(8)` synchronously, because the
binder admission owner is task-bound.

## Exact selected source seam

The post-`0410` source audit selects three deliberately narrow additions:

- a locked, read-only `mt6797_a72_binder_available()` accessor that reveals
  only whether the already published binder exists;
- production register/unregister wrappers around the existing physical-source
  callback, so the controller uses the already tested six-stage capture rather
  than duplicating a reader; and
- one operation-injected controller core whose atomic consumed flag is set
  before source registration and the first owner mutation.

`mt6797_a72_membership_derive_cpu8()` already performs source capture, A34
bootstrap publication, entry derivation, P31 consumption, token minting, A36
derivation, and identity binding under the existing CPU and owner locks. The
controller therefore calls that entry once while the source is registered; it
does not make a second observation or split capture from publication.

The production platform driver resolves explicit binder, platform-state,
clock-backend, and BigiDVFS phandles with managed device links before
consumption. Binder absence and READY-token absence remain pre-consumption
probe failures. Once consumed, every result is logged as terminal and probe
returns success, preventing driver-core reprobe from creating another attempt.
The driver registers at late init, exposes no unbind control, and has no remove
callback.

## A36 repair

A36 version 1 contains four dormant caller assertions that cannot be promoted
to physical evidence:

- `da921x_page` is not captured by the five-register provider snapshot, which
  deliberately performs no `PAGE_CON` access;
- `secure_sentinels_stable` is not a field in the current composed source;
- `pstore_console_available` is superseded by the binder's fallible retained
  ledger begin and checkpoints; and
- `watchdog_owned` is superseded by the binder's exact takeover result before
  the first mutation.

The repaired record must reserve and require zero for those fields. It derives
DA921x enable/VSEL, SPM, PWRAP, DCM, online-state, target-MPIDR, call-shape,
and protected-clock validity from the composed snapshot. The membership owner fills
`secondary_entry_pa`, generation, and cookie from its own minted transaction.
No caller can pass a Boolean equivalent of `token_exact`, `prefix_complete`,
ledger readiness, or watchdog ownership.

## Controller lifetime and one shot

The candidate-only built-in platform controller resolves the same physical
source devices and the binder through explicit phandles and device links. It
uses `.suppress_bind_attrs = true` and sets its consumed flag before the first
owner mutation. Supplier absence may return `-EPROBE_DEFER` only before that
flag is consumed. Every later outcome returns a stable successful probe after
logging the terminal result, so driver-core retry cannot mint a second
transaction or make another CPU request.

The controller has no sysfs/debugfs/module parameter trigger, no remove-time
operation, no CPU9 branch, and no CPU_OFF path. It makes one synchronous
`add_cpu(8)` call. The binder remains the only physical-effect owner.

## Required order

```text
source suppliers bound
  -> binder READY (read-only check)
  -> register composed source
  -> capture exact source
  -> publish A34 bootstrap
  -> derive and bind CPU8 transaction
  -> publish P17/P18
  -> add_cpu(8) exactly once
     -> binder claim
     -> retained ledger begin
     -> watchdog takeover
     -> P27 first mutation
     -> provider / P28 / CPU_ON / lifecycle proof
  -> unregister composed source
```

Before `add_cpu(8)`, every failure has zero physical mutation. After entry,
the binder's existing pre-isolation rollback and post-isolation reset-only
rules apply. The controller never retries either class.

## Proof before a device candidate

The first implementation remains hardware-free and must prove:

1. exact source-to-entry/A36 derivation and rejection of every mutated source;
2. no caller-controlled recovery Boolean or transaction identity;
3. same-task bootstrap, publish, and request order;
4. one request on success and zero on every pre-admission failure;
5. consumed-before-mutation and no probe retry after consumption;
6. binder unavailable and READY-token unavailable rejection;
7. CPU9, CPU_OFF, userspace trigger, and repeat absence;
8. ledger -> watchdog -> first-mutation order remains unchanged; and
9. base Gemini DT remains without an enabled controller or binder.

Only an exact clean Buildbox compile and a bounded no-network KUnit/QEMU pass
may admit the separate candidate DT derivative and its single physical boot.
