#!/usr/bin/env python3
"""Validate the pinned, read-only MT6797 thermal/AUXADC source audit."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = EXPERIMENT.parents[1]
CONTRACT_PATH = EXPERIMENT / "contract.json"
MATRIX_PATH = EXPERIMENT / "results" / "transaction-matrix.tsv"


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ordered(text: str, labels: list[tuple[str, str]]) -> None:
    position = -1
    for label, needle in labels:
        found = text.find(needle, position + 1)
        require(found >= 0, f"missing ordered marker {label}: {needle}")
        require(found > position, f"out-of-order marker: {label}")
        position = found


def validate_contract_data(data: dict) -> None:
    require(data.get("schema") == 1, "schema must be 1")
    require(
        data.get("experiment")
        == "2026-09-03-mt6797-thermal-auxadc-transaction-audit",
        "wrong experiment ID",
    )
    require(data["canonical_series"]["entry_count"] == 502, "wrong series count")
    require(
        data.get("selected_next")
        == "MT6797_PROVEN_RESET_SET_CLR_REPAIR_RST1_CLOSURE_AND_PMIC_WRAP_AUDIT",
        "wrong selected prerequisite",
    )
    constants = data["confirmed_constants"]
    require(
        constants["source_proven_reset_set_bases"] == ["0x120", "0x140"],
        "wrong source-proven reset SET bases",
    )
    require(constants["inferred_rst1_set_base"] == "0x130", "wrong inferred RST1 SET")
    require(constants["rst1_source_status"] == "unresolved", "RST1 source must remain unresolved")
    require(constants["thermal_reset_clear"] == "0x124", "wrong thermal CLEAR")
    require(constants["pmic_wrap_reset_clear"] == "0x144", "wrong pwrap CLEAR")
    require(constants["auxadc_channel"] == 11, "wrong AUXADC channel")
    require(constants["auxadc_power_bit"] == 14, "wrong AUXADC power bit")
    require(constants["vendor_gemini_auxadc_power_write"] is False, "Gemini vendor power write must remain false")
    require(constants["auxadc_power_bit_required_state"] == "unresolved", "AUXADC power-bit state must remain unresolved")
    require(constants["bank_count"] == 6, "wrong bank count")
    require(constants["sensor_count"] == 5, "wrong sensor count")
    scope = data["implementation_scope"]
    for key in (
        "thermal_dt_enabled",
        "auxadc_dt_enabled",
        "thermal_reset_phandle_added",
        "thermal_sample",
        "irq_or_watchdog_action",
        "device_action",
        "boot_candidate",
    ):
        require(scope.get(key) is False, f"{key} must remain false")
    require(scope.get("hardware_free") is True, "audit must remain hardware-free")


def validate_repo(data: dict) -> None:
    series = REPO / "patches" / "series"
    require(
        sha256_file(series) == data["canonical_series"]["sha256"],
        "canonical series hash mismatch",
    )
    entries = [
        line
        for line in series.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(len(entries) == data["canonical_series"]["entry_count"], "series count mismatch")
    for relative, expected in data["pinned_repository_inputs"].items():
        path = REPO / relative
        require(path.is_file(), f"missing pinned input: {relative}")
        require(sha256_file(path) == expected, f"hash mismatch: {relative}")

    reset_patch = (REPO / "patches/v7.1.3/0002-clk-mediatek-mt6797-add-infracfg-reset-controller.patch").read_text()
    for marker in ("\t0x120,", "\t0x124,", "\t0x128,", ".version = MTK_RST_SIMPLE"):
        require(marker in reset_patch, f"audit no longer matches reset patch: {marker}")

    aux_patch = (REPO / "patches/v7.1.3/0057-thermal-mediatek-add-MT6797-AUXADC-support.patch").read_text()
    for marker in (
        '"mediatek,mt6797-auxadc", .data = &mt8173_compat',
        ".apmixed_buffer_ctl_mask = GENMASK(31, 6) | BIT(3)",
        ".apmixed_buffer_ctl_set = BIT(0)",
    ):
        require(marker in aux_patch, f"audit no longer matches AUXADC patch: {marker}")

    rows = MATRIX_PATH.read_text().splitlines()
    require(len(rows) == 13, "matrix must contain header plus 12 rows")
    require(rows[0] == "id\tboundary\tvendor_or_hardware_contract\tcurrent_linux_7_1_3\tdecision", "matrix header mismatch")
    require(any(row.startswith("T02\t") and row.endswith("\trepair_first") for row in rows), "reset row must be selected first")


def validate_prepared_source(data: dict, root: Path) -> None:
    expected = data["prepared_source"]
    require((root / ".gemini-source-state").read_text().strip() == expected["source_state"], "prepared source-state mismatch")
    require((root / ".gemini-source-integrity").read_text().strip() == expected["source_integrity"], "prepared source-integrity mismatch")
    for relative, digest in expected["files"].items():
        require(sha256_file(root / relative) == digest, f"prepared source hash mismatch: {relative}")

    reset_clk = (root / "drivers/clk/mediatek/clk-mt6797.c").read_text()
    require(".version = MTK_RST_SIMPLE" in reset_clk, "current reset version changed")
    ordered(reset_clk, [("RST0", "0x120,"), ("misread RST1", "0x124,"), ("misread RST2", "0x128,")])

    reset_core = (root / "drivers/clk/mediatek/reset.c").read_text()
    require("regmap_update_bits" in reset_core, "simple reset update missing")
    require("deassert_ofs = deassert ? 0x4 : 0" in reset_core, "SET/CLEAR implementation missing")

    aux = (root / "drivers/iio/adc/mt6577_auxadc.c").read_text()
    require('{ .compatible = "mediatek,mt6797-auxadc", .data = &mt8173_compat }' in aux, "MT6797 compat mapping changed")
    ordered(
        aux[aux.index("static int mt6577_auxadc_read("):aux.index("static int mt6577_auxadc_read_raw")],
        [("clear", "0, 1 << chan->channel"), ("trigger", "1 << chan->channel, 0"), ("global idle", "check_global_idle")],
    )
    require("MT6577_AUXADC_PDN_EN, 0" in aux, "AUXADC power-on bit write missing")

    thermal = (root / "drivers/thermal/mediatek/auxadc_thermal.c").read_text()
    require(".apmixed_buffer_ctl_mask = GENMASK(31, 6) | BIT(3)" in thermal, "MT6797 APMIXED mask changed")
    require(".apmixed_buffer_ctl_set = BIT(0)" in thermal, "MT6797 APMIXED set changed")
    probe = thermal[thermal.index("static int mtk_thermal_probe("):thermal.index("static struct platform_driver mtk_thermal_driver")]
    ordered(probe, [("release", "mtk_thermal_release_periodic_ts"), ("bank init", "mtk_thermal_init_bank")])
    require("device_reset_optional" in probe, "optional reset call missing")
    require("request_irq(" not in thermal and "devm_request_irq(" not in thermal, "thermal IRQ behavior changed")
    bank = thermal[thermal.index("static void mtk_thermal_init_bank("):thermal.index("static u64 of_get_phys_base")]
    ordered(bank, [("first write control", "TEMP_ADCWRITECTRL_ADC_MUX_WRITE"), ("enable bank", "TEMP_MONCTL0"), ("final write control", "TEMP_ADCWRITECTRL_ADC_PNP_WRITE")])
    require("if (raw == 0)\n\t\treturn 0;" in thermal, "raw-zero behavior changed")

    dts = (root / "arch/arm64/boot/dts/mediatek/mt6797.dtsi").read_text()
    thermal_node = dts[dts.index("thermal: thermal@1100b000"):dts.index("i2c5: i2c@1101c000")]
    aux_node = dts[dts.index("auxadc: adc@11001000"):dts.index("thermal: thermal@1100b000")]
    require('status = "disabled";' in thermal_node, "thermal node must remain disabled")
    require('status = "disabled";' in aux_node, "AUXADC node must remain disabled")
    require("resets =" not in thermal_node, "thermal reset phandle unexpectedly present")
    require("resets = <&infrasys MT6797_INFRA_PMIC_WRAP_RST>;" in dts, "PMIC-wrap consumer changed")


def git_show(git_dir: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", f"--git-dir={git_dir}", "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def validate_vendor_source(data: dict, git_dir: Path) -> None:
    vendor = data["vendor_source"]
    commit = vendor["commit"]
    files: dict[str, str] = vendor["files"]
    contents: dict[str, str] = {}
    for path, digest in files.items():
        blob = git_show(git_dir, commit, path)
        require(sha256_bytes(blob) == digest, f"vendor source hash mismatch: {path}")
        contents[path] = blob.decode()

    aux = contents["drivers/misc/mediatek/auxadc/mt_auxadc.c"]
    conversion = aux[aux.index("static int IMM_auxadc_GetOneChannelValue"):aux.index("static int IMM_auxadc_GetOneChannelValue_Cali")]
    ordered(
        conversion,
        [("global idle", "step1 check con2"), ("clear", "step2 clear bit"), ("old ready", "step3"), ("trigger", "step4"), ("new ready", "step5"), ("read", "step6")],
    )
    require("AUXADC_MISC, 1 << 14" in aux, "vendor AUXADC power bit missing")

    settings = contents["drivers/misc/mediatek/thermal/mt6797/inc/tscpu_settings.h"]
    require("+ 0x120" in settings and "+ 0x124" in settings and "+ 0x128" in settings, "vendor RST0 triplet changed")

    tc = contents["drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c"]
    reset = tc[tc.index("void tscpu_reset_thermal"):tc.index("int tscpu_read_temperature_info")]
    ordered(reset, [("assert", "INFRA_GLOBALCON_RST_0_SET"), ("deassert", "INFRA_GLOBALCON_RST_0_CLR")])
    all_banks_start = tc.index("void tscpu_thermal_initial_all_bank")
    all_banks = tc[
        all_banks_start:tc.index("#if THERMAL_INFORM_OTP", all_banks_start)
    ]
    ordered(all_banks, [("clear CH11", "AUXADC_CON1_CLR_V"), ("program banks", "thermal_reset_and_initial"), ("set CH11", "AUXADC_CON1_SET_V"), ("enable banks", "tscpu_thermal_enable_all_periodoc_sensing_point")])

    pwrap_h = contents["drivers/misc/mediatek/pmic_wrap/mt6797/pwrap_hal.h"]
    require("INFRACFG_AO_REG_BASE+0x140" in pwrap_h, "vendor pwrap SET changed")
    require("INFRACFG_AO_REG_BASE+0x144" in pwrap_h, "vendor pwrap CLEAR changed")

    defconfig = contents["arch/arm64/configs/lineage_gemini_defconfig"]
    require("# CONFIG_AUXADC_NEED_POWER_ON is not set" in defconfig, "Gemini vendor AUXADC power policy changed")

    common = contents["drivers/misc/mediatek/thermal/common/thermal_zones/mtk_ts_cpu.c"]
    init = common[common.index("static void init_thermal"):common.index("static void tscpu_create_fs")]
    ordered(init, [("calibration", "tscpu_thermal_cal_prepare"), ("reset", "tscpu_reset_thermal"), ("buffer", "temp &= ~(TS_TURN_OFF)"), ("verify", "BUG_ON((readl(TS_CONFIGURE)"), ("AUXADC ready", "IMM_IsAdcInitReady"), ("disable", "thermal_disable_all_periodoc_temp_sensing"), ("all banks", "tscpu_thermal_initial_all_bank"), ("release", "thermal_release_all_periodoc_temp_sensing")])


def run_self_test(data: dict) -> None:
    mutations = [
        ("schema", 2),
        ("selected_next", "ENABLE_THERMAL"),
        ("canonical_series.entry_count", 501),
        ("confirmed_constants.source_proven_reset_set_bases", ["0x120", "0x130", "0x140"]),
        ("confirmed_constants.rst1_source_status", "confirmed"),
        ("confirmed_constants.thermal_reset_clear", "0x128"),
        ("confirmed_constants.auxadc_channel", 10),
        ("confirmed_constants.vendor_gemini_auxadc_power_write", True),
        ("confirmed_constants.bank_count", 5),
        ("implementation_scope.thermal_dt_enabled", True),
        ("implementation_scope.boot_candidate", True),
    ]
    for dotted, value in mutations:
        candidate = copy.deepcopy(data)
        target = candidate
        keys = dotted.split(".")
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        try:
            validate_contract_data(candidate)
        except ValidationError:
            continue
        raise ValidationError(f"self-test mutation accepted: {dotted}")
    print(f"self_test_mutations={len(mutations)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--vendor-git", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    data = json.loads(CONTRACT_PATH.read_text())
    validate_contract_data(data)
    validate_repo(data)
    if args.source_root:
        validate_prepared_source(data, args.source_root)
    if args.vendor_git:
        validate_vendor_source(data, args.vendor_git)
    if args.self_test:
        run_self_test(data)

    print(f"experiment={data['experiment']}")
    print(f"selected_next={data['selected_next']}")
    print(f"prepared_source_checked={'yes' if args.source_root else 'no'}")
    print(f"vendor_source_checked={'yes' if args.vendor_git else 'no'}")
    print("device_action=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError, ValidationError) as error:
        print(f"validation_error={error}", file=sys.stderr)
        raise SystemExit(1)
