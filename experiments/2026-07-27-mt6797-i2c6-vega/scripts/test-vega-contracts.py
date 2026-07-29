#!/usr/bin/env python3
"""Static and mutation contracts for Candidate Vega's one-patch delta."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import candidate_vega as co
import installer_vega as iv

PACKAGE_VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "vega_package_validator_contract",
    SCRIPT_DIR / "validate-package-vega.py",
)
if PACKAGE_VALIDATOR_SPEC is None or PACKAGE_VALIDATOR_SPEC.loader is None:
    raise RuntimeError("cannot load Vega package validator")
PACKAGE_VALIDATOR = importlib.util.module_from_spec(PACKAGE_VALIDATOR_SPEC)
PACKAGE_VALIDATOR_SPEC.loader.exec_module(PACKAGE_VALIDATOR)
PATCH_REL = (
    "v7.1.3/0118-i2c-mediatek-fix-Orion-I2C6-node-identity-check.patch"
)
PATCH = ROOT / "patches" / PATCH_REL
ORION_SERIES = ROOT / "patches/series-orion-i2c6-idvfs-fifo"
VEGA_SERIES = ROOT / "patches/series-vega-i2c6-idvfs-fifo"
CANONICAL_SERIES = ROOT / "patches/series"
FRAGMENT = ROOT / "configs/gemini-i2c6-vega.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-vega"
)
TAG = "GEMINI_VEGA_DIAGNOSTIC_GATE"


def entries(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def validate_patch(text: str) -> None:
    additions = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    required = (
        "Subject: [PATCH 118/118] i2c: mediatek: fix Orion I2C6 node identity check",
        "if (i2c->dev_comp != &mt6797_idvfs_compat)",
        "if (!i2c->dvfsp_handoff)",
        'target = of_find_node_by_path("/i2c@1100e000");',
        "if (i2c->dev->of_node != target) {",
        "GEMINI_ORION_DIAGNOSTIC state=ready one_shot=unused",
        'debugfs_create_file("orion-run-all", 0600,',
    )
    for needle in required:
        if needle not in text:
            raise ValueError(f"missing Vega patch contract: {needle}")
    if "strcmp(of_node_full_name" in additions:
        raise ValueError("representation-sensitive node-name comparison remains")
    if text.count("diff --git ") != 1:
        raise ValueError("Vega must modify exactly one kernel file")
    if "diff --git a/drivers/i2c/busses/i2c-mt65xx.c " not in text:
        raise ValueError("Vega changed the wrong kernel file")
    if text.count('of_find_node_by_path("/i2c@1100e000")') != 1:
        raise ValueError("Vega target lookup is not singular and exact")
    if text.count("+\t\tof_node_put(target);") != 1:
        raise ValueError("Vega mismatch path does not release its node reference")
    if text.count("+\tof_node_put(target);") != 1:
        raise ValueError("Vega success path does not release its node reference")
    if text.count("+\t\treturn dev_err_probe(") != 5:
        raise ValueError("Vega setup failures are not all attributable")
    if text.count(TAG) != 5:
        raise ValueError("Vega tagged failure inventory changed")


def validate_inputs(
    orion_text: str,
    vega_text: str,
    canonical_text: str,
    fragment_text: str,
    manifest: dict,
) -> None:
    orion = entries(orion_text)
    vega = entries(vega_text)
    canonical = entries(canonical_text)
    if vega != orion + [PATCH_REL]:
        raise ValueError("Vega series is not exact Orion plus 0118")
    if canonical.count(PATCH_REL) != 1:
        raise ValueError("canonical series does not contain Vega exactly once")
    if canonical.index(PATCH_REL) != canonical.index(orion[-1]) + 1:
        raise ValueError("Vega patch is not immediately after Orion")

    requested = entries(fragment_text)
    exact = {
        'CONFIG_LOCALVERSION="-gemini-vega"',
        "CONFIG_DEBUG_FS=y",
        "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y",
        "# CONFIG_I2C_CHARDEV is not set",
        "# CONFIG_REGULATOR_DA9211 is not set",
        "# CONFIG_MTK_MT6797_A72_POWER is not set",
    }
    for line in exact:
        if line not in fragment_text.splitlines():
            raise ValueError(f"Vega safety line changed: {line}")
    cmdlines = [line for line in requested if line.startswith("CONFIG_CMDLINE=")]
    if len(cmdlines) != 1:
        raise ValueError("Vega must have one forced command line")
    cmdline = cmdlines[0]
    for token in (
        "maxcpus=8",
        "panic=0",
        "Gemini-L-Vega",
        "GEMINI_VEGA_20260727",
        "initcall_blacklist=mt6797_a72_power_driver_init",
    ):
        if token not in cmdline:
            raise ValueError(f"Vega command line lacks {token}")

    profiles = manifest["config"]["profiles"]
    if PROFILE not in profiles:
        raise ValueError("Vega manifest profile is absent")
    profile = profiles[PROFILE]
    if profile["base"] != "defconfig":
        raise ValueError("Vega base changed")
    if profile["patch_series"] != "patches/series-vega-i2c6-idvfs-fifo":
        raise ValueError("Vega manifest series changed")
    if profile["fragments"][-1] != "configs/gemini-i2c6-vega.fragment":
        raise ValueError("Vega fragment is not the final policy layer")
    if profile["fragments"].count("configs/gemini-i2c6-vega.fragment") != 1:
        raise ValueError("Vega fragment selection is not singular")


class VegaContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch = PATCH.read_text()
        cls.orion = ORION_SERIES.read_text()
        cls.vega = VEGA_SERIES.read_text()
        cls.canonical = CANONICAL_SERIES.read_text()
        cls.fragment = FRAGMENT.read_text()
        cls.manifest = json.loads(MANIFEST.read_text())

    def test_current_inputs(self) -> None:
        validate_patch(self.patch)
        validate_inputs(
            self.orion,
            self.vega,
            self.canonical,
            self.fragment,
            self.manifest,
        )

    def test_tooling_source_pins_are_calibrated(self) -> None:
        co.require_input_pins()
        self.assertEqual(co.digest_path(ROOT / co.SERIES), co.SERIES_SHA256)
        self.assertEqual(
            co.digest_path(ROOT / co.CONFIG_FRAGMENT),
            co.CONFIG_FRAGMENT_SHA256,
        )
        for relative, wanted in zip(
            co.VEGA_PATCHES, co.VEGA_PATCH_SHA256S, strict=True
        ):
            self.assertEqual(co.digest_path(ROOT / "patches" / relative), wanted)

    def test_production_validator_rejects_each_mutated_patch_pin(self) -> None:
        source = (SCRIPT_DIR / "validate-package-vega.py").read_text()
        self.assertEqual(
            source.count("validate_vega_patch_pins(repository)"),
            1,
        )
        with tempfile.TemporaryDirectory(
            prefix="vega-patch-pin-contract."
        ) as raw:
            repository = pathlib.Path(raw)
            for relative in co.VEGA_PATCHES:
                destination = repository / "patches" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(
                    (ROOT / "patches" / relative).read_bytes()
                )
            PACKAGE_VALIDATOR.validate_vega_patch_pins(repository)
            for relative in co.VEGA_PATCHES:
                destination = repository / "patches" / relative
                original = destination.read_bytes()
                destination.write_bytes(original + b"\n")
                with self.subTest(relative=relative):
                    with self.assertRaisesRegex(
                        ValueError,
                        "source-pinned Vega patch changed",
                    ):
                        PACKAGE_VALIDATOR.validate_vega_patch_pins(
                            repository
                        )
                destination.write_bytes(original)

    def test_tooling_retains_exact_orion_diagnostic_and_dt_lineage(self) -> None:
        package_validator = (
            SCRIPT_DIR / "validate-package-vega.py"
        ).read_text()
        builder = (SCRIPT_DIR / "build-candidate-vega.sh").read_text()
        runner = (SCRIPT_DIR / "run-vega-one-shot.py").read_text()
        for source in (package_validator, runner):
            self.assertIn("GEMINI_ORION_DIAGNOSTIC", source)
            self.assertIn("orion-run-all", source)
        self.assertIn("ORION_COMPILED_DTB_SHA256", package_validator)
        self.assertIn("ORION_BOOT_DTB_SHA256", builder)
        self.assertIn("build-orion-dtb.sh", builder)
        self.assertIn("validate-orion-dtb-lineage.py", builder)

    def test_installer_artifact_and_self_pins_are_resolved(self) -> None:
        pins = iv.production_pins()
        self.assertTrue(iv.pins_resolved(pins))
        iv.require_artifact_pins(pins)
        self.assertRegex(iv.INSTALLER_SHA256, co.HEX256)
        self.assertRegex(iv.REPRODUCIBILITY_RECORD_SHA256, co.HEX256)
        record = ROOT / iv.REPRODUCIBILITY_RECORD
        self.assertEqual(
            iv.digest_path(record),
            iv.REPRODUCIBILITY_RECORD_SHA256,
        )

    def test_patch_mutations_fail_closed(self) -> None:
        mutations = (
            self.patch.replace(
                'of_find_node_by_path("/i2c@1100e000")',
                'of_find_node_by_path("/soc/i2c@1100e000")',
                1,
            ),
            self.patch.replace(
                "if (i2c->dev->of_node != target) {",
                "if (i2c->dev->of_node == target) {",
                1,
            ),
            self.patch.replace("+\t\tof_node_put(target);\n", "", 1),
            self.patch.replace("+\tof_node_put(target);\n", "", 1),
            self.patch.replace("+\tif (!i2c->dvfsp_handoff)\n", "", 1),
            self.patch.replace(
                "if (i2c->dev_comp != &mt6797_idvfs_compat)",
                "if (i2c->dev_comp != &mt8173_compat)",
                1,
            ),
            self.patch.replace(TAG, "UNTAGGED", 1),
            self.patch + "\ndiff --git a/Makefile b/Makefile\n",
        )
        for mutated in mutations:
            with self.subTest(mutation=mutations.index(mutated)):
                with self.assertRaises(ValueError):
                    validate_patch(mutated)

    def test_input_mutations_fail_closed(self) -> None:
        cases = []
        cases.append(
            (
                self.orion,
                self.vega.replace(PATCH_REL, "", 1),
                self.canonical,
                self.fragment,
                self.manifest,
            )
        )
        cases.append(
            (
                self.orion,
                self.vega,
                self.canonical.replace(PATCH_REL, "", 1),
                self.fragment,
                self.manifest,
            )
        )
        cases.append(
            (
                self.orion,
                self.vega,
                self.canonical,
                self.fragment.replace("maxcpus=8", "maxcpus=9", 1),
                self.manifest,
            )
        )
        changed_manifest = copy.deepcopy(self.manifest)
        changed_manifest["config"]["profiles"][PROFILE]["patch_series"] = (
            "patches/series-orion-i2c6-idvfs-fifo"
        )
        cases.append(
            (
                self.orion,
                self.vega,
                self.canonical,
                self.fragment,
                changed_manifest,
            )
        )
        for case in cases:
            with self.assertRaises(ValueError):
                validate_inputs(*case)


if __name__ == "__main__":
    unittest.main(verbosity=2)
