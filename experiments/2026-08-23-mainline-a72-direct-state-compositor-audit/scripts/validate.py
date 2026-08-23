#!/usr/bin/env python3
"""Validate the frozen A72 direct-state compositor source/lock audit."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/2026-08-23-mainline-a72-direct-state-compositor-audit"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


contract = json.loads((EXP / "contract.json").read_text())
readme = (EXP / "README.md").read_text()
design = (EXP / "DESIGN.md").read_text()
result = (EXP / "results/source-lock-audit-20260823.txt").read_text()
roadmap = (ROOT / "docs/ROADMAP.md").read_text()
index = (ROOT / "experiments/README.md").read_text()

require(contract["schema"] == 1, "unexpected schema")
require(contract["canonical_parent"].startswith("patches/v7.1.3/0336-"),
        "canonical parent is not patch 0336")
require(len(contract["source_files"]) == 6, "source identity inventory changed")
require(set(contract["existing_readers"]) ==
        {"da921x", "platform", "clock", "bigidvfs"},
        "reader inventory changed")

owner = contract["selected_owner"]
require(owner["hotplug_lock"] == "cpus_read_lock",
        "CPU-hotplug ownership changed")
require(owner["transition_lock"] == "a72_transition_lock",
        "A72 transition ownership changed")
require(owner["failure_output"] == "all-zero",
        "failure publication is not fail closed")

implementation = contract["first_implementation"]
require(implementation["default_off"] and
        implementation["hardware_free"] and
        implementation["injected_source"],
        "first implementation is not isolated and hardware free")
for field in ("a34_abi_change", "lifecycle_publication", "dt_enablement",
              "hardware_operation", "cpu_request", "device_action"):
    require(implementation[field] is False, f"forbidden scope opened: {field}")

for text in (readme, design):
    require("cpu_hotplug_lock (read)" in text or "CPU-hotplug read lock" in text,
            "hotplug lock order is missing")
    require("a72_transition_lock" in text, "A72 transition lock is missing")
    require("all-zero" in text, "zero-on-error rule is missing")
    require("A34" in text, "A34 separation is missing")

require("current_atomic_compositor=absent" in result,
        "negative source finding is missing")
require("result=confirmed-owner-contract" in result,
        "audit result is not confirmed")
require("Compose the validated readers" in roadmap,
        "Roadmap Gate 7 composition item is missing")
require("mainline A72 direct-state compositor audit" in index,
        "experiment index entry is missing")

print("validation=a72-direct-state-compositor-audit")
print("source_files=6")
print("reader_interfaces=4")
print("selected_outer_owner=cpu-hotplug-read-lock+a72-transition-lock")
print("hardware_operation=none")
print("cpu8_cpu9_admission=closed")
print("result=pass")
