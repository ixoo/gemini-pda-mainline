#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify only pinned text patches and synthetic host parser fixtures."""
import ast
import fcntl
import shutil
import signal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]

def main():
    spec = json.loads((HERE / "inputs.json").read_text())
    patch = HERE / "0002-wifi-mediatek-add-mtke-parser.patch"
    generated = subprocess.check_output([sys.executable, str(HERE / "scripts/generate-patch.py")])
    assert generated == patch.read_bytes(), "patch reproduction differs"
    for name, digest in spec["parser_files"].items():
        packaged = (HERE / "src" / name).read_bytes()
        assert hashlib.sha256(packaged).hexdigest() == digest
        original = subprocess.check_output(["git", "show", spec["parser_commit"] +
            ":experiments/2026-09-05-mtke-c-parser/" + name], cwd=ROOT)
        assert hashlib.sha256(original).hexdigest() == spec["original_parser_files"][name]
        if name in ("mtke.c", "crc-kernel.c"):
            original = original.replace(b"/* SPDX-License-Identifier: GPL-2.0-only */",
                                        b"// SPDX-License-Identifier: GPL-2.0-only", 1)
        assert packaged == original, "unexpected parser source change"
    managed = ROOT / "artifacts/wifi-hif-parser-compile"
    managed.mkdir(parents=True, exist_ok=True)
    assert not managed.is_symlink()
    lock = (managed / ".verify.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = "hif-parser-verify-v1\n"
    for stale in managed.glob("verify-*"):
        assert stale.is_dir() and not stale.is_symlink()
        assert (stale / ".owner").read_text() == marker
        assert all(not item.is_symlink() for item in stale.rglob("*"))
        shutil.rmtree(stale)
    report = {"kernel_build": "NOT RUN", "device": "NOT ACCESSED",
              "patch_reproduction_and_replay": "PASS",
              "patch_sha256": hashlib.sha256(generated).hexdigest(), "host_tests": {}}
    with tempfile.TemporaryDirectory(prefix="verify-", dir=managed) as directory:
        scratch = Path(directory)
        (scratch / ".owner").write_text(marker)
        oracle = scratch / "oracle.py"
        oracle.write_bytes(subprocess.check_output(["git", "show",
            "b441128eadf8cd834d74a5f8262d3a43e2d93778:experiments/2026-09-05-mt6797-wifi-contract/scripts/wifi_firmware.py"], cwd=ROOT))
        env = dict(os.environ, TMPDIR=str(scratch), PYTHONDONTWRITEBYTECODE="1")
        for name, args in (("test-parser.py", ["--oracle", str(oracle)]), ("test-memory.py", [])):
            result = subprocess.run([sys.executable, str(HERE / "src" / name), *args],
                                    env=env, text=True, capture_output=True, timeout=120)
            assert result.returncode == 0, result.stdout + result.stderr
            report["host_tests"][name] = {"exit": result.returncode, "output": result.stdout + result.stderr}
        tools = json.loads((HERE / "checkpatch-inputs.json").read_text())
        for name, digest in tools["files"].items():
            with urllib.request.urlopen("https://raw.githubusercontent.com/torvalds/linux/" + spec["upstream_commit"] + "/scripts/" + name, timeout=20) as response:
                data = response.read(400001)
            assert len(data) <= 400000 and hashlib.sha256(data).hexdigest() == digest
            (scratch / name).write_bytes(data)
        result = subprocess.run(["perl", str(scratch / "checkpatch.pl"), "--strict", "--no-tree", str(patch)], text=True, capture_output=True, timeout=60)
        report["checkpatch"] = {"exit": result.returncode, "exclusions": [], "output": (result.stdout + result.stderr).replace(str(ROOT), "<project>")}
    findings = [line for line in report["checkpatch"]["output"].splitlines()
                if line.startswith(("ERROR:", "WARNING:", "CHECK:"))]
    assert findings == [
        "WARNING: added, moved or deleted file(s), does MAINTAINERS need updating?",
        "CHECK: Prefer kernel type 'u8' over 'uint8_t'",
        "CHECK: Prefer kernel type 'u32' over 'uint32_t'",
        "ERROR: Missing Signed-off-by: line(s)",
    ], "unexpected checkpatch findings"
    for script in (HERE / "scripts").glob("*.py"):
        ast.parse(script.read_text())
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
