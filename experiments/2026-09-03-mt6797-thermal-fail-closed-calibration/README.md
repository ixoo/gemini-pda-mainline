# Experiment: MT6797 thermal calibration fails closed

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-03-mt6797-thermal-fail-closed-calibration` |
| Status | `completed` |
| Subsystem | MediaTek AUXADC thermal calibration |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-03 to 2026-09-04 |
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

- The deterministic Buildbox generator produced two normal patches from the
  pinned prepared source. Patch replay and strict checkpatch passed, and the
  patch validator rejected all six unsafe mutations.
- The first focused build compiled both the production driver and KUnit test,
  then exposed an existing link dependency from MT6797 EEM helpers in the same
  object to the DVFSP PPM policy validators. Enabling that existing validator
  provider in the isolated profile resolved the link without adding a runtime
  DT node or device action.
- The second Buildbox build passed from exact clean, published repository
  commit `b8fa37e34b5bf9000353e133de81e4ed527c9d99`. Its source, patchset, and
  configuration SHA-256 values were respectively `be41c068...`, `e221392b...`,
  and `971247f1...`; package checksums passed and modules were not built.
- Isolated arm64 QEMU ran only `mtk-thermal-calibration-policy`. All nine exact
  cases passed with zero failures or skips, including required/optional
  success, missing and invalid data, deferred probe, and length-policy cases.
  The raw console log SHA-256 is `03d4fb45...`.
- No candidate was created, no device was contacted, and no hardware access
  occurred. The detailed build and KUnit identities are retained in `results/`.

## Analysis

The MT6797 policy now differs from the shared driver's legacy-compatible
variants only at the explicitly selected calibration boundary. Missing,
malformed, or invalid MT6797 calibration returns an error before clock enable,
reset release, or thermal/AUXADC register writes. Deferred probe remains
deferred, while other SoCs preserve their existing fallback and minimum-length
behavior.

The source checks, strict patch checks, exact Buildbox build, and pure-helper
KUnit suite establish that policy without claiming a working thermal sensor.
The earlier
[calibration-provider experiment](../2026-09-03-mainline-power-observability-gate/README.md)
independently proved that the named NVMEM provider binds on the Gemini runtime
path; this experiment did not repeat that boot or read calibration values.

## Conclusion

Confirmed for the hardware-free gate: MT6797 requires an exact, valid
three-word calibration payload and fails closed otherwise, while optional
variants retain their prior fallback behavior. All nine focused policy cases
pass. Runtime temperature conversion, controller transactions, interrupts,
and protection remain unproven and disabled.

## Follow-up

Keep the Gemini thermal and AUXADC DT nodes disabled while auditing the exact
MT6797 thermal/AUXADC register transaction and enable ordering against the
pinned vendor source and current mainline driver. Resolve global-idle ordering,
clock/reset ownership, data-valid semantics, indirect-sampling constants, and
IRQ/watchdog timeout behavior. Then hardware-free-test a transaction plan
before any runtime enablement. Do not add OPPs, cpufreq, trips, cooling, longer
CPU load, idle, or suspend yet.
