# Mainline CPU8 active-transition admission audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-cpu8-active-transition-audit` |
| Status | current tree not request-reachable; bounded active executor selected |
| Subsystem | MT6797 CPU8 rail, platform, secure SRAM, PSCI, DCM, and recovery |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, first mainline CPU8 request |

## Question

After the exact `7.1.3-gemini-a72-cpumask` runtime completed the stable
platform, DA921x provider, and protected-clock prefix, can the canonical tree
produce the planned single CPU8 request by selecting existing configuration,
or is active transition code still missing?

## Result

It cannot be enabled by configuration alone. Read-only inspection of the exact
Buildbox prepared tree through canonical patch `0383` found zero production callers
for bootstrap publication, transaction begin/publication, P27,
positive provider acquisition, P28, P30E handoff, or P30 arming. The MT6797
CPU boot callback still unconditionally returns `-EAGAIN`, and the admission
hook still returns `-EOPNOTSUPP` even after an injected `AVAILABLE` owner state.

The platform-state source contains no write, update, reset-assert/deassert, or
CPU call. The BigiDVFS backend exposes only secure register reads through FID
`0xc200035f`; it has no SRAM-LDO setter. P27 and P28 validate typed records but
perform no hardware effects. The current device profile explicitly excludes
the positive DA921x transaction and I2C6 firmware-writer window. The upstream
watchdog driver exports boot-status observation only and has no exclusive
bounded recovery takeover.

This is a useful stop, not a regression: the repaired prefix is now proven,
and the audit prevents an inert or partially wired image from consuming the
next boot.

## Selected next implementation

Add one default-off experiment-only active transition executor with injected
operations and exhaustive hardware-free tests before connecting any physical
callback. It must:

1. accept only CPU8 and exactly one exact-token request after the complete
   platform/provider/clock prefix is revalidated;
2. arm a 15-second hardware recovery watchdog before the first mutation;
3. checkpoint before and after every P27, provider, P28, CPU_ON, online-wait,
   and DCM step;
4. use the source-backed sequence already proven by the named Gemian CPU8
   cycle: MP2 reset release, PLL ordering read, PWRAP assert, exact DA921x
   Buck-B acquire, isolation clear, PWRAP deassert, 240 microsecond guard,
   1.1 V SRAM-LDO request and selector/calibration verification, one PSCI
   `CPU_ON` for MPIDR `0x200`, bounded generic secondary completion, then the
   MP2 DCM toggle/readback;
5. roll back only exact attempt-owned P27/provider state before isolation;
6. after an isolation attempt, retain power, forbid guessed isolation/SRAM
   inverses and CPU_OFF, publish the last attributable stage, and allow the
   watchdog to return the device to Gemian; and
7. keep CPU9 offline, run one bounded CPU8 IPI/accounting proof on success,
   and still use reset recovery rather than an unproved CPU8-off path.

The production A34/membership owner remains closed in this experiment. The
executor must not manufacture current-boot replay authority or present an
experiment-only CPU8 result as production lifecycle support.

## Evidence and tools

- [`DESIGN.md`](DESIGN.md) freezes the trigger, stages, failure domains, and
  evidence path.
- [`results/source-audit-20260826.txt`](results/source-audit-20260826.txt)
  records exact prepared-source identities and call-path findings.
- [`results/decision-matrix.tsv`](results/decision-matrix.tsv) separates the
  rejected configuration-only branches from the selected implementation.
- [`scripts/transition_model.py`](scripts/transition_model.py) is an I/O-free
  executable model of the one-shot and rollback boundary.
- [`scripts/test_transition_model.py`](scripts/test_transition_model.py)
  exhausts every injected stage failure and the CPU9/repeat/timeout guards.
- [`contract.json`](contract.json) and [`scripts/validate.py`](scripts/validate.py)
  pin the audit and model evidence.

No kernel build, native VM build, hardware write, retained-memory write, CPU
request, reboot, or device action occurred during this audit.
