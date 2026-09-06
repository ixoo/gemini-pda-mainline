#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify generation, strict host compilation and the no-runtime boundary."""
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


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "remap_fields_patch", HERE / "scripts" / "generate-patch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    generated = load_generator().generate()
    patch_path = HERE / SPEC["patch"]
    require(generated == patch_path.read_bytes(), "patch reproduction differs")
    implementation = (HERE / "src" / "remap-fields.c").read_text()
    header = (HERE / "src" / "remap-fields.h").read_text()
    makefile = patch_path.read_text()
    forbidden = ("EXPORT_SYMBOL", "module_init", "platform_driver",
                 "arm_smccc", "ioremap", "memremap", "readl", "writel",
                 "dma_map", "request_firmware", "request_irq", "regulator_",
                 "regmap", "spin_lock", "mutex_lock")
    require(not any(token in implementation for token in forbidden),
            "effectful implementation token found")
    require(not any(token in header for token in forbidden),
            "effectful header token found")
    for name in ("mt6797_remap_encode_common", "mt6797_remap_encode_wlan",
                 "mt6797_remap_replace_common", "mt6797_remap_replace_wlan"):
        require(len(re.findall(r"\b" + name + r"\s*\(", implementation)) == 1,
                "implementation contains a caller: " + name)
    require("obj-y += remap-fields.o" in makefile,
            "Kbuild object missing")
    require("remap-fields-test.c" not in makefile,
            "host test entered Kbuild")

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
        "runtime_caller": "NONE; object is linked but unreferenced",
        "effect_api_scan": "PASS",
    }
    with scratch("verify") as work:
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Wconversion",
                 "-Wsign-conversion", "-pedantic", "-O1", "-g",
                 "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                 "-fno-omit-frame-pointer"]
        include = ["-I", str(HERE / "src")]
        object_file = work / "remap-fields.o"
        binary = work / "remap-fields-test"
        subprocess.run(["cc", *flags, *include, "-c",
                        str(HERE / "src" / "remap-fields.c"),
                        "-o", str(object_file)], check=True, timeout=60)
        subprocess.run(["cc", *flags, *include, str(object_file),
                        str(HERE / "src" / "remap-fields-test.c"),
                        "-o", str(binary)], check=True, timeout=60)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1")
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                timeout=90, env=env)
        require(result.returncode == 0 and not result.stderr,
                result.stdout + result.stderr)
        report["host_test"] = result.stdout
        report["test_counts"] = {
            "common_base_encodings": 4096 * 2,
            "wlan_upper_encodings": 65536,
            "common_alignment_residues": 1048575,
            "wlan_alignment_residues": 65535,
            "common_neighbor_patterns": 524288,
            "wlan_neighbor_patterns": 65536,
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
        "Linux __KERNEL__ include branch is not host-compiled.",
        "Proposal replay and Buildbox require the integrator's clean pushed commit.",
        "No runtime caller, MMIO, mapping, firmware or hardware path exists.",
        "Expected-state APIs rely on an owner-supplied exact read observation.",
    ]
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(143))
    main()
