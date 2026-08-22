#!/usr/bin/env python3
"""Offline positive, mutation, and static tests for raw-ledger runtime tools."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
CLASSIFIER = SCRIPT_DIR / "classify-retained.py"
INSTALLER = SCRIPT_DIR / "install-boot2.sh"

spec = importlib.util.spec_from_file_location("raw_retained_classifier", CLASSIFIER)
assert spec and spec.loader
retained = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retained)


def test_payload_decisions() -> None:
    assert retained.classify_payload(b"")[:2] == (
        "neither",
        "raw-entry-mapping-or-first-commit-not-established",
    )
    assert retained.classify_payload(retained.BEFORE)[:2] == (
        "before-clock-only",
        "protected-clock-call-entered-and-did-not-return",
    )
    assert retained.classify_payload(retained.BEFORE + retained.AFTER)[:2] == (
        "before-and-after-clock",
        "protected-clock-call-returned",
    )
    assert retained.classify_payload(retained.AFTER)[0] == "rejected-attribution"
    assert retained.classify_payload(retained.BEFORE * 2)[0] == "rejected-attribution"
    assert retained.classify_payload(retained.PREFIX + b"foreign\n")[0] == "rejected-attribution"


def test_capture_interface() -> None:
    with tempfile.TemporaryDirectory() as directory:
        capture = Path(directory)
        pstore = capture / "pstore"
        pstore.mkdir()
        (pstore / "dmesg-ramoops-0").write_bytes(retained.BEFORE)
        (pstore / "dmesg-ramoops-1").write_bytes(retained.AFTER)
        result = subprocess.run(
            [str(CLASSIFIER), "--capture", str(capture)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "runtime_classification=before-and-after-clock" in result.stdout
        assert "runtime_reason=protected-clock-call-returned" in result.stdout
        assert "before_clock_record_count=1" in result.stdout
        assert "after_clock_record_count=1" in result.stdout


def test_unsafe_capture_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        capture = Path(directory)
        pstore = capture / "pstore"
        pstore.mkdir()
        target = capture / "outside"
        target.write_bytes(retained.BEFORE)
        (pstore / "unsafe").symlink_to(target)
        result = subprocess.run(
            [str(CLASSIFIER), "--capture", str(capture)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 3
        assert "runtime_classification=rejected-attribution" in result.stdout


def test_installer_contract() -> None:
    result = subprocess.run(
        [str(INSTALLER), "--help"], capture_output=True, text=True, check=True
    )
    help_text = result.stdout + result.stderr
    assert "protected-readback-raw-entry-ledger-deployment-N" in help_text
    assert "No fresh partition backup is made." in help_text
    source = INSTALLER.read_text(encoding="utf-8")
    assert "7c403a38197f948eff8cc02779ac55d1a172e3898e8663cc98fb8e22a2dc41a9" in source
    assert "candidate-protected-readback-raw-0ad7160c" in source


def main() -> None:
    test_payload_decisions()
    test_capture_interface()
    test_unsafe_capture_rejected()
    test_installer_contract()
    print("validation=protected-readback-raw-entry-ledger-runtime-tools-offline")
    print("retained_decision_branches=3")
    print("retained_negative_mutations_rejected=3")
    print("unsafe_capture_mutations_rejected=1")
    print("installer_help_and_identity_contract=pass")
    print("device_access=none")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
