#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private-input candidate primitives with the passive-CON SYS identity pins."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import struct
import subprocess
from dataclasses import replace
from pathlib import Path

PARENT = Path(__file__).resolve().parents[2] / "2026-09-06-mt6797-toprgu-minimal-restart/scripts/candidate_lib.py"
spec = importlib.util.spec_from_file_location("toprgu_candidate_lib", PARENT)
if spec is None or spec.loader is None:
    raise RuntimeError("parent candidate primitives unavailable")
_parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_parent)

RELEASE = "7.1.3-gemini-consys-passive"
PROFILE = "mt6797-consys-passive-boot"
PACKAGE_INVENTORY_SHA256 = "7c43a80cce28a15dc70306e3b8c225b537f1589eec4ac7411a46d422d705401c"
PATCHSET_SHA256 = "cca18743ba514d12f8c537752d6fdbea41b27a8cddaa34429d36c24bada49423"
CONFIG_INPUTS_SHA256 = "a0550db472534d70490da4fa8f80323a239553c705da66d0d90154656f24a5ef"
SERIES_SHA256 = "8fdbd1b0a28ff71c9fbbf72554e005876a78250157c82e68ed8e14c1e58d6ef1"
PROFILE_FRAGMENT_SHA256 = "470f68c8da4bfa345b0cd25ca3b27024c33596251204ff98f7ac60909d265941"
IMAGE_GZ_SHA256 = "35ecdf4c274c222a9db2b2dc31b6b40290b7d0d563241a0b7da78cb887dba416"
CONFIG_SHA256 = "7f28c03b964b7b19ed1aa383dc15fcee07e180145b3a92dd17dfda71e5927bff"
BASE_DTB_SHA256 = "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc"
SERVICEABILITY_DTB_SHA256 = "58629ff9f48ffa3840b04a336d45a52da7f2c1483a4400d2a0f1637fe9638037"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
USERSPACE_MANIFEST_SHA256 = "dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60"
FOUNDATION_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
LK_LIMIT = _parent.LK_LIMIT
PAGE = _parent.PAGE
ADDRESSES = _parent.ADDRESSES
REMOVED = _parent.REMOVED
REQUIRED_USERSPACE = _parent.REQUIRED_USERSPACE
FORBIDDEN_TEXT = _parent.FORBIDDEN_TEXT
OLD_EXECUTABLE_TEXT = _parent.OLD_EXECUTABLE_TEXT
PUBLIC_INIT_SOURCE_DIGESTS = dict(_parent.PUBLIC_INIT_SOURCE_DIGESTS)
PUBLIC_INIT_SOURCE_DIGESTS["init"] = "b4f2312a56143d7538f3e94bf83bfd70c2804db836195ccfbb7a07ba815757be"
del PUBLIC_INIT_SOURCE_DIGESTS["reboot-toprgu"]
PUBLIC_INIT_SOURCE_DIGESTS["reboot-passive"] = "fcfacfa8d1c9472f3a9b5b6ba8076274f6e898ceb2eadb731f8f628d13f49fcd"
STALE_IDENTITY_TEXT = (
    b"7.1.3-gemini-mt6797-toprgu-minimal-restart",
    b"mt6797-toprgu-minimal-restart",
    b"GEMINI_TOPRGU_V1",
    b"contract=toprgu-minimal-restart-v1",
)
ARTIFACT_ROOT = Path(__file__).resolve().parents[3] / "artifacts/consys-passive"

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def regular(path: Path, label: str = "file") -> bytes: return _parent.regular(path, label)
def private(path: Path, mode: int = 0o600) -> bytes: return _parent.private(path, mode)
def require(condition: bool, reason: str) -> None: _parent.require(condition, reason)
def is_elf(data: bytes) -> bool: return _parent.is_elf(data)
def is_untrusted_action_data(item) -> bool: return _parent.is_untrusted_action_data(item)
def load_newc_tools(repo: Path): return _parent.load_newc_tools(repo)

def validate_source_pins(repo: Path) -> None:
    _parent.validate_source_pins(repo)
    pins = {
        "patches/series-mt6797-consys-passive-boot": SERIES_SHA256,
        "configs/gemini-mt6797-consys-passive.fragment": PROFILE_FRAGMENT_SHA256,
        "experiments/2026-09-06-mt6797-toprgu-minimal-restart/scripts/validate-dtb.py":
            "77bcd71667c6ad82016494a40d5d8bb554b699897c00f63653efe4d515339246",
        "experiments/2026-09-06-mt6797-consys-passive-boot/initramfs/init":
            PUBLIC_INIT_SOURCE_DIGESTS["init"],
        "experiments/2026-09-06-mt6797-consys-passive-boot/initramfs/reboot-passive":
            PUBLIC_INIT_SOURCE_DIGESTS["reboot-passive"],
    }
    for relative, expected in pins.items():
        require(sha(regular(repo / relative, relative)) == expected,
                f"pinned input changed: {relative}")

def validate_private_root(path: Path, leaf: str) -> Path:
    expected = ARTIFACT_ROOT / leaf
    require(path.absolute() == expected, "output is outside the fixed private artifact root")
    for item in (ARTIFACT_ROOT, expected):
        info = item.lstat()
        require(not item.is_symlink() and stat.S_ISDIR(info.st_mode) and
                stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid(),
                f"private artifact directory is unsafe: {item.name}")
    require(subprocess.run(["git", "-C", str(ARTIFACT_ROOT.parents[1]),
                            "check-ignore", "-q", "--", str(expected)],
                           check=False).returncode == 0,
            "private artifact root is not Git-ignored")
    return expected

def validate_userspace(path: Path) -> None:
    old = {k: getattr(_parent, k) for k in ("USERSPACE_MANIFEST_SHA256",)}
    _parent.USERSPACE_MANIFEST_SHA256 = USERSPACE_MANIFEST_SHA256
    try: _parent.validate_userspace(path)
    finally: _parent.USERSPACE_MANIFEST_SHA256 = old["USERSPACE_MANIFEST_SHA256"]

def validate_credentials(path: Path): return _parent.validate_credentials(path)

def compute_input_id(image, dtb, foundation, userspace, credentials) -> str:
    auth = validate_credentials(credentials)
    material = {
        "release": RELEASE, "profile": PROFILE,
        "image_sha256": sha(image), "dtb_sha256": sha(dtb),
        "foundation_sha256": sha(foundation),
        "userspace_manifest_sha256": sha(regular(userspace / "SHA256SUMS")),
        "userspace_revision": "e9c028005b88ef8536ecb58c095e8d172253fa12",
        "package_inventory_sha256": PACKAGE_INVENTORY_SHA256,
        "config_sha256": CONFIG_SHA256, "source_sha256": SOURCE_SHA256,
        "patchset_sha256": PATCHSET_SHA256, "series_sha256": SERIES_SHA256,
        "profile_fragment_sha256": PROFILE_FRAGMENT_SHA256,
        "credentials": {name: sha(value) for name, value in sorted(auth.items())},
        "init_sources": PUBLIC_INIT_SOURCE_DIGESTS,
    }
    return sha(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("ascii"))

def compose_initramfs(repo, foundation, userspace, credentials, input_id):
    require(re.fullmatch(r"[0-9a-f]{64}", input_id) is not None,
            "input identity malformed")
    parse, encode = load_newc_tools(repo)
    baseline = parse(regular(foundation, "foundation initramfs"))
    require({"init", "bin/busybox", "bin/reboot"} <= set(baseline),
            "foundation initramfs inventory incomplete")
    members = {name: item for name, item in baseline.items() if name not in REMOVED}
    template = members["bin/reboot"]
    current = repo / "experiments/2026-09-06-mt6797-consys-passive-boot/initramfs"
    parent = repo / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/initramfs"
    sources = {
        "init": (current / "init", "init"),
        "inittab": (parent / "inittab", "etc/inittab"),
        "usb-auth": (parent / "usb-auth", "bin/usb-auth"),
        "console-status": (parent / "console-status", "bin/console-status"),
        "admin-shell": (parent / "admin-shell", "bin/admin-shell"),
        "reboot-passive": (current / "reboot-passive", "bin/reboot"),
    }
    for source, (path, target) in sources.items():
        data = regular(path, source)
        require(sha(data) == PUBLIC_INIT_SOURCE_DIGESTS[source],
                f"published init source changed: {source}")
        if source in {"init", "reboot-passive"}:
            require(data.count(b"INPUT_ID_PLACEHOLDER") == 1,
                    "input marker placeholder missing")
            data = data.replace(b"INPUT_ID_PLACEHOLDER", input_id.encode("ascii"))
        if source != "reboot-passive":
            require(not any(token in data for token in FORBIDDEN_TEXT),
                    f"unsafe initramfs source: {source}")
        require(not any(token in data for token in STALE_IDENTITY_TEXT),
                f"stale TOPRGU identity in initramfs source: {source}")
        mode = 0o644 if source == "inittab" else 0o755
        members[target] = replace(template, mode=stat.S_IFREG | mode, data=data)
    auth = validate_credentials(credentials)
    for name, mode in (("root", stat.S_IFDIR | 0o700),
                       ("root/.ssh", stat.S_IFDIR | 0o700),
                       ("etc/dropbear", stat.S_IFDIR | 0o700)):
        if name not in members:
            members[name] = replace(template, mode=mode, nlink=2, data=b"")
    added = {
        "bin/dropbear": (regular(userspace / "dropbear"), 0o755),
        "bin/dropbearkey": (regular(userspace / "dropbearkey"), 0o755),
        "bin/dropbearconvert": (regular(userspace / "dropbearconvert"), 0o755),
        "bin/keyboard-observe": (regular(userspace / "keyboard-observe"), 0o755),
        "bin/kmsg-capture": (regular(userspace / "kmsg-capture"), 0o755),
        "bin/kmsg-seal": (regular(userspace / "kmsg-seal"), 0o755),
        "etc/passwd": (b"root:x:0:0:Administrator:/root:/bin/admin-shell\n", 0o644),
        "etc/group": (b"root:x:0:\n", 0o644),
        "etc/shells": (b"/bin/admin-shell\n", 0o644),
        "root/.ssh/authorized_keys": (auth["authorized_keys"], 0o600),
        "etc/dropbear/host_key": (auth["dropbear_host_key"], 0o600),
    }
    for name, (data, mode) in added.items():
        require(name not in members, f"initramfs member collision: {name}")
        members[name] = replace(template, mode=stat.S_IFREG | mode, data=data)
    for name, item in members.items():
        if not is_untrusted_action_data(item):
            continue
        require(not any(token in item.data for token in STALE_IDENTITY_TEXT),
                f"stale TOPRGU executable identity: {name}")
        if name != "bin/reboot":
            require(not any(token in item.data for token in FORBIDDEN_TEXT),
                    f"forbidden runtime action in {name}")
            require(not any(token in item.data for token in OLD_EXECUTABLE_TEXT),
                    f"old executable marker in {name}")
    first = encode(members)
    require(first == encode(parse(first)), "initramfs serialization changed")
    summary = {name: {"mode": oct(item.mode), "size": len(item.data),
                      "sha256": sha(item.data)}
               for name, item in sorted(members.items())}
    return first, summary

def validate_package(package: Path) -> None:
    require(sha(regular(package / "Image.gz")) == IMAGE_GZ_SHA256, "kernel Image.gz identity changed")
    require(sha(regular(package / "kernel.config")) == CONFIG_SHA256, "resolved config identity changed")
    build = json.loads(regular(package / "provenance/build.json"))
    require(build.get("source_sha256") == SOURCE_SHA256 and build.get("kernel_source", {}).get("sha256") == SOURCE_SHA256, "kernel source identity changed")
    require(build.get("repository_commit") == "f9981eaf63381a558f77be251da4c2320cb4321b" and build.get("repository_dirty") is False, "kernel package commit/clean state changed")
    require(build.get("kernel_release") == RELEASE and build.get("build_profile") == PROFILE and build.get("target_architecture") == "arm64" and build.get("build_architecture") == "x86_64" and build.get("modules_built") is False, "kernel package provenance changed")
    require(build.get("patchset_sha256") == PATCHSET_SHA256 and build.get("config_sha256") == CONFIG_SHA256 and build.get("config_inputs_sha256") == CONFIG_INPUTS_SHA256, "series/config provenance changed")
    sums = regular(package / "SHA256SUMS", "kernel package inventory").decode("ascii")
    seen = set()
    for line in sums.splitlines():
        fields = line.split(maxsplit=1)
        require(len(fields) == 2 and re.fullmatch(r"[0-9a-f]{64}", fields[0]) is not None,
                "kernel package inventory framing changed")
        expected, name = fields
        name = name.removeprefix("*").removeprefix("./")
        require(name not in seen and ".." not in Path(name).parts and not Path(name).is_absolute(),
                "kernel package inventory framing changed")
        member = package / name
        require(member.is_file() and not member.is_symlink() and sha(member.read_bytes()) == expected,
                f"kernel package member changed: {name}")
        seen.add(name)
    require(sha(regular(package / "SHA256SUMS")) == PACKAGE_INVENTORY_SHA256,
            "kernel package inventory changed")

def android_v0(kernel: Path, ramdisk: Path, dtb: Path, repo: Path):
    serializer = repo / "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
    require(sha(regular(serializer)) == "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4", "Android-v0 serializer changed")
    spec = importlib.util.spec_from_file_location("consys_android_v0", serializer)
    require(spec and spec.loader, "Android-v0 serializer unavailable")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    args = type("Args", (), {"kernel": kernel, "ramdisk": ramdisk, "dtb": dtb, "page_size": PAGE,
        "lk_android8": True, "dtb_mode": "append", "cmdline": "bootopt=64S3,32N2,64N2", "name": "gemini-consys-P",
        "kernel_addr": ADDRESSES["kernel"], "ramdisk_addr": ADDRESSES["ramdisk"], "second_addr": ADDRESSES["second"], "tags_addr": ADDRESSES["tags"]})()
    return mod.build(args)

def pad(raw: bytes) -> bytes:
    require(0 < len(raw) < LK_LIMIT, "Android-v0 image does not fit boot2")
    return raw + bytes(LK_LIMIT - len(raw))

def write_exclusive(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); fd = path.open("xb")
    try: fd.write(data)
    finally: fd.close()
    path.chmod(mode)
