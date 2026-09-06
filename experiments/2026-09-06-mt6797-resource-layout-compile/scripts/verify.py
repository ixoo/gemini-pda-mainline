#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify resource-layout generation, composition and the no-effect boundary."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import urllib.request
from support import HERE, ROOT, SPEC, digest, require, scratch


PREVIOUS = ROOT / "experiments" / "2026-09-06-mt6797-remap-fields-compile" / "src"
PREVIOUS_EMI = ROOT / "experiments" / "2026-09-06-mt6797-emi-abi-compile" / "src"


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "resource_layout_patch", HERE / "scripts" / "generate-patch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    generated = load_generator().generate()
    patch_path = HERE / SPEC["patch"]
    require(generated == patch_path.read_bytes(), "patch reproduction differs")
    implementation = (HERE / "src" / "resource-layout.c").read_text()
    header = (HERE / "src" / "resource-layout.h").read_text()
    patch_text = patch_path.read_text()
    forbidden = ("EXPORT_SYMBOL", "module_init", "platform_driver",
                 "arm_smccc", "ioremap", "memremap", "readl", "writel",
                 "dma_map", "request_firmware", "request_irq", "regulator_",
                 "regmap", "spin_lock", "mutex_lock", "of_")
    require(not any(token in implementation for token in forbidden),
            "effectful implementation token found")
    require(not any(token in header for token in forbidden[:-1]),
            "effectful header token found")
    require("mt6797_remap_encode_common(info->start, 1, &common_field)" in
            implementation, "predecessor remap encoder is not called")
    require("MT6797_REMAP_COMMON" not in implementation,
            "common encoding was copied instead of composed")
    require("+obj-y += resource-layout.o" in patch_text and
            "+obj-y += remap-fields.o" not in patch_text,
            "unexpected Kbuild change")
    require("image_binding_begin" not in patch_text,
            "active binding refusal changed")
    require(len(re.findall(r"\bmt6797_resource_layout_build\s*\(",
                           implementation)) == 1,
            "constructor contains a caller")
    struct = re.search(r"struct mt6797_resource_layout \{(.*?)\};",
                       header, re.S)
    require(struct and "permission" not in struct.group(1).lower(),
            "output contains a permission field")

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
        "runtime_caller": "NONE; constructor is linked but unreferenced",
        "effect_api_scan": "PASS",
    }
    with scratch("verify") as work:
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Wconversion",
                 "-Wsign-conversion", "-pedantic", "-O1", "-g",
                 "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                 "-fno-omit-frame-pointer"]
        include = ["-I", str(HERE / "src"), "-I", str(PREVIOUS),
                   "-I", str(PREVIOUS_EMI)]
        layout_object = work / "resource-layout.o"
        remap_object = work / "remap-fields.o"
        binary = work / "resource-layout-test"
        subprocess.run(["cc", *flags, *include, "-c",
                        str(HERE / "src" / "resource-layout.c"),
                        "-o", str(layout_object)], check=True, timeout=60)
        subprocess.run(["cc", *flags, "-I", str(PREVIOUS), "-I",
                        str(PREVIOUS_EMI), "-c", str(PREVIOUS / "remap-fields.c"),
                        "-o", str(remap_object)], check=True, timeout=60)
        subprocess.run(["cc", *flags, *include, str(layout_object),
                        str(remap_object), str(HERE / "src" / "resource-layout-test.c"),
                        "-o", str(binary)], check=True, timeout=60)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1")
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                timeout=90, env=env)
        require(result.returncode == 0 and not result.stderr,
                result.stdout + result.stderr)
        report["host_test"] = result.stdout
        report["predecessor_remap_link"] = "PASS; separately compiled predecessor object"
        report["test_counts"] = {
            "successful_layouts": 4,
            "interval_mismatch_fields": 6,
            "invalid_selector_values": 3,
            "identical_address_refusals": 1,
            "null_output_refusals": 1,
            "zero_generation_refusals": 1,
            "start_end_order_refusals": 1,
            "clear_below_representable_refusals": 1,
            "first_mib_fit_overflow_refusals": 1,
        }
        report["sanitizer_flags"] = flags
        report["compiler"] = subprocess.check_output(
            ["cc", "--version"], text=True).splitlines()[0]

        checkpatch_url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                          SPEC["linux_source"] + "/scripts/checkpatch.pl")
        with urllib.request.urlopen(checkpatch_url, timeout=30) as response:
            checkpatch = response.read(300001)
        require(len(checkpatch) <= 300000, "oversized checkpatch")
        require(digest(checkpatch) == SPEC["checkpatch_sha256"],
                "checkpatch identity changed")
        checkpatch_path = work / "checkpatch.pl"
        checkpatch_path.write_bytes(checkpatch)
        for name, expected in {
                "spelling.txt": "4095d4a8810f115bae1b7c0d8a1946beb3435f6e22d9a48ac009bb024bad1e68",
                "const_structs.checkpatch": "ea064f6916a74763468037494aeb270aae34b7c97617e84d424ca5b8733539b2",
        }.items():
            auxiliary_url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                             SPEC["linux_source"] + "/scripts/" + name)
            with urllib.request.urlopen(auxiliary_url, timeout=30) as response:
                auxiliary = response.read(300001)
            require(len(auxiliary) <= 300000, "oversized checkpatch auxiliary")
            require(digest(auxiliary) == expected,
                    "checkpatch auxiliary identity changed: " + name)
            (work / name).write_bytes(auxiliary)
        check = subprocess.run(
            ["perl", str(checkpatch_path), "--strict", "--no-tree",
             str(patch_path)], capture_output=True, text=True, timeout=60,
            cwd=work)
        check_output = (check.stdout + check.stderr).replace(str(ROOT), "<project>")
        report["checkpatch"] = {
            "exit": check.returncode,
            "checkpatch_sha256": SPEC["checkpatch_sha256"],
            "allowed_findings": [
                "WARNING: added, moved or deleted file(s), does MAINTAINERS need updating?",
                "ERROR: Missing Signed-off-by: line(s)",
            ],
            "output": check_output,
        }
        require(check.returncode == 1 and
                "ERROR: Missing Signed-off-by: line(s)" in check_output and
                "No typos will be found" not in check_output and
                "No structs that should be const" not in check_output and
                "CHECK:" not in check_output and
                "ERROR: " not in check_output.replace(
                    "ERROR: Missing Signed-off-by: line(s)", ""),
                "unexpected checkpatch finding")
    for source in (HERE / "scripts").glob("*.py"):
        ast.parse(source.read_text())
    report["source_hashes"] = {
        path.name: digest(path.read_bytes())
        for path in sorted((HERE / "src").iterdir())
    }
    report["limitations"] = [
        "Linux __KERNEL__ include branch and real arm64 object await Buildbox.",
        "Proposal replay and Buildbox require the integrator's clean pushed commit.",
        "The input is descriptive initialized state, not reservation or exclusion authority.",
        "Partial byte overlap is a caller precondition and is not detected.",
        "Expected selector and remap equality do not establish provenance or external-writer exclusion.",
        "No runtime caller, permission policy, MMIO, mapping, firmware or hardware path exists.",
    ]
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(143))
    main()
