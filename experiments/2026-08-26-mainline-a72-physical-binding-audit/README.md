# Mainline CPU8 physical-binding audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-physical-binding-audit` |
| Status | `completed` |
| Subsystem | MT6797 CPU8 recovery, power, provider, PSCI, and retained evidence |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, first mainline CPU8 request |

## Question or hypothesis

Can the hardware-free CPU8 executor's callback table be connected directly to
current owners in the exact prepared source, or are additional narrowly scoped
interfaces and lifecycle work required before a physical candidate is safe?

## Provenance and environment

- Repository commit audited: `84dfebce99353ae3473760bfc4fe201550cc383f`.
- Canonical series: 377 patches through `0385`.
- Prepared-source state: `66469bd0272084cbf607b068608096ec1e4ea075638393501e758d113e3c7106`.
- Prepared-source integrity: `674cb5a9b47ee509f55f4ee512c356c0493331dc612c3eb5569cbb6a8180c49f`.
- Backend: read-only inspection of the managed Buildbox source tree.
- No kernel configuration, build, package, boot path, or target partition was
  selected by this audit.

Exact file identities and line-level findings are recorded in
[`results/source-callback-map-20260826.txt`](results/source-callback-map-20260826.txt).

## Safety assessment

This was read-only source inspection. It did not compile a kernel, contact the
Gemini, write retained RAM, request a CPU, alter a partition, or reboot a
device. Historical Gemian and older mainline experiment patches were used only
as evidence for ordering and prior behavior; they are not copied into the
current implementation.

## Associated code

- [`contract.json`](contract.json) is the machine-readable callback map and
  implementation order.
- [`scripts/validate.py`](scripts/validate.py) checks the callback inventory,
  source identities, ownership classes, and no-device boundary.
- The already-proven executor remains in the preceding
  [transition-executor experiment](../2026-08-26-mainline-a72-cpu8-transition-executor/README.md).

## Procedure

1. Read every executor callback from the exact prepared source.
2. Trace each callback to the current watchdog, pstore, platform-state,
   DA921x, BigiDVFS, PSCI, generic CPU-hotplug, SMP-call, and DCM owners.
3. Classify a callback as directly reusable only when its present API has the
   required mutation, ownership, validation, and lifecycle semantics.
4. Compare the resulting order with the runtime-proven Gemian CPU8 sequence
   and the current one-shot/rollback contract.
5. Select the smallest implementation units that can receive independent
   hardware-free tests before they are composed.

## Observations

Only the DA921x provider acquire and release callbacks are directly reusable.
The provider already serializes the exact I2C endpoint, returns a generation
and cookie handle, verifies held state, and accepts release only for that
handle.

The platform-state source owns the exact SPM regmap, PWRAP reset control,
MCUCFG mapping, and serialization needed by P27, isolation, and DCM, but it is
read-only. Reacquiring those resources in a separate binder would split
ownership and conflicts with the exclusive reset control, so the source must
grow narrow transaction methods instead.

The current BigiDVFS backend exposes only secure FID `0xc200035f` reads. It has
no SRAM-LDO setter and does not sample calibration word `0x102222b4`, both of
which are required by the proven sequence.

The MT6797 CPU boot callback still returns `-EAGAIN`. Generic arm64 owns the
secondary completion, and generic CPU hotplug continues after `__cpu_up()`
observes `cpu_online()`. The physical integration therefore needs an explicit
post-bringup continuation for the IPI/DCM proof; it must not equate the PSCI
return with completed generic CPU admission.

The current retained-RAM helper is also not a transition journal. It accepts
only checkpoint 0 followed by checkpoint 1 and writes two compile-time-fixed
records. It cannot represent the executor's last stage or its 18 before/after
checkpoints.

Finally, the watchdog driver has the register programming primitives for a
15-second reset, but no exclusive recovery-takeover API. Ordinary watchdog-core
and userspace keepalives would remain able to reload or reconfigure the timer
unless the MediaTek owner explicitly closes those paths after takeover.

## Analysis

The hypothesis that the executor can be wired directly is rejected. Two of 12
callbacks are ready, four can be implemented by extending the current
platform-state owner, three require new narrowly scoped owner APIs, and three
require an arm64/generic-hotplug lifecycle bridge. Treating the current
read-only readers or the PSCI return as completed effects would produce a
candidate with weak attribution and repeat the earlier reset-only evidence
problem.

The work can still remain bounded. The selected order is:

1. add and hardware-free-test an exclusive 15-second MediaTek watchdog
   takeover;
2. add a dedicated last-stage retained transition ledger;
3. add one serialized platform-effect transaction for P27 acquire/release,
   isolation clear, and post-online DCM;
4. add one exact BigiDVFS SRAM-LDO set-and-verify owner;
5. split/bridge the executor across PSCI issue and completed generic CPU
   bring-up, then add the one late CPU8 caller; and
6. prove the complete binder with injected tests and no-network QEMU before
   assembling a boot2 candidate.

## Conclusion

`confirmed`: direct binding is not safe or complete at revision `84dfebce`.
The DA921x pair is ready, but the other ten callbacks need owner or lifecycle
work. No hardware support claim follows from this source audit.

## Follow-up

The next implementation is the default-off watchdog recovery-takeover
boundary. It must accept exactly 15 seconds, become one-shot and non-releasable,
block later reload/reconfiguration paths, return register readback plus a
nonzero identity, and pass injected KUnit/QEMU testing without a physical
watchdog action. The retained stage ledger follows before any device candidate.
