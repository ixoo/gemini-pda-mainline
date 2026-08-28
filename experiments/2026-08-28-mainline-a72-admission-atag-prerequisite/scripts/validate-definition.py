#!/usr/bin/env python3
"""Validate the config-only ATAG prerequisite restoration definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
FRAGMENT = ROOT / "configs/gemini-a72-admission-atag-prerequisite.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
SERIES = ROOT / "patches/series"
ATAG_PATCH = ROOT / "patches/v7.1.3/0057a-nvmem-mediatek-add-MT6797-LK-calibration-provider.patch"
IDENTITY_PATCH = ROOT / "patches/v7.1.3/0237-soc-mediatek-add-MT6797-efuse-identity-and-rail-converters.patch"
PROFILE = "a72-admission-live-trigger-candidate"
FRAGMENT_NAME = "configs/gemini-a72-admission-atag-prerequisite.fragment"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"definition rejected: {message}")


effective = [
    line.strip()
    for line in FRAGMENT.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
require(
    effective == ["CONFIG_NVMEM=y", "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y"],
    "fragment is not the exact two-option built-in delta",
)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
profiles = manifest["config"]["profiles"]
require(PROFILE in profiles, "candidate profile absent")
fragments = profiles[PROFILE]["fragments"]
require(fragments.count(FRAGMENT_NAME) == 1, "fragment is not pinned exactly once")
require(
    fragments.index(FRAGMENT_NAME) + 1 ==
    fragments.index("configs/gemini-a72-admission-live-trigger-candidate.fragment"),
    "fragment must immediately precede the candidate policy fragment",
)
require(profiles[PROFILE]["base"] == "defconfig", "profile base changed")
require(profiles[PROFILE].get("patch_series", manifest["patch_series"]) == "patches/series",
        "profile series changed")

series = [line.strip() for line in SERIES.read_text(encoding="utf-8").splitlines()
          if line.strip() and not line.startswith("#")]
atag_name = "v7.1.3/0057a-nvmem-mediatek-add-MT6797-LK-calibration-provider.patch"
identity_name = "v7.1.3/0237-soc-mediatek-add-MT6797-efuse-identity-and-rail-converters.patch"
admission_name = "v7.1.3/0411-soc-mediatek-add-one-shot-CPU8-admission-controller.patch"
require(series.index(atag_name) < series.index(identity_name) < series.index(admission_name),
        "provider/identity/admission source order changed")

atag = ATAG_PATCH.read_text(encoding="utf-8")
require(atag.count("config NVMEM_MTK_ATAG_DEVINFO") == 1, "ATAG Kconfig changed")
require(".read_only = true" in atag and ".root_only = true" in atag,
        "ATAG provider is not read-only/root-only")
require(".reg_write" not in atag, "ATAG provider gained a write callback")
identity = IDENTITY_PATCH.read_text(encoding="utf-8")
require(identity.count("cpu-efuse-identity@58") >= 2, "identity cell changed")
require("nvmem-cell-names = \"ptp-calibration-data\", \"cpu-efuse-identity\";" in identity,
        "handoff identity-cell link changed")

candidate = (ROOT / "configs/gemini-a72-admission-live-trigger-candidate.fragment").read_text(
    encoding="utf-8"
)
for forbidden in ("CPU9", "CPU_OFF", "automatic probe action"):
    require(forbidden in candidate, f"candidate safety declaration missing: {forbidden}")
require("CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y" in candidate,
        "live trigger policy changed")

print(f"fragment_sha256={sha256(FRAGMENT)}")
print(f"manifest_sha256={sha256(MANIFEST)}")
print(f"series_sha256={sha256(SERIES)}")
print(f"atag_provider_patch_sha256={sha256(ATAG_PATCH)}")
print(f"identity_patch_sha256={sha256(IDENTITY_PATCH)}")
print("config_delta=CONFIG_NVMEM=y,CONFIG_NVMEM_MTK_ATAG_DEVINFO=y")
print("kernel_source_changes=0")
print("dt_changes=0")
print("trigger_requests=0")
print("cpu_requests=0")
print("native_vm_build=none")
print("result=pass")
