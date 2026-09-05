#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently validate the complete private A53 candidate and member delta."""

import argparse
import base64
import gzip
import io
import json
import os
from pathlib import Path
import re
import runpy
import stat
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[2]
AUDIT = runpy.run_path(str(HERE / "audit_foundation.py"))
regular, require, digest = AUDIT["regular"], AUDIT["require"], AUDIT["digest"]
CANDIDATE_FILES = {"boot.img", "boot2-padded.img", "Image.gz", "board.dtb",
                   "kernel.config", "initramfs.img", "candidate.json"}
REMOVED = {"bin/usb-net", "bin/usb-shell", "bin/local-shell", "bin/emmc-flash-boot2",
           "bin/x-probe", "bin/input-event-capture", "bin/ac-record"}
SOURCES = {"init": ("init", 0o755), "etc/inittab": ("inittab", 0o644),
           "bin/usb-auth": ("usb-auth", 0o755), "bin/console-status": ("console-status", 0o755),
           "bin/admin-shell": ("admin-shell", 0o755)}
BINARIES = {"dropbear", "dropbearkey", "dropbearconvert", "keyboard-observe", "kmsg-capture", "kmsg-seal"}
USERSPACE_FILES = BINARIES | {"SHA256SUMS", "auth-tests.json", "localoptions.h", "inputs.json",
    "effective-options.txt", "provenance.txt", "kmsg-parser-tests.txt", "kmsg-io-tests.txt", "kmsg-seal-tests.txt", "licenses/Dropbear-LICENSE",
    "licenses/LibTomCrypt-LICENSE", "licenses/LibTomMath-LICENSE", "shell-tests.json",
    "emmc-shell-tests.txt", "emmc-runner-tests.txt", "session-shell-tests.json", "licenses/BusyBox-copyright"}
BUSYBOX_SHA = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
INPUTS = {"localoptions.h", "scripts/build-userspace.sh", "scripts/provision.py", "scripts/test-auth.py",
          "src/kmsg-capture.c", "src/kmsg-seal.c", "../keyboard/keyboard-observe.c", "../keyboard/protocol.h"}
AUTH_CASES = ["compiled-authentication-surface", "independent-host-key-conversion",
    "authorized-exec-separated-streams", "unapproved-key-refused", "password-authentication-refused",
    "host-identity-mismatch-refused", "forwarding-refused", "interrupted-server-refused"]
META = ("mode", "uid", "gid", "nlink", "mtime", "devmajor", "devminor", "rdevmajor", "rdevminor", "data")
SHELL_CASES = ["exact-required-applet-inventory", "syntax-init", "syntax-usb-auth", "syntax-console-status",
    "usb-missing", "usb-wrong-interface", "usb-link-fail", "usb-address-fail", "usb-pass",
    "usb-server-fail", "usb-server-hold", "console-pass", "console-map-hash", "console-vt-fail",
    "console-stty-fail", "console-unicode-fail", "console-preflight-fail", "console-load-fail",
    "console-readback-fail", "console-load-pass", "init-pass", "init-mount-fail", "init-cpu-fail",
    "init-kernel-fail", "inherited-regular-file-size-limit"]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def load_json(path):
    return json.loads(regular(path), object_pairs_hook=unique_object)


def private_tree(root, files, executable=frozenset(), directories=frozenset()):
    root = AUDIT["safe_directory"](root)
    found, subdirectories = set(), set()
    for directory, dirs, names in os.walk(root, followlinks=False):
        current = Path(directory)
        require(stat.S_IMODE(current.lstat().st_mode) == 0o700 and
                current.stat().st_uid == os.getuid(), "private directory mode or owner")
        for name in dirs:
            child = current / name
            require(not child.is_symlink(), "private directory symlink")
            subdirectories.add(child.relative_to(root).as_posix())
        for name in names:
            child = current / name
            relative = child.relative_to(root).as_posix()
            info = child.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid(),
                    "private file type, links or owner")
            require(stat.S_IMODE(info.st_mode) == (0o700 if relative in executable else 0o600),
                    "private file mode")
            found.add(relative)
    require(found == files and subdirectories == directories, "private tree inventory")
    return root


def check_elf(data):
    require(len(data) >= 64 and data[:7] == b"\x7fELF\x02\x01\x01", "ELF64 little-endian header")
    elf_type, machine, version = struct.unpack_from("<HHI", data, 16)
    entry, phoff = struct.unpack_from("<QQ", data, 24)
    ehsize, phsize, phcount = struct.unpack_from("<HHH", data, 52)
    require((elf_type, machine, version, ehsize, phsize) == (2, 183, 1, 64, 56) and
            0 < phcount <= 1024 and 64 <= phoff <= len(data) and
            phoff + phsize * phcount <= len(data), "static AArch64 ELF layout")
    entry_mapped = False
    for index in range(phcount):
        kind, flags, offset, virtual, _, size, memory, _ = struct.unpack_from("<IIQQQQQQ", data, phoff + index * phsize)
        require(kind not in (2, 3), "dynamic or interpreted ELF")
        require(offset <= len(data) and size <= len(data) - offset, "ELF segment bounds")
        if kind == 1:
            require(size <= memory, "ELF load size")
            entry_mapped |= bool(flags & 1 and virtual <= entry < virtual + memory)
    require(entry_mapped, "ELF entry is not executable")


def git_source(revision, path):
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "repository revision format")
    return AUDIT["git_bytes"](REPO, revision, path)


def check_unittest_receipt(raw, count):
    """Accept one complete fixed suite, with no skipped or failed outcomes."""
    require(type(raw) is bytes and type(count) is int and count > 0, "unittest receipt input")
    report = raw.decode("ascii")
    summaries = re.findall(r"^Ran .*", report, re.MULTILINE)
    ending = re.search(r"(?:\A|\n)Ran ([0-9]+) tests in ([0-9]+(?:\.[0-9]+)?)s\n\nOK\n?\Z", report)
    require(len(summaries) == 1 and ending is not None and ending[1] == str(count) and
            re.search(r"\b(?:FAIL|FAILED|ERROR|skipped)\b|\.\.\. (?:expected failure|unexpected success)\b",
                      report) is None, "unittest receipt incomplete, malformed, skipped or failed")


def check_userspace(package, manifest_sha, candidate_revision):
    package = private_tree(package, USERSPACE_FILES, BINARIES, {"licenses"})
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha), "userspace manifest format")
    AUDIT["inventory"](package, {"manifest_sha256": manifest_sha,
                               "inventory_count": len(USERSPACE_FILES) - 1})
    require(regular(package / "localoptions.h") == regular(HERE / "localoptions.h"), "server options differ")
    options = regular(package / "effective-options.txt").decode().splitlines()
    for line in regular(HERE / "localoptions.h").decode().splitlines():
        if line.startswith("#define "):
            require(options.count(line) == 1, "effective server option missing or duplicate")
    provenance, tool_hashes = {}, {}
    for line in regular(package / "provenance.txt").decode().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (aarch64-linux-gnu-(?:gcc|ld))", line)
        if match:
            sha, name = match.groups()
            require(name not in tool_hashes, "duplicate compiler identity")
            tool_hashes[name] = sha
        else:
            key, separator, value = line.partition("=")
            require(separator and value and key not in provenance, "malformed build provenance")
            provenance[key] = value
    require(set(provenance) == {"repository_commit", "source_sha256", "compiler",
            "independent_binary_builds", "byte_identical", "device_action"} and
            set(tool_hashes) == {"aarch64-linux-gnu-gcc", "aarch64-linux-gnu-ld"}, "build provenance inventory")
    require(provenance["independent_binary_builds"] == "2" and provenance["byte_identical"] == "yes" and
            provenance["device_action"] == "none", "build reproducibility evidence")
    source_contract = load_json(HERE / "userspace.json")
    require(provenance["source_sha256"] == source_contract["dropbear"]["sha256"], "Dropbear source pin")
    inputs = load_json(package / "inputs.json")
    require(set(inputs) == INPUTS, "userspace source inventory")
    for relative, sha in inputs.items():
        path = (HERE / relative).resolve(strict=True)
        repository_path = path.relative_to(REPO).as_posix()
        current = regular(path)
        require(digest(current) == sha and current == git_source(provenance["repository_commit"], repository_path)
                and current == git_source(candidate_revision, repository_path), "userspace input revision drift")
    auth = load_json(package / "auth-tests.json")
    require(auth == {"classification": "offline-authentication-pass", "cases": AUTH_CASES,
            "server": "exact-AArch64-binary-under-QEMU", "command_shell": "builder-account-shell",
            "candidate-init-boot": "not-tested", "device_action": "none", "private-fixtures": "removed"},
            "authentication evidence inventory or result")
    check_unittest_receipt(regular(package / "kmsg-parser-tests.txt"), 15)
    for name, count in (("kmsg-io-tests.txt", 12), ("kmsg-seal-tests.txt", 9)):
        check_unittest_receipt(regular(package / name), count)
    check_unittest_receipt(regular(package / "emmc-runner-tests.txt"), 6)
    shell = load_json(package / "shell-tests.json")
    unit = shell.get("ulimit_f_block_bytes")
    require(type(unit) is int and unit in (512, 1024), "shell file-size unit")
    shell_sources = {name: digest(regular(HERE / "initramfs" / name))
                     for name in ("init", "usb-auth", "console-status")}
    require(shell == {"classification": "offline-exact-busybox-shell-pass", "cases": SHELL_CASES,
            "busybox_sha256": BUSYBOX_SHA, "source_sha256": shell_sources,
            "ulimit_f_block_bytes": unit, "ulimit_f_256_bytes": unit * 256,
            "file_limit_scope": "inherited regular files only; pipes and SSH output need independent bounds",
            "device_action": "none; all effectful applets mocked", "kernel_evdev_vt_ioctl": "not-tested",
            "dropbear_binary": "not-executed-by-this-test", "candidate_init_boot": "not-tested",
            "private_fixtures": "removed"}, "exact BusyBox shell evidence differs")
    session = load_json(package / "session-shell-tests.json")
    session_tools = runpy.run_path(str(HERE / "scripts/test-session-shell.py"))
    session_cases = session_tools["EXPECTED_CASES"]
    require(type(session_cases) is list and len(session_cases) == len(set(session_cases)) == 61 and
            session.get("cases") == session_cases,
            "session shell case inventory")
    require(session == {"classification": "session-shell-fixtures-pass", "cases": session_cases,
            "case_count": 61, "shell": "exact-ARM64-BusyBox-under-QEMU", "busybox_sha256": BUSYBOX_SHA,
            "generated_source_sha256": session_tools["PINS"], "effects": "intercepted; no actual target signal or reboot",
            "effect_guard_cases": 10, "effect_guard_optimization_levels": [0, 1], "python_optimization": 0,
            "parser_transport_cases": 4,
            "runner_test_cases": 7, "fixture_timeout_seconds": 45, "fixture_cleanup_seconds": 1,
            "pidfd_kernel_behavior": "not-tested", "device_access": "none", "private_fixtures": "removed"},
            "session shell evidence inventory or result")
    emmc = regular(package / "emmc-shell-tests.txt").decode()
    for line in ("emmc_fixture_mode=exact-busybox-qemu", "actual_busybox_sha256=" + BUSYBOX_SHA,
                 "observer_busybox_identity=fixture-dispatcher-hash", "observer_fixture_timeout_seconds=90"):
        require(emmc.splitlines().count(line) == 1, "exact BusyBox eMMC fixture identity")
    check_unittest_receipt(regular(package / "emmc-shell-tests.txt"), 28)
    tested_sources = {"scripts/test-shell.py", "scripts/test-session-shell.py", "scripts/session_steps.py", "test-kmsg.py", "test-kmsg-io.py", "tests/kmsg-io-harness.c", "test-kmsg-seal.py", "tests/kmsg-seal-harness.c", "../emmc/observe.sh",
                      "../emmc/classify.py", "../emmc/test_packet.py", "../emmc/test-runner.py"}
    tested_sources.update("initramfs/" + name for name in shell_sources)
    for relative in tested_sources:
        path = (HERE / relative).resolve(strict=True)
        current = regular(path)
        repository_path = path.relative_to(REPO).as_posix()
        require(current == git_source(provenance["repository_commit"], repository_path) and
                current == git_source(candidate_revision, repository_path), "test input revision drift")
    for name in BINARIES:
        check_elf(regular(package / name))
    return package


def take_string(data):
    require(len(data) >= 4, "truncated key field")
    size = int.from_bytes(data[:4], "big")
    require(size <= len(data) - 4, "truncated key field")
    return data[4:4 + size], data[4 + size:]


def check_credentials(directory):
    files = {"admin", "admin.pub", "host", "host.pub", "dropbear_host_key", "authorized_keys", "known_hosts"}
    directory = private_tree(directory, files)
    public = {}
    for role in ("admin", "host"):
        fields = regular(directory / (role + ".pub")).split()
        require(len(fields) == 2 and fields[0] == b"ssh-ed25519", "public key format")
        verified = subprocess.run(["ssh-keygen", "-y", "-P", "", "-f", str(directory / role)],
                                  capture_output=True, timeout=10, check=True).stdout.split()
        require(verified == fields, "private and public keys disagree")
        blob = base64.b64decode(fields[1], validate=True)
        kind, rest = take_string(blob)
        raw_public, rest = take_string(rest)
        require(kind == b"ssh-ed25519" and len(raw_public) == 32 and not rest, "public key framing")
        public[role] = (fields, raw_public)
    require(public["admin"][1] != public["host"][1], "host and administrator keys must differ")
    host_key = regular(directory / "dropbear_host_key")
    kind, rest = take_string(host_key)
    secret, rest = take_string(rest)
    require(kind == b"ssh-ed25519" and len(secret) == 64 and not rest and
            secret[32:] == public["host"][1], "Dropbear host-key framing")
    # Compare the private seed as well as its public half, independently of the
    # provisioning converter. Neither key bytes nor public identities are printed.
    lines = regular(directory / "host").splitlines()
    require(lines[0] == b"-----" + b"BEGIN OPENSSH PRIVATE KEY" + b"-----" and
            lines[-1] == b"-----" + b"END OPENSSH PRIVATE KEY" + b"-----", "OpenSSH key envelope")
    raw = base64.b64decode(b"".join(lines[1:-1]), validate=True)
    require(raw.startswith(b"openssh-key-v1\0"), "OpenSSH key magic")
    cipher, tail = take_string(raw[15:])
    kdf, tail = take_string(tail)
    options, tail = take_string(tail)
    require(cipher == kdf == b"none" and options == b"" and tail[:4] == b"\0\0\0\1", "generated key encoding")
    _, tail = take_string(tail[4:])
    payload, tail = take_string(tail)
    require(not tail and len(payload) >= 8 and payload[:4] == payload[4:8], "OpenSSH private framing")
    private_kind, payload = take_string(payload[8:])
    private_public, payload = take_string(payload)
    private_secret, _ = take_string(payload)
    require(private_kind == kind and private_public == public["host"][1] and private_secret == secret,
            "private host-key conversion differs")
    authorized = b"no-port-forwarding,no-agent-forwarding,no-X11-forwarding " + b" ".join(public["admin"][0]) + b"\n"
    known = b"10.15.19.82 " + b" ".join(public["host"][0]) + b"\n"
    require(regular(directory / "authorized_keys") == authorized and regular(directory / "known_hosts") == known,
            "authentication or host pin differs")
    return authorized, host_key, known


def fields(member):
    return {name: getattr(member, name) for name in META}


def check_member_delta(baseline, candidate, new_files):
    new_dirs = {"root", "root/.ssh", "etc/dropbear"}
    expected_names = (set(baseline) - REMOVED) | set(new_files) | new_dirs
    require(REMOVED <= set(baseline) and set(candidate) == expected_names, "complete archive member inventory")
    require(not REMOVED & set(candidate), "forbidden historical helper retained")
    for name in set(baseline) - REMOVED - set(new_files):
        require(fields(candidate[name]) == fields(baseline[name]), "inherited member data or metadata changed")
    for name, (data, mode) in new_files.items():
        expected = fields(baseline["bin/reboot"])
        expected.update(mode=stat.S_IFREG | mode, data=data)
        require(fields(candidate[name]) == expected, "new member source or metadata differs")
    for name in new_dirs:
        require(name not in baseline, "new directory collides with foundation")
        expected = fields(baseline["etc"])
        expected.update(mode=stat.S_IFDIR | 0o700, data=b"")
        require(fields(candidate[name]) == expected, "credential directory metadata differs")


def validate(candidate, parent, userspace):
    candidate = private_tree(candidate, CANDIDATE_FILES)
    manifest = load_json(candidate / "candidate.json")
    require(set(manifest) == {"schema", "experiment", "preparation_state", "repository_commit", "foundation_commit",
            "foundation_manifest_sha256", "userspace_manifest_sha256", "secret_bearing", "physical_admission",
            "files", "members", "removed", "known_hosts_sha256"}, "candidate manifest inventory")
    require(manifest["schema"] == 1 and manifest["experiment"] == "a53-authenticated-baseline" and
            manifest["preparation_state"] == "preparing" and manifest["secret_bearing"] is True and
            manifest["physical_admission"] is False, "candidate status or secret classification")
    require(set(manifest["files"]) == CANDIDATE_FILES - {"candidate.json"}, "candidate file manifest inventory")
    for name, sha in manifest["files"].items():
        require(digest(regular(candidate / name)) == sha, "candidate file checksum")
    foundation = load_json(HERE / "foundation.json")
    require(manifest["foundation_commit"] == foundation["repository_build_commit"] and
            manifest["foundation_manifest_sha256"] == digest(regular(HERE / "foundation.json")), "foundation pin")
    parent = AUDIT["inventory"](parent, foundation["candidate"])
    require(parent.name == foundation["candidate"]["directory_name"], "historical candidate name")
    for new, old in {"Image.gz": "Image.gz", "kernel.config": "kernel.config",
                     "board.dtb": "mt6797-gemini-pda-pwrap-reset-serviceability.dtb"}.items():
        require(regular(candidate / new) == regular(parent / old), "kernel, DT or configuration differs")
    userspace = check_userspace(userspace, manifest["userspace_manifest_sha256"], manifest["repository_commit"])
    authorized, host_key, known = check_credentials(REPO / "artifacts/credentials/a53-auth")
    require(digest(known) == manifest["known_hosts_sha256"], "host-verification file pin")
    archive_parser = REPO / "experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py"
    require(digest(regular(archive_parser)) == "19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c", "archive parser pin")
    parse = runpy.run_path(str(archive_parser))["parse_newc"]
    ramdisk = regular(candidate / "initramfs.img")
    require(len(ramdisk) < 16777216, "compressed initramfs limit")
    with gzip.GzipFile(fileobj=io.BytesIO(ramdisk)) as stream:
        require(len(stream.read(64 * 1024 * 1024 + 1)) <= 64 * 1024 * 1024, "expanded initramfs limit")
    baseline = parse(regular(parent / "gemini-pwrap-reset-serviceability-initramfs.img"))
    members = parse(ramdisk)
    require({path.name for path in (HERE / "initramfs").iterdir()} == {item[0] for item in SOURCES.values()}, "init source inventory")
    new_files = {}
    for name, (source, mode) in SOURCES.items():
        path = HERE / "initramfs" / source
        data = regular(path)
        require(data == git_source(manifest["repository_commit"], path.relative_to(REPO).as_posix()), "init source revision")
        new_files[name] = data, mode
    emmc = HERE.parent / "emmc/observe.sh"
    emmc_source = regular(emmc)
    require(emmc_source == git_source(manifest["repository_commit"], emmc.relative_to(REPO).as_posix()), "eMMC observer revision")
    new_files.update({"bin/dropbear": (regular(userspace / "dropbear"), 0o755),
        "bin/keyboard-observe": (regular(userspace / "keyboard-observe"), 0o755),
        "bin/kmsg-capture": (regular(userspace / "kmsg-capture"), 0o755),
        "bin/kmsg-seal": (regular(userspace / "kmsg-seal"), 0o755), "bin/emmc-observe": (emmc_source, 0o755),
        "etc/passwd": (b"root:x:0:0:Administrator:/root:/bin/admin-shell\n", 0o644),
        "etc/group": (b"root:x:0:\n", 0o644), "etc/shells": (b"/bin/admin-shell\n", 0o644),
        "root/.ssh/authorized_keys": (authorized, 0o600), "etc/dropbear/host_key": (host_key, 0o600)})
    check_member_delta(baseline, members, new_files)
    summary = {name: {"mode": oct(member.mode), "size": len(member.data), "sha256": digest(member.data)}
               for name, member in members.items()}
    require(manifest["members"] == summary and manifest["removed"] == sorted(REMOVED), "member manifest or removals")
    raw, padded = regular(candidate / "boot.img"), regular(candidate / "boot2-padded.img")
    require(0 < len(raw) < 16777216 and len(padded) == 16777216 and padded == raw + bytes(16777216 - len(raw)),
            "boot container size or zero padding")
    analyzer = REPO / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    require(digest(regular(analyzer)) == "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95", "LK analyzer pin")
    subprocess.run([sys.executable, str(analyzer), "--validate-lk", "--expected-image-gz", str(candidate / "Image.gz"),
        "--expected-ramdisk", str(candidate / "initramfs.img"), "--expected-dtb", str(candidate / "board.dtb"),
        "--expected-name", "gemini-obs-L", "--expected-cmdline", "bootopt=64S3,32N2,64N2", str(candidate / "boot.img")],
        check=True, stdout=subprocess.DEVNULL)
    return {"validation": "a53-authenticated-private-candidate-pass", "candidate_sha256": digest(padded),
            "initramfs_members": len(members), "secret_bearing": True, "physical_admission": False,
            "candidate_runtime": "not-tested", "device_action": "none"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "foundation", "userspace"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.candidate, args.foundation, args.userspace)
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as error:
        parser.exit(2, f"candidate refused: {error}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
