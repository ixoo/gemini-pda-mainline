#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Set up the one reviewed Debian QEMU tool prefix; no system installation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time

INVENTORY_SHA = "99f81a08d3cee92a3878ec9c5a94d3575e000b3358f27a87ec6377fbfe43f97e"
TOOLS = Path("/workspace/gemini-pda/tools")
DESTINATION = TOOLS / "qemu-bookworm-7.2-deb12u18-b3"
STAGE_NAME = ".qemu-bookworm-7.2-deb12u18-b3.partial"
MAX_UNPACKED = 256 * 1024 * 1024
MAX_MEMBERS = 20000
TRANSFER_SECONDS = 60


def run(arguments, *, env=None):
    result = subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=30, env=env, check=False)
    if result.returncode:
        raise ValueError("command refused: " + str(arguments[0]) + ": "
                         + result.stderr.decode(errors="replace")[:2000])
    if len(result.stdout) > 1024 * 1024 or len(result.stderr) > 65536:
        raise ValueError("unexpected command output size")
    return result.stdout.decode()


def file_digest(path, *, durable=False):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        if durable:
            os.fsync(stream.fileno())
    return digest.hexdigest()


def safe_directory(path):
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or not ancestor.is_dir():
            raise ValueError("unsafe directory path")
    if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o022:
        raise ValueError("unsafe managed directory ownership/mode")


def installed_versions():
    output = run(["dpkg-query", "-W", "-f=${Package}\t${db:Status-Abbrev}\t${Version}\t${Architecture}\n"])
    return {parts[0]: parts[2] for line in output.splitlines()
            if len(parts := line.split("\t")) == 4 and parts[1].startswith("ii")
            and parts[3] in ("amd64", "all")}


def check_dependencies(value, available):
    # Binary amd64/all control relations must not contain source-build profile
    # or architecture restrictions. Refuse syntax outside this reviewed subset.
    relation = re.compile(r"([a-z0-9][a-z0-9+.-]*)(?::(any|native|amd64))?"
                          r"(?:\s*\((<<|<=|=|>=|>>)\s*([^()\s]+)\))?")
    if not value:
        return
    for group in value.split(","):
        satisfied = False
        for alternative in group.split("|"):
            match = relation.fullmatch(alternative.strip())
            if not match:
                raise ValueError("unsupported dependency relation: " + alternative.strip())
            name, _qualifier, operator, required = match.groups()
            if name not in available:
                continue
            if operator is None:
                satisfied = True
            else:
                compared = subprocess.run(["dpkg", "--compare-versions", available[name],
                                           operator, required], timeout=5, check=False)
                if compared.returncode not in (0, 1):
                    raise ValueError("dependency version comparison failed")
                satisfied |= compared.returncode == 0
        if not satisfied:
            raise ValueError("unsatisfied dependency: " + group.strip())


def member_name(name):
    while name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/")
    if name in ("", "."):
        return ""
    if (name.startswith("/") or any(p in ("", ".", "..") for p in name.split("/"))
            or any(ord(c) < 32 for c in name)):
        raise ValueError("unsafe package member path")
    return name


def link_destination(name, target, hard, inventory):
    if target.startswith("/") or any(ord(c) < 32 for c in target):
        raise ValueError("absolute/control package link: " + name)
    parts = [] if hard else name.split("/")[:-1]
    for component in target.split("/"):
        if component in ("", "."):
            continue
        current = "/".join(parts)
        if current in inventory and inventory[current]["kind"] != "directory":
            raise ValueError("package link traverses non-directory: " + name)
        if component == "..":
            if not parts:
                raise ValueError("package link escapes prefix: " + name)
            parts.pop()
        else:
            parts.append(component)
            current = "/".join(parts)
            if current in inventory and inventory[current]["kind"] in ("link", "hard"):
                raise ValueError("package link traverses another link: " + name)
    result = "/".join(parts)
    if hard and (result not in inventory or inventory[result]["kind"] != "file"):
        raise ValueError("hard link does not name an archived regular file")
    return result


def scan_packages(packages, download):
    inventory = {}
    total = 0
    for package in packages:
        process = subprocess.Popen(["dpkg-deb", "--fsys-tarfile", str(download / package["package"])],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                for item in archive:
                    name = member_name(item.name)
                    if not name:
                        if not item.isdir():
                            raise ValueError("package root is not a directory")
                        continue
                    if (not item.issym() and item.mode & 0o6022) or item.size < 0:
                        raise ValueError("unsafe package mode/size: " + name)
                    total += item.size
                    if len(inventory) >= MAX_MEMBERS or total > MAX_UNPACKED:
                        raise ValueError("package inventory exceeds bounds")
                    record = {"mode": item.mode & 0o777, "bytes": item.size}
                    if item.isfile():
                        record["kind"] = "file"
                        data = archive.extractfile(item)
                        sha = hashlib.sha256()
                        remaining = item.size
                        while remaining:
                            chunk = data.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise ValueError("short package member")
                            remaining -= len(chunk)
                            sha.update(chunk)
                        record["sha256"] = sha.hexdigest()
                    elif item.isdir():
                        record["kind"] = "directory"
                    elif item.issym() or item.islnk():
                        record.update(kind="hard" if item.islnk() else "link", target=item.linkname)
                    else:
                        raise ValueError("special package member refused")
                    if name in inventory and inventory[name] != record:
                        raise ValueError("conflicting package member: " + name)
                    inventory[name] = record
            # Drain only bounded tar padding, then require successful producer.
            if len(process.stdout.read(1024 * 1024 + 1)) > 1024 * 1024:
                raise ValueError("excessive package tar padding")
            process.wait(timeout=10)
            errors = process.stderr.read(65537)
            if process.returncode or errors:
                raise ValueError("package tar producer failed")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()
    for name, record in inventory.items():
        for parent in PurePosixPath(name).parents:
            if str(parent) != "." and (str(parent) not in inventory
                                       or inventory[str(parent)]["kind"] != "directory"):
                raise ValueError("package member traverses non-directory: " + name)
        if record["kind"] in ("link", "hard"):
            link_destination(name, record["target"], record["kind"] == "hard", inventory)
    return inventory, total


def fetch(package, directory, cancellation, *, protocols="=https"):
    partial = directory / (package["package"] + ".partial")
    deadline = time.monotonic() + TRANSFER_SECONDS
    partial.touch(mode=0o600, exist_ok=False)
    process = subprocess.Popen([
        "curl", "--fail", "--silent", "--show-error", "--proto", protocols,
        "--connect-timeout", "5", "--max-time", str(TRANSFER_SECONDS),
        "--max-filesize", str(package["bytes"]), "--output", str(partial), package["url"]],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        start_new_session=True)
    try:
        while process.poll() is None:
            if cancellation.is_set() or time.monotonic() >= deadline:
                raise InterruptedError("package transfer canceled or exceeded deadline")
            if partial.stat().st_size > package["bytes"]:
                raise ValueError("package exceeds pinned size")
            try:
                process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
        errors = process.stderr.read(65537)
        if process.returncode:
            raise ValueError("package download failed: " + package["package"]
                             + ": " + errors.decode(errors="replace")[:2000])
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
        process.stderr.close()
    if partial.stat().st_size != package["bytes"] or file_digest(partial, durable=True) != package["sha256"]:
        raise ValueError("package hash/size mismatch: " + package["package"])
    partial.rename(directory / package["package"])


def publish_prefix(source, destination):
    library = ctypes.CDLL(None, use_errno=True)
    rename = library.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        number = ctypes.get_errno()
        raise OSError(number, "no-replace prefix publication failed")


def verify_prefix(prefix, inventory):
    for name, record in inventory.items():
        path = prefix / name
        info = path.lstat()
        kind = record["kind"]
        if kind == "directory":
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("extracted directory mismatch")
        elif kind == "link":
            if not stat.S_ISLNK(info.st_mode) or os.readlink(path) != record["target"]:
                raise ValueError("extracted link mismatch")
        else:
            source = record
            if kind == "hard":
                target = link_destination(name, record["target"], True, inventory)
                source = inventory[target]
            if (not stat.S_ISREG(info.st_mode) or info.st_size != source["bytes"]
                    or file_digest(path, durable=True) != source["sha256"]):
                raise ValueError("extracted regular file mismatch: " + name)


def inspect_emulator(prefix):
    binary = prefix / "usr/bin/qemu-system-aarch64"
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("LD_"):
            environment.pop(name)
    environment["LD_BIND_NOW"] = "1"
    environment["LD_LIBRARY_PATH"] = str(prefix / "usr/lib/x86_64-linux-gnu") + ":" + str(prefix / "lib/x86_64-linux-gnu")
    environment["QEMU_MODULE_DIR"] = str(prefix / "usr/lib/x86_64-linux-gnu/qemu")
    elf = run(["readelf", "-l", str(binary)])
    interpreters = re.findall(r"Requesting program interpreter: ([^\]]+)\]", elf)
    if len(interpreters) != 1 or interpreters[0] != "/lib64/ld-linux-x86-64.so.2":
        raise ValueError("unexpected ELF interpreter")
    linked = run([interpreters[0], "--list", str(binary)], env=environment)
    if "not found" in linked:
        raise ValueError("unresolved QEMU library")
    libraries = {}
    for line in linked.splitlines():
        if line.strip().startswith("linux-vdso.so."):
            continue
        match = re.search(r"(?:=>\s*)?(/[^\s]+)\s+\(0x[0-9a-f]+\)", line)
        if not match:
            raise ValueError("unclassified loader output")
        path = Path(match.group(1)).resolve(strict=True)
        label = str(path).replace(str(prefix), "$QEMU_PREFIX")
        libraries[label] = {"bytes": path.stat().st_size, "sha256": file_digest(path)}
    command = [str(binary), "-L", str(prefix / "usr/share/qemu")]
    version = run(command + ["--version"], env=environment)
    if "Debian 1:7.2+dfsg-7+deb12u18+b3" not in version:
        raise ValueError("unexpected QEMU runtime version")
    machines = run(command + ["-machine", "help"], env=environment)
    cpus = run(command + ["-machine", "virt,accel=tcg", "-cpu", "help"], env=environment)
    if not re.search(r"^virt\s", machines, re.M) or not re.search(r"^\s*max\s*$", cpus, re.M):
        raise ValueError("required virt/max not enumerated")
    return {"version": version.strip(), "executable_sha256": file_digest(binary),
            "resolved_libraries": libraries, "machine_virt": True, "cpu_max": True,
            "machine_listing_sha256": hashlib.sha256(machines.encode()).hexdigest(),
            "cpu_listing_sha256": hashlib.sha256(cpus.encode()).hexdigest(), "guest_run": False}


def setup(inventory, raw, execute):
    if (platform.system() != "Linux" or platform.machine() != "x86_64"
            or os.getuid() != 10001 or hashlib.sha256(raw).hexdigest() != INVENTORY_SHA):
        raise ValueError("exact Buildbox identity/inventory required")
    if (len(inventory["packages"]) != 39 or inventory["total_archive_bytes"] != 21419684
            or sum(p["bytes"] for p in inventory["packages"]) != 21419684):
        raise ValueError("package inventory bound mismatch")
    actual = installed_versions()
    for name, version in inventory["installed_dependency_versions"].items():
        if actual.get(name) != version:
            raise ValueError("installed dependency changed: " + name)
    if DESTINATION.exists() or DESTINATION.is_symlink():
        raise ValueError("destination already exists; preserve it and review its receipt")
    if not execute:
        return {"status": "preflight_only", "package_count": 39, "destination": str(DESTINATION)}
    safe_directory(TOOLS.parent)
    TOOLS.mkdir(mode=0o700, exist_ok=True)
    safe_directory(TOOLS)
    if shutil.disk_usage(TOOLS).free < inventory["free_space_admission_minimum_bytes"]:
        raise ValueError("insufficient setup space")
    lock = TOOLS / ".qemu-bookworm-7.2-deb12u18-b3.lock"
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_mode & 0o077):
            raise ValueError("unsafe setup lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if DESTINATION.exists() or DESTINATION.is_symlink():
            raise ValueError("destination appeared while acquiring lock")
        stage = TOOLS / STAGE_NAME
        marker = b"gemini-qemu-setup:" + INVENTORY_SHA.encode() + b"\n"
        if stage.exists() or stage.is_symlink():
            safe_directory(stage)
            marker_path = stage / ".owner"
            if (marker_path.is_symlink() or not marker_path.is_file()
                    or marker_path.read_bytes() != marker
                    or not set(p.name for p in stage.iterdir()) <= {".owner", "debs", "prefix"}):
                raise ValueError("unrecognized stale setup state")
            shutil.rmtree(stage)
        stage.mkdir(mode=0o700)
        try:
            (stage / ".owner").write_bytes(marker)
            downloads, prefix = stage / "debs", stage / "prefix"
            downloads.mkdir(mode=0o700)
            prefix.mkdir(mode=0o700)
            print("phase=download_verified_packages", flush=True)
            pool = ThreadPoolExecutor(max_workers=4)
            cancellation = threading.Event()
            try:
                list(pool.map(lambda package: fetch(package, downloads, cancellation), inventory["packages"]))
            finally:
                cancellation.set()
                pool.shutdown(wait=True, cancel_futures=True)
            available = dict(inventory["installed_dependency_versions"])
            available.update({p["package"]: p["version"] for p in inventory["packages"]})
            controls = {}
            for package in inventory["packages"]:
                output = run(["dpkg-deb", "--field", str(downloads / package["package"])])
                fields = {}
                key = None
                for line in output.splitlines():
                    if line and not line[0].isspace():
                        key, value = line.split(":", 1)
                        if key in fields:
                            raise ValueError("duplicate package control field")
                        fields[key] = value.strip()
                    elif line and key is not None:
                        fields[key] += " " + line.strip()
                for field, key in (("Package", "package"), ("Version", "version"), ("Architecture", "architecture")):
                    if fields.get(field) != package[key]:
                        raise ValueError("package control identity mismatch: " + package["package"]
                                         + " " + field + " expected=" + package[key]
                                         + " actual=" + fields.get(field, "missing"))
                for field in ("Depends", "Pre-Depends"):
                    check_dependencies(fields.get(field, ""), available)
                controls[package["package"]] = {field: fields.get(field, "") for field in ("Depends", "Pre-Depends")}
            print("phase=scan_complete_package_inventory", flush=True)
            members, total = scan_packages(inventory["packages"], downloads)
            print("phase=extract_verified_prefix", flush=True)
            for package in inventory["packages"]:
                run(["dpkg-deb", "--extract", str(downloads / package["package"]), str(prefix)])
            verify_prefix(prefix, members)
            inspection = inspect_emulator(prefix)
            receipt = {"schema": 1, "inventory_sha256": INVENTORY_SHA,
                       "destination": str(DESTINATION), "package_count": 39,
                       "archive_bytes": 21419684, "unpacked_member_bytes": total,
                       "installed_dependency_versions": inventory["installed_dependency_versions"],
                       "verified_control_relations": controls, "members": members,
                       "inspection": inspection, "system_installation": False,
                       "maintainer_scripts_executed": False, "guest_or_device_action": False}
            with (prefix / "setup-receipt.json").open("x") as stream:
                json.dump(receipt, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            for directory in sorted((prefix, *(prefix / name for name, entry in members.items()
                                               if entry["kind"] == "directory")),
                                    key=lambda path: len(path.parts), reverse=True):
                dirfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    os.fsync(dirfd)
                finally:
                    os.close(dirfd)
            if DESTINATION.exists() or DESTINATION.is_symlink():
                raise ValueError("destination appeared before publication")
            publish_prefix(prefix, DESTINATION)
            dirfd = os.open(TOOLS, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
            # Verify that relocation still resolves the same local libraries.
            final_inspection = inspect_emulator(DESTINATION)
            if final_inspection != inspection:
                raise ValueError("relocated emulator inspection changed; retain prefix for review")
            return {"status": "ready", "destination": str(DESTINATION),
                    "inventory_sha256": INVENTORY_SHA, "inspection": inspection,
                    "receipt_sha256": file_digest(DESTINATION / "setup-receipt.json"),
                    "receipt_path": str(DESTINATION / "setup-receipt.json"),
                    "package_count": 39, "archive_bytes": 21419684,
                    "guest_or_device_action": False}
        finally:
            shutil.rmtree(stage)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--inventory-stdin", action="store_true")
    args = parser.parse_args()
    raw = (sys.stdin.buffer.read(32769) if args.inventory_stdin else
           (Path(__file__).resolve().parents[1] / "qemu-debian-packages.json").read_bytes())
    if len(raw) > 32768:
        parser.error("oversized inventory")
    def interrupted(number, _frame):
        raise InterruptedError("setup interrupted by signal " + str(number))
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGALRM):
        signal.signal(number, interrupted)
    signal.alarm(300)
    try:
        print(json.dumps(setup(json.loads(raw), raw, args.execute), sort_keys=True))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, "QEMU setup refused: " + str(error) + "\n")
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
