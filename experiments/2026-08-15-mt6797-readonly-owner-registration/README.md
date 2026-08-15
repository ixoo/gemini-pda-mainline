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

Buildbox then fetched exact pushed generator commit `967f5e4036fb...`, verified
the managed prepared-source state, and emitted three zero-commit
`git format-patch` files from a bounded six-file temporary repository. Their
full SHA-256 identities are recorded in the
[`patch-generation receipt`](results/prerequisite-patch-generation-buildbox-20260815.txt).
All format, synthetic-signoff, composed-source, and no-write checks pass. One
initial request named a nonexistent full commit and was rejected before edits;
its exact temporary directory was removed before the successful retry.

The exact prerequisite commit `c93ebabea3be...` then passed the focused
Buildbox profile: 263 patches applied, 119 DTBs built, package checksums passed,
and only the validated package was fetched. The
[`focused-build receipt`](results/prerequisite-focused-buildbox-20260815.txt)
records the artifact and input identities. The build exposed no compiler or API
error. It did preserve pre-existing test stack warnings and added a warning for
the vendor-provider bridge's large automatic snapshot; reduce that frame before
adding registration state.

The fetched image booted under isolated arm64 QEMU and all six focused KUnit
suites passed: 24 tests, zero failures, and zero skips. This includes the new
wide-epoch, assembled-attribution, and vendor-provenance-mismatch cases. QEMU
reported the kernel halted before the outer runner's expected timeout. See the
[`KUnit receipt`](results/prerequisite-qemu-kunit-20260815.txt). No Gemini or
other physical device was accessed.

The exact evidence commit `5fe5fa7f4261...` also passed the normal full
Buildbox profile: the same 263-patch identity compiled into 119 DTBs, every
package checksum passed, and only the validated package was fetched. The
[`full-build receipt`](results/prerequisite-full-buildbox-20260815.txt) records
the exact source, patchset, configuration, image, and Gemini DTB identities.

## Analysis

Registering the owner before these repairs would either truncate a legitimate
epoch, publish an unattributed snapshot, or accept an identity not tied to the
sampled generation. The three repairs now pass their focused compile,
hardware-free runtime, and full-profile compile gates. The bridge stack warning
should be removed as part of the next bounded implementation rather than
carried into its lifetime path.

## Conclusion

`inconclusive`: every prerequisite gate passes; read-only owner registration
remains open.

## Follow-up

Add a separate read-only registration change that reduces bridge stack use and
cross-checks the vendor and calibrated views before calling the existing
arbitration registry. Setters, hardware writes, and CPU8/CPU9 admission remain
closed for later gates.
