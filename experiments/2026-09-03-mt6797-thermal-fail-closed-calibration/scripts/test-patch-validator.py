#!/usr/bin/env python3
"""Exercise the thermal patch validator against unsafe mutations."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_patches.py")
SPEC = importlib.util.spec_from_file_location("thermal_patch_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load patch validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def production_patch() -> str:
    additions = "\n".join(f"+{token}" for token in (
        "bool requires_calibration;", ".requires_calibration = true,",
        "mtk_thermal_calibration_status(",
        "mtk_thermal_calibration_length_valid(",
        "required ? len == expected : len >= expected",
    ))
    return f"""From {'1' * 40} Mon Sep 17 00:00:00 2001
From: Gemini Mainline Experiment <gemini-mainline@example.invalid>
Subject: [PATCH 1/2] thermal: mediatek: require valid MT6797 calibration

---
diff --git a/drivers/thermal/mediatek/auxadc_thermal.c b/drivers/thermal/mediatek/auxadc_thermal.c
--- a/drivers/thermal/mediatek/auxadc_thermal.c
+++ b/drivers/thermal/mediatek/auxadc_thermal.c
@@
{additions}
diff --git a/drivers/thermal/mediatek/auxadc_thermal_internal.h b/drivers/thermal/mediatek/auxadc_thermal_internal.h
--- /dev/null
+++ b/drivers/thermal/mediatek/auxadc_thermal_internal.h
@@
+policy
"""


def kunit_patch() -> str:
    cases = "\n".join(f"+KUNIT_CASE(case_{index})," for index in range(9))
    additions = "\n".join(f"+{token}" for token in (
        "MTK_SOC_THERMAL_KUNIT_TEST",
        "mtk_thermal_required_missing_fails",
        "mtk_thermal_required_invalid_fails",
        "mtk_thermal_required_length_is_exact",
        "mtk-thermal-calibration-policy",
    ))
    return f"""From {'2' * 40} Mon Sep 17 00:00:00 2001
From: Gemini Mainline Experiment <gemini-mainline@example.invalid>
Subject: [PATCH 2/2] thermal: mediatek: test calibration requirement policy

---
diff --git a/drivers/thermal/mediatek/Kconfig b/drivers/thermal/mediatek/Kconfig
--- a/drivers/thermal/mediatek/Kconfig
+++ b/drivers/thermal/mediatek/Kconfig
@@
+config
diff --git a/drivers/thermal/mediatek/Makefile b/drivers/thermal/mediatek/Makefile
--- a/drivers/thermal/mediatek/Makefile
+++ b/drivers/thermal/mediatek/Makefile
@@
+object
diff --git a/drivers/thermal/mediatek/auxadc_thermal_test.c b/drivers/thermal/mediatek/auxadc_thermal_test.c
--- /dev/null
+++ b/drivers/thermal/mediatek/auxadc_thermal_test.c
@@
{additions}
{cases}
"""


def validate_pair(production: str, kunit: str,
                  extra: dict[str, str] | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="gemini-thermal-patch-test.") as tmp:
        root = Path(tmp)
        (root / VALIDATOR.PATCH_NAMES[0]).write_text(production, encoding="utf-8")
        (root / VALIDATOR.PATCH_NAMES[1]).write_text(kunit, encoding="utf-8")
        for name, text in (extra or {}).items():
            (root / name).write_text(text, encoding="utf-8")
        VALIDATOR.validate(root)


def main() -> None:
    production = production_patch()
    kunit = kunit_patch()
    validate_pair(production, kunit)
    mutations = (
        (production.replace("[PATCH 1/2]", "[PATCH]", 1), kunit, None),
        (production.replace("requires_calibration = true", "requires_calibration = false", 1), kunit, None),
        (production + "Signed-off-by: Nobody <nobody@example.invalid>\n", kunit, None),
        (production, kunit.replace("KUNIT_CASE(case_8),\n", "", 1), None),
        (production, kunit + "+writel(1, base);\n", None),
        (production, kunit, {"9999-extra.patch": production}),
    )
    rejected = 0
    for changed_production, changed_kunit, extra in mutations:
        try:
            validate_pair(changed_production, changed_kunit, extra)
        except VALIDATOR.ValidationError:
            rejected += 1
        else:
            raise SystemExit("unsafe patch mutation accepted")
    print("validation=mt6797-thermal-patch-validator-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
