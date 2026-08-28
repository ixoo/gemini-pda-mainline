#!/usr/bin/env python3
"""Validate the durable CPU8 production-candidate definition."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
require(contract["schema"] == 1, "contract schema")
require(contract["experiment"] == EXPERIMENT.name, "experiment identity")
series = ROOT / "patches/series"
require(len(series.read_text(encoding="utf-8").splitlines()) ==
        contract["parent_series_entries"], "parent series entries")
require(sha256(series) == contract["parent_series_sha256"],
        "parent series checksum")
parent_patch = ROOT / "patches/v7.1.3" / contract["parent_patch"]
require(sha256(parent_patch) == contract["parent_patch_sha256"],
        "parent patch checksum")

for section in ("hardware_free_build", "hardware_free_kunit"):
    evidence = contract[section]
    record = (EXPERIMENT / evidence["record"]).resolve()
    require(record.is_file() and not record.is_symlink(),
            f"{section} record")
    require(sha256(record) == evidence["record_sha256"] and
            evidence["result"] == "pass", f"{section} evidence")
kunit = contract["hardware_free_kunit"]
require(kunit["suites"] == 2 and kunit["tests"] == 12 and
        kunit["failed"] == 0 and kunit["skipped"] == 0 and
        kunit["physical_cpu_requests"] == 0,
        "hardware-free KUnit scope")

production = contract["production_profile"]
manifest_path = ROOT / "kernel/manifest.json"
config_path = ROOT / production["fragment"]
require(sha256(manifest_path) == production["manifest_sha256"],
        "manifest checksum")
require(sha256(config_path) == production["fragment_sha256"],
        "production fragment checksum")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
profiles = manifest["config"]["profiles"]
require(len(profiles) == production["profiles_checked"], "profile count")
profile = profiles[production["name"]]
require(profile["base"] == "defconfig" and
        profile["patch_series"] == "patches/series" and
        profile["fragments"][-1] == production["fragment"],
        "production profile definition")

definition = contract["definition_validation"]
definition_record = EXPERIMENT / definition["record"]
require(sha256(definition_record) == definition["record_sha256"] and
        definition["result"] == "pass", "definition validation record")

for section in ("production_build", "candidate", "offline_gates"):
    evidence = contract[section]
    key = "record" if section != "candidate" else "validation_record"
    hash_key = "record_sha256" if section != "candidate" else "validation_record_sha256"
    record = EXPERIMENT / evidence[key]
    require(record.is_file() and not record.is_symlink(), f"{section} record")
    require(sha256(record) == evidence[hash_key] and evidence["result"] == "pass",
            f"{section} evidence")
build = contract["production_build"]
require(build["repository_commit"] == "eb87d46ae9d58df1ff336751103745d58eed59fe" and
        build["backend"] == "buildbox" and build["native_vm_build"] is False,
        "production Buildbox identity")
candidate = contract["candidate"]
require(candidate["raw_size"] == 6_934_528 and
        candidate["raw_sha256"] ==
        "ed6fc5294f5677ed1895bf1157649330c91dd1f6051a6677f2d26972915cd185" and
        candidate["padded_size"] == 16_777_216 and
        candidate["padded_sha256"] ==
        "60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1" and
        candidate["lk_gates"] == 32, "exact candidate identity")
offline = contract["offline_gates"]
require(offline["admission_trace_mutation_tests"] == 10 and
        offline["recovery_decision_map_tests"] == 7 and
        offline["installer_derivation"] == "pass", "offline gate scope")
live_correction = contract["live_preflight_tooling_correction"]
live_record = EXPERIMENT / live_correction["record"]
require(sha256(live_record) == live_correction["record_sha256"] and
        live_correction["device_access"] == "read-only" and
        live_correction["device_storage_write"] is False and
        live_correction["retained_ram_write"] is False,
        "live preflight tooling correction")
live = contract["live_preflight"]
live_record = EXPERIMENT / live["record"]
require(sha256(live_record) == live["record_sha256"] and
        live["boot2_predecessor_sha256"] ==
        contract["expected_boot2_predecessor_sha256"] and
        live["transition_ledger_state"] == "logical-empty" and
        live["entry_trace_state"] == "logical-empty" and
        live["terminal_trace_state"] == "logical-empty" and
        live["device_storage_write"] is False and
        live["retained_ram_write"] is False and
        live["result"] == "pass-ready-for-guarded-install",
        "live preflight pass")
deployment = contract["deployment"]
deployment_record = EXPERIMENT / deployment["record"]
require(sha256(deployment_record) == deployment["record_sha256"] and
        deployment["target_logical_name"] == "boot2" and
        deployment["target"] != deployment["active_root"] and
        deployment["predecessor_sha256"] ==
        contract["expected_boot2_predecessor_sha256"] and
        deployment["candidate_sha256"] == candidate["padded_sha256"] and
        deployment["readback_sha256"] == candidate["padded_sha256"] and
        deployment["fresh_predecessor_backup"] is False and
        deployment["shutdown"] == "confirmed-unreachable-and-tcp-closed" and
        deployment["reboot"] is False and deployment["result"] == "pass",
        "guarded boot2 deployment")
runtime = contract["runtime_attempt_1"]
runtime_record = EXPERIMENT / runtime["record"]
require(sha256(runtime_record) == runtime["record_sha256"] and
        runtime["boot_cycle"] == "confirmed-changed-id" and
        runtime["console_visible"] is False and
        runtime["mainline_usb_observed"] is False and
        runtime["pstore_files"] == 0 and
        runtime["transition_ledger_state"] == "logical-empty" and
        runtime["entry_trace_state"] == "logical-empty" and
        runtime["terminal_trace_state"] == "logical-empty" and
        runtime["classification"] == "pre-controller-or-retention-failure" and
        runtime["candidate_disposition"] == "retired-no-repeat" and
        runtime["result"] == "pass", "runtime attempt 1")

config = config_path.read_text(encoding="utf-8")
for token in (
    "CONFIG_MODULES=y",
    "CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y",
    "CONFIG_PSTORE_GEMINI_ADMISSION_TRACE=y",
    "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y",
    "CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y",
    "CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION=y",
    "CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR=y",
    "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER=y",
    "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
    "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",
    "# CONFIG_KUNIT is not set",
    "# CONFIG_PSTORE_GEMINI_ADMISSION_TRACE_KUNIT_TEST is not set",
    "# CONFIG_HOTPLUG_SPLIT_STARTUP is not set",
    'CONFIG_LOCALVERSION="-gemini-a72-admission-trace"',
):
    require(config.count(token + "\n") == 1, f"config token {token}")
for forbidden in (
    "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
    "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",
    "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER=y",
    "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER=y",
    "CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER=y",
):
    require(forbidden not in config, f"conflicting retained owner {forbidden}")

require(contract["target_cpu"] == 8 and contract["excluded_cpu"] == 9,
        "CPU scope")
require(contract["physical_boots_budget"] == 1 and
        contract["physical_boots_used"] == 1, "one consumed boot budget")
require(contract["entry_slot"] == 2 and
        contract["entry_address"] == "0x44411000" and
        contract["terminal_slot"] == 3 and
        contract["terminal_address"] == "0x44412000",
        "retained slot identity")
require(contract["maximum_trace_record_writes"] == 2 and
        contract["maximum_cpu8_requests"] == 1 and
        contract["cpu9_request_paths"] == 0 and
        contract["cpu_off_paths"] == 0 and
        contract["retry_paths"] == 0, "bounded effects")
require(contract["fresh_predecessor_backup"] is False and
        contract["native_vm_build"] is False and
        contract["device_access"] ==
        "guarded-deployment-and-read-only-runtime-recovery" and
        contract["device_action"] is True and
        contract["boot_candidate"] is False,
        "retired-candidate safety state")
require(contract["result"] ==
        "attempt-1-pre-controller-or-retention-candidate-retired",
        "retired-candidate result")

for relative in (
    "README.md", "DESIGN.md", "contract.json", "scripts/validate.py",
    "scripts/build-candidate.sh", "scripts/validate-candidate.py",
    "scripts/validate-admission-trace.py",
    "scripts/validate-transition-ledger.py", "scripts/classify-recovery.py",
    "scripts/install-boot2.sh", "scripts/collect-recovery.sh",
):
    path = EXPERIMENT / relative
    require(path.is_file() and not path.is_symlink(), f"exact file {relative}")
ast.parse((EXPERIMENT / "scripts/validate.py").read_text(encoding="utf-8"))
subprocess.run([str(ROOT / "scripts/validate-manifest-series")], check=True,
               stdout=subprocess.DEVNULL)
subprocess.run([str(ROOT / "scripts/test-manifest-series-invariant")],
               check=True, stdout=subprocess.DEVNULL)

print("validation=a72-admission-durable-candidate-retired")
print("parent_series_entries=410")
print("profiles_checked=154")
print("hardware_free_suites=2")
print("hardware_free_tests=12")
print("entry_slot=2")
print("terminal_slot=3")
print("maximum_trace_record_writes=2")
print("maximum_cpu8_requests=1")
print("cpu9_request_paths=0")
print("cpu_off_paths=0")
print("retry_paths=0")
print("native_vm_build=none")
print("device_action=guarded-boot2-write")
print("shutdown=confirmed-unreachable-and-tcp-closed")
print("physical_boots_used=1")
print("runtime_classification=pre-controller-or-retention-failure")
print("boot_candidate=false")
print("result=pass")
