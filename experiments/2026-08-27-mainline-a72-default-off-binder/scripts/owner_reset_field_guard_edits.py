#!/usr/bin/env python3
"""Keep late-startup-only online fields out of the owner KUnit reset."""

from __future__ import annotations

import argparse
from pathlib import Path


SOURCE = Path("arch/arm64/kernel/late_cpu_startup.c")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / SOURCE
    require(path.is_file() and not path.is_symlink(),
            "startup source absent or unsafe")
    text = path.read_text(encoding="utf-8")
    old = (
        "\tlate_startup.stuck_interlock = false;\n"
        "\tlate_startup.test_online_cpu = 0;\n"
        "\tlate_startup.test_online = false;\n"
        "\treinit_completion(&late_startup.published);\n"
    )
    new = (
        "\tlate_startup.stuck_interlock = false;\n"
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST\n"
        "\tlate_startup.test_online_cpu = 0;\n"
        "\tlate_startup.test_online = false;\n"
        "#endif\n"
        "\treinit_completion(&late_startup.published);\n"
    )
    require(text.count(old) == 1, "online reset field anchor count changed")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
