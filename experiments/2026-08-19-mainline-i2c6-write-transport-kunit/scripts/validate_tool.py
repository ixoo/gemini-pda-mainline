#!/usr/bin/env python3
"""Validate the deterministic B2 source editor and generated source bodies."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import source_edits


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
MANIFEST = REPO / "kernel/manifest.json"
FRAGMENT = REPO / "configs/gemini-i2c6-write-transport-kunit.fragment"
TOOL = Path(source_edits.__file__)
GENERATOR = ROOT / "scripts/generate-on-buildbox"
PATCH_VALIDATOR = ROOT / "scripts/validate_patches.py"
QEMU_RUNNER = ROOT / "scripts/run-kunit-qemu"
QEMU_CLASSIFIER = ROOT / "scripts/classify-kunit.py"
BUILDBOX = REPO / "scripts/buildbox"


class ValidationError(RuntimeError):
    """Raised when generated source escapes the B2 boundary."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        require(token in text, f"{label} missing token: {token}")


def require_kernel_indent(text: str, label: str) -> None:
    for number, line in enumerate(text.splitlines(), start=1):
        require(not (line.startswith(" ") and
                     line.lstrip(" ").startswith("\t")),
                f"{label} line {number} has spaces before a tab")


def validate_fragments(header: str, helpers: str, test: str, tool: str,
                       generator: str, patch_validator: str, runner: str,
                       classifier: str, buildbox: str) -> None:
    require_kernel_indent(header, "contract header")
    require_kernel_indent(helpers, "production helpers")
    require_kernel_indent(test, "KUnit source")
    require_tokens(header, (
        "struct mtk_i2c_idvfs_short_write_plan",
        "MTK_I2C_IDVFS_SHORT_WRITE_BYTES\t2",
        "mtk_i2c_idvfs_plan_short_write",
        "mtk_i2c_idvfs_emit_short_write",
        "mtk_i2c_idvfs_completion_result",
        "mtk_i2c_idvfs_result_after_lease",
        "mtk_i2c_idvfs_transfer_once",
    ), "contract header")
    require_tokens(helpers, (
        "num != 1",
        "msgs[0].flags",
        "msgs[0].len != MTK_I2C_IDVFS_SHORT_WRITE_BYTES",
        "plan->slave_addr = msgs[0].addr << 1",
        "plan->fifo_count = MTK_I2C_IDVFS_SHORT_WRITE_BYTES",
        "write(context, plan->fifo[i])",
        "irq_stat & MTK_I2C_IDVFS_IRQ_ARB_LOST",
        "irq_stat != MTK_I2C_IDVFS_IRQ_TRANSAC_COMP",
        "transport_result >= 0 && lease_result < 0",
        "adap->retries = 0",
        "i2c_lock_bus(adap, I2C_LOCK_ROOT_ADAPTER)",
        "ret = __i2c_transfer(adap, msgs, num)",
        "adap->retries = retries",
        "i2c_unlock_bus(adap, I2C_LOCK_ROOT_ADAPTER)",
    ), "production helpers")
    require(helpers.count("__i2c_transfer(adap, msgs, num)") == 1,
            "no-retry helper must contain one core transfer call")

    require(test.count("KUNIT_CASE(") == 12, "KUnit case count changed")
    require_tokens(test, (
        "#define MTK_I2C_TEST_ADDR\t0x2a",
        "#define MTK_I2C_TEST_BYTE0\t0xa5",
        "#define MTK_I2C_TEST_BYTE1\t0x5a",
        "mtk_i2c_idvfs_exact_two_byte_fifo_plan",
        "mtk_i2c_idvfs_no_retry_eagain",
        "mtk_i2c_idvfs_transfer_fake_init(&fake, -EAGAIN)",
        "fake.calls, 1U",
        "fake.lock_calls, 1U",
        "fake.unlock_calls, 1U",
        "fake.lock_flags,",
        "I2C_LOCK_ROOT_ADAPTER",
        "fake.locked_during",
        "fake.retries_during, 0U",
        "fake.adap.retries, 1U",
        "mtk_i2c_idvfs_lease_failure_overrides_success",
        "mtk_i2c_idvfs_transport_failure_retains_precedence",
        ".name = \"mtk-i2c-idvfs-write-contract\"",
    ), "KUnit source")
    for forbidden in (
        "0x68", "0x69", "0xda", "0x46", "i2c_add_adapter",
        "i2c_new_client", "ioremap", "debugfs", "sysfs", "procfs",
        "module_param", "OFFSET_START", "I2C_TRANSAC_START", "writel(",
    ):
        require(forbidden not in test,
                f"KUnit source contains forbidden token: {forbidden}")

    require_tokens(tool, (
        "--phase", "choices=(\"production\", \"kunit\")",
        "i2c-mt65xx-gemini-write-contract.h",
        "i2c-mt65xx-gemini-write-test.c",
        "idvfs_short_write = i2c->dev_comp == &mt6797_idvfs_compat",
        "mtk_i2c_idvfs_emit_short_write(",
        'result_anchor = indent(dedent(',
        'result_replacement = indent(dedent(',
        "mtk_i2c_idvfs_completion_result(ret,",
        "mtk_i2c_idvfs_result_after_lease(ret, lease_ret)",
        "I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST",
    ), "source editor")
    for forbidden in ("scp ", "rsync ", "boot2", "/dev/mmc", "ssh "):
        require(forbidden not in tool,
                f"source editor contains forbidden workflow token: {forbidden}")

    require_tokens(generator, (
        "PARENT_SOURCE_STATE=d93c7411cf83d24b4a59ad7bf01a42ab7282b10a00d3453b8897e2b0a9081f68",
        "DRIVER_SHA256=7a2b79e46b3735ece7ee403b3f39a824230dff501f8e9221ce1a6a8fb59022e5",
        "[[ -z \"$(git -C \"$repository_dir\" status --porcelain)\" ]]",
        "cp -- \"$bus_dir/i2c-mt65xx.c\"",
        "format-patch -2 --no-signature --numbered",
        "0288-i2c-mediatek-factor-MT6797-short-write-contract.patch",
        "0289-i2c-mediatek-add-MT6797-short-write-contract-KUnit.patch",
        "validate_patches.py",
        "git -C \"$work/verify\" am --quiet --committer-date-is-author-date",
        "checkpatch.pl\" --no-tree --strict",
        "synthetic_signoff=absent",
        "hardware_action=none",
        "device_action=none",
        "boot_candidate=false",
    ), "Buildbox generator")
    require(generator.count("cp -- \"$bus_dir/") == 3,
            "generator source-copy boundary changed")
    for forbidden in ("scp ", "rsync ", "boot2", "/dev/mmc", "qemu-system"):
        require(forbidden not in generator,
                f"generator contains forbidden workflow token: {forbidden}")

    require_tokens(patch_validator, (
        "PATCH_NAMES = (",
        "actual == PATCH_NAMES",
        "not a normal format-patch",
        "Signed-off-by:",
        "synthetic sign-off is forbidden",
        "changed_paths(production) == (",
        "changed_paths(kunit) == (",
        "KUnit patch case count changed",
        "hardware_action=none",
    ), "patch validator")

    require_tokens(runner, (
        "EXPECTED_PROFILE=i2c6-write-transport-kunit",
        "repository HEAD is not published at origin/main",
        "sha256sum --check --strict SHA256SUMS",
        "CONFIG_I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST=y",
        "focused KUnit test inventory changed",
        "timeout --signal=TERM 45 qemu-system-aarch64",
        "-machine virt -cpu cortex-a53 -smp 4 -m 1024",
        "-nographic -no-reboot -nic none -kernel \"$image\"",
        "classify-kunit.py",
    ), "QEMU runner")
    for forbidden in ("ssh ", "boot2", "/dev/mmc", "-netdev user"):
        require(forbidden not in runner,
                f"QEMU runner contains forbidden token: {forbidden}")

    require_tokens(classifier, (
        "EXPECTED_CASES = (",
        "qemu_exit == 124",
        'ktap.count("1..12") == 1',
        "an unexpected KUnit suite executed",
        "observed_cases == list(enumerate(EXPECTED_CASES, start=1))",
        "pass:12 fail:0 skip:0 total:12",
        'totals = "# Totals: pass:12 fail:0 skip:0 total:12"',
        "Kernel panic - not syncing: VFS: Unable to mount root",
        "gate6_B2=closed",
        "gate6_write=not-authorized",
        "cpu8_cpu9_admission=closed",
    ), "QEMU classifier")

    require_tokens(buildbox, (
        "generate-i2c6-write-transport-patches",
        "fetch-i2c6-write-transport-patches",
        "generate_i2c6_write_transport_patches()",
        "fetch_i2c6_write_transport_patches()",
        'readonly source_root="${workspace_root}/src/linux-7.1.3"',
        'readonly artifact_root="${workspace_root}/i2c6-write-transport-artifacts"',
        "readonly purpose=mainline-i2c6-write-transport-patch-generation",
        "2026-08-19-mainline-i2c6-write-transport-kunit/scripts/generate-on-buildbox",
        "repository_commit=${commit}",
        "generated_patch_count=2",
        "generate_i2c6_write_transport_patches ;;",
        "fetch_i2c6_write_transport_patches ;;",
    ), "Buildbox transport")
    section = buildbox[buildbox.index(
        "generate_i2c6_write_transport_patches()"):
        buildbox.index('readonly COMMAND="${1:-}"')]
    for forbidden in ("scp ", "rsync "):
        require(forbidden not in section,
                f"B2 Buildbox transport contains forbidden token: {forbidden}")


def test_mutations(header: str, helpers: str, test: str, tool: str,
                   generator: str, patch_validator: str, runner: str,
                   classifier: str, buildbox: str) -> int:
    mutations = [
        ("retry-enabled", "helpers", "adap->retries = 0",
         "adap->retries = 1"),
        ("retry-not-restored", "helpers", "adap->retries = retries",
         "adap->retries = 0"),
        ("segment-lock", "helpers", "I2C_LOCK_ROOT_ADAPTER",
         "I2C_LOCK_SEGMENT"),
        ("unlock-removed", "helpers",
         "\ti2c_unlock_bus(adap, I2C_LOCK_ROOT_ADAPTER);\n", ""),
        ("lease-success-hidden", "helpers",
         "transport_result >= 0 && lease_result < 0",
         "transport_result == 0 && lease_result < 0"),
        ("two-core-calls", "helpers",
         "ret = __i2c_transfer(adap, msgs, num);",
         "ret = __i2c_transfer(adap, msgs, num);\n"
         "\tret = __i2c_transfer(adap, msgs, num);"),
        ("spaces-before-tab", "helpers",
         "\tconst struct i2c_msg *msgs, int num,",
         "    \tconst struct i2c_msg *msgs, int num,"),
        ("real-address", "test", "#define MTK_I2C_TEST_ADDR\t0x2a",
         "#define MTK_I2C_TEST_ADDR\t0x68"),
        ("drop-case", "test",
         "\tKUNIT_CASE(mtk_i2c_idvfs_no_retry_eagain),\n", ""),
        ("start-write", "test", "MODULE_LICENSE(\"GPL\");",
         "writel(1, OFFSET_START);\nMODULE_LICENSE(\"GPL\");"),
        ("detach-production", "tool",
         "mtk_i2c_idvfs_completion_result(ret,",
         "mtk_i2c_idvfs_completion_model(ret,"),
        ("result-anchor-outdented", "tool",
         "result_anchor = indent(dedent(",
         "result_anchor = dedent("),
        ("result-replacement-outdented", "tool",
         "result_replacement = indent(dedent(",
         "result_replacement = dedent("),
        ("source-hash-drift", "generator",
         "DRIVER_SHA256=7a2b79e46b3735ece7ee403b3f39a824230dff501f8e9221ce1a6a8fb59022e5",
         "DRIVER_SHA256=0000000000000000000000000000000000000000000000000000000000000000"),
        ("dirty-check-removed", "generator",
         "[[ -z \"$(git -C \"$repository_dir\" status --porcelain)\" ]]",
         "[[ -n \"$repository_dir\" ]]"),
        ("patch-count-reduced", "generator", "format-patch -2",
         "format-patch -1"),
        ("signoff-allowed", "patch_validator",
         "require(\"Signed-off-by:\" not in text,",
         "require(True,"),
        ("qemu-network", "runner", "-nic none", "-nic user"),
        ("qemu-unbounded", "runner",
         "timeout --signal=TERM 45 qemu-system-aarch64",
         "qemu-system-aarch64"),
        ("qemu-exit-ignored", "classifier", "qemu_exit == 124",
         "qemu_exit >= 0"),
        ("runtime-skip-allowed", "classifier",
         'totals = "# Totals: pass:12 fail:0 skip:0 total:12"',
         'totals = "# Totals: pass:11 fail:0 skip:1 total:12"'),
        ("wrong-managed-source", "buildbox",
         'readonly source_root="${workspace_root}/src/linux-7.1.3"',
         'readonly source_root="${workspace_root}/src/linux"'),
        ("wrong-generation-purpose", "buildbox",
         "readonly purpose=mainline-i2c6-write-transport-patch-generation",
         "readonly purpose=unbounded-i2c6-patch-generation"),
    ]
    rejected = 0
    originals = {
        "header": header,
        "helpers": helpers,
        "test": test,
        "tool": tool,
        "generator": generator,
        "patch_validator": patch_validator,
        "runner": runner,
        "classifier": classifier,
        "buildbox": buildbox,
    }
    for name, target, old, new in mutations:
        candidate = copy.copy(originals)
        require(old in candidate[target], f"mutation anchor absent: {name}")
        candidate[target] = candidate[target].replace(old, new, 1)
        try:
            validate_fragments(**candidate)
        except ValidationError:
            rejected += 1
        else:
            raise ValidationError(f"unsafe tool mutation accepted: {name}")
    return rejected


def validate_profile() -> None:
    manifest = MANIFEST.read_text(encoding="utf-8")
    fragment = FRAGMENT.read_text(encoding="utf-8")
    profiles = json.loads(manifest)["config"]["profiles"]
    parent = profiles["da921x-i2c6-firmware-writer-transaction-window"]
    profile = profiles["i2c6-write-transport-kunit"]
    require_tokens(manifest, (
        '"i2c6-write-transport-kunit"',
        '"configs/gemini-i2c6-firmware-writer-transaction-window.fragment"',
        '"configs/gemini-i2c6-write-transport-kunit.fragment"',
    ), "manifest")
    require(profile["base"] == parent["base"],
            "B2 profile base differs from B1")
    require(profile["fragments"] == parent["fragments"] + [
        "configs/gemini-i2c6-write-transport-kunit.fragment"
    ], "B2 profile is not an exact KUnit-only extension of B1")
    require_tokens(fragment, (
        "CONFIG_KUNIT=y",
        "CONFIG_I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST=y",
        'CONFIG_LOCALVERSION="-gemini-i2c6-write-kunit"',
    ), "profile fragment")
    for forbidden in (
        "CONFIG_REGULATOR_DA9213_LEGACY_WRITE",
        "CONFIG_MTK_MT6797_A72",
    ):
        require(forbidden not in fragment,
                f"profile enables forbidden option: {forbidden}")


def main() -> None:
    header = source_edits.contract_header()
    helpers = source_edits.production_helpers()
    test = source_edits.kunit_source()
    tool = TOOL.read_text(encoding="utf-8")
    generator = GENERATOR.read_text(encoding="utf-8")
    patch_validator = PATCH_VALIDATOR.read_text(encoding="utf-8")
    runner = QEMU_RUNNER.read_text(encoding="utf-8")
    classifier = QEMU_CLASSIFIER.read_text(encoding="utf-8")
    buildbox = BUILDBOX.read_text(encoding="utf-8")
    validate_fragments(header, helpers, test, tool, generator,
                       patch_validator, runner, classifier, buildbox)
    validate_profile()
    rejected = test_mutations(header, helpers, test, tool, generator,
                              patch_validator, runner, classifier, buildbox)
    print("validation=mainline-i2c6-write-transport-source-tool")
    print("production_helpers=plan,emit,completion,lease,root-locked-once")
    print("kunit_cases=12")
    print("hardware_action=none")
    print(f"unsafe_tool_mutations_rejected={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
