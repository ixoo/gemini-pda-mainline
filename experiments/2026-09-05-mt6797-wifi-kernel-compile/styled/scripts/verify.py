#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run the same pinned protocol fixtures on reference and styled headers."""
import fcntl
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

sys.dont_write_bytecode = True
from prepare import HERE, PROPOSAL, ROOT, digest, require, tokens


def main():
    require(len(sys.argv) == 1, "no arguments accepted")
    subprocess.run([sys.executable, str(HERE / "scripts/prepare.py")], check=True)
    spec = json.loads((HERE / "test-inputs.json").read_text())
    original = json.loads((PROPOSAL / "inputs.json").read_text())
    # Ensure this oracle detects an operational token change, not just a hash.
    sample = "a += 1; b = a + +c; /* comment */"
    require(tokens(sample) == tokens("a+=1; b=a + + c;"), "whitespace oracle")
    require(tokens(sample) != tokens("a += 2; b=a + +c;"), "value mutation escaped")
    require(tokens(sample) != tokens("a += 1; b=a ++c;"), "operator mutation escaped")
    managed = ROOT / "artifacts/wifi-kernel-style"
    lock_path = managed / ".lock"
    require(not lock_path.is_symlink(), "unsafe lock")
    lock = lock_path.open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = "mt6797-hif-style-fixtures-v1\n"
    for stale in managed.glob("verify-*"):
        stamp = stale / ".owner"
        require(stale.is_dir() and not stale.is_symlink() and stamp.is_file()
                and not stamp.is_symlink() and stamp.read_text() == marker,
                "unowned fixture scratch")
        require(all(not path.is_symlink() for path in stale.rglob("*")), "scratch symlink")
        shutil.rmtree(stale)
    report = {"scope": "host-only original protocol fixtures; no kernel or backend",
              "fixture_commit": spec["fixture_commit"],
              "compiler": subprocess.check_output(["clang", "--version"]).decode().splitlines()[0],
              "flags": ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer"],
              "token_oracle_mutations_rejected": 2, "fixtures": {}}
    with tempfile.TemporaryDirectory(prefix="verify-", dir=managed) as directory:
        tree = Path(directory)
        (tree / ".owner").write_text(marker)
        for variant in ("reference", "styled"):
            folder = tree / variant
            folder.mkdir()
            for name, expected in original["protocol_headers"].items():
                if variant == "reference":
                    data = subprocess.check_output([
                        "git", "show", original["protocol_commit"] + ":" +
                        original["protocol_directory"] + "/" + name], cwd=ROOT)
                    require(digest(data) == expected, "reference header changed")
                else:
                    data = (HERE / "headers" / name).read_bytes()
                (folder / name).write_bytes(data)
            for name, expected in spec["fixtures"].items():
                data = subprocess.check_output([
                    "git", "show", spec["fixture_commit"] + ":" +
                    spec["fixture_directory"] + "/" + name], cwd=ROOT)
                require(digest(data) == expected, "fixture hash: " + name)
                source = folder / name
                source.write_bytes(data)
                executable = folder / name.removesuffix(".c")
                compile_result = subprocess.run([
                    "clang", *report["flags"], str(source), "-o", str(executable)],
                    capture_output=True, text=True, timeout=60)
                require(compile_result.returncode == 0,
                        variant + "/" + name + " compile failed: " + compile_result.stderr)
                env = os.environ.copy()
                env.update(ASAN_OPTIONS="halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
                run = subprocess.run([str(executable)], capture_output=True,
                                     text=True, timeout=60, env=env)
                require(run.returncode == 0 and not run.stderr,
                        variant + "/" + name + " failed: " + run.stderr)
                record = report["fixtures"].setdefault(name, {"sha256": expected})
                record[variant] = {"compile_exit": 0, "runtime_exit": 0,
                                   "stdout": run.stdout, "sanitizer_stderr": run.stderr}
                if variant == "styled":
                    require(record["reference"] == record["styled"], "fixture outcomes differ")
        for name, expected in spec["checkpatch_tools"].items():
            url = ("https://raw.githubusercontent.com/torvalds/linux/" +
                   spec["checkpatch_commit"] + "/scripts/" + name)
            with urllib.request.urlopen(url, timeout=20) as response:
                data = response.read(400001)
            require(len(data) <= 400000 and digest(data) == expected, "checkpatch tool hash")
            (tree / name).write_bytes(data)
        check = subprocess.run([
            "perl", str(tree / "checkpatch.pl"), "--no-tree", "--strict",
            str(HERE / "0001-lib-mt6797-hif-compile.patch")], capture_output=True,
            text=True, timeout=60)
        output = (check.stdout + check.stderr).replace(str(ROOT), "<project>")
        output = output.replace(str(tree), "<managed-checkpatch>")
        report["checkpatch"] = {"exit": check.returncode, "exclusions": [], "output": output}
        findings = [block for block in re.split(r"\n\n", output)
                    if "FILE:" in block and
                    any(kind in block for kind in ("ERROR:", "WARNING:", "CHECK:"))]
        report["checkpatch"]["source_findings"] = len(findings)
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    require(not findings, "source checkpatch findings remain; see validation.json")
    print("protocol_fixtures=8 variants=2 strict_C11_ASan_UBSan=PASS identical_outcomes=PASS")
    print("source_style_findings=0 unfiltered_mail_metadata_findings_retained")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
