#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure candidate policy and serialization helpers.

The module deliberately has no device, network, or credential-generation
side effects.  Its callers may write only below the ignored artifact root.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import runpy


RELEASE = "7.1.3-gemini-mt6797-toprgu-minimal-restart"
PROFILE = "mt6797-toprgu-minimal-restart"
PACKAGE_INVENTORY_SHA256 = "9b14f15515bb56ec19eb39611a1262edfe56d9df25d3ed69828c4318d76498ca"
PATCHSET_SHA256 = "a49c7726dad3d8e2a98d1c3c2884f36e68e0c33ead26887c87c5f33ddfc8d1b4"
SERIES_SHA256 = "1b475e2890f161b9cc9cf423dbaee0ee14224b53171936c9189df841f28f2997"
PROFILE_FRAGMENT_SHA256 = "7fbb3db6ce8525e27aababd1aa8fb3794b98027821f683349c7b31a3b2616ffc"
CONFIG_INPUTS_SHA256 = "e8b27cf3c09b22f4475a6facac23b0c27b11c198734bd1631d7f3716f0846478"
IMAGE_GZ_SHA256 = "78f4c931fbb03ea18ea1cbb5c4bff72d68376a39a92f2b9c57b8fb86d4f5f2da"
BASE_DTB_SHA256 = "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc"
SERVICEABILITY_DTB_SHA256 = "58629ff9f48ffa3840b04a336d45a52da7f2c1483a4400d2a0f1637fe9638037"
CONFIG_SHA256 = "273e9c60fd0036551e5f1c295cd4fb8cb5acd3bcd41307485deb9979f510287c"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
USERSPACE_MANIFEST_SHA256 = "dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60"
DT_TRANSFORMER_SHA256 = "550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d"
DT_VALIDATOR_SHA256 = "332aa7baf063f817552c3394ef55c6448aa19c9703703fc6148475d9520b355a"
BASELINE_BUILDER_SHA256 = "365e6ba85693abb4a273efc4160abaeea78e425867903c9a5a706738694dc104"
BASELINE_VALIDATOR_SHA256 = "ef76e8b99aeb94dc56651752855efdb493bdfabbd31fbd91a0cba07f1a7f22bb"
PROVISIONER_SHA256 = "eabe2167a4bfb97a4ca763d5d1a6c918ae65e8738d57736323a86e45d5ef163c"
ATTENDED_OUTCOME_SHA256 = "589cacb51b21e4ca7e9e790caf1aadb0b0bb5c2eebf70972ea017d19db36dc23"
RECOVERY_WITNESS_SHA256 = "bec1377df7135cf552eac0f299bfbd97e0fe6554ec030d820bd4d37f0e484aa6"
LK_LIMIT = 0x01000000
PAGE = 2048
ADDRESSES = {"kernel": 0x40200000, "ramdisk": 0x45000000,
             "second": 0x40F00000, "tags": 0x44000000}
REMOVED = {"bin/usb-net", "bin/usb-shell", "bin/local-shell",
           "bin/emmc-flash-boot2", "bin/x-probe", "bin/input-event-capture",
           "bin/ac-record"}
REQUIRED_USERSPACE = {"dropbear", "dropbearkey", "dropbearconvert",
                      "keyboard-observe", "kmsg-capture", "kmsg-seal",
                      "auth-tests.json", "localoptions.h", "effective-options.txt",
                      "provenance.txt", "SHA256SUMS"}
FORBIDDEN_TEXT = (b"/dev/watchdog", b"watchdog", b"reboot -f", b"reboot -n",
                  b"/sys/devices/system/cpu/cpu8/online", b"/sys/devices/system/cpu/cpu9/online",
                  b"mount -o rw", b"/dev/mmc", b"ioctl")
OLD_EXECUTABLE_TEXT = (b"3.18.41+", b"pwrap-reset", b"Candidate-AB", b"CANDIDATE_AB")
PUBLIC_INIT_SOURCE_DIGESTS = {
    "init": "533fbf455e418d35973a6651d882b6d3c5240e5ef8594804109cde70adc05e4b",
    "inittab": "6b3bcd89055fa50cdf5c5d973611c9e5f30719197b50ad059079e649906fec6f",
    "usb-auth": "3b292c1af12e18437254af49e321b968cddd348b3a5846dd9165927b6a81c672",
    "console-status": "82dcf6d37295560a4c151f9d94e18376ea6baab469ac39b3f30d76e963c1c995",
    "admin-shell": "862edd23f60971b3fb777ba2b613d6bffbff99f32362dc40014311016de44c0e",
    "reboot-toprgu": "0011b9cc729cc04886228fb5f1f56c8243a10179f1d030647f8ac36f735b6318",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, label: str = "file") -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"{label} is not a regular file")
    return path.read_bytes()


def private(path: Path, mode: int = 0o600) -> bytes:
    data = regular(path)
    if stat.S_IMODE(path.stat().st_mode) != mode:
        raise ValueError(f"private file mode changed: {path.name}")
    return data


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def validate_source_pins(repo: Path) -> None:
    pins = {
        "patches/series-mt6797-toprgu-minimal-restart": SERIES_SHA256,
        "configs/gemini-mt6797-toprgu-minimal-restart.fragment": PROFILE_FRAGMENT_SHA256,
        "experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-serviceability-dtb.sh": DT_TRANSFORMER_SHA256,
        "experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/test-candidate.py": DT_VALIDATOR_SHA256,
        "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/build-candidate.py": BASELINE_BUILDER_SHA256,
        "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/validate-candidate.py": BASELINE_VALIDATOR_SHA256,
        "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/provision.py": PROVISIONER_SHA256,
        "experiments/2026-09-05-owner-away-experiment-preparation/baseline/ATTENDED_OUTCOME.md": ATTENDED_OUTCOME_SHA256,
        "experiments/2026-09-05-owner-away-experiment-preparation/baseline/RECOVERY_WITNESS_REVIEW.md": RECOVERY_WITNESS_SHA256,
    }
    for relative, expected in pins.items():
        path = repo / relative
        require(sha(regular(path, relative)) == expected, f"pinned input changed: {relative}")


def load_newc_tools(repo: Path):
    parser_path = repo / "experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py"
    encoder_path = repo / "experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py"
    require(sha(regular(parser_path)) == "19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c", "newc parser changed")
    require(sha(regular(encoder_path)) == "0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38", "newc encoder changed")
    parser = importlib.util.spec_from_file_location("candidate_newc_parser", parser_path)
    encoder = importlib.util.spec_from_file_location("candidate_newc_encoder", encoder_path)
    require(parser and parser.loader and encoder and encoder.loader, "newc tools unavailable")
    pmod = importlib.util.module_from_spec(parser)
    emod = importlib.util.module_from_spec(encoder)
    sys.modules[parser.name] = pmod
    sys.modules[encoder.name] = emod
    parser.loader.exec_module(pmod)
    encoder.loader.exec_module(emod)
    return pmod.parse_newc, emod.encode_newc


def validate_userspace(package: Path) -> None:
    package = package.resolve(strict=True)
    sums = regular(package / "SHA256SUMS", "userspace manifest")
    require(sha(sums) == USERSPACE_MANIFEST_SHA256, "authenticated userspace manifest changed")
    for line in sums.decode("ascii").splitlines():
        expected, name = line.split(maxsplit=1)
        name = name.removeprefix("*").removeprefix("./")
        path = package / name
        require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == expected,
                f"userspace member checksum changed: {name}")
    names = {p.name for p in package.iterdir() if not p.is_symlink()}
    require(REQUIRED_USERSPACE <= names, "authenticated userspace inventory incomplete")
    auth = json.loads(regular(package / "auth-tests.json"))
    require(auth.get("classification") == "offline-authentication-pass", "userspace authentication receipt missing")
    provenance = regular(package / "provenance.txt").decode("ascii").splitlines()
    fields = dict(line.split("=", 1) for line in provenance if "=" in line)
    require(fields.get("repository_commit") == "e9c028005b88ef8536ecb58c095e8d172253fa12" and
            fields.get("independent_binary_builds") == "2" and fields.get("byte_identical") == "yes" and
            fields.get("device_action") == "none", "userspace provenance changed")
    for name in REQUIRED_USERSPACE - {"SHA256SUMS", "auth-tests.json", "localoptions.h", "effective-options.txt", "provenance.txt"}:
        data = regular(package / name, name)
        if name in {"dropbear", "dropbearkey", "dropbearconvert", "keyboard-observe", "kmsg-capture", "kmsg-seal"}:
            require(data.startswith(b"\x7fELF\x02\x01"), f"{name} is not AArch64 ELF")


def validate_credentials(credentials: Path) -> dict[str, bytes]:
    credentials = credentials.resolve(strict=True)
    require(stat.S_IMODE(credentials.stat().st_mode) == 0o700, "credential directory mode changed")
    expected = {"authorized_keys", "dropbear_host_key", "known_hosts"}
    require({p.name for p in credentials.iterdir()} >= expected, "credential inventory incomplete")
    for path in credentials.iterdir():
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
                "credential file metadata changed")
    result = {}
    for name in expected:
        path = credentials / name
        result[name] = private(path)
        require(b"PRIVATE KEY" not in result[name], "private credential must not be embedded")
    require(result["authorized_keys"].startswith(b"no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 "), "authorized key restrictions changed")
    require(result["known_hosts"].decode("ascii").splitlines() ==
            ["10.15.19.82 " + regular(credentials / "host.pub").decode("ascii").strip()],
            "candidate known-host pin does not match generated host identity")
    # Public-key consistency is checked without emitting secret material. The
    # reviewed converter proves the Dropbear host container matches host.key.
    provision_path = Path(__file__).resolve().parents[3] / "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/provision.py"
    converter = runpy.run_path(str(provision_path))["convert_ed25519"]
    require(converter(private(credentials / "host")) == result["dropbear_host_key"],
            "Dropbear host key conversion mismatch")
    admin_public = subprocess.run(["ssh-keygen", "-y", "-f", str(credentials / "admin")],
                                  check=True, text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).stdout.strip()
    require(admin_public == regular(credentials / "admin.pub").decode("ascii").strip(),
            "administrator private/public key mismatch")
    # The administrator key is intentionally never copied into the initramfs,
    # but its reviewed public identity is still an input to the candidate.
    # Otherwise rotating the host-side SSH key could leave the same input_id
    # attached to a candidate that no longer matches the session packet.
    result["host.pub"] = regular(credentials / "host.pub", "host public key")
    result["admin.pub"] = regular(credentials / "admin.pub", "administrator public key")
    return result


def compute_input_id(image: bytes, dtb: bytes, foundation: bytes, userspace: Path,
                     credentials: Path) -> str:
    """Bind the on-device marker to every fixed public candidate input."""
    auth = validate_credentials(credentials)
    material = {"release": RELEASE, "profile": PROFILE,
                "image_sha256": sha(image), "dtb_sha256": sha(dtb),
                "foundation_sha256": sha(foundation),
                "userspace_manifest_sha256": sha(regular(userspace / "SHA256SUMS")),
                "userspace_revision": "e9c028005b88ef8536ecb58c095e8d172253fa12",
                "package_inventory_sha256": PACKAGE_INVENTORY_SHA256,
                "config_sha256": CONFIG_SHA256, "source_sha256": SOURCE_SHA256,
                "patchset_sha256": PATCHSET_SHA256, "series_sha256": SERIES_SHA256,
                "profile_fragment_sha256": PROFILE_FRAGMENT_SHA256,
                "credentials": {name: sha(value) for name, value in sorted(auth.items())},
                "init_sources": PUBLIC_INIT_SOURCE_DIGESTS}
    return sha(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("ascii"))


def compose_initramfs(repo: Path, parent: Path, userspace: Path, credentials: Path,
                      input_id: str) -> tuple[bytes, dict[str, object]]:
    require(re.fullmatch(r"[0-9a-f]{64}", input_id) is not None, "input identity malformed")
    parse, encode = load_newc_tools(repo)
    baseline = parse(regular(parent, "foundation initramfs"))
    require({"init", "bin/busybox", "bin/reboot"} <= set(baseline), "foundation initramfs inventory incomplete")
    members = {name: item for name, item in baseline.items() if name not in REMOVED}
    template = members["bin/reboot"]
    source_root = repo / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/initramfs"
    source_map = {"init": "init", "inittab": "etc/inittab", "usb-auth": "bin/usb-auth",
                  "console-status": "bin/console-status", "admin-shell": "bin/admin-shell",
                  "reboot-toprgu": "bin/reboot"}
    for source, target in source_map.items():
        data = regular(source_root / source, source)
        if source in {"init", "reboot-toprgu"}:
            require(data.count(b"INPUT_ID_PLACEHOLDER") == 1, "input marker placeholder missing")
            data = data.replace(b"INPUT_ID_PLACEHOLDER", input_id.encode("ascii"))
        if source != "reboot-toprgu":
            require(not any(token in data for token in FORBIDDEN_TEXT), f"unsafe initramfs source: {source}")
        mode = 0o644 if source == "inittab" else 0o755
        members[target] = replace(template, mode=stat.S_IFREG | mode, data=data)
    auth = validate_credentials(credentials)
    for name, mode in (("root", stat.S_IFDIR | 0o700), ("root/.ssh", stat.S_IFDIR | 0o700),
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
    # The baseline must not retain an additional userspace action owner.
    for name, item in members.items():
        if stat.S_ISREG(item.mode) and name not in {"bin/busybox", "bin/reboot"}:
            require(not any(token in item.data for token in FORBIDDEN_TEXT), f"forbidden runtime action in {name}")
        if stat.S_ISREG(item.mode) and stat.S_IMODE(item.mode) & 0o111:
            require(not any(token in item.data for token in OLD_EXECUTABLE_TEXT), f"old executable marker in {name}")
    first = encode(members)
    second = encode(parse(first))
    require(first == second, "initramfs serialization is not byte-identical")
    return first, {name: {"mode": oct(item.mode), "size": len(item.data), "sha256": sha(item.data)} for name, item in sorted(members.items())}


def android_v0(kernel: Path, ramdisk: Path, dtb: Path, repo: Path) -> tuple[bytes, dict[str, object]]:
    serializer = repo / "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
    require(sha(regular(serializer)) == "569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4", "Android-v0 serializer changed")
    # The serializer's public build() API is used after a source identity gate.
    spec = importlib.util.spec_from_file_location("android_v0_serializer", serializer)
    require(spec and spec.loader, "Android-v0 serializer unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    args = type("Args", (), {"kernel": kernel, "ramdisk": ramdisk, "dtb": dtb,
        "page_size": PAGE, "lk_android8": True, "dtb_mode": "append", "cmdline": "bootopt=64S3,32N2,64N2",
        "name": "gemini-toprgu-L", "kernel_addr": ADDRESSES["kernel"],
        "ramdisk_addr": ADDRESSES["ramdisk"], "second_addr": ADDRESSES["second"],
        "tags_addr": ADDRESSES["tags"]})()
    return mod.build(args)


def validate_package(package: Path) -> None:
    require(sha(regular(package / "Image.gz")) == IMAGE_GZ_SHA256, "kernel Image.gz identity changed")
    require(sha(regular(package / "kernel.config")) == CONFIG_SHA256, "resolved config identity changed")
    build = json.loads(regular(package / "provenance/build.json"))
    require(build.get("source_sha256") == SOURCE_SHA256 and build.get("kernel_source", {}).get("sha256") == SOURCE_SHA256,
            "kernel source identity changed")
    require(build.get("repository_commit") == "745ecaea21c004a377a01287bea8ac3b58c2d6e2" and
            build.get("repository_dirty") is False, "kernel package commit/clean state changed")
    require(build.get("kernel_release") == RELEASE and build.get("build_profile") == PROFILE and
            build.get("target_architecture") == "arm64" and build.get("build_architecture") == "x86_64" and
            build.get("modules_built") is False, "kernel package provenance changed")
    require(build.get("patchset_sha256") == PATCHSET_SHA256 and
            build.get("config_sha256") == CONFIG_SHA256 and
            build.get("config_inputs_sha256") == CONFIG_INPUTS_SHA256, "series/config provenance changed")
    sums = regular(package / "SHA256SUMS", "kernel package inventory").decode("ascii")
    seen: set[str] = set()
    for line in sums.splitlines():
        expected, name = line.split(maxsplit=1); name = name.removeprefix("*").removeprefix("./")
        require(name not in seen and ".." not in Path(name).parts and not Path(name).is_absolute(),
                "kernel package inventory framing changed")
        member = package / name
        require(member.is_file() and not member.is_symlink() and sha(member.read_bytes()) == expected,
                f"kernel package member changed: {name}")
        seen.add(name)
    require(sha(regular(package / "SHA256SUMS")) == PACKAGE_INVENTORY_SHA256, "kernel package inventory changed")


def pad(raw: bytes) -> bytes:
    require(0 < len(raw) < LK_LIMIT, "Android-v0 image does not fit boot2")
    return raw + bytes(LK_LIMIT - len(raw))


def write_exclusive(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = path.open("xb")
    try:
        fd.write(data)
    finally:
        fd.close()
    path.chmod(mode)
