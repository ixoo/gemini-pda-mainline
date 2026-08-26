# Physical-binding decomposition

## Fixed boundary

The existing executor names nine ordered stages and exposes 12 callbacks when
the common checkpoint callback is included. Its one-shot, one-CPU_ON,
pre-isolation inverse, post-isolation retention, CPU9 veto, CPU_OFF veto, and
no-retry rules remain unchanged.

This audit does not authorize a physical callback merely because a historical
implementation used the same address or function. A current owner is reusable
only when it supplies serialization, exact pre/post validation, attempt
ownership, and the required failure semantics.

## Ownership decisions

### Retained checkpoint

Add a dedicated transition ledger. It must publish a compact attempt identity,
phase, stage, terminal, and integrity word in an already-qualified retained
region. Updating the last attributable stage is the requirement; allocating 18
independent ramoops records is not. The existing two-fixed-record protected
readback helper remains unchanged and cannot be substituted.

### Watchdog

Keep ownership in `drivers/watchdog/mtk_wdt.c`. The new operation must be
one-shot, accept only 15000 ms on MT6797, disable IRQ/dual-mode delivery, enable
reset/auto-start, program and reload the timer, validate length/mode readback,
and return a monotonically nonzero identity. Once owned, ping, timeout,
pretimeout, start, and stop paths must not extend, shorten, or disable recovery.
There is no release operation after a physical transition begins.

### P27, isolation, and DCM

Keep all four operations in the platform-state source because it already owns
the SPM regmap, PWRAP reset control, MCUCFG mapping, and mutex. One transaction
object must retain exact prestate and attempt ownership:

- P27 acquire: require SPM `0x218 == 0x00010132`, set/read back bit 0 as
  `0x00010133`, perform the B-PLL ordering read, and assert/read back PWRAP.
- P27 release: before isolation only, deassert owned PWRAP and restore
  `0x00010133 -> 0x00010132`; any mismatch becomes retained fault.
- Isolation: require the same transaction and held provider, clear exact SPM
  external isolation `0x00000002 -> 0x00000000`, deassert owned PWRAP, then
  cross the no-guessed-inverse boundary.
- DCM: only after completed CPU8 bring-up and CPU9 absence, serialize the exact
  low-seven-bit toggle/readback `0x00 -> 0x0f -> 0x0d` without changing upper
  bits.

### DA921x provider

Reuse `mt6797_a72_provider_acquire()` and
`mt6797_a72_provider_release()`. The binder must build the exact CPU8 request,
validate every response field, and retain the returned generation/cookie
handle. Release is allowed only before isolation and only for the exact handle.

### SRAM-LDO

Extend the BigiDVFS backend rather than placing a raw SMC in the binder. The
owner must accept only the fixed 1.1 V request, execute the proven firmware
service once, wait 240 microseconds, then perform two stable reads of selector
`0x102222b0` and calibration `0x102222b4`. Success requires selector `0x8fb`, a
stable nonzero 16-bit calibration, no upper calibration bits, and no CPU9.
Any returned ambiguity crosses the retained-power boundary.

### CPU lifecycle

The MT6797 `.cpu_boot` callback is the only permitted CPU_ON issuer and delegates
the actual SMC to `cpu_psci_ops.cpu_boot(8)`. It must reject CPU9 and a missing
exact binder attempt. PSCI success is only `CPU_ON` acceptance.

Generic arm64 must remain the owner of `secondary_data`, `cpu_running`, and the
online transition. A narrow successful-completion hook after generic bring-up
must resume the attempt for one synchronous `smp_call_function_single()` proof
and the DCM operation. No direct `psci_ops.cpu_on()`, private completion access,
CPU_OFF, or guessed timeout loop belongs in the binder.

## Trigger

A single late built-in caller may request `add_cpu(8)` only after the exact
physical-source snapshot, provider availability, protected clocks, BigiDVFS
prestate, retained ledger, and recovery watchdog owners are ready. It must mint
one internal attempt identity, never expose a userspace trigger, and never
request CPU9.

## Validation order

Each owner lands default-off with injected hardware-free tests. The complete
binder then receives one focused Buildbox profile and exactly one bounded,
no-network QEMU run. QEMU may prove callback ordering and refusal behavior only;
it does not prove an MT6797 effect. A physical boot2 candidate remains forbidden
until every callback is present, the complete binder proof passes, and the
candidate-specific source/config/package/DT checks succeed.
