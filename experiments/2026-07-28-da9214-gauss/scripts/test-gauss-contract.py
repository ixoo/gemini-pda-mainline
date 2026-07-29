#!/usr/bin/env python3
"""Static and mutation contracts for Candidate Gauss."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
import candidate_gauss as co


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_fragment(path: pathlib.Path) -> tuple[str, ...]:
    return tuple(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("# Candidate")
        and not line.startswith("# identity")
        and not line.startswith("# byte-length")
    )


def validate_patch_semantics(text: str) -> None:
    exact = (
        " drivers/i2c/busses/Kconfig      |  8 +++---",
        " drivers/i2c/busses/i2c-mt65xx.c | 46 ++++++++++++++++-----------------",
        "-config I2C_MT65XX_CURIE_DIAGNOSTIC",
        "+config I2C_MT65XX_FERMI_DIAGNOSTIC",
        '-#define MTK_I2C_QUASAR_CANDIDATE\t"Curie"',
        '+#define MTK_I2C_QUASAR_CANDIDATE\t"Gauss"',
        '-#define MTK_I2C_QUASAR_DEBUGFS_FILE\t"curie-run-native"',
        '+#define MTK_I2C_QUASAR_DEBUGFS_FILE\t"fermi-run-native"',
        '-#define MTK_I2C_QUASAR_GATE\t\t"GEMINI_CURIE_DIAGNOSTIC_GATE"',
        '+#define MTK_I2C_QUASAR_GATE\t\t"GEMINI_FERMI_DIAGNOSTIC_GATE"',
        '-#define MTK_I2C_QUASAR_READY_MARKER\t'
        '"GEMINI_CURIE_NATIVE_DIAGNOSTIC"',
        '+#define MTK_I2C_QUASAR_READY_MARKER\t'
        '"GEMINI_FERMI_NATIVE_DIAGNOSTIC"',
        "-\t\treturn \"exact-stable\";",
        '+\t\treturn "exact-d3-stable";',
        '-\t\t"expected_signature=d9,d0,c0 board_control_register=d3 "',
        '-\t\t"board_control_expected=1f "',
        '+\t\t"expected_signature=d9,d0,c0 topology_register=d3 "',
        '+\t\t"d3_exact_mask=ff d3_exact_expected=1f "',
    )
    for token in exact:
        if text.count(token) != 1:
            raise ValueError(f"Gauss patch semantic token changed: {token}")
    if text.count("diff --git ") != 2:
        raise ValueError("Gauss patch does not change exactly two files")
    additions = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for forbidden in (
        "regmap_write",
        "i2c_smbus_write",
        "PAGE_CON",
        "mtk_i2c_init_hw",
        "cpu_up",
        "psci",
        "reset_control",
        "CONFIG_I2C_MT65XX_CURIE_DIAGNOSTIC",
        "curie-run-native",
        "GEMINI_CURIE",
        "mtk_i2c_curie",
    ):
        if forbidden in additions:
            raise ValueError(f"Gauss patch gained forbidden action: {forbidden}")
    changed = "\n".join(
        line
        for line in text.splitlines()
        if line.startswith(("+", "-"))
        and not line.startswith(("+++", "---"))
    )
    for inherited in (
        "0xd9, 0xd0, 0xc0, 0x1f",
        "sample->index == 3 && sample->value != sample->expected",
    ):
        if inherited in changed:
            raise ValueError(
                f"Gauss patch rewrites Curie's inherited exact-D3 gate: {inherited}"
            )


class GaussContract(unittest.TestCase):
    def test_input_pins_and_canonical_curie_successor(self) -> None:
        co.require_input_pins()
        series = (REPOSITORY / co.SERIES).read_text(encoding="ascii")
        entries = tuple(line for line in series.splitlines() if line)
        self.assertEqual(len(entries), 114)
        self.assertEqual(entries[-1], co.GAUSS_PATCH)
        curie_entries = tuple(
            line
            for line in (
                REPOSITORY / "patches/series-curie-i2c6-board-tuple"
            ).read_text(encoding="ascii").splitlines()
            if line
        )
        fermi_entries = tuple(
            line
            for line in (
                REPOSITORY / "patches/series-fermi-i2c6-topology-fingerprint"
            ).read_text(encoding="ascii").splitlines()
            if line
        )
        canonical_entries = tuple(
            line
            for line in (
                REPOSITORY / "patches/series"
            ).read_text(encoding="ascii").splitlines()
            if line
        )
        self.assertEqual(curie_entries[:-1], fermi_entries)
        self.assertEqual(curie_entries[-1], co.CURIE_PATCH)
        self.assertEqual(entries[:-1], curie_entries)
        self.assertEqual(entries, canonical_entries)
        self.assertEqual(digest(REPOSITORY / co.SERIES), co.SERIES_SHA256)
        curie_patch = REPOSITORY / "patches" / co.CURIE_PATCH
        self.assertEqual(digest(curie_patch), co.CURIE_PATCH_SHA256)
        patch = REPOSITORY / "patches" / co.GAUSS_PATCH
        self.assertEqual(digest(patch), co.GAUSS_PATCH_SHA256)

    def test_patch_is_exact_curie_to_final_gauss_transition(self) -> None:
        patch = (
            REPOSITORY / "patches" / co.GAUSS_PATCH
        ).read_text(encoding="utf-8")
        self.assertIn("index 06271e3..b7df181 100644", patch)
        self.assertIn("index 1af5143..0a45366 100644", patch)
        validate_patch_semantics(patch)
        mutations = (
            (
                "+config I2C_MT65XX_FERMI_DIAGNOSTIC",
                "+config I2C_MT65XX_CURIE_DIAGNOSTIC",
            ),
            (
                '+#define MTK_I2C_QUASAR_CANDIDATE\t"Gauss"',
                '+#define MTK_I2C_QUASAR_CANDIDATE\t"Curie"',
            ),
            (
                '+#define MTK_I2C_QUASAR_DEBUGFS_FILE\t"fermi-run-native"',
                '+#define MTK_I2C_QUASAR_DEBUGFS_FILE\t"gauss-run-native"',
            ),
            (
                '+\t\treturn "exact-d3-stable";',
                '+\t\treturn "stable";',
            ),
            (
                '+\t\t"d3_exact_mask=ff d3_exact_expected=1f "',
                '+\t\t"d3_exact_mask=07 d3_exact_expected=1f "',
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertIn(old, patch)
                with self.assertRaises(ValueError):
                    validate_patch_semantics(patch.replace(old, new, 1))

    def test_config_is_semantically_byte_identical_to_fermi(self) -> None:
        gauss = REPOSITORY / co.CONFIG_FRAGMENT
        fermi = REPOSITORY / "configs/gemini-i2c6-fermi.fragment"
        self.assertEqual(digest(gauss), co.CONFIG_FRAGMENT_SHA256)
        gauss_lines = tuple(
            line for line in gauss.read_text().splitlines()
            if not line.startswith("# Candidate")
            and not line.startswith("# identity")
            and not line.startswith("# byte-length")
        )
        fermi_lines = tuple(
            line for line in fermi.read_text().splitlines()
            if not line.startswith("# Candidate")
            and not line.startswith("# native")
            and not line.startswith("# fingerprint")
            and not line.startswith("# I2C6")
        )
        self.assertEqual(gauss_lines, fermi_lines)
        text = gauss.read_text()
        self.assertIn('CONFIG_LOCALVERSION="-gemini-fermi"', text)
        self.assertIn("CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y", text)
        self.assertIn("# CONFIG_REGULATOR_DA9211 is not set", text)
        self.assertIn("# CONFIG_MTK_MT6797_A72_POWER is not set", text)
        self.assertIn("maxcpus=8", text)
        self.assertIn("GEMINI_FERMI_20260728", text)

    def test_manifest_selects_only_named_gauss_inputs(self) -> None:
        manifest = json.loads(
            (REPOSITORY / "kernel/manifest.json").read_text(encoding="utf-8")
        )
        profile = manifest["config"]["profiles"][co.PROFILE]
        self.assertEqual(profile["patch_series"], co.SERIES)
        self.assertEqual(profile["fragments"][-1], co.CONFIG_FRAGMENT)
        self.assertNotIn("gemini-i2c6-curie.fragment", profile["fragments"])

    def test_runtime_identity_and_fixed_observation_contract(self) -> None:
        self.assertEqual(co.KERNEL_RELEASE, "7.1.3-gemini-fermi")
        self.assertEqual(co.LK_NAME, "gemini-fermi")
        self.assertEqual(co.LK_CMDLINE, "bootopt=64S3,32N2,64N2")
        self.assertEqual(co.DEBUGFS_FILE, "fermi-run-native")
        self.assertEqual(co.READY_MARKER, "GEMINI_FERMI_NATIVE_DIAGNOSTIC")
        self.assertEqual(co.D3_EXPECTED, 0x1F)
        self.assertEqual(co.SAMPLE_COUNT, 14)
        self.assertEqual(co.TRANSFER_ORDER, co._FERMI.TRANSFER_ORDER)
        self.assertEqual(co.PREFILLS, co._FERMI.PREFILLS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
