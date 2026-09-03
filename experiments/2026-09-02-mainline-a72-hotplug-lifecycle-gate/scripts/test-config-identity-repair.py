#!/usr/bin/env python3
"""Reject unsafe mutations of the physical-hotplug identity repair."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve()
VALIDATOR = SCRIPT.with_name("validate-config-identity-repair.py")
spec = importlib.util.spec_from_file_location("physical_config_identity_validator", VALIDATOR)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def rejected(text: str) -> bool:
    try:
        validator.validate_patch_text(text)
    except ValueError:
        return True
    return False


def main() -> int:
    baseline = validator.PATCH.read_text(encoding="utf-8")
    validator.validate_patch_text(baseline)
    mutations = {
        "wrong-target-word": baseline.replace("0x2e50cc09d2241006", "0x2e50cc09d2241007", 1),
        "unscoped-production": baseline.replace(
            "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING)", "#if 1", 1),
        "wrong-profile": baseline.replace("A72_HOTPLUG_BINDING", "A72_HOTPLUG_EXECUTOR", 1),
        "predecessor-overwritten": baseline.replace(
            "0xcda6d936e61122d8", "0x2e50cc09d2241006", 1),
        "extra-code": baseline.replace("+#endif\n #endif", "+pr_info(\"unsafe\");\n+#endif\n #endif", 1),
    }
    for name, text in mutations.items():
        if not rejected(text):
            raise SystemExit(f"unsafe mutation accepted: {name}")
        print(f"mutation={name} result=rejected")
    print(f"mutations_rejected={len(mutations)}")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
