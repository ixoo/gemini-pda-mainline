#!/usr/bin/env python3
"""Validate deterministic thermal edit fragments and workflow boundaries."""

from __future__ import annotations

from pathlib import Path

import source_edits


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    header = source_edits.policy_header()
    test = source_edits.kunit_source()
    editor = Path(source_edits.__file__).read_text(encoding="utf-8")
    generator = (ROOT / "scripts/generate-on-buildbox").read_text(encoding="utf-8")
    buildbox = (REPO / "scripts/buildbox").read_text(encoding="utf-8")
    require("required ? len == expected : len >= expected" in header,
            "length policy absent")
    require("!required && ret != -EPROBE_DEFER" in header,
            "error policy absent")
    require(test.count("KUNIT_CASE(") == 9, "KUnit inventory changed")
    for token in (".requires_calibration = true,",
                  "mt->conf->requires_calibration, PTR_ERR(cell)",
                  "MTK_SOC_THERMAL_KUNIT_TEST"):
        require(token in editor, f"editor token absent: {token}")
    for token in ("PARENT_SOURCE_STATE=cfb17989", "format-patch -2",
                  "synthetic_signoff=absent", "hardware_action=none",
                  "boot_candidate=false"):
        require(token in generator, f"generator token absent: {token}")
    for token in ("generate-mt6797-thermal-calibration-patches",
                  "fetch-mt6797-thermal-calibration-patches"):
        require(token in buildbox, f"Buildbox action absent: {token}")
    for body, label in ((editor, "editor"), (generator, "generator")):
        for forbidden in ("scp ", "rsync ", "/dev/mmc", "boot2"):
            require(forbidden not in body, f"{label} contains {forbidden}")
    print("validation=mt6797-thermal-generator-tool")
    print("kunit_cases=9")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
