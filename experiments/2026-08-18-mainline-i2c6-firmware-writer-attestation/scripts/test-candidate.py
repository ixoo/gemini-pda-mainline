#!/usr/bin/env python3
"""Source-pin and independently validate the firmware-writer candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "2a71b30f76366fc83429efc987b5b4f8ce1007847710448d74964118838d6d8c"
DTB_FILE = "mt6797-gemini-pda-i2c6-fwatt.dtb"
HANDOFF = "/dvfsp-handoff@11015000"
EXPECTED_REG = (
    "0 11015000 0 1000 0 100a0000 0 1000 0 1000e000 0 1000"
)
EXPECTED_REG_NAMES = "cspm scp-cfg devapc-ao"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def option_path(name: str) -> Path:
    try:
        index = sys.argv.index(name)
        return Path(sys.argv[index + 1])
    except (ValueError, IndexError) as error:
        raise SystemExit(f"missing required option: {name}") from error


def fdtget(dtb: Path, value_type: str, prop: str) -> str:
    return subprocess.run(
        ["fdtget", f"-t{value_type}", str(dtb), HANDOFF, prop],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def validate_attestation_resources(dtb: Path) -> None:
    require(fdtget(dtb, "x", "reg") == EXPECTED_REG,
            "attestation register windows changed")
    require(fdtget(dtb, "s", "reg-names") == EXPECTED_REG_NAMES,
            "attestation register names changed")


def attestation_mutation_rejected(dtb: Path, command: list[str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-i2c6-fwatt-mutation.") as raw:
        mutated = Path(raw) / DTB_FILE
        shutil.copyfile(dtb, mutated)
        subprocess.run(
            ["fdtput", command[0], str(mutated), *command[1:]],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            validate_attestation_resources(mutated)
        except (AssertionError, subprocess.CalledProcessError):
            return True
    return False


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
            '"""Source-pin and run the independent firmware-writer candidate validator."""',
            1,
        ),
        (
            '("KERNEL_FIELD_SIZE = 4_814_197", "KERNEL_FIELD_SIZE = 4_814_409", 1),',
            '("KERNEL_FIELD_SIZE = 4_814_197", "KERNEL_FIELD_SIZE = 4_815_528", 1),\n'
            '        ("RAW_SIZE = 6_891_520", "RAW_SIZE = 6_893_568", 1),\n'
            '        (\n'
            '            \'DTB_SHA256 = "d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48"\',\n'
            '            \'DTB_SHA256 = "80972fc24406d5be8818c891d06fb8ed4d40f2332bd1eda2d8263597029ea683"\',\n'
            '            1,\n'
            '        ),',
            1,
        ),
        ("f2837f05083bf2ee5e3caa28b3415d529ecd104b",
         "9ed564adac77042d9d0dff9dabc98b6caa646aca", 1),
        ("da921x-readonly-preflight-ledger",
         "da921x-i2c6-firmware-writer-attestation", 1),
        ("7.1.3-gemini-da921x-preflight", "7.1.3-gemini-i2c6-fwatt", 2),
        ("2ecc140cd87f151107b6ad5b21491232962d4a33b39d5770e77bf08f13b7bc04",
         "72d019e54409238a201d69941fd2b3829d99e8beeeea1c1c2124a27fbc0c8ebb", 1),
        ("c8225bc2355083d02171b9113d89ea931ece4be0edec9ee1e5c04002fab59a34",
         "6fc835e4ee3fac426c13993bb9b409a678197679115d4f33160f1eaa326730e9", 1),
        ("28c1bccede0210991a42b31e4a342d8f543222605e4096c02b718b4b503c7c27",
         "bfd4fcbda62ed8e335e4343fbc3942bd5e22da290b39be78cd1c007163548a6f", 1),
        ("4087c7671b46c57b0e9221511db6e8918d8eef6402d8e102148fd9d060580b0a",
         "e34ce1c507e110cefa8c7964a893ed22720d170a38b3f74ff0f9e55654f50452", 1),
        ("939b7c3a575dea3e1bcd06d8d8c0fb622b4c7b5b7af7c6435a30f0bb2dcb76cb",
         "94ef393cd97d0046f762fa438596df83bbd85bab9b82a8b46491ad43f08213fd", 1),
        ("a2a185aed8291f4f9f578bbbe6b65b9d4b3d3d3749347f675baa189fda886578",
         "791ddea68da68b8b6342ff030e1c8061148ff300ab553ec2bb82bf187df54d1d", 1),
        ("4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7",
         "7d8efed2f932e0a61e9417ae062fbb8b72b0baddc21c3857fb15093e0446c22b", 1),
        ("41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3",
         "4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972", 1),
        ("gemini-preflt", "gemini-fwatt", 1),
        ("gemini-mt6797-da921x-preflight.boot.img",
         "gemini-mt6797-i2c6-fwatt.boot.img", 1),
        ("mt6797-gemini-pda-da921x-preflight.dtb", DTB_FILE, 1),
        ("gemini-da921x-preflight-mutation.",
         "gemini-i2c6-fwatt-base-mutation.", 1),
        (
            "'        \"CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y\\\\n\",\\n'",
            "'        \"# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set\\\\n\",\\n'\n"
            "            '        \"# CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT is not set\\\\n\",\\n'",
            1,
        ),
        ("CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y",
         "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y", 1),
        ("CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y",
         "# CONFIG_REMOTEPROC is not set", 1),
        ("DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads",
         "DA921x_runtime_operations=identity-reads,provider-reads-only", 1),
        (
            "'        \"I2C6_ledger_expected_entries=30\\\\n\",\\n'\n"
            "            '        \"I2C6_ledger_capacity=32\\\\n\",'",
            "'        \"firmware_writer_attestation_register_writes=0\\\\n\",\\n'\n"
            "            '        \"firmware_writer_attestation_i2c6_transfers=0\\\\n\",'",
            1,
        ),
        (
            "'    print(\"I2C6_ledger_expected_entries=30\")\\n'\n"
            "            '    print(\"I2C6_ledger_capacity=32\")\\n'",
            "'    print(\"firmware_writer_attestation_register_writes=0\")\\n'\n"
            "            '    print(\"firmware_writer_attestation_i2c6_transfers=0\")\\n'",
            1,
        ),
        ("DA921x_preflight_reads_expected=10",
         "firmware_writer_attestation_samples_expected=2", 1),
        ("mainline-da921x-readonly-preflight-candidate",
         "mainline-i2c6-firmware-writer-attestation-candidate", 1),
        ("gemini-preflight-validator.", "gemini-i2c6-fwatt-validator.", 1),
    )
    for old, new, count in replacements:
        actual = text.count(old)
        if actual != count:
            raise SystemExit(
                f"unsafe validator derivation: expected {count}, found {actual}: {old}"
            )
        text = text.replace(old, new)

    # The source-pinned validator resolves repository paths from __file__, so
    # keep the ephemeral derivative beside this wrapper and remove it on exit.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=".test-candidate-derived.",
        suffix=".py",
        dir=script_dir,
    ) as handle:
        handle.write(text)
        handle.flush()
        derived = Path(handle.name)
        result = subprocess.run(
            [sys.executable, str(derived), *sys.argv[1:]], check=False
        )
    if result.returncode:
        raise SystemExit(result.returncode)

    candidate = option_path("--candidate")
    dtb = candidate / DTB_FILE
    validate_attestation_resources(dtb)
    mutations = (
        ["-tx", HANDOFF, "reg", "0", "11015000", "0", "1000",
         "0", "100a1000", "0", "1000", "0", "1000e000", "0", "1000"],
        ["-d", HANDOFF, "reg-names"],
    )
    require(
        all(attestation_mutation_rejected(dtb, list(mutation))
            for mutation in mutations),
        "an attestation-specific DT mutation escaped validation",
    )
    print("attestation_register_windows=exact")
    print("attestation_DT_mutations_rejected=2")
    print("SCP_status=disabled")
    print("boot_candidate=true")


if __name__ == "__main__":
    main()
