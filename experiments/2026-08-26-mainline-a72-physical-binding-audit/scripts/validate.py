#!/usr/bin/env python3
"""Validate the exact CPU8 physical-binding audit."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


EXP = Path(__file__).resolve().parent.parent
ROOT = EXP.parents[1]
CONTRACT = json.loads((EXP / "contract.json").read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


require(CONTRACT["schema"] == 1, "schema")
require(CONTRACT["experiment"] == EXP.name, "experiment")
require(len((ROOT / "patches/series").read_text(encoding="utf-8").splitlines()) ==
        CONTRACT["canonical_series_entries"], "series entries")
require(sha256(ROOT / "patches/series") ==
        CONTRACT["canonical_series_sha256"], "series hash")
require(sha256(ROOT / "kernel/manifest.json") == CONTRACT["manifest_sha256"],
        "manifest hash")

callbacks = CONTRACT["callbacks"]
names = [entry["name"] for entry in callbacks]
require(len(callbacks) == 12 and len(set(names)) == 12, "12 unique callbacks")
require(names == [
    "checkpoint", "watchdog_arm", "p27_acquire", "p27_release",
    "provider_acquire", "provider_release", "isolation_clear",
    "sram_enable", "cpu_on", "online_wait", "ipi_proof", "dcm_update",
], "callback order")
require(dict(Counter(entry["class"] for entry in callbacks)) ==
        CONTRACT["class_counts"], "class counts")
require(CONTRACT["class_counts"] == {
    "reuse-existing-owner": 2,
    "extend-platform-owner": 4,
    "new-owner-api": 3,
    "lifecycle-bridge": 3,
}, "exact class inventory")
require(CONTRACT["implementation_order"] == [
    "exclusive-watchdog-takeover",
    "retained-transition-stage-ledger",
    "serialized-platform-effect-owner",
    "bigidvfs-sram-set-verify-owner",
    "psci-generic-hotplug-binder-and-one-late-caller",
    "complete-injected-kunit-and-no-network-qemu-proof",
    "one-decision-bearing-boot2-candidate",
], "implementation order")

receipt = EXP / "results/source-callback-map-20260826.txt"
require(CONTRACT["source_receipt_sha256"] != "pending", "receipt hash pending")
require(sha256(receipt) == CONTRACT["source_receipt_sha256"], "receipt hash")
receipt_text = receipt.read_text(encoding="utf-8")
for token in (
    "reuse-existing-owner=2", "extend-platform-owner=4",
    "new-owner-api=3", "lifecycle-bridge=3",
    "kernel_build=none", "native_vm_build=none", "device_access=none",
    "cpu_request=none", "partition_write=none",
):
    require(token in receipt_text, f"receipt token: {token}")

readme = (EXP / "README.md").read_text(encoding="utf-8")
design = (EXP / "DESIGN.md").read_text(encoding="utf-8")
readme_words = " ".join(readme.split())
design_words = " ".join(design.split())
for token in (
    "Only the DA921x provider acquire and release callbacks are directly reusable",
    "accepts only checkpoint 0 followed by checkpoint 1",
    "watchdog recovery-takeover",
):
    require(token in readme_words, f"README token: {token}")
for token in (
    "one-shot, one-CPU_ON", "No direct `psci_ops.cpu_on()`",
    "smp_call_function_single()", "never request CPU9",
):
    require(token in design_words, f"DESIGN token: {token}")
require("/Users/" not in readme + design + receipt_text,
        "no personal absolute path")
require(CONTRACT["kernel_build"] is False, "no kernel build")
require(CONTRACT["device_action"] is False, "no device action")

print("definition_validation=pass")
print("callbacks=12")
print("directly_reusable=2")
print("selected_next=exclusive-watchdog-takeover")
print("native_vm_build=none")
print("device_action=none")
