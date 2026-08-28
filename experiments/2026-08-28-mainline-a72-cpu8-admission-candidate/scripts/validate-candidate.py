#!/usr/bin/env python3
"""Independently validate the exact one-shot CPU8 admission candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
REPOSITORY_COMMIT = "c5b5cd6e450f9b7563a4a620629090344d5eb047"
PROFILE = "a72-admission-candidate"
RELEASE = "7.1.3-gemini-a72-admission"
PACKAGE_NAME = "linux-7.1.3-gemini-a72-admission-candidate-4d75b626-a9cff04e"
IMAGE_SHA256 = "beb68e4b9954d942e755f0e3809637b788d9c3fb7da9c19ad60ecdfa582f61d9"
IMAGE_GZIP_SHA256 = "54d26167e3e7d8159316b2c9958c9d3c8aec4086ab67419cd05ae874b28b622a"
DTB_SHA256 = "1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509"
CONFIG_SHA256 = "2ff19f0d10045763b41f615101cdf11d90952a79d56fd670a9a673aa8228225b"
SYSTEM_MAP_SHA256 = "6c30e196696660e758af7de1fb5f7b4d6a0b075a605ef9764ac93b6fd5cca499"
BUILD_JSON_SHA256 = "492a195b05a88ba3c12621fcf9702f24ad27534f487143ac97262b5e030f8fab"
PACKAGE_MANIFEST_SHA256 = "9b015dac33b84ff1de585de440c0f6e1b4f793bdb562e815e7b798f5f9181a98"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
RAW_SHA256 = "d52d3c4e857aede5442be66cbb88b3dc4cdee34f8c01dae008af9d1a5251d6d8"
PADDED_SHA256 = "fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0"
RAW_SIZE = 6_934_528
BOOT2_SIZE = 16_777_216
BOOT_NAME = "gemini-a72adm"
BOOT_CMDLINE = "bootopt=64S3,32N2,64N2"
BOOT_FILE = "gemini-mt6797-a72-admission.boot.img"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path: Path) -> None:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
            f"missing, empty, or unsafe input: {path}")


def parse_dtb(path: Path) -> dict[str, dict[str, bytes]]:
    """Parse enough flattened DT structure to validate exact node properties."""
    data = path.read_bytes()
    require(len(data) >= 40, "DTB header truncated")
    header = struct.unpack_from(">10I", data)
    magic, total, off_struct, off_strings = header[:4]
    size_strings, size_struct = header[8], header[9]
    require(magic == 0xD00DFEED and total == len(data), "DTB header identity")
    require(off_struct + size_struct <= total, "DTB structure bounds")
    require(off_strings + size_strings <= total, "DTB string bounds")
    strings = data[off_strings:off_strings + size_strings]
    pos = off_struct
    end = off_struct + size_struct
    stack: list[str] = []
    nodes: dict[str, dict[str, bytes]] = {}

    def align(value: int) -> int:
        return (value + 3) & ~3

    def cstring(blob: bytes, offset: int) -> tuple[str, int]:
        stop = blob.find(b"\0", offset)
        require(stop >= 0, "unterminated DT string")
        return blob[offset:stop].decode("ascii"), stop + 1

    while pos < end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == 1:  # FDT_BEGIN_NODE
            name, pos = cstring(data, pos)
            pos = align(pos)
            stack.append(name)
            node_path = "/" + "/".join(part for part in stack if part)
            nodes[node_path or "/"] = {}
        elif token == 2:  # FDT_END_NODE
            require(bool(stack), "unbalanced DT node end")
            stack.pop()
        elif token == 3:  # FDT_PROP
            length, name_offset = struct.unpack_from(">II", data, pos)
            pos += 8
            require(pos + length <= end and name_offset < len(strings),
                    "DT property bounds")
            prop_name, _ = cstring(strings, name_offset)
            value = data[pos:pos + length]
            pos = align(pos + length)
            node_path = "/" + "/".join(part for part in stack if part)
            nodes[node_path or "/"][prop_name] = value
        elif token == 4:  # FDT_NOP
            continue
        elif token == 9:  # FDT_END
            require(not stack, "unbalanced DT final stack")
            return nodes
        else:
            raise AssertionError(f"unknown DT token: {token}")
    raise AssertionError("missing DT end token")


def dt_string(nodes: dict[str, dict[str, bytes]], node: str, prop: str) -> str:
    value = nodes[node][prop]
    require(value.endswith(b"\0"), f"DT string termination: {node}:{prop}")
    return value[:-1].decode("ascii")


def dt_u32(nodes: dict[str, dict[str, bytes]], node: str, prop: str) -> int:
    value = nodes[node][prop]
    require(len(value) == 4, f"DT u32 size: {node}:{prop}")
    return struct.unpack(">I", value)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    package = args.package.resolve()
    ramdisk = args.ramdisk.resolve()
    require(artifact.name == f"candidate-a72-admission-{RAW_SHA256[:8]}",
            "artifact directory identity changed")
    require(package.name == PACKAGE_NAME, "package directory identity changed")

    image = package / "Image"
    image_gz = package / "Image.gz"
    config = package / "kernel.config"
    system_map = package / "System.map"
    dtb = package / "dtbs/mediatek/mt6797-gemini-pda-a72-admission.dtb"
    build_json = package / "provenance/build.json"
    package_manifest = package / "SHA256SUMS"
    analyzer = ROOT / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    raw = artifact / BOOT_FILE
    padded = artifact / "boot2-padded.img"
    artifact_manifest = artifact / "SHA256SUMS"
    provenance = artifact / "provenance.txt"
    container_analysis = artifact / "container-analysis.txt"
    for path in (image, image_gz, config, system_map, dtb, build_json,
                 package_manifest, ramdisk, analyzer, raw, padded,
                 artifact_manifest, provenance, container_analysis):
        regular(path)

    expected_hashes = {
        image: IMAGE_SHA256,
        image_gz: IMAGE_GZIP_SHA256,
        config: CONFIG_SHA256,
        system_map: SYSTEM_MAP_SHA256,
        dtb: DTB_SHA256,
        build_json: BUILD_JSON_SHA256,
        package_manifest: PACKAGE_MANIFEST_SHA256,
        ramdisk: RAMDISK_SHA256,
        analyzer: ANALYZER_SHA256,
        raw: RAW_SHA256,
        padded: PADDED_SHA256,
    }
    for path, expected in expected_hashes.items():
        require(sha256(path) == expected, f"identity changed: {path.name}")
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"],
                   cwd=package, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"],
                   cwd=artifact, check=True, stdout=subprocess.DEVNULL)

    build = json.loads(build_json.read_text(encoding="utf-8"))
    require(build["repository_commit"] == REPOSITORY_COMMIT,
            "package repository commit changed")
    require(build["repository_dirty"] is False, "package source was dirty")
    require(build["build_profile"] == PROFILE, "package profile changed")
    require(build["kernel_release"] == RELEASE, "kernel release changed")
    require(build["config_sha256"] == CONFIG_SHA256,
            "build-record configuration identity changed")

    config_text = config.read_text(encoding="utf-8")
    for line in (
        "CONFIG_MODULES=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
        "CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION=y",
        "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y",
        "CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y",
        "CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y",
        "CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS=y",
        "CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y",
        "CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y",
        "CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER=y",
        "CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR=y",
        "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",
        "CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-admission"',
    ):
        require(config_text.count(line + "\n") == 1,
                f"configuration gate changed: {line}")
    require("CONFIG_HOTPLUG_SPLIT_STARTUP=y\n" not in config_text,
            "split-startup experiment is enabled")
    for symbol in (
        "PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER",
        "PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER",
        "PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER",
    ):
        require(f"CONFIG_{symbol}=y\n" not in config_text,
                f"conflicting retained ledger enabled: {symbol}")
    command_line = re.search(r'^CONFIG_CMDLINE="(.*)"$', config_text, re.MULTILINE)
    require(command_line is not None and command_line.group(1).split().count("maxcpus=8") == 1,
            "exact maxcpus=8 closure")

    symbols = system_map.read_text(encoding="utf-8")
    for symbol in (
        "mt6797_a72_admission_run",
        "mt6797_a72_binder_available",
        "mt6797_a72_binder_cpu_boot",
        "mt6797_a72_physical_source_capture",
        "mt6797_a72_source_register",
        "mt6797_a72_membership_derive_cpu8",
        "mt6797_a72_membership_publish_up",
        "gemini_transition_ledger_checkpoint",
        "mt6797_a72_transition_run",
        "add_cpu",
    ):
        require(len(re.findall(rf" [A-Za-z] {re.escape(symbol)}$", symbols,
                               re.MULTILINE)) == 1,
                f"required symbol absent or duplicated: {symbol}")
    require(re.search(r"mt6797_a72_.*_test", symbols) is None,
            "KUnit-only symbol linked")

    marker = (b"GEMINI_A72_ADMISSION_V1 state=terminal ret=%d consumed=1 "
              b"requests=%u/0/0 retries=0")
    require(image.read_bytes().count(marker) == 1, "Image admission marker changed")

    nodes = parse_dtb(dtb)
    compatible_nodes = {
        node for node, props in nodes.items()
        if props.get("compatible", b"").split(b"\0", 1)[0] ==
        b"mediatek,mt6797-a72-admission-controller"
    }
    require(compatible_nodes == {"/a72-admission-controller"},
            "exactly one admission controller")
    binder_nodes = {
        node for node, props in nodes.items()
        if props.get("compatible", b"").split(b"\0", 1)[0] ==
        b"mediatek,mt6797-a72-binder"
    }
    require(binder_nodes == {"/a72-binder"}, "exactly one transition binder")
    require(all(b"mediatek,mt6797-a72-physical-source-observer" not in
                props.get("compatible", b"") for props in nodes.values()),
            "standalone physical-source observer absent")
    for node in (
        "/a72-admission-controller", "/a72-binder",
        "/a72-platform-state@10222000", "/dvfsp-clock-backend@1001a000",
        "/dvfsp-bigidvfs-backend",
    ):
        require(dt_string(nodes, node, "status") == "okay", f"{node} enabled")
    require(dt_string(nodes, "/dvfsp-resource-owner", "status") == "disabled",
            "unrelated DVFSP owner disabled")
    require(dt_string(nodes, "/dvfsp-bigidvfs-backend", "method") == "smc",
            "BigiDVFS SMC method")
    controller = "/a72-admission-controller"
    binder = "/a72-binder"
    platform = "/a72-platform-state@10222000"
    clock = "/dvfsp-clock-backend@1001a000"
    bigidvfs = "/dvfsp-bigidvfs-backend"
    require(dt_u32(nodes, controller, "mediatek,binder") ==
            dt_u32(nodes, binder, "phandle"), "controller binder phandle")
    require(dt_u32(nodes, controller, "mediatek,platform-state") ==
            dt_u32(nodes, platform, "phandle"), "controller platform phandle")
    require(dt_u32(nodes, controller, "mediatek,clock-backend") ==
            dt_u32(nodes, clock, "phandle"), "controller clock phandle")
    require(dt_u32(nodes, controller, "mediatek,bigidvfs-backend") ==
            dt_u32(nodes, bigidvfs, "phandle"), "controller BigiDVFS phandle")
    require(dt_u32(nodes, binder, "mediatek,platform-state") ==
            dt_u32(nodes, platform, "phandle"), "binder platform phandle")
    require(dt_u32(nodes, binder, "mediatek,bigidvfs") ==
            dt_u32(nodes, bigidvfs, "phandle"), "binder BigiDVFS phandle")
    for cpu, reg in (("/cpus/cpu@200", 0x200), ("/cpus/cpu@201", 0x201)):
        require(dt_string(nodes, cpu, "compatible") == "arm,cortex-a72",
                f"{cpu} identity")
        require(dt_string(nodes, cpu, "enable-method") == "mediatek,mt6797-psci",
                f"{cpu} enable method")
        require(dt_u32(nodes, cpu, "reg") == reg, f"{cpu} MPIDR")

    require(raw.stat().st_size == RAW_SIZE, "raw candidate size changed")
    require(padded.stat().st_size == BOOT2_SIZE, "padded candidate size changed")
    raw_bytes = raw.read_bytes()
    padded_bytes = padded.read_bytes()
    require(padded_bytes[:RAW_SIZE] == raw_bytes, "padded prefix differs from raw candidate")
    require(not any(padded_bytes[RAW_SIZE:]), "padded tail is not all zero")
    analysis = subprocess.run(
        ["python3", str(analyzer), "--validate-lk",
         "--expected-image-gz", str(image_gz),
         "--expected-ramdisk", str(ramdisk), "--expected-dtb", str(dtb),
         "--expected-name", BOOT_NAME, "--expected-cmdline", BOOT_CMDLINE,
         str(raw)],
        check=True, capture_output=True, text=True,
    ).stdout
    require(len(re.findall(r"^gate_.*=yes$", analysis, re.MULTILINE)) == 32,
            "independent analyzer did not pass 32 gates")
    require("lk_validation=passed\n" in analysis and
            "lk_validation_failures=none\n" in analysis,
            "independent LK validation failed")
    require("boot_candidate=pending-independent-validation\n" in
            provenance.read_text(encoding="utf-8"),
            "builder provenance state changed")
    require(container_analysis.read_text(encoding="utf-8").count(
            "lk_validation=passed\n") == 1,
            "builder container analysis changed")

    print("validation=a72-admission-candidate-independent")
    print(f"repository_commit={REPOSITORY_COMMIT}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={RELEASE}")
    print(f"candidate_sha256={RAW_SHA256}")
    print(f"candidate_size={RAW_SIZE}")
    print(f"padded_sha256={PADDED_SHA256}")
    print(f"padded_size={BOOT2_SIZE}")
    print("lk_gates=32-of-32")
    print("controller_nodes=1")
    print("binder_nodes=1")
    print("standalone_observer_nodes=0")
    print("cpu8_requests=1")
    print("cpu9_requests=0")
    print("retry_paths=0")
    print("cpu_off_paths=0")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
