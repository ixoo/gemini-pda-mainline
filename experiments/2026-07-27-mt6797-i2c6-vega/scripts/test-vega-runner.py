#!/usr/bin/env python3
"""Source and reset-accounting tests for the Vega one-shot collector."""

from __future__ import annotations

import collections
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ORION_SCRIPT_DIR = (
    SCRIPT_DIR.parents[1] / "2026-07-27-mt6797-i2c6-orion/scripts"
)
sys.path.insert(0, str(ORION_SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR))
RUNNER_PATH = SCRIPT_DIR / "run-vega-one-shot.py"
SPEC = importlib.util.spec_from_file_location("vega_runner", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Vega runner")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, ORION_SCRIPT_DIR / filename
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FULL = load("vega_runner_full", "validate-orion-result.py")
PARTIAL = load("vega_runner_partial", "validate-orion-partial.py")
FIXTURE = load("vega_runner_fixture", "test-orion-result.py")
PARTIAL_FIXTURE = load("vega_runner_partial_fixture", "test-orion-partial.py")


def topology_text(
    config_hash: str = "a" * 64,
    *,
    entries: tuple[str, ...] | None = None,
    summary: str | None = None,
    platform_target: str = "/sys/devices/platform/1100e000.i2c",
    dt_target: str = "/sys/firmware/devicetree/base/i2c@1100e000",
) -> str:
    if entries is None:
        entries = (
            "entry index=1 adapter=i2c-1 link=1 name_valid=1 "
            "canonical=1 "
            "target=/sys/devices/platform/1100e000.i2c/i2c-1 "
            "parent=/sys/devices/platform/1100e000.i2c "
            "parent_match=1 of_canonical=1 "
            "of_target=/sys/firmware/devicetree/base/i2c@1100e000 "
            "of_match=1 match=1",
        )
    if summary is None:
        summary = (
            f"summary entry_count={len(entries)} link_count={len(entries)} "
            f"name_count={len(entries)} canonical_count={len(entries)} "
            "parent_match_count=1 of_canonical_count=1 "
            "of_match_count=1 match_count=1 overflow=0"
        )
    return "\n".join(
        (
            RUNNER.ADAPTER_TOPOLOGY_BEGIN,
            f"contract={RUNNER.ADAPTER_TOPOLOGY_CONTRACT}",
            f"kernel={RUNNER.KERNEL_RELEASE}",
            f"config_sha256={config_hash}",
            "boot_id=00000000-0000-0000-0000-000000000001",
            f"platform_target={platform_target}",
            f"dt_target={dt_target}",
            f"entry_limit={RUNNER.ADAPTER_TOPOLOGY_ENTRY_LIMIT}",
            *entries,
            summary,
            RUNNER.ADAPTER_TOPOLOGY_END,
        )
    )


def valid_capture(config_hash: str = "a" * 64) -> bytes:
    adapter = "i2c-1"
    adapter_debugfs = f"/run/vega-debugfs/i2c/{adapter}"
    gate = {
        "kernel": RUNNER.KERNEL_RELEASE,
        "cmdline": RUNNER.KERNEL_CMDLINE,
        "config_sha256": config_hash,
        "rootfs_type": "rootfs",
        "run_mounts": "0",
        "boot_id_pre": "00000000-0000-0000-0000-000000000001",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "nproc": "8",
        "handoff_state": "ready",
        "i2c6_compatible_sha256": RUNNER.I2C6_COMPATIBLE_SHA256,
        "i2c6_status_pre": RUNNER.I2C_STATUS_PRE,
        "i2c6_adapter": adapter,
        "i2c6_of": "/sys/firmware/devicetree/base/i2c@1100e000",
        "i2c6_clients": "0",
        "i2c_chardev": "absent",
        "keyboard_devices": "1",
        "tty1": "character-device",
        "usb0_address": "42:00:15:19:82:01",
        "usb0_carrier": "1",
        "usb0_operstate": "up",
        "usb0_ipv4_exact": "1",
        "udc_name": "11271000.usb",
        "udc_state": "configured",
        "usb_service_count": "1",
        "usb_ready_count": "1",
        "pre_dmesg_fatal_count": "0",
        "debugfs_mount": "/run/vega-debugfs",
        "debugfs_mount_count": "1",
        "adapter_debugfs": adapter_debugfs,
        "diagnostic_path": adapter_debugfs + "/orion-run-all",
        "diagnostic_mode": "600:0:0",
        "diagnostic_pre": RUNNER.DIAGNOSTIC_STATUS_PRE,
    }
    gate_text = "\n".join(f"{key}={value}" for key, value in gate.items())
    result = FIXTURE.valid_result().decode("ascii").rstrip("\n")
    i2c_status = (
        "handoff=ready probe_attempts=1 init_attempts=4 init_successes=4 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
        "clock_domains=i2c-appm,ap-dma transfer_attempts=9 dma_starts=6 "
        "nonzero_starts=9 irq_count=9 suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    post = {
        "write_rc": "0",
        "vega_final_rc": "0",
        "i2c_status_post_rc": "0",
        "dmesg_rc": "0",
        "boot_id_post": gate["boot_id_pre"],
        "boot_id_post_rc": "0",
        "cpu_online_post": "0-7",
        "cpu_online_post_rc": "0",
        "cpu_offline_post": "8-9",
        "cpu_offline_post_rc": "0",
        "nproc_post": "8",
        "nproc_post_rc": "0",
        "handoff_state_post": "ready",
        "handoff_state_post_rc": "0",
        "usb_carrier_post": "1",
        "usb_carrier_post_rc": "0",
        "usb_operstate_post": "up",
        "usb_operstate_post_rc": "0",
        "udc_state_post": "configured",
        "udc_state_post_rc": "0",
        "ac_status_post_rc": "0",
    }
    post_text = "\n".join(f"{key}={value}" for key, value in post.items())
    log = (
        "[    1.0] GEMINI_ORION_DIAGNOSTIC state=ready one_shot=unused\n"
        "[   10.0] i2c register snapshot dma_tx_mem=0xdeadbeef"
    )
    text = "\n".join(
        (
            "\n".join(RUNNER.expected_usb_envelope(1)),
            topology_text(config_hash),
            "__VEGA_GATE_BEGIN__",
            gate_text,
            RUNNER.FINAL_REVALIDATION_BEGIN,
            *RUNNER.FINAL_REVALIDATION_STEPS,
            RUNNER.FINAL_REVALIDATION_END,
            "__VEGA_GATE_END__",
            "__VEGA_GATE_PASS__",
            "__VEGA_FINAL_BEGIN__",
            result,
            "__VEGA_FINAL_END__",
            "__VEGA_I2C_STATUS_POST_BEGIN__",
            i2c_status,
            "__VEGA_I2C_STATUS_POST_END__",
            "__VEGA_POST_BEGIN__",
            post_text,
            "__VEGA_POST_END__",
            "__VEGA_AC_STATUS_POST_BEGIN__",
            "usb_shell=ready reboot_dispatch=validated privilege=root",
            "__VEGA_AC_STATUS_POST_END__",
            "__VEGA_DMESG_RAW_BEGIN__",
            log,
            "__VEGA_DMESG_RAW_END__",
            "__VEGA_COMPLETE__ write_rc=0 invocation_count=1 "
            "guard_mode=400:0:0 post_capture=unconditional",
            "",
        )
    )
    return text.encode("ascii")


def partial_capture(result: bytes, init_count: int) -> bytes:
    text = valid_capture().decode("ascii")
    final_start = text.index("__VEGA_FINAL_BEGIN__\n") + len(
        "__VEGA_FINAL_BEGIN__\n"
    )
    final_stop = text.index("\n__VEGA_FINAL_END__", final_start)
    text = text[:final_start] + result.decode("ascii").rstrip("\n") + text[final_stop:]
    header = dict(
        token.split("=", 1)
        for token in result.decode("ascii").splitlines()[0].split()
    )
    old_status = (
        "handoff=ready probe_attempts=1 init_attempts=4 init_successes=4 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
        "clock_domains=i2c-appm,ap-dma transfer_attempts=9 dma_starts=6 "
        "nonzero_starts=9 irq_count=9 suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    new_status = (
        f"handoff=ready probe_attempts=1 init_attempts={init_count} "
        f"init_successes={init_count} clock_ungated_checks=1 "
        "clock_gated_checks=1 clock_validation_failures=0 "
        "runtime_pm_link=1 clock_domains=i2c-appm,ap-dma "
        f"transfer_attempts={header['transfer_attempts']} "
        f"dma_starts={header['dma_starts']} "
        f"nonzero_starts={header['nonzero_starts']} "
        f"irq_count={header['irqs']} suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    text = text.replace(old_status, new_status, 1)
    text = text.replace("write_rc=0", "write_rc=1", 2)
    return text.encode("ascii")


def pre_gate_abort_capture(
    reason: str = "i2c6-adapter-count",
    *,
    session_count: int = 1,
    rc: int | None = None,
) -> bytes:
    marker = f"__VEGA_ABORT__ reason={reason}"
    if rc is not None:
        marker += f" rc={rc}"
    body = marker
    if reason in {
        "i2c-adapter-entry-limit",
        "i2c-adapter-link-type",
        "i2c-adapter-name",
        "i2c-adapter-canonical-path",
        "i2c6-adapter-parent-count",
        "i2c6-adapter-of-node-count",
        "i2c6-adapter-count",
    }:
        entries: tuple[str, ...] = ()
        summary = (
            "summary entry_count=0 link_count=0 name_count=0 "
            "canonical_count=0 parent_match_count=0 "
            "of_canonical_count=0 of_match_count=0 "
            "match_count=0 overflow=0"
        )
        if reason == "i2c-adapter-name":
            entries = (
                "entry index=1 adapter=i2c-1 link=1 name_valid=1 "
                "canonical=1 "
                "target=/sys/devices/platform/1100e000.i2c/i2c-1 "
                "parent=/sys/devices/platform/1100e000.i2c "
                "parent_match=1 of_canonical=1 "
                "of_target=/sys/firmware/devicetree/base/i2c@1100e000 "
                "of_match=1 match=1",
                "entry index=2 adapter=i2c-z link=1 name_valid=0 "
                "canonical=0 target=- parent=- parent_match=0 "
                "of_canonical=0 of_target=- of_match=0 match=0",
            )
            summary = (
                "summary entry_count=2 link_count=2 name_count=1 "
                "canonical_count=1 parent_match_count=1 "
                "of_canonical_count=1 of_match_count=1 "
                "match_count=1 overflow=0"
            )
        elif reason == "i2c6-adapter-count":
            entries = (
                "entry index=1 adapter=i2c-1 link=1 name_valid=1 "
                "canonical=1 "
                "target=/sys/devices/platform/1100e000.i2c/i2c-1 "
                "parent=/sys/devices/platform/1100e000.i2c "
                "parent_match=1 of_canonical=1 "
                "of_target=/sys/firmware/devicetree/base/i2c@11007000 "
                "of_match=0 match=0",
                "entry index=2 adapter=i2c-2 link=1 name_valid=1 "
                "canonical=1 "
                "target=/sys/devices/platform/11007000.i2c/i2c-2 "
                "parent=/sys/devices/platform/11007000.i2c "
                "parent_match=0 of_canonical=1 "
                "of_target=/sys/firmware/devicetree/base/i2c@1100e000 "
                "of_match=1 match=0",
            )
            summary = (
                "summary entry_count=2 link_count=2 name_count=2 "
                "canonical_count=2 parent_match_count=1 "
                "of_canonical_count=2 of_match_count=1 "
                "match_count=0 overflow=0"
            )
        body = topology_text(
            entries=entries,
            summary=summary,
        ) + "\n" + marker
    return (
        "\n".join(RUNNER.expected_usb_envelope(session_count))
        + "\n"
        + body
        + "\n"
    ).encode("ascii")


class VegaRunnerContracts(unittest.TestCase):
    def test_runtime_package_validator_is_source_pinned(self) -> None:
        validator = SCRIPT_DIR / "validate-package-vega.py"
        self.assertEqual(
            RUNNER.digest(validator.read_bytes()),
            RUNNER.PACKAGE_VALIDATOR_SHA256,
        )
        self.assertIn(
            "load_source_pinned_module",
            RUNNER.validate_package.__code__.co_names,
        )
        self.assertIn(
            "PACKAGE_VALIDATOR_SHA256",
            RUNNER.validate_package.__code__.co_names,
        )
        module = RUNNER.load_source_pinned_module(
            validator,
            RUNNER.PACKAGE_VALIDATOR_SHA256,
            "Vega package validator",
            "vega_test_package_validator",
        )
        self.assertTrue(callable(module.validate))
        with tempfile.TemporaryDirectory(
            prefix="vega-runner-source-pin."
        ) as raw:
            mutated = pathlib.Path(raw) / validator.name
            mutated.write_bytes(validator.read_bytes() + b"\n# mutation\n")
            with self.assertRaisesRegex(
                RUNNER.ContractError,
                "source-pinned input changed",
            ):
                RUNNER.load_source_pinned_module(
                    mutated,
                    RUNNER.PACKAGE_VALIDATOR_SHA256,
                    "Vega package validator",
                    "vega_test_mutated_package_validator",
                )

    def test_source_pinned_orion_result_validators_load(self) -> None:
        repository = SCRIPT_DIR.parents[2]
        full = RUNNER.load_orion_result_validator(
            repository,
            "validate-orion-result.py",
            RUNNER.co.ORION_RESULT_VALIDATOR_SHA256,
            "vega_test_full_validator",
        )
        partial = RUNNER.load_orion_result_validator(
            repository,
            "validate-orion-partial.py",
            RUNNER.co.ORION_PARTIAL_VALIDATOR_SHA256,
            "vega_test_partial_validator",
        )
        self.assertTrue(callable(full.validate_text))
        self.assertTrue(callable(partial.validate_partial))

    def test_remote_program_resolves_only_placeholders(self) -> None:
        config_hash = "a" * 64
        program = RUNNER.build_remote_program(config_hash).decode("ascii")
        self.assertEqual(
            collections.Counter(RUNNER.REMOTE_TOKEN.findall(program)),
            RUNNER.RUNTIME_TOKEN_COUNTS,
        )
        self.assertIn(config_hash, program)
        self.assertNotIn("__VEGA_CONFIG_SHA256__", program)

        original = RUNNER.REMOTE_TEMPLATE
        try:
            RUNNER.REMOTE_TEMPLATE = original + "\n__VEGA_UNKNOWN__\n"
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.build_remote_program(config_hash)
            RUNNER.REMOTE_TEMPLATE = original + "\n__VEGA_KERNEL__\n"
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.build_remote_program(config_hash)
        finally:
            RUNNER.REMOTE_TEMPLATE = original

    def test_transport_is_raw_outer_shell_without_nested_shell(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        self.assertTrue(source.startswith("PS1=; PS2=; export PS1 PS2\nset -eu\n"))
        self.assertNotIn("exec /bin/busybox sh", source)
        self.assertNotIn("sh -s", source)
        self.assertNotIn("<<", source)
        self.assertNotIn("__VEGA_REMOTE__", source)
        self.assertTrue(source.endswith("exit 0\n"))
        self.assertLess(
            source.rindex("completion_emitted=yes"),
            source.rindex("printf '__VEGA_COMPLETE__"),
        )
        syntax = subprocess.run(
            ["/bin/sh", "-n"],
            input=source.encode("ascii"),
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr.decode())

    def test_unmarked_pregate_shell_failure_is_attributed_once(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="vega-pregate-exit."
        ) as raw:
            root = pathlib.Path(raw)
            guard = root / "invocation-guard"
            write = root / "diagnostic-write"
            simulated = RUNNER.REMOTE_TEMPLATE.replace(
                "guard_path=/run/vega-run-all.invoked",
                f"guard_path={guard}",
                1,
            ).replace(
                "printf 'run\\n' >\"$diag\"",
                f"printf 'run\\n' >{write}",
                1,
            ).replace(
                "trap on_signal HUP INT TERM PIPE\n",
                "trap on_signal HUP INT TERM PIPE\n"
                "forced_probe=$(false)\n",
                1,
            )
            result = subprocess.run(
                ["/bin/sh"],
                input=simulated.encode("ascii"),
                capture_output=True,
                check=False,
                timeout=5,
            )
            self.assertEqual(result.returncode, 1)
            marker = "__VEGA_ABORT__ reason=unexpected-shell-exit rc=1"
            output = result.stdout.decode("ascii")
            self.assertEqual(output.splitlines().count(marker), 1)
            self.assertEqual(output.count("__VEGA_ABORT__"), 1)
            self.assertEqual(
                output.count("__VEGA_ABORT__")
                + output.count("__VEGA_COMPLETE__"),
                1,
            )
            self.assertFalse(guard.exists())
            self.assertFalse(write.exists())

    def test_explicit_abort_suppresses_unexpected_exit_marker(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        preamble, _gates = source.split(
            'require_equal "$(/bin/busybox id -u)" 0 not-root',
            1,
        )
        result = subprocess.run(
            ["/bin/sh"],
            input=(preamble + "abort simulated-gate\n").encode("ascii"),
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 90)
        output = result.stdout.decode("ascii")
        self.assertEqual(
            output.splitlines().count(
                "__VEGA_ABORT__ reason=simulated-gate"
            ),
            1,
        )
        self.assertNotIn("unexpected-shell-exit", output)
        self.assertEqual(
            output.count("__VEGA_ABORT__")
            + output.count("__VEGA_COMPLETE__"),
            1,
        )

    def test_successful_completion_suppresses_exit_marker(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        preamble, _gates = source.split(
            'require_equal "$(/bin/busybox id -u)" 0 not-root',
            1,
        )
        simulated = preamble + (
            "completion_emitted=yes\n"
            "printf '__VEGA_COMPLETE__ simulated\\n'\n"
            "exit 0\n"
        )
        result = subprocess.run(
            ["/bin/sh"],
            input=simulated.encode("ascii"),
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        output = result.stdout.decode("ascii")
        self.assertEqual(
            output.splitlines().count("__VEGA_COMPLETE__ simulated"),
            1,
        )
        self.assertNotIn("__VEGA_ABORT__", output)
        self.assertEqual(
            output.count("__VEGA_ABORT__")
            + output.count("__VEGA_COMPLETE__"),
            1,
        )

    def test_signal_after_completion_emission_cannot_add_abort(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        preamble, _gates = source.split(
            'require_equal "$(/bin/busybox id -u)" 0 not-root',
            1,
        )
        simulated = preamble + (
            "completion_emitted=yes\n"
            "printf '__VEGA_COMPLETE__ simulated\\n'\n"
            "kill -TERM $$\n"
            "exit 99\n"
        )
        result = subprocess.run(
            ["/bin/sh"],
            input=simulated.encode("ascii"),
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 91)
        output = result.stdout.decode("ascii")
        self.assertEqual(
            output.splitlines().count("__VEGA_COMPLETE__ simulated"),
            1,
        )
        self.assertNotIn("__VEGA_ABORT__", output)
        self.assertEqual(
            output.count("__VEGA_ABORT__")
            + output.count("__VEGA_COMPLETE__"),
            1,
        )

    def test_unbound_i2c6_status_aborts_before_debugfs_or_write(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        ordered = (
            '[ -d "$i2c6" ] || abort i2c6-platform-device-absent',
            '[ -L "$i2c6/driver" ] || abort i2c6-driver-unbound',
            '[ -r "$i2c6/handoff_status" ] || abort i2c6-status-absent',
            "abort i2c6-status-read",
            'require_equal "$i2c_status_pre" '
            '"__VEGA_I2C_STATUS_PRE__" i2c6-pre-exact',
            '/bin/busybox mkdir -m 0700 "$debugfs_root"',
            "printf 'run\\n' >\"$diag\"",
        )
        positions = [source.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_i2c6_adapter_uses_exact_canonical_parent_identity(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        RUNNER.require_canonical_adapter_mapping(source)
        self.assertIn(
            '/bin/busybox readlink -f "$i2c6" 2>/dev/null',
            source,
        )
        self.assertIn(
            '/bin/busybox readlink -f "$adapter" 2>/dev/null',
            source,
        )
        self.assertIn(
            "adapter_parent=${adapter_target%/*}",
            source,
        )
        self.assertIn(
            'if [ "$entry_parent" = "$i2c6_target" ]; then',
            source,
        )
        self.assertIn(
            '[ -L "$adapter/of_node" ]',
            source,
        )
        self.assertIn(
            'elif [ "$child_parent" = "$adapter_target_selected" ]; then',
            source,
        )
        self.assertIn(
            '"$i2c_status_pre" "$adapter_name" "$dt_i2c6"',
            source,
        )
        for forbidden in (
            '"$adapter/device"',
            '"$adapter/device/of_node"',
            'adapter_number=${adapter_name#i2c-}',
            "*/i2c@1100e000",
            'case "$target" in',
            "adapter_of=",
        ):
            self.assertNotIn(forbidden, source)

        mutations = (
            source.replace(
                '/bin/busybox readlink -f "$adapter" 2>/dev/null',
                '/bin/busybox readlink -f "$adapter/device" 2>/dev/null',
                1,
            ),
            source.replace(
                "adapter_parent=${adapter_target%/*}",
                "adapter_parent=${adapter_target##*/}",
                1,
            ),
            source.replace(
                'if [ "$entry_parent" = "$i2c6_target" ]; then',
                'if [ "${entry_parent##*/}" = "1100e000.i2c" ]; then',
                1,
            ),
            source.replace(
                '"$adapter/of_node"',
                '"$adapter/device/of_node"',
                1,
            ),
            source.replace(
                'if [ "$entry_parent_match" -eq 1 ] &&\n'
                '\t   [ "$entry_of_match" -eq 1 ]; then',
                'if [ "$entry_parent_match" -eq 1 ] ||\n'
                '\t   [ "$entry_of_match" -eq 1 ]; then',
                1,
            ),
            source.replace(
                'if [ "$repeat_adapter_parent" = \\\n'
                '\t\t\t     "$repeat_i2c6_target" ]; then',
                'if [ -n "$repeat_adapter_parent" ]; then',
                1,
            ),
            source.replace(
                'if [ "$repeat_adapter_of_target" = \\\n'
                '\t\t\t\t\t     "$repeat_dt_i2c6_target" ]; then',
                'if [ -n "$repeat_adapter_of_target" ]; then',
                1,
            ),
            source.replace(
                'if [ "$repeat_adapter_of_target" = \\\n'
                '\t\t\t\t\t     "$repeat_dt_i2c6_target" ]; then',
                'if [ "$repeat_entry_parent_match" -eq 1 ] &&\n'
                '\t\t\t\t\t   [ "$repeat_adapter_of_target" = \\\n'
                '\t\t\t\t\t     "$repeat_dt_i2c6_target" ]; then',
                1,
            ),
            source.replace(
                '\t\t\tfi\n'
                '\t\t\tif [ -L "$repeat_adapter/of_node" ]; then',
                '\t\t\t\tif [ -L "$repeat_adapter/of_node" ]; then',
                1,
            ),
            source.replace(
                'require_equal "$repeat_of_match_count" 1 \\\n'
                "\t\ti2c6-adapter-repeat-of-node-count",
                'require_equal "$repeat_match_count" 1 \\\n'
                "\t\ti2c6-adapter-repeat-of-node-count",
                1,
            ),
            source.replace(
                'elif [ "$child_parent" = "$adapter_target_selected" ]; then',
                'elif [ "${child##*-}" = "${adapter_name#i2c-}" ]; then',
                1,
            ),
            source.replace(
                "printf '\\n__VEGA_ADAPTER_TOPOLOGY_BEGIN__\\n'",
                "printf '__VEGA_ADAPTER_TOPOLOGY_BEGIN__\\n'",
                1,
            ),
            source.replace(
                '"$i2c_status_pre" "$adapter_name" "$dt_i2c6"',
                '"$i2c_status_pre" "$adapter_name" "$adapter_parent"',
                1,
            ),
            source.replace(
                "LC_ALL=C\nLANG=C\nexport LC_ALL LANG",
                "LC_ALL=en_US.UTF-8\nLANG=en_US.UTF-8\n"
                "export LC_ALL LANG",
                1,
            ),
        )
        original = RUNNER.REMOTE_TEMPLATE
        try:
            for index, mutated in enumerate(mutations, 1):
                with self.subTest(mutation=index):
                    self.assertNotEqual(mutated, source)
                    RUNNER.REMOTE_TEMPLATE = mutated
                    with self.assertRaisesRegex(
                        RUNNER.ContractError,
                        "adapter mapping",
                    ):
                        RUNNER.build_remote_program("a" * 64)
        finally:
            RUNNER.REMOTE_TEMPLATE = original

    def test_final_prewrite_identity_checks_are_adjacent_to_write(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        ordered = (
            "__VEGA_FINAL_REVALIDATION_BEGIN__",
            "\nverify_selected_identity\n",
            "step=topology",
            "adapter-debugfs-repeat-path",
            "diagnostic-repeat-path",
            "adapter-debugfs-repeat-type",
            "diagnostic-repeat-type",
            "diagnostic-repeat-mode",
            "diagnostic-repeat-read",
            "diagnostic-repeat-exact",
            "i2c6-status-repeat-absent",
            "i2c6-status-repeat-read",
            "i2c6-status-repeat-exact",
            "step=i2c6-status",
            "__VEGA_FINAL_REVALIDATION_END__",
            "__VEGA_GATE_END__\\n__VEGA_GATE_PASS__",
            '( set -C; : >"$guard_path" )',
            "printf 'run\\n' >\"$diag\"",
        )
        positions = [source.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))

        mutations = (
            source.replace(
                "\nverify_selected_identity\n",
                "\nverify_selected_identity\n"
                'diag="$debugfs_root/i2c/i2c-9/orion-run-all"\n',
                1,
            ),
            source.replace(
                '[ -f "$diag" ] && [ ! -L "$diag" ] || '
                "abort diagnostic-repeat-type\n",
                "",
                1,
            ),
            source.replace(
                "vega_status_repeat=$(\n"
                '\t/bin/busybox cat "$diag" 2>/dev/null\n'
                ") || abort diagnostic-repeat-read\n",
                "",
                1,
            ),
            source.replace(
                "i2c_status_repeat=$(\n"
                '\t/bin/busybox cat "$i2c6/handoff_status" 2>/dev/null\n'
                ") || abort i2c6-status-repeat-read\n",
                "",
                1,
            ),
            source.replace(
                "printf 'step=diagnostic-status\\n'\n"
                '[ -r "$i2c6/handoff_status" ]',
                "printf 'step=diagnostic-status\\n'\n"
                'diag="$debugfs_root/i2c/i2c-9/orion-run-all"\n'
                '[ -r "$i2c6/handoff_status" ]',
                1,
            ),
            source.replace(
                "printf '__VEGA_FINAL_REVALIDATION_END__\\n'\n\n"
                "printf '__VEGA_GATE_END__\\n__VEGA_GATE_PASS__\\n'",
                "printf '__VEGA_FINAL_REVALIDATION_END__\\n'\n"
                'diag="$debugfs_root/i2c/i2c-9/orion-run-all"\n'
                "printf '__VEGA_GATE_END__\\n__VEGA_GATE_PASS__\\n'",
                1,
            ),
            source.replace(
                "printf '__VEGA_GATE_END__\\n__VEGA_GATE_PASS__\\n'\n"
                '( set -C; : >"$guard_path" )',
                "printf '__VEGA_GATE_END__\\n__VEGA_GATE_PASS__\\n'\n"
                'diag="$debugfs_root/i2c/i2c-9/orion-run-all"\n'
                '( set -C; : >"$guard_path" )',
                1,
            ),
            source.replace(
                "set +e\nprintf 'run\\n' >\"$diag\"",
                "set +e\n"
                'diag="$debugfs_root/i2c/i2c-9/orion-run-all"\n'
                "printf 'run\\n' >\"$diag\"",
                1,
            ),
        )
        original = RUNNER.REMOTE_TEMPLATE
        try:
            for index, mutated in enumerate(mutations, 1):
                with self.subTest(mutation=index):
                    self.assertNotEqual(mutated, source)
                    RUNNER.REMOTE_TEMPLATE = mutated
                    with self.assertRaisesRegex(
                        RUNNER.ContractError,
                        "identity revalidation or write adjacency",
                    ):
                        RUNNER.build_remote_program("a" * 64)
        finally:
            RUNNER.REMOTE_TEMPLATE = original

    def test_synthetic_sysfs_uses_adapter_target_direct_parent(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="vega-synthetic-sysfs."
        ) as raw:
            root = pathlib.Path(raw)
            platform_target = (
                root / "sys/devices/platform/1100e000.i2c"
            )
            adapter_target = platform_target / "i2c-1"
            dt_target = (
                root / "sys/firmware/devicetree/base/i2c@1100e000"
            )
            adapter_target.mkdir(parents=True)
            dt_target.mkdir(parents=True)
            (adapter_target / "of_node").symlink_to(
                dt_target,
                target_is_directory=True,
            )
            platform_bus = root / "sys/bus/platform/devices"
            i2c_bus = root / "sys/bus/i2c/devices"
            platform_bus.mkdir(parents=True)
            i2c_bus.mkdir(parents=True)
            platform_link = platform_bus / "1100e000.i2c"
            adapter_link = i2c_bus / "i2c-1"
            platform_link.symlink_to(
                platform_target,
                target_is_directory=True,
            )
            adapter_link.symlink_to(
                adapter_target,
                target_is_directory=True,
            )

            canonical_platform = platform_link.resolve(strict=True)
            canonical_adapter = adapter_link.resolve(strict=True)
            canonical_dt = (adapter_link / "of_node").resolve(strict=True)
            self.assertFalse((adapter_link / "device").exists())
            self.assertEqual(canonical_adapter.parent, canonical_platform)
            self.assertEqual(canonical_dt, dt_target.resolve(strict=True))
            entry = (
                "entry index=1 adapter=i2c-1 link=1 name_valid=1 "
                f"canonical=1 target={canonical_adapter} "
                f"parent={canonical_adapter.parent} parent_match=1 "
                f"of_canonical=1 of_target={canonical_dt} "
                "of_match=1 match=1"
            )
            body = topology_text(
                entries=(entry,),
                platform_target=str(canonical_platform),
                dt_target=str(canonical_dt),
            ) + "\n__VEGA_GATE_BEGIN__\n"
            topology, remainder = RUNNER.parse_adapter_topology(
                body,
                "a" * 64,
            )
            self.assertIsNotNone(topology)
            assert topology is not None
            self.assertTrue(RUNNER.topology_is_ready(topology))
            self.assertEqual(topology.matching_adapters, ("i2c-1",))
            self.assertEqual(remainder, "__VEGA_GATE_BEGIN__\n")

    def test_topology_rejects_noise_counts_and_malformed_paths(self) -> None:
        body = topology_text() + "\n__VEGA_GATE_BEGIN__\n"
        mutations = (
            body.replace(
                "\nsummary entry_count=",
                "\nunexpected=topology-noise\nsummary entry_count=",
                1,
            ),
            body.replace("canonical_count=1", "canonical_count=0", 1),
            body.replace(
                "target=/sys/devices/platform/1100e000.i2c/i2c-1",
                "target=/",
                1,
            ),
            body.replace(
                "target=/sys/devices/platform/1100e000.i2c/i2c-1",
                "target=/sys/devices/platform/./1100e000.i2c/i2c-1",
                1,
            ),
            body.replace(
                "target=/sys/devices/platform/1100e000.i2c/i2c-1",
                "target=/sys/devices/platform/../platform/"
                "1100e000.i2c/i2c-1",
                1,
            ),
            body.replace(
                "parent=/sys/devices/platform/1100e000.i2c",
                "parent=/sys/devices/platform",
                1,
            ),
            body.replace("parent_match=1", "parent_match=0", 1),
            body.replace("of_match=1 match=1", "of_match=1 match=0", 1),
            body.replace(
                "adapter=i2c-1 link=1",
                "link=1 adapter=i2c-1",
                1,
            ),
            body.replace("overflow=0", "overflow=1", 1),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.parse_adapter_topology(
                        mutated,
                        "a" * 64,
                    )

    def test_safe_nonnumeric_adapter_abort_is_exactly_attributed(
        self,
    ) -> None:
        capture = pre_gate_abort_capture("i2c-adapter-name")
        envelope = (
            "\n".join(RUNNER.expected_usb_envelope(1)) + "\n"
        ).encode("ascii")
        self.assertTrue(capture.startswith(envelope))
        topology, remainder = RUNNER.parse_adapter_topology(
            capture[len(envelope) :].decode("ascii"),
            "a" * 64,
        )
        self.assertIsNotNone(topology)
        assert topology is not None
        self.assertEqual(topology.entry_count, 2)
        self.assertEqual(topology.name_count, 1)
        self.assertFalse(RUNNER.topology_is_ready(topology))
        self.assertEqual(
            remainder,
            "__VEGA_ABORT__ reason=i2c-adapter-name\n",
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega pre-gate aborted: i2c-adapter-name$",
        ):
            RUNNER.validate_capture(
                capture,
                "a" * 64,
                object(),
                object(),
            )

        bad_bit = capture.replace(
            b"adapter=i2c-z link=1 name_valid=0",
            b"adapter=i2c-z link=1 name_valid=1",
            1,
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            "name-valid bit changed",
        ):
            RUNNER.validate_capture(
                bad_bit,
                "a" * 64,
                object(),
                object(),
            )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega pre-gate aborted: i2c-adapter-token$",
        ):
            RUNNER.validate_capture(
                pre_gate_abort_capture("i2c-adapter-token"),
                "a" * 64,
                object(),
                object(),
            )

    def test_adapter_tokens_are_bounded_safe_and_c_ordered(self) -> None:
        body = topology_text() + "\n__VEGA_GATE_BEGIN__\n"
        unsafe_tokens = (
            "i2c-.",
            "i2c-..",
            "i2c-foo.bar",
            "i2c-foo/bar",
            "i2c-foo:bar",
            "i2c-foo bar",
            "i2c-\x01foo",
            "i2c-" + "1" * 61,
        )
        for token in unsafe_tokens:
            with self.subTest(token=repr(token)):
                mutated = body.replace(
                    "adapter=i2c-1",
                    f"adapter={token}",
                    1,
                )
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.parse_adapter_topology(
                        mutated,
                        "a" * 64,
                    )

        ordered_entries = (
            "entry index=1 adapter=i2c-10 link=0 name_valid=1 "
            "canonical=0 target=- parent=- parent_match=0 "
            "of_canonical=0 of_target=- of_match=0 match=0",
            "entry index=2 adapter=i2c-2 link=0 name_valid=1 "
            "canonical=0 target=- parent=- parent_match=0 "
            "of_canonical=0 of_target=- of_match=0 match=0",
        )
        summary = (
            "summary entry_count=2 link_count=0 name_count=2 "
            "canonical_count=0 parent_match_count=0 "
            "of_canonical_count=0 of_match_count=0 "
            "match_count=0 overflow=0"
        )
        ordered_body = topology_text(
            entries=ordered_entries,
            summary=summary,
        ) + "\n__VEGA_ABORT__ reason=i2c-adapter-link-type\n"
        topology, _remainder = RUNNER.parse_adapter_topology(
            ordered_body,
            "a" * 64,
        )
        self.assertIsNotNone(topology)

        reversed_names = (
            ordered_entries[0].replace("adapter=i2c-10", "adapter=i2c-2"),
            ordered_entries[1].replace("adapter=i2c-2", "adapter=i2c-10"),
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            "C-locale order",
        ):
            RUNNER.parse_adapter_topology(
                topology_text(
                    entries=reversed_names,
                    summary=summary,
                )
                + "\n__VEGA_ABORT__ reason=i2c-adapter-link-type\n",
                "a" * 64,
            )
        duplicate = (
            ordered_entries[0],
            ordered_entries[0].replace("index=1", "index=2"),
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            "duplicated an adapter",
        ):
            RUNNER.parse_adapter_topology(
                topology_text(
                    entries=duplicate,
                    summary=summary,
                )
                + "\n__VEGA_ABORT__ reason=i2c-adapter-link-type\n",
                "a" * 64,
            )

    def test_topology_framing_is_exact_on_success_and_abort(self) -> None:
        success = valid_capture()
        abort = pre_gate_abort_capture()
        mutations = (
            success.replace(
                b"__VEGA_ADAPTER_TOPOLOGY_END__\n__VEGA_GATE_BEGIN__",
                b"__VEGA_ADAPTER_TOPOLOGY_END__\nnoise=1\n"
                b"__VEGA_GATE_BEGIN__",
                1,
            ),
            abort.replace(
                b"__VEGA_ADAPTER_TOPOLOGY_END__\n__VEGA_ABORT__",
                b"__VEGA_ADAPTER_TOPOLOGY_END__\nnoise=1\n"
                b"__VEGA_ABORT__",
                1,
            ),
            success.replace(
                b"GEMINI-AC-USB# \n__VEGA_ADAPTER_TOPOLOGY_BEGIN__",
                b"GEMINI-AC-USB# __VEGA_ADAPTER_TOPOLOGY_BEGIN__",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        FULL,
                        PARTIAL,
                    )

    def test_exact_write_then_unconditional_capture_order(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        ordered = (
            "set +e\nprintf 'run\\n' >\"$diag\"\nwrite_rc=$?",
            'vega_final=$(/bin/busybox cat "$diag" 2>&1)',
            'i2c_status_post=$(/bin/busybox cat "$i2c6/handoff_status" 2>&1)',
            "\nkernel_log=$(/bin/busybox dmesg 2>&1)",
            "__VEGA_FINAL_BEGIN__",
            "__VEGA_I2C_STATUS_POST_BEGIN__",
            "__VEGA_DMESG_RAW_BEGIN__",
            "__VEGA_COMPLETE__",
        )
        positions = [source.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("printf 'run\\n' >\"$diag\""), 1)
        self.assertIn("post_capture=unconditional", source)

    def test_prewrite_fatal_gate_precedes_guard_and_write(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        ordered = (
            "pre_kernel_log=$(/bin/busybox dmesg 2>&1)",
            'require_equal "$pre_dmesg_fatal_count" 0 pre-dmesg-fatal',
            '( set -C; : >"$guard_path" )',
            "printf 'run\\n' >\"$diag\"",
        )
        positions = [source.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("pre_dmesg_fatal_count=0", source)

    def test_write_target_is_exact_adapter_debugfs_child(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        self.assertIn(
            'adapter_debugfs="$debugfs_root/i2c/$adapter_name"', source
        )
        self.assertIn(
            'diag="$adapter_debugfs/orion-run-all"', source
        )
        self.assertNotIn('find "$debugfs_root"', source)

    def test_raw_log_is_private_and_not_sanitized(self) -> None:
        source = RUNNER_PATH.read_text()
        self.assertIn("The transcript's dmesg section may contain DMA addresses", source)
        self.assertIn("raw_dmesg_address_lines=private-not-copied", source)
        self.assertNotIn("*log.splitlines()", source)

    def test_valid_capture_sanitizes_address_bearing_log(self) -> None:
        classification, result, sanitized = RUNNER.validate_capture(
            valid_capture(), "a" * 64, FULL, PARTIAL
        )
        self.assertEqual(classification, "complete-success")
        self.assertEqual(result, FIXTURE.valid_result())
        self.assertNotIn("deadbeef", sanitized)
        self.assertNotIn("dma_tx_mem", sanitized)
        self.assertIn("raw_dmesg_address_lines=private-not-copied", sanitized)

    def test_capture_requires_exact_usb_prelude_and_envelope(self) -> None:
        capture = valid_capture()
        one_session = "\n".join(
            RUNNER.expected_usb_envelope(1)
        ).encode("ascii")
        two_sessions = "\n".join(
            RUNNER.expected_usb_envelope(2)
        ).encode("ascii")
        mutations = (
            b"unexpected-before-banner\n" + capture,
            capture.replace(
                b"Direct USB link only: device 10.15.19.82/24, TCP port 2323.",
                b"changed service prelude",
                1,
            ),
            capture.replace(
                b"GEMINI-AC-USB# \n__VEGA_ADAPTER_TOPOLOGY_BEGIN__",
                b"GEMINI-AC-USB# \nunframed-before-topology\n"
                b"__VEGA_ADAPTER_TOPOLOGY_BEGIN__",
                1,
            ),
            capture.replace(one_session, two_sessions, 1),
            capture + b"unframed-after-complete\n",
            capture + b" \n",
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        FULL,
                        PARTIAL,
                    )
        classification, _result, _sanitized = RUNNER.validate_capture(
            capture + b"\n\n",
            "a" * 64,
            FULL,
            PARTIAL,
        )
        self.assertEqual(classification, "complete-success")

    def test_success_capture_rejects_every_unframed_boundary(self) -> None:
        capture = valid_capture()
        boundaries = (
            (b"__VEGA_GATE_END__", b"__VEGA_GATE_PASS__"),
            (b"__VEGA_GATE_PASS__", b"__VEGA_FINAL_BEGIN__"),
            (
                b"__VEGA_FINAL_END__",
                b"__VEGA_I2C_STATUS_POST_BEGIN__",
            ),
            (
                b"__VEGA_I2C_STATUS_POST_END__",
                b"__VEGA_POST_BEGIN__",
            ),
            (
                b"__VEGA_POST_END__",
                b"__VEGA_AC_STATUS_POST_BEGIN__",
            ),
            (
                b"__VEGA_AC_STATUS_POST_END__",
                b"__VEGA_DMESG_RAW_BEGIN__",
            ),
            (b"__VEGA_DMESG_RAW_END__", b"__VEGA_COMPLETE__"),
        )
        for before, after in boundaries:
            with self.subTest(before=before, after=after):
                canonical = before + b"\n" + after
                mutated = capture.replace(
                    canonical,
                    before + b"\nunframed=unexpected\n" + after,
                    1,
                )
                self.assertNotEqual(mutated, capture)
                with self.assertRaisesRegex(
                    RUNNER.ContractError,
                    "success transcript framing changed",
                ):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        FULL,
                        PARTIAL,
                    )

    def test_success_framing_preserves_raw_section_contents(self) -> None:
        text = valid_capture().decode("ascii")
        text = text.replace(
            "__VEGA_AC_STATUS_POST_BEGIN__\n",
            "__VEGA_AC_STATUS_POST_BEGIN__\n"
            "opaque AC status payload with spaces\n\n",
            1,
        )
        text = text.replace(
            "__VEGA_DMESG_RAW_BEGIN__\n",
            "__VEGA_DMESG_RAW_BEGIN__\n"
            "[   10.1] opaque raw dmesg payload=0xcafef00d\n\n",
            1,
        )
        RUNNER.validate_success_transcript_framing(text)

    def test_structured_post_rejects_extra_field(self) -> None:
        capture = valid_capture().replace(
            b"\n__VEGA_POST_END__",
            b"\nunexpected_extra=1\n__VEGA_POST_END__",
            1,
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            "post-run field inventory changed",
        ):
            RUNNER.validate_capture(
                capture,
                "a" * 64,
                FULL,
                PARTIAL,
            )

    def test_captured_pregate_abort_reports_exact_reason_and_fails(self) -> None:
        capture = pre_gate_abort_capture()
        never_validate = object()
        self.assertEqual(len(capture.splitlines()), 30)
        self.assertEqual(
            capture.splitlines().count(
                b"__VEGA_ADAPTER_TOPOLOGY_BEGIN__"
            ),
            1,
        )
        self.assertEqual(
            capture.splitlines()[-1],
            b"__VEGA_ABORT__ reason=i2c6-adapter-count",
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega pre-gate aborted: i2c6-adapter-count$",
        ):
            RUNNER.validate_capture(
                capture,
                "a" * 64,
                never_validate,
                never_validate,
            )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega pre-gate aborted: unexpected-shell-exit$",
        ):
            RUNNER.validate_capture(
                pre_gate_abort_capture(
                    "unexpected-shell-exit",
                    rc=1,
                ),
                "a" * 64,
                never_validate,
                never_validate,
            )

        mutations = (
            b"unframed\n" + capture,
            capture + b"unframed-after-abort\n",
            capture.replace(
                b"reason=i2c6-adapter-count",
                b"reason=i2c6-adapter-count extra=1",
                1,
            ),
            capture.replace(
                b"reason=i2c6-adapter-count",
                b"reason=I2C6-adapter-count",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        never_validate,
                        never_validate,
                    )

    def test_final_revalidation_abort_is_attributed_without_gate_pass(
        self,
    ) -> None:
        prefix, separator, _remainder = valid_capture().partition(
            (RUNNER.FINAL_REVALIDATION_BEGIN + "\n").encode("ascii")
        )
        self.assertTrue(separator)
        prefix += separator
        prefix += (
            "\n".join(RUNNER.FINAL_REVALIDATION_STEPS[:4]) + "\n"
        ).encode("ascii")
        abort = (
            prefix
            + b"__VEGA_ABORT__ reason=diagnostic-repeat-exact\n"
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega gate aborted: diagnostic-repeat-exact$",
        ):
            RUNNER.validate_capture(
                abort,
                "a" * 64,
                object(),
                object(),
            )

        misleading_pass = (
            prefix
            + b"__VEGA_GATE_PASS__\n"
            + b"__VEGA_ABORT__ reason=diagnostic-repeat-exact\n"
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^aborted Vega gate claimed completion$",
        ):
            RUNNER.validate_capture(
                misleading_pass,
                "a" * 64,
                object(),
                object(),
            )

        stage_zero_prefix, separator, _remainder = valid_capture().partition(
            (RUNNER.FINAL_REVALIDATION_BEGIN + "\n").encode("ascii")
        )
        self.assertTrue(separator)
        stage_zero = (
            stage_zero_prefix
            + separator
            + b"__VEGA_ABORT__ reason=i2c6-platform-repeat-link\n"
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega gate aborted: i2c6-platform-repeat-link$",
        ):
            RUNNER.validate_capture(
                stage_zero,
                "a" * 64,
                object(),
                object(),
            )

        unexpected = (
            prefix
            + b"__VEGA_ABORT__ reason=unexpected-shell-exit rc=1\n"
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega gate aborted: unexpected-shell-exit$",
        ):
            RUNNER.validate_capture(
                unexpected,
                "a" * 64,
                object(),
                object(),
            )

        gate_kernel = f"kernel={RUNNER.KERNEL_RELEASE}\n".encode("ascii")
        gate_cmdline = f"cmdline={RUNNER.KERNEL_CMDLINE}\n".encode("ascii")
        malformed = (
            abort.replace(
                b"step=diagnostic-type\nstep=diagnostic-mode\n",
                b"step=diagnostic-mode\nstep=diagnostic-type\n",
                1,
            ),
            abort.replace(
                b"step=diagnostic-mode\n__VEGA_ABORT__",
                b"step=diagnostic-mode\nstep=diagnostic-mode\n"
                b"__VEGA_ABORT__",
                1,
            ),
            abort.replace(b"step=diagnostic-type\n", b"", 1),
            abort.replace(
                b"step=diagnostic-mode\n__VEGA_ABORT__",
                b"step=diagnostic-mode\nnoise=1\n__VEGA_ABORT__",
                1,
            ),
            abort.replace(gate_kernel, b"", 1),
            abort.replace(
                gate_kernel + gate_cmdline,
                gate_cmdline + gate_kernel,
                1,
            ),
            abort.replace(
                b"run_mounts=0\n",
                b"run_mounts=0\nrun_mounts=0\n",
                1,
            ),
            abort.replace(
                (RUNNER.FINAL_REVALIDATION_BEGIN + "\n").encode("ascii"),
                b"noise=1\n"
                + (RUNNER.FINAL_REVALIDATION_BEGIN + "\n").encode("ascii"),
                1,
            ),
            abort.replace(
                b"reason=diagnostic-repeat-exact",
                b"reason=diagnostic-repeat-mode",
                1,
            ),
            unexpected.replace(
                b"step=diagnostic-mode\n__VEGA_ABORT__",
                b"step=diagnostic-mode\nnoise=1\n__VEGA_ABORT__",
                1,
            ),
        )
        for index, mutated in enumerate(malformed, 1):
            with self.subTest(mutation=index):
                self.assertNotEqual(mutated, abort)
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        object(),
                        object(),
                    )

    def test_final_revalidation_success_frame_is_exact(self) -> None:
        capture = valid_capture()
        begin = (RUNNER.FINAL_REVALIDATION_BEGIN + "\n").encode("ascii")
        end = (RUNNER.FINAL_REVALIDATION_END + "\n").encode("ascii")
        step_topology = b"step=topology\n"
        step_path = b"step=diagnostic-path\n"
        step_type = b"step=diagnostic-type\n"
        gate_kernel = f"kernel={RUNNER.KERNEL_RELEASE}\n".encode("ascii")
        gate_cmdline = f"cmdline={RUNNER.KERNEL_CMDLINE}\n".encode("ascii")
        mutations = (
            capture.replace(
                step_path,
                step_path + b"noise=1\n",
                1,
            ),
            capture.replace(step_path, b"", 1),
            capture.replace(step_path, step_path + step_path, 1),
            capture.replace(
                step_path + step_type,
                step_type + step_path,
                1,
            ),
            capture.replace(begin, begin + begin, 1),
            capture.replace(begin, b"", 1),
            capture.replace(end, end + end, 1),
            capture.replace(end, b"", 1),
            capture.replace(
                step_topology,
                step_topology + end,
                1,
            ),
            capture.replace(
                gate_kernel + gate_cmdline,
                gate_cmdline + gate_kernel,
                1,
            ),
            capture.replace(
                b"__VEGA_GATE_BEGIN__\n",
                b"__VEGA_GATE_BEGIN__\n\n",
                1,
            ),
            capture.replace(
                (RUNNER.FINAL_REVALIDATION_END + "\n").encode("ascii")
                + b"__VEGA_GATE_END__",
                (RUNNER.FINAL_REVALIDATION_END + "\n\n").encode("ascii")
                + b"__VEGA_GATE_END__",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                self.assertNotEqual(mutated, capture)
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        FULL,
                        PARTIAL,
                    )

    def test_downstream_abort_requires_mapping_ready_topology(self) -> None:
        nonready = pre_gate_abort_capture().replace(
            b"reason=i2c6-adapter-count",
            b"reason=i2c-child-link-type",
            1,
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^Vega downstream abort contradicts non-ready "
            r"adapter topology$",
        ):
            RUNNER.validate_capture(
                nonready,
                "a" * 64,
                object(),
                object(),
            )

        unexpected_exit = pre_gate_abort_capture().replace(
            b"reason=i2c6-adapter-count",
            b"reason=unexpected-shell-exit rc=1",
            1,
        )
        with self.assertRaisesRegex(
            RUNNER.ContractError,
            r"^remote Vega pre-gate aborted: unexpected-shell-exit$",
        ):
            RUNNER.validate_capture(
                unexpected_exit,
                "a" * 64,
                object(),
                object(),
            )

    def test_pregate_abort_requires_canonical_spacing_and_order(self) -> None:
        capture = pre_gate_abort_capture(
            "unexpected-shell-exit",
            rc=1,
        )
        mutations = (
            capture.replace(
                b"__VEGA_ABORT__ reason=",
                b"__VEGA_ABORT__  reason=",
                1,
            ),
            capture.replace(
                b"reason=unexpected-shell-exit rc=1",
                b"rc=1 reason=unexpected-shell-exit",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaisesRegex(
                    RUNNER.ContractError,
                    "pre-gate abort framing changed",
                ):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        object(),
                        object(),
                    )

    def test_capture_requires_exactly_one_final_terminal_marker(self) -> None:
        capture = valid_capture()
        complete = (
            b"__VEGA_COMPLETE__ write_rc=0 invocation_count=1 "
            b"guard_mode=400:0:0 post_capture=unconditional"
        )
        mutations = (
            capture.replace(complete, b"terminal-marker-absent", 1),
            capture + complete + b"\n",
            capture + b"__VEGA_ABORT__ reason=late-signal\n",
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        FULL,
                        PARTIAL,
                    )

    def test_completion_marker_requires_canonical_spacing_and_order(self) -> None:
        capture = valid_capture()
        canonical = (
            b"__VEGA_COMPLETE__ write_rc=0 invocation_count=1 "
            b"guard_mode=400:0:0 post_capture=unconditional"
        )
        mutations = (
            capture.replace(
                canonical,
                canonical.replace(
                    b"__VEGA_COMPLETE__ ",
                    b"__VEGA_COMPLETE__",
                    1,
                ),
                1,
            ),
            capture.replace(
                canonical,
                canonical.replace(
                    b"__VEGA_COMPLETE__ ",
                    b"__VEGA_COMPLETE__  ",
                    1,
                ),
                1,
            ),
            capture.replace(
                canonical,
                b"__VEGA_COMPLETE__ invocation_count=1 write_rc=0 "
                b"guard_mode=400:0:0 post_capture=unconditional",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaisesRegex(
                    RUNNER.ContractError,
                    "completion marker changed",
                ):
                    RUNNER.validate_capture(
                        mutated,
                        "a" * 64,
                        FULL,
                        PARTIAL,
                    )

    def test_rejects_noncanonical_boot_id_or_wrong_of_path(self) -> None:
        for old, new in (
            (
                b"boot_id_pre=00000000-0000-0000-0000-000000000001",
                b"boot_id_pre=NOT-A-UUID",
            ),
            (
                b"i2c6_of=/sys/firmware/devicetree/base/i2c@1100e000",
                b"i2c6_of=/other/i2c@1100e000",
            ),
        ):
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.validate_capture(
                    valid_capture().replace(old, new, 1),
                    "a" * 64,
                    FULL,
                    PARTIAL,
                )

    def test_started_partial_capture_uses_error_reset(self) -> None:
        data = partial_capture(PARTIAL_FIXTURE.started_dma_timeout(), 4)
        classification, _result, sanitized = RUNNER.validate_capture(
            data, "a" * 64, FULL, PARTIAL
        )
        self.assertEqual(classification, "bounded-stop-first-partial")
        self.assertIn("failing_mode=packed-dma", sanitized)

    def test_new_mode_prestart_accepts_before_or_after_pending_reset(self) -> None:
        for init_count in (2, 3):
            data = partial_capture(
                PARTIAL_FIXTURE.prestart_dma_failure(), init_count
            )
            classification, _result, _sanitized = RUNNER.validate_capture(
                data, "a" * 64, FULL, PARTIAL
            )
            self.assertEqual(classification, "bounded-stop-first-partial")

    def test_full_success_reset_count(self) -> None:
        self.assertEqual(
            RUNNER.allowed_init_counts("complete-success", 9, 9, 9),
            {4},
        )

    def test_started_partial_reset_counts(self) -> None:
        expected = {
            0: {3},
            1: {3},
            2: {3},
            3: {4},
            4: {4},
            5: {4},
            6: {5},
            7: {5},
            8: {5},
        }
        for completed, wanted in expected.items():
            attempted = completed + 1
            self.assertEqual(
                RUNNER.allowed_init_counts(
                    "bounded-stop-first-partial",
                    completed,
                    attempted,
                    attempted,
                ),
                wanted,
            )

    def test_prestart_partial_reset_counts(self) -> None:
        expected = {
            0: {1, 2},
            1: {2},
            2: {2},
            3: {2, 3},
            4: {3},
            5: {3},
            6: {3, 4},
            7: {4},
            8: {4},
        }
        for completed, wanted in expected.items():
            self.assertEqual(
                RUNNER.allowed_init_counts(
                    "bounded-stop-first-partial",
                    completed,
                    completed + 1,
                    completed,
                ),
                wanted,
            )


if __name__ == "__main__":
    unittest.main()
