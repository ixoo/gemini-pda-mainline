#!/usr/bin/env python3
"""Validate the repository-side durable admission-trace definition."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parents[1]
SCRIPTS = EXPERIMENT / "scripts"
TEMPLATES = EXPERIMENT / "templates"
ENTRY = (
    "====0.000000-D\n"
    "GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
    "kind=entry slot=2\n"
)
TERMINALS = tuple(
    "====0.000000-D\n"
    "GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "
    f"kind={kind} slot=3\n"
    for kind in ("zero-source-register", "zero-derive", "zero-publish")
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
require(contract["schema"] == 1, "contract schema")
require(contract["prepared_source_state"] ==
        "6fcc8878d91c8c0c34fc8b5591a98bc8fcf7de927847690a8ecb55207b33e6a4",
        "exact post-0414 source state")
require(contract["prepared_source_integrity"] ==
        "79523b2d2e61aafee04e3ced7e26b6e2771ced2f477bdb0508b5068e96971853",
        "exact post-0414 source integrity")
require(contract["parent_patch"] ==
        "0414-arm64-dts-mediatek-add-Gemini-CPU8-admission-candidate.patch",
        "exact parent patch")
require(sha256(ROOT / "patches/v7.1.3" / contract["parent_patch"]) ==
        contract["parent_patch_sha256"], "parent patch checksum")
require(contract["planned_patches"] == 4, "four logical patches")
require(contract["entry_slot"] == 2 and
        contract["entry_address"] == "0x44411000", "exact entry slot")
require(contract["terminal_slot"] == 3 and
        contract["terminal_address"] == "0x44412000", "exact terminal slot")
require(contract["maximum_trace_record_writes"] == 2,
        "two retained writes maximum")
require(contract["zero_request_outcomes"] == 3,
        "three zero-request outcomes")
require(contract["cpu8_request_maximum"] == 1 and
        contract["cpu9_request_paths"] == 0 and
        contract["cpu_off_paths"] == 0 and contract["retry_paths"] == 0,
        "bounded CPU effect contract")
require(contract["normal_ramoops_registration"] is False,
        "transition ledger continues to bypass normal ramoops")
require(contract["native_vm_build"] is False and
        contract["device_action"] is False and
        contract["boot_candidate"] is False,
        "hardware-free definition")
require(contract["result"] == "hardware-free-definition",
        "definition-only result")
definition = contract["definition_validation"]
require(definition["record"] ==
        "results/local-definition-validation-20260828.txt" and
        sha256(EXPERIMENT / definition["record"]) == definition["record_sha256"],
        "definition validation record")
require(definition["mutation_checks"] == "pass" and
        definition["result"] == "pass", "definition validation result")
attempt = contract["buildbox_generation_attempt_1"]
require(attempt["repository_commit"] ==
        "50a62a43c599fccf83d7d4de9e9d23dce24f6332" and
        attempt["record"] ==
        "results/buildbox-generation-attempt1-20260828.txt" and
        sha256(EXPERIMENT / attempt["record"]) == attempt["record_sha256"],
        "first Buildbox generation attempt record")
require(attempt["generated_patch_count"] == 0 and
        attempt["result"] == "fail-closed-definition-corrected",
        "first Buildbox generation fail-closed result")
attempt = contract["buildbox_generation_attempt_2"]
require(attempt["repository_commit"] ==
        "2a43d27860ec91f3eb8826461ce087d37e67c0ad" and
        attempt["record"] ==
        "results/buildbox-generation-attempt2-20260828.txt" and
        sha256(EXPERIMENT / attempt["record"]) == attempt["record_sha256"],
        "second Buildbox generation attempt record")
require(attempt["generated_patch_count"] == 0 and
        attempt["result"] == "fail-closed-style-corrected",
        "second Buildbox generation fail-closed result")
attempt = contract["buildbox_generation_attempt_3"]
require(attempt["repository_commit"] ==
        "332c143dd4a2b8ba34a6ebcae984f4e1afa946c1" and
        attempt["record"] ==
        "results/buildbox-generation-attempt3-20260828.txt" and
        sha256(EXPERIMENT / attempt["record"]) == attempt["record_sha256"],
        "third Buildbox generation attempt record")
require(attempt["generated_patch_count"] == 0 and
        attempt["result"] == "fail-closed-alignment-corrected",
        "third Buildbox generation fail-closed result")

for relative in (
    "README.md", "DESIGN.md", "contract.json",
    "templates/fs/pstore/gemini_admission_trace.c",
    "templates/fs/pstore/gemini_admission_trace_internal.h",
    "templates/fs/pstore/gemini_admission_trace_test.c",
    "templates/include/linux/gemini_admission_trace.h",
    "scripts/source_edits.py", "scripts/validate_source.py",
    "scripts/generate-patches.py", "scripts/generate-on-buildbox",
):
    path = EXPERIMENT / relative
    require(path.is_file() and not path.is_symlink(), f"exact file {relative}")

design = (EXPERIMENT / "DESIGN.md").read_text(encoding="utf-8")
readme = (EXPERIMENT / "README.md").read_text(encoding="utf-8")
production = (
    TEMPLATES / "fs/pstore/gemini_admission_trace.c"
).read_text(encoding="utf-8")
test = (
    TEMPLATES / "fs/pstore/gemini_admission_trace_test.c"
).read_text(encoding="utf-8")
for record in (ENTRY, *TERMINALS):
    require(record.strip() in design, f"design exact record {record.splitlines()[-1]}")
    kind = record.split("kind=", 1)[1].strip()
    for source_name, source in (("production", production), ("test", test)):
        require('"====0.000000-D\\n"' in source and
                '"GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A "'
                in source and f'"kind={kind}\\n"' in source,
                f"{source_name} record {record.splitlines()[-1]}")
require("record 1" in design and "record 2" in design and "record 3" in design,
        "disjoint retained ownership")
require("payload" in design and "readback" in design and
        "never clears, repairs, retries, or overwrites" in readme,
        "retained write policy")
for forbidden in (
    "add_cpu(", "cpu_up(", "cpu_down(", "cpu_off(", "kernel_restart(",
    "orderly_reboot(", "orderly_poweroff(", "kernel_power_off(",
    "request_firmware", "filp_open", "blkdev",
):
    require(forbidden not in production.lower(),
            f"trace implementation excludes {forbidden}")

source_edits_path = SCRIPTS / "source_edits.py"
spec = importlib.util.spec_from_file_location("durable_trace_source_edits",
                                              source_edits_path)
require(spec is not None and spec.loader is not None, "load source editor")
source_edits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_edits)
require(source_edits.PARENT_HASHES == contract["parent_hashes"],
        "source editor parent hashes match contract")

with tempfile.TemporaryDirectory(prefix="admission-trace-validation-") as name:
    path = Path(name) / "anchor.txt"
    path.write_text("anchor\nanchor\n", encoding="utf-8")
    rejected = False
    try:
        source_edits.replace_once(path, "anchor", "replacement")
    except SystemExit:
        rejected = True
    require(rejected and path.read_text(encoding="utf-8") == "anchor\nanchor\n",
            "duplicate source anchor mutation is rejected unchanged")

generator = (SCRIPTS / "generate-patches.py").read_text(encoding="utf-8")
for patch in (
    "0415-pstore-add-Gemini-CPU8-admission-trace.patch",
    "0416-pstore-test-Gemini-CPU8-admission-trace.patch",
    "0417-soc-mediatek-retain-CPU8-admission-entry-and-rejections.patch",
    "0418-soc-mediatek-test-durable-CPU8-admission-trace.patch",
):
    require(generator.count(patch) == 1, f"one generated patch {patch}")
require("git\", \"apply\", \"--check" in generator,
        "generated series is replay-checked")
require("scripts/checkpatch.pl" in generator, "strict kernel patch style check")
require("MISSING_SIGN_OFF,FILE_PATH_CHANGES,SPLIT_STRING" in generator,
        "only exact-wire split strings extend normal style exceptions")

buildbox = (SCRIPTS / "generate-on-buildbox").read_text(encoding="utf-8")
for marker in (
    contract["prepared_source_state"], contract["prepared_source_integrity"],
    contract["parent_patch"], contract["parent_patch_sha256"],
    "/workspace/gemini-pda/src/linux-7.1.3-series-source",
):
    require(marker in buildbox, f"Buildbox gate {marker}")
require("source-tree-integrity\" verify" in buildbox,
        "Buildbox source integrity verification")

for script in (
    SCRIPTS / "source_edits.py", SCRIPTS / "validate_source.py",
    SCRIPTS / "generate-patches.py", SCRIPTS / "validate.py",
):
    ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
subprocess.run(["bash", "-n", str(SCRIPTS / "generate-on-buildbox")], check=True)

print("validation=a72-admission-durable-trace-definition")
print("prepared_source=exact-post-0414")
print("planned_patches=4")
print("entry_slot=2")
print("terminal_slot=3")
print("maximum_trace_record_writes=2")
print("zero_request_outcomes=3")
print("cpu8_request_maximum=1")
print("cpu9_request_paths=0")
print("cpu_off_paths=0")
print("retry_paths=0")
print("mutation_checks=pass")
print("native_vm_build=none")
print("device_action=none")
print("boot_candidate=false")
print("result=pass")
