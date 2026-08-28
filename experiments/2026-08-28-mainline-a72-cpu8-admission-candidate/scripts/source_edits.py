#!/usr/bin/env python3
"""Apply deterministic binding and DT edits for the CPU8 candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


PARENT_HASHES = {
    "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-binder.yaml":
        "1843b00a0510fe1ec8d4aefe8b0f870ad3d604b757d13836693863b33a79e248",
    "arch/arm64/boot/dts/mediatek/Makefile":
        "68da4601d3d8825643845f6294869ad2f3ed3400e40edca2c3dd0e84ba62577c",
    "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts":
        "08f8b007379e52daa441d8b48731f8cd4a0549a3c1d887791762db68320fdbd8",
    "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-a72-physical-source.dts":
        "faa265ee5ad2061ca212e0854c65790c6f6edeb471612d5eb688f847ee33b0bf",
    "arch/arm64/boot/dts/mediatek/mt6797.dtsi":
        "e83520a2abf511acf6ce6b32efb5a71ea4f8dc95fb05670a8dead1b021c25479",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "b03d12563fd90967bfa2a58d5b1581a7c600a6ffe310fd876bbe464d093c8aef",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"source path is not an exact file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"source hash changed: {relative}: {actual} != {expected}"
            )


def copy_template(template_root: Path, name: str, target: Path) -> None:
    source = template_root / name
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"template is unavailable: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def apply_binding(root: Path, templates: Path) -> None:
    copy_template(
        templates,
        "mediatek,mt6797-a72-admission-controller.yaml",
        root / "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-admission-controller.yaml",
    )


def apply_dts(root: Path, templates: Path) -> None:
    makefile = root / "arch/arm64/boot/dts/mediatek/Makefile"
    old = "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda-a72-physical-source.dtb\n"
    new = old + "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda-a72-admission.dtb\n"
    text = makefile.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit("candidate DT Makefile anchor changed")
    makefile.write_text(text.replace(old, new, 1), encoding="utf-8")
    copy_template(
        templates,
        "mt6797-gemini-pda-a72-admission.dts",
        root / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-a72-admission.dts",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--template-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("binding", "dts"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    templates = args.template_root.resolve()
    validate_parent(root)
    apply_binding(root, templates)
    if args.stage == "dts":
        apply_dts(root, templates)


if __name__ == "__main__":
    main()
