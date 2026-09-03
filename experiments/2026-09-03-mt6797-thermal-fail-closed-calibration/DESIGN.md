# MT6797 fail-closed calibration design

The shared driver currently starts with generic fallback values, treats a
missing non-deferred NVMEM cell as success, and converts an extractor failure
back to success. That policy remains useful compatibility behavior for existing
SoCs, but it is unsafe as the foundation for MT6797 power and thermal work.

The change adds one immutable match-data flag, `requires_calibration`, set only
by `mediatek,mt6797-thermal`. Two pure helpers define the boundary:

- optional variants keep the existing fallback for non-deferred lookup and
  extraction errors;
- required variants propagate those errors;
- `-EPROBE_DEFER` always propagates;
- optional variants accept at least three words, preserving the old length
  rule, while MT6797 requires exactly three words.

Calibration is checked before the probe enables clocks, resets hardware, or
writes thermal/AUXADC registers. A failure therefore leaves the runtime path
closed. The KUnit suite includes only the policy header and cannot reach the
platform driver or hardware.
