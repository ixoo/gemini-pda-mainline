#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline refusal fixtures for the passive boot2 deployment adapter."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "scripts"))
import installer  # noqa: E402


class InstallerTests(unittest.TestCase):
    def test_exact_candidate_predecessor_and_shutdown_closure_are_pinned(self):
        source = Path(installer.__file__).read_text(encoding="utf-8")
        for token in (
            installer.CANDIDATE_SHA256,
            installer.EXPECTED_PREDECESSOR_SHA256,
            'source.count(\'of="$target"\') == 1',
            'dd if="$EXPECTED_STAGE" of="$target"',
            'blockdev --flushbufs "$target"',
            'cmp -s "$candidate" "$readback_tmp"',
            "sudo -n systemctl poweroff",
            "reboot=no",
        ):
            self.assertIn(token, source)

    def test_every_source_pin_matches_and_a_mutation_refuses(self):
        paths = {
            installer.PARENT_INSTALLER: installer.PARENT_INSTALLER_SHA256,
            installer.PARENT_VALIDATOR: installer.PARENT_VALIDATOR_SHA256,
            installer.PARENT_RECEIPT: installer.PARENT_RECEIPT_SHA256,
            installer.VALIDATOR: installer.VALIDATOR_SHA256,
            installer.RECEIPT: installer.RECEIPT_SHA256,
        }
        for path, expected in paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        original = installer.regular

        def changed(path, limit=32 * 1024 * 1024):
            data = original(path, limit)
            return data + b"\n" if path == installer.PARENT_INSTALLER else data

        with mock.patch.object(installer, "regular", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "source changed"):
                installer.source_pins()

    def test_anchor_count_mutations_refuse(self):
        self.assertEqual(installer.replace_count("aa", "a", "b", 2, "x"), "bb")
        for count in (1, 3):
            with self.subTest(count=count), self.assertRaisesRegex(
                    ValueError, "anchors changed"):
                installer.replace_count("aa", "a", "b", count, "x")

    def test_execute_requires_exact_target_before_device_inputs(self):
        result = subprocess.run([
            sys.executable, str(HERE / "scripts/installer.py"),
            "--candidate", "missing", "--package", "missing",
            "--foundation-initramfs", "missing", "--userspace", "missing",
            "--credentials", "missing", "--execute", "--target", "wrong",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"--execute requires exact target", result.stderr)

    def test_symlinked_intermediate_output_refuses(self):
        root = installer.REPO / "artifacts/consys-passive"
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
        import tempfile
        with tempfile.TemporaryDirectory(prefix="output-fixture-", dir=root) as raw, \
                tempfile.TemporaryDirectory(prefix="passive-output-external-") as external:
            fixture = Path(raw)
            link = fixture / "nested-link"
            link.symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                installer.private_output(link / "child/install.sh")
            self.assertFalse((Path(external) / "child").exists())
        self.assertFalse(os.path.lexists(link))


class ReceiptTests(unittest.TestCase):
    CANDIDATE = installer.CANDIDATE_SHA256
    MANIFEST = "e" * 64
    PREDECESSOR = installer.EXPECTED_PREDECESSOR_SHA256

    @staticmethod
    def raw(experiment=installer.EXPERIMENT, predecessor=PREDECESSOR):
        return "\n".join((
            "experiment=" + experiment,
            "candidate_manifest_sha256=" + ReceiptTests.MANIFEST,
            "result=write-synced-flushed-full-readback-verified",
            "target_logical_name=boot2",
            "target=/dev/mmcblk0p30",
            "root=/dev/mmcblk0p29",
            "boot2_device_guard=passed",
            "boot2_device_guard_sha256=0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf",
            "target_major_minor=179:30",
            "root_major_minor=179:29",
            "predecessor_sha256=" + predecessor,
            "fresh_predecessor_backup=no",
            "candidate_sha256=" + ReceiptTests.CANDIDATE,
            "readback_sha256=" + ReceiptTests.CANDIDATE,
            "boot_id=11111111-1111-4111-8111-111111111111",
            "power=1|100|Good|1",
            "temporary_readback_removed=yes",
            "shutdown=requested-after-evidence-flush",
            "poweroff_ssh_rc=255",
            "post_shutdown_reachability=unreachable",
            "reboot=no",
            "next_action=owner-physically-selects-boot2",
        ))

    def test_verified_write_receipt_accepts(self):
        parser = runpy.run_path(str(HERE / "scripts/deployment_receipt.py"))
        self.assertEqual(parser["receipt"](
            self.raw(), self.CANDIDATE, self.MANIFEST, self.PREDECESSOR),
            "11111111-1111-4111-8111-111111111111")

    def test_wrong_experiment_or_predecessor_refuses(self):
        parser = runpy.run_path(str(HERE / "scripts/deployment_receipt.py"))
        for label, raw in (
            ("experiment", self.raw(experiment=installer.PARENT_EXPERIMENT)),
            ("predecessor", self.raw(predecessor="a" * 64)),
        ):
            with self.subTest(label=label), self.assertRaises(ValueError):
                parser["receipt"](
                    raw, self.CANDIDATE, self.MANIFEST, self.PREDECESSOR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
