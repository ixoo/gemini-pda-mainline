#!/usr/bin/env python3
"""Build the exact topology, thermal, and package-provenance production DT."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import NoReturn


TOPOLOGY_SHA256 = "4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923"
THERMAL_SOURCE_SHA256 = "2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a"
THERMAL_OVERLAY_SHA256 = "f2d4cec4b2dec6593a148c9bcb46cc989b825d4ea12aa46c06be0d8da11dd748"
TOPOLOGY_THERMAL_SHA256 = "fe24e244b74fe9b504727a6d19d590b1e03a28fc7e461d4d033d9be718757569"
PACKAGE_DTB_SHA256 = "df70033883ae3dc7bee7d3af42e7d1677573c153c24fc295b9b79d919f8722a3"
RECORD_JSON_SHA256 = "1cb788595e9af5aa977882308c82938b5d1c1848ae323f4b840172d0994598db"
OUTPUT_SHA256 = "46be0ae62bf66bf8e9f905ec3ad5eebbdc51c79ff3dc21859077ebe3f1aec363"
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


def run(arguments: list[str]) -> str:
    try:
        result = subprocess.run(arguments, check=True, capture_output=True)
    except FileNotFoundError:
        fail(f"required tool is unavailable: {arguments[0]}")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip()
        fail(f"command failed ({error.returncode}): {' '.join(arguments)}: {detail}")
    return result.stdout.decode("ascii").strip()


def fdtget(dtb: Path, option: str, node: str,
           property_name: str | None = None) -> str:
    arguments = ["fdtget", option, str(dtb), node]
    if property_name is not None:
        arguments.append(property_name)
    return run(arguments)


def package_bytes(dtb: Path, name: str) -> str:
    values = fdtget(dtb, "-tbx", NODE, name).split()
    if len(values) != 32:
        fail(f"package DT property is not 32 bytes: {name}")
    try:
        return bytes(int(value, 16) for value in values).hex()
    except ValueError:
        fail(f"package DT property is not hexadecimal: {name}")


def dts_bytes(value: str) -> str:
    try:
        decoded = bytes.fromhex(value)
    except ValueError:
        fail("record contains a non-hexadecimal digest")
    if len(decoded) != 32 or not any(decoded) or decoded.hex() != value:
        fail("record contains an invalid digest")
    return "[" + " ".join(f"{byte:02x}" for byte in decoded) + "]"


def validate_record(package_dtb: Path, record_path: Path) -> dict[str, object]:
    children = fdtget(package_dtb, "-l", "/chosen").splitlines()
    if children.count(NODE_NAME) != 1 or fdtget(package_dtb, "-l", NODE):
        fail("package DT provenance leaf shape changed")
    if set(fdtget(package_dtb, "-p", NODE).splitlines()) != PROPERTIES:
        fail("package DT provenance property set changed")
    record = json.loads(record_path.read_text(encoding="ascii"))
    if (record.get("schema") != 1 or record.get("compatible") != COMPATIBLE or
            record.get("profile_id") != PROFILE or
            record.get("target_cpus") != [8, 9] or
            record.get("target_mpidrs") != [512, 513]):
        fail("package A41 record topology or schema changed")
    digests = record.get("digests")
    if not isinstance(digests, dict) or set(digests) != set(DIGESTS):
        fail("package A41 digest set changed")
    identity = record.get("record_identity")
    if not isinstance(identity, str):
        fail("package A41 record identity is missing")
    if fdtget(package_dtb, "-ts", NODE, "compatible") != COMPATIBLE:
        fail("package DT compatible does not match record")
    if fdtget(package_dtb, "-tu", NODE, "schema-version") != "1":
        fail("package DT schema does not match record")
    if fdtget(package_dtb, "-ts", NODE, "profile-id") != PROFILE:
        fail("package DT profile does not match record")
    if fdtget(package_dtb, "-tu", NODE, "target-cpus") != "8 9":
        fail("package DT target CPUs do not match record")
    if fdtget(package_dtb, "-tbx", NODE, "target-mpidrs") != (
            "0 0 0 0 0 0 2 0 0 0 0 0 0 0 2 1"):
        fail("package DT target MPIDRs do not match record")
    for name in DIGESTS:
        value = digests.get(name)
        if not isinstance(value, str) or package_bytes(package_dtb, name) != value:
            fail(f"package DT digest does not match record: {name}")
    if package_bytes(package_dtb, "record-identity") != identity:
        fail("package DT record identity does not match record")
    return record


def write_provenance_overlay(path: Path, record: dict[str, object]) -> None:
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
    identity = record["record_identity"]
    assert isinstance(identity, str)
    lines.extend([
        f"\t\t\t\trecord-identity = {dts_bytes(identity)};",
        "\t\t\t};", "\t\t};", "\t};", "};", "",
    ])
    path.write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology-dtb", type=Path, required=True)
    parser.add_argument("--thermal-overlay", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = (
        (args.topology_dtb, TOPOLOGY_SHA256, "topology DT"),
        (args.thermal_overlay, THERMAL_SOURCE_SHA256, "thermal overlay source"),
        (args.package_dtb, PACKAGE_DTB_SHA256, "package DT"),
        (args.record_json, RECORD_JSON_SHA256, "package A41 record"),
    )
    for path, expected, label in inputs:
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            fail(f"{label} identity changed")
    if args.output.exists() or args.output.is_symlink():
        fail("refusing to overwrite output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record = validate_record(args.package_dtb, args.record_json)
    with tempfile.TemporaryDirectory(
            prefix=".a72-frequency-production-dt.",
            dir=str(args.output.parent)) as directory:
        root = Path(directory)
        thermal_dtbo = root / "thermal-serviceability.dtbo"
        topology_thermal = root / "topology-thermal-serviceability.dtb"
        provenance_source = root / "package-provenance.dtso"
        provenance_dtbo = root / "package-provenance.dtbo"
        result = root / "topology-thermal-frequency.dtb"
        run([
            "dtc", "-Wno-resets_property", "-Wno-thermal_sensors_property",
            "-I", "dts", "-O", "dtb", "-o", str(thermal_dtbo),
            str(args.thermal_overlay),
        ])
        if sha256(thermal_dtbo) != THERMAL_OVERLAY_SHA256:
            fail("compiled thermal overlay identity changed")
        run([
            "fdtoverlay", "-i", str(args.topology_dtb), "-o",
            str(topology_thermal), str(thermal_dtbo),
        ])
        if sha256(topology_thermal) != TOPOLOGY_THERMAL_SHA256:
            fail("topology/thermal transform identity changed")
        write_provenance_overlay(provenance_source, record)
        run([
            "dtc", "-q", "-@", "-I", "dts", "-O", "dtb", "-o",
            str(provenance_dtbo), str(provenance_source),
        ])
        run([
            "fdtoverlay", "-i", str(topology_thermal), "-o", str(result),
            str(provenance_dtbo),
        ])
        run([
            "dtc", "-q", "-I", "dtb", "-O", "dtb", "-o", "/dev/null",
            str(result),
        ])
        actual = sha256(result)
        if actual != OUTPUT_SHA256:
            fail(f"production DT identity changed: {actual}")
        os.replace(result, args.output)
    os.chmod(args.output, 0o600)
    print("validation=mt6797-a72-frequency-thermal-production-dtb")
    print(f"topology_dtb_sha256={TOPOLOGY_SHA256}")
    print(f"thermal_overlay_sha256={THERMAL_SOURCE_SHA256}")
    print(f"topology_thermal_dtb_sha256={TOPOLOGY_THERMAL_SHA256}")
    print(f"package_dtb_sha256={PACKAGE_DTB_SHA256}")
    print(f"package_a41_record_sha256={RECORD_JSON_SHA256}")
    print(f"output_dtb_sha256={sha256(args.output)}")
    print(f"a41_record_identity={record['record_identity']}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
