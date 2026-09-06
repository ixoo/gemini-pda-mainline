#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify EMI service-gate composition, refusal behavior and no-effect scope."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
sys.dont_write_bytecode = True
from support import HERE, ROOT, SPEC, digest, require, scratch


PREVIOUS = ROOT / "experiments" / "2026-09-06-mt6797-resource-layout-compile" / "src"
PREVIOUS_REMAP = ROOT / "experiments" / "2026-09-06-mt6797-remap-fields-compile" / "src"
PREVIOUS_EMI = ROOT / "experiments" / "2026-09-06-mt6797-emi-abi-compile" / "src"


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "emi_service_gate_patch", HERE / "scripts" / "generate-patch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    generated = load_generator().generate()
    patch_path = HERE / SPEC["patch"]
    require(generated == patch_path.read_bytes(), "patch reproduction differs")
    implementation = (HERE / "src" / "emi-service-gate.c").read_text()
    header = (HERE / "src" / "emi-service-gate.h").read_text()
    patch_text = patch_path.read_text()
    forbidden = ("EXPORT_SYMBOL", "module_init", "platform_driver", "arm_smccc",
                 "smc_call", "ioremap", "memremap", "readl", "writel",
                 "dma_map", "request_firmware", "request_irq", "regulator_",
                 "regmap", "spin_lock", "mutex_lock", "of_", "probe",
                 "initcall", "register")
    require(not any(token in implementation for token in forbidden),
            "effectful implementation token found")
    require(not any(token in header for token in forbidden),
            "effectful header token found")
    require("mt6797_emi_prepare(&gate->layout.region18" in implementation,
            "gate does not call predecessor EMI preparation")
    require("mt6797_emi_decode_result(raw)" in implementation,
            "gate does not call predecessor result decoder")
    require("mt6797_remap_encode_common(layout->start, 1, &expected_common)" in
            implementation and "MT6797_REMAP_COMMON" not in implementation,
            "remap helper was not composed without copied logic")
    require("+obj-y += emi-service-gate.o" in patch_text and
            "+obj-y += resource-layout.o" not in patch_text,
            "unexpected Kbuild change")
    require("image_binding_begin" not in patch_text,
            "active binding refusal changed")
    require(len(re.findall(r"\bmt6797_emi_service_gate_(?:init|apply)\s*\(",
                           implementation)) == 2,
            "gate API definitions do not have one implementation each")
    require("MT6797_EMI_SERVICE_GATE_ATTEMPTED" in implementation,
            "attempt-before-effect state is absent")

    report = {
        "patch_sha256": digest(generated),
        "patch_reproduction": "PASS",
        "named_series_path": SPEC["series_path"],
        "named_series_sha256": SPEC["series_sha256"],
        "named_series_inventory": SPEC["series_entries"],
        "named_series_identity_and_order": "PASS",
        "evidence_documents": SPEC["evidence_documents"],
        "evidence_document_identity": "PASS",
        "proposal_replay": "PENDING INTEGRATOR LINUX REPLAY",
        "kernel_build": "PENDING INTEGRATOR BUILD",
        "backend": "NOT ACCESSED",
        "hardware": "NOT ACCESSED",
        "runtime_caller": "NONE; gate is linked but unreferenced",
        "effect_api_scan": "PASS",
        "network": "NOT ACCESSED",
    }
    with scratch("verify") as work:
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Wconversion",
                 "-Wsign-conversion", "-pedantic", "-O1", "-g",
                 "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                 "-fno-omit-frame-pointer"]
        include = ["-I", str(HERE / "src"), "-I", str(PREVIOUS), "-I",
                   str(PREVIOUS_REMAP), "-I", str(PREVIOUS_EMI)]
        objects = []
        sources = [
            (HERE / "src" / "emi-service-gate.c", "emi-service-gate.o"),
            (PREVIOUS / "resource-layout.c", "resource-layout.o"),
            (PREVIOUS_EMI / "emi-abi.c", "emi-abi.o"),
            (PREVIOUS_REMAP / "remap-fields.c", "remap-fields.o"),
        ]
        for source, name in sources:
            output = work / name
            subprocess.run(["cc", *flags, *include, "-c", str(source),
                            "-o", str(output)], check=True, timeout=60)
            objects.append(output)
            if name == "emi-service-gate.o":
                undefined = subprocess.check_output(["nm", "-u", str(output)],
                                                     text=True)
                for symbol in ("mt6797_emi_prepare", "mt6797_emi_decode_result",
                               "mt6797_remap_encode_common"):
                    require(symbol in undefined,
                            "gate object does not reference predecessor: " + symbol)
                report["gate_undefined_predecessor_symbols"] = [
                    "mt6797_emi_prepare", "mt6797_emi_decode_result",
                    "mt6797_remap_encode_common"]
        binary = work / "emi-service-gate-test"
        subprocess.run(["cc", *flags, *include, *map(str, objects),
                        str(HERE / "src" / "emi-service-gate-test.c"),
                        "-o", str(binary)], check=True, timeout=60)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1")
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                timeout=90, env=env)
        require(result.returncode == 0 and not result.stderr,
                result.stdout + result.stderr)
        report["host_test"] = result.stdout
        report["predecessor_linkage"] = {
            "resource_layout": "PASS; separately compiled predecessor object",
            "emi_abi": "PASS; separately compiled predecessor object",
            "remap_fields": "PASS; separately compiled predecessor object",
        }
        report["test_inventory"] = {
            "valid_generation_boundaries": 2,
            "apply_ullong_max_cases": 1,
            "init_null_and_exact_alias_refusals": 6,
            "init_missing_callback_refusals": 1,
            "init_range_and_split_refusals": 10,
            "init_region_identity_selector_mismatch_refusals": 10,
            "init_common_field_refusals": 1,
            "remap_helper_erange_refusals": 1,
            "apply_null_empty_generation_refusals": 5,
            "apply_exact_alias_refusals": 1,
            "direct_attempted_refusals": 1,
            "permission_high_bit_refusals": 8,
            "callback_status_matrix_cases": 11,
            "successful_permission_boundary_apply_cases": 1,
            "terminal_repeat_refusals": 12,
            "source_copy_mutation_cases": 1,
            "self_consistent_clear_lower_bound_branch_cases": 1,
        }
        report["sanitizer_flags"] = flags
        report["compiler"] = subprocess.check_output(
            ["cc", "--version"], text=True).splitlines()[0]

        report["checkpatch"] = {
            "status": "PENDING INTEGRATOR",
            "reason": "Pinned Linux Checkpatch and Buildbox replay are integrator-owned.",
            "network": "NOT ACCESSED",
            "pinned_linux_checkpatch_sha256": SPEC["checkpatch_sha256"],
        }
    for source in (HERE / "scripts").glob("*.py"):
        ast.parse(source.read_text())
    report["source_hashes"] = {
        path.name: digest(path.read_bytes())
        for path in sorted((HERE / "src").iterdir())
    }
    report["limitations"] = [
        "Linux __KERNEL__ include branch and real arm64 object await Buildbox.",
        "Proposal replay and Buildbox require the integrator's clean pushed commit.",
        "The backend callback is an injected seam, not a secure-service implementation.",
        "Partial byte overlap and concurrent calls are caller preconditions.",
        "Copied descriptors and decoded success do not establish reservation, policy or firmware authority.",
        "No runtime caller, permission policy, MMIO, mapping, firmware or hardware path exists.",
    ]
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(143))
    main()
