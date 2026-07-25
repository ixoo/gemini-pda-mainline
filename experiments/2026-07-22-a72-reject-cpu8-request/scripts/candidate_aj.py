#!/usr/bin/env python3
"""Shared, storage-inert Candidate AJ identities and exact transforms."""

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

EXPERIMENT = "2026-07-22-a72-reject-cpu8-request"
CANDIDATE = "AJ"
AI_EXPERIMENT = "2026-07-22-a72-reject-gate-kernel-split"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-reject-gate-cpu8-request"
)
AI_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-reject-gate"
)
SERIES_REL = "patches/series-a72-reject-gate"
FRAGMENT_REL = "configs/gemini-a72-reject-cpu8-request.fragment"
AI_FRAGMENTS = [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
]
FRAGMENTS = [*AI_FRAGMENTS, FRAGMENT_REL]

SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
SERIES_SHA256 = "b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00"
PATCHSET_SHA256 = "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd"
PATCH_0092_SHA256 = "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5"
FRAGMENT_SHA256 = "fbbc03dec4021f2e23e51e2aaad5f7bc8942d011470db90552a10d4467631ba3"
CONFIG_INPUTS_SHA256 = "9fa44c817649a81a633b0c2443e2d7bf73008af613431577b1cddc525121f409"
AI_CONFIG_SHA256 = "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46"
CONFIG_SHA256 = "64f1c3d1b9a506aad5b0ee0549188abac2fbcff12e9e8aacbda015cf4ee7b8cb"
AI_IMAGE_SHA256 = "fb2c02601a07b49781b97ef9d39b79218db1c158ce1547a2ea53df7fb1e51fe2"
AI_SYSTEM_MAP_SHA256 = "622945b38e025db7ee7719f2fa3132e17f8ad0158651e2f77e57918a76ac384d"
AI_PACKAGE_DTB_SHA256 = "510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8"
FINAL_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AI_GATE_AUDIT_SHA256 = "67519ff0a82376e2d0628f7061af474b0df6427c0f54878717a6c6b1d672a525"

AI_PACKAGE_MANIFEST_SHA256S = {
    "97b9741a4c99ae2f83e19eb2b47640dacb702b73de5fa4dfcfa85404c3685df6",
    "44eb5f57395ce7282fbf4dc98af19a507840954438a384369f8edc5d308a3bc5",
}
AI_ARTIFACT_MANIFEST_SHA256 = "b8c2953dd07e2a84a05e99f7bd0a981cbe593e928ba7507f16691279d82fa8cc"
AI_RAW_SHA256 = "1ecfc787fec2f5dc11c5b7d30eb4f11d34b0496e57daf42adea567f010282309"
AI_RAW_SIZE = 7_380_992
AI_PADDED_SHA256 = "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
AI_INSTALLER_SHA256 = "8d9d0ac258fdb031e840b2042c7abc1fc1fdf01cf6c6893bc24c234b6d9054f6"
AI_ARTIFACT_DIR = "candidate-AI-a72-reject-gate-1ecfc787"
AI_BOOT_MEMBER = "gemini-a72-reject-gate-kernel-split.boot.img"
BOOT_MEMBER = "gemini-a72-reject-cpu8-request.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-a72-reject-cpu8-request.dtb"
INITRAMFS_MEMBER = "gemini-a72-reject-cpu8-request-initramfs.img"

# CONFIG_IKCONFIG embeds a compressed copy of the changed .config in Image.
# These identities were therefore selected only after two independent VM
# packages reproduced every substantive output. The timestamp-bearing package
# manifests remain distinct and both exact identities are accepted.
IMAGE_SHA256 = "3312c868aaafd0dd383b0d99ffc2f815fb124ff731dc11b92f1322f1f320405a"
IMAGE_SIZE = "13293576"
IMAGE_GZ_SHA256 = "6014c00b3ed32c529f3ab66e8fe39f2c86b6bda3bfef5e0c603d6fb505a6de93"
IMAGE_GZ_SIZE = "5531650"
SYSTEM_MAP_SHA256 = "b8408b1c07924f5ffaa7cf8173d887f4a97f89b38e9d01bd31398d7c9c713b2e"
PACKAGE_DTB_SHA256 = "510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8"
GATE_AUDIT_SHA256 = "2ee5ebc7ed4f4784a957d537009d60e82b2e2254d5be33b8744b429aa1f32785"
PACKAGE_MANIFEST_SHA256S = (
    "dae3846f367e9465b1996dfc894879dad754bd0a26fffe13b5f45df5a0df8d9e",
    "1cfe77e54d0151dd104099c50363d9d83307f33632a50b7706d940407cf84906",
)

# Two independent artifact assemblies reproduced these raw and manifest
# identities, and two independent 16 MiB padding checks reproduced the exact
# full-partition identity. Hardware-facing entry points still call
# require_artifact_pins() before any path or evidence processing.
RAW_SHA256 = "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
RAW_SIZE = "7380992"
ARTIFACT_MANIFEST_SHA256 = "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
PADDED_SHA256 = "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"

AI_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"
)
CMDLINE = AI_CMDLINE.replace("maxcpus=8", "maxcpus=9")
EXPECTED_FRAGMENT = (
    "# Candidate AJ boot-time rejection request. Apply after Candidate AI's exact\n"
    "# maxcpus=8 gate-only profile. The sole resolved configuration delta is\n"
    "# maxcpus=8 -> maxcpus=9, which requests logical CPU8 once during serialized\n"
    "# bring-up; the fail-closed method must reject before PSCI CPU_ON, and CPU9\n"
    "# must remain unrequested.\n"
    f'CONFIG_CMDLINE="{CMDLINE}"\n'
).encode()

AI_SCRIPT_HASHES = {
    "validate-series-selection.py": "35ac2e525907745259d85c96f1e51b60e7fa00b0d92d7f9eeb70e465b4044346",
    "validate-package.py": "8c2f105e5cdc89ef4be747a895aeaa78619eafdf0113903a6ec9b3bfae194eda",
    "audit-mt6797-psci-cpu-boot.py": "90aa983f66261e18f192b14a535ccf9520b6e9079d45a8ce9234e30de8e90bde",
    "validate-lineage.py": "7f87eca5d6e89e02f5cb711bfbbf0fe64356775c5fe7735c723ee87e703adb19",
    "validate-boot.py": "4dff83a54875ed96bfd69dd0f67d22e5560c6761970f95f028e255ba3c1200da",
    "finalize-artifact.py": "ffb36348561972aefc0b25fa195d4defe12aa427b190d9f011ad18f0affef718",
    "derive-installer.py": "7f9a912f1a9cc05372ad95b5fb6a9dcc8253eda85635358572556362a504e99e",
}
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


def ai_script(name: str) -> pathlib.Path:
    return repository_root() / "experiments" / AI_EXPERIMENT / "scripts" / name


def load_ai_module(name: str, module_name: str) -> ModuleType:
    path = ai_script(name)
    data = read_regular(path, f"Candidate AI {name}")
    if digest_bytes(data) != AI_SCRIPT_HASHES[name]:
        raise ValueError(f"source-pinned Candidate AI script changed: {name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Candidate AI script: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def derive_config(ai_config: bytes) -> bytes:
    if digest_bytes(ai_config) != AI_CONFIG_SHA256:
        raise ValueError("baseline config is not exact Candidate AI")
    old = f'CONFIG_CMDLINE="{AI_CMDLINE}"'.encode()
    new = f'CONFIG_CMDLINE="{CMDLINE}"'.encode()
    if ai_config.count(old) != 1 or ai_config.count(b"maxcpus=8") != 1:
        raise ValueError("Candidate AI config command line is not unique")
    result = ai_config.replace(old, new)
    if digest_bytes(result) != CONFIG_SHA256:
        raise ValueError("derived Candidate AJ config identity changed")
    return result


def validate_kernel_policy(
    image: bytes,
    system_map_data: bytes,
    config_data: bytes,
    ai_validator: ModuleType | None = None,
) -> None:
    """Apply AI's exact kernel policy with AJ's sole maxcpus delta."""

    validator = ai_validator or load_ai_module(
        "validate-package.py", "candidate_aj_kernel_policy"
    )
    if digest_bytes(config_data) != CONFIG_SHA256:
        raise ValueError("resolved configuration is not exact Candidate AJ")
    validator.config_map(config_data)
    lines = set(config_data.decode("utf-8").splitlines())
    old_cmdline = f'CONFIG_CMDLINE="{AI_CMDLINE}"'
    new_cmdline = f'CONFIG_CMDLINE="{CMDLINE}"'
    required = (set(validator.REQUIRED_CONFIG) - {old_cmdline}) | {new_cmdline}
    missing = required - lines
    if missing:
        raise ValueError(f"required Candidate AJ config line is absent: {sorted(missing)[0]}")
    ikconfig = {"CONFIG_IKCONFIG=y", "CONFIG_IKCONFIG_PROC=y"}
    if not ikconfig <= lines:
        raise ValueError("Candidate AJ config lacks the embedded IKCONFIG contract")
    forbidden = set(validator.FORBIDDEN_ENABLED_CONFIG) & lines
    if forbidden:
        raise ValueError(
            f"forbidden regulator/observer config is enabled: {sorted(forbidden)[0]}"
        )
    if b"CONFIG_HOTPLUG_PARALLEL=y" in config_data:
        raise ValueError("parallel CPU hotplug invalidates CPU8-only request ordering")

    tokens = CMDLINE.split()
    if tokens.count("maxcpus=9") != 1:
        raise ValueError("exact Candidate AJ maxcpus=9 policy changed")
    if any(
        token in {"maxcpus=1", "maxcpus=8", "maxcpus=10", "nosmp"}
        or token.startswith(
            (
                "nr_cpus=",
                "isolcpus=",
                "irqaffinity=",
                "initcall_blacklist=",
                "cpu8",
                "cpu9",
            )
        )
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
    system_map = system_map_data.decode("ascii").splitlines()
    symbols = {line.rsplit(" ", 1)[-1] for line in system_map if " " in line}
    missing_symbols = set(validator.REQUIRED_SYSTEM_MAP) - symbols
    if missing_symbols:
        raise ValueError(f"System.map lacks gate symbol: {sorted(missing_symbols)[0]}")
    for line in system_map:
        if any(fragment in line for fragment in validator.FORBIDDEN_SYSTEM_MAP_FRAGMENTS):
            raise ValueError(
                f"System.map contains forbidden regulator/observer symbol: {line}"
            )


def config_inputs_digest(fragments: dict[str, bytes]) -> str:
    records = [f"profile={PROFILE}\n", "base=defconfig\n"]
    for relative in FRAGMENTS:
        records.append(f"{digest_bytes(fragments[relative])}  {relative}\n")
    return digest_bytes("".join(records).encode("ascii"))


def validate_manifest_profile(data: bytes, label: str) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8"))
    profiles = value.get("config", {}).get("profiles", {}) if isinstance(value, dict) else {}
    expected_ai = {
        "base": "defconfig",
        "patch_series": SERIES_REL,
        "fragments": AI_FRAGMENTS,
    }
    expected = {
        "base": "defconfig",
        "patch_series": SERIES_REL,
        "fragments": FRAGMENTS,
    }
    if profiles.get(AI_PROFILE) != expected_ai:
        raise ValueError(f"{label} changed exact Candidate AI profile")
    if profiles.get(PROFILE) != expected:
        raise ValueError(f"{label} lacks exact Candidate AJ profile")
    return value


def require_package_pins() -> None:
    values = {
        "IMAGE_SHA256": IMAGE_SHA256,
        "IMAGE_SIZE": IMAGE_SIZE,
        "IMAGE_GZ_SHA256": IMAGE_GZ_SHA256,
        "IMAGE_GZ_SIZE": IMAGE_GZ_SIZE,
        "SYSTEM_MAP_SHA256": SYSTEM_MAP_SHA256,
        "PACKAGE_DTB_SHA256": PACKAGE_DTB_SHA256,
        "GATE_AUDIT_SHA256": GATE_AUDIT_SHA256,
    }
    unresolved = [name for name, value in values.items() if value.startswith("TO_PIN_")]
    unresolved.extend(
        f"PACKAGE_MANIFEST_SHA256S[{index}]"
        for index, value in enumerate(PACKAGE_MANIFEST_SHA256S)
        if value.startswith("TO_PIN_")
    )
    if unresolved:
        raise ValueError("Candidate AJ package identities remain unpinned: " + ",".join(unresolved))
    for name in (
        "IMAGE_SHA256",
        "IMAGE_GZ_SHA256",
        "SYSTEM_MAP_SHA256",
        "PACKAGE_DTB_SHA256",
        "GATE_AUDIT_SHA256",
    ):
        if HEX256.fullmatch(values[name]) is None:
            raise ValueError(f"Candidate AJ {name} is malformed")
    size_limits = {
        "IMAGE_SIZE": 128 * 1024 * 1024,
        "IMAGE_GZ_SIZE": 16 * 1024 * 1024,
    }
    for name, limit in size_limits.items():
        if not values[name].isdecimal() or not 0 < int(values[name]) <= limit:
            raise ValueError(f"Candidate AJ {name} is malformed")
    if len(PACKAGE_MANIFEST_SHA256S) != 2:
        raise ValueError("Candidate AJ package manifest pin inventory is not two builds")
    if any(HEX256.fullmatch(value) is None for value in PACKAGE_MANIFEST_SHA256S):
        raise ValueError("Candidate AJ package manifest SHA-256 is malformed")
    if len(set(PACKAGE_MANIFEST_SHA256S)) != 2:
        raise ValueError("Candidate AJ package manifest pins are not two distinct builds")


def require_artifact_pins() -> None:
    require_package_pins()
    values = {
        "RAW_SHA256": RAW_SHA256,
        "RAW_SIZE": RAW_SIZE,
        "ARTIFACT_MANIFEST_SHA256": ARTIFACT_MANIFEST_SHA256,
        "PADDED_SHA256": PADDED_SHA256,
    }
    unresolved = [name for name, value in values.items() if value.startswith("TO_PIN_")]
    if unresolved:
        raise ValueError("Candidate AJ artifact identities remain unpinned: " + ",".join(unresolved))
    for name in ("RAW_SHA256", "ARTIFACT_MANIFEST_SHA256", "PADDED_SHA256"):
        if HEX256.fullmatch(values[name]) is None:
            raise ValueError(f"Candidate AJ {name} is malformed")
    if not values["RAW_SIZE"].isdecimal() or not 0 < int(values["RAW_SIZE"]) <= 16 * 1024 * 1024:
        raise ValueError("Candidate AJ RAW_SIZE is malformed")


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)
