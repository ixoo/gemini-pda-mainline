#!/usr/bin/env python3
"""Source-pin and run the independent runtime-preflight candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "2a71b30f76366fc83429efc987b5b4f8ce1007847710448d74964118838d6d8c"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    source = (
        repo_root
        / "experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger"
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
            '"""Source-pin and run the independent preflight/ledger candidate validator."""',
            '"""Source-pin and run the independent runtime-preflight candidate validator."""',
            1,
        ),
        (
            '("KERNEL_FIELD_SIZE = 4_814_197", "KERNEL_FIELD_SIZE = 4_814_409", 1),',
            '("KERNEL_FIELD_SIZE = 4_814_197", "KERNEL_FIELD_SIZE = 4_815_973", 1),\n'
            '        ("RAW_SIZE = 6_891_520", "RAW_SIZE = 6_893_568", 1),',
            1,
        ),
        ("f2837f05083bf2ee5e3caa28b3415d529ecd104b",
         "a3679cd38937bf9a7c9e25d19385e8f992506370", 1),
        ("da921x-readonly-preflight-ledger", "da921x-runtime-preflight-ledger", 1),
        ("7.1.3-gemini-da921x-preflight", "7.1.3-gemini-da921x-preflight-rt", 2),
        ("2ecc140cd87f151107b6ad5b21491232962d4a33b39d5770e77bf08f13b7bc04",
         "617dec242ecc82222d6dc05df60e534c7e63fd84fad249504378901f094d6d11", 1),
        ("c8225bc2355083d02171b9113d89ea931ece4be0edec9ee1e5c04002fab59a34",
         "a33fc7b29ed09e1d30a79447fc3ef9cc70775f31d5085c93ddfc07a103f546b0", 1),
        ("28c1bccede0210991a42b31e4a342d8f543222605e4096c02b718b4b503c7c27",
         "2241843a550091422381ec59b4b57c7abc8d9ae757c2956edbd0acb5a11a19b3", 1),
        ("4087c7671b46c57b0e9221511db6e8918d8eef6402d8e102148fd9d060580b0a",
         "1b2759aa513d73678e8f421c223e399ea0e9dcb8042029c26848b84e3f68d9f6", 1),
        ("939b7c3a575dea3e1bcd06d8d8c0fb622b4c7b5b7af7c6435a30f0bb2dcb76cb",
         "7a99af2e89749b515448fa8703a93fa54a11c64c654cd187e24af062037dcee7", 1),
        ("a2a185aed8291f4f9f578bbbe6b65b9d4b3d3d3749347f675baa189fda886578",
         "cc94db055cbde031701f80de97f6ef9f6ed5f99cd4caf1b8d023a7a1c7eb6e99", 1),
        ("4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7",
         "5f1ce652cee1fe77a4d963849dd047a9fbed6b0a25ef8fb48bcde74cb30b665d", 1),
        ("41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3",
         "af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296", 1),
        ("gemini-preflt", "gemini-prefrt", 1),
        ("gemini-mt6797-da921x-preflight.boot.img",
         "gemini-mt6797-da921x-runtime-preflight.boot.img", 1),
        ("mt6797-gemini-pda-da921x-preflight.dtb",
         "mt6797-gemini-pda-da921x-runtime-preflight.dtb", 1),
        ("gemini-da921x-preflight-mutation.",
         "gemini-da921x-runtime-preflight-mutation.", 1),
        (
            "'        \"CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y\\\\n\",\\n'",
            "'        \"# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set\\\\n\",\\n'\n"
            "            '        \"CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y\\\\n\",\\n'",
            1,
        ),
        ("DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads",
         "DA921x_runtime_operations=identity-reads,provider-reads,one-shot-triggered-preflight-reads", 1),
        (
            "'        \"I2C6_ledger_expected_entries=30\\\\n\",\\n'",
            "'        \"I2C6_ledger_pretrigger_entries=20\\\\n\",\\n'\n"
            "            '        \"I2C6_ledger_posttrigger_entries=30\\\\n\",\\n'",
            1,
        ),
        (
            "'    print(\"I2C6_ledger_expected_entries=30\")\\n'",
            "'    print(\"I2C6_ledger_pretrigger_entries=20\")\\n'\n"
            "            '    print(\"I2C6_ledger_posttrigger_entries=30\")\\n'",
            1,
        ),
        ("DA921x_preflight_reads_expected=10", "DA921x_triggered_preflight_reads_expected=10", 1),
        ("mainline-da921x-readonly-preflight-candidate",
         "mainline-da921x-runtime-preflight-candidate", 1),
        ("gemini-preflight-validator.", "gemini-runtime-preflight-validator.", 1),
    )
    for old, new, count in replacements:
        actual = text.count(old)
        if actual != count:
            raise SystemExit(
                f"unsafe validator derivation: expected {count}, found {actual}: {old}"
            )
        text = text.replace(old, new)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=".derived-test-candidate.",
        suffix=".py",
        dir=script_dir,
        delete=False,
    ) as handle:
        handle.write(text)
        derived = Path(handle.name)
    try:
        result = subprocess.run([sys.executable, str(derived), *sys.argv[1:]], check=False)
    finally:
        derived.unlink(missing_ok=True)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
