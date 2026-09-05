#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic metadata-only tests; no live collection is performed."""

import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import parent_presence as probe
from test_wifi_sysfs import BOOT, OTHER_BOOT, KERNEL, Fixture


SCRIPT = Path(__file__).with_name("parent_presence.py")
HELPER = Path(__file__).with_name("wifi_sysfs.py")


class PresenceTests(unittest.TestCase):
    def setUp(self):
        self.managed = tempfile.TemporaryDirectory(prefix="wifi-parent-tests-", dir="/tmp")
        self.addCleanup(self.managed.cleanup)
        self.root = Path(self.managed.name) / "fixture"
        self.root.mkdir()
        self.fixture = Fixture(self.root)
        self.netdev = self.fixture.device + "/net/wlan0"
        self.fixture.path(self.netdev).mkdir(parents=True)
        self.fixture.path(probe.WLAN + "/device").unlink()
        self.fixture.path(probe.WLAN).rmdir()
        self.fixture.link(self.netdev + "/device", self.fixture.device)
        self.fixture.link(probe.WLAN, self.netdev)
        self.fixture.link(probe.PLATFORM, self.fixture.device)

    def run_reader(self, cls=probe.core.Reader):
        reader = cls(self.root, fixture=True, seconds=10)
        try:
            return probe.collect(reader, KERNEL, BOOT)
        finally:
            reader.close()

    def test_exactly_eight_fixed_paths_and_frozen_helper(self):
        self.assertEqual(len(probe.PATHS), 8)
        self.assertEqual(len(set(path for _, path in probe.PATHS)), 8)
        self.assertEqual(hashlib.sha256(HELPER.read_bytes()).hexdigest(), probe.HELPER_SHA256)

    def test_complete_metadata(self):
        result = self.run_reader()
        self.assertEqual(result["status"], "observed")
        self.assertTrue(result["identity_checked_end"])
        self.assertEqual(result["paths"]["wlan"]["entry_kind"], "symlink")
        self.assertEqual(result["paths"]["compatible"]["target_kind"], "regular")
        self.assertEqual(result["budget"]["identity_bytes_read"], 92)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_no_property_payloads_are_read(self):
        class IdentityOnlyReader(probe.core.Reader):
            def read(self, path):
                if path not in (probe.core.BOOT_PATH, probe.core.KERNEL_PATH):
                    raise AssertionError("unexpected payload read")
                return super().read(path)

        self.fixture.put(self.fixture.node + "/compatible", "SECRET UNREAD PAYLOAD")
        result = self.run_reader(cls=IdentityOnlyReader)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["property_payload_reads"], 0)
        self.assertNotIn("SECRET", json.dumps(result))

    def test_missing_wlan_preserves_independent_platform_result(self):
        self.fixture.path(probe.WLAN).unlink()
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["paths"]["wlan"]["entry_kind"], "unavailable")
        self.assertEqual(result["paths"]["platform_driver"]["resolved_relation"], "expected")
        self.assertTrue(result["identity_checked_end"])

    def test_partial_of_properties_localize_failure(self):
        self.fixture.path(self.fixture.node + "/clock-names").unlink()
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["paths"]["of_node"]["resolved_relation"], "expected")
        self.assertEqual(result["paths"]["compatible"]["resolved_relation"], "expected")
        self.assertEqual(result["paths"]["clock_names"]["resolved_relation"], "unavailable")

    def test_missing_driver_is_distinguished_from_missing_netdev(self):
        self.fixture.path(self.fixture.device + "/driver").unlink()
        result = self.run_reader()
        self.assertEqual(result["paths"]["wlan"]["resolved_relation"], "expected")
        self.assertEqual(result["paths"]["driver"]["resolved_relation"], "unavailable")
        self.assertEqual(result["paths"]["platform_driver"]["resolved_relation"], "unavailable")

    def test_dangling_final_link_retains_link_kind(self):
        self.fixture.link(self.netdev + "/device", "/sys/devices/missing")
        result = self.run_reader()
        self.assertEqual(result["paths"]["device"]["entry_kind"], "symlink")
        self.assertEqual(result["paths"]["device"]["target_kind"], "unavailable")

    def test_unexpected_target_strings_are_suppressed(self):
        path = "/sys/bus/platform/drivers/PRIVATE_IDENTIFIER"
        self.fixture.path(path).mkdir()
        self.fixture.link(self.fixture.device + "/driver", path)
        result = self.run_reader()
        self.assertEqual(result["paths"]["driver"]["resolved_relation"], "other")
        self.assertNotIn("PRIVATE_IDENTIFIER", json.dumps(result))

    def test_escaping_symlink_refuses(self):
        path = self.fixture.path(self.fixture.node + "/compatible")
        path.unlink()
        path.symlink_to("/etc/passwd")
        result = self.run_reader()
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["reason"], "path_escape")
        self.assertTrue(result["identity_checked_end"])

    def test_special_path_refuses_without_open(self):
        path = self.fixture.path(self.fixture.node + "/compatible")
        path.unlink()
        os.mkfifo(path)
        result = self.run_reader()
        self.assertEqual(result["reason"], "special_path")
        self.assertEqual(result["budget"]["identity_bytes_read"], 92)

    def test_identity_drift_refuses(self):
        class DriftReader(probe.core.Reader):
            calls = 0

            def text(self, path):
                value = super().text(path)
                if path == probe.core.BOOT_PATH:
                    self.calls += 1
                    if self.calls == 2:
                        return OTHER_BOOT
                return value

        result = self.run_reader(cls=DriftReader)
        self.assertEqual(result["reason"], "identity_mismatch_or_drift")
        self.assertFalse(result["identity_checked_end"])

    def test_python35_grammar(self):
        ast.parse(SCRIPT.read_text(), feature_version=(3, 5))

    def test_default_opens_no_metadata(self):
        with mock.patch.object(probe.core, "Reader", side_effect=AssertionError("unexpected read")):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = probe.main([])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "dry-run")

    def test_cli_missing_pins_refuses_before_live_read(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--collect"],
                                text=True, capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["reason"], "expected_identity_required")

    def test_streamed_helper_and_probe_work_on_fixture(self):
        # Exercise the exact import strategy for a streamed, caller-pinned
        # helper, without installing files or reading a live device tree.
        source = (
            "import sys, types\n"
            "helper = types.ModuleType('wifi_sysfs')\n"
            "exec(compile({0}, 'wifi_sysfs.py', 'exec'), helper.__dict__)\n"
            "sys.modules['wifi_sysfs'] = helper\n"
            "exec(compile({1}, 'parent_presence.py', 'exec'), {{'__name__': '__main__'}})\n"
        ).format(repr(HELPER.read_text()), repr(SCRIPT.read_text()))
        result = subprocess.run(
            [sys.executable, "-B", "-", "--fixture-root", str(self.root),
             "--expected-kernel", KERNEL, "--expected-boot-id", BOOT],
            input=source, text=True, capture_output=True, timeout=15, check=False)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "observed")


if __name__ == "__main__":
    unittest.main()
