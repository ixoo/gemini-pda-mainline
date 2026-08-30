#!/usr/bin/env python3
"""Prove representative unsafe composed-DT mutations are rejected."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile


SCRIPT = Path(__file__).with_name("validate-composed-dtb.py")
SPEC = importlib.util.spec_from_file_location("composed_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
NODE = "/chosen/gemini-late-cpu-provenance"


def mutate(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serviceability-dtb", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    mutations = (
        ("missing-leaf", ["fdtput", "-r", "{path}", NODE]),
        ("wrong-compatible", ["fdtput", "-ts", "{path}", NODE, "compatible", "invalid"]),
        ("wrong-schema", ["fdtput", "-tu", "{path}", NODE, "schema-version", "2"]),
        ("wrong-targets", ["fdtput", "-tu", "{path}", NODE, "target-cpus", "8", "8"]),
        ("missing-digest", ["fdtput", "-d", "{path}", NODE, "expected-ikconfig-identity"]),
        ("extra-property", ["fdtput", "-ts", "{path}", NODE, "unexpected", "value"]),
        ("usb-disabled", ["fdtput", "-ts", "{path}", "/usb@11271000", "status", "disabled"]),
        ("clock-disabled", ["fdtput", "-ts", "{path}", "/dvfsp-clock-backend@1001a000", "status", "disabled"]),
        ("controller-changed", ["fdtput", "-ts", "{path}", "/a72-admission-controller", "compatible", "invalid"]),
        ("extra-node", ["fdtput", "-c", "{path}", "/unexpected"]),
    )
    accepted = 0
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-composed-dtb-mutations-") as directory:
        root = Path(directory)
        for name, template in mutations:
            candidate = root / f"{name}.dtb"
            shutil.copyfile(args.candidate, candidate)
            mutate([value.format(path=str(candidate)) for value in template])
            try:
                VALIDATOR.validate(args.serviceability_dtb, args.package_dtb,
                                   args.record_json, candidate, pin=False)
            except ValueError:
                rejected += 1
            else:
                accepted += 1
    if accepted or rejected != len(mutations):
        raise SystemExit(f"mutation rejection failed: accepted={accepted} rejected={rejected}")
    print("validation=provenance-serviceability-dtb-mutations")
    print(f"mutations_rejected={rejected}")
    print("mutations_accepted=0")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
