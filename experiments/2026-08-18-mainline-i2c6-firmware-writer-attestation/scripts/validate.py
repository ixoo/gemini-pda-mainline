#!/usr/bin/env python3
"""Validate the read-only MT6797 I2C6 firmware-writer attestation."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
PATCH = ROOT / (
    "patches/v7.1.3/"
    "0286-soc-mediatek-attest-I2C6-firmware-writer-closure.patch"
)
FRAGMENT = ROOT / "configs/gemini-i2c6-firmware-writer-attestation.fragment"
SERIES_ENTRY = (
    "v7.1.3/0286-soc-mediatek-attest-I2C6-firmware-writer-closure.patch"
)
PROFILE = "da921x-i2c6-firmware-writer-attestation"
PARENT = "da921x-lk-clock-readonly-provider"


class ValidationError(RuntimeError):
    """Raised when a source or contract invariant is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def additions(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def validate_patch_hunks(text: str) -> None:
    lines = text.splitlines()
    index = 0
    hunk_count = 0
    while index < len(lines):
        match = re.match(
            r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[index]
        )
        if not match:
            index += 1
            continue
        declared_old = int(match.group(2) or 1)
        declared_new = int(match.group(4) or 1)
        actual_old = 0
        actual_new = 0
        hunk_count += 1
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.startswith("@@ ") or line.startswith("diff --git ") or line == "-- ":
                break
            if line.startswith(" "):
                actual_old += 1
                actual_new += 1
            elif line.startswith("-"):
                actual_old += 1
            elif line.startswith("+"):
                actual_new += 1
            elif line.startswith("\\"):
                pass
            else:
                break
            index += 1
        require(
            (actual_old, actual_new) == (declared_old, declared_new),
            f"malformed patch hunk {hunk_count}",
        )
    require(hunk_count == 8, "unexpected patch hunk count")


def validate_contract(contract: dict) -> None:
    require(
        contract["status"] == "candidate-validated-awaiting-runtime",
        "contract status changed",
    )
    require(contract["profile"] == PROFILE, "profile changed")
    require(contract["parent_profile"] == PARENT, "parent changed")
    require(contract["kernel_release"] == "7.1.3-gemini-i2c6-fwatt",
            "release changed")
    require(contract["samples"] == 2, "sample count changed")
    require(contract["sample_delay_us"] == {"minimum": 10000, "maximum": 11000},
            "sample delay changed")
    require(contract["resources"]["scp_cfg"] == {
        "base": "0x100a0000",
        "size": "0x1000",
        "reset_control_offset": "0x000",
        "debug_pc_offset": "0x0b4",
    }, "SCP resource contract changed")
    require(contract["resources"]["devapc_ao"] == {
        "base": "0x1000e000",
        "size": "0x1000",
        "i2c6_module": 98,
        "permission_offset": "0x018",
        "domain_stride": "0x100",
        "master_domain_offsets": ["0xa00", "0xa04", "0xa08", "0xa0c"],
        "control_offset": "0xf00",
    }, "Device-APC resource contract changed")
    require(contract["pass_condition"] == {
        "scp_reset_control_samples": ["0x00000000", "0x00000000"],
        "scp_debug_pc_samples": ["0x00000000", "0x00000000"],
        "devapc_samples_stable": True,
        "i2c6_domain0_permission": 0,
        "i2c6_domain1_permission": 3,
    }, "pass condition changed")
    require(all(value == 0 for value in contract["forbidden"].values()),
            "forbidden action opened")
    require(contract["decision_map"]["gate6_write"] == "not-authorized",
            "Gate-6 write opened")
    require(contract["decision_map"]["cpu8_cpu9_admission"] == "closed",
            "CPU admission opened")


def validate_sources(patch_text: str, fragment: str, manifest: dict,
                     series: str, builder: str) -> None:
    validate_patch_hunks(patch_text)
    added = additions(patch_text)
    c_diff = patch_text.split(
        "diff --git a/drivers/soc/mediatek/mt6797-dvfsp-handoff.c", 1
    )[1]
    c_added = additions(c_diff)

    for required in (
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION",
        "SCP_CFG_RESET_CONTROL",
        "SCP_CFG_DEBUG_PC",
        "DEVAPC_I2C6_PERMISSION",
        "DEVAPC_MAS_DOM_0",
        "DEVAPC_APC_CON",
        "mt6797_dvfsp_capture_fw_attestation",
        "firmware_writer_attestation",
        "devm_platform_ioremap_resource_byname",
        "i2c6-fw-writer-attestation-failed",
        "register_writes=0 i2c6_transfers=0",
    ):
        require(required in added, f"source missing: {required}")

    require(c_added.count("readl(") == 5, "read-only register set changed")
    require("usleep_range(10000, 11000)" in c_added, "sample delay changed")
    require("!att->scp_reset_control[0]" in c_added and
            "!att->scp_reset_control[1]" in c_added,
            "SCP reset-zero gate missing")
    require("!att->scp_debug_pc[0]" in c_added and
            "!att->scp_debug_pc[1]" in c_added,
            "SCP PC-zero gate missing")
    require("DEVAPC_PERMISSION_NO_SEC" in c_added and
            "DEVAPC_PERMISSION_FORBID" in c_added,
            "ATF permission gate missing")
    require(
        "mt6797_dvfsp_i2c6_permission(att->devapc_permission[0][1]) ==\n"
        "\t\t\tDEVAPC_PERMISSION_FORBID;" in c_added,
        "domain-1 forbidden gate changed",
    )

    for forbidden in (
        "writel(", "writeb(", "writew(", "regmap_write(",
        "regmap_update_bits(", "i2c_transfer(", "i2c_master_send(",
        "i2c_smbus_write", "cpu_up(", "cpu_down(", "reset_control_",
    ):
        require(forbidden not in c_added,
                f"source opens forbidden boundary: {forbidden}")

    capture = patch_text.find("mt6797_dvfsp_capture_fw_attestation(handoff);")
    fail_gate = patch_text.find("!handoff->fw_attestation.passed")
    handoff = patch_text.rfind("mt6797_dvfsp_run_handoff(handoff);")
    require(-1 not in (capture, fail_gate, handoff), "probe gate missing")
    require(capture < fail_gate < handoff, "probe gate order changed")

    require(fragment.count(
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y") == 1,
        "fragment option missing or duplicated")
    require(fragment.count('CONFIG_LOCALVERSION="-gemini-i2c6-fwatt"') == 1,
            "local version changed")

    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles and PARENT in profiles, "profile missing")
    require(profiles[PROFILE]["base"] == profiles[PARENT]["base"],
            "profile base changed")
    require(
        profiles[PROFILE]["fragments"] ==
        profiles[PARENT]["fragments"] + [
            "configs/gemini-i2c6-firmware-writer-attestation.fragment"
        ],
        "profile is not the exact parent plus isolated fragment",
    )
    require(series.splitlines()[-1] == SERIES_ENTRY,
            "canonical series tail changed")

    for required in (
        "PROVIDER_DTB_SHA256=d7dba05e",
        "OUTPUT_DTB_SHA256=80972fc2",
        "0 100a0000 0 1000",
        "0 1000e000 0 1000",
        "cspm scp-cfg devapc-ao",
        "SCP_status=disabled",
        "attestation_register_writes=0",
        "I2C6_attestation_transfers=0",
    ):
        require(required in builder, f"DT builder missing: {required}")
    require(builder.count("0 1000e000 0 1000") == 2,
            "Device-APC DT window is not pinned twice")
    require(builder.count("\nfdtput -") == 2, "unexpected DT mutation count")


def reject_mutations(contract: dict, patch_text: str, fragment: str,
                     manifest: dict, series: str, builder: str) -> int:
    mutations = []
    changed = copy.deepcopy(contract)
    changed["samples"] = 1
    mutations.append(("sample-count", lambda value=changed: validate_contract(value)))
    changed = copy.deepcopy(contract)
    changed["pass_condition"]["scp_debug_pc_samples"][1] = "any"
    mutations.append(("pc-wildcard", lambda value=changed: validate_contract(value)))
    changed = copy.deepcopy(contract)
    changed["forbidden"]["scp_register_writes"] = 1
    mutations.append(("scp-write", lambda value=changed: validate_contract(value)))
    changed = copy.deepcopy(contract)
    changed["decision_map"]["gate6_write"] = "authorized"
    mutations.append(("gate6-write", lambda value=changed: validate_contract(value)))

    def source_mutation(old: str, new: str):
        return lambda: validate_sources(
            patch_text.replace(old, new, 1), fragment, manifest, series, builder
        )

    mutations.extend([
        ("scp-reset", source_mutation(
            "!att->scp_reset_control[0]", "att->scp_reset_control[0] >= 0")),
        ("scp-pc", source_mutation(
            "!att->scp_debug_pc[1]", "att->scp_debug_pc[1] >= 0")),
        ("domain1", source_mutation(
            "\t\t\tDEVAPC_PERMISSION_FORBID;",
            "\t\t\tDEVAPC_PERMISSION_NO_SEC;")),
        ("register-write", source_mutation(
            "readl(handoff->scp_cfg", "writel(0, handoff->scp_cfg")),
        ("fragment", lambda: validate_sources(
            patch_text,
            fragment.replace(
                "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y",
                "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION is not set",
            ), manifest, series, builder)),
        ("dt-window", lambda: validate_sources(
            patch_text, fragment, manifest, series,
            builder.replace("0 1000e000 0 1000", "0 1000f000 0 1000", 1))),
    ])

    rejected = 0
    for name, mutation in mutations:
        try:
            mutation()
        except (ValidationError, KeyError, IndexError, TypeError):
            rejected += 1
        else:
            raise ValidationError(f"unsafe mutation accepted: {name}")
    return rejected


def main() -> None:
    patch_text = PATCH.read_text(encoding="utf-8")
    fragment = FRAGMENT.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    series = (ROOT / "patches/series").read_text(encoding="utf-8")
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    builder = (EXPERIMENT / "scripts/build-attestation-dtb.sh").read_text()

    validate_contract(contract)
    validate_sources(patch_text, fragment, manifest, series, builder)
    rejected = reject_mutations(
        contract, patch_text, fragment, manifest, series, builder
    )
    print("validation=mainline-i2c6-firmware-writer-attestation")
    print(f"profile={PROFILE}")
    print("samples=2")
    print("sample_delay_us=10000..11000")
    print("SCP_register_writes=0")
    print("Device_APC_register_writes=0")
    print("I2C6_attestation_transfers=0")
    print("Gate6_write=not-authorized")
    print("CPU8_CPU9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
