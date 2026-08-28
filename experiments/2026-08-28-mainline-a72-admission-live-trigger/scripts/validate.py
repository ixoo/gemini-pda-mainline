#!/usr/bin/env python3
"""Validate the repository-side admission live-trigger definition."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parents[1]
SCRIPTS = EXPERIMENT / "scripts"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
require(contract["schema"] == 1, "contract schema")
require(
    contract["prepared_source_state"] ==
    "3d5c7e6572d06e50cf7db20ceed9e702780be5549f41d58904d1eb76dfa01bea",
    "exact post-0418 source state",
)
require(
    contract["prepared_source_integrity"] ==
    "4f067fb09248e1d0f72fbe1446d8374e7445c514010090d630483db27497861b",
    "exact post-0418 source integrity",
)
require(
    contract["parent_patch"] ==
    "0418-soc-mediatek-test-durable-CPU8-admission-trace.patch",
    "exact parent patch",
)
require(
    sha256(ROOT / "patches/v7.1.3" / contract["parent_patch"]) ==
    contract["parent_patch_sha256"],
    "parent patch checksum",
)
require(contract["planned_patches"] == 2, "two logical patches")
require(
    contract["trigger_token"] == "run-a72-admission-20260828-a\n",
    "exact trigger bytes",
)
require(
    contract["trigger_group"] == "gemini_admission" and
    contract["trigger_attribute"] == "trigger" and
    contract["status_attribute"] == "status" and
    contract["trigger_mode"] == "0200-root-only",
    "exact sysfs interface",
)
require(
    contract["probe_supplier_resolution"] is False and
    contract["automatic_probe_action"] is False,
    "dormant probe",
)
require(
    contract["trigger_execution_maximum"] == 1 and
    contract["admission_core_maximum"] == 1 and
    contract["cpu8_request_maximum"] == 1 and
    contract["cpu9_request_paths"] == 0 and
    contract["cpu_off_paths"] == 0 and contract["retry_paths"] == 0,
    "bounded effect contract",
)
require(
    contract["retained_records_primary_evidence"] is False and
    contract["pretrigger_live_frame_required"] is True,
    "live evidence is primary",
)
require(
    contract["native_vm_build"] is False and
    contract["device_action"] is False and
    contract["boot_candidate"] is False and
    contract["result"] == "definition-ready",
    "hardware-free definition state",
)
definition = contract["definition_validation"]
require(
    definition["record"] ==
    "results/local-definition-validation-20260828.txt" and
    sha256(EXPERIMENT / definition["record"]) ==
    definition["record_sha256"],
    "definition validation record",
)
require(
    definition["python_syntax"] == "pass" and
    definition["bash_syntax"] == "pass" and
    definition["git_diff_check"] == "pass" and
    definition["result"] == "pass",
    "definition validation result",
)

for relative in (
    "README.md", "DESIGN.md", "contract.json", "scripts/source_edits.py",
    "scripts/validate_source.py", "scripts/generate-patches.py",
    "scripts/generate-on-buildbox",
    "results/local-definition-validation-20260828.txt",
):
    path = EXPERIMENT / relative
    require(path.is_file() and not path.is_symlink(), f"exact file {relative}")

for relative in ("source_edits.py", "validate_source.py", "generate-patches.py"):
    path = SCRIPTS / relative
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

result = subprocess.run(
    ["bash", "-n", str(SCRIPTS / "generate-on-buildbox")],
    check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
require(result.returncode == 0, "Buildbox entry-point syntax")

spec = importlib.util.spec_from_file_location(
    "admission_live_source_edits", SCRIPTS / "source_edits.py"
)
require(spec is not None and spec.loader is not None, "load source editor")
source_edits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_edits)
require(
    source_edits.PARENT_HASHES == contract["parent_hashes"],
    "source editor hashes match contract",
)

design = (EXPERIMENT / "DESIGN.md").read_text(encoding="utf-8")
readme = (EXPERIMENT / "README.md").read_text(encoding="utf-8")
editor = (SCRIPTS / "source_edits.py").read_text(encoding="utf-8")
validator = (SCRIPTS / "validate_source.py").read_text(encoding="utf-8")
for token in (
    "run-a72-admission-20260828-a",
    "atomic_cmpxchg(&state->consumed, 0, 1)",
    "ret = ops->execute(context)",
    "smp_store_release(&state->complete, true)",
    "static DEVICE_ATTR_WO(trigger);",
    "static DEVICE_ATTR_RO(status);",
    '.name = "gemini_admission"',
    "CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER",
):
    require(token in editor, f"source edit contract {token}")
for token in (
    "automatic_probe_action=0", "trigger_execution_maximum=1",
    "admission_core_maximum=1", "cpu8_request_maximum=1",
    "cpu9_request_paths=0", "cpu_off_paths=0", "retry_paths=0",
):
    require(token in validator, f"source validation marker {token}")
require(
    "pre-trigger frame" in readme and "Retained records are corroborating" in readme,
    "primary live evidence policy",
)
require(
    "Screen color and reboot timing are contextual observations only" in design,
    "screen/reboot caution",
)
for forbidden in (
    "CPU9 requests: at most", "retry paths: at most",
):
    require(forbidden not in readme + design, f"forbidden policy {forbidden}")

generator = (SCRIPTS / "generate-on-buildbox").read_text(encoding="utf-8")
for token in (
    contract["prepared_source_state"], contract["prepared_source_integrity"],
    contract["parent_patch"], contract["parent_patch_sha256"],
    "generated_patch_count=2", "boot_candidate=false",
):
    require(token in generator, f"Buildbox pin {token}")

print("validation=gemini-a72-admission-live-trigger-definition")
print("planned_patches=2")
print("automatic_probe_action=0")
print("trigger_execution_maximum=1")
print("admission_core_maximum=1")
print("cpu8_request_maximum=1")
print("cpu9_request_paths=0")
print("cpu_off_paths=0")
print("retry_paths=0")
print("native_vm_build=none")
print("device_action=none")
print("boot_candidate=false")
print("result=pass")
