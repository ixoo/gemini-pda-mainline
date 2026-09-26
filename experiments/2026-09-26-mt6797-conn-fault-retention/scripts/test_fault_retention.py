#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the pinned, patched SCPSYS callbacks with host-only fault injection."""

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
PIN = "4d7d9486c04d917265f64c55bd23b2cc4fe7749c"
SOURCE = "drivers/pmdomain/mediatek/mtk-scpsys.c"
SOURCE_SHA256 = "9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226"
PATCHES = (
    ("0001-pmdomain-mediatek-defer-initial-activation.patch", "e2338d566150a9e5a929b6a37e1bf76e356c4989391dd8549ed36b8e7554bc7f"),
    ("0002-pmdomain-mediatek-conn-off-clock-before-reset.patch", "bfbe2cf768bf6170cddef3dd6bbfeb2be3cb931e8f24404282ee5a7eabcf3acc"),
    ("0003-pmdomain-mediatek-retain-failed-domain-resources.patch", "2ca761d5b8be64d70dc0a4ec88e9b406980a09379050f215a4853afe6f7bf824"),
)
FUNCTIONS = (
    "scpsys_hold_fault", "scpsys_regulator_enable", "scpsys_regulator_disable",
    "scpsys_clk_disable", "scpsys_clk_enable", "scpsys_power_on", "scpsys_power_off",
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(argv, cwd):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                            timeout=45, check=False)
    require(result.returncode == 0,
            "failed: " + " ".join(argv[:2]) + "\n" + result.stdout + result.stderr)
    return result.stdout


def function(source, name):
    match = re.search(r"(?m)^static [^\n]*\b" + re.escape(name) + r"\(", source)
    require(match is not None, "missing function: " + name)
    end = source.find("\n}\n", match.start())
    require(end >= 0, "unterminated function: " + name)
    return source[match.start():end + 3]


def main():
    url = "https://raw.githubusercontent.com/torvalds/linux/" + PIN + "/" + SOURCE
    source = urllib.request.urlopen(url, timeout=45).read()
    require(hashlib.sha256(source).hexdigest() == SOURCE_SHA256,
            "upstream source digest mismatch")
    with tempfile.TemporaryDirectory(prefix="gemini-scpsys-fault-") as directory:
        work = Path(directory)
        source_path = work / SOURCE
        source_path.parent.mkdir(parents=True)
        source_path.write_bytes(source)
        for name, digest in PATCHES:
            patch = ROOT / "patches/proposals" / name
            data = patch.read_bytes()
            require(hashlib.sha256(data).hexdigest() == digest,
                    "patch digest mismatch: " + name)
            local = work / name
            local.write_bytes(data)
            run(["git", "apply", "--check", "--whitespace=error", name], work)
            run(["git", "apply", "--whitespace=error", name], work)
        patched = source_path.read_text()
        functions = "\n".join(function(patched, name) for name in FUNCTIONS)
        (work / "scpsys-under-test.inc").write_text(functions)
        (work / "fault_retention_test.c").write_bytes(
            (EXPERIMENT / "src/fault_retention_test.c").read_bytes())
        run(["cc", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-Wno-unused-parameter", "fault_retention_test.c", "-o", "fixture"], work)
        print(run(["./fixture"], work).strip())
        print("source_pin=" + PIN)
        print("actual_callbacks=" + ",".join(FUNCTIONS))
        print("hardware_validation=not_run")


if __name__ == "__main__":
    main()
