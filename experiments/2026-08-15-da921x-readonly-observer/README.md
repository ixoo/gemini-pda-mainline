# Experiment: DA921x read-only provider observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-da921x-readonly-observer` |
| Status | running |
| Subsystem | legacy DA9213/DA9214/DA9215 regulator provider |
| Device variant | Planet Gemini PDA, MT6797; no live-device action yet |
| Date(s) | 2026-08-15 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | none |

## Question or hypothesis

Can the native Linux 7.1 legacy DA921x provider produce one uniquely
attributable observation proving its identity transcript, two read-only
provider registrations, bounded state reads for both rails, and zero
register-data writes, while failing closed on every partial observation?

## Provenance and environment

- Kernel release: Linux 7.1.3 from the manifest-selected prepared source.
- Parent series: canonical `patches/series` through patch `0277`.
- Build backend: Buildbox only.
- Boot path: none during source design and validation.

## Safety assessment

The proposed observer is default-off and reuses only the provider's existing
`get_voltage_sel`, `list_voltage`, and `is_enabled` operations. It adds no
setter, regulator consumer, IRQ, page selection, register-data write, firmware
call, CPU request, or device write. Hardware-free tests use a fake read
callback. No device backup is needed. Until source, KUnit, full Buildbox,
package, and container validation pass, no boot candidate exists.

## Associated code

- [`DESIGN.md`](DESIGN.md): observation, failure, and lifecycle contract.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic bounded
  source transformation used only in a temporary Buildbox Git repository.
- [`scripts/validate_source.py`](scripts/validate_source.py): source contract
  and no-write validation.
- [`scripts/validate_tool.py`](scripts/validate_tool.py): deterministic editor
  contract validation.
- [`scripts/validate_patch.py`](scripts/validate_patch.py): generated
  format-patch validation.
- [`scripts/test_mutations.py`](scripts/test_mutations.py): decision-changing
  mutation checks.

## Procedure

1. Audit the exact final driver, Device Tree node, and Kconfig on Buildbox.
2. Freeze the read-only observation and cleanup contract.
3. Commit and push the deterministic source tool and validators.
4. Generate one normal experiment-only `git format-patch` from a bounded
   temporary Git repository on Buildbox.
5. Add the patch in canonical order plus isolated observer and KUnit profiles.
6. Run static, mutation, patch-apply, checkpatch, focused KUnit, and normal
   Buildbox validation.
7. Decide from that evidence whether one separately attributable boot2
   candidate is justified.

## Observations

The final Linux 7.1 driver performs the exact two-pass, seven-sample identity
transcript before registering two descriptors. Each descriptor exposes only
`get_voltage_sel`, `list_voltage`, and `is_enabled`. The final driver has two
`__i2c_transfer()` call sites, both combined reads; it has no register-data
write helper or writable regulator operation. The Gemini Device Tree node has
the exact primary and page2 addresses and no regulator child.

## Analysis

The smallest decision-changing runtime evidence is a one-shot record after
both registrations. It must exercise the same regulator operations exposed by
the descriptors instead of introducing a parallel raw-register reader. A
devres action registered before the provider registrations can distinguish a
normal unbind from a failed later probe and runs after the later provider
devres entries have been released.

## Conclusion

Pending source and Buildbox validation. No runtime or hardware claim is made.

## Follow-up

If every offline gate passes, construct and independently validate one exact
diagnostic container before considering a guarded boot2 deployment. Provider
setters, hardware writes, transition ownership, and CPU8/CPU9 admission remain
closed.
