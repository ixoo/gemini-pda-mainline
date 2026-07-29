# Experiment: superseded userspace CPU8 request draft

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-21-cortex-a72-cpu8-diagnostic` |
| Status | `archived; superseded before build or boot; must not be selected` |
| Subsystem | MT6797 Cortex-A72 CPU8 hotplug |
| Device variant | Named Gemini PDA development unit |
| Date | 2026-07-21 |
| Runtime evidence | None |

## Original question

Could an initramfs derived from the eight-A53 Candidate AD foundation request
CPU8 through the generic sysfs hotplug interface and use the watchdog to return
to the known-good system?

The retained scripts attempted to keep Candidate AD's kernel and Device Tree
while changing userspace to mount a private writable sysfs view and write the
CPU8 `online` control. Internal labels mix Candidate AE and AF because the
draft was abandoned during design; they are not validated candidate identities.

## Why it was rejected

The draft would have issued an active CPU8 request before the external DA921x
regulator contract, I2C6 ownership, SRAM-LDO sequence, clock/CCI ownership,
rollback, and firmware coordination were established. A watchdog is not a
sufficient safety mechanism for an incorrect rail or power sequence.

No package, installation, boot selection, CPU8 transition, or runtime result is
recorded for this directory. The scripts are retained only as historical
evidence of the rejected approach and must not be treated as buildable current
tooling.

The work was superseded first by the
[read-only A72 power observer](../2026-07-21-cortex-a72-power-observer/README.md)
and later by the staged regulator/ownership investigation. The current safe
boundary is documented in
[DA921x, I2C6, and Cortex-A72](../../docs/hardware/da921x-i2c6-a72.md); the
ordered next gates are owned by the [roadmap](../../docs/ROADMAP.md).

## Decision

- Do not build, install, or boot this draft.
- Do not infer any A72 support from its source.
- Keep CPU8 and CPU9 offline until the zero-probe-write legacy-family driver,
  provider constraints, bounded write/readback/rollback, and full power
  sequence gates pass.
