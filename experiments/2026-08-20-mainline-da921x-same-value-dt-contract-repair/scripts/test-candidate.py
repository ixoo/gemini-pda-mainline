#!/usr/bin/env python3
"""Validate the repaired candidate and its kernel/DT resource contract."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "09a8bf67e830e7a78057027b3e4def6fbd1273b1174236474d9c9420c70956ac"
DTB_SHA256 = "80972fc24406d5be8818c891d06fb8ed4d40f2332bd1eda2d8263597029ea683"
RAW_SHA256 = "87b38fc41969f3bfcc33ef814f10b5987e32fdfd3d25b2a35fc703fe40fd5f83"
PADDED_SHA256 = "85dbd8d020cc6d3527743f05d4a1071a8f573407a5519ae1584127e55e33bae9"
BOOT_FILE = "gemini-mt6797-da921x-same-value-dt-repair.boot.img"
DTB_FILE = "mt6797-gemini-pda-da921x-same-value-dt-repair.dtb"
EXPECTED_REG_NAMES = "cspm scp-cfg devapc-ao"
EXPECTED_REG = "0 11015000 0 1000 0 100a0000 0 1000 0 1000e000 0 1000"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def option(name: str) -> Path:
    try:
        index = sys.argv.index(name)
        return Path(sys.argv[index + 1])
    except (ValueError, IndexError) as error:
        raise SystemExit(f"missing {name}") from error


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = repo_root / (
        "experiments/2026-08-19-mainline-da921x-same-value-write-implementation/"
        "scripts/test-candidate.py"
    )
    require(source.is_file() and not source.is_symlink(), "source validator is unsafe")
    require(hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256,
            "source validator identity changed")
    spec = importlib.util.spec_from_file_location("same_value_candidate_validator", source)
    require(spec is not None and spec.loader is not None, "cannot load source validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    old_boot_file = module.BOOT_FILE
    old_dtb_file = module.DTB_FILE
    module.KERNEL_FIELD_SIZE = 4_818_804
    module.DTB_SHA256 = DTB_SHA256
    module.RAW_SHA256 = RAW_SHA256
    module.PADDED_SHA256 = PADDED_SHA256
    module.BOOT_FILE = BOOT_FILE
    module.DTB_FILE = DTB_FILE
    module.FILES = (module.FILES - {old_boot_file, old_dtb_file}) | {BOOT_FILE, DTB_FILE}

    base_validate_dtb = module.validate_dtb

    def validate_dtb(dtb: Path, *, pin_identity: bool) -> None:
        base_validate_dtb(dtb, pin_identity=pin_identity)
        module.require(module.fdtget(dtb, module.HANDOFF, "s", "reg-names") ==
                       EXPECTED_REG_NAMES, "handoff register names changed")
        module.require(module.fdtget(dtb, module.HANDOFF, "x", "reg") ==
                       EXPECTED_REG, "handoff register windows changed")

    module.validate_dtb = validate_dtb
    module.main()

    package = option("--package")
    config = (package / "kernel.config").read_text(encoding="ascii")
    for gate in (
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y\n",
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y\n",
    ):
        require(config.count(gate) == 1, f"configuration resource gate changed: {gate!r}")

    candidate = option("--candidate")
    dtb = candidate / DTB_FILE
    mutations = (
        ["-d", module.HANDOFF, "reg-names"],
        ["-d", module.HANDOFF, "reg"],
        ["-ts", module.HANDOFF, "reg-names", "cspm"],
    )
    require(all(module.mutation_rejected(dtb, mutation) for mutation in mutations),
            "a handoff-resource negative mutation escaped")
    print("DT_contract=three-named-windows")
    print("independent_DT_mutations_rejected=11")
    print("kernel_delta_from_rejected_candidate=none")
    print("result=pass")


if __name__ == "__main__":
    main()
