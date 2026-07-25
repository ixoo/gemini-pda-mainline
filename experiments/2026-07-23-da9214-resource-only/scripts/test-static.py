#!/usr/bin/env python3
"""Storage-inert static and synthetic tests for Candidate AL tooling."""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
FAKE_HASH = "a" * 64


def load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(
            f"fixture token count differs for {old!r}: expected {count}, found {actual}"
        )
    return text.replace(old, new)


def replace_first(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"fixture token is absent: {old!r}")
    return text.replace(old, new, 1)


def al_runtime_fixture(runtime) -> str:
    ah_test = load(
        ROOT
        / "experiments/2026-07-22-ad-contract-af-kernel-split/scripts/"
        "test-runtime-validator.py",
        "candidate_al_ah_runtime_fixture",
    )
    text = ah_test.exact_capture(runtime.AH).replace("__AH_", "__AL_")
    text = replace_exact(
        text,
        "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012",
        FAKE_HASH,
        1,
    )
    text = replace_exact(
        text,
        "__AL_HOST_END__",
        "regulator_access_path=regulator-sysfs-driver-regmap-serialized\n"
        "regulator_sysfs_may_be_regcache=yes\n"
        "physical_readback_claim=none\n"
        "__AL_HOST_END__",
        1,
    )
    replacements = (
        ("i2c6_status_hex=64697361626c656400", "i2c6_status_hex=6f6b617900", 2),
        ("i2c6_platform_count=0", "i2c6_platform_count=1", 2),
        ("da9214_dt_count=0", "da9214_dt_count=1", 2),
        ("da9214_client_count=0", "da9214_client_count=1", 2),
        ("da9214_bucka_count=0", "da9214_bucka_count=1", 2),
        ("vproc_big_count=0", "vproc_big_count=1", 2),
    )
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    detail = "\n".join(
        (
            "i2c6_adapter_count=1",
            "i2c6_adapter=2",
            "i2c6_clock_frequency_hex=0033e140",
            "i2c6_push_pull_present=1",
            "i2c6_pinctrl_names_hex=64656661756c7400",
            "i2c6_pinctrl_0_hex=0000002c",
            "i2c6_pins_phandle_hex=0000002c",
            "da9214_dt_compatible_hex=646c672c64613932313400",
            "da9214_dt_reg_hex=00000068",
            "da9214_bucka_name_hex=6461393231342d6275636b6100",
            "da9214_buckb_name_hex=7670726f632d62696700",
            "i2c6_device=1100e000.i2c",
            "i2c6_driver=i2c-mt65xx",
            "da9214_client_total=1",
            "da9214_device=2-0068",
            "da9214_driver=da9211",
            "da9214_parent=i2c@1100e000",
            "da9214_bucka_class=regulator.20",
            "da9214_bucka_parent=2-0068",
            "da9214_bucka_state=enabled",
            "da9214_bucka_microvolts=800000",
            "vproc_big_class=regulator.21",
            "vproc_big_parent=2-0068",
            "vproc_big_state=enabled",
            "vproc_big_microvolts=900000",
        )
    )
    text = replace_exact(
        text,
        "vproc_big_count=1",
        "vproc_big_count=1\n" + detail,
        2,
    )
    text = replace_exact(
        text,
        "aw9523_client_count=1",
        "aw9523_client_count=1\naw9523_device=3-005b",
        2,
    )
    text = replace_exact(
        text,
        "aw9523_client=0-005b driver=aw9523-pinctrl",
        "aw9523_client=3-005b driver=aw9523-pinctrl",
        1,
    )
    return text


def main() -> int:
    python_files = sorted(SCRIPT_DIR.glob("*.py"))
    shell_files = sorted(SCRIPT_DIR.glob("*.sh"))
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for path in shell_files:
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"bash -n rejected {path.name}: {result.stderr}")

    al = load(SCRIPT_DIR / "candidate_al.py", "candidate_al_test_identity")
    al.require_artifact_pins()
    pinned_dtb = al.FINAL_DTB_SHA256
    al.FINAL_DTB_SHA256 = "TO_PIN_SYNTHETIC_FINAL_DTB_SHA256"
    try:
        al.require_artifact_pins()
    except ValueError as exc:
        if "remains unresolved" not in str(exc):
            raise
    else:
        raise RuntimeError("Candidate AL placeholder mutation did not fail closed")
    finally:
        al.FINAL_DTB_SHA256 = pinned_dtb
    al.require_artifact_pins()

    runtime = load(SCRIPT_DIR / "validate-runtime.py", "candidate_al_test_runtime")
    base = al_runtime_fixture(runtime)
    result = runtime.validate(
        base,
        FAKE_HASH,
        synthetic_installed_full_sha256_override=FAKE_HASH,
    )
    if (
        result["i2c6_adapter"] != "2"
        or result["da9214_device"] != "2-0068"
        or result["aw9523_device"] != "3-005b"
    ):
        raise RuntimeError("dynamic I2C client correlation did not validate")
    if result["bucka_microvolts"] != "800000" or result["buckb_microvolts"] != "900000":
        raise RuntimeError("exact synthetic regulator fixture did not validate")
    mutations = {
        "regcache-claim": replace_exact(
            base, "physical_readback_claim=none", "physical_readback_claim=physical", 1
        ),
        "off-grid-voltage": replace_first(
            base,
            "da9214_bucka_microvolts=800000",
            "da9214_bucka_microvolts=805000",
        ),
        "unreadable-state": replace_first(
            base, "vproc_big_state=enabled", "vproc_big_state=unknown"
        ),
        "unstable-voltage": replace_first(
            base,
            "vproc_big_microvolts=900000",
            "vproc_big_microvolts=910000",
        ),
        "i2c-error": replace_exact(
            base,
            "__AL_DMESG_END__",
            "[   50.0] i2c-mt65xx 1100e000.i2c: transfer timed out\n"
            "__AL_DMESG_END__",
            1,
        ),
        "da9211-read-failure": replace_exact(
            base,
            "__AL_DMESG_END__",
            "[   50.0] da9211 2-0068: Failed to read DEVICE_ID reg: -121\n"
            "__AL_DMESG_END__",
            1,
        ),
        "i2c-driver-name": replace_exact(
            base,
            "i2c6_driver=i2c-mt65xx",
            "i2c6_driver=mtk-i2c",
            2,
        ),
        "cpu8-request": replace_exact(
            base,
            "__AL_DMESG_END__",
            "[   50.0] mt6797-psci: CPU8 boot rejected\n__AL_DMESG_END__",
            1,
        ),
        "da9214-adapter-mismatch": replace_exact(
            base,
            "da9214_device=2-0068",
            "da9214_device=4-0068",
            2,
        ),
        "da9214-regulator-parent-mismatch": replace_exact(
            base,
            "da9214_bucka_parent=2-0068",
            "da9214_bucka_parent=4-0068",
            2,
        ),
        "aw9523-adapter-mismatch": replace_exact(
            base,
            "aw9523_client=3-005b driver=aw9523-pinctrl",
            "aw9523_client=4-005b driver=aw9523-pinctrl",
            1,
        ),
    }
    for name, mutated in mutations.items():
        try:
            runtime.validate(
                mutated,
                FAKE_HASH,
                synthetic_installed_full_sha256_override=FAKE_HASH,
            )
        except ValueError:
            continue
        raise RuntimeError(f"runtime mutation unexpectedly passed: {name}")

    # Exercise all three source adapters without creating a device-capable
    # production helper. The fake identities exist only in process memory.
    fake_values = {
        "FINAL_DTB_SHA256": "b" * 64,
        "RAW_SHA256": "c" * 64,
        "RAW_SIZE": "7385088",
        "ARTIFACT_MANIFEST_SHA256": "d" * 64,
        "PADDED_SHA256": "e" * 64,
    }
    runtime_deriver = load(
        SCRIPT_DIR / "derive-runtime-collector.py",
        "candidate_al_test_runtime_deriver",
    )
    cycle_deriver = load(
        SCRIPT_DIR / "derive-cycle-collector.py",
        "candidate_al_test_cycle_deriver",
    )
    for module in (runtime_deriver.al, cycle_deriver.al):
        for name, value in fake_values.items():
            setattr(module, name, value)
    ah_runtime_source = (
        ROOT
        / "experiments/2026-07-22-ad-contract-af-kernel-split/scripts/"
        "collect-runtime.sh"
    ).read_text(encoding="utf-8")
    derived_runtime = runtime_deriver.derive(
        ah_runtime_source, SCRIPT_DIR / "validate-runtime.py"
    )
    if "__AH_" in derived_runtime or "__AL_STATE1_BEGIN__" not in derived_runtime:
        raise RuntimeError("runtime collector derivation did not isolate AL markers")
    if "physical_readback_claim=none" not in derived_runtime:
        raise RuntimeError("runtime collector lost the regcache limitation")
    if "i2c6_adapter_count=" not in derived_runtime:
        raise RuntimeError("runtime collector lost dynamic I2C6 correlation")
    if "aw9523_device=" not in derived_runtime:
        raise RuntimeError("runtime collector lost dynamic AW9523 identity")
    if "6-0068" in derived_runtime:
        raise RuntimeError("runtime collector retained a fixed I2C adapter assumption")
    validator_source = (SCRIPT_DIR / "validate-runtime.py").read_text(
        encoding="utf-8"
    )
    if "6-0068" in validator_source or "0-005b-bound" in validator_source:
        raise RuntimeError("runtime validator retained a fixed I2C adapter assumption")

    ah_cycle_source = (
        ROOT
        / "experiments/2026-07-22-ad-contract-af-kernel-split/scripts/"
        "collect-cycle.sh"
    ).read_text(encoding="utf-8")
    derived_cycle = cycle_deriver.derive(
        ah_cycle_source, ROOT, SCRIPT_DIR / "collect-runtime.sh"
    )
    if "candidate_label=AL" not in derived_cycle or al.EXPERIMENT not in derived_cycle:
        raise RuntimeError("cycle collector derivation retained AH identity")

    installer = load(
        SCRIPT_DIR / "derive-installer.py",
        "candidate_al_test_installer_deriver",
    )
    calibration = installer.Calibration(
        "c" * 64, "7385088", "d" * 64, "e" * 64
    )
    with tempfile.TemporaryDirectory(prefix="candidate-al-installer-test.") as raw:
        source_path = installer.reconstruct_ak(pathlib.Path(raw))
        derived = installer.derive_text(
            source_path.read_text(encoding="utf-8"),
            calibration,
        )
    if al.AK_PADDED_SHA256 not in derived:
        raise RuntimeError("derived AL installer lost exact AK predecessor")
    if "reboot_or_shutdown_performed=no" not in derived:
        raise RuntimeError("derived AL installer lost no-reboot contract")

    print("validation=candidate-al-static-and-synthetic-tests")
    print(f"python_ast={len(python_files)}")
    print(f"bash_syntax={len(shell_files)}")
    print("artifact_identity=source-pinned")
    print("artifact_placeholder_mutation=fail-closed")
    print("exact_runtime_fixture=passed")
    print(f"runtime_mutations_rejected={len(mutations)}")
    print("runtime_collector_derivation=passed")
    print("cycle_collector_derivation=passed")
    print("installer_derivation=passed")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
