#!/usr/bin/env python3
"""Validate the guarded pre-capture cleanup-label fix."""

from __future__ import annotations

import argparse
from pathlib import Path


MODE = "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"
RELATIVE = Path(
    "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    root = parser.parse_args().source_root.resolve()
    text = (root / RELATIVE).read_text(encoding="utf-8")
    probe = text.split(
        "mt6797_a72_physical_source_probe(struct platform_device *pdev)", 1
    )[1].split("static const struct of_device_id", 1)[0]
    guarded_label = (
        f"#ifdef {MODE}\n"
        "put_bigidvfs:\n"
        "#endif\n"
        "\tput_device(context.bigidvfs);\n"
        "put_clock:\n"
        "\tput_device(context.clock);\n"
        "put_platform:\n"
        "\tput_device(context.platform);\n"
        "free_snapshot:\n"
        "\tkvfree(snapshot);\n"
    )
    require(probe.count("goto put_bigidvfs;") == 2, "two pre-capture exits")
    require(probe.count("put_bigidvfs:") == 1, "one cleanup label")
    require(guarded_label in probe, "guarded cleanup release order")
    require(
        probe.index("gemini_protected_readback_ledger_checkpoint(1)")
        < probe.index("goto put_bigidvfs;")
        < probe.index("put_bigidvfs:"),
        "checkpoint exits reach the release label",
    )
    require(probe.count("mt6797_a72_physical_source_run(&context") == 1,
            "capture call count changed")
    require("cpu_up(" not in text and "cpu_down(" not in text,
            "CPU request added")
    print("validation=a72-physical-source-precapture-control-flow-fix")
    print(f"changed_files={RELATIVE}")
    print("added_cleanup_labels=1")
    print("hardware_actions_changed=false")
    print("result=pass")


if __name__ == "__main__":
    main()
