#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test the real C binding with pinned parser/plan and memory/lock shims only."""
import ast
import importlib.util
import json
import os
import signal
import subprocess
import sys
import urllib.request
from support import HERE, ROOT, SPEC, digest, pinned, require, scratch


def main():
    require(len(sys.argv) == 1, "no arguments accepted")
    module_spec = importlib.util.spec_from_file_location(
        "binding_patch", HERE / "scripts/generate-patch.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    generated = module.generate()
    patch = HERE / "0005-wifi-mediatek-describe-reserved-memory.patch"
    require(generated == patch.read_bytes(), "patch reproduction differs")
    report = {"patch_sha256": digest(generated), "patch_reproduction_and_replay": "PASS",
              "kernel_build": "NOT RUN", "backend": "NOT ACCESSED",
              "hardware": "NOT ACCESSED"}
    with scratch("verify") as work:
        for name, item in (SPEC["dependencies"] | SPEC["regression"]).items():
            (work / name).write_bytes(pinned(item))
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Wconversion", "-pedantic",
                 "-pthread", "-O1", "-g", "-fsanitize=address,undefined",
                 "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]
        binary = work / "binding-test"
        subprocess.run(["cc", *flags, "-DMT6797_BINDING_HOST_TEST",
                        "-I", str(work), "-I", str(HERE / "src"),
                        "-I", str(HERE / "tests"), str(work / "mtke.c"),
                        str(work / "image-plan.c"), str(HERE / "src/image-binding.c"),
                        str(HERE / "tests/test-reserved.c"), "-lz", "-o", str(binary)],
                       check=True, timeout=60)
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1")
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                timeout=90, env=env)
        require(result.returncode == 0 and not result.stderr, result.stdout + result.stderr)
        report["same_code_host_test"] = result.stdout
        report["sanitizer_flags"] = flags
        report["compiler"] = subprocess.check_output(["cc", "--version"]).decode().splitlines()[0]
        report["source_hashes"] = {p.name: digest(p.read_bytes()) for p in (HERE / "src").iterdir()}
        report["test_hashes"] = {p.name: digest(p.read_bytes()) for p in (HERE / "tests").iterdir()}
        for name, expected in SPEC["checkpatch"].items():
            url = "https://raw.githubusercontent.com/torvalds/linux/" + SPEC["upstream_commit"] + "/scripts/" + name
            with urllib.request.urlopen(url, timeout=20) as response:
                data = response.read(400001)
            require(len(data) <= 400000 and digest(data) == expected, "checkpatch identity changed")
            (work / name).write_bytes(data)
        result = subprocess.run(["perl", str(work / "checkpatch.pl"), "--strict", "--no-tree", str(patch)],
                                capture_output=True, text=True, timeout=60)
        output = (result.stdout + result.stderr).replace(str(ROOT), "<project>")
        report["checkpatch"] = {"exit": result.returncode, "exclusions": [], "output": output}
    for source in (HERE / "scripts").glob("*.py"):
        ast.parse(source.read_text())
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    findings = [line for line in output.splitlines() if line.startswith(("ERROR:", "WARNING:", "CHECK:"))]
    require(findings == ["ERROR: Missing Signed-off-by: line(s)"], "unexpected source findings; see validation.json")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
