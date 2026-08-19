#!/usr/bin/env python3
"""Source-pin and independently validate the transaction-window candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "e0b06a69801b8aafaffcf716119b5766843b648b881eaabcc2ad8624be931dd6"
DTB_FILE = "mt6797-gemini-pda-i2c6-fwtxn.dtb"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def option_path(name: str) -> Path:
    try:
        index = sys.argv.index(name)
        return Path(sys.argv[index + 1])
    except (ValueError, IndexError) as error:
        raise SystemExit(f"missing required option: {name}") from error


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    source = (
        repo_root
        / "experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation"
        / "scripts/test-candidate.py"
    )
    if source.is_symlink() or not source.is_file():
        raise SystemExit("source validator is missing or unsafe")
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise SystemExit("source validator identity changed")

    text = source_bytes.decode("utf-8")
    replacements = (
        ("9ed564adac77042d9d0dff9dabc98b6caa646aca",
         "21728a382e771d7e11b4b9bf0392037002ffd572", 1),
        ("da921x-i2c6-firmware-writer-attestation",
         "da921x-i2c6-firmware-writer-transaction-window", 1),
        ("7.1.3-gemini-i2c6-fwatt", "7.1.3-gemini-i2c6-fwtxn", 1),
        ("KERNEL_FIELD_SIZE = 4_815_528", "KERNEL_FIELD_SIZE = 4_816_040", 1),
        ("72d019e54409238a201d69941fd2b3829d99e8beeeea1c1c2124a27fbc0c8ebb",
         "ac943b89424976e081f9456a5875d4590b5d58f97d1b67bb72587a4407901b33", 1),
        ("6fc835e4ee3fac426c13993bb9b409a678197679115d4f33160f1eaa326730e9",
         "9fa80052966f62822ad010784c374bed65714502410e89915d47ec4f0eca2ff9", 1),
        ("bfd4fcbda62ed8e335e4343fbc3942bd5e22da290b39be78cd1c007163548a6f",
         "a6ebe65225cea56cb176545fab2620affabd0ec8062a9e3a1ef1160f3f4e32d0", 1),
        ("e34ce1c507e110cefa8c7964a893ed22720d170a38b3f74ff0f9e55654f50452",
         "a8bc482a268c8223f3205d77fa220eebd8a6ca585c47a0ac5ab528297181431c", 1),
        ("94ef393cd97d0046f762fa438596df83bbd85bab9b82a8b46491ad43f08213fd",
         "44afe75ba245bc9575995df34f4292ca23fb193b094aa5ed07581fdbf38d17b6", 1),
        ("791ddea68da68b8b6342ff030e1c8061148ff300ab553ec2bb82bf187df54d1d",
         "d7d4d1842ac2b07e29b25d025fd1ba6e922008ae7815a98822860182604ff4d7", 1),
        ("7d8efed2f932e0a61e9417ae062fbb8b72b0baddc21c3857fb15093e0446c22b",
         "db828e1a6295167f8b370f04e87e675dba9bc08b6c0908283c3b11fe2cca7549", 1),
        ("4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972",
         "fd6680d6e0ab3fbd61cc4f46b517a4672dd115eed92f2bbc0ae788b6e263c760", 1),
        ('("gemini-preflt", "gemini-fwatt", 1)',
         '("gemini-preflt", "gemini-fwtxn", 1)', 1),
        ("gemini-mt6797-i2c6-fwatt.boot.img",
         "gemini-mt6797-i2c6-fwtxn.boot.img", 1),
        ("mt6797-gemini-pda-i2c6-fwatt.dtb", DTB_FILE, 1),
        ("gemini-i2c6-fwatt-base-mutation.",
         "gemini-i2c6-fwtxn-base-mutation.", 1),
        ("mainline-i2c6-firmware-writer-attestation-candidate",
         "mainline-i2c6-firmware-writer-transaction-window-candidate", 1),
        ("gemini-i2c6-fwatt-validator.", "gemini-i2c6-fwtxn-validator.", 1),
    )
    for old, new, count in replacements:
        actual = text.count(old)
        if actual != count:
            raise SystemExit(
                f"unsafe validator derivation: expected {count}, found {actual}: {old}"
            )
        text = text.replace(old, new)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=".test-candidate-derived.",
        suffix=".py", dir=script_dir,
    ) as handle:
        handle.write(text)
        handle.flush()
        result = subprocess.run(
            [sys.executable, handle.name, *sys.argv[1:]], check=False
        )
    if result.returncode:
        raise SystemExit(result.returncode)

    package = option_path("--package")
    config = (package / "kernel.config").read_text(encoding="ascii")
    for gate in (
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y\n",
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y\n",
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y\n",
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y\n",
        "# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set\n",
        "# CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT is not set\n",
        "# CONFIG_REMOTEPROC is not set\n",
    ):
        require(gate in config, f"transaction-window configuration gate missing: {gate!r}")

    candidate = option_path("--candidate")
    provenance = (candidate / "provenance.txt").read_text(encoding="ascii")
    for gate in (
        "transaction_window_expected_entries=20\n",
        "transaction_entry_reset_checks_expected=20\n",
        "transaction_exit_reset_checks_expected=20\n",
        "transaction_reset_failures_expected=0\n",
        "I2C6_entry_ledger_expected_entries=20\n",
        "I2C6_entry_ledger_capacity=32\n",
    ):
        require(gate in provenance, f"candidate transaction gate missing: {gate!r}")
    print("transaction_window_configuration=exact")
    print("transaction_entry_reset_checks_expected=20")
    print("transaction_exit_reset_checks_expected=20")
    print("I2C6_entry_ledger_expected_entries=20")
    print("boot_candidate=true")


if __name__ == "__main__":
    main()
