#!/usr/bin/env python3
"""Replay and verify the offline ordinary-transfer bridge contract."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, cwd=HERE, **kwargs):
    return subprocess.run(command, cwd=cwd, check=True, **kwargs)


def main():
    inputs = json.loads((HERE / "inputs.json").read_text())
    if digest(ROOT / "experiments/2026-09-06-mt6797-ordinary-transfer-bridge/WORK_ITEM.md") != inputs["work_item_sha256"]:
        raise SystemExit("work item changed")
    for item in inputs["inputs"]:
        if digest(ROOT / item["path"]) != item["sha256"]:
            raise SystemExit("input changed: " + item["path"])
    run(["python3", str(HERE / "scripts/generate-patch.py")], stdout=subprocess.PIPE,
        text=True)
    if digest(HERE / "0012-wifi-mediatek-compile-ordinary-transfer-bridge.patch") != inputs["generated_patch_sha256"]:
        raise SystemExit("generated patch does not match recorded identity")
    run(["python3", str(HERE / "scripts/test_candidate.py")])
    sanitizer = HERE / "ordinary-transfer-sanitized"
    run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O1", "-g",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
         "-DORDINARY_TRANSFER_HOST_TEST", "-Isrc", "src/ordinary-transfer.c",
         "src/ordinary-transfer-test.c", "-o", str(sanitizer)])
    try:
        run([str(sanitizer)], env=dict(os.environ, ASAN_OPTIONS="halt_on_error=1"))
    finally:
        sanitizer.unlink(missing_ok=True)
        shutil.rmtree(Path(str(sanitizer) + ".dSYM"), ignore_errors=True)
    text = (HERE / "src/ordinary-transfer.c").read_text() + (HERE / "src/ordinary-transfer.h").read_text()
    forbidden = ("swapoff", "swapon", "mt6797_image_binding", "image_binding_begin",
                 "START", "emi_service_gate", "EXPORT_SYMBOL", "module_init")
    if any(token in text for token in forbidden):
        raise SystemExit("forbidden production boundary token")
    print(json.dumps({"normal": "pass", "optimized": "pass", "asan_ubsan": "pass",
                      "patch": digest(HERE / "0012-wifi-mediatek-compile-ordinary-transfer-bridge.patch")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
