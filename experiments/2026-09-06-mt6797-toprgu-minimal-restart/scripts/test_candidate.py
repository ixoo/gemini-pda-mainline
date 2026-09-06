#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline refusal fixtures for the deployment and one-attempt contracts.

The fixtures never open a credential, contact a device, or execute a reboot.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import installer  # noqa: E402
import session as S  # noqa: E402
RUNNER = runpy.run_path(str(HERE / "run-session.py"))

DEPLOYMENT = "11111111-1111-4111-8111-111111111111"
MAINLINE = "22222222-2222-4222-8222-222222222222"
RECOVERY = "33333333-3333-4333-8333-333333333333"
RAW = "a" * 64
PADDED = "b" * 64
INPUT_ID = "c" * 64
WRAPPER = "d" * 64
MANIFEST = "e" * 64
CHECKS = {name: True for name in (
    "raw_exact", "padded_exact", "input_id_exact", "release_exact",
    "boot_id_exact", "usb_only", "authenticated", "serviceable",
    "logger_healthy", "ramoops_exact", "no_userspace_watchdog")}


def records(*, duplicate_entry: bool = False, boot: str = MAINLINE,
            input_id: str = INPUT_ID) -> dict[str, bytes]:
    prefix = S.marker_prefix(input_id, boot).encode("ascii")
    entry = prefix + b" phase=entry\n"
    if duplicate_entry:
        entry += entry
    return {"console-ramoops-0": entry + prefix +
            b" phase=request count=1\n6,9,10,-;reboot: Restarting system\n"}


def fresh() -> S.Session:
    return S.Session(RAW, PADDED, INPUT_ID, WRAPPER, DEPLOYMENT)


def through_request() -> S.Session:
    item = fresh()
    item.select()
    item.bind_mainline(MAINLINE)
    item.preflight(CHECKS, 1)
    item.stable_idle(45, same_boot=True, identities_unchanged=True,
                     automatic_reset=False)
    item.preserve_log("complete-log-through-seal", MANIFEST)
    item.request(S.wrapper_command(MAINLINE))
    return item


class SessionTests(unittest.TestCase):
    def test_one_attempt_pass(self):
        item = through_request()
        item.observe_reset(process_status=255, process_reason=None,
                           stdin_complete=True, request_frame_exact=True,
                           elapsed_seconds=5, disconnected=True)
        result = item.recover(RECOVERY, records(), recovery_kernel="3.18.41+",
                              recovery_arch="aarch64", collector_complete=True)
        self.assertEqual(result["classification"], "toprgu-minimal-restart-pass")
        self.assertTrue(result["consumed"])

    def test_constructor_and_selection_refusals_do_not_consume(self):
        with self.assertRaises(S.Refusal):
            S.Session(RAW, PADDED, "short", WRAPPER, DEPLOYMENT)
        item = fresh()
        with self.assertRaises(S.Refusal):
            item.bind_mainline(MAINLINE)
        self.assertFalse(item.consumed)

    def test_every_postselection_gate_consumes(self):
        item = fresh(); item.select()
        with self.assertRaises(S.Inconclusive): item.bind_mainline(DEPLOYMENT)
        item = fresh(); item.select(); item.bind_mainline(MAINLINE)
        with self.assertRaises(S.Inconclusive): item.preflight({**CHECKS, "logger_healthy": False}, 1)
        item = fresh(); item.select(); item.bind_mainline(MAINLINE); item.preflight(CHECKS, 1)
        with self.assertRaises(S.Inconclusive):
            item.stable_idle(44, same_boot=True, identities_unchanged=True,
                             automatic_reset=False)

    def test_request_and_disconnect_are_exact(self):
        item = fresh(); item.select(); item.bind_mainline(MAINLINE); item.preflight(CHECKS, 1)
        item.stable_idle(45, same_boot=True, identities_unchanged=True,
                         automatic_reset=False)
        item.preserve_log("complete-log-through-seal", MANIFEST)
        with self.assertRaises(S.Inconclusive): item.request(b"/bin/reboot -f\n")
        item = through_request()
        with self.assertRaises(S.Inconclusive):
            item.observe_reset(process_status=255, process_reason=None,
                               stdin_complete=True, request_frame_exact=True,
                               elapsed_seconds=5.001, disconnected=True)

    def test_pstore_attribution_refuses_ambiguity(self):
        values = (records(duplicate_entry=True), records(boot=RECOVERY),
                  {"a": records()["console-ramoops-0"],
                   "b": ("input_id=" + INPUT_ID).encode()})
        for value in values:
            with self.subTest(value=value), self.assertRaises(S.Inconclusive):
                S.classify_pstore(value, mainline_boot_id=MAINLINE,
                                  input_id=INPUT_ID, raw_sha256=RAW,
                                  padded_sha256=PADDED)

    def test_runtime_usb_deadline_consumes_selection(self):
        item = fresh()
        with self.assertRaises(S.Inconclusive):
            S.classify_runtime(
                item, mainline_boot_id=MAINLINE, usb_seconds=91, ssh_seconds=1,
                checks=CHECKS, idle_seconds=45, same_boot=True,
                identities_unchanged=True, automatic_reset=False,
                log_classification="complete-log-through-seal",
                log_manifest_sha256=MANIFEST, command=S.wrapper_command(MAINLINE),
                process_status=255, process_reason=None, stdin_complete=True,
                request_frame_exact=True, disconnect_seconds=1,
                disconnected=True, recovered_boot_id=RECOVERY,
                recovery_kernel="3.18.41+", recovery_arch="aarch64",
                collector_complete=True, pstore_records=records())
        self.assertTrue(item.consumed)

    def test_session_packet_matches_classifier(self):
        packet = json.loads((HERE.parent / "session-packet.json").read_text())
        self.assertEqual(packet["transport"]["usb_deadline_seconds"], S.USB_DEADLINE)
        self.assertEqual(packet["transport"]["ssh_exchange_deadline_seconds"], S.SSH_DEADLINE)
        self.assertEqual(packet["postselection"]["stable_idle_seconds_minimum"], S.IDLE_MINIMUM)
        self.assertEqual(packet["postselection"]["disconnect_reset_bound_seconds"], S.RESET_GOOD)
        self.assertEqual(packet["markers"]["wrapper_contract"], S.WRAPPER_CONTRACT)


class InstallerTests(unittest.TestCase):
    SWAP_HEADER = "Filename Type Size Used Priority\n"
    ZRAM_ROW = "/dev/block/zram0 partition 1930336 0 -1\n"

    def run_swap_policy(self, swaps: str, *, node_identity: str =
                        "block special file fe:0", sys_device: str = "254:0\n",
                        disk_size: str = "1976668160\n", backing: bool = False,
                        dangling_backing: bool = False, writeback: bool = False,
                        change_after_read: bool = False) -> int:
        with tempfile.TemporaryDirectory(prefix="toprgu-swap-") as raw:
            root = Path(raw).resolve()
            (root / "proc").mkdir()
            (root / "proc/swaps").write_text(swaps)
            (root / "dev/block").mkdir(parents=True)
            (root / "dev/zram0").write_bytes(b"")
            (root / "dev/block/zram0").symlink_to("../zram0")
            zram_class = root / "sys/class/block/zram0"
            zram_block = root / "sys/block/zram0"
            zram_class.mkdir(parents=True)
            zram_block.mkdir(parents=True)
            (zram_class / "dev").write_text(sys_device)
            (zram_class / "disksize").write_text(disk_size)
            if backing:
                (zram_class / "backing_dev").write_text("8:0\n")
            if dangling_backing:
                (zram_class / "backing_dev").symlink_to("missing")
            if writeback:
                (zram_block / "writeback_limit_enable").write_text("1\n")

            policy = installer.TOPRGU_SWAP_POLICY
            policy = policy.replace("cat -- /proc/swaps",
                                    "cat -- " + str(root / "proc/swaps"))
            policy = policy.replace("readlink -f -- /dev/block/zram0",
                                    "readlink -f -- " + str(root / "dev/block/zram0"))
            policy = policy.replace('[[ "$canonical" == /dev/zram0 ]]',
                                    '[[ "$canonical" == ' + str(root / "dev/zram0") + " ]]")
            for live, fixture in {
                    "/sys/class/block/zram0/dev": zram_class / "dev",
                    "/sys/class/block/zram0/disksize": zram_class / "disksize",
                    "/sys/class/block/zram0/backing_dev": zram_class / "backing_dev",
                    "/sys/block/zram0/backing_dev": zram_block / "backing_dev",
                    "/sys/class/block/zram0/writeback_limit_enable":
                        zram_class / "writeback_limit_enable",
                    "/sys/block/zram0/writeback_limit_enable":
                        zram_block / "writeback_limit_enable"}.items():
                policy = policy.replace(live, str(fixture))
            policy = policy.replace("a53_no_swap", "toprgu_staging_swap_policy")
            counter = root / "swap-reads"
            changed = root / "changed-swaps"
            changed.write_text(self.SWAP_HEADER +
                               "/dev/block/zram0 partition 1930336 1 -1\n")
            script = root / "policy.sh"
            script.write_text(
                "#!/bin/bash\nset -u\n" +
                "stat() { printf '%s\\n' \"$NODE_IDENTITY\"; }\n" +
                "cat() {\n"
                "  local last=${!#}\n"
                "  if [[ \"$CHANGE_AFTER_READ\" == 1 && \"$last\" == \"$SWAPS_PATH\" ]]; then\n"
                "    if [[ -e \"$READ_COUNTER\" ]]; then command cat -- \"$CHANGED_SWAPS\"; else : >\"$READ_COUNTER\"; command cat \"$@\"; fi\n"
                "  else command cat \"$@\"; fi\n"
                "}\n" + policy + "\n"
                "toprgu_staging_swap_policy\n")
            result = subprocess.run(
                ["bash", str(script)], check=False,
                env={"PATH": "/usr/bin:/bin", "NODE_IDENTITY": node_identity,
                     "CHANGE_AFTER_READ": "1" if change_after_read else "0",
                     "SWAPS_PATH": str(root / "proc/swaps"),
                     "READ_COUNTER": str(counter), "CHANGED_SWAPS": str(changed)},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            return result.returncode

    def test_source_pins_and_single_write_closure_are_explicit(self):
        source = Path(installer.__file__).read_text()
        for token in ("EXPECTED_PREDECESSOR_SHA256", 'source.count(\'of="$target"\') == 1',
                      'dd if="$EXPECTED_STAGE" of="$target"',
                      'blockdev --flushbufs "$target"',
                      'cmp -s "$candidate" "$readback_tmp"',
                      "sudo -n systemctl poweroff"):
            self.assertIn(token, source)

    def test_exact_ram_only_zram_swap_policy(self):
        self.assertEqual(self.run_swap_policy(self.SWAP_HEADER), 0)
        self.assertEqual(self.run_swap_policy(self.SWAP_HEADER + self.ZRAM_ROW), 0)
        mutations = {
            "used": self.ZRAM_ROW.replace(" 0 -1", " 1 -1"),
            "extra": self.ZRAM_ROW + "/dev/zram1 partition 1 0 -2\n",
            "path": self.ZRAM_ROW.replace("/dev/block/zram0", "/dev/zram0"),
            "type": self.ZRAM_ROW.replace("partition", "file"),
            "size": self.ZRAM_ROW.replace("1930336", "1930335"),
            "priority": self.ZRAM_ROW.replace("-1", "-2"),
        }
        for label, rows in mutations.items():
            with self.subTest(label=label):
                self.assertNotEqual(self.run_swap_policy(self.SWAP_HEADER + rows), 0)
        for label, arguments in {
                "node-type": {"node_identity": "regular file fe:0"},
                "node-number": {"node_identity": "block special file fe:1"},
                "sys-device": {"sys_device": "254:1\n"},
                "disk-size": {"disk_size": "1976668159\n"},
                "backing": {"backing": True},
                "dangling-backing": {"dangling_backing": True},
                "writeback": {"writeback": True},
                "changed": {"change_after_read": True}}.items():
            with self.subTest(label=label):
                self.assertNotEqual(
                    self.run_swap_policy(self.SWAP_HEADER + self.ZRAM_ROW, **arguments), 0)

    def test_active_adapter_preserves_historical_source_and_never_mutates_swap(self):
        baseline = installer.BASELINE_INSTALLER.read_text()
        self.assertEqual(hashlib.sha256(baseline.encode()).hexdigest(),
                         installer.BASELINE_INSTALLER_SHA256)
        source = Path(installer.__file__).read_text()
        self.assertIn("toprgu_staging_swap_policy", source)
        self.assertIn("BASELINE_SWAP_POLICY", source)
        self.assertNotIn("swapoff", installer.TOPRGU_SWAP_POLICY)
        self.assertNotIn("swapon", installer.TOPRGU_SWAP_POLICY)

    def test_deriver_rejects_malformed_predecessor_before_inputs(self):
        with self.assertRaisesRegex(ValueError, "predecessor"):
            installer.derive(Path("missing"), Path("missing"), Path("missing"), "short")


class RunnerTests(unittest.TestCase):
    def test_directory_publication_precedes_selection_marker_and_prompt(self):
        with tempfile.TemporaryDirectory(prefix="toprgu-dirs-") as raw:
            base = Path(raw)
            target = base / "new-parent" / "attempt"
            events = []

            def sync(path):
                events.append(("sync", Path(path)))

            mkdir_globals = RUNNER["mkdir_durable"].__globals__
            persist_globals = RUNNER["persist_selection_checkpoint"].__globals__
            with mock.patch.dict(mkdir_globals, {"sync_directory": sync}), \
                 mock.patch.dict(persist_globals, {"sync_directory": sync}):
                RUNNER["mkdir_durable"](target, parents=True)
                events.append(("directory-published", target))
                RUNNER["persist_selection_checkpoint"](target)
                events.append(("prompt", target))
            self.assertEqual([event[0] for event in events],
                             ["sync", "sync", "sync", "sync", "directory-published",
                              "sync", "sync", "prompt"])
            self.assertEqual(events[0][1], target.parent)
            self.assertEqual(events[1][1], base)
            self.assertEqual(events[2][1], target)
            self.assertEqual(events[3][1], target.parent)

            failed = base / "failed-parent" / "attempt"

            def fail_parent(path):
                if Path(path) == failed.parent:
                    raise OSError("parent publication fsync failed")

            with mock.patch.dict(mkdir_globals, {"sync_directory": fail_parent}):
                with self.assertRaises(OSError):
                    RUNNER["mkdir_durable"](failed, parents=True)
            self.assertFalse(failed.exists())

            wrong_mode = base / "wrong-mode"
            wrong_mode.mkdir(mode=0o755)
            wrong_mode.chmod(0o755)
            with self.assertRaises(ValueError):
                RUNNER["mkdir_durable"](wrong_mode, parents=False)

    def test_result_transaction_never_exposes_pass_on_checksum_failure(self):
        with tempfile.TemporaryDirectory(prefix="toprgu-result-") as raw:
            attempt = Path(raw)
            attempt.chmod(0o700)
            evidence = attempt / "evidence.txt"
            evidence.write_bytes(b"evidence\n")
            evidence.chmod(0o600)
            prospective = {"classification": "toprgu-minimal-restart-pass", "consumed": True}
            publish_globals = RUNNER["publish_attempt_result"].__globals__
            original_write = publish_globals["write_new"]

            def fail_before_checksum(path, data, mode=0o600):
                if Path(path).name == ".SHA256SUMS.pending":
                    raise OSError("checksum publication preparation failed")
                return original_write(path, data, mode)

            with mock.patch.dict(publish_globals, {"write_new": fail_before_checksum}):
                with self.assertRaises(OSError):
                    RUNNER["publish_attempt_result"](attempt, prospective)
            self.assertFalse((attempt / "result.json").exists())
            self.assertFalse((attempt / "SHA256SUMS").exists())
            self.assertFalse((attempt / ".result.json.pending").exists())
            self.assertFalse((attempt / ".SHA256SUMS.pending").exists())

            publish_globals["write_new"] = original_write
            original_replace = RUNNER["os"].replace

            def fail_checksum_replace(source, destination):
                if Path(source).name == ".SHA256SUMS.pending":
                    raise OSError("checksum publication failed")
                return original_replace(source, destination)

            with mock.patch.object(RUNNER["os"], "replace", side_effect=fail_checksum_replace):
                with self.assertRaises(OSError):
                    RUNNER["publish_attempt_result"](attempt, prospective)
            self.assertFalse((attempt / "result.json").exists())
            self.assertFalse((attempt / "SHA256SUMS").exists())
            self.assertFalse((attempt / ".result.json.pending").exists())
            self.assertFalse((attempt / ".SHA256SUMS.pending").exists())

            publish_globals["write_new"] = original_write
            with mock.patch.dict(publish_globals, {"sync_directory": mock.Mock(
                    side_effect=[None, None, OSError("final directory fsync failed"), None])}):
                with self.assertRaises(OSError):
                    RUNNER["publish_attempt_result"](attempt, prospective)
            self.assertFalse((attempt / "result.json").exists())
            self.assertFalse((attempt / "SHA256SUMS").exists())
            self.assertFalse((attempt / ".result.json.pending").exists())
            self.assertFalse((attempt / ".SHA256SUMS.pending").exists())

            completed = {"classification": "toprgu-minimal-restart-pass", "consumed": True}
            RUNNER["publish_attempt_result"](attempt, completed)
            result_bytes = (json.dumps(completed, indent=2, sort_keys=True) + "\n").encode()
            self.assertEqual(json.loads((attempt / "result.json").read_text()), completed)
            self.assertIn(RUNNER["digest"](result_bytes) + "  result.json\n",
                          (attempt / "SHA256SUMS").read_text())
            self.assertFalse((attempt / ".result.json.pending").exists())
            self.assertFalse((attempt / ".SHA256SUMS.pending").exists())

    def test_postselection_preservation_exceptions_are_inconclusive(self):
        class PollFailure:
            def poll(self):
                raise OSError("poll failed")

        class WriteFailure:
            def write(self, _data):
                raise InterruptedError("second signal")

            def flush(self):
                raise AssertionError("flush must not run after write failure")

            def fileno(self):
                return -1

        with self.assertRaises(S.Inconclusive):
            RUNNER["preserve_collector_after_failure"](PollFailure(), WriteFailure())

        class LiveCollector:
            def __init__(self):
                self.communicate_calls = 0

            def poll(self):
                return None

            def communicate(self, timeout):
                self.communicate_calls += 1
                return b"collector\n", b""

        drained_state = {"drained": False}
        with self.assertRaises(S.Inconclusive):
            RUNNER["preserve_collector_after_failure"](LiveCollector(), WriteFailure(),
                                                        drain_state=drained_state)
        self.assertTrue(drained_state["drained"])

        class CaptureLog:
            def __init__(self):
                self.data = b""

            def write(self, data):
                self.data += data

            def flush(self):
                return None

            def fileno(self):
                return 1

        class CommunicateFailure:
            def __init__(self):
                self.communicate_calls = 0

            def poll(self):
                return 0

            def communicate(self, timeout):
                self.communicate_calls += 1
                raise subprocess.TimeoutExpired("collector", timeout)

        failed = CommunicateFailure()
        failed_state = {"attempted": False, "drained": False}
        with self.assertRaises(S.Inconclusive):
            RUNNER["preserve_collector_after_failure"](failed, CaptureLog(),
                                                        drain_state=failed_state)
        self.assertEqual(failed.communicate_calls, 1)
        self.assertTrue(failed_state["attempted"])
        self.assertFalse(failed_state["drained"])
        self.assertFalse(RUNNER["preserve_collector_after_failure"](
            failed, CaptureLog(), drain_state=failed_state))
        self.assertEqual(failed.communicate_calls, 1)

        class ExitedCollector:
            def __init__(self):
                self.communicate_calls = 0

            def poll(self):
                return 0

            def communicate(self, timeout):
                self.communicate_calls += 1
                return b"already-exited\n", b""

        exited = ExitedCollector()
        captured = CaptureLog()
        with mock.patch.object(RUNNER["os"], "fsync"):
            self.assertTrue(RUNNER["preserve_collector_after_failure"](exited, captured))
        self.assertEqual(exited.communicate_calls, 1)
        self.assertEqual(captured.data, b"already-exited\n")

    def test_postselection_cleanup_and_main_failure_use_durable_marker(self):
        class Collector:
            pid = 1

            def poll(self):
                return None

            def wait(self, timeout):
                return None

        class Log:
            def close(self):
                raise OSError("close failed")

        with tempfile.TemporaryDirectory(prefix="toprgu-checkpoint-") as raw:
            attempt = Path(raw)
            attempt.chmod(0o700)
            RUNNER["persist_selection_checkpoint"](attempt)
            with mock.patch.object(RUNNER["os"], "killpg"), \
                 mock.patch.object(RUNNER["signal"], "signal", side_effect=InterruptedError("restore interrupted")):
                with self.assertRaises(S.Inconclusive):
                    RUNNER["cleanup_after_execute"](attempt, Collector(), Log(), {1: object()})
            result = RUNNER["classify_failure"](attempt, OSError("arbitrary postselection failure"))
            self.assertEqual(result["classification"], "inconclusive")
            self.assertTrue(result["consumed"])

            preselection = attempt / "preselection"
            preselection.mkdir(mode=0o700)
            result = RUNNER["classify_failure"](preselection, OSError("collector arm failed"))
            self.assertEqual(result["classification"], "refusal")
            self.assertFalse(result["consumed"])

            # A cleanup failure before the durable selection gate is still a
            # raw refusal; it must not be hidden by post-selection wrapping.
            with self.assertRaises(OSError):
                RUNNER["cleanup_after_execute"](preselection, Collector(), Log(), {1: object()})
            result = RUNNER["classify_failure"](preselection, OSError("cleanup failed"))
            self.assertEqual(result["classification"], "refusal")
            self.assertFalse(result["consumed"])

            failed_checkpoint = attempt / "failed-checkpoint"
            failed_checkpoint.mkdir(mode=0o700)
            with mock.patch.dict(RUNNER["persist_selection_checkpoint"].__globals__, {"sync_directory": mock.Mock(
                    side_effect=[None, OSError("directory fsync failed")])}):
                with self.assertRaises(OSError):
                    RUNNER["persist_selection_checkpoint"](failed_checkpoint)
            self.assertFalse(RUNNER["selection_consumed"](failed_checkpoint))

    def test_recovery_collector_is_strict_and_single_cycle(self):
        source = RUNNER["strict_collector_source"]().decode()
        self.assertNotIn("StrictHostKeyChecking=accept-new", source)
        for token in ("StrictHostKeyChecking=yes", "UserKnownHostsFile=",
                      "GlobalKnownHostsFile=/dev/null", "UpdateHostKeys=no"):
            self.assertIn(token, source)
        runner = Path(HERE / "run-session.py").read_text()
        self.assertEqual(runner.count('"--wait-for-cycle"'), 1)
        self.assertEqual(runner.count("state.request(S.wrapper_command(boot))"), 1)
        self.assertIn('restart_script(context["candidate"], boot, attempt)', runner)
        self.assertIn('"restart-request", restart, S.SSH_DEADLINE', runner)
        self.assertNotIn("while time.monotonic() - started", runner)

    def test_remote_preflight_is_read_only_and_identity_bound(self):
        members = {name: {"sha256": "f" * 64} for name in
                   ("init", "bin/busybox", "bin/reboot", "bin/kmsg-capture", "bin/kmsg-seal")}
        source = RUNNER["preflight_script"]({"members": members}).decode()
        for token in (S.RELEASE, "usb_ipv4_exact_count", "logger_healthy",
                      "ramoops_exact", "userspace_watchdog_count"):
            self.assertIn(token, source)
        self.assertIn("/run/a53/boot-id", source)
        self.assertNotIn("/run/toprgu/boot-id", source)
        for token in (">/sys/", "/dev/mmc", "/dev/watchdog"):
            self.assertNotIn(token, source)

    def test_disconnect_requires_exact_bounded_observation(self):
        process = {"exit_status": 255, "reason": None, "stdin_complete": True,
                   "elapsed_seconds": 4.999}
        self.assertTrue(RUNNER["disconnect_evidence"](
            b"", b"Connection to 10.15.19.82 closed by remote host.\n", process))
        for mutation in ({"exit_status": 0}, {"reason": "outer-timeout"},
                         {"stdin_complete": False}, {"elapsed_seconds": 5.001}):
            self.assertFalse(RUNNER["disconnect_evidence"](b"", b"", process | mutation))
        self.assertFalse(RUNNER["disconnect_evidence"](b"", b"Permission denied\n", process))

    def test_preaction_export_is_manifested_before_admission(self):
        with tempfile.TemporaryDirectory(prefix="toprgu-seal-") as raw:
            attempt = Path(raw); attempt.chmod(0o700)
            phase = attempt / "pre-action-seal"; phase.mkdir(mode=0o700)
            for name in ("command.sh", "stdout.txt", "stderr.txt", "process.json"):
                path = phase / name; path.write_bytes(name.encode()); path.chmod(0o600)
            parsed = {"files": {"kmsg.log": b"log\n", "kmsg.status": b"status\n", "kmsg-exit": b"0\n"},
                      "result": {"classification": "complete-log-through-seal",
                                 "preservation_complete": True}}
            manifest = RUNNER["preserve_seal"](attempt, parsed)
            self.assertRegex(manifest, r"^[0-9a-f]{64}$")
            sums = (phase / "SHA256SUMS").read_text()
            self.assertIn("exported/kmsg.log", sums)
            self.assertIn("classification.json", sums)
            candidate = {"members": {name: {"sha256": "f" * 64} for name in
                                       ("init", "bin/busybox", "bin/reboot", "bin/kmsg-capture", "bin/kmsg-seal")}}
            restart = RUNNER["restart_script"](candidate, MAINLINE, attempt)
            self.assertIn(b'[ "$boot" = "' + MAINLINE.encode() + b'" ]', restart)
            self.assertIn(b"kmsg.log|4|", restart)
            self.assertIn(b"kmsg.status|7|", restart)
            self.assertIn(b"kmsg-exit|2|", restart)
            self.assertIn(b"kmsg.status.partial", restart)
            self.assertIn(b'exec /bin/reboot "$boot"', restart)
            subprocess.run(["/bin/bash", "-n"], input=restart, check=True)

    def test_wrapper_rechecks_host_boot_identity_before_effect(self):
        wrapper = (HERE.parent / "initramfs" / "reboot-toprgu").read_text()
        self.assertIn('[ "$#" -eq 1 ]', wrapper)
        self.assertIn("expected_boot=$1", wrapper)
        self.assertGreaterEqual(wrapper.count("/proc/sys/kernel/random/boot_id"), 2)
        self.assertGreaterEqual(wrapper.count("/run/a53/boot-id"), 2)
        self.assertIn('[ "$boot_id" = "$expected_boot" ]', wrapper)
        self.assertIn('exec /bin/busybox reboot -n -f', wrapper)

    def test_collector_capture_is_cycle_and_archive_bound(self):
        with tempfile.TemporaryDirectory(prefix="toprgu-pstore-") as raw:
            capture = Path(raw); capture.chmod(0o700)
            pstore = capture / "pstore"; pstore.mkdir(mode=0o700)
            record = pstore / "console-ramoops-0"; record.write_bytes(b"retained\n"); record.chmod(0o600)
            initial = DEPLOYMENT
            recovered = RECOVERY
            initial_hash = hashlib.sha256((initial + "\n").encode()).hexdigest()
            final_hash = hashlib.sha256((recovered + "\n").encode()).hexdigest()
            cycle = ("wait_for_cycle=yes\ncycle_started_utc=x\ndisconnect_observed_utc=y\n"
                     "reconnect_observed_utc=z\ninitial_boot_id_sha256=" + initial_hash +
                     "\nfinal_boot_id_sha256=" + final_hash + "\nboot_id_changed=yes\n"
                     "capture_kernel=3.18.41+\ncapture_arch=aarch64\nexpected_kernel=3.18.41+\n"
                     "archive_pre_boot_id_sha256=" + final_hash +
                     "\narchive_post_boot_id_sha256=" + final_hash + "\n")
            metadata = "kernel=3.18.41+\narchitecture=aarch64\nboot_id_sha256=" + final_hash + "\n"
            members = "./\n./console-ramoops-0\n"
            for name, data in (("cycle.txt", cycle.encode()), ("metadata.txt", metadata.encode()),
                               ("pstore-members.txt", members.encode()),
                               ("pstore-members-verbose.txt", b"- file ./console-ramoops-0\n"),
                               ("candidate-l-evidence.txt", b"legacy-supplement-only\n")):
                path = capture / name; path.write_bytes(data); path.chmod(0o600)
            with tarfile.open(capture / "pstore.tar", "w") as archive:
                info = tarfile.TarInfo("./console-ramoops-0"); info.size = len(b"retained\n"); info.mode = 0o600
                archive.addfile(info, io.BytesIO(b"retained\n"))
            (capture / "pstore.tar").chmod(0o600)
            lines = []
            for path in sorted(capture.rglob("*")):
                if path.is_file() and path.name != "SHA256SUMS":
                    lines.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  ./" +
                                 path.relative_to(capture).as_posix() + "\n")
            sums = capture / "SHA256SUMS"; sums.write_text("".join(lines)); sums.chmod(0o600)
            found = RUNNER["validate_collector_capture"](capture, initial, recovered)
            self.assertEqual(found, {"console-ramoops-0": b"retained\n"})
            record.write_bytes(b"changed\n")
            with self.assertRaises(ValueError):
                RUNNER["validate_collector_capture"](capture, initial, recovered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
