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
    contract["result"] == "patches-integrated-build-pending",
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
attempt = contract["buildbox_generation_attempt_1"]
require(
    attempt["repository_commit"] ==
    "a6353c01d5d2e26564d73c4d32f359f5acf8ce5b" and
    attempt["record"] ==
    "results/buildbox-generation-attempt1-20260828.txt" and
    sha256(EXPERIMENT / attempt["record"]) == attempt["record_sha256"],
    "first Buildbox generation attempt record",
)
require(
    attempt["source_stage_validations"] == "2-of-2-pass" and
    attempt["admitted_generated_patch_count"] == 0 and
    attempt["result"] == "fail-closed-style-corrected",
    "first Buildbox generation attempt result",
)
attempt = contract["buildbox_generation_attempt_2"]
require(
    attempt["repository_commit"] ==
    "bc63b46d770e9311840f28013c0d0859a54d9c49" and
    attempt["record"] ==
    "results/buildbox-generation-attempt2-20260828.txt" and
    sha256(EXPERIMENT / attempt["record"]) == attempt["record_sha256"],
    "second Buildbox generation attempt record",
)
require(
    attempt["source_stage_validations"] == "2-of-2-pass" and
    attempt["strict_production_patch"] == "pass" and
    attempt["admitted_generated_patch_count"] == 0 and
    attempt["result"] == "fail-closed-description-corrected",
    "second Buildbox generation attempt result",
)
generation = contract["buildbox_generation"]
require(
    generation["repository_commit"] ==
    "48c367ffb997dea5473f185645f746a75668989f" and
    generation["record"] == "results/buildbox-generation-20260828.txt" and
    sha256(EXPERIMENT / generation["record"]) == generation["record_sha256"],
    "successful Buildbox generation record",
)
require(
    generation["generated_patch_count"] == 2 and
    generation["source_stage_validations"] == "2-of-2-pass" and
    generation["strict_checkpatch"] == "pass" and
    generation["full_series_replay"] == "pass" and
    generation["result"] == "pass",
    "successful Buildbox generation result",
)
patch_names = {
    "0419": "0419-soc-mediatek-arm-CPU8-admission-after-live-service.patch",
    "0420": "0420-soc-mediatek-test-live-CPU8-admission-trigger.patch",
}
for number, name in patch_names.items():
    require(
        sha256(ROOT / "patches/v7.1.3" / name) ==
        generation["generated_patch_sha256"][number],
        f"integrated generated patch {number}",
    )

integration = contract["integration"]
require(
    integration["record"] == "results/canonical-integration-20260828.txt" and
    sha256(EXPERIMENT / integration["record"]) == integration["record_sha256"],
    "canonical integration record",
)
series_path = ROOT / "patches/series"
manifest_path = ROOT / "kernel/manifest.json"
config_path = ROOT / "configs/gemini-a72-admission-live-trigger-kunit.fragment"
require(
    sha256(series_path) == integration["series_sha256"] and
    len(series_path.read_text(encoding="utf-8").splitlines()) ==
    integration["series_entries"],
    "canonical series integration",
)
require(
    series_path.read_text(encoding="utf-8").splitlines()[-2:] ==
    [f"v7.1.3/{name}" for name in patch_names.values()],
    "canonical series tail",
)
require(
    sha256(manifest_path) == integration["manifest_sha256"] and
    sha256(config_path) == integration["config_fragment_sha256"],
    "manifest and isolated config integration",
)
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
profile = manifest["config"]["profiles"][integration["profile"]]
require(
    profile["base"] == "defconfig" and
    profile["patch_series"] == "patches/series" and
    profile["fragments"][-1] ==
    "configs/gemini-a72-admission-live-trigger-kunit.fragment",
    "isolated KUnit profile",
)
config = config_path.read_text(encoding="utf-8")
for token in (
    "CONFIG_KUNIT=y", "CONFIG_PSTORE_GEMINI_ADMISSION_TRACE=y",
    "CONFIG_PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST=y",
    "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",
    "CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y",
    "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST=y",
    "# CONFIG_HOTPLUG_SPLIT_STARTUP is not set",
    'CONFIG_LOCALVERSION="-gemini-a72-admission-live-kunit"',
):
    require(token in config, f"isolated config token {token}")
require(
    integration["series_entries"] == 412 and
    integration["profiles_checked"] == 155 and
    integration["manifest_series_mutations_rejected"] == 8 and
    integration["result"] == "pass",
    "integration invariant result",
)

for relative in (
    "README.md", "DESIGN.md", "contract.json", "scripts/source_edits.py",
    "scripts/validate_source.py", "scripts/generate-patches.py",
    "scripts/generate-on-buildbox",
    "results/local-definition-validation-20260828.txt",
    "results/buildbox-generation-attempt1-20260828.txt",
    "results/buildbox-generation-attempt2-20260828.txt",
    "results/buildbox-generation-20260828.txt",
    "results/canonical-integration-20260828.txt",
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
