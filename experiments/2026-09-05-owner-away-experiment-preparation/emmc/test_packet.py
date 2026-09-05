#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Confined host or exact-BusyBox/QEMU fixtures; hardware stays mocked.

Exact mode: EMMC_TEST_BUSYBOX and EMMC_TEST_WORK_ROOT are required together.
EMMC_TEST_QEMU defaults to qemu-aarch64 or qemu-aarch64-static on PATH.
EMMC_TEST_BUSYBOX_SHA256 can
add an expected binary pin; the actual digest is always reported. No device or
network access is performed. See README.md for the remaining evidence limits.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("emmc_classifier", HERE / "classify.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load eMMC classifier")
CLASSIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSIFIER)
BOOT = "11111111-2222-3333-4444-555555555555"
RELEASE = "7.1.3-gemini-fixture"
PADDED_SHA = hashlib.sha256(bytes(16777216)).hexdigest()

# The dispatcher has command/argument and path gates, independent of Python
# assertions. Ordinary applets use real BusyBox/QEMU in exact mode. Hardware
# identity, partition bytes, and the observer's timeout effect are simulated.
MOCK = r'''#!/usr/bin/env python3
import hashlib, json, os, pathlib, re, subprocess, sys

def require(condition, reason):
    if not condition:
        raise RuntimeError("fixture refusal: " + reason)

root = pathlib.Path(os.environ["EMMC_FIXTURE_ROOT"]).resolve(strict=True)
require(root.name.startswith("gemini-emmc-fixture-"), "managed fixture root")
require(root.is_dir() and not (root.stat().st_mode & 0o077), "private fixture root")
prefix = json.loads(os.environ.get("EMMC_FIXTURE_EXACT_PREFIX", "[]"))
require(isinstance(prefix, list) and len(prefix) in (0, 2), "exact executable prefix")

def confined(value, follow=True):
    path = pathlib.Path(value)
    require(path.is_absolute() and ".." not in path.parts, "absolute nontraversing path")
    require(path.is_relative_to(root), "path outside fixture")
    require(path.parent.resolve().is_relative_to(root), "parent symlink escape")
    if follow:
        require(path.resolve().is_relative_to(root), "symlink escape")
    return path

def run_applet(name, values):
    with (root / "applet-calls.jsonl").open("a") as record:
        record.write(json.dumps({"mode": "exact" if prefix else "host", "applet": name}) + "\n")
    executable = [*prefix, name] if prefix else ["/bin/sh" if name=="sh" else name]
    return subprocess.run([*executable, *values]).returncode

require(len(sys.argv) > 1, "missing applet")
cmd, *args = sys.argv[1:]
with (root / "dispatch-calls.jsonl").open("a") as record:
    record.write(json.dumps({"applet": cmd, "args": [value.replace(str(root), "<fixture>")[:512] for value in args[:8]]}) + "\n")
if cmd == "readlink":
    require(len(args) == 1 or (len(args)==2 and args[0]=="-f"), "readlink arguments")
    path = confined(args[-1], follow="-f" in args)
    if "-f" in args:
        print(path.resolve(strict=True))
    else:
        require(path in (root/"proc/self/ns/mnt", root/"proc/1/ns/mnt"), "namespace path")
        value = os.readlink(path)
        require(re.fullmatch(r"mnt:\[[0-9]+\]", value) is not None, "namespace fixture value")
        print(value)
elif cmd == "stat":
    require(len(args)==4 and args[:3]==["-L", "-c", "%F|%t:%T"], "stat arguments")
    path = confined(args[-1])
    require(path.parent==root/"dev" and re.fullmatch(r"mmcblk0(?:p[1-9][0-9]*)?", path.name), "stat node")
    value = "block special file|b3:1e" if "mmcblk0p" in args[-1] else "block special file|b3:0"
    print(os.environ.get("EMMC_FIXTURE_STAT", value))
elif cmd == "uname":
    require(args in (["-m"], ["-r"]), "uname arguments")
    print("aarch64" if args==["-m"] else "7.1.3-gemini-fixture")
elif cmd == "sha256sum":
    require(len(args)<=1, "hash arguments")
    if args: confined(args[0])
    if prefix:
        sys.exit(run_applet(cmd, args))
    data = pathlib.Path(args[0]).read_bytes() if args else sys.stdin.buffer.read()
    print(hashlib.sha256(data).hexdigest() + "  " + (args[0] if args else "-"))
elif cmd == "dmesg":
    require(not args, "dmesg arguments")
    print(os.environ.get("EMMC_FIXTURE_LOG", "mmc0: card initialized"))
elif cmd == "dd":
    require(len(args)==3 and args[1:]==["bs=4096", "count=4096"], "dd bounds")
    require(args[0].startswith("if="), "dd input-only")
    path = confined(args[0][3:])
    require(path.parent==root/"dev" and re.fullmatch(r"mmcblk0p[1-9][0-9]*", path.name), "dd target")
    with (root / "reads").open("a") as f: f.write("one\n")
    mode = os.environ.get("EMMC_FIXTURE_DD", "pass")
    require(mode in ("pass", "short", "interrupt"), "dd fixture mode")
    if mode=="interrupt": os._exit(7)
    sys.stdout.buffer.write(bytes(16777216 if mode=="pass" else 4096))
    sys.exit(0)
elif cmd == "timeout":
    require(len(args)==8 and args[:3]==["-s", "KILL", "20"], "timeout arguments")
    require(args[3]==str(root/"bin/busybox") and args[4]=="dd", "timeout direct worker")
    require(args[5].startswith("if=") and args[6:]==["bs=4096", "count=4096"], "timeout read bounds")
    confined(args[5][3:])
    if os.environ.get("EMMC_FIXTURE_DD")=="timeout": sys.exit(137)
    sys.exit(subprocess.run(args[3:], timeout=10).returncode)
else:
    require(cmd in ("cat", "cut", "grep", "awk", "find", "mkdir", "rm", "date"), "unreviewed applet")
    if cmd=="cat":
        require(len(args)==1, "cat arguments")
        confined(args[0])
    elif cmd=="cut":
        require(len(args) in (4,5) and args[:4]==["-d", " ", "-f", "1"], "cut arguments")
        if len(args)==5: confined(args[4])
    elif cmd=="grep":
        require(len(args) in (2,3) and args[0] in ("-Eq", "-Eic"), "grep arguments")
        if len(args)==3: confined(args[2])
    elif cmd=="awk":
        if args and args[0]=="-F=": args=args[1:]; options=["-F="]
        else: options=[]
        require(len(args)==2, "awk arguments")
        programs=json.loads(os.environ["EMMC_FIXTURE_AWK_HASHES"])
        require(hashlib.sha256(args[0].encode()).hexdigest() in programs, "awk program")
        confined(args[1])
        args=options+args
    elif cmd=="find":
        require(len(args)==6 and args[1:]==["-mindepth", "1", "-maxdepth", "1", "-print"], "find arguments")
        confined(args[0])
    elif cmd=="mkdir":
        require(args==["-m", "700", str(root/"run/gemini-emmc-readonly")], "mkdir target")
        confined(args[-1])
    elif cmd=="rm":
        require(len(args)==6 and args[0]=="-f", "cleanup arguments")
        for value in args[1:]:
            path=confined(value, follow=False)
            require(path.parent==root/"run/gemini-emmc-readonly" and path.name in
                    ("dd.status", "dd.stderr", "read.sha", "log.before", "log.after"), "cleanup target")
    elif cmd=="date":
        require(args==["+%s"], "date arguments")
    sys.exit(run_applet(cmd, args))
'''


def exact_configuration():
    binary = os.environ.get("EMMC_TEST_BUSYBOX")
    work = os.environ.get("EMMC_TEST_WORK_ROOT")
    if binary and not work:
        raise RuntimeError("exact BusyBox mode requires an explicit EMMC_TEST_WORK_ROOT")
    root = Path(work or "/tmp").resolve(strict=True)
    if not root.is_dir() or root == Path("/") or any(root.is_relative_to(Path(item)) for item in ("/dev", "/proc", "/sys")):
        raise RuntimeError("unsafe test work root")
    if not binary:
        if os.environ.get("EMMC_TEST_QEMU") or os.environ.get("EMMC_TEST_BUSYBOX_SHA256"):
            raise RuntimeError("exact emulator/digest needs EMMC_TEST_BUSYBOX")
        return root, [], None
    busybox = Path(binary).resolve(strict=True)
    if not busybox.is_file():
        raise RuntimeError("BusyBox must be a regular file")
    digest = hashlib.sha256(busybox.read_bytes()).hexdigest()
    expected = os.environ.get("EMMC_TEST_BUSYBOX_SHA256")
    if expected is not None and expected != digest:
        raise RuntimeError("BusyBox expected SHA-256 mismatch")
    configured = os.environ.get("EMMC_TEST_QEMU")
    choices = [configured] if configured else ["qemu-aarch64", "qemu-aarch64-static"]
    emulator = next((resolved for name in choices if (resolved := shutil.which(name))), None)
    if emulator is None:
        raise RuntimeError("exact mode requires qemu-aarch64 or qemu-aarch64-static on PATH")
    canonical_emulator = Path(emulator).resolve(strict=True)
    if not canonical_emulator.is_file() or not os.access(canonical_emulator, os.X_OK):
        raise RuntimeError("exact mode requires a regular qemu-aarch64 executable")
    return root, [str(canonical_emulator), str(busybox)], digest


FIXTURE_STREAM_LIMITS = {'stdout': 131072, 'stderr': 16384}
FIXTURE_CLEANUP_SECONDS = 1


class FixtureRunError(ValueError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__(json.dumps(diagnostic, sort_keys=True))


def bounded_process(command, environment, timeout=30):
    """Bound only a fresh, disposable fixture group and its captured output."""
    started = time.monotonic()
    deadline = started + timeout
    buffers = {name: bytearray() for name in FIXTURE_STREAM_LIMITS}
    selector = selectors.DefaultSelector()
    process, reason = None, None
    interrupted, handlers = [], {}

    def drain(wait):
        nonlocal reason
        for key, _ in selector.select(wait):
            try:
                data = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                continue
            if not data:
                selector.unregister(key.fileobj)
                key.fileobj.close()
                continue
            name = key.data
            available = FIXTURE_STREAM_LIMITS[name] - len(buffers[name])
            buffers[name].extend(data[:available])
            if len(data) > available:
                reason = reason or name + '-limit'

    def signal_group(number):
        if process is not None:
            try:
                os.killpg(process.pid, number)
            except ProcessLookupError:
                pass

    try:
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[number] = signal.signal(number, lambda received, _frame: interrupted.append(received))
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=environment, start_new_session=True)
        for name in FIXTURE_STREAM_LIMITS:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map() or process.poll() is None:
            if interrupted:
                reason = 'fixture-interrupted-' + str(interrupted[0])
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = 'fixture-timeout'
                break
            drain(min(0.05, remaining))
            if reason:
                break
    finally:
        cleanup_deadline = time.monotonic() + FIXTURE_CLEANUP_SECONDS
        signal_group(signal.SIGTERM)
        grace = min(cleanup_deadline, time.monotonic() + 0.1)
        while process is not None and time.monotonic() < grace:
            if selector.get_map():
                drain(min(0.02, max(0, grace - time.monotonic())))
            else:
                time.sleep(min(0.01, max(0, grace - time.monotonic())))
        if process is not None:
            process.poll()
        signal_group(signal.SIGKILL)
        if process is not None:
            try:
                process.wait(timeout=max(0.01, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                reason = reason or 'fixture-cleanup-timeout'
            while selector.get_map() and time.monotonic() < cleanup_deadline:
                drain(min(0.02, max(0, cleanup_deadline - time.monotonic())))
            for name in FIXTURE_STREAM_LIMITS:
                stream = getattr(process, name)
                if stream and not stream.closed:
                    stream.close()
        selector.close()
        for number, previous in handlers.items():
            signal.signal(number, previous)
    if interrupted:
        reason = reason or 'fixture-interrupted-' + str(interrupted[0])
    if reason:
        recent = []
        root_text = environment.get('EMMC_FIXTURE_ROOT')
        if root_text:
            root = Path(root_text)
            trace = root / 'dispatch-calls.jsonl'
            if (root.name.startswith('gemini-emmc-fixture-') and root.is_dir() and not root.is_symlink()
                    and trace.is_file() and not trace.is_symlink()):
                with trace.open('rb') as stream:
                    size = stream.seek(0, os.SEEK_END)
                    stream.seek(max(0, size - 8192))
                    lines = stream.read(8192).splitlines()
                if size > 8192:
                    lines = lines[1:]
                recent = [line[-1024:].decode('utf-8', errors='backslashreplace') for line in lines[-8:]]
        raise FixtureRunError({'classification': 'emmc-fixture-runner-failed', 'reason': reason,
            'fixture_timeout_seconds': timeout, 'fixture_cleanup_seconds': FIXTURE_CLEANUP_SECONDS,
            'elapsed_seconds': round(time.monotonic() - started, 3),
            'return_code': process.returncode if process else None,
            'captured_bytes': {name: len(data) for name, data in buffers.items()},
            'stdout_tail': bytes(buffers['stdout'][-4096:]).decode('utf-8', errors='backslashreplace'),
            'stderr_tail': bytes(buffers['stderr'][-4096:]).decode('utf-8', errors='backslashreplace'),
            'recent_dispatches': recent})
    return subprocess.CompletedProcess(command, process.returncode,
                                       bytes(buffers['stdout']).decode(), bytes(buffers['stderr']).decode())

class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work_root, cls.exact_prefix, cls.actual_busybox_sha = exact_configuration()
        print("emmc_fixture_mode=" + ("exact-busybox-qemu" if cls.exact_prefix else "host-mocked-busybox"), flush=True)
        print("observer_fixture_timeout_seconds=" + str(90 if cls.exact_prefix else 30), flush=True)
        if cls.actual_busybox_sha:
            print("actual_busybox_sha256=" + cls.actual_busybox_sha, flush=True)
            print("qemu_executable_sha256=" + hashlib.sha256(Path(cls.exact_prefix[0]).read_bytes()).hexdigest(), flush=True)
            print("observer_busybox_identity=fixture-dispatcher-hash", flush=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gemini-emmc-fixture-", dir=self.work_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("EMMC_FIXTURE_")}
        self.env.update({"EMMC_FIXTURE_ROOT": str(self.root), "EMMC_FIXTURE_EXACT_PREFIX": json.dumps(self.exact_prefix)})
        self.write("bin/busybox", MOCK)
        self.bb = self.root / "bin/busybox"
        self.bb.chmod(0o700)
        self.bb_sha = hashlib.sha256(self.bb.read_bytes()).hexdigest()
        self.write("proc/sys/kernel/random/boot_id", BOOT + "\n")
        for name, content in {"possible": "0-9", "present": "0-9", "online": "0-7", "offline": "8-9"}.items():
            self.write("sys/devices/system/cpu/" + name, content + "\n")
        for name in ("self", "1"):
            self.link("proc/" + name + "/ns/mnt", "mnt:[1234]")
        self.mounts = "1 0 0:1 / / rw - rootfs rootfs rw\n2 1 0:2 / " + str(self.root) + "/run rw - tmpfs tmpfs rw\n"
        self.write("proc/self/mountinfo", self.mounts)
        self.write("proc/swaps", "Filename Type Size Used Priority\n")
        self.write("dev/null", "")
        self.parent = "sys/devices/platform/11230000.mmc/mmc_host/mmc0/mmc0:0001/block/mmcblk0"
        self.part = self.parent + "/mmcblk0p30"
        for name, content in {"size": "32768", "partition": "30", "dev": "179:30", "start": "100000", "uevent": "PARTNAME=boot2"}.items():
            self.write(self.part + "/" + name, content + "\n")
        for name, content in {"size": "122142720", "dev": "179:0", "device/type": "MMC"}.items():
            self.write(self.parent + "/" + name, content + "\n")
        for rel in ("run", self.parent + "/holders", self.part + "/holders", "sys/bus/platform/drivers/mtk-msdc"):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        self.link("sys/class/block/mmcblk0", str(self.root / self.parent))
        self.link("sys/class/block/mmcblk0p30", str(self.root / self.part))
        self.link("sys/dev/block/179:0", str(self.root / self.parent))
        self.link("sys/dev/block/179:30", str(self.root / self.part))
        self.link("sys/bus/platform/devices/11230000.mmc/driver", str(self.root / "sys/bus/platform/drivers/mtk-msdc"))
        source = (HERE / "observe.sh").read_text()
        source = re.sub(r"(?<![A-Za-z0-9_/])/(?:bin/busybox|sys|proc|dev|run)(?=[/\"'\s)]|$)",
                        lambda match: str(self.root) + match.group(), source)
        programs = re.findall(r"\$BB awk(?: -F=)? '([^']*)'", source)
        if len(programs) != 3 or source.count('$BB timeout -s KILL 20 "$BB" dd ') != 1:
            raise RuntimeError("observer program boundaries changed; review fixture adapter")
        # These programs are known reviewed observer text. No fixture-supplied
        # value can replace them or add another awk invocation.
        self.env["EMMC_FIXTURE_AWK_HASHES"] = json.dumps([hashlib.sha256(value.encode()).hexdigest() for value in programs])
        self.write("observe.sh", source)

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def link(self, rel, target):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)

    def run_packet(self):
        shell = [*self.exact_prefix, "sh"] if self.exact_prefix else ["/bin/sh"]
        result = bounded_process([*shell, str(self.root / "observe.sh"), BOOT, RELEASE, PADDED_SHA, self.bb_sha],
                                 self.env, timeout=90 if self.exact_prefix else 30)
        return result

    def classify(self, stdout):
        return CLASSIFIER.classify(stdout.replace(str(self.root), ""), BOOT, RELEASE, PADDED_SHA, self.bb_sha)

    def assert_refused_without_read(self):
        result = self.run_packet()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse((self.root / "reads").exists(), result.stdout)
        self.assertNotEqual(self.classify(result.stdout)["classification"], "read-integrity-pass")

    def test_success_is_only_partial_acceptance(self):
        result = self.run_packet()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.classify(result.stdout)["classification"], "read-integrity-pass", result.stdout)
        self.assertEqual((self.root / "reads").read_text(), "one\n")
        self.assertEqual(list((self.root / "run/gemini-emmc-readonly").iterdir()), [self.root / "run/gemini-emmc-readonly/consumed"])
        if self.exact_prefix:
            calls = [json.loads(line) for line in (self.root / "applet-calls.jsonl").read_text().splitlines()]
            self.assertTrue(all(call["mode"] == "exact" for call in calls))
            expected = {"cat", "cut", "grep", "awk", "find", "mkdir", "rm", "date", "sha256sum"}
            self.assertTrue(expected.issubset({call["applet"] for call in calls}))
        repeated = self.run_packet()
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual((self.root / "reads").read_text(), "one\n")

    def test_short_read_fails(self):
        self.env["EMMC_FIXTURE_DD"] = "short"
        result = self.run_packet()
        self.assertEqual(self.classify(result.stdout)["reason"], "readback-mismatch", result.stderr)

    def test_failed_read_fails(self):
        self.env["EMMC_FIXTURE_DD"] = "interrupt"
        result = self.run_packet()
        self.assertEqual(self.classify(result.stdout)["reason"], "read-command-failed", result.stderr)

    def test_timeout_consumes_attempt(self):
        self.env["EMMC_FIXTURE_DD"] = "timeout"
        result = self.run_packet()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.classify(result.stdout)["classification"], "inconclusive")
        self.assertEqual(self.classify(result.stdout)["reason"], "read-timeout-or-kill")
        self.env.pop("EMMC_FIXTURE_DD")
        self.assert_refused_without_read()

    def test_bad_cpu(self):
        self.write("sys/devices/system/cpu/online", "0-9\n")
        self.assert_refused_without_read()

    def test_wrong_boot(self):
        self.write("proc/sys/kernel/random/boot_id", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n")
        self.assert_refused_without_read()

    def test_wrong_size(self):
        self.write(self.part + "/size", "32769\n")
        self.assert_refused_without_read()

    def test_wrong_parent_size(self):
        self.write(self.parent + "/size", "32768\n")
        self.assert_refused_without_read()

    def test_target_out_of_range(self):
        self.write(self.part + "/start", "122109953\n")
        self.assert_refused_without_read()

    def test_swap(self):
        self.write("proc/swaps", "Filename Type Size Used Priority\n/dev/root partition 1 1 1\n")
        self.assert_refused_without_read()

    def test_target_mounted_by_alias(self):
        self.write("proc/self/mountinfo", self.mounts + "3 1 179:30 / /mnt rw - ext4 /dev/root rw\n")
        self.assert_refused_without_read()

    def test_persistent_root(self):
        self.write("proc/self/mountinfo", self.mounts.replace("0:1 / / rw - rootfs rootfs", "179:29 / / rw - ext4 /dev/root"))
        self.assert_refused_without_read()

    def test_missing_run_mount(self):
        self.write("proc/self/mountinfo", self.mounts.splitlines()[0] + "\n")
        self.assert_refused_without_read()

    def test_duplicate_root(self):
        self.write("proc/self/mountinfo", self.mounts + "3 1 0:3 / / rw - tmpfs tmpfs rw\n")
        self.assert_refused_without_read()

    def test_different_namespace(self):
        (self.root / "proc/1/ns/mnt").unlink()
        self.link("proc/1/ns/mnt", "mnt:[5678]")
        self.assert_refused_without_read()

    def test_target_holders(self):
        self.write(self.part + "/holders/dm-0", "")
        self.assert_refused_without_read()

    def test_parent_holders(self):
        self.write(self.parent + "/holders/dm-0", "")
        self.assert_refused_without_read()

    def test_bad_device_node_identity(self):
        self.env["EMMC_FIXTURE_STAT"] = "regular file|0:0"
        self.assert_refused_without_read()

    def test_duplicate_gpt_label(self):
        self.write(self.part + "/uevent", "PARTNAME=boot2\nPARTNAME=boot2\n")
        self.assert_refused_without_read()

    def test_missing_gpt_label(self):
        self.write(self.part + "/uevent", "PARTNAME=boot\n")
        self.assert_refused_without_read()

    def test_prior_error(self):
        self.env["EMMC_FIXTURE_LOG"] = "mmc0: timeout waiting for hardware interrupt"
        self.assert_refused_without_read()

    def test_classifier_mutations(self):
        result = self.run_packet()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout.replace(str(self.root), "")
        mutations = [text.replace("read_attempts=1", "read_attempts=2"),
                     text.replace("controller_error_count=0", "controller_error_count=1"),
                     text.replace("device_storage_writes=none", "device_storage_writes=one"),
                     text.replace("guards_after=pass", "guards_after=missing"),
                     text.replace("__GEMINI_EMMC_READONLY_END__", ""),
                     text.replace("read_attempts=1", "read_attempts=1\nread_attempts=1"),
                     "untrusted prefix\n" + text, text + "extra\n"]
        for mutated in mutations:
            with self.subTest(mutated=mutated[:100]):
                self.assertNotEqual(self.classify(mutated)["classification"], "read-integrity-pass")

    def test_dispatcher_rejects_unconfined_paths_without_assertions(self):
        for applet, arguments in (("cat", ["/dev/mmcblk0"]),
                                  ("sha256sum", ["/dev/mmcblk0"]),
                                  ("dd", ["if=/dev/mmcblk0", "bs=4096", "count=4096"]),
                                  ("rm", ["-f", "/dev/mmcblk0"]),
                                  ("sh", ["-c", "exit 0"]),
                                  ("mount", [])):
            with self.subTest(applet=applet):
                result = bounded_process([sys.executable, "-O", str(self.bb), applet, *arguments], self.env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("fixture refusal", result.stderr)
        self.assertFalse((self.root / "reads").exists())
        self.assertFalse((self.root / "applet-calls.jsonl").exists())

    def test_dispatcher_rejects_symlink_escape(self):
        self.link("escape", "/dev")
        result = bounded_process([sys.executable, "-O", str(self.bb), "cat", str(self.root / "escape/mmcblk0")], self.env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture refusal", result.stderr)
        self.assertFalse((self.root / "applet-calls.jsonl").exists())

    def test_exact_configuration_resolves_static_emulator_symlink(self):
        self.write("qemu-real", "#!/bin/sh\nexit 2\n")
        (self.root / "qemu-real").chmod(0o700)
        self.link("qemu-aarch64-static", "qemu-real")
        environment = {key: value for key, value in os.environ.items() if not key.startswith("EMMC_TEST_")}
        environment.update(EMMC_TEST_BUSYBOX=str(self.bb), EMMC_TEST_WORK_ROOT=str(self.root),
                           EMMC_TEST_BUSYBOX_SHA256=self.bb_sha)
        resolve = lambda name: str(self.root / name) if name == "qemu-aarch64-static" else None
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(shutil, "which", side_effect=resolve):
            root, prefix, digest = exact_configuration()
        self.assertEqual(root, self.root)
        self.assertEqual(prefix, [str(self.root / "qemu-real"), str(self.bb)])
        self.assertEqual(digest, self.bb_sha)

    def test_exact_configuration_rejects_wrong_busybox_identity(self):
        environment = {key: value for key, value in os.environ.items() if not key.startswith("EMMC_TEST_")}
        environment.update(EMMC_TEST_BUSYBOX=str(self.bb), EMMC_TEST_WORK_ROOT=str(self.root),
                           EMMC_TEST_BUSYBOX_SHA256="0" * 64)
        with mock.patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "expected SHA-256 mismatch"):
                exact_configuration()

    @unittest.skipUnless(os.environ.get("EMMC_TEST_BUSYBOX"), "exact BusyBox/QEMU binary not supplied")
    def test_exact_timeout_closes_emitting_worker(self):
        # A single-process harmless worker emits again four seconds later. The
        # old timed non-exec shell lets that worker outlive the one-second
        # timeout and keep the output pipe open; a timed direct worker cannot.
        self.write("emitter.py", 'import time\nprint("BEFORE", flush=True)\ntime.sleep(4)\nprint("AFTER", flush=True)\n')
        emitter = str(self.root / "emitter.py")
        command = [*self.exact_prefix, "timeout", "-s", "KILL", "1", sys.executable, emitter]
        start = time.monotonic()
        result = bounded_process(command, self.env, timeout=6)
        elapsed = time.monotonic() - start
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertGreaterEqual(elapsed, 0.7, result.stderr)
        self.assertLess(elapsed, 3, "timed worker or its pipe survived the deadline")
        self.assertEqual(result.stdout, "BEFORE\n", result.stderr)

        # Regression control: the command after the worker deliberately stops
        # ash from replacing itself with exec. Seeing AFTER proves this fixture
        # detects the reviewed surviving-child failure, rather than just timing
        # a process that never had an observable descendant.
        old_shell = '"$1" "$2"; result=$?; printf "%s\\n" "$result" >&2'
        control = [*self.exact_prefix, "timeout", "-s", "KILL", "1",
                   *self.exact_prefix, "sh", "-c", old_shell, "read", sys.executable, emitter]
        start = time.monotonic()
        old_result = bounded_process(control, self.env, timeout=7)
        self.assertNotEqual(old_result.returncode, 0)
        self.assertEqual(old_result.stdout, "BEFORE\nAFTER\n", old_result.stderr)
        self.assertGreaterEqual(time.monotonic() - start, 3.5)

    @unittest.skipUnless(os.environ.get("EMMC_TEST_BUSYBOX"), "exact BusyBox/QEMU binary not supplied")
    def test_exact_timeout_refuses_invalid_duration(self):
        command = [*self.exact_prefix, "timeout", "-s", "KILL", "invalid", *self.exact_prefix, "printf", "UNEXPECTED_EXECUTION"]
        result = bounded_process(command, self.env, timeout=4)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("UNEXPECTED_EXECUTION", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
