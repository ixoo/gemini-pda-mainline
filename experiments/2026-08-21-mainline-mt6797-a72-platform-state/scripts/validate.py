#!/usr/bin/env python3
"""Validate the MT6797 A72 platform-state generation input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["repository_parent"] ==
            "cdf5dbe9e1f9331eb261b705f22a52b871a0bc94",
            "signed audit parent")
    for key in ("readme", "design", "matrix"):
        path = ROOT / contract["decision"][key]
        require(sha256(path) == contract["decision"][f"{key}_sha256"],
                f"decision {key} hash")
    require(contract["decision"]["selected_boundary"] ==
            "DEFAULT_OFF_CAPTURE_ONLY_PLATFORM_STATE",
            "selected boundary")
    require(contract["parent"]["source_state"] ==
            "905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e",
            "parent source state")
    require(contract["expected_patches"] == [
        "patches/v7.1.3/0308-watchdog-mtk-expose-locked-reset-status.patch",
        "patches/v7.1.3/0309-dt-bindings-soc-mediatek-add-MT6797-A72-platform-state.patch",
        "patches/v7.1.3/0310-soc-mediatek-add-MT6797-A72-platform-state-source.patch",
        "patches/v7.1.3/0311-arm64-dts-mediatek-add-MT6797-A72-platform-state-source.patch",
    ], "four logical patch identities")
    patch_hashes = []
    for relative in contract["expected_patches"]:
        patch = ROOT / relative
        require(patch.is_file(), f"canonical patch exists: {relative}")
        patch_hashes.append(sha256(patch))
    require(contract["validated_generation"] == {
        "repository_commit": "31f73570ad039a9004b91a1a6762aeeafd4f8e0f",
        "buildbox_job": (
            "31f73570ad039a9004b91a1a6762aeeafd4f8e0f-"
            "mt6797-a72-platform-state-patchgen"
        ),
        "package": "mt6797-a72-platform-state-patches-31f73570ad03",
        "baseline_commit": "96eba93ec8a24a9068f325695ee05aec78ebc682",
        "result_commit": "69cc6582c8b46f8b74e2bb7cbbcb28cc2e695b05",
        "sha256sums_sha256": (
            "7020f72e18ba5dafedb1884003e3e1ce49df9515062a85458c80b5bcf36fb5e7"
        ),
        "patch_sha256": [
            "917182820800180aaa45d555c9e73f43847ded4c2e23b0a875e8071613aa5c33",
            "69b41c42cdf240fed2c76b94eff521c549ba717ff8cf39498d2f6589217bca79",
            "9f9475cd4402b76d48fe9f736371711e626b107a8eb0fe5165f1c69491dc888d",
            "2775da6b8fa59447db9df85574f616fe4f35cc11342f79f8873f829460ae51d2",
        ],
        "source_validation": "pass",
        "patch_replay": "pass",
        "strict_checkpatch": "0-errors-0-warnings-0-checks",
    }, "validated Buildbox generation identity")
    require(contract["validated_build"] == {
        "repository_commit": "aa7dc4ffe71ce7884e577ec572ec6f03304ce77f",
        "buildbox_job": (
            "aa7dc4ffe71ce7884e577ec572ec6f03304ce77f-"
            "mt6797-a72-platform-state-source-m0"
        ),
        "package": (
            "linux-7.1.3-gemini-mt6797-a72-platform-state-source-"
            "49c30e65-43b552e2"
        ),
        "kernel_release": "7.1.3-gemini-a72-platform-state",
        "profile": "mt6797-a72-platform-state-source",
        "source_sha256": (
            "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
        ),
        "patchset_sha256": (
            "49c30e6544406c6093aa6b5683894419aa07839a298467a97db29e8600d4d211"
        ),
        "config_sha256": (
            "15c58ba5b0e3ef89e854b068968730730bff8f1c15f5a79e3ab99144bd03441c"
        ),
        "image_gzip_sha256": (
            "f8c9e3fe49b359eac1565be42c80dfa08ec8ee22ebbce92634dc129f6effc512"
        ),
        "gemini_dtb_sha256": (
            "dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e"
        ),
        "sha256sums_sha256": (
            "a567ddc606fc9d53c950b7239bc62af3062e62f6b5b358b1c865586c84c45887"
        ),
        "dtb_count": 119,
        "package_validation": "pass",
        "source_symbols": "present",
        "dt_node_status": "disabled",
    }, "validated Buildbox compile identity")
    require(patch_hashes == contract["validated_generation"]["patch_sha256"],
            "canonical patch hashes match Buildbox package")
    require(contract["scope"] == {
        "default_off": True,
        "toprgu_status_read": True,
        "platform_samples": 2,
        "polling": False,
        "hardware_write": False,
        "a34_caller": False,
        "opens_owner": False,
        "cpu_on": False,
        "cpu_off": False,
        "device_action": False,
        "boot_candidate": False,
    }, "scope remains closed")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    for token in (
        "generated, canonically admitted, and Buildbox compile-validated",
        "strict one-match guard correctly rejected the",
        "explicit tab-preserving string",
        "series is therefore split into four logical patches",
        "every reported style check is",
        "two immediate bounded samples with no loop or retry",
        "destination that remains all-zero on error",
        "DT node stays disabled",
        "CPU8/CPU9 remain closed",
    ):
        require(token in readme, f"README token: {token}")
    for token in (
        "clears the caller record before any lookup",
        "but do not serialize",
        "secure firmware.",
        "cannot open A34",
        "No register write",
    ):
        require(token in design, f"design token: {token}")

    driver = (HERE / "source/mt6797-a72-platform-state.c").read_text()
    header = (HERE / "source/mt6797-a72-platform-state.h").read_text()
    binding = (HERE / "source/mediatek,mt6797-a72-platform-state.yaml").read_text()
    source_edits = (HERE / "scripts/source_edits.py").read_text()
    for token in (
        "MT6797_CCI_MP2_PORT_CONTROL\t\t0x6000",
        "MT6797_CCI_STATUS\t\t\t0x000c",
        "reset_control_status(source->pwrap_reset)",
        "ret = -EBUSY",
        "ret = -EAGAIN",
        "snapshot->valid = true",
    ):
        require(token in driver, f"source driver token: {token}")
    for forbidden in (
        "writel(", "regmap_write(", "reset_control_assert(",
        "reset_control_deassert(", "readl_poll", "while (", "for (",
        "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in driver, f"forbidden source effect: {forbidden}")
    require("bool valid;" in header and "return -EOPNOTSUPP;" in header,
            "typed API and disabled stub")
    require("additionalProperties: false" in binding and
            "- const: cci" in binding,
            "strict named-resource binding")
    require('"\\ta72_power: a72-power@10222000 {\\n"' in source_edits and
            '"\\ta72_platform_state: a72-platform-state@10222000 {\\n"'
            in source_edits,
            "tab-preserving exact DTS edit anchors")

    failed_attempt = (HERE / "results/buildbox-generation-attempt-cfb17745.txt").read_text()
    for token in (
        "repository_commit=cfb17745c9a1d4dd7b8e8ce13b08642ec0bd78e3",
        "parent_integrity=pass",
        "failure=dtsi-edit-anchor-zero-match",
        "patch_package=none",
        "device_action=none",
    ):
        require(token in failed_attempt, f"failed attempt receipt: {token}")

    style_attempt = (HERE / "results/buildbox-generation-attempt-5866aeff.txt").read_text()
    for token in (
        "repository_commit=5866aeff5039c253780771039fb88405b0d50b59",
        "source_validation=pass",
        "patch_replay=pass",
        "failure=strict-checkpatch",
        "errors=0",
        "warnings=1",
        "checks=9",
        "patch_package=none",
        "device_action=none",
    ):
        require(token in style_attempt, f"style attempt receipt: {token}")

    alignment_attempt = (HERE / "results/buildbox-generation-attempt-1669a6b3.txt").read_text()
    for token in (
        "repository_commit=1669a6b3c9f2c1b44b6633181c961d868802b2ef",
        "source_validation=pass",
        "patch_replay=pass",
        "generated_patch_count=4",
        "failure=strict-checkpatch",
        "errors=0",
        "warnings=0",
        "checks=3",
        "patch_package=none",
        "device_action=none",
    ):
        require(token in alignment_attempt,
                f"alignment attempt receipt: {token}")

    generation = (HERE / "results/buildbox-generation-31f73570.txt").read_text()
    for token in (
        "repository_commit=31f73570ad039a9004b91a1a6762aeeafd4f8e0f",
        "generated_patch_count=4",
        "source_validation=pass",
        "patch_replay=pass",
        "strict_checkpatch=0-errors-0-warnings-0-checks",
        "canonical_admission=0308-0311",
        "build=pending",
        "device_action=none",
    ):
        require(token in generation, f"generation receipt: {token}")

    build = (HERE / "results/buildbox-aa7dc4ff.txt").read_text()
    for token in (
        "repository_commit=aa7dc4ffe71ce7884e577ec572ec6f03304ce77f",
        "kernel_release=7.1.3-gemini-a72-platform-state",
        "patch_count=300",
        "config_symbol=CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y",
        "source_symbols=present",
        "dt_node_status=disabled",
        "package_validation=pass",
        "hardware_write=none",
        "device_action=none",
    ):
        require(token in build, f"Buildbox compile receipt: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-mt6797-a72-platform-state-patches",
        "fetch-mt6797-a72-platform-state-patches",
    ):
        require(buildbox.count(command) >= 2, f"Buildbox command: {command}")

    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-4:] == [
        path.removeprefix("patches/")
        for path in contract["expected_patches"]
    ], "canonical series tail")
    fragment = (ROOT / "configs/gemini-mt6797-a72-platform-state.fragment").read_text()
    for token in (
        "CONFIG_RESET_CONTROLLER=y",
        "CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y",
        'CONFIG_LOCALVERSION="-gemini-a72-platform-state"',
    ):
        require(token in fragment, f"compile profile fragment: {token}")
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    require(manifest["config"]["profiles"][
        "mt6797-a72-platform-state-source"
    ] == {
        "base": "defconfig",
        "patch_series": "patches/series",
        "fragments": [
            "configs/gemini-handoff.fragment",
            "configs/gemini-mt6797-a72-platform-state.fragment",
        ],
    }, "isolated Buildbox compile profile")

    print("validation=mt6797-a72-platform-state-generation-input")
    print("result=pass")
    print("expected_patches=4")
    print("platform_samples=2-no-loop")
    print("hardware_write=none")
    print("a34_caller=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
