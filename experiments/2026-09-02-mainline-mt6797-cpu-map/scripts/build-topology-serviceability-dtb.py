#!/usr/bin/env python3
"""Add the package-proven MT6797 CPU map to the exact serviceability DTB."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


SERVICEABILITY_SHA256 = "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c"
PACKAGE_DTB_SHA256 = "51fefc506400df2da28998d3970fef8d09c21e2ece7d6d08d5ecef7370705e7c"
OUTPUT_SHA256 = "4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923"
VALIDATOR_SHA256 = "99495d59d047f312f416076b788014a64d267cbe4bf899a59d0120d5dd22d7c5"

CPU_NODES = (
    ("cpu@0", 0x37),
    ("cpu@1", 0x38),
    ("cpu@2", 0x39),
    ("cpu@3", 0x3A),
    ("cpu@100", 0x3B),
    ("cpu@101", 0x3C),
    ("cpu@102", 0x3D),
    ("cpu@103", 0x3E),
    ("cpu@200", 0x3F),
    ("cpu@201", 0x40),
)
CORES = (
    ("cluster0/core0", 0x37),
    ("cluster0/core1", 0x38),
    ("cluster0/core2", 0x39),
    ("cluster0/core3", 0x3A),
    ("cluster1/core0", 0x3B),
    ("cluster1/core1", 0x3C),
    ("cluster1/core2", 0x3D),
    ("cluster1/core3", 0x3E),
    ("cluster2/core0", 0x3F),
    ("cluster2/core1", 0x40),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(arguments: list[str], *, allow_failure: bool = False) -> str:
    completed = subprocess.run(
        arguments,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode and not allow_failure:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ValueError(f"command failed: {' '.join(arguments)}: {detail}")
    return completed.stdout.strip()


def load_validator(script: Path):
    if sha256(script) != VALIDATOR_SHA256:
        raise ValueError("CPU-map validator changed")
    specification = importlib.util.spec_from_file_location(
        "mt6797_cpu_map_validator", script
    )
    if specification is None or specification.loader is None:
        raise ValueError("cannot load CPU-map validator")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module.validate


def validate_base(serviceability: Path) -> None:
    failure = subprocess.run(
        ["fdtget", "-l", str(serviceability), "/cpus/cpu-map"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if failure.returncode == 0:
        raise ValueError("serviceability DTB unexpectedly contains cpu-map")
    dump = run(["fdtdump", str(serviceability)])
    handles = {int(value, 16) for value in re.findall(r"phandle = <0x([0-9a-fA-F]+)>", dump)}
    allocated = {handle for _, handle in CPU_NODES}
    collision = handles & allocated
    if collision:
        raise ValueError(f"CPU phandle allocation collides: {sorted(collision)!r}")
    for node, _ in CPU_NODES:
        path = f"/cpus/{node}"
        existing = subprocess.run(
            ["fdtget", "-tx", str(serviceability), path, "phandle"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if existing.returncode == 0:
            raise ValueError(f"{path} unexpectedly has a phandle")


def add_map(tree: Path) -> None:
    for node, handle in CPU_NODES:
        run(["fdtput", "-tx", str(tree), f"/cpus/{node}", "phandle", f"{handle:x}"])
    # fdtput prepends nodes, so reverse creation preserves canonical order.
    for core, _ in reversed(CORES):
        run(["fdtput", "-c", "-p", str(tree), f"/cpus/cpu-map/{core}"])
    for core, handle in CORES:
        run(["fdtput", "-tx", str(tree), f"/cpus/cpu-map/{core}", "cpu", f"{handle:x}"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serviceability-dtb", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.serviceability_dtb, args.package_dtb):
        if not path.is_file() or path.is_symlink():
            parser.error(f"required input is missing or unsafe: {path}")
    if args.output.exists() or args.output.is_symlink():
        parser.error("refusing to overwrite output")
    if sha256(args.serviceability_dtb) != SERVICEABILITY_SHA256:
        parser.error("serviceability DTB identity changed")
    if sha256(args.package_dtb) != PACKAGE_DTB_SHA256:
        parser.error("package DTB identity changed")

    script = Path(__file__).with_name("validate-cpu-map.py")
    try:
        validate = load_validator(script)
        validate(args.package_dtb)
        validate_base(args.serviceability_dtb)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".mt6797-cpu-map.", dir=str(args.output.parent)
        ) as directory:
            result = Path(directory) / "topology-serviceability.dtb"
            shutil.copyfile(args.serviceability_dtb, result)
            add_map(result)
            validate(result)
            actual = sha256(result)
            if actual != OUTPUT_SHA256:
                raise ValueError(f"output identity changed: {actual}")
            os.replace(result, args.output)
        os.chmod(args.output, 0o600)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print("validation=mt6797-topology-serviceability-composition")
    print(f"serviceability_dtb_sha256={SERVICEABILITY_SHA256}")
    print(f"package_dtb_sha256={PACKAGE_DTB_SHA256}")
    print(f"output_dtb_sha256={OUTPUT_SHA256}")
    print("clusters=0-3,4-7,8-9")
    print("non_topology_serviceability_transform=unchanged")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
