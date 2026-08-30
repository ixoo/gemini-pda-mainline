#!/usr/bin/env python3
"""Independently validate the exact provenance-only DT delta."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct


SERVICEABILITY_SHA256 = "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c"
PACKAGE_DTB_SHA256 = "d3197c6870aa025840f6dc330e83e7871e78cce56e4b314e03085d7879c6954f"
RECORD_JSON_SHA256 = "05a3e54a412e02bc224138056552451b706111d2d98d6e1363597efeecada93d"
COMPOSED_SHA256 = "8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2"
NODE = "/chosen/gemini-late-cpu-provenance"
FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9
DIGESTS = (
    "expected-ikconfig-identity", "expected-gnu-build-id-identity",
    "expected-cmdline-identity", "upstream-source-sha256",
    "patch-series-sha256", "config-inputs-sha256",
    "resolved-config-sha256", "package-image-sha256",
    "build-provenance-sha256",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def align4(value: int) -> int:
    return (value + 3) & ~3


def cstring(data: bytes, offset: int, limit: int) -> tuple[str, int]:
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise ValueError("unterminated FDT string")
    return data[offset:end].decode("ascii"), end + 1


def parse_fdt(path: Path) -> tuple[dict[str, dict[str, bytes]], tuple[tuple[int, int], ...], int]:
    data = path.read_bytes()
    if len(data) < 40:
        raise ValueError("truncated FDT header")
    (magic, total, off_struct, off_strings, off_reserve, version, last,
     boot_cpu, size_strings, size_struct) = struct.unpack_from(">10I", data)
    if magic != FDT_MAGIC or total != len(data) or not 16 <= last <= version <= 17:
        raise ValueError("invalid FDT header")
    if off_struct + size_struct > total or off_strings + size_strings > total:
        raise ValueError("FDT block exceeds total size")
    reservations: list[tuple[int, int]] = []
    pos = off_reserve
    limit = min(value for value in (off_struct, off_strings, total) if value >= off_reserve)
    while pos + 16 <= limit:
        address, size = struct.unpack_from(">2Q", data, pos)
        pos += 16
        if not address and not size:
            break
        reservations.append((address, size))
    else:
        raise ValueError("unterminated reservation map")

    tree: dict[str, dict[str, bytes]] = {}
    stack: list[str] = []
    pos = off_struct
    end = off_struct + size_struct
    while pos + 4 <= end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, pos = cstring(data, pos, end)
            pos = align4(pos)
            node = "/" if not stack else stack[-1].rstrip("/") + "/" + name
            if node in tree:
                raise ValueError(f"duplicate node {node}")
            tree[node] = {}
            stack.append(node)
        elif token == FDT_END_NODE:
            if not stack:
                raise ValueError("unmatched end node")
            stack.pop()
        elif token == FDT_PROP:
            if not stack or pos + 8 > end:
                raise ValueError("malformed property")
            length, name_offset = struct.unpack_from(">2I", data, pos)
            pos += 8
            name, _ = cstring(data, off_strings + name_offset,
                              off_strings + size_strings)
            if pos + length > end or name in tree[stack[-1]]:
                raise ValueError("invalid or duplicate property")
            tree[stack[-1]][name] = data[pos:pos + length]
            pos = align4(pos + length)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack or pos != end:
                raise ValueError("malformed FDT end")
            return tree, tuple(reservations), boot_cpu
        else:
            raise ValueError(f"unknown FDT token {token}")
    raise ValueError("missing FDT end")


def cells(*values: int) -> bytes:
    return struct.pack(">" + "I" * len(values), *values)


def string(value: str) -> bytes:
    return value.encode("ascii") + b"\0"


def expected_record(record: dict[str, object]) -> dict[str, bytes]:
    digests = record.get("digests")
    if not isinstance(digests, dict):
        raise ValueError("record digest map changed")
    result = {
        "compatible": string("planet,gemini-a72-runtime-binding-v1"),
        "schema-version": cells(1),
        "profile-id": string("mt6797-a53-a72-a41-v7"),
        "target-cpus": cells(8, 9),
        "target-mpidrs": struct.pack(">2Q", 0x200, 0x201),
    }
    for name in DIGESTS:
        value = digests.get(name)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"record digest changed: {name}")
        result[name] = bytes.fromhex(value)
    identity = record.get("record_identity")
    if not isinstance(identity, str) or len(identity) != 64:
        raise ValueError("record identity changed")
    result["record-identity"] = bytes.fromhex(identity)
    return result


def validate(serviceability: Path, package_dtb: Path, record_path: Path,
             candidate: Path, *, pin: bool = True) -> None:
    if sha256(serviceability) != SERVICEABILITY_SHA256:
        raise ValueError("serviceability DT identity changed")
    if sha256(package_dtb) != PACKAGE_DTB_SHA256:
        raise ValueError("package DT identity changed")
    if sha256(record_path) != RECORD_JSON_SHA256:
        raise ValueError("record JSON identity changed")
    if pin and sha256(candidate) != COMPOSED_SHA256:
        raise ValueError("composed DT identity changed")

    base, base_reservations, base_boot_cpu = parse_fdt(serviceability)
    package, _, _ = parse_fdt(package_dtb)
    actual, actual_reservations, actual_boot_cpu = parse_fdt(candidate)
    record = json.loads(record_path.read_text(encoding="ascii"))
    expected_leaf = expected_record(record)
    if NODE in base or any(path.startswith(NODE + "/") for path in base):
        raise ValueError("serviceability DT already contains provenance")
    if package.get(NODE) != expected_leaf:
        raise ValueError("package DT leaf does not match package record")
    if any(path.startswith(NODE + "/") for path in package):
        raise ValueError("package provenance leaf gained a child")

    expected = copy.deepcopy(base)
    expected[NODE] = expected_leaf
    if actual != expected:
        details: list[str] = []
        for node in sorted(set(expected) | set(actual)):
            if node not in expected:
                details.append(f"unexpected node {node}")
            elif node not in actual:
                details.append(f"missing node {node}")
            else:
                for prop in sorted(set(expected[node]) | set(actual[node])):
                    if expected[node].get(prop) != actual[node].get(prop):
                        details.append(f"changed property {node}:{prop}")
        raise ValueError("DT delta is not provenance-only: " + "; ".join(details[:16]))
    if actual_reservations != base_reservations or actual_boot_cpu != base_boot_cpu:
        raise ValueError("FDT reservation or boot-CPU metadata changed")

    status_okay = string("okay")
    for node in (
        "/usb@11271000", "/t-phy@11290000",
        "/t-phy@11290000/usb-phy@11290800", "/i2c@1101c000",
        "/i2c@1101c000/gpio-expander@5b", "/keyboard-matrix",
        "/dvfsp-clock-backend@1001a000", "/dvfsp-bigidvfs-backend",
    ):
        if actual.get(node, {}).get("status") != status_okay:
            raise ValueError(f"serviceability/admission node is not enabled: {node}")
    blob = candidate.read_bytes()
    if blob.count(b"mediatek,mt6797-a72-admission-controller") != 1:
        raise ValueError("admission controller count changed")
    if blob.count(b"mediatek,mt6797-a72-binder") != 1:
        raise ValueError("admission binder count changed")
    if b"mediatek,mt6797-a72-platform-provider-clock-observer" in blob:
        raise ValueError("standalone observer leaked into admission DT")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serviceability-dtb", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    validate(args.serviceability_dtb, args.package_dtb, args.record_json,
             args.candidate)
    print("validation=provenance-serviceability-composed-dtb-independent")
    print("dt_delta=one-exact-package-provenance-leaf")
    print("serviceability_nodes=preserved")
    print("controller_nodes=1")
    print("binder_nodes=1")
    print("cpu8_request_paths=unchanged")
    print("cpu9_requests=0")
    print("boot_candidate=pending-container-validation")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
