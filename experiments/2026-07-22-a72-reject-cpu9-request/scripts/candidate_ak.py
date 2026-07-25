#!/usr/bin/env python3
"""Shared, storage-inert identities for Candidate AK's CPU9 control."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import stat
import sys
from types import ModuleType
from typing import Any

sys.dont_write_bytecode = True

EXPERIMENT = "2026-07-22-a72-reject-cpu9-request"
CANDIDATE = "AK"
AJ_EXPERIMENT = "2026-07-22-a72-reject-cpu8-request"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-reject-gate-cpu9-request"
)
AJ_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-reject-gate-cpu8-request"
)
SERIES_REL = "patches/series-a72-reject-gate"
FRAGMENT_REL = "configs/gemini-a72-reject-cpu9-request.fragment"

AJ_IDENTITY_SHA256 = "77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1"
AJ_SCRIPT_HASHES = {
    "validate-profile.py": "90232be6d528bc8975d0c11364d86e5442342068111a1dc2f67ab6fc8ab459d2",
    "validate-package.py": "02c9129e069150396056887ae9a6a016f30d18d1a2cbae82d32f6b69b2cef0cc",
    "validate-package-pins.py": "a14e72f11609c533992f17785a1b93001b3f388ed264e62ff4e856a012c98b20",
    "validate-package-reproduction.py": "f2ddf81daf9b1a9fddf1ca2010567f1856dd71a8d16cda21adbcf6e437c30ff5",
    "validate-boot.py": "e7d6b4e0dd4cf433818962261773389c7521dbf1aaa87240764272bcafc9e3fb",
    "finalize-artifact.py": "193f77adc720d67d46192e09f5fba10372e7002958f09d0d4797f4e89e678c32",
    "validate-artifact-pins.py": "d690969935d7d4554f2603489939ad18ccf5e80f6decc7e08169d88e7756ed7b",
    "validate-artifact-reproduction.py": "622c5c728d0b35673bf1b83d316c106aa633eaba58ef1d8ed63f3b818a61a3d4",
    "derive-installer.py": "07ac69c75f412a4478bf54f4156fd4375c1f0c9e108cb8ef41ce00728d607a0f",
}

SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
SERIES_SHA256 = "b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00"
PATCHSET_SHA256 = "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd"
PATCH_0092_SHA256 = "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5"
FRAGMENT_SHA256 = "8eca91064cbaa7d1d3143bef61f1a74121247f7823001f24066487c918aa67ff"
CONFIG_INPUTS_SHA256 = "fc923b7dd2005648339d8e48f1b36299e7ecc104cffb091383861231e7330594"
AJ_CONFIG_SHA256 = "64f1c3d1b9a506aad5b0ee0549188abac2fbcff12e9e8aacbda015cf4ee7b8cb"
CONFIG_SHA256 = "e4e9ffe96810ad135469d42edaa14dc43ad7fb463b23bc3cd3008ca8ba789228"

FINAL_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AJ_RAW_SHA256 = "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
AJ_RAW_SIZE = "7380992"
AJ_ARTIFACT_MANIFEST_SHA256 = "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
AJ_PADDED_SHA256 = "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
AJ_ARTIFACT_DIR = "candidate-AJ-a72-reject-cpu8-a3c649b5"
AJ_BOOT_MEMBER = "gemini-a72-reject-cpu8-request.boot.img"

BOOT_MEMBER = "gemini-a72-reject-cpu9-request.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-a72-reject-cpu9-request.dtb"
INITRAMFS_MEMBER = "gemini-a72-reject-cpu9-request-initramfs.img"

# These identities were selected only after two independent package builds
# reproduced all substantive bytes and modes. Their timestamp-bearing package
# manifests are distinct and both exact identities are accepted.
IMAGE_SHA256 = "4bad3dd4df6dd9727cac0c97aa7cc3ed063759e48afcbb6afa5d3b0f0d791cf4"
IMAGE_SIZE = "13293576"
IMAGE_GZ_SHA256 = "a65e1fe5ca6a1d24fd96475df3eda0bda657633fb1ce8c09d267934db128601d"
IMAGE_GZ_SIZE = "5531103"
SYSTEM_MAP_SHA256 = "ecfacec1736649df6ded949c52d6252078c667416c5a6bbdc2444352fdf2a729"
PACKAGE_DTB_SHA256 = "510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8"
GATE_AUDIT_SHA256 = "6154f2c08f21cad5d1af69d143800c8f09f7766ab736a7be00231620c48c0371"
PACKAGE_MANIFEST_SHA256S = (
    "d2bf2b7c001a7d32e95d76414570fe1900d7c5466f1b41b8c098f35e96eee62f",
    "7c4cab7a17c51aaf0d4bd064b31e73785589cbf7bff2f970079460bde4fd3aa1",
)
# Two independent Android-v0 assemblies reproduced all 20 members and modes;
# each raw copy then reproduced the same 16 MiB identity through both sparse
# extension and explicit zero-overlay constructions.
RAW_SHA256 = "e8fd45b4c6b3626330d49c84b13f6c7147ab5d324422bff5901c35545f5b6d28"
RAW_SIZE = "7380992"
ARTIFACT_MANIFEST_SHA256 = "8910caa303b69555fb792d061b19dc0fdb9f25108e55212135e8d099be84c93b"
PADDED_SHA256 = "66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e"

AJ_FRAGMENTS = [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-reject-cpu8-request.fragment",
]
FRAGMENTS = [*AJ_FRAGMENTS, FRAGMENT_REL]

AJ_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=9 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"
)
CMDLINE = AJ_CMDLINE.replace("maxcpus=9", "maxcpus=10")
EXPECTED_FRAGMENT = (
    "# Candidate AK boot-time rejection request. Apply after Candidate AJ's exact\n"
    "# maxcpus=9 CPU8 rejection profile. The sole resolved configuration delta is\n"
    "# maxcpus=9 -> maxcpus=10, which requests logical CPU9 after CPU8 returns\n"
    "# -EAGAIN; both A72 CPUs must remain behind the fail-closed pre-PSCI gate.\n"
    f'CONFIG_CMDLINE="{CMDLINE}"\n'
).encode()

HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def aj_script(name: str) -> pathlib.Path:
    return repository_root() / "experiments" / AJ_EXPERIMENT / "scripts" / name


def load_module(path: pathlib.Path, expected: str, module_name: str, label: str) -> ModuleType:
    data = read_regular(path, label)
    if digest_bytes(data) != expected:
        raise ValueError(f"source-pinned {label} changed")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {label}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_aj_identity(module_name: str = "candidate_ak_aj_identity") -> ModuleType:
    return load_module(
        aj_script("candidate_aj.py"), AJ_IDENTITY_SHA256, module_name,
        "Candidate AJ identity module",
    )


def load_aj_module(name: str, module_name: str) -> ModuleType:
    # AJ helpers import their own identity module by this canonical name. Load
    # the exact source-pinned module first instead of relying on sys.path.
    existing = sys.modules.get("candidate_aj")
    if existing is None:
        load_aj_identity("candidate_aj")
    else:
        source_name = getattr(existing, "__file__", None)
        if not isinstance(source_name, str):
            raise ValueError("preloaded candidate_aj module lacks a source path")
        source = pathlib.Path(source_name).resolve(strict=True)
        expected = aj_script("candidate_aj.py").resolve(strict=True)
        if source != expected or digest_path(source) != AJ_IDENTITY_SHA256:
            raise ValueError("unexpected candidate_aj module is already loaded")
    return load_module(
        aj_script(name), AJ_SCRIPT_HASHES[name], module_name,
        f"Candidate AJ {name}",
    )


def derive_config(aj_config: bytes) -> bytes:
    if digest_bytes(aj_config) != AJ_CONFIG_SHA256:
        raise ValueError("baseline config is not exact Candidate AJ")
    old = f'CONFIG_CMDLINE="{AJ_CMDLINE}"'.encode()
    new = f'CONFIG_CMDLINE="{CMDLINE}"'.encode()
    if aj_config.count(old) != 1 or aj_config.count(b"maxcpus=9") != 1:
        raise ValueError("Candidate AJ config command line is not unique")
    result = aj_config.replace(old, new)
    if digest_bytes(result) != CONFIG_SHA256:
        raise ValueError("derived Candidate AK config identity changed")
    return result


def validate_kernel_policy(
    image: bytes,
    system_map_data: bytes,
    config_data: bytes,
    ai_validator: ModuleType | None = None,
) -> None:
    """Apply AJ's fail-closed kernel policy with only the CPU9 request added."""

    aj = load_aj_identity("candidate_ak_kernel_aj_identity")
    validator = ai_validator or aj.load_ai_module(
        "validate-package.py", "candidate_ak_ai_kernel_policy"
    )
    if digest_bytes(config_data) != CONFIG_SHA256:
        raise ValueError("resolved configuration is not exact Candidate AK")
    validator.config_map(config_data)
    lines = set(config_data.decode("utf-8").splitlines())
    old_cmdline = f'CONFIG_CMDLINE="{aj.AI_CMDLINE}"'
    new_cmdline = f'CONFIG_CMDLINE="{CMDLINE}"'
    required = (set(validator.REQUIRED_CONFIG) - {old_cmdline}) | {new_cmdline}
    missing = required - lines
    if missing:
        raise ValueError(f"required Candidate AK config line is absent: {sorted(missing)[0]}")
    if not {"CONFIG_IKCONFIG=y", "CONFIG_IKCONFIG_PROC=y"} <= lines:
        raise ValueError("Candidate AK config lacks the embedded IKCONFIG contract")
    forbidden = set(validator.FORBIDDEN_ENABLED_CONFIG) & lines
    if forbidden:
        raise ValueError(f"forbidden regulator/observer config is enabled: {sorted(forbidden)[0]}")
    if b"CONFIG_HOTPLUG_PARALLEL=y" in config_data:
        raise ValueError("parallel CPU hotplug invalidates serialized CPU8/CPU9 ordering")

    tokens = CMDLINE.split()
    if tokens.count("maxcpus=10") != 1:
        raise ValueError("exact Candidate AK maxcpus=10 policy changed")
    if any(
        token in {"maxcpus=1", "maxcpus=8", "maxcpus=9", "nosmp"}
        or token.startswith(("nr_cpus=", "isolcpus=", "irqaffinity=", "initcall_blacklist="))
        or token == "regulator_ignore_unused"
        for token in tokens
    ):
        raise ValueError("forced command line contains a conflicting CPU or observer policy")
    for marker in validator.REQUIRED_KERNEL_MARKERS:
        if marker not in image:
            raise ValueError(f"kernel lacks reject-gate marker: {marker!r}")
    for marker in validator.FORBIDDEN_KERNEL_MARKERS:
        if marker in image:
            raise ValueError(f"kernel contains forbidden 0088-0091 marker: {marker!r}")
    symbols = {
        line.rsplit(" ", 1)[-1]
        for line in system_map_data.decode("ascii").splitlines()
        if " " in line
    }
    missing_symbols = set(validator.REQUIRED_SYSTEM_MAP) - symbols
    if missing_symbols:
        raise ValueError(f"System.map lacks gate symbol: {sorted(missing_symbols)[0]}")
    for line in system_map_data.decode("ascii").splitlines():
        if any(fragment in line for fragment in validator.FORBIDDEN_SYSTEM_MAP_FRAGMENTS):
            raise ValueError(f"System.map contains forbidden regulator/observer symbol: {line}")


def config_inputs_digest(fragments: dict[str, bytes]) -> str:
    records = [f"profile={PROFILE}\n", "base=defconfig\n"]
    for relative in FRAGMENTS:
        records.append(f"{digest_bytes(fragments[relative])}  {relative}\n")
    return digest_bytes("".join(records).encode("ascii"))


def validate_manifest_profile(data: bytes, label: str) -> dict[str, Any]:
    aj = load_aj_identity("candidate_ak_manifest_aj_identity")
    aj.validate_manifest_profile(data, label)
    value = json.loads(data.decode("utf-8"))
    profiles = value.get("config", {}).get("profiles", {}) if isinstance(value, dict) else {}
    expected = {
        "base": "defconfig",
        "patch_series": SERIES_REL,
        "fragments": FRAGMENTS,
    }
    if profiles.get(PROFILE) != expected:
        raise ValueError(f"{label} lacks exact Candidate AK profile")
    return value


def require_package_pins() -> None:
    values = {
        "IMAGE_SHA256": IMAGE_SHA256, "IMAGE_SIZE": IMAGE_SIZE,
        "IMAGE_GZ_SHA256": IMAGE_GZ_SHA256, "IMAGE_GZ_SIZE": IMAGE_GZ_SIZE,
        "SYSTEM_MAP_SHA256": SYSTEM_MAP_SHA256,
        "PACKAGE_DTB_SHA256": PACKAGE_DTB_SHA256,
        "GATE_AUDIT_SHA256": GATE_AUDIT_SHA256,
    }
    unresolved = [name for name, value in values.items() if value.startswith("TO_PIN_")]
    unresolved += [
        f"PACKAGE_MANIFEST_SHA256S[{index}]"
        for index, value in enumerate(PACKAGE_MANIFEST_SHA256S)
        if value.startswith("TO_PIN_")
    ]
    if unresolved:
        raise ValueError("Candidate AK package identities remain unpinned: " + ",".join(unresolved))
    for name in ("IMAGE_SHA256", "IMAGE_GZ_SHA256", "SYSTEM_MAP_SHA256", "PACKAGE_DTB_SHA256", "GATE_AUDIT_SHA256"):
        if HEX256.fullmatch(values[name]) is None:
            raise ValueError(f"Candidate AK {name} is malformed")
    for name, limit in (("IMAGE_SIZE", 128 * 1024 * 1024), ("IMAGE_GZ_SIZE", 16 * 1024 * 1024)):
        if not values[name].isdecimal() or not 0 < int(values[name]) <= limit:
            raise ValueError(f"Candidate AK {name} is malformed")
    if len(PACKAGE_MANIFEST_SHA256S) != 2 or len(set(PACKAGE_MANIFEST_SHA256S)) != 2:
        raise ValueError("Candidate AK package manifest pins are not two distinct builds")
    if any(HEX256.fullmatch(value) is None for value in PACKAGE_MANIFEST_SHA256S):
        raise ValueError("Candidate AK package manifest SHA-256 is malformed")


def require_artifact_pins() -> None:
    require_package_pins()
    values = {
        "RAW_SHA256": RAW_SHA256, "RAW_SIZE": RAW_SIZE,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
    }
    unresolved = [name for name, value in values.items() if value.startswith("TO_PIN_")]
    if unresolved:
        raise ValueError("Candidate AK artifact identities remain unpinned: " + ",".join(unresolved))
    for name in ("RAW_SHA256", "ARTIFACT_MANIFEST_SHA256", "PADDED_SHA256"):
        if HEX256.fullmatch(values[name]) is None:
            raise ValueError(f"Candidate AK {name} is malformed")
    if not RAW_SIZE.isdecimal() or not 0 < int(RAW_SIZE) <= 16 * 1024 * 1024:
        raise ValueError("Candidate AK RAW_SIZE is malformed")
    if RAW_SHA256 == AJ_RAW_SHA256:
        raise ValueError("Candidate AK raw identity equals Candidate AJ")
    if ARTIFACT_MANIFEST_SHA256 == AJ_ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AK artifact manifest identity equals Candidate AJ")
    if PADDED_SHA256 == AJ_PADDED_SHA256:
        raise ValueError("Candidate AK padded identity equals Candidate AJ predecessor")


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)
