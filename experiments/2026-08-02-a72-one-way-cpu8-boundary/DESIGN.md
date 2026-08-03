# One-way CPU8 startup design

## Entry contract

The first natural HPS request for CPU8 is the sole trigger. Before any write,
the transaction must prove the exact accepted offline state:

- CPU8 and CPU9 offline and no other A72 transaction active;
- observer capture window open before the one-shot is consumed;
- DA921x page `0x80`, BUCKB disabled, inherited VSEL `0x46`;
- SPM `0x218 == 0x00010132` and `0x290 == 0x00000002`;
- TOPRGU PWRAP reset bit clear, MP2 DCM zero, secure sentinels stable, and the
  protected clock snapshot valid;
- pstore console available and the independent hardware watchdog taken over
  inside the serialized CPU8 boot callback before the first A72 hardware
  mutation or PSCI request.

Any mismatch records `rejected-prestate` and performs no hardware mutation.

## Forward sequence

1. Release MP2 reset with an exact compare/update/readback of SPM `0x218`.
2. Perform the inherited B-PLL ordering read.
3. Assert PWRAP reset through the locked TOPRGU owner.
4. Enable DA921x BUCKB through its owner, wait the inherited 1 ms, and verify
   enable, page restore, and VSEL.
5. Clear external isolation with an exact owner-locked full-word transition
   `0x00000002 -> 0x00000000`; never write bit 0 from another pre-state.
6. Deassert PWRAP reset, clear only the owned software guard, and wait the
   inherited 240 microseconds.
7. Request the exact 1.1 V SRAM-LDO state through the implemented secure
   service, wait 240 microseconds, and independently read the selector and
   calibration state. The SMC return alone is never success evidence.
8. Invoke standard PSCI `CPU_ON` for MPIDR `0x200` and the exact physical
   `secondary_entry`; record raw and mapped results.
9. Reconcile any result with bounded `AFFINITY_INFO` and the existing secondary
   completion. `ALREADY_ON` or `ON_PENDING` never authorizes cleanup.
10. Only after secondary completion, run the exact serialized MP2 DCM enable
    toggle and require its final readback.
11. Publish terminal `cpu8-online-held`; keep CPU8 online and reject CPU disable,
    CPU9, and another cluster preparation attempt.

## Failure domains

Before a successful isolation clear, unwind only exact attempt-owned state in
the already-proven order: BUCKB disable, SPM reset restore, PWRAP deassert, and
software-guard release. A cleanup mismatch becomes terminal `fault-retain`.

At or after an attempted isolation write, never set isolation, disable BUCKB,
restore SPM reset, call an SRAM-disable service, or issue CPU_OFF. Deassert
PWRAP only when the locked owner proves this attempt still owns the asserted
bit. Record the last attributable stage, keep power on, reject retry, and enter
reset recovery.

If PSCI may have accepted the request, power remains retained regardless of
Linux errno. If secondary completion occurs but DCM validation fails, CPU8 is
still treated as powered/online for cleanup purposes and reset recovery is the
only permitted exit.

## Recovery and evidence

Every terminal path must write a compact identity and last-stage record to the
already-proven console-ramoops region. The hardware watchdog is armed before
the CPU8 request and is never pinged afterward. A reviewed native restart may
shorten recovery only after the terminal marker is committed; watchdog expiry
remains the independent fallback.

The later known-good boot must prove a disconnect/reconnect cycle, changed boot
ID, exact 2019 Gemian identity, sanitized pstore retrieval, and unchanged
`boot2`. Screen color or an apparent reboot is not attribution.

## Runtime classifications

| Result | Required evidence | Next action |
| --- | --- | --- |
| `rejected-prestate` | immutable exact mismatch, zero mutation | review mismatch; no retry unchanged |
| `rolled-back-preiso` | exact owned forward subset and full entry restoration | close only that injected failure row |
| `fault-retain-preiso` | failed owned-state rollback before isolation, exact last stage | recover by watchdog; review mismatch; no retry unchanged |
| `fault-retain-postiso` | last stage, retained power, no guessed inverse, recovered pstore | review exact stage; no retry unchanged |
| `cpu8-online-held` | secondary completion, CPU8 accounting, DCM readback, CPU9 absent | preserve evidence and design later stability/off policy |
| missing/ambiguous record | only recovery or visual observation | inconclusive; stop |

## Implementation gate

The no-A72 recovery runtime has now proved console-ramoops persistence,
exclusive watchdog ownership, bounded reset, and known-good return. Source
generation must still prove source-drift guards, owner-lock composition,
bounded timing, one-shot dominance, forbidden-call absence, and mutation tests
for every terminal edge. Generate reviewable patches on Buildbox, commit and
push them before any Buildbox compile, and keep the implementation
experiment-only without a synthetic DCO sign-off.
