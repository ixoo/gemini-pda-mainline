# MT6797 A72 A34 eligibility evaluator design

## Claim boundary

This experiment implements only the default-off, pure A34 evaluator selected
by the Gate-7 remaining-boundary audit. It does not replace the harness seed,
add a boot caller, or perform the future lifecycle transition.

The evaluator answers only:

```text
complete immutable A34 input -> eligible or reject
```

Eligibility is not reset evidence or authority. The owner remains
`CLOSED / UNINITIALIZED`, all four A38 attempts remain uninitialized, and P31,
A36, P17/P18, provider acquisition, P27/P28, P30 arm, and `CPU_ON` remain
unreachable.

## Exact immutable input

The ABI is accepted only when every field is exact:

- reset provenance is explicitly either known-good platform reset or external
  reset; unknown, default-zero, and ordinary-Linux-reboot provenance reject;
- private replay proof is explicitly owner-safe zero, with a zero replay
  value; unknown or inferred proof rejects;
- ABI `1`, `max_cpus=8`, and `nr_cpu_ids=10`;
- possible and present counts `10`, masks `0x3ff`;
- online count `8`, mask `0x0ff`;
- CPUs 8 and 9 use `mediatek,mt6797-psci`;
- CPU8/CPU9 generic states are both `CPUHP_OFFLINE`;
- CPU8/CPU9 MPIDRs are `0x200` and `0x201`, separately and non-aliased;
- the complete P30 snapshot is zero/FREE;
- the complete membership-owner snapshot is its exact initial state: ABI `2`,
  diagnostic blockers complete, health CLOSED, phase UNINITIALIZED, provider
  NONE, and every transaction, membership, provider identity, controller,
  fault, validity, attempt, and retirement field empty;
- internal next generation and cookie are zero; and
- proposed first generation `1` and cookie `0xa7200001` are exact.

The observation must be zero-initialized before fields are assigned. Counts and
masks remain intentionally redundant. The pure evaluator accepts only the two
named reset-provenance values, then compares every remaining byte against an
exact immutable object. This also makes reserved or padding bytes fail closed
instead of silently becoming a second ABI.

## Result and ownership

Null input returns `-EINVAL`. An exact platform-reset or external-reset tuple
returns zero. Every other input returns `-EPERM`.

The function reads no global owner state, takes no lock, and writes no state.
A successful return does not initialize attempts, clear a blocker, mint a
generation, or make admission available. A later reviewed production
reset/bootstrap owner must establish both provenance sources, collect and
serialize the tuple, revalidate it at publication, and own the atomic
`CLOSED / UNINITIALIZED -> AVAILABLE / IDLE` transition. That owner is outside
this slice.

## Future reset-provenance candidate

The pinned vendor MT6797 watchdog source defines the read-only TOPRGU
`WDT_STATUS` register at offset `0x0c`. It distinguishes hardware-watchdog,
software-watchdog, IRQ-watchdog, debug-watchdog, SPM-watchdog, thermal, and
security reset classes. The exact mainline source through patch `0301` does
not define or read that register. Its probe maps TOPRGU and later calls
`mtk_wdt_init()`, which may change timeout and reload state when firmware left
the watchdog enabled.

A future reset-provenance producer could therefore snapshot `WDT_STATUS`
immediately after successful resource mapping and before `mtk_wdt_init()`.
That is only a candidate: the LK path must first prove which bits survive into
Linux, whether it reads or clears the latch, and which exact values establish
a completed platform/external reset. Until those semantics are frozen, the
status register cannot make the evaluator input true. It also cannot prove the
separate private replay ledger.

## Hardware-free proof

The focused KUnit suite uses only an injected immutable observation. It must:

1. accept exact platform-reset and external-reset inputs;
2. reject null input;
3. mutate every byte of the otherwise-valid observation and reject each one;
4. reject explicit unknown/ordinary-Linux reset provenance; and
5. prove byte-identical owner snapshots and closed admission before and after
   positive evaluation.

QEMU runs only that focused suite. There is no production A34 hook or
target-topology interpretation in this slice.

## Explicit exclusions

The patch adds no production init caller, lifecycle publication, attempt
initialization, CPUHP accessor or callback, provider or regulator call, I2C or
MMIO access, P27/P28 executor, P30 mutation, firmware call, PSCI call,
`CPU_ON`, `CPU_OFF`, boot-veto change, boot candidate, device write, or device
action. The A41 profile remains identity-only and blocked, admission remains
closed, and MT6797 `.cpu_boot` remains `-EAGAIN`.
