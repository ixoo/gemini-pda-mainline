#!/usr/bin/env python3
"""Static and mutation contracts for Gauss package and binary validation."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
import candidate_gauss as co


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


vp = load("gauss_package_validator_test", "validate-package-gauss.py")
ab = load("gauss_binary_auditor_test", "audit-gauss-binary.py")


def synthetic_config() -> bytes:
    return ("\n".join(sorted(vp.REQUIRED_CONFIG)) + "\n").encode("ascii")


def synthetic_system_map() -> bytes:
    return "".join(
        f"ffff00000000{index:04x} T {symbol}\n"
        for index, symbol in enumerate(sorted(vp.REQUIRED_SYMBOLS))
    ).encode("ascii")


def synthetic_image() -> bytes:
    command = vp.KERNEL_CMDLINE.removeprefix(
        'CONFIG_CMDLINE="'
    ).removesuffix('"').encode("ascii")
    required = (
        b"GEMINI_FERMI_NATIVE_DIAGNOSTIC state=ready",
        b"GEMINI_FERMI_DIAGNOSTIC_GATE missing DVFSP handoff",
        b"GEMINI_FERMI_DIAGNOSTIC_GATE target node unavailable",
        b"GEMINI_FERMI_DIAGNOSTIC_GATE node identity mismatch",
        b"GEMINI_FERMI_DIAGNOSTIC_GATE adapter debugfs unavailable",
        b"GEMINI_FERMI_DIAGNOSTIC_GATE debugfs creation failed",
        b"fermi-run-native",
        b"candidate=%s state=%s one_shot=%s",
        b"Gauss",
        b"addresses=0x69,0x68 passes=2 ",
        b"transfer_order=69:05,69:06,69:47,68:d3,68:5e,68:d9,68:da ",
        b"d3_exact_mask=ff d3_exact_expected=1f ",
        b"stability_registers=d3,5e,d9,da stability_validated=%u ",
        b"sample=%u pass=%u index=%u address=%02x ",
        b"forced_length_mode=none forced_engine=none reset_pending=0",
        b"CPU%u boot rejected: A72 power sequence inactive",
    )
    return b"\0".join((command, command, *required))


class GaussPackageContract(unittest.TestCase):
    def test_exact_profile_series_and_patch_identity(self) -> None:
        co.require_input_pins()
        vp.validate_patch_pins(REPOSITORY)
        series = vp.regular(REPOSITORY / co.SERIES, "Gauss series")
        entries = vp.series_entries(series)
        self.assertEqual(len(entries), 111)
        self.assertEqual(tuple(entries[-9:]), co.GAUSS_PATCHES)
        self.assertEqual(vp.digest(series), co.SERIES_SHA256)

    def test_config_and_image_preserve_fermi_identity(self) -> None:
        config = synthetic_config()
        vp.validate_config(config)
        image = synthetic_image()
        vp.validate_image(image)
        mutations = (
            (b'CONFIG_LOCALVERSION="-gemini-fermi"', b'CONFIG_LOCALVERSION="-gemini-gauss"'),
            (b"maxcpus=8", b"maxcpus=10"),
            (b"CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y", b"# CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC is not set"),
            (b"fermi-run-native", b"gauss-run-native"),
            (b"Gauss", b"Fermi"),
            (b"d3_exact_mask=ff d3_exact_expected=1f ", b"d3_exact_mask=07 d3_exact_expected=05 "),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                target = config if old in config else image
                with self.assertRaises(ValueError):
                    (vp.validate_config if target is config else vp.validate_image)(
                        target.replace(old, new, 1)
                    )

    def test_system_map_retains_fermi_symbols(self) -> None:
        system_map = synthetic_system_map()
        vp.validate_system_map(system_map)
        self.assertIn(b"mtk_i2c_fermi_write", system_map)
        with self.assertRaises(ValueError):
            vp.validate_system_map(
                system_map.replace(b"mtk_i2c_fermi_write", b"mtk_i2c_gauss_write")
            )

    def test_manifest_is_canonical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gauss-package-manifest.") as raw:
            root = pathlib.Path(raw)
            member = root / "Image"
            member.write_bytes(b"synthetic Gauss Image")
            wanted = hashlib.sha256(member.read_bytes()).hexdigest()
            manifest = root / "SHA256SUMS"
            manifest.write_text(f"{wanted}  ./Image\n", encoding="ascii")
            vp.validate_package_manifest(root)
            manifest.write_text(f"{wanted}  ../Image\n", encoding="ascii")
            with self.assertRaises((OSError, ValueError)):
                vp.validate_package_manifest(root)

    def test_exact_comparator_and_build_id_allowlist(self) -> None:
        self.assertEqual(ab.IMAGE_COMPARATOR_OFFSET, 0x6463DC)
        self.assertEqual(ab.OLD_COMPARATOR.hex(), "410800123f140071")
        self.assertEqual(ab.NEW_COMPARATOR.hex(), "21cc42393f00026b")
        self.assertEqual(len(ab.COMPARATOR_DIFF_OFFSETS), 7)
        self.assertEqual(ab.IMAGE_BUILD_ID_NOTE_OFFSET, 0xA50838)
        self.assertEqual(ab.BUILD_ID_SIZE, 20)
        expected = bytearray(ab.OLD_COMPARATOR)
        ab.replace_at(
            expected,
            0,
            ab.OLD_COMPARATOR,
            ab.NEW_COMPARATOR,
            "synthetic comparator",
        )
        self.assertEqual(bytes(expected), ab.NEW_COMPARATOR)
        with self.assertRaises(ab.AuditError):
            ab.replace_at(
                bytearray(ab.OLD_COMPARATOR),
                0,
                b"\0" * 8,
                ab.NEW_COMPARATOR,
                "mutated comparator",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
