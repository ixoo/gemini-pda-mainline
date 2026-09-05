#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Hardware-free classifier mutations; these do not execute Linux evdev/VT."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("keyboard_classifier", ROOT / "classify.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def fixture():
    expected = {"schema_version": 1, "state": "conditional",
                **{key: "1" * 64 for key in c.HASH_INPUTS},
                "kernel_release": "fixture-kernel",
                "input_sysfs_realpath": "/sys/devices/platform/keyboard-matrix/input/input0"}
    expected["protocol_sha256"] = c.sha((ROOT / "protocol.json").read_bytes())
    receipt = {**expected, "schema_version": 1,
               "deployment_receipt_sha256": "2" * 64,
               "recovery_reference_sha256": "3" * 64,
               "boot_id_before": "00000000-0000-0000-0000-000000000001",
               "boot_id_after": "00000000-0000-0000-0000-000000000001",
               "known_good_boot_id": "00000000-0000-0000-0000-000000000002",
               "cpu_online_before": "0-7", "cpu_online_after": "0-7",
               "map_sha256": c.PROTOCOL["map_sha256"], "map_verify_before": True,
               "map_verify_after": True, "baseline_dependencies_verified": True,
               "console_logs_separated": True, "tty1_exclusive": True,
               "owner_sequence_complete": True, "owner_screen_readable": True,
               "post_capture_usb_pass": True, "budget_claimed_once": True,
               "capture_exit_status": 0, "event": "event0", "event_minor": 64}
    lines = ["keyboard-observe version=1",
             "device event=event0 major=13 minor=64 name=keyboard-matrix",
             "window events=0 bytes=0 held=0",
             "preflight state=pass vt=1 unicode=1 held=0 functions=exact"]
    for step in c.PROTOCOL["steps"]:
        lines.append(f"step begin index={step['index']}")
        for key, value in step["key_edges"]:
            lines.extend([f"event type=4 code=4 value={c.SCANS[key]}",
                          f"event type=1 code={key} value={value}",
                          "event type=0 code=0 value=0"])
        lines.extend(["tty hex=" + step["vt_hex"],
                      f"window events={len(step['key_edges']) * 3} bytes={len(bytes.fromhex(step['vt_hex']))} held=0",
                      f"step end index={step['index']}"])
    lines.append("complete steps=20 restored=1")
    data = ("\n".join(lines) + "\n").encode()
    receipt["capture_sha256"] = c.sha(data)
    return expected, receipt, data


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.expected, self.receipt, self.data = fixture()

    def classify(self, data=None):
        if data is not None:
            self.data = data
            self.receipt["capture_sha256"] = c.sha(data)
        return c.classify(self.expected, self.receipt, self.data)

    def test_complete_fixture(self):
        result = self.classify()
        self.assertEqual(result["classification"], "pass")
        self.assertEqual(len(result["cases"]), 20)
        self.assertFalse(result["hardware_claim"])

    def test_unfrozen_actual_contract_refuses(self):
        self.expected = json.loads((ROOT / "expected-contract.json").read_text())
        self.assertEqual(self.classify()["reason"], "contract-unfrozen")

    def test_every_missing_candidate_input_refuses(self):
        for key in c.HASH_INPUTS:
            with self.subTest(key=key):
                expected = copy.deepcopy(self.expected)
                expected[key] = None
                self.assertEqual(c.classify(expected, self.receipt, self.data)["classification"], "inconclusive")

    def test_wrong_candidate(self):
        self.receipt["candidate_sha256"] = "4" * 64
        self.assertEqual(self.classify()["reason"], "mismatched-candidate_sha256")

    def test_changed_boot(self):
        self.receipt["boot_id_after"] = self.receipt["known_good_boot_id"]
        self.assertEqual(self.classify()["reason"], "lost-boot-attribution")

    def test_a72_online(self):
        self.receipt["cpu_online_after"] = "0-9"
        self.assertEqual(self.classify()["reason"], "cpu-policy")

    def test_missing_prerequisite_witness(self):
        self.receipt["baseline_dependencies_verified"] = False
        self.assertEqual(self.classify()["classification"], "inconclusive")

    def test_owner_interruption(self):
        self.receipt["owner_sequence_complete"] = False
        self.assertEqual(self.classify()["classification"], "inconclusive")

    def test_unreadable_screen(self):
        self.receipt["owner_screen_readable"] = False
        self.assertEqual(self.classify()["classification"], "inconclusive")

    def test_checksum(self):
        self.receipt["capture_sha256"] = "5" * 64
        self.assertEqual(self.classify()["reason"], "capture-checksum")

    def test_wrong_event(self):
        self.assertEqual(self.classify(self.data.replace(b"event=event0", b"event=event1"))["classification"], "inconclusive")

    def test_truncated_every_step(self):
        for index in range(20):
            with self.subTest(index=index):
                expected, receipt, data = fixture()
                data = data.split(f"step end index={index}\n".encode())[0]
                receipt["capture_sha256"] = c.sha(data)
                self.assertEqual(c.classify(expected, receipt, data)["classification"], "inconclusive")

    def test_dropped_sync(self):
        self.assertEqual(self.classify(self.data.replace(b"event type=0 code=0", b"event type=0 code=3", 1))["reason"], "dropped-or-malformed-sync")

    def test_repeat(self):
        self.assertEqual(self.classify(self.data.replace(b"code=42 value=1", b"code=42 value=2", 1))["reason"], "repeat-or-malformed-key")

    def test_unassigned_contact(self):
        result = self.classify(self.data.replace(b"event type=4 code=4 value=30", b"event type=4 code=4 value=63", 1))
        self.assertEqual(result["cases"][0]["result"], "input-sequence-mismatch")

    def test_wrong_key(self):
        result = self.classify(self.data.replace(b"code=42 value=1", b"code=54 value=1", 1))
        self.assertEqual(result["cases"][0]["result"], "input-sequence-mismatch")

    def test_wrong_vt_bytes(self):
        result = self.classify(self.data.replace(b"tty hex=1b5b5b4161", b"tty hex=1b5b5b4261", 1))
        self.assertEqual(result["cases"][0]["result"], "vt-byte-mismatch")

    def test_stuck_logical_shift_sentinel(self):
        result = self.classify(self.data.replace(b"tty hex=1b5b5b4161", b"tty hex=1b5b5b4141", 1))
        self.assertEqual(result["cases"][0]["result"], "vt-byte-mismatch")

    def test_wrong_counter(self):
        self.assertEqual(self.classify(self.data.replace(b"window events=24", b"window events=23", 1))["reason"], "counter-mismatch")

    def test_trailing_data(self):
        self.assertEqual(self.classify(self.data + b"arbitrary\n")["reason"], "trailing-capture-record")

    def test_restoration_failure(self):
        self.assertEqual(self.classify(self.data.replace(b"restored=1", b"restored=0"))["classification"], "inconclusive")

    def test_byte_budget(self):
        self.assertEqual(self.classify(b"x" * 262145)["reason"], "capture-byte-budget")

    def test_duplicate_json_fields(self):
        with self.assertRaisesRegex(c.Refusal, "duplicate-json-field"):
            json.loads('{"value":1,"value":2}', object_pairs_hook=c.no_duplicates)

    def test_protocol_budget_and_manual_anchors(self):
        p = c.PROTOCOL
        self.assertEqual([p['step_seconds'], p['idle_seconds'], p['capture_sessions']], [10, 2, 1])
        self.assertEqual(len(p['steps']), 20)
        self.assertEqual(sum(len(s['key_edges']) for s in p['steps']), 142)
        self.assertEqual(p['steps'][0]['vt_hex'], '1b5b5b4161')
        self.assertEqual(p['steps'][9]['vt_hex'], '1b5b32317e61')
        self.assertEqual(p['steps'][11]['vt_hex'], '1b5b357e61')
        self.assertEqual(p['steps'][12]['vt_hex'], '1b5b367e61')
        self.assertEqual(p['steps'][16]['vt_hex'], '0161')
        self.assertEqual(p['steps'][19]['vt_hex'], '68656c700d')

    def test_matrix_coordinates_against_retained_active_binary(self):
        names = {**{f'KEY_{i}': i + 1 for i in range(1, 10)}, 'KEY_0': 11,
                 'KEY_LEFTMETA': 125, 'KEY_LEFTSHIFT': 42, 'KEY_RIGHTSHIFT': 54,
                 'KEY_LEFTCTRL': 29, 'KEY_LEFTALT': 56, 'KEY_LEFT': 105,
                 'KEY_UP': 103, 'KEY_DOWN': 108, 'KEY_RIGHT': 106,
                 'KEY_A': 30, 'KEY_H': 35, 'KEY_E': 18, 'KEY_L': 38,
                 'KEY_P': 25, 'KEY_ENTER': 28}
        source = ROOT.parents[1] / '2026-07-12-input-backlight-recovery/results/keyboard-keymap-active-boot.txt'
        observed = {}
        for line in source.read_text().splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[2] in names:
                observed[names[fields[2]]] = (int(fields[0]) << 3) | int(fields[1])
        self.assertEqual(observed, c.SCANS)

    def test_generated_header_and_runtime_budgets(self):
        subprocess.run([sys.executable, str(ROOT / 'render_protocol.py')], check=True, capture_output=True)
        source = (ROOT / 'keyboard-observe.c').read_text()
        for define in ('#define STEP_MS 10000', '#define IDLE_MS 2000',
                       '#define EVENT_LIMIT 64', '#define BYTE_LIMIT 128'):
            self.assertIn(define, source)


if __name__ == '__main__':
    unittest.main()
