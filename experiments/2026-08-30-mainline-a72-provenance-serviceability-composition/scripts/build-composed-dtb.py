#!/usr/bin/env python3
"""Add the exact package-owned A41 provenance leaf to the serviceability DT."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import NoReturn


SERVICEABILITY_SHA256 = "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c"
PACKAGE_DTB_SHA256 = "d3197c6870aa025840f6dc330e83e7871e78cce56e4b314e03085d7879c6954f"
RECORD_JSON_SHA256 = "05a3e54a412e02bc224138056552451b706111d2d98d6e1363597efeecada93d"
OUTPUT_SHA256 = "8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2"
NODE = "/chosen/gemini-late-cpu-provenance"
NODE_NAME = "gemini-late-cpu-provenance"
COMPATIBLE = "planet,gemini-a72-runtime-binding-v1"
PROFILE = "mt6797-a53-a72-a41-v7"
DIGESTS = (
    "expected-ikconfig-identity",
    "expected-gnu-build-id-identity",
    "expected-cmdline-identity",
    "upstream-source-sha256",
    "patch-series-sha256",
    "config-inputs-sha256",
    "resolved-config-sha256",
    "package-image-sha256",
    "build-provenance-sha256",
)
PROPERTIES = {
    "compatible", "schema-version", "profile-id", "target-cpus",
    "target-mpidrs", "record-identity", *DIGESTS,
}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, check=True, capture_output=True)
    except FileNotFoundError:
        fail(f"required tool is unavailable: {args[0]}")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip()
        fail(f"command failed ({error.returncode}): {' '.join(args)}: {detail}")
    return result.stdout.decode("ascii").strip()


def fdtget(dtb: Path, option: str, node: str, property_name: str | None = None) -> str:
    args = ["fdtget", option, str(dtb), node]
    if property_name is not None:
        args.append(property_name)
    return run(args)


def bytes_property(dtb: Path, name: str) -> str:
    raw = fdtget(dtb, "-tbx", NODE, name)
    values = raw.split()
    if len(values) != 32:
        fail(f"package DT property {name} is not 32 bytes")
    try:
        return bytes(int(value, 16) for value in values).hex()
    except ValueError:
        fail(f"package DT property {name} is not hexadecimal")


def dts_bytes(value: str) -> str:
    if len(value) != 64 or bytes.fromhex(value).hex() != value or not any(bytes.fromhex(value)):
        fail("record contains an invalid digest")
    return "[" + " ".join(value[index:index + 2] for index in range(0, 64, 2)) + "]"


def validate_inputs(serviceability: Path, package_dtb: Path,
                    record_path: Path) -> dict[str, object]:
    if sha256(serviceability) != SERVICEABILITY_SHA256:
        fail("serviceability DT identity changed")
    if sha256(package_dtb) != PACKAGE_DTB_SHA256:
        fail("package DT identity changed")
    if sha256(record_path) != RECORD_JSON_SHA256:
        fail("package A41 record identity changed")

    service_children = set(fdtget(serviceability, "-l", "/chosen").splitlines())
    if NODE_NAME in service_children:
        fail("serviceability DT already contains the provenance leaf")
    package_children = fdtget(package_dtb, "-l", "/chosen").splitlines()
    if package_children.count(NODE_NAME) != 1:
        fail("package DT does not contain exactly one provenance leaf")
    if fdtget(package_dtb, "-l", NODE):
        fail("package provenance leaf gained a child")
    properties = set(fdtget(package_dtb, "-p", NODE).splitlines())
    if properties != PROPERTIES:
        fail("package provenance property set changed")

    record = json.loads(record_path.read_text(encoding="ascii"))
    if (record.get("schema") != 1 or record.get("compatible") != COMPATIBLE or
            record.get("profile_id") != PROFILE or
            record.get("target_cpus") != [8, 9] or
            record.get("target_mpidrs") != [512, 513]):
        fail("package A41 record topology or schema changed")
    digests = record.get("digests")
    if not isinstance(digests, dict) or set(digests) != set(DIGESTS):
        fail("package A41 digest set changed")
    record_identity = record.get("record_identity")
    if not isinstance(record_identity, str):
        fail("package A41 record identity is missing")

    if fdtget(package_dtb, "-ts", NODE, "compatible") != COMPATIBLE:
        fail("package DT compatible does not match the A41 record")
    if fdtget(package_dtb, "-tu", NODE, "schema-version") != "1":
        fail("package DT schema does not match the A41 record")
    if fdtget(package_dtb, "-ts", NODE, "profile-id") != PROFILE:
        fail("package DT profile does not match the A41 record")
    if fdtget(package_dtb, "-tu", NODE, "target-cpus") != "8 9":
        fail("package DT target CPUs do not match the A41 record")
    if fdtget(package_dtb, "-tbx", NODE, "target-mpidrs") != (
            "0 0 0 0 0 0 2 0 0 0 0 0 0 0 2 1"):
        fail("package DT target MPIDRs do not match the A41 record")
    for name in DIGESTS:
        value = digests.get(name)
        if not isinstance(value, str) or bytes_property(package_dtb, name) != value:
            fail(f"package DT digest does not match record: {name}")
    if bytes_property(package_dtb, "record-identity") != record_identity:
        fail("package DT record identity does not match record JSON")
    return record


def write_overlay(path: Path, record: dict[str, object]) -> None:
    digests = record["digests"]
    assert isinstance(digests, dict)
    lines = [
        "/dts-v1/;", "/plugin/;", "", "/ {", "\tfragment@0 {",
        "\t\ttarget-path = \"/chosen\";", "\t\t__overlay__ {",
        f"\t\t\t{NODE_NAME} {{",
        f"\t\t\t\tcompatible = \"{COMPATIBLE}\";",
        "\t\t\t\tschema-version = <1>;",
        f"\t\t\t\tprofile-id = \"{PROFILE}\";",
        "\t\t\t\ttarget-cpus = <8 9>;",
        "\t\t\t\ttarget-mpidrs = /bits/ 64 <0x200 0x201>;",
    ]
    for name in DIGESTS:
        value = digests[name]
        assert isinstance(value, str)
        lines.append(f"\t\t\t\t{name} = {dts_bytes(value)};")
    record_identity = record["record_identity"]
    assert isinstance(record_identity, str)
    lines.extend([
        f"\t\t\t\trecord-identity = {dts_bytes(record_identity)};",
        "\t\t\t};", "\t\t};", "\t};", "};", "",
    ])
    path.write_text("\n".join(lines), encoding="ascii")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serviceability-dtb", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.serviceability_dtb, args.package_dtb, args.record_json):
        if not path.is_file() or path.is_symlink():
            fail(f"required input is missing or unsafe: {path}")
    if args.output.exists() or args.output.is_symlink():
        fail("refusing to overwrite output")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    record = validate_inputs(args.serviceability_dtb, args.package_dtb,
                             args.record_json)
    with tempfile.TemporaryDirectory(
            prefix=".a72-provenance-serviceability.",
            dir=str(args.output.parent)) as directory:
        root = Path(directory)
        source = root / "provenance-overlay.dts"
        overlay = root / "provenance-overlay.dtb"
        result = root / "composed.dtb"
        write_overlay(source, record)
        run(["dtc", "-q", "-@", "-I", "dts", "-O", "dtb", "-o",
             str(overlay), str(source)])
        run(["fdtoverlay", "-i", str(args.serviceability_dtb), "-o",
             str(result), str(overlay)])
        run(["dtc", "-q", "-I", "dtb", "-O", "dtb", "-o", "/dev/null",
             str(result)])
        if sha256(result) != OUTPUT_SHA256:
            fail(f"composed DT identity changed: {sha256(result)}")
        os.replace(result, args.output)
    os.chmod(args.output, 0o600)

    print("validation=provenance-serviceability-composed-dtb")
    print(f"serviceability_dtb_sha256={SERVICEABILITY_SHA256}")
    print(f"package_dtb_sha256={PACKAGE_DTB_SHA256}")
    print(f"package_a41_record_sha256={RECORD_JSON_SHA256}")
    print(f"output_dtb_sha256={OUTPUT_SHA256}")
    print(f"a41_record_identity={record['record_identity']}")
    print("serviceability_transform=unchanged")
    print("a41_provenance_leaf=package-exact")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
