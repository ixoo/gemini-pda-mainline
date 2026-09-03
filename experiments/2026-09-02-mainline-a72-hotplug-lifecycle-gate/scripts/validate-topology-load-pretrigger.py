#!/usr/bin/env python3
"""Require a fresh pristine topology/load boot before its sole trigger."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "0c6dd91d31dd5ae3f9506006c824fbf4b2ea4ff714f0fb30194474a736d0d669"
PRIOR_MAINLINE_BOOT_IDS = {
    "c1bd9a56-919f-4ba1-8404-1287148b334a",
}
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("validate-topology-repeat-pretrigger.py")


def load_source():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise SystemExit("source topology-repeat pre-trigger validator changed")
    specification = importlib.util.spec_from_file_location(
        "topology_repeat_pretrigger", SOURCE
    )
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--deployment-summary", type=Path, required=True)
    args = parser.parse_args()
    source = load_source()
    try:
        deployment_boot_id = source.validate_deployment(
            args.deployment_summary.read_text(encoding="utf-8", errors="replace")
        )
        boot_id = source.validate_capture(
            args.capture.read_text(encoding="utf-8", errors="replace"),
            deployment_boot_id,
        )
        source.require(boot_id not in PRIOR_MAINLINE_BOOT_IDS, "previous-runtime-boot-id")
    except source.Rejected as error:
        print("pretrigger_classification=rejected")
        print(f"pretrigger_reason={error}")
        return 3
    print("pretrigger_classification=serviceable-armed-zero-execution")
    print("pretrigger_reason=exact-topology-load-identity-ready-pristine-fresh-contract")
    print(f"boot_id={boot_id}")
    print("arm64_late_profile=ready")
    print("arm64_proof_mask=absent")
    print("trigger_executions=0")
    print("cpu8_requests=0")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    print("prior_topology_repeat_boot_ids_rejected=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
