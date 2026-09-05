#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic tests. All temporary state lives under a managed root and cleans up."""

import contextlib
import ast
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("wifi_sysfs.py")
SPEC = importlib.util.spec_from_file_location("wifi_sysfs", SCRIPT)
wifi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wifi)
BOOT = "11111111-2222-3333-4444-555555555555"
OTHER_BOOT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
KERNEL = "3.18.41+"


class Fixture:
    def __init__(self, root):
        self.root = Path(root)
        self.put(wifi.BOOT_PATH, BOOT + "\n")
        self.put(wifi.KERNEL_PATH, KERNEL + "\n")
        self.put(wifi.MODEL_PATH, b"MT6797X\0")
        for path in ("/sys/bus/sdio/devices", "/sys/bus/platform/drivers/mt-wifi",
                     "/sys/bus/sdio/drivers/mtk_sdio_client"):
            self.path(path).mkdir(parents=True, exist_ok=True)
        self.platform()

    def path(self, path):
        return self.root / path.lstrip("/")

    def put(self, path, content):
        target = self.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode() if isinstance(content, str) else content)

    def link(self, path, target):
        dest = self.path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            dest.unlink()
        dest.symlink_to(os.path.relpath(self.path(target), dest.parent))

    def platform(self):
        self.device = "/sys/devices/platform/soc/180f0000.wifi"
        self.node = "/sys/firmware/devicetree/base/soc/wifi@180f0000"
        self.path(self.device).mkdir(parents=True, exist_ok=True)
        self.put(self.node + "/compatible", b"mediatek,wifi\0")
        self.put(self.node + "/clock-names", b"wifi-dma\0")
        self.link(self.device + "/subsystem", "/sys/bus/platform")
        self.link(self.device + "/driver", "/sys/bus/platform/drivers/mt-wifi")
        self.link(self.device + "/of_node", self.node)
        self.link(wifi.WLAN_PATH, self.device)

    def sdio(self, index=1, vendor=0x037a, device=0x6630, as_wlan=False):
        name = f"mmc1:{index:04x}:1"
        path = f"/sys/devices/platform/mmc_host/mmc1/mmc1:{index:04x}/{name}"
        self.path(path).mkdir(parents=True, exist_ok=True)
        self.link(wifi.SDIO_PATH + "/" + name, path)
        self.link(path + "/subsystem", "/sys/bus/sdio")
        self.link(path + "/driver", "/sys/bus/sdio/drivers/mtk_sdio_client")
        self.put(path + "/vendor", f"0x{vendor:04x}\n")
        self.put(path + "/device", f"0x{device:04x}\n")
        self.put(path + "/class", "0x00\n")
        self.put(path + "/modalias", f"sdio:c00v{vendor:04X}d{device:04X}\n")
        if as_wlan:
            self.link(wifi.WLAN_PATH, path)
        return path


class InventoryTests(unittest.TestCase):
    def setUp(self):
        # Explicit managed root, with cleanup registered immediately. The
        # temporary directory context cleans up success, failure and exceptions.
        self.managed = tempfile.TemporaryDirectory(prefix="wifi-sysfs-tests-", dir="/tmp")
        self.addCleanup(self.managed.cleanup)
        self.root = Path(self.managed.name) / "fixture"
        self.root.mkdir()
        self.fixture = Fixture(self.root)

    def run_reader(self, cls=wifi.Reader, **kwargs):
        reader = cls(self.root, fixture=True, **kwargs)
        try:
            return wifi.collect(reader, KERNEL, BOOT)
        finally:
            reader.close()

    def cli(self, *args):
        completed = subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                                   capture_output=True, text=True, timeout=20,
                                   check=False)
        self.assertEqual(completed.stderr, "")
        return completed.returncode, json.loads(completed.stdout)

    def fixture_cli(self, *args):
        return self.cli("--fixture-root", str(self.root), "--expected-kernel", KERNEL,
                        "--expected-boot-id", BOOT, *args)

    def test_platform_and_empty_sdio_is_metadata_only(self):
        result = self.run_reader()
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["classification"], "platform_wifi_parent_observed")
        self.assertEqual(result["facts"]["sdio"]["functions"], [])
        self.assertEqual(result["silicon_identity"], "unproven")
        self.assertEqual(result["radio_operations"], 0)
        self.assertTrue(result["identity_checked_end"])
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn("_path", json.dumps(result))

    def test_sdio_wlan_parent_requires_matching_inventory(self):
        self.fixture.sdio(as_wlan=True)
        result = self.run_reader()
        self.assertEqual(result["classification"], "sdio_wifi_parent_observed")
        self.assertEqual(result["facts"]["sdio"]["functions"][0]["device"], "0x6630")

    def test_platform_and_sdio_coexist_without_implied_connection(self):
        self.fixture.sdio()
        result = self.run_reader()
        self.assertEqual(result["classification"], "platform_wifi_parent_observed")
        self.assertEqual(len(result["facts"]["sdio"]["functions"]), 1)

    def test_unrelated_sdio_ids_do_not_create_chip_match(self):
        self.fixture.sdio(vendor=0x1234, device=0x5678, as_wlan=True)
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["classification"], "sdio_parent_outside_retained_vendor_table")

    def test_conflicting_subsystem_is_inconclusive(self):
        path = self.fixture.sdio()
        self.fixture.link(path + "/subsystem", "/sys/bus/platform")
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["facts"]["sdio"]["reason"], "contradictory_sdio_subsystem")

    def test_conflicting_numeric_ids_and_alias_are_inconclusive(self):
        path = self.fixture.sdio()
        self.fixture.put(path + "/modalias", "sdio:c00v037Ad6628\n")
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["facts"]["sdio"]["reason"], "contradictory_sdio_ids")

    def test_duplicate_sdio_alias_is_inconclusive(self):
        path = self.fixture.sdio()
        self.fixture.link(wifi.SDIO_PATH + "/mmc1:0002:1", path)
        result = self.run_reader()
        self.assertEqual(result["facts"]["sdio"]["reason"], "duplicate_sdio_alias")

    def test_missing_sdio_directory_is_not_empty_inventory(self):
        self.fixture.path(wifi.SDIO_PATH).rmdir()
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["facts"]["sdio"]["state"], "unavailable")
        self.assertNotIn("functions", result["facts"]["sdio"])

    def test_missing_numeric_field_is_inconclusive(self):
        path = self.fixture.sdio()
        self.fixture.path(path + "/vendor").unlink()
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")

    def test_missing_wlan_is_inconclusive(self):
        self.fixture.path(wifi.WLAN_PATH).unlink()
        result = self.run_reader()
        self.assertEqual(result["facts"]["wlan"]["state"], "unavailable")
        self.assertEqual(result["status"], "inconclusive")

    def test_unrecognized_strings_are_never_serialized(self):
        secret = "owner@example.test secret-private-unit"
        self.fixture.put(wifi.MODEL_PATH, secret.encode() + b"\0")
        result = self.run_reader()
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotIn(secret, json.dumps(result))

    def test_unknown_driver_is_inconclusive_and_redacted(self):
        target = "/sys/bus/platform/drivers/private-owner-label"
        self.fixture.path(target).mkdir()
        self.fixture.link(self.fixture.device + "/driver", target)
        result = self.run_reader()
        self.assertEqual(result["facts"]["wlan"]["reason"], "unknown_wlan_driver")
        self.assertNotIn("private-owner-label", json.dumps(result))

    def test_unknown_bus_is_inconclusive(self):
        self.fixture.path("/sys/bus/pci").mkdir()
        self.fixture.link(self.fixture.device + "/subsystem", "/sys/bus/pci")
        result = self.run_reader()
        self.assertEqual(result["facts"]["wlan"]["reason"], "unknown_wlan_bus")

    def test_truncated_of_string_is_inconclusive(self):
        self.fixture.put(self.fixture.node + "/compatible", b"mediatek,wifi")
        result = self.run_reader()
        self.assertEqual(result["facts"]["wlan"]["reason"], "malformed_of_metadata")

    def test_clock_or_compatible_mismatch_is_inconclusive(self):
        for filename in ("compatible", "clock-names"):
            with self.subTest(filename=filename):
                self.fixture.platform()
                self.fixture.put(self.fixture.node + "/" + filename, b"unrelated\0")
                self.assertEqual(self.run_reader()["status"], "inconclusive")

    def test_file_budget_never_reads_past_limit(self):
        self.fixture.put(wifi.MODEL_PATH, b"x" * 5000)
        result = self.run_reader()
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["reason"], "file_byte_budget")
        self.assertLessEqual(result["budget"]["bytes_read"], 4096 + len(BOOT) + len(KERNEL) + 2)

    def test_total_budget_never_reads_past_limit(self):
        result = self.run_reader(max_total=70)
        self.assertEqual(result["reason"], "total_byte_budget")
        self.assertLessEqual(result["budget"]["bytes_read"], 70)

    def test_entry_budget_refuses_partial_inventory(self):
        self.fixture.sdio(index=1)
        self.fixture.sdio(index=2)
        result = self.run_reader(max_entries=1)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["reason"], "entry_budget")
        self.assertLessEqual(result["budget"]["sdio_entries_seen"], 1)

    def test_production_entry_budget(self):
        for index in range(1, 34):
            self.fixture.sdio(index=index)
        result = self.run_reader()
        self.assertEqual(result["reason"], "entry_budget")
        self.assertEqual(result["budget"]["sdio_entries_seen"], 32)

    def test_collector_accepts_python35_grammar(self):
        ast.parse(SCRIPT.read_text(), feature_version=(3, 5))

    def test_python35_scandir_uses_only_anchored_descriptor(self):
        original = os.scandir
        seen = []

        def older_scandir(path):
            self.assertIsInstance(path, str)
            self.assertTrue(path.startswith("/proc/self/fd/"))
            fd = int(path.rsplit("/", 1)[1])
            seen.append(fd)
            return original(fd)

        with mock.patch.object(wifi.sys, "version_info", (3, 5, 3)):
            with mock.patch.object(wifi.os, "scandir", older_scandir):
                result = self.run_reader()
        self.assertEqual(result["classification"], "platform_wifi_parent_observed")
        self.assertEqual(len(seen), 1)

    def test_contradictory_same_parent_cannot_classify(self):
        self.fixture.sdio()
        reader = wifi.Reader(self.root, fixture=True)
        try:
            facts = {"model": "vendor_mt6797x", "wlan": wifi.collect_wlan(reader),
                     "sdio": wifi.collect_sdio(reader)}
        finally:
            reader.close()
        facts["sdio"]["functions"][0]["_path"] = facts["wlan"]["_path"]
        self.assertEqual(wifi.classify(facts), ("inconclusive", "contradictory_parent_membership"))

    def test_deadline_is_finite(self):
        times = iter([0.0, 16.0])
        result = self.run_reader(clock=lambda: next(times))
        self.assertEqual(result["reason"], "time_budget")

    def test_special_file_is_refused_without_read(self):
        target = self.fixture.path(wifi.MODEL_PATH)
        target.unlink()
        os.mkfifo(target)
        result = self.run_reader()
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["reason"], "special_file")

    def test_absolute_symlink_escape_is_refused(self):
        target = self.fixture.path(wifi.MODEL_PATH)
        target.unlink()
        target.symlink_to("/proc/sys/kernel/osrelease")
        result = self.run_reader()
        self.assertEqual(result["reason"], "path_escape")

    def test_relative_symlink_escape_is_refused(self):
        target = self.fixture.path(wifi.MODEL_PATH)
        target.unlink()
        target.symlink_to("../../../../../../../../etc/passwd")
        result = self.run_reader()
        self.assertEqual(result["reason"], "path_escape")

    def test_symlink_loop_is_refused(self):
        target = self.fixture.path(wifi.MODEL_PATH)
        target.unlink()
        target.symlink_to("model")
        result = self.run_reader()
        self.assertEqual(result["reason"], "symlink_budget")

    def test_boot_drift_is_refused(self):
        class DriftReader(wifi.Reader):
            calls = 0

            def text(self, path):
                value = super().text(path)
                if path == wifi.BOOT_PATH:
                    self.calls += 1
                    if self.calls == 2:
                        return OTHER_BOOT
                return value

        result = self.run_reader(cls=DriftReader)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["reason"], "identity_mismatch_or_drift")
        self.assertFalse(result["identity_checked_end"])

    def test_kernel_drift_is_refused(self):
        class DriftReader(wifi.Reader):
            calls = 0

            def text(self, path):
                value = super().text(path)
                if path == wifi.KERNEL_PATH:
                    self.calls += 1
                    if self.calls == 2:
                        return "3.18.42+"
                return value

        self.assertEqual(self.run_reader(cls=DriftReader)["reason"], "identity_mismatch_or_drift")

    def test_topology_change_is_inconclusive(self):
        original = wifi.collect_wlan
        calls = 0

        def changed(reader):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise wifi.Inconclusive("metadata_unavailable")
            return original(reader)

        with mock.patch.object(wifi, "collect_wlan", changed):
            result = self.run_reader()
        self.assertEqual(result["reason"], "wlan_topology_changed")
        self.assertTrue(result["identity_checked_end"])

    def test_unreadable_fact_is_inconclusive(self):
        class MissingReader(wifi.Reader):
            def read(self, path):
                if path.endswith("/clock-names"):
                    raise wifi.Inconclusive("metadata_unavailable")
                return super().read(path)

        self.assertEqual(self.run_reader(cls=MissingReader)["status"], "inconclusive")

    def test_default_constructs_no_reader(self):
        with mock.patch.object(wifi, "Reader", side_effect=AssertionError("live read")):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = wifi.main([])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "not-collected")

    def test_cli_default_has_no_live_observation(self):
        code, result = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["mode"], "dry-run")
        self.assertNotIn("identity", result)

    def test_cli_fixture_success(self):
        code, result = self.fixture_cli()
        self.assertEqual(code, 0)
        self.assertEqual(result["mode"], "fixture")

    def test_cli_missing_pin_cannot_reach_live_reader(self):
        code, result = self.cli("--collect")
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "expected_identity_required")

    def test_cli_fixture_cannot_be_live_root(self):
        code, result = self.cli("--fixture-root", "/", "--expected-kernel", KERNEL,
                                "--expected-boot-id", BOOT)
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "invalid_fixture_root")

    def test_cli_modes_are_mutually_exclusive(self):
        code, result = self.fixture_cli("--collect")
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "invalid_arguments")

    def test_cli_identity_mismatch(self):
        self.fixture.put(wifi.BOOT_PATH, OTHER_BOOT + "\n")
        code, result = self.fixture_cli()
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "identity_mismatch_or_drift")

    def test_cli_truncation_has_nonzero_status(self):
        self.fixture.put(wifi.MODEL_PATH, b"x" * 5000)
        code, result = self.fixture_cli()
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "file_byte_budget")

    def test_cli_missing_fact_has_nonzero_status(self):
        self.fixture.path(wifi.SDIO_PATH).rmdir()
        code, result = self.fixture_cli()
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
