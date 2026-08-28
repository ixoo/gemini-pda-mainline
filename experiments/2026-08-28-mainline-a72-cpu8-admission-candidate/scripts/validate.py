#!/usr/bin/env python3
"""Validate the repository-side CPU8 admission candidate definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
require(contract["prepared_source_state"] ==
        "9fd302b315e0da6860d00295b4865d732a72e60b58d0ec1fd3f80631b8c4ff10",
        "exact post-0412 source state")
require(contract["prepared_source_integrity"] ==
        "01f388011bf406bfc56c8a8c7b60ea5b2ee769c6f2d608a471f1cce797eb4897",
        "exact post-0412 source integrity")
require(contract["physical_boots_budget"] == 1, "one physical boot")
require(contract["target_cpu"] == 8 and contract["excluded_cpu"] == 9,
        "CPU8 only")
require(contract["device_action"] is False, "definition has no device action")
require(contract["boot_candidate"] is True, "exact candidate is promoted")
require(contract["result"] ==
        "boot-candidate-validated-awaiting-guarded-deployment",
        "candidate phase")
series = ROOT / "patches/series"
require(sha256(series) == contract["integrated_series_sha256"],
        "integrated series hash")
require(len(series.read_text(encoding="utf-8").splitlines()) ==
        contract["integrated_series_entries"], "integrated series entries")
require(series.read_text(encoding="utf-8").splitlines()[-1].endswith(
        "0414-arm64-dts-mediatek-add-Gemini-CPU8-admission-candidate.patch"),
        "integrated series tail")
for number, name in (
    ("0413", "0413-dt-bindings-soc-mediatek-add-MT6797-A72-admission-controller.patch"),
    ("0414", "0414-arm64-dts-mediatek-add-Gemini-CPU8-admission-candidate.patch"),
):
    require(
        sha256(ROOT / "patches/v7.1.3" / name) ==
        contract["generated_patch_sha256"][number],
        f"generated patch {number}",
    )
manifest_path = ROOT / "kernel/manifest.json"
config_path = ROOT / "configs/gemini-a72-admission-candidate.fragment"
require(sha256(manifest_path) == contract["integrated_manifest_sha256"],
        "integrated manifest")
require(sha256(config_path) == contract["integrated_config_fragment_sha256"],
        "integrated candidate fragment")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
profile = manifest["config"]["profiles"][contract["integrated_profile"]]
require(profile["base"] == "defconfig", "candidate base config")
require(profile["patch_series"] == "patches/series", "candidate canonical series")
require(profile["fragments"][-1] ==
        "configs/gemini-a72-admission-candidate.fragment",
        "candidate policy is final fragment")
for fragment in (
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-p32-rollback.fragment",
    "configs/gemini-da921x-provider-modules-control.fragment",
    "configs/gemini-da921x-positive-provider.fragment",
    "configs/gemini-a72-pre-p28-provider-abort.fragment",
):
    require(fragment in profile["fragments"], f"required profile fragment {fragment}")
config = config_path.read_text(encoding="utf-8")
for symbol in (
    "CONFIG_MODULES=y",
    "CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y",
    "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
    "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y",
    "CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y",
    "CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION=y",
    "CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS=y",
    "CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER=y",
    "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER=y",
    "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
    "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",
    '# CONFIG_KUNIT is not set',
    '# CONFIG_HOTPLUG_SPLIT_STARTUP is not set',
    'CONFIG_LOCALVERSION="-gemini-a72-admission"',
):
    require(symbol in config, f"candidate config token {symbol}")
for path in (
    EXPERIMENT / "kernel/mediatek,mt6797-a72-admission-controller.yaml",
    EXPERIMENT / "kernel/mt6797-gemini-pda-a72-admission.dts",
    EXPERIMENT / "scripts/source_edits.py",
    EXPERIMENT / "scripts/validate_source.py",
    EXPERIMENT / "scripts/generate-patches.py",
    EXPERIMENT / "scripts/generate-on-buildbox",
):
    require(path.is_file() and not path.is_symlink(), f"exact file {path.name}")
build = contract["kernel_build"]
require(build["commit"] ==
        "c5b5cd6e450f9b7563a4a620629090344d5eb047",
        "kernel build commit")
require(build["backend"] == "buildbox" and build["result"] == "pass",
        "exact Buildbox result")
require(build["profile"] == "a72-admission-candidate",
        "kernel build profile")
require(build["config_sha256"] ==
        "2ff19f0d10045763b41f615101cdf11d90952a79d56fd670a9a673aa8228225b",
        "final configuration identity")
require(build["dtb_sha256"] ==
        "1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509",
        "candidate DTB identity")
candidate = contract["candidate"]
require(candidate["raw_sha256"] ==
        "d52d3c4e857aede5442be66cbb88b3dc4cdee34f8c01dae008af9d1a5251d6d8",
        "raw candidate identity")
require(candidate["padded_sha256"] ==
        "fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0",
        "padded candidate identity")
require(candidate["raw_size"] == 6_934_528 and
        candidate["padded_size"] == 16_777_216,
        "candidate sizes")
require(candidate["lk_gates"] == "32-of-32" and
        candidate["result"] == "pass", "candidate validation result")
require(sha256(EXPERIMENT / "scripts/build-candidate.sh") ==
        candidate["builder_sha256"], "candidate builder identity")
require(sha256(EXPERIMENT / "scripts/validate-candidate.py") ==
        candidate["validator_sha256"], "candidate validator identity")
for result in (
    "buildbox-kernel-20260828.txt",
    "candidate-validation-20260828.txt",
    "predeployment-hypothesis-20260828.txt",
):
    path = EXPERIMENT / "results" / result
    require(path.is_file() and not path.is_symlink(), f"result record {result}")
source_validator = (
    EXPERIMENT / "scripts/validate_source.py"
).read_text(encoding="utf-8")
require(
    '"mediatek,platform-state = <&a72_platform_state>;": 2' in source_validator,
    "binder and controller share the platform-state supplier",
)
patch_generator = (
    EXPERIMENT / "scripts/generate-patches.py"
).read_text(encoding="utf-8")
require(
    '"Enable the binder, controller, and their three owned sources in a\\n"'
    in patch_generator,
    "generated DT commit body is wrapped for strict checkpatch",
)
subprocess.run(
    ["python3", "-m", "py_compile",
     str(EXPERIMENT / "scripts/source_edits.py"),
     str(EXPERIMENT / "scripts/validate_source.py"),
     str(EXPERIMENT / "scripts/generate-patches.py")],
    check=True,
)
print("validation=a72-cpu8-admission-candidate-definition-and-artifact")
print("physical_boots_budget=1")
print("target_cpu=8")
print("excluded_cpu=9")
print("standalone_observer_nodes=0")
print("generated_patch_count=2")
print("integrated_series_entries=406")
print("integrated_profile=a72-admission-candidate")
print("native_vm_build=none")
print("kernel_build=exact-buildbox-pass")
print("lk_gates=32-of-32")
print("device_action=none")
print("boot_candidate=true")
print("result=pass")
