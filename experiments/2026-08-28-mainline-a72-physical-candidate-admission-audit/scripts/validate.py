#!/usr/bin/env python3
"""Validate the exact CPU8 physical-candidate admission audit."""

from __future__ import annotations

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
series = ROOT / "patches/series"
manifest = ROOT / "kernel/manifest.json"
require(len(series.read_text(encoding="utf-8").splitlines()) ==
        CONTRACT["canonical_series_entries"], "series entries")
require(sha256(series) == CONTRACT["canonical_series_sha256"], "series hash")
require(sha256(manifest) == CONTRACT["manifest_sha256"], "manifest hash")

direct = CONTRACT["direct_design"]
require(direct == {
    "binder_dt_enable": True,
    "late_add_cpu8": True,
    "safe": False,
    "reason": "unsourced-a36-and-ledger-watchdog-order-cycle",
}, "direct design rejection")
require(set(CONTRACT["external_production_callers"]) == {
    "publish_bootstrap", "membership_begin_up", "membership_publish_up",
    "add_cpu8",
}, "external caller inventory")
require(not any(CONTRACT["external_production_callers"].values()),
        "external callers remain absent")
require(CONTRACT["obsolete_a36_caller_assertions"] == [
    "da921x_page", "secure_sentinels_stable", "pstore_console_available",
    "watchdog_owned",
], "obsolete A36 assertions")
require(CONTRACT["required_order"] == [
    "exact-source-capture", "a34-bootstrap-publication",
    "owner-derived-cpu8-transaction", "p17-p18-publication",
    "one-add-cpu8", "retained-ledger-begin", "watchdog-takeover",
    "p27-first-mutation",
], "required order")
require(CONTRACT["selected_implementation"] == [
    "derived-membership-admission-compositor",
    "read-only-binder-ready-gate",
    "one-task-consumed-before-mutation-controller",
    "hardware-free-kunit-and-no-network-qemu",
    "separate-one-boot-physical-candidate",
], "selected implementation")
require(CONTRACT["model_cases"] == 6, "model cases")
require(CONTRACT["model_result"] == "pass", "model result")
require(CONTRACT["planned_generated_patches"] == 2, "planned patches")
require(CONTRACT["planned_derived_kunit_cases"] == 5,
        "planned derived KUnit cases")
require(CONTRACT["source_generator_execution"] ==
        "deferred-until-signed-pushed-clean-commit",
        "source generator execution")

receipt = EXP / "results/source-admission-audit-20260828.txt"
require(CONTRACT["source_receipt_sha256"] != "pending", "receipt hash pending")
require(sha256(receipt) == CONTRACT["source_receipt_sha256"], "receipt hash")
receipt_text = receipt.read_text(encoding="utf-8")
for token in (
    "A36_watchdog_owned_before_add_cpu=impossible",
    "A36_da921x_page_source=absent-no-PAGE_CON-read",
    "binder_entry=inside-add_cpu-MT6797-cpu_boot",
    "binder_recovery_order=ledger-begin-before-watchdog-takeover-before-P27",
    "direct_late_caller_safe=no",
    "controller=consumed-before-mutation-one-task-one-add_cpu8",
    "native_vm_build=none", "device_access=none", "cpu_request=none",
    "boot_candidate=false",
):
    require(token in receipt_text, f"receipt token: {token}")

local_validation = EXP / "results/local-definition-validation-20260828.txt"
require(CONTRACT["local_validation_sha256"] != "pending",
        "local validation hash pending")
require(sha256(local_validation) == CONTRACT["local_validation_sha256"],
        "local validation hash")
local_text = local_validation.read_text(encoding="utf-8")
for token in (
    "bash_syntax=pass", "shellcheck=pass", "python_syntax=pass",
    "model_validation=pass", "model_cases=6",
    "source_generator_execution=deferred-until-signed-pushed-clean-commit",
    "buildbox_kernel_build=none", "native_vm_build=none",
    "device_action=none", "cpu_request=none", "boot_candidate=false",
):
    require(token in local_text, f"local validation token: {token}")

readme = (EXP / "README.md").read_text(encoding="utf-8")
design = (EXP / "DESIGN.md").read_text(encoding="utf-8")
combined = readme + design + receipt_text + local_text
words = " ".join(combined.split())
for token in (
    "No direct caller can satisfy the current graph",
    "The obsolete A36 page/recovery assertions must no longer authorize anything",
    "consumed flag before the first owner mutation",
    "one synchronous `add_cpu(8)` call",
    "zero CPU9, CPU_OFF, or retry operations",
):
    require(token in words, f"documentation token: {token}")
require("/Users/" not in combined, "no personal absolute path")
require(CONTRACT["kernel_build"] is False, "no kernel build")
require(CONTRACT["device_action"] is False, "no device action")
require(CONTRACT["result"] ==
        "direct-caller-rejected-derived-admission-compositor-required",
        "result")

print("definition_validation=pass")
print("direct_late_caller=rejected")
print("selected_next=derived-membership-admission-compositor")
print("model_cases=6")
print("native_vm_build=none")
print("device_action=none")
