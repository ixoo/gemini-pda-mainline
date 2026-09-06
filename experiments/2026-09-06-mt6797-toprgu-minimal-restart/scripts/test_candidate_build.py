#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline tests for candidate/DT construction guards.

These tests inspect only published source and disposable text fixtures. They
never read credential bytes, contact a device, or invoke a network/build.
"""
from pathlib import Path
from dataclasses import dataclass
import hashlib
import importlib.util
from types import SimpleNamespace
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zlib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
import candidate_lib as C  # noqa: E402

DTB_SPEC = importlib.util.spec_from_file_location("candidate_validate_dtb", HERE / "validate-dtb.py")
DTB = importlib.util.module_from_spec(DTB_SPEC)
DTB_SPEC.loader.exec_module(DTB)
VALIDATOR_SPEC = importlib.util.spec_from_file_location("candidate_validator", HERE / "validate-candidate.py")
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


class CandidateBuildTests(unittest.TestCase):
    def test_exact_pins_and_full_candidate_identity(self):
        builder = (HERE / "build-candidate.py").read_text(encoding="utf-8")
        dt_builder = (HERE / "build-serviceability-dtb.sh").read_text(encoding="utf-8")
        validator = (HERE / "validate-dtb.py").read_text(encoding="utf-8")
        self.assertIn("refs/remotes/origin/main", builder)
        self.assertIn('name = out / ("candidate-" + C.sha(padded))', builder)
        self.assertIn('for suffix in ("one", "two")', builder)
        self.assertIn("independent DT/initramfs/Android-v0/padded constructions differ", builder)
        self.assertIn("58629ff9f48ffa3840b04a336d45a52da7f2c1483a4400d2a0f1637fe9638037", dt_builder)
        self.assertIn("DERIVED = \"58629ff9f48ffa3840b04a336d45a52da7f2c1483a4400d2a0f1637fe9638037\"", validator)
        self.assertEqual(C.SERIES_SHA256, "1b475e2890f161b9cc9cf423dbaee0ee14224b53171936c9189df841f28f2997")
        self.assertEqual(C.PROFILE_FRAGMENT_SHA256, "7fbb3db6ce8525e27aababd1aa8fb3794b98027821f683349c7b31a3b2616ffc")

    def test_reboot_and_marker_templates_are_narrow(self):
        for name in ("init", "reboot-toprgu"):
            data = (HERE.parent / "initramfs" / name).read_bytes()
            self.assertIn(b"INPUT_ID_PLACEHOLDER", data)
            if name == "init":
                self.assertNotIn(b"reboot -n", data)
                self.assertNotIn(b"reboot -f", data)
        wrapper = (HERE.parent / "initramfs" / "reboot-toprgu").read_bytes()
        self.assertEqual(wrapper.count(b"[ \"$#\" -eq 1 ]"), 1)
        self.assertEqual(wrapper.count(b"expected_boot=$1"), 1)
        self.assertGreaterEqual(wrapper.count(b"/proc/sys/kernel/random/boot_id"), 2)
        self.assertGreaterEqual(wrapper.count(b"/run/a53/boot-id"), 2)
        self.assertGreaterEqual(wrapper.count(b'[ "$boot_id" = "$expected_boot" ]'), 2)
        self.assertEqual(wrapper.count(b"exec /bin/busybox reboot -n -f"), 1)
        self.assertEqual(wrapper.count(b"wrapper=busybox-reboot-n-f-v1"), 1)
        self.assertIn(b"wrapper=busybox-reboot-n-f-v1", (HERE.parent / "initramfs" / "init").read_bytes())
        self.assertNotIn(b"/bin/reboot\n", wrapper)

    def test_logger_contract_is_baseline_compatible(self):
        init = (HERE.parent / "initramfs" / "init").read_bytes()
        reboot = (HERE.parent / "initramfs" / "reboot-toprgu").read_bytes()
        self.assertIn(b"/run/a53/boot-id", init)
        self.assertIn(b"/run/a53/kmsg-pid", init)
        self.assertIn(b"/run/a53/kmsg-exit", init)
        self.assertIn(b"wait \"$capture_pid\"", init)
        self.assertIn(b"printf '%s\\n' \"$capture_pid\"", init)
        self.assertIn(b"printf '%s\\n' \"$result\"", init)
        self.assertNotIn(b"%s\\\\n", init)
        self.assertGreaterEqual(reboot.count(b"cat /run/a53/boot-id"), 2)
        self.assertGreaterEqual(reboot.count(b"cat /proc/sys/kernel/random/boot_id"), 2)

    def test_independent_validator_binds_all_inputs_and_dtb(self):
        source = (HERE / "validate-candidate.py").read_text(encoding="utf-8")
        self.assertIn("validate-dtb.py", source)
        for argument in ("--base-dtb", "--foundation-initramfs", "--userspace", "--credentials"):
            self.assertIn(argument, source)
        self.assertIn("candidate.name == \"candidate-\" + manifest.get(\"padded_sha256\", \"\")", source)
        self.assertIn("initramfs_sha256", source)
        self.assertIn("boot2 padding is not zero", source)
        self.assertIn("differs from exact input-bound source", source)
        self.assertIn("wrapper.count(b\"input_id=%s\") == 1", source)
        self.assertIn("def derive_expected_initramfs", source)
        self.assertNotIn("C.compose_initramfs", source)
        self.assertIn("foundation initramfs identity changed", source)
        self.assertIn("published init source changed", source)

    def test_android_v0_replay_rejects_self_consistent_container_mutations(self):
        page = C.PAGE
        image_plain = bytearray(64)
        struct.pack_into("<3Q", image_plain, 8, 0, 0x100, 0x0A)
        image_plain[56:60] = b"ARM\x64"
        image = zlib.compress(bytes(image_plain), wbits=16 + zlib.MAX_WBITS)
        dtb = b"fixture-dtb"
        ramdisk = b"fixture-ramdisk"
        kernel_payload = image + dtb
        digest = hashlib.sha1()
        for payload in (kernel_payload, ramdisk, b""):
            digest.update(payload)
            digest.update(struct.pack("<I", len(payload)))
        header = bytearray(page)
        struct.pack_into("<8s10I", header, 0, b"ANDROID!", len(kernel_payload), 0x40200000,
                         len(ramdisk), 0x45000000, 0, 0x40F00000, 0x44000000, page, 0, 0)
        header[48:64] = b"gemini-toprgu-L\0"
        header[64:576] = b"bootopt=64S3,32N2,64N2".ljust(512, b"\0")
        header[576:596] = digest.digest()
        raw = bytes(header) + kernel_payload
        raw += bytes((-len(raw)) % page)
        raw += ramdisk
        raw += bytes((-len(raw)) % page)
        metadata = {"kernel_size": len(kernel_payload), "ramdisk_size": len(ramdisk), "dt_size": 0,
                    "page_size": page, "kernel_addr": 0x40200000, "ramdisk_addr": 0x45000000,
                    "second_addr": 0x40F00000, "tags_addr": 0x44000000, "dtb_mode": "append",
                    "lk_android8_compatible": "yes", "arm64_text_offset": 0,
                    "arm64_image_size": 0x100, "arm64_flags": 0x0A,
                    "arm64_placement_base": 0x40200000, "decompressed_kernel_size": 64,
                    "file_size": len(raw), "sha1_id": digest.hexdigest()}
        def fixture(raw_value=raw, metadata_value=metadata):
            padded = raw_value + bytes(0x01000000 - len(raw_value))
            return padded, {"raw_size": len(raw_value), "padded_size": len(padded),
                            "raw_sha256": C.sha(raw_value), "padded_sha256": C.sha(padded),
                            "android_v0": metadata_value}

        mutations = {}
        altered = bytearray(raw); altered[48] ^= 1; mutations["name"] = bytes(altered)
        altered = bytearray(raw); altered[64] ^= 1; mutations["cmdline"] = bytes(altered)
        altered = bytearray(raw); altered[576] ^= 1; mutations["id"] = bytes(altered)
        altered = bytearray(raw); altered[1700] ^= 1; mutations["reserved"] = bytes(altered)
        kernel_pad = page + ((len(kernel_payload) + page - 1) // page) * page
        altered = bytearray(raw); altered[kernel_pad - 1] = 1; mutations["padding"] = bytes(altered)
        mutations["trailing-raw"] = raw + b"trailing"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory)
            (candidate / "Image.gz").write_bytes(image)
            (candidate / "board.dtb").write_bytes(dtb)
            (candidate / "initramfs.img").write_bytes(ramdisk)
            for label, mutated_raw in {"valid": raw, **mutations}.items():
                padded, manifest = fixture(mutated_raw)
                (candidate / "boot2-padded.img").write_bytes(padded)
                if label == "trailing-raw":
                    manifest["android_v0"] = dict(metadata, file_size=len(mutated_raw))
                with self.subTest(label=label):
                    if label == "valid":
                        VALIDATOR.validate_container(candidate, manifest)
                    else:
                        with self.assertRaises(ValueError):
                            VALIDATOR.validate_container(candidate, manifest)
            valid_padded, bad_metadata = fixture(raw)
            (candidate / "boot2-padded.img").write_bytes(valid_padded)
            bad_metadata["android_v0"] = dict(metadata, file_size=1)
            with self.assertRaises(ValueError):
                VALIDATOR.validate_container(candidate, bad_metadata)

    def test_expected_members_are_derived_and_mutations_refused(self):
        input_id = "d" * 64
        source_root = HERE.parent / "initramfs"
        payloads = {
            "init": (source_root / "init").read_bytes().replace(
                b"INPUT_ID_PLACEHOLDER", input_id.encode()),
            "bin/reboot": (source_root / "reboot-toprgu").read_bytes().replace(
                b"INPUT_ID_PLACEHOLDER", input_id.encode()),
            "bin/dropbear": b"\x7fELF\x02\x01dropbear",
            "bin/kmsg-capture": b"\x7fELF\x02\x01capture",
            "bin/kmsg-seal": b"\x7fELF\x02\x01seal",
            "bin/keyboard-observe": b"\x7fELF\x02\x01keyboard",
            "etc/dropbear/host_key": b"dropbear-host-public-container",
            "root/.ssh/authorized_keys": b"no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 fixture",
        }

        def member_map(payload):
            result = {}
            for name, data in payload.items():
                permissions = 0o600 if name in ("etc/dropbear/host_key", "root/.ssh/authorized_keys") else 0o755
                result[name] = SimpleNamespace(mode=stat.S_IFREG | permissions, nlink=1, data=data)
            return result

        expected = member_map(payloads)
        expected_summary = {name: {"mode": oct(item.mode), "size": len(item.data),
                                   "sha256": C.sha(item.data)} for name, item in expected.items()}
        original_regular = VALIDATOR.C.regular

        def fake_regular(path, *args):
            if Path(path) == Path("synthetic-initramfs"):
                return b"expected-archive"
            return original_regular(path, *args)

        def parse(raw):
            self.assertEqual(raw, b"expected-archive")
            return expected

        manifest = {"input_id": input_id, "members": expected_summary}
        with mock.patch.object(VALIDATOR, "derive_expected_initramfs", autospec=True,
                               return_value=(b"expected-archive", expected_summary)), \
             mock.patch.object(VALIDATOR.C, "compose_initramfs",
                               side_effect=AssertionError("validator called production composer")), \
             mock.patch.object(VALIDATOR.C, "load_newc_tools", return_value=(parse, object())), \
             mock.patch.object(VALIDATOR.C, "regular", side_effect=fake_regular):
            VALIDATOR.validate_members(Path("synthetic-initramfs"), manifest,
                                       foundation_initramfs=Path("foundation"),
                                       userspace=Path("userspace"), credentials=Path("credentials"))

        # Each mutation keeps the same input_id and supplies self-consistent
        # candidate metadata, but must fail against independently derived
        # expected bytes/inventory. No credential or private key is opened.
        mutations = {
            "userspace-elf": ("bin/dropbear", b"\x7fELF\x02\x01mutated", None),
            "authorized-key": ("root/.ssh/authorized_keys", b"no-port-forwarding ssh-ed25519 other", None),
            "host-key": ("etc/dropbear/host_key", b"changed-host-key", None),
            "public-template": ("init", expected["init"].data.replace(b"phase=entry", b"phase=altered"), None),
            "member-mode": ("bin/kmsg-seal", expected["bin/kmsg-seal"].data, stat.S_IFREG | 0o644),
        }
        for label, (name, data, mutated_mode) in mutations.items():
            with self.subTest(label=label):
                mutated = dict(expected)
                mutated[name] = SimpleNamespace(mode=mutated_mode or expected[name].mode, nlink=1, data=data)
                mutated_summary = {key: {"mode": oct(item.mode), "size": len(item.data),
                                         "sha256": C.sha(item.data)} for key, item in mutated.items()}
                def mutated_parse(raw, members=mutated):
                    return expected if raw == b"expected-archive" else members
                with mock.patch.object(VALIDATOR, "derive_expected_initramfs", autospec=True,
                                       return_value=(b"expected-archive", expected_summary)), \
                     mock.patch.object(VALIDATOR.C, "load_newc_tools", return_value=(mutated_parse, object())), \
                     mock.patch.object(VALIDATOR.C, "regular", side_effect=lambda path, *args:
                         b"mutated-archive" if Path(path) == Path("synthetic-initramfs") else original_regular(path, *args)):
                    with self.assertRaises(ValueError):
                        VALIDATOR.validate_members(Path("synthetic-initramfs"),
                                                   {"input_id": input_id, "members": mutated_summary},
                                                   foundation_initramfs=Path("foundation"),
                                                   userspace=Path("userspace"), credentials=Path("credentials"))

        for label, remove in (("missing-member", "bin/kmsg-seal"), ("unexpected-member", "bin/unexpected")):
            with self.subTest(label=label):
                mutated = dict(expected)
                if remove == "bin/kmsg-seal":
                    mutated.pop(remove)
                else:
                    mutated[remove] = SimpleNamespace(mode=stat.S_IFREG | 0o755, nlink=1, data=b"unexpected")
                mutated_summary = {key: {"mode": oct(item.mode), "size": len(item.data),
                                         "sha256": C.sha(item.data)} for key, item in mutated.items()}
                def inventory_parse(raw, members=mutated):
                    return expected if raw == b"expected-archive" else members
                with mock.patch.object(VALIDATOR, "derive_expected_initramfs", autospec=True,
                                       return_value=(b"expected-archive", expected_summary)), \
                     mock.patch.object(VALIDATOR.C, "load_newc_tools", return_value=(inventory_parse, object())), \
                     mock.patch.object(VALIDATOR.C, "regular", side_effect=lambda path, *args:
                         b"mutated-archive" if Path(path) == Path("synthetic-initramfs") else original_regular(path, *args)):
                    with self.assertRaises(ValueError):
                        VALIDATOR.validate_members(Path("synthetic-initramfs"),
                                                   {"input_id": input_id, "members": mutated_summary},
                                                   foundation_initramfs=Path("foundation"),
                                                   userspace=Path("userspace"), credentials=Path("credentials"))

    def test_independent_derivation_replays_every_input_class(self):
        @dataclass
        class Member:
            mode: int
            nlink: int
            data: bytes

        foundation = b"synthetic-foundation"
        baseline = {
            "init": Member(stat.S_IFREG | 0o755, 1, b"old-init"),
            "bin/busybox": Member(stat.S_IFREG | 0o755, 1, b"\x7fELF\x02\x01busybox"),
            "bin/reboot": Member(stat.S_IFREG | 0o755, 1, b"old-reboot"),
            "bin/usb-net": Member(stat.S_IFREG | 0o755, 1, b"removed-action"),
            "etc/foundation": Member(stat.S_IFREG | 0o644, 1, b"retained"),
            # This retained foundation ELF contains an implementation symbol
            # named ioctl; exact foundation bytes, not token scanning, govern it.
            "bin/console-keymap-verify": Member(stat.S_IFREG | 0o755,
                                                  1, b"\x7fELF\x02\x01ioctl"),
        }
        encoded = {}

        def encode(members):
            rows = tuple((name, item.mode, item.nlink, item.data) for name, item in sorted(members.items()))
            raw = repr(rows).encode("ascii")
            encoded[raw] = dict(members)
            return raw

        def parse(raw):
            if raw == foundation:
                return dict(baseline)
            return dict(encoded[raw])

        userspace_names = ("dropbear", "dropbearkey", "dropbearconvert", "keyboard-observe",
                           "kmsg-capture", "kmsg-seal")
        userspace_bytes = {name: b"\x7fELF\x02\x01" + name.encode("ascii") for name in userspace_names}
        credentials = {"authorized_keys": b"restricted-admin-key", "dropbear_host_key": b"host-key"}
        original_regular = VALIDATOR.C.regular
        original_sha = VALIDATOR.C.sha

        def fake_regular(path, *args):
            path = Path(path)
            if path == Path("foundation"):
                return foundation
            if path.parent == Path("userspace") and path.name in userspace_bytes:
                return userspace_bytes[path.name]
            return original_regular(path, *args)

        def fake_sha(data):
            if data == foundation:
                return VALIDATOR.FOUNDATION_INITRAMFS_SHA256
            return original_sha(data)

        input_id = "e" * 64
        with mock.patch.object(VALIDATOR.C, "load_newc_tools", return_value=(parse, encode)), \
             mock.patch.object(VALIDATOR.C, "regular", side_effect=fake_regular), \
             mock.patch.object(VALIDATOR.C, "sha", side_effect=fake_sha), \
             mock.patch.object(VALIDATOR.C, "validate_credentials", return_value=credentials), \
             mock.patch.object(VALIDATOR.C, "compose_initramfs",
                               side_effect=AssertionError("validator called production composer")):
            archive, summary = VALIDATOR.derive_expected_initramfs(
                Path("foundation"), Path("userspace"), Path("credentials"), input_id)

        members = parse(archive)
        self.assertEqual(members["bin/busybox"].data, baseline["bin/busybox"].data)
        self.assertEqual(members["etc/foundation"].data, b"retained")
        self.assertEqual(members["bin/console-keymap-verify"].data,
                         baseline["bin/console-keymap-verify"].data)
        self.assertNotIn("bin/usb-net", members)
        source_map = {"init": "init", "inittab": "etc/inittab", "usb-auth": "bin/usb-auth",
                      "console-status": "bin/console-status", "admin-shell": "bin/admin-shell",
                      "reboot-toprgu": "bin/reboot"}
        for source, target in source_map.items():
            expected = (HERE.parent / "initramfs" / source).read_bytes()
            if source in {"init", "reboot-toprgu"}:
                expected = expected.replace(b"INPUT_ID_PLACEHOLDER", input_id.encode("ascii"))
            self.assertEqual(members[target].data, expected)
        for name, data in userspace_bytes.items():
            self.assertEqual(members["bin/" + name].data, data)
        self.assertEqual(members["root/.ssh/authorized_keys"].data, credentials["authorized_keys"])
        self.assertEqual(members["etc/dropbear/host_key"].data, credentials["dropbear_host_key"])
        self.assertEqual(members["etc/passwd"].data,
                         b"root:x:0:0:Administrator:/root:/bin/admin-shell\n")
        self.assertEqual(set(summary), set(members))

    def test_action_token_closure_allows_exact_elf_and_rejects_non_elf_script(self):
        @dataclass
        class Member:
            mode: int
            nlink: int
            data: bytes

        foundation = b"synthetic-foundation-action-closure"
        baseline = {
            "init": Member(stat.S_IFREG | 0o755, 1, b"old-init"),
            "bin/busybox": Member(stat.S_IFREG | 0o755, 1, b"\x7fELF\x02\x01busybox"),
            "bin/reboot": Member(stat.S_IFREG | 0o755, 1, b"old-reboot"),
            # Real foundation behavior includes an ELF symbol containing ioctl.
            "bin/console-keymap-verify": Member(stat.S_IFREG | 0o755, 1,
                                                  b"\x7fELF\x02\x01ioctl"),
        }
        userspace_names = ("dropbear", "dropbearkey", "dropbearconvert", "keyboard-observe",
                           "kmsg-capture", "kmsg-seal")
        userspace_bytes = {name: b"\x7fELF\x02\x01" + name.encode("ascii") for name in userspace_names}
        credentials = {"authorized_keys": b"restricted-admin-key", "dropbear_host_key": b"host-key"}
        input_id = "f" * 64
        original_regular = C.regular
        original_sha = C.sha

        def fake_regular(path, *args):
            path = Path(path)
            if path == Path("foundation"):
                return foundation
            if path.parent == Path("userspace") and path.name in userspace_bytes:
                return userspace_bytes[path.name]
            return original_regular(path, *args)

        def fake_sha(data):
            if data == foundation:
                return VALIDATOR.FOUNDATION_INITRAMFS_SHA256
            return original_sha(data)

        def codec(base_members):
            encoded = {}

            def encode(members):
                rows = tuple((name, item.mode, item.nlink, item.data)
                             for name, item in sorted(members.items()))
                raw = repr(rows).encode("ascii")
                encoded[raw] = dict(members)
                return raw

            def parse(raw):
                return dict(base_members) if raw == foundation else dict(encoded[raw])

            return parse, encode

        with mock.patch.object(C, "regular", side_effect=fake_regular), \
             mock.patch.object(C, "sha", side_effect=fake_sha), \
             mock.patch.object(C, "validate_credentials", return_value=credentials), \
             mock.patch.object(C, "load_newc_tools", side_effect=lambda _repo: codec(baseline)):
            archive, summary = C.compose_initramfs(
                VALIDATOR.REPO, Path("foundation"), Path("userspace"),
                Path("credentials"), input_id)
        self.assertIn("bin/console-keymap-verify", summary)
        elf = b"\x7fELF\x02\x01ioctl"
        self.assertEqual(summary["bin/console-keymap-verify"]["size"], len(elf))
        self.assertEqual(summary["bin/console-keymap-verify"]["sha256"], C.sha(elf))

        bad_baseline = dict(baseline)
        bad_baseline["bin/legacy-action"] = Member(
            stat.S_IFREG | 0o755, 1, b"#!/bin/sh\nioctl /dev/watchdog\n")
        with mock.patch.object(C, "regular", side_effect=fake_regular), \
             mock.patch.object(C, "sha", side_effect=fake_sha), \
             mock.patch.object(C, "validate_credentials", return_value=credentials), \
             mock.patch.object(C, "load_newc_tools", side_effect=lambda _repo: codec(bad_baseline)):
            with self.assertRaisesRegex(ValueError, "forbidden runtime action"):
                C.compose_initramfs(VALIDATOR.REPO, Path("foundation"), Path("userspace"),
                                    Path("credentials"), input_id)

        with mock.patch.object(VALIDATOR.C, "regular", side_effect=fake_regular), \
             mock.patch.object(VALIDATOR.C, "sha", side_effect=fake_sha), \
             mock.patch.object(VALIDATOR.C, "validate_credentials", return_value=credentials), \
             mock.patch.object(VALIDATOR.C, "load_newc_tools", side_effect=lambda _repo: codec(baseline)):
            archive, summary = VALIDATOR.derive_expected_initramfs(
                Path("foundation"), Path("userspace"), Path("credentials"), input_id)
        self.assertIn("bin/console-keymap-verify", summary)
        self.assertEqual(summary["bin/console-keymap-verify"]["size"], len(elf))
        self.assertEqual(summary["bin/console-keymap-verify"]["sha256"], C.sha(elf))

        with mock.patch.object(VALIDATOR.C, "regular", side_effect=fake_regular), \
             mock.patch.object(VALIDATOR.C, "sha", side_effect=fake_sha), \
             mock.patch.object(VALIDATOR.C, "validate_credentials", return_value=credentials), \
             mock.patch.object(VALIDATOR.C, "load_newc_tools", side_effect=lambda _repo: codec(bad_baseline)):
            with self.assertRaisesRegex(ValueError, "forbidden runtime action"):
                VALIDATOR.derive_expected_initramfs(
                    Path("foundation"), Path("userspace"), Path("credentials"), input_id)
    def test_reserved_memory_checks_container_and_static_children(self):
        source = (HERE / "validate-dtb.py").read_text(encoding="utf-8")
        self.assertIn("reserved-memory properties changed", source)
        self.assertIn("reserved-memory child reg disappeared", source)
        self.assertIn("reserved-memory dynamic child gained reg", source)

    def test_reserved_memory_fixture_reaches_container_and_child_guards(self):
        nodes = {"/reserved-memory", "/reserved-memory/ramoops@44410000"}
        props = {("/reserved-memory", "#address-cells", "#address-cells = <2>;"),
                 ("/reserved-memory", "#size-cells", "#size-cells = <2>;"),
                 ("/reserved-memory", "ranges", "ranges;")}
        inventories = [(nodes, props), (nodes, props)]
        children = ["ramoops@44410000", "reserve-memory-scp_share"]

        def fake_absent(path, node, prop):
            return node.endswith("reserve-memory-scp_share") and prop == "reg"

        with mock.patch.object(DTB, "dts_inventory", side_effect=inventories), \
             mock.patch.object(DTB, "children", return_value=children), \
             mock.patch.object(DTB, "absent", side_effect=fake_absent), \
             mock.patch.object(DTB, "get", return_value="0 44410000 0 e0000"):
            DTB.validate_reserved_memory(Path("base.dtb"), Path("derived.dtb"))

        bad_props = [(nodes, props), (nodes, props | {("/reserved-memory", "reg", "reg = <0>;" )})]
        with mock.patch.object(DTB, "dts_inventory", side_effect=bad_props), \
             mock.patch.object(DTB, "children", return_value=children), \
             mock.patch.object(DTB, "absent", side_effect=fake_absent), \
             mock.patch.object(DTB, "get", return_value="0 44410000 0 e0000"), \
             self.assertRaises(ValueError):
            DTB.validate_reserved_memory(Path("base.dtb"), Path("derived.dtb"))

    def test_dt_validator_rejects_wrong_expected_identity_before_tools(self):
        source = (HERE / "validate-dtb.py").read_text(encoding="utf-8")
        self.assertIn("require(expected == DERIVED", source)
        self.assertIn("unrelated DT node inventory changed", source)
        self.assertIn("unrelated DT nodes/properties/raw values changed", source)

    def test_candidate_validator_launches_real_dt_validator_sibling(self):
        with tempfile.TemporaryDirectory(prefix="toprgu-dtb-launch-") as raw:
            root = Path(raw)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "board.dtb").write_bytes(b"derived")
            base = root / "base.dtb"
            base.write_bytes(b"base")
            calls = []

            def record(command, check):
                calls.append(command)
                self.assertTrue(check)
                return SimpleNamespace(returncode=0)

            with mock.patch.object(VALIDATOR.C, "sha", return_value=C.BASE_DTB_SHA256), \
                 mock.patch.object(VALIDATOR.subprocess, "run", side_effect=record):
                VALIDATOR.validate_dtb(
                    candidate, base,
                    {"serviceability_dtb_sha256": C.SERVICEABILITY_DTB_SHA256})

            self.assertEqual(len(calls), 1)
            self.assertEqual(Path(calls[0][1]).resolve(strict=True),
                             (HERE / "validate-dtb.py").resolve(strict=True))
            self.assertTrue(Path(calls[0][1]).is_file())

    def test_shell_and_python_syntax(self):
        shell_files = [HERE / "build-serviceability-dtb.sh"] + list((HERE.parent / "initramfs").iterdir())
        for path in shell_files:
            if path.name == "inittab":
                continue
            subprocess.run(["bash", "-n", str(path)], check=True)
        subprocess.run([sys.executable, "-m", "py_compile", str(HERE / "candidate_lib.py"),
                        str(HERE / "build-candidate.py"), str(HERE / "validate-candidate.py"),
                        str(HERE / "validate-dtb.py")], check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
