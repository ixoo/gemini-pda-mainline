# Experiment: mainline A72 direct-state compositor audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-a72-direct-state-compositor-audit` |
| Status | completed offline source/lock audit; owner contract frozen |
| Subsystem | MT6797 A72 hotplug, DA921x, protected state, platform state |
| Device variant | Planet Gemini PDA contract; hardware-free audit |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, direct-state composition |

## Question or hypothesis

Which existing lock can honestly own a combined DA921x, protected-clock,
BigiDVFS, platform-state, generic-CPU, and Linux-owner snapshot, and what
smallest new boundary is required before A34 can consume it?

The hypothesis is that the existing A72 membership owner must be the outer
owner because it alone can serialize its transaction state with CPU8/CPU9
hotplug. The independent reader locks remain necessary inside that outer
transaction but cannot substitute for it.

## Provenance and environment

- Repository input: signed, pushed protected-clock evidence commit
  `cb24e51645bc84ab3e1754de0ea529093458db4a`.
- Managed Buildbox source state through canonical patch `0336`:
  `e321876084d9f2250fbb0a76e5deded87499e65d7c131daa5117023275d3e30b`.
- Managed source integrity:
  `56230cbfa53d3ba7de0d214ce74848baa2d8a05ba401c4a9b5fa9105f7938af4`.
- Exact inspected source identities are pinned in
  [`contract.json`](contract.json) and the
  [source/lock receipt](results/source-lock-audit-20260823.txt).
- The prepared source was inspected read-only on Buildbox. No Linux source
  tree was copied to or from the development host.

## Safety assessment

This audit was read-only. It performed no build, MMIO, SMC, I2C transfer,
device contact, partition access, boot2 write, reboot, owner registration,
provider operation, or CPU request. It authorizes only the default-off,
hardware-free implementation boundary in [`DESIGN.md`](DESIGN.md).

The selected implementation must leave every caller output all-zero on
failure, register no production A34 caller, publish no lifecycle state, change
no CPU veto, and contain no setter, CPU_ON, CPU_OFF, retry, polling, or device
enablement.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the ownership, lock order, record, and
  failure rules.
- [`contract.json`](contract.json) pins the exact inputs and selected/rejected
  boundaries.
- [`scripts/validate.py`](scripts/validate.py) checks the audit and its scope
  offline.
- [`results/source-lock-audit-20260823.txt`](results/source-lock-audit-20260823.txt)
  is the sanitized source/lock receipt.

No privilege or hardware access is required to validate this audit:

```sh
python3 experiments/2026-08-23-mainline-a72-direct-state-compositor-audit/scripts/validate.py
```

## Procedure

1. Pin the exact prepared source state after canonical patch `0336`.
2. Inspect the final A72 membership, DA921x provider snapshot, A72 platform
   snapshot, protected-clock snapshot, BigiDVFS snapshot, and DVFSP resource
   owner APIs.
3. Enumerate every lock held by those paths and identify which state changes
   each lock excludes.
4. Compare the A72 membership transition lock and Linux CPU-hotplug lock with
   the independent DVFSP resource-owner lock.
5. Freeze one outer-owner and callback contract that composes the readers
   without changing A34 or enabling a hardware path.
6. Run the offline validator and record the exact result.

## Observations

- `mt6797_a72_membership_snapshot()` takes only `a72_state_lock`; it does not
  hold `a72_transition_lock` or the CPU-hotplug lock through any hardware
  source read.
- DA921x, platform-state, protected-clock, and BigiDVFS snapshots each provide
  their own bounded local serialization and zero-on-error contract.
- `cpus_read_lock()` excludes CPU hotplug operations, whose transition path
  takes the CPU-hotplug write lock.
- `a72_transition_lock` is the existing outer serialization point for every
  A72 membership transition and test bootstrap mutation.
- `mt6797_dvfsp_resource_owner.transition_lock` is a separate DVFSP resource
  lifecycle lock. It neither owns generic CPU hotplug nor serializes the A72
  membership owner, and its device tuple requires unrelated thermal and
  calibration sources.
- No current call path holds the CPU-hotplug lock and `a72_transition_lock`
  while consuming all four owner-local readers and the generic/Linux state.

The exact source hashes and lock decision are in the
[source/lock receipt](results/source-lock-audit-20260823.txt).

## Analysis

The hypothesis is confirmed. Nesting the existing bounded readers under the
A72 membership owner preserves their local ownership, but merely invoking
them from an unrelated observer or the DVFSP resource owner would still allow
the A72 Linux transaction state or generic hotplug state to move between
samples.

The smallest honest implementation is a default-off source registry plus one
snapshot entry point in the A72 membership owner. That entry point takes the
CPU-hotplug read lock, then `a72_transition_lock`, invokes one registered
hardware-only compositor into local storage, captures the generic and Linux
owner state, validates the complete record, and publishes it only at the end.
The first implementation is hardware-free and injected; the later platform
binding may call the already-existing readers in the frozen order.

This does not prove that separately timed physical fields equal the historical
reference tuple. It defines who may take that measurement and how project-
controlled writers and CPU8/CPU9 hotplug are excluded while it is consumed.
Secure firmware movement must still surface through the existing bounded
reader failures and platform change detection.

## Conclusion

`confirmed`: the A72 membership owner, nested inside the Linux CPU-hotplug
read lock, is the only current ownership boundary suitable for the complete
direct-state snapshot.

`rejected`: independent probe-time reads, `mt6797_a72_membership_snapshot()`
alone, local reader mutexes alone, or the separate DVFSP resource-owner mutex
as A34 atomicity.

`selected`: add a default-off, hardware-free, injected direct-state source
registry and owner-held snapshot entry point. It must retain exact zero-on-
failure semantics and must not revise A34, publish `AVAILABLE / IDLE`, enable
a DT node, perform a hardware operation, or request CPU8/CPU9.

## Follow-up

The authoritative execution order remains in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment owns
only the exact source/lock decision and its rejected alternatives.
