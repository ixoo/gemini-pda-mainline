#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded metadata inventory; never powers, opens, or commands a radio.

Default execution reports the protocol without reading the host. Fixture mode
reads an immutable synthetic tree, never a mixture of fixture and live paths.
An observation identifies Linux device ancestry, not silicon or wire protocol.
"""

import argparse
import errno
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time


MAX_FILE = 4096
MAX_TOTAL = 256 * 1024
MAX_ENTRIES = 32
MAX_SECONDS = 15
BOOT_PATH = "/proc/sys/kernel/random/boot_id"
KERNEL_PATH = "/proc/sys/kernel/osrelease"
MODEL_PATH = "/sys/firmware/devicetree/base/model"
SDIO_PATH = "/sys/bus/sdio/devices"
WLAN_PATH = "/sys/class/net/wlan0/device"
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
KERNEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+\-]{0,127}\Z")
SDIO_NAME = re.compile(r"mmc[0-9]{1,3}:[0-9a-fA-F]{4}:([1-7])\Z")
HEX = re.compile(r"0x([0-9a-fA-F]{1,4})\Z")
ALIAS = re.compile(r"sdio:c([0-9a-fA-F]{2})v([0-9a-fA-F]{4})d([0-9a-fA-F]{4})\Z")
MODELS = {"MT6797X": "vendor_mt6797x", "Planet Computers Gemini PDA": "gemini_pda"}
KNOWN_SDIO = {0x6628, 0x6630, 0x6632}


class ObservationError(Exception):
    """A fixed, non-sensitive reason code; never includes input content."""


class Refusal(ObservationError):
    pass


class Inconclusive(ObservationError):
    pass


class Reader:
    """Resolve below one root, then use no-follow directory descriptors.

    Paths returned by resolve are internal only and must not be serialized.
    Fixture trees must remain immutable while collecting. No unrestricted
    directory walk, driver attribute, proc debug interface, or resource file
    is exposed by this class's callers.
    """

    def __init__(self, root, *, fixture, max_file=MAX_FILE,
                 max_total=MAX_TOTAL, max_entries=MAX_ENTRIES,
                 seconds=MAX_SECONDS, clock=time.monotonic):
        try:
            self.root = Path(root).resolve()
        except (OSError, RuntimeError):
            raise Refusal("invalid_root") from None
        if not self.root.is_dir() or (fixture and self.root == Path("/")):
            raise Refusal("invalid_fixture_root")
        if not fixture and self.root != Path("/"):
            raise Refusal("invalid_live_root")
        self.fixture = fixture
        self.max_file = max_file
        self.max_total = max_total
        self.max_entries = max_entries
        self.bytes_read = 0
        self.entries_seen = 0
        self.clock = clock
        self.deadline = clock() + seconds
        self.root_fd = os.open(str(self.root), os.O_RDONLY | os.O_DIRECTORY)

    def close(self):
        os.close(self.root_fd)

    def check_time(self):
        if self.clock() >= self.deadline:
            raise Refusal("time_budget")

    @staticmethod
    def translate_error(exc):
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return Refusal("unsafe_or_changed_path")
        return Inconclusive("metadata_unavailable")

    def directory(self, parts):
        self.check_time()
        fd = os.dup(self.root_fd)
        try:
            for part in parts:
                self.check_time()
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=fd)
                os.close(fd)
                fd = nxt
            return fd
        except OSError as exc:
            os.close(fd)
            raise self.translate_error(exc) from None

    def resolve(self, path):
        self.check_time()
        pending = str(path).split("/")
        resolved = []
        links = 0
        components = 0
        while pending:
            self.check_time()
            part = pending.pop(0)
            components += 1
            if components > 96:
                raise Refusal("path_budget")
            if part in ("", "."):
                continue
            if part == "..":
                if not resolved:
                    raise Refusal("path_escape")
                resolved.pop()
                continue
            fd = self.directory(resolved)
            try:
                info = os.stat(part, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    target = os.readlink(part, dir_fd=fd)
                    links += 1
                    if links > 16 or len(target) > MAX_FILE:
                        raise Refusal("symlink_budget")
                    if os.path.isabs(target):
                        if self.fixture:
                            try:
                                target = str(Path(target).relative_to(self.root))
                            except ValueError:
                                raise Refusal("path_escape") from None
                        resolved = []
                    pending = target.split("/") + pending
                else:
                    resolved.append(part)
            except OSError as exc:
                raise self.translate_error(exc) from None
            finally:
                os.close(fd)
        return tuple(resolved)

    def read(self, path):
        parts = self.resolve(path)
        if not parts:
            raise Refusal("special_file")
        parent = self.directory(parts[:-1])
        fd = None
        try:
            mode = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False).st_mode
            if not stat.S_ISREG(mode):
                raise Refusal("special_file")
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent)
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise Refusal("special_file")
            chunks = []
            length = 0
            while True:
                self.check_time()
                if length >= self.max_file:
                    raise Refusal("file_byte_budget")
                if self.bytes_read >= self.max_total:
                    raise Refusal("total_byte_budget")
                chunk = os.read(fd, min(self.max_file - length,
                                        self.max_total - self.bytes_read, 4096))
                self.bytes_read += len(chunk)
                length += len(chunk)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        except OSError as exc:
            raise self.translate_error(exc) from None
        finally:
            if fd is not None:
                os.close(fd)
            os.close(parent)

    def text(self, path):
        try:
            data = self.read(path).decode("ascii")
        except UnicodeDecodeError:
            raise Inconclusive("malformed_metadata") from None
        # Sysfs/proc scalar attributes have at most one final newline.
        if data.endswith("\n"):
            data = data[:-1]
        if not data or "\n" in data or "\x00" in data:
            raise Inconclusive("malformed_metadata")
        return data

    def of_strings(self, path):
        data = self.read(path)
        if not data.endswith(b"\0"):
            raise Inconclusive("malformed_of_metadata")
        try:
            values = data[:-1].decode("ascii").split("\0")
        except UnicodeDecodeError:
            raise Inconclusive("malformed_of_metadata") from None
        if not values or any(not value for value in values):
            raise Inconclusive("malformed_of_metadata")
        return values

    def sdio_entries(self):
        fd = self.directory(self.resolve(SDIO_PATH))
        names = []
        entries = None
        try:
            # Python 3.5 in the retained Gemian image predates scandir(fd).
            # Linux procfs resolves this path to our already-open directory;
            # it does not select an unrestricted caller-supplied directory.
            scan_path = fd if sys.version_info >= (3, 7) else "/proc/self/fd/" + str(fd)
            entries = os.scandir(scan_path)
            for entry in entries:
                self.check_time()
                if self.entries_seen >= self.max_entries:
                    raise Refusal("entry_budget")
                self.entries_seen += 1
                if not SDIO_NAME.fullmatch(entry.name):
                    raise Inconclusive("unknown_sdio_entry")
                names.append(entry.name)
        except OSError as exc:
            raise self.translate_error(exc) from None
        finally:
            if entries is not None:
                # Explicit close was added in Python 3.6. The 3.5 iterator
                # releases its directory handle when its reference is dropped.
                close = getattr(entries, "close", None)
                if close is not None:
                    close()
                del entries
            os.close(fd)
        return sorted(names)


def check_identity(reader, expected_kernel, expected_boot_id):
    kernel = reader.text(KERNEL_PATH)
    boot = reader.text(BOOT_PATH)
    if not KERNEL.fullmatch(kernel) or not UUID.fullmatch(boot):
        raise Refusal("malformed_identity")
    if kernel != expected_kernel or boot != expected_boot_id:
        raise Refusal("identity_mismatch_or_drift")
    return {"kernel": kernel, "boot_id": boot}


def numeric(reader, path, max_value):
    match = HEX.fullmatch(reader.text(path))
    if not match or int(match.group(1), 16) > max_value:
        raise Inconclusive("malformed_sdio_id")
    return int(match.group(1), 16)


def collect_sdio(reader):
    rows = []
    for name in reader.sdio_entries():
        path = SDIO_PATH + "/" + name
        resolved = reader.resolve(path)
        if resolved[:2] != ("sys", "devices"):
            raise Inconclusive("unexpected_device_ancestry")
        if reader.resolve(path + "/subsystem") != ("sys", "bus", "sdio"):
            raise Inconclusive("contradictory_sdio_subsystem")
        vendor = numeric(reader, path + "/vendor", 0xffff)
        device = numeric(reader, path + "/device", 0xffff)
        cls = numeric(reader, path + "/class", 0xff)
        alias = ALIAS.fullmatch(reader.text(path + "/modalias"))
        if not alias or tuple(int(alias.group(i), 16) for i in (1, 2, 3)) != (cls, vendor, device):
            raise Inconclusive("contradictory_sdio_ids")
        rows.append({"function": int(SDIO_NAME.fullmatch(name).group(1)),
                     "vendor": "0x{0:04x}".format(vendor),
                     "device": "0x{0:04x}".format(device),
                     "class": "0x{0:02x}".format(cls),
                     "vendor_source_table_match": vendor == 0x037a and device in KNOWN_SDIO,
                     "_path": resolved})
    if len({row["_path"] for row in rows}) != len(rows):
        raise Inconclusive("duplicate_sdio_alias")
    return {"state": "observed", "functions": rows,
            "absence_interpretation": "no_silicon_or_bus_absence_claim"}


def collect_wlan(reader):
    path = reader.resolve(WLAN_PATH)
    if path[:2] != ("sys", "devices"):
        raise Inconclusive("unexpected_device_ancestry")
    subsystem = reader.resolve(WLAN_PATH + "/subsystem")
    if subsystem not in (("sys", "bus", "platform"), ("sys", "bus", "sdio")):
        raise Inconclusive("unknown_wlan_bus")
    bus = subsystem[-1]
    driver = reader.resolve(WLAN_PATH + "/driver")
    expected_driver = "mt-wifi" if bus == "platform" else "mtk_sdio_client"
    if driver != ("sys", "bus", bus, "drivers", expected_driver):
        raise Inconclusive("unknown_wlan_driver")
    facts = {"state": "observed", "bus": bus, "driver": expected_driver,
             "_path": path, "_subsystem": subsystem, "_driver": driver}
    if bus == "platform":
        node = reader.resolve(WLAN_PATH + "/of_node")
        if (path[-1] != "180f0000.wifi" or
                node[:5] != ("sys", "firmware", "devicetree", "base", "soc") or
                node[-1] != "wifi@180f0000"):
            raise Inconclusive("unmatched_platform_of_ancestry")
        if reader.of_strings(WLAN_PATH + "/of_node/compatible") != ["mediatek,wifi"]:
            raise Inconclusive("unmatched_platform_compatible")
        if reader.of_strings(WLAN_PATH + "/of_node/clock-names") != ["wifi-dma"]:
            raise Inconclusive("unmatched_platform_clock_name")
        facts.update({"of_compatible": "mediatek,wifi", "clock_name": "wifi-dma",
                      "_of_node": node})
    return facts


def observe(function, reader):
    try:
        return function(reader)
    except Inconclusive as exc:
        return {"state": "unavailable", "reason": str(exc)}


def classify(facts):
    """Only complete Linux metadata can establish the immediate netdev parent."""
    wlan = facts["wlan"]
    sdio = facts["sdio"]
    if facts["model"] == "unrecognized" or wlan["state"] != "observed" or sdio["state"] != "observed":
        return "inconclusive", "incomplete_or_unrecognized_metadata"
    matching = [row for row in sdio["functions"] if row["_path"] == wlan["_path"]]
    if wlan["bus"] == "platform":
        if matching:
            return "inconclusive", "contradictory_parent_membership"
        return "observed", "platform_wifi_parent_observed"
    if len(matching) != 1:
        return "inconclusive", "sdio_parent_not_uniquely_enumerated"
    if not matching[0]["vendor_source_table_match"]:
        return "inconclusive", "sdio_parent_outside_retained_vendor_table"
    return "observed", "sdio_wifi_parent_observed"


def public(value):
    if isinstance(value, dict):
        return {key: public(item) for key, item in value.items() if not key.startswith("_")}
    if isinstance(value, list):
        return [public(item) for item in value]
    return value


def collect(reader, expected_kernel, expected_boot_id):
    result = {"schema": 1, "mode": "fixture" if reader.fixture else "live",
              "silicon_identity": "unproven", "radio_operations": 0,
              "firmware_reads": 0}
    try:
        result["identity"] = check_identity(reader, expected_kernel, expected_boot_id)
        models = reader.of_strings(MODEL_PATH)
        model = MODELS.get(models[0], "unrecognized") if len(models) == 1 else "unrecognized"
        facts = {"model": model, "sdio": observe(collect_sdio, reader),
                 "wlan": observe(collect_wlan, reader)}
        # A stable boot ID alone cannot exclude netdev unbind/rebind. Repeat
        # the bounded ancestry observation and refuse a changed result.
        if observe(collect_wlan, reader) != facts["wlan"]:
            raise Inconclusive("wlan_topology_changed")
        reader.check_time()
        result["status"], result["classification"] = classify(facts)
        result["facts"] = public(facts)
    except Refusal as exc:
        result.update(status="refused", reason=str(exc))
    except Inconclusive as exc:
        result.update(status="inconclusive", reason=str(exc))
    result["identity_checked_end"] = False
    if "identity" in result and result["status"] != "refused":
        try:
            check_identity(reader, expected_kernel, expected_boot_id)
            reader.check_time()
            result["identity_checked_end"] = True
        except ObservationError as exc:
            result.update(status="refused", reason=str(exc))
    result["budget"] = {"bytes_read": reader.bytes_read,
                        "sdio_entries_seen": reader.entries_seen,
                        "max_file_bytes": reader.max_file,
                        "max_total_bytes": reader.max_total,
                        "max_sdio_entries": reader.max_entries,
                        "max_seconds": MAX_SECONDS}
    return result


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal("invalid_arguments")


def alarm_handler(_signum, _frame):
    raise Refusal("time_budget")


def main(argv=None):
    reader = None
    alarm_set = False
    try:
        parser = JsonParser(description=__doc__)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--collect", action="store_true", help="read live allowlisted metadata")
        mode.add_argument("--fixture-root", help="read only an immutable synthetic tree")
        parser.add_argument("--expected-kernel")
        parser.add_argument("--expected-boot-id")
        args = parser.parse_args(argv)
        if not args.collect and args.fixture_root is None:
            result = {"schema": 1, "mode": "dry-run", "status": "not-collected",
                      "radio_operations": 0, "firmware_reads": 0,
                      "requires": ["explicit_collection_mode", "expected_kernel",
                                   "expected_boot_id", "admitted_exclusive_custody"],
                      "limits": {"file_bytes": MAX_FILE, "total_bytes": MAX_TOTAL,
                                 "sdio_entries": MAX_ENTRIES, "seconds": MAX_SECONDS}}
        else:
            if (not args.expected_kernel or not KERNEL.fullmatch(args.expected_kernel) or
                    not args.expected_boot_id or not UUID.fullmatch(args.expected_boot_id)):
                raise Refusal("expected_identity_required")
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS)
            alarm_set = True
            reader = Reader(args.fixture_root if args.fixture_root is not None else "/",
                            fixture=args.fixture_root is not None)
            result = collect(reader, args.expected_kernel, args.expected_boot_id)
    except Refusal as exc:
        result = {"schema": 1, "status": "refused", "reason": str(exc)}
    except (OSError, RuntimeError):
        result = {"schema": 1, "status": "refused", "reason": "environment_unavailable"}
    finally:
        if alarm_set:
            signal.setitimer(signal.ITIMER_REAL, 0)
        if reader is not None:
            reader.close()
    print(json.dumps(result, sort_keys=True))
    return {"not-collected": 0, "observed": 0, "inconclusive": 2, "refused": 3}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
