# Experiment: MT6797 read-only transition-owner registration

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mt6797-readonly-owner-registration` |
| Status | `running` |
| Subsystem | MT6797 DVFSP state/provenance ownership |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-15 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | none |

## Question or hypothesis

Can the runtime-proven vendor epoch/calibration identity be carried without
narrowing or loss through the existing mainline review bridge, then used to
register the already-dormant state owner read-only and fail closed?

The first gate is narrower: repair every attribution loss or width mismatch
found before registration. A later patch may expose registration only after
the vendor snapshot, vendor provenance, calibrated snapshot, and calibrated
owner identity all agree.

## Provenance and environment

- Kernel release: Linux 7.1.3 from the manifest-selected prepared source.
- Patch base: canonical `patches/series` through patch `0271`.
- Configuration: manifest profile `dvfsp-owner-kunit` for focused validation,
  followed by the normal `full` profile.
- Build backend: Buildbox only.
- Boot path: none; this experiment is hardware-free until a later, separately
  reviewed runtime gate exists.
- Runtime premise: the named Gemini published two stable, complete EEM/PPM
  snapshots with generation 9, table epoch 1, calibration handle 1, and no
  owner/transition handle. See the linked provenance-observer experiment.

## Safety assessment

This phase is read-only and default-off. It must not add a setter, provider
vote, register-data write, MMIO write, I2C transfer, firmware request, CPU hotplug
operation, boot candidate, or device action. Registration remains absent until
all identity surfaces agree. Any zero, stale, truncated, or mismatched identity
must fail closed.

No device filesystem or partition backup is needed because no device is
accessed. Any later guarded `boot2` write remains governed by the repository's
standing policy and project-wide recovery backup.

## Associated code

- [`DESIGN.md`](DESIGN.md): contract and ordered gates.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic edits to
  the managed Buildbox source, applied in one logical phase per commit.
- [`scripts/validate_source.py`](scripts/validate_source.py): final-source
  contract and no-write audit.
- [`scripts/validate_patch.py`](scripts/validate_patch.py): canonical patch
  identity, attribution, and forbidden-operation audit.

## Procedure

1. Reuse the manifest-matching managed prepared Linux tree on Buildbox.
2. Copy only the affected files into a bounded temporary Git repository on
   Buildbox; never edit the managed source or transfer a Linux source tree.
3. Apply one deterministic source-edit phase, commit it without a synthetic
   DCO sign-off, and emit one `git format-patch` file.
4. Validate each patch and the composed source, then add the patches to the
   canonical series in order.
5. Commit and push the exact repository state before the focused and full
   Buildbox builds.

## Observations

The initial source audit found three prerequisites before registration:

- `mt6797_dvfsp_state_provenance.table_epoch` was 32-bit while every source
  epoch contract is 64-bit;
- the state-snapshot assembler validated owner, transition, and provenance
  input but did not copy those fields to its output;
- the vendor provider bridge validated a snapshot and identity but never
  consumed the already-required vendor provenance callback.

These are compile-review findings. No hardware-support claim follows.

## Analysis

Registering the owner before these repairs would either truncate a legitimate
epoch, publish an unattributed snapshot, or accept an identity not tied to the
sampled generation. Therefore registration is not yet the next safe code
change; the three attribution repairs are ordered prerequisites.

## Conclusion

`inconclusive` until the prerequisite patches and Buildbox validation complete.

## Follow-up

After the prerequisite series passes, add one separate read-only registration
patch that cross-checks the vendor and calibrated views before calling the
existing arbitration registry. Setters, hardware writes, and CPU8/CPU9
admission remain closed for later gates.
