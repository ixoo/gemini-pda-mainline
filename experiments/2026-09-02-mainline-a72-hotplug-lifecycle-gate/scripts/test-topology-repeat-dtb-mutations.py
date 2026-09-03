#!/usr/bin/env python3
"""Prove provenance, serviceability, and CPU-map mutations are rejected."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


VALIDATOR_SHA256 = "cd1b5f097c41760ae50607fdbfa646b823c98d368ebf0311fc47c6258055665a"
SCRIPT = Path(__file__).resolve()
VALIDATOR = SCRIPT.with_name("validate-topology-repeat-composed-dtb.py")
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
    if hashlib.sha256(VALIDATOR.read_bytes()).hexdigest() != VALIDATOR_SHA256:
        parser.error("topology-repeat DT validator changed")
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
        ("duplicate-cluster2-cpu", ["fdtput", "-tx", "{path}", "/cpus/cpu-map/cluster2/core1", "cpu", "3f"]),
        ("missing-cluster2-core1", ["fdtput", "-r", "{path}", "/cpus/cpu-map/cluster2/core1"]),
        ("extra-cluster", ["fdtput", "-c", "{path}", "/cpus/cpu-map/cluster3"]),
    )
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-topology-repeat-dtb-mutations-") as directory:
        root = Path(directory)
        for name, template in mutations:
            candidate = root / f"{name}.dtb"
            shutil.copyfile(args.candidate, candidate)
            mutate([value.format(path=str(candidate)) for value in template])
            completed = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--serviceability-dtb", str(args.serviceability_dtb),
                    "--package-dtb", str(args.package_dtb),
                    "--record-json", str(args.record_json),
                    "--candidate", str(candidate),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if completed.returncode:
                rejected += 1
    accepted = len(mutations) - rejected
    if accepted or rejected != len(mutations):
        raise SystemExit(
            f"mutation rejection failed: accepted={accepted} rejected={rejected}"
        )
    print("validation=a72-topology-repeat-dtb-mutations")
    print(f"mutations_rejected={rejected}")
    print("topology_mutations_rejected=3")
    print("mutations_accepted=0")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
