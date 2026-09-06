#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify exact generation, strict host compilation and no runtime hooks."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import urllib.request
from support import HERE, ROOT, SPEC, digest, require, scratch


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "emi_abi_patch", HERE / "scripts" / "generate-patch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    require(len(sys.argv) == 1, "no arguments accepted")
    generated = load_generator().generate()
    patch_path = HERE / SPEC["patch"]
    require(generated == patch_path.read_bytes(), "patch reproduction differs")
    implementation = (HERE / "src" / "emi-abi.c").read_text()
    makefile = patch_path.read_text()
    forbidden = ("EXPORT_SYMBOL", "module_init", "platform_driver",
                 "arm_smccc", "ioremap", "memremap", "readl", "writel",
                 "dma_map", "request_firmware", "request_irq", "regulator_")
    require(not any(token in implementation for token in forbidden),
            "effectful implementation token found")
    require(len(re.findall(r"\bmt6797_emi_prepare\s*\(", implementation)) == 1,
            "implementation contains a caller")
    require(len(re.findall(r"\bmt6797_emi_decode_result\s*\(", implementation)) == 1,
            "decoder contains an unexpected caller")
    require("obj-y += emi-abi.o" in makefile, "Kbuild object missing")
    require("emi-abi-test.c" not in makefile, "host test entered Kbuild")

    report = {
        "patch_sha256": digest(generated),
        "patch_reproduction_and_replay": "PASS",
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
        object_file = work / "emi-abi.o"
        binary = work / "emi-abi-test"
        subprocess.run(["cc", *flags, *include, "-c",
                        str(HERE / "src" / "emi-abi.c"), "-o", str(object_file)],
                       check=True, timeout=60)
        subprocess.run(["cc", *flags, *include, str(object_file),
                        str(HERE / "src" / "emi-abi-test.c"), "-o", str(binary)],
                       check=True, timeout=60)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1")
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                timeout=90, env=env)
        require(result.returncode == 0 and not result.stderr,
                result.stdout + result.stderr)
        report["host_test"] = result.stdout
        report["sanitizer_flags"] = flags
        report["compiler"] = subprocess.check_output(
            ["cc", "--version"], text=True).splitlines()[0]
        checkpatch_url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                          SPEC["linux_commit"] + "/scripts/checkpatch.pl")
        with urllib.request.urlopen(checkpatch_url, timeout=30) as response:
            checkpatch = response.read(300001)
        require(len(checkpatch) <= 300000, "oversized checkpatch")
        require(digest(checkpatch) == SPEC["checkpatch_sha256"],
                "checkpatch identity changed")
        checkpatch_path = work / "checkpatch.pl"
        checkpatch_path.write_bytes(checkpatch)
        for name, expected in SPEC["checkpatch_auxiliary"].items():
            auxiliary_url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                             SPEC["linux_commit"] + "/scripts/" + name)
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
            "auxiliary_sha256": SPEC["checkpatch_auxiliary"],
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
        p.name: digest(p.read_bytes()) for p in sorted((HERE / "src").iterdir())
    }
    report["limitations"] = [
        "Linux __KERNEL__ include branch is not host-compiled.",
        "Buildbox requires the integrator's clean pushed commit and shared series.",
        "No runtime caller, secure call, mapping, firmware or hardware path exists.",
    ]
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
