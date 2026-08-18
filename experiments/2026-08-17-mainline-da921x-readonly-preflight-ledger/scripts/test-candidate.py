#!/usr/bin/env python3
"""Source-pin and run the independent preflight/ledger candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "d1379831ff9e2a3f288cc5c4f098538097fe6a5356192e03e53feb61a199b00b"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    source = (
        repo_root
        / "experiments/2026-08-17-mainline-da921x-readonly-provider-baseline"
        / "scripts/test-candidate.py"
    )
    if source.is_symlink() or not source.is_file():
        raise SystemExit("source validator is missing or unsafe")
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise SystemExit("source validator identity changed")

    text = source_bytes.decode("utf-8")
    replacements = (
        (
            '"""Independently validate the read-only DA921x provider boot candidate."""',
            '"""Independently validate the DA921x read-only preflight/ledger candidate."""',
            1,
        ),
        ("KERNEL_FIELD_SIZE = 4_814_197", "KERNEL_FIELD_SIZE = 4_814_409", 1),
        (
            'REPOSITORY_COMMIT = "7199e8229c6a805a941e33a6862956949dfebd3a"',
            'REPOSITORY_COMMIT = "f2837f05083bf2ee5e3caa28b3415d529ecd104b"',
            1,
        ),
        (
            'PROFILE = "da921x-lk-clock-readonly-provider"',
            'PROFILE = "da921x-readonly-preflight-ledger"',
            1,
        ),
        (
            'RELEASE = "7.1.3-gemini-da921x-lkro"',
            'RELEASE = "7.1.3-gemini-da921x-preflight"',
            1,
        ),
        (
            'IMAGE_SHA256 = "c5d73e077165f0f22b0d8ff109661edc29763c12f4ed6fbd64b2d0fef910e1cc"',
            'IMAGE_SHA256 = "2ecc140cd87f151107b6ad5b21491232962d4a33b39d5770e77bf08f13b7bc04"',
            1,
        ),
        (
            'IMAGE_GZIP_SHA256 = "086d109464533194abed2c19fa56e647033edd957dafb2ee2512acd3100ed9f1"',
            'IMAGE_GZIP_SHA256 = "c8225bc2355083d02171b9113d89ea931ece4be0edec9ee1e5c04002fab59a34"',
            1,
        ),
        (
            'CONFIG_SHA256 = "4ea4743024f6e8f10beeaf7db837af153d1bada99c704835143d9d5e691e9326"',
            'CONFIG_SHA256 = "28c1bccede0210991a42b31e4a342d8f543222605e4096c02b718b4b503c7c27"',
            1,
        ),
        (
            'SYSTEM_MAP_SHA256 = "12b760eee8c704cfd968a084d4a81a293ebeb95edbfa6504c56a2c8e14c684c1"',
            'SYSTEM_MAP_SHA256 = "4087c7671b46c57b0e9221511db6e8918d8eef6402d8e102148fd9d060580b0a"',
            1,
        ),
        (
            'BUILD_JSON_SHA256 = "5732eff6428a1dbc983ed2dc096209693fef752919e13d196d8bb97701a1a82d"',
            'BUILD_JSON_SHA256 = "939b7c3a575dea3e1bcd06d8d8c0fb622b4c7b5b7af7c6435a30f0bb2dcb76cb"',
            1,
        ),
        (
            'PACKAGE_MANIFEST_SHA256 = "c0cb589e35ca1b49860317bd343fa0fbf195e456469b4eff3b193ecaa0fe3566"',
            'PACKAGE_MANIFEST_SHA256 = "a2a185aed8291f4f9f578bbbe6b65b9d4b3d3d3749347f675baa189fda886578"',
            1,
        ),
        (
            'RAW_SHA256 = "ab86ce3950a335cc863f4d0a5921b17348cb1c184fcc69f3efa326f8ed22a321"',
            'RAW_SHA256 = "4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7"',
            1,
        ),
        (
            'PADDED_SHA256 = "eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854"',
            'PADDED_SHA256 = "41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3"',
            1,
        ),
        (
            'BOOT_FILE = "gemini-mt6797-da921x-lkro-provider.boot.img"',
            'BOOT_FILE = "gemini-mt6797-da921x-preflight.boot.img"',
            1,
        ),
        (
            'DTB_FILE = "mt6797-gemini-pda-da921x-lkro-provider.dtb"',
            'DTB_FILE = "mt6797-gemini-pda-da921x-preflight.dtb"',
            1,
        ),
        ("gemini-da921x-lkro-mutation.", "gemini-da921x-preflight-mutation.", 1),
        (
            '        "CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\\n",',
            '        "CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\\n",\n'
            '        "CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y\\n",\n'
            '        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y\\n",\n'
            '        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y\\n",',
            1,
        ),
        ('b"gemini-lkro"', 'b"gemini-preflt"', 1),
        (
            '        "DA921x_provider_operations=get_voltage_sel,list_voltage,is_enabled\\n",',
            '        "DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads\\n",\n'
            '        "I2C6_ledger_expected_entries=30\\n",\n'
            '        "I2C6_ledger_capacity=32\\n",',
            1,
        ),
        (
            'print("validation=mainline-da921x-readonly-provider-candidate")',
            'print("validation=mainline-da921x-readonly-preflight-candidate")',
            1,
        ),
        (
            'print("kernel_release=7.1.3-gemini-da921x-lkro")',
            'print("kernel_release=7.1.3-gemini-da921x-preflight")',
            1,
        ),
        (
            '    print("DA921x_register_data_writes_expected=0")',
            '    print("I2C6_ledger_expected_entries=30")\n'
            '    print("I2C6_ledger_capacity=32")\n'
            '    print("DA921x_preflight_reads_expected=10")\n'
            '    print("DA921x_register_data_writes_expected=0")',
            1,
        ),
    )
    for old, new, count in replacements:
        actual = text.count(old)
        if actual != count:
            raise SystemExit(
                f"unsafe validator derivation: expected {count}, found {actual}: {old}"
            )
        text = text.replace(old, new)

    with tempfile.TemporaryDirectory(prefix="gemini-preflight-validator.") as raw:
        derived = Path(raw) / "test-candidate-derived.py"
        derived.write_text(text, encoding="utf-8")
        result = subprocess.run([sys.executable, str(derived), *sys.argv[1:]], check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
