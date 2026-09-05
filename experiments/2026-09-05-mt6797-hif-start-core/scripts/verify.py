#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify the proposed implementation with scalar-I/O/time host substitution."""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    require(len(sys.argv) == 1, "no arguments accepted")
    spec = json.loads((HERE / "inputs.json").read_text())
    patch = (HERE / "0004-wifi-mediatek-execute-bounded-start.patch").read_bytes()
    generated = subprocess.check_output([sys.executable, str(HERE / "scripts/generate-patch.py")])
    require(generated == patch, "patch reproduction differs")
    managed = ROOT / "artifacts/wifi-hif-start-core"
    lock_path = managed / ".verification.lock"
    require(not managed.is_symlink() and not lock_path.is_symlink(), "unsafe managed root/lock")
    lock = lock_path.open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = "mt6797-start-core-host-verification-v1\n"
    for stale in managed.glob("verify-*"):
        stamp = stale / ".owner"
        require(stale.is_dir() and not stale.is_symlink() and stamp.is_file()
                and not stamp.is_symlink() and stamp.read_text() == marker,
                "unowned stale verification scratch")
        require(all(not path.is_symlink() for path in stale.rglob("*")), "scratch symlink")
        shutil.rmtree(stale)
    flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    report = {"scope": "host execution of actual hif.c with allocation/lock/time/scalar-I/O substitutions",
              "kernel_compile": "NOT RUN", "backend": "NOT ACCESSED", "device": "NOT ACCESSED",
              "publication": "NOT PERFORMED", "patch_sha256": digest(patch),
              "patch_reproduction_and_tree_replay": "PASS", "flags": flags,
              "compiler": subprocess.check_output(["clang", "--version"]).decode().splitlines()[0],
              "test_source_sha256": {}, "checkpatch_exclusions": []}
    with tempfile.TemporaryDirectory(prefix="verify-", dir=managed) as directory:
        tree = Path(directory)
        (tree / ".owner").write_text(marker)
        for name, expected in spec["protocol_headers"].items():
            data = subprocess.check_output([
                "git", "show", spec["protocol_commit"] + ":" +
                spec["protocol_directory"] + "/" + name], cwd=ROOT)
            require(digest(data) == expected, "frozen header changed: " + name)
            (tree / "headers").mkdir(exist_ok=True)
            (tree / "headers" / name).write_bytes(data)
        for name, expected in spec["start_files"].items():
            data = (HERE / "src" / name).read_bytes()
            require(digest(data) == expected, "implementation hash changed: " + name)
            (tree / "src").mkdir(exist_ok=True)
            (tree / "src" / name).write_bytes(data)
        (tree / "tests").mkdir()
        for name in ("test-hif.c", "test-compat.h"):
            data = (HERE.parent / "2026-09-05-mt6797-wifi-hif-core" / "tests" / name).read_bytes()
            require(digest(data) == spec["regression_files"][name], "regression fixture hash changed")
            report["test_source_sha256"][name] = digest(data)
            (tree / "tests" / name).write_bytes(data)
        data = (HERE / "tests/test-start.c").read_bytes()
        report["test_source_sha256"]["test-start.c"] = digest(data)
        (tree / "tests/test-start.c").write_bytes(data)
        executable = tree / "test-start"
        built = subprocess.run(["clang", *flags, "-I" + str(tree / "tests"),
                                "-I" + str(tree / "headers"),
                                str(tree / "tests/test-start.c"), "-o", str(executable)],
                               capture_output=True, text=True, timeout=60)
        require(built.returncode == 0 and not built.stderr, "strict compile failed: " + built.stderr)
        env = os.environ.copy()
        env.update(ASAN_OPTIONS="halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
        ran = subprocess.run([str(executable)], capture_output=True, text=True,
                             timeout=60, env=env)
        require(ran.returncode == 0 and not ran.stderr, "fixture failed: " + ran.stderr)
        report["compile_exit"] = built.returncode
        report["runtime_exit"] = ran.returncode
        report["fixture_output"] = ran.stdout
        report["sanitizer_stderr"] = ran.stderr
        tools = json.loads((HERE / "checkpatch-inputs.json").read_text())
        for name, expected in tools["files"].items():
            url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                   spec["upstream_commit"] + "/scripts/" + name)
            with urllib.request.urlopen(url, timeout=20) as response:
                data = response.read(400001)
            require(len(data) <= 400000 and digest(data) == expected, "checkpatch input changed")
            (tree / name).write_bytes(data)
        checked = subprocess.run([
            "perl", str(tree / "checkpatch.pl"), "--no-tree", "--strict",
            str(HERE / "0004-wifi-mediatek-execute-bounded-start.patch")],
            capture_output=True, text=True, timeout=60)
        output = (checked.stdout + checked.stderr).replace(str(ROOT), "<project>")
        report["checkpatch"] = {"exit": checked.returncode, "output": output}
        findings = [block for block in re.split(r"\n\n", output)
                    if "FILE:" in block and
                    any(kind in block for kind in ("ERROR:", "WARNING:", "CHECK:"))]
        report["checkpatch"]["source_findings"] = len(findings)
    for path in (HERE / "scripts").glob("*.py"):
        ast.parse(path.read_text())
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    require(not findings, "source style findings remain; see validation.json")
    print(ran.stdout, end="")
    print("source_style_findings=0 unfiltered_metadata_findings_retained patch_reproduction=PASS")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
