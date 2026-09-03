# Experiment: MT6797 thermal calibration fails closed

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-03-mt6797-thermal-fail-closed-calibration` |
| Status | `running` |
| Subsystem | MediaTek AUXADC thermal calibration |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | CPU8/CPU9 power-observability gate |

## Question or hypothesis

Can the shared MediaTek AUXADC thermal driver require exact, valid calibration
for MT6797 without changing the fallback behavior of its other supported SoCs?

## Provenance and environment

- Prepared Linux source state:
  `cfb17989ea0cbf135c70ddd6c4fb32d0060f1a7d251fdd6fc6b61c719991d7be`
- Prepared Linux source integrity:
  `2c2e9a81eccd1a97253b7864c9b9ada4b959e11399bf016ef990f9e92c384687`
- Parent `auxadc_thermal.c` SHA-256:
  `154b221b9dd55a703bbbb6ac9196b7479d235fdea7592500e69eac8a7524a257`
- Build backend: Buildbox only.
- Boot path: none; this is a hardware-free source, build, and KUnit gate.

## Safety assessment

The generator operates on bounded copies of three Linux source files inside a
temporary Buildbox directory. The KUnit suite calls only pure inline policy
helpers. It registers no platform device, maps no MMIO, enables no clock,
touches no storage, writes no partition, and creates no boot candidate.

## Associated code

- `scripts/source_edits.py`: deterministic production and KUnit edits.
- `scripts/validate_source.py`: final edited-source contract validator.
- `scripts/validate_patches.py`: normal-format-patch boundary validator.
- `scripts/test-patch-validator.py`: mutation tests for the patch validator.
- `scripts/validate_tool.py`: generator-body validation.
- `scripts/generate-on-buildbox`: pinned Buildbox patch generation.
- `scripts/run-kunit-qemu`: isolated arm64 QEMU KUnit runner.
- `scripts/classify-kunit.py`: exact KTAP classifier.

## Procedure

1. Validate the local generator and mutation checks.
2. Commit and publish the generator at a clean repository revision.
3. Generate two normal patches from the pinned prepared source on Buildbox.
4. Admit the validated patches and a focused KUnit-only manifest profile.
5. Build the exact published profile on Buildbox and run its image in isolated
   arm64 QEMU.
6. Record exact source, patch, configuration, package, and KTAP identities.

## Observations

Pending.

## Analysis

Pending.

## Conclusion

Pending.

## Follow-up

If the hardware-free gate passes, keep the Gemini thermal and AUXADC DT nodes
disabled while auditing the MT6797 clock/reset/idle/valid-bit/IRQ transaction
contract. Do not add OPPs, cpufreq, trips, cooling, or longer CPU load yet.
