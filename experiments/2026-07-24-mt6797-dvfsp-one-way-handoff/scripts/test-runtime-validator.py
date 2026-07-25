#!/usr/bin/env python3
"""Device-inert unit and mutation tests for Candidate AO runtime validation."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import pathlib
import sys
import unittest


sys.dont_write_bytecode = True

SOURCE = pathlib.Path(__file__).with_name("validate-runtime.py")
SPEC = importlib.util.spec_from_file_location("candidate_ao_runtime_validator", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AO runtime validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

INSTALLED_SHA256 = "a" * 64
CONFIG_SHA256 = "b" * 64
FDT_SHA256 = "c" * 64
BOOT_ID = "12345678-1234-4abc-8def-1234567890ab"


def snapshot(
    name: str,
    *,
    gated: bool,
    **changes: object,
) -> VALIDATOR.Snapshot:
    values: dict[str, object] = {
        "name": name,
        "timer_before": 0,
        "timer_after": 0,
        "pcm_con0": 0x00000004,
        "pcm_con1": 0x00006C00,
        "pcm_pwr_io_en": 0,
        "pcm_reg15_data": 0,
        "pcm_fsm_sta": 0x00048490,
        "sw_rsv": (0xBABEBABE,) * 7,
        "gate_valid": True,
        "gate": 0x00001002 if gated else 0x00001000,
    }
    values.update(changes)
    return VALIDATOR.Snapshot(**values)


def ready_snapshots() -> tuple[VALIDATOR.Snapshot, ...]:
    return tuple(
        snapshot(name, gated=name in {"post", "late"})
        for name in VALIDATOR.SAMPLE_ORDER
    )


def inconclusive_snapshots() -> tuple[VALIDATOR.Snapshot, ...]:
    return tuple(snapshot(name, gated=True) for name in VALIDATOR.PRE_SAMPLE_ORDER)


def snapshot_line(sample: VALIDATOR.Snapshot) -> str:
    rsv = ",".join(f"{value:08x}" for value in sample.sw_rsv)
    return (
        f"sample={sample.name} "
        f"timer={sample.timer_before:08x}/{sample.timer_after:08x} "
        f"con0={sample.pcm_con0:08x} con1={sample.pcm_con1:08x} "
        f"pwr_io={sample.pcm_pwr_io_en:08x} "
        f"r15={sample.pcm_reg15_data:08x} "
        f"fsm={sample.pcm_fsm_sta:08x} rsv={rsv} "
        f"gate_valid={int(sample.gate_valid)} gate={sample.gate:08x}"
    )


def payload(samples: tuple[VALIDATOR.Snapshot, ...]) -> bytes:
    return ("\n".join(snapshot_line(sample) for sample in samples) + "\n").encode()


def status_line(outcome: str) -> str:
    if outcome == "ready":
        return (
            "state=ready reason=late-validation-passed initial_gate=ungated "
            "transition_attempts=1 enable_successes=1 disable_count=1 "
            "late=passed late_checks=1 faults=0 i2c6_policy=disabled"
        )
    return (
        "state=inconclusive reason=initial-gate-already-gated "
        "initial_gate=gated transition_attempts=0 enable_successes=0 "
        "disable_count=0 late=not-scheduled late_checks=0 faults=0 "
        "i2c6_policy=disabled"
    )


def key_value_lines(values: dict[str, str]) -> str:
    return "\n".join(f"{key}={value}" for key, value in values.items())


def handoff_dmesg(outcome: str, samples: tuple[VALIDATOR.Snapshot, ...]) -> list[str]:
    prefix = (
        "[    1.000000] mt6797-dvfsp-handoff "
        "11015000.dvfsp-handoff: "
    )
    by_name = {sample.name: sample for sample in samples}
    lines = [
        prefix + "state=validating operation=one-way-handoff i2c6_policy=disabled",
        prefix + snapshot_line(by_name["pre0"]),
        prefix + snapshot_line(by_name["pre1"]),
        prefix + snapshot_line(by_name["pre2"]),
    ]
    if outcome == "ready":
        lines.extend(
            (
                prefix
                + "state=normalizing transition=ccf-temporary-reference attempt=1",
                prefix + snapshot_line(by_name["enabled"]),
                prefix + snapshot_line(by_name["post"]),
                prefix
                + "state=provisional normalization=ungated-to-gated "
                "enable_successes=1 disable_count=1 late_validation=pending "
                "delay_ms=45000 i2c6_policy=disabled",
                prefix + snapshot_line(by_name["late"]),
                prefix
                + "state=ready normalization=ungated-to-gated "
                "late_validation=passed i2c6_policy=disabled",
            )
        )
    else:
        lines.append(
            prefix
            + "state=inconclusive reason=initial-gate-already-gated "
            "transition_attempts=0 i2c6_policy=disabled"
        )
    return lines


def make_capture(outcome: str = "ready") -> str:
    samples = ready_snapshots() if outcome == "ready" else inconclusive_snapshots()
    raw = payload(samples)
    host = {
        "installed_full_sha256_input": INSTALLED_SHA256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "handoff_access_path": "platform-device-read-only-sysfs",
        "i2c_transaction_or_controller_control": "none",
        "regulator_control_or_value_read": "none",
        "cpu_online_control_access": "none",
        "watchdog_control_access": "none",
        "reboot_executed": "no",
        "keymap_helper_tty_open_mode": "O_RDWR",
        "keymap_helper_ioctl_scope": "KDGKBMODE-plus-KDGKBENT-readback-only",
        "keymap_helper_mutating_ioctl": "none",
        "interface": "en12",
        "mac": "42:00:15:19:82:00",
        "host_address": "10.15.19.1",
        "route_interface": "en12",
    }
    identity = dict(VALIDATOR.EXPECTED_IDENTITY)
    identity.update(
        {
            "boot_id": BOOT_ID,
            "uptime_seconds": "50",
            "config_sha256": CONFIG_SHA256,
        }
    )
    state = dict(VALIDATOR.EXPECTED_STATE)
    state.update(
        {
            "live_fdt_sha256": FDT_SHA256,
            "live_fdt_size": "52611",
            "handoff_clocks_hex": VALIDATOR.EXPECTED_HANDOFF_CLOCKS_HEX,
            "handoff_infracfg_hex": "00000003",
            "handoff_state": outcome,
            "handoff_status": status_line(outcome),
            "handoff_snapshots_hex": raw.hex(),
            "handoff_snapshots_sha256": hashlib.sha256(raw).hexdigest(),
            "handoff_snapshot_line_count": str(len(samples)),
            "ac_ready_count": "1",
            "boot_id": BOOT_ID,
            "uptime_seconds": "50",
        }
    )
    state2 = dict(state)
    state2["uptime_seconds"] = "55"
    stat1 = "\n".join(
        f"cpu{cpu} {100 + cpu} 0 0 900 0 0 0 0 0 0" for cpu in range(8)
    )
    stat2 = "\n".join(
        f"cpu{cpu} {110 + cpu} 0 0 900 0 0 0 0 0 0" for cpu in range(8)
    )

    dmesg = [
        VALIDATOR.BLACKLIST_DMESG,
        "smp: Brought up 1 node, 8 CPUs",
    ]
    for cpu, mpidr in VALIDATOR.EXPECTED_BOOT_NODES.items():
        dmesg.extend(
            (
                f"CPU{cpu}: Booted secondary processor 0x{mpidr} [0x410fd034]",
                f"GICv3: CPU{cpu}: found redistributor 100 region 0:0x00000000",
            )
        )
    dmesg.extend(
        (
            "calling  simplefb_driver_init+0x0/0x100",
            "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
            "(32320 KiB) nomap non-reusable mblock-3-framebuffer",
            "simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
            "initcall simplefb_driver_init+0x0/0x100 returned 0 after 1 usecs",
            "calling  da9211_regulator_driver_init+0x0/0x100",
            "initcall da9211_regulator_driver_init+0x0/0x100 returned 0 "
            "after 1 usecs",
            "calling  mt6797_dvfsp_handoff_driver_init+0x0/0x100",
            *handoff_dmesg(outcome, samples),
            "initcall mt6797_dvfsp_handoff_driver_init+0x0/0x100 "
            "returned 0 after 22000 usecs",
            "input: keyboard-matrix as "
            "/devices/platform/keyboard-matrix/input/input0",
            "matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
            "GEMINI_MT6797_KERNEL_RESTART_20260720_AB services=launched "
            "probe=independent tty1_shell=supervised "
            "clean_tty1_background=yes reboot_dispatch=env-alias "
            "watchdog_userspace=none keyboard_map=tty1-synchronous "
            "manual_reboot=busybox-no-sync-force "
            "usb_network=background-nc-2323",
            "aw9523_client=0-005b driver=aw9523-pinctrl",
            "matrix_platform_device=keyboard-matrix driver=matrix-keypad",
            "matrix_input_name=keyboard-matrix event_node=/dev/input/event0",
            "keyboard_map=loaded origin=existing "
            "sha256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c "
            "tty1_shell=ready prompt=GEMINI-AB# reboot_dispatch=validated",
            f"{VALIDATOR.USB_MARKER} service=nc status=listening "
            "address=10.15.19.82 port=2323 shell=/bin/usb-shell "
            "authentication=none encryption=none direct_link_only=yes",
            f"{VALIDATOR.USB_MARKER} services=launched usb_network=background "
            "worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 "
            "local_console=unchanged watchdog_userspace=none",
            f"{VALIDATOR.USB_MARKER} usb_shell=session-entry "
            "usb0_operstate=up usb0_carrier=1 udc=11271000.usb "
            "udc_state=configured",
            f"{VALIDATOR.USB_MARKER} usb_shell=ready "
            "reboot_dispatch=validated privilege=root authentication=none "
            "encryption=none direct_link_only=yes",
        )
    )
    return "\n".join(
        (
            "__AO_HOST_BEGIN__",
            key_value_lines(host),
            "__AO_HOST_END__",
            VALIDATOR.USB_MARKER,
            "__AO_IDENTITY_BEGIN__",
            key_value_lines(identity),
            "__AO_IDENTITY_END__",
            "__AO_STATE1_BEGIN__",
            key_value_lines(state),
            "__AO_STATE1_END__",
            "__AO_STAT1_BEGIN__",
            stat1,
            "__AO_STAT1_END__",
            "__AO_STATE2_BEGIN__",
            key_value_lines(state2),
            "__AO_STATE2_END__",
            "__AO_STAT2_BEGIN__",
            stat2,
            "__AO_STAT2_END__",
            "__AO_DMESG_BEGIN__",
            "\n".join(dmesg),
            "__AO_DMESG_END__",
            "",
        )
    )


def validate_fixture(text: str) -> VALIDATOR.ValidationResult:
    return VALIDATOR.validate(
        text,
        INSTALLED_SHA256,
        CONFIG_SHA256,
        FDT_SHA256,
    )


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"fixture replacement count changed: expected {count}, found {actual}"
        )
    return text.replace(old, new, 1)


class ClassificationTests(unittest.TestCase):
    def test_ready_requires_exact_six_sample_transition(self) -> None:
        self.assertEqual(VALIDATOR.classify(ready_snapshots()), "ready")

    def test_inconclusive_requires_three_initially_gated_samples(self) -> None:
        self.assertEqual(
            VALIDATOR.classify(inconclusive_snapshots()), "inconclusive"
        )

    def test_every_required_reset_bit_fails_closed(self) -> None:
        mutations = (
            {"pcm_con0": 0x00000005},
            {"pcm_con0": 0x00000006},
            {"pcm_con0": 0x00008004},
            {"pcm_con1": 0x00006C20},
            {"pcm_con1": 0x00006D00},
            {"pcm_pwr_io_en": 1},
            {"pcm_fsm_sta": 0x00048491},
            {"timer_after": 1},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                samples = list(ready_snapshots())
                samples[2] = dataclasses.replace(samples[2], **mutation)
                with self.assertRaises(ValueError):
                    VALIDATOR.classify(tuple(samples))

    def test_timer_r15_and_rsv_must_stay_stable(self) -> None:
        mutations = (
            {"timer_before": 1, "timer_after": 1},
            {"pcm_reg15_data": 1},
            {"sw_rsv": (0xBABEBABE,) * 6 + (0xBABEBABF,)},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                samples = list(ready_snapshots())
                samples[4] = dataclasses.replace(samples[4], **mutation)
                with self.assertRaises(ValueError):
                    VALIDATOR.classify(tuple(samples))

    def test_stable_but_wrong_an_signature_values_fail(self) -> None:
        mutations = (
            {"timer_before": 1, "timer_after": 1},
            {"pcm_reg15_data": 1},
            # Timer/WDT activity bits remain clear, but this is not 0x00006c00.
            {"pcm_con1": 0x00004C00},
            {"sw_rsv": (1, 2, 3, 4, 5, 6, 7)},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                samples = tuple(
                    dataclasses.replace(sample, **mutation)
                    for sample in ready_snapshots()
                )
                with self.assertRaises(ValueError):
                    VALIDATOR.classify(samples)

    def test_gate_validity_and_each_transition_boundary_are_mandatory(self) -> None:
        mutations = (
            (0, {"gate_valid": False}),
            (0, {"gate": 0x1002}),
            (3, {"gate": 0x1002}),
            (4, {"gate": 0x1000}),
            (5, {"gate": 0x1000}),
        )
        for index, mutation in mutations:
            with self.subTest(index=index, mutation=mutation):
                samples = list(ready_snapshots())
                samples[index] = dataclasses.replace(samples[index], **mutation)
                with self.assertRaises(ValueError):
                    VALIDATOR.classify(tuple(samples))

    def test_only_i2c_appm_gate_bit_has_semantic_weight(self) -> None:
        samples = list(ready_snapshots())
        unrelated = (0x00000000, 0xFFFFFFFC, 0x13579BD9, 0x2468ACF0, 0x2, 0xFFFFFFFE)
        for index, value in enumerate(unrelated):
            gated = samples[index].name in {"post", "late"}
            samples[index] = dataclasses.replace(
                samples[index],
                gate=(value & ~(1 << 1)) | ((1 << 1) if gated else 0),
            )
        self.assertEqual(VALIDATOR.classify(tuple(samples)), "ready")

    def test_initially_ungated_short_result_is_not_inconclusive(self) -> None:
        samples = list(inconclusive_snapshots())
        samples[2] = dataclasses.replace(samples[2], gate=0x1000)
        with self.assertRaises(ValueError):
            VALIDATOR.classify(tuple(samples))


class ParserTests(unittest.TestCase):
    def test_exact_ready_and_inconclusive_payloads(self) -> None:
        for samples in (ready_snapshots(), inconclusive_snapshots()):
            with self.subTest(count=len(samples)):
                raw = payload(samples)
                self.assertEqual(
                    VALIDATOR.parse_snapshots(
                        raw.hex(), hashlib.sha256(raw).hexdigest()
                    ),
                    samples,
                )

    def test_payload_rejects_reorder_duplicate_missing_hash_and_termination(self) -> None:
        samples = ready_snapshots()
        cases = (
            samples[:3] + (samples[4], samples[3], samples[5]),
            samples[:3] + (samples[3], samples[3], samples[5]),
            samples[:-1],
        )
        for mutated in cases:
            with self.subTest(names=[item.name for item in mutated]):
                raw = payload(mutated)
                with self.assertRaises(ValueError):
                    VALIDATOR.parse_snapshots(
                        raw.hex(), hashlib.sha256(raw).hexdigest()
                    )
        raw = payload(samples)
        with self.assertRaises(ValueError):
            VALIDATOR.parse_snapshots(raw.hex(), "0" * 64)
        no_newline = raw.rstrip(b"\n")
        with self.assertRaises(ValueError):
            VALIDATOR.parse_snapshots(
                no_newline.hex(), hashlib.sha256(no_newline).hexdigest()
            )

    def test_status_requires_exact_counter_inventory(self) -> None:
        status = VALIDATOR.parse_status(status_line("ready"))
        VALIDATOR.validate_status(status, "ready")
        mutated = dataclasses.replace(status, enable_successes=2)
        with self.assertRaises(ValueError):
            VALIDATOR.validate_status(mutated, "ready")


class FullValidationTests(unittest.TestCase):
    def test_ready_capture_passes(self) -> None:
        result = validate_fixture(make_capture("ready"))
        self.assertEqual(result.outcome, "PASS")
        self.assertEqual(result.boot_id, BOOT_ID)

    def test_initially_gated_capture_is_explicitly_inconclusive(self) -> None:
        result = validate_fixture(make_capture("inconclusive"))
        self.assertEqual(result.outcome, "INCONCLUSIVE")

    def test_prompt_prefixes_are_normalized(self) -> None:
        text = make_capture("ready")
        text = text.replace(
            "__AO_IDENTITY_BEGIN__",
            "GEMINI-AC-USB# GEMINI-AC-USB# > > "
            "GEMINI-AC-USB# GEMINI-AC-USB# __AO_IDENTITY_BEGIN__",
        )
        text = text.replace("__AO_STATE1_BEGIN__", "GEMINI-AC-USB# __AO_STATE1_BEGIN__")
        self.assertEqual(validate_fixture(text).outcome, "PASS")

    def test_malformed_prompt_prefixes_fail_closed(self) -> None:
        good = make_capture("ready")
        cases = (
            good.replace(
                "__AO_IDENTITY_BEGIN__",
                "GEMINI-AC-USB# > unexpected __AO_IDENTITY_BEGIN__",
                1,
            ),
            good.replace("cmdline=", "> cmdline=", 1),
        )
        for text in cases:
            with self.subTest():
                with self.assertRaises(ValueError):
                    validate_fixture(text)

    def test_section_reorder_duplicate_and_unknown_marker_fail_closed(self) -> None:
        good = make_capture()
        cases = (
            good.replace(
                "__AO_STATE1_END__\n__AO_STAT1_BEGIN__",
                "__AO_STAT1_BEGIN__\n__AO_STATE1_END__",
            ),
            good.replace("__AO_STATE1_BEGIN__", "__AO_STATE1_BEGIN__\n__AO_STATE1_BEGIN__"),
            good.replace("__AO_STATE1_BEGIN__", "__AO_EXTRA_BEGIN__\n__AO_STATE1_BEGIN__"),
        )
        for text in cases:
            with self.subTest():
                with self.assertRaises(ValueError):
                    validate_fixture(text)

    def test_duplicate_key_and_state_drift_fail_closed(self) -> None:
        good = make_capture()
        duplicate = replace_exact(
            good,
            "handoff_state=ready",
            "handoff_state=ready\nhandoff_state=ready",
            count=2,
        )
        with self.assertRaises(ValueError):
            validate_fixture(duplicate)
        drift = good
        # Mutate only STATE2's immutable clock provider.
        first = drift.index("__AO_STATE2_BEGIN__")
        at = drift.index("handoff_infracfg_hex=00000003", first)
        drift = drift[:at] + drift[at:].replace(
            "handoff_infracfg_hex=00000003",
            "handoff_infracfg_hex=00000004",
            1,
        )
        with self.assertRaises(ValueError):
            validate_fixture(drift)

    def test_handoff_clock_encoding_is_exact_and_fails_closed(self) -> None:
        self.assertEqual(
            VALIDATOR.EXPECTED_HANDOFF_CLOCKS_HEX,
            "0000000300000036",
        )
        good = make_capture()
        self.assertIn("handoff_clocks_hex=0000000300000036", good)
        wrong_encodings = (
            "00000036",
            "0000000400000036",
            "0000000300000037",
            "000000030000003600000000",
        )
        for wrong_encoding in wrong_encodings:
            with self.subTest(wrong_encoding=wrong_encoding):
                wrong_clock = good.replace(
                    "handoff_clocks_hex=0000000300000036",
                    f"handoff_clocks_hex={wrong_encoding}",
                )
                with self.assertRaises(ValueError):
                    validate_fixture(wrong_clock)

    def test_dmesg_duplicate_or_reordered_handoff_evidence_fails_closed(self) -> None:
        good = make_capture()
        sample = (
            "[    1.000000] mt6797-dvfsp-handoff "
            "11015000.dvfsp-handoff: "
            + snapshot_line(ready_snapshots()[3])
        )
        duplicate = replace_exact(good, sample, sample + "\n" + sample)
        with self.assertRaises(ValueError):
            validate_fixture(duplicate)
        normalizing = (
            "[    1.000000] mt6797-dvfsp-handoff "
            "11015000.dvfsp-handoff: "
            "state=normalizing transition=ccf-temporary-reference attempt=1"
        )
        reordered = replace_exact(
            good,
            normalizing + "\n" + sample,
            sample + "\n" + normalizing,
        )
        with self.assertRaises(ValueError):
            validate_fixture(reordered)

    def test_driver_counter_lie_fails_independent_classification(self) -> None:
        text = make_capture()
        text = text.replace(
            "transition_attempts=1 enable_successes=1",
            "transition_attempts=1 enable_successes=2",
        )
        with self.assertRaises(ValueError):
            validate_fixture(text)

    def test_i2c6_da9214_and_a72_activity_each_fail(self) -> None:
        additions = (
            "mtk-i2c 1100e000.i2c: probe complete",
            "da9214 6-0068: probe complete",
            "CPU8: Booted secondary processor 0x0000000200 [0x410fd091]",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                text = make_capture().replace(
                    "__AO_DMESG_END__", addition + "\n__AO_DMESG_END__"
                )
                with self.assertRaises(ValueError):
                    validate_fixture(text)

    def test_cpu_inventory_and_accounting_must_be_exact_and_advance(self) -> None:
        good = make_capture()
        stalled = replace_exact(
            good,
            "cpu7 117 0 0 900 0 0 0 0 0 0",
            "cpu7 107 0 0 900 0 0 0 0 0 0",
        )
        with self.assertRaises(ValueError):
            validate_fixture(stalled)
        extra = replace_exact(
            good,
            "__AO_STAT2_END__",
            "cpu8 1 0 0 1 0 0 0 0 0 0\n__AO_STAT2_END__",
        )
        with self.assertRaises(ValueError):
            validate_fixture(extra)

    def test_inherited_usb_keyboard_console_and_reboot_checks_are_mandatory(self) -> None:
        needles = (
            "simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
            "aw9523_client=0-005b driver=aw9523-pinctrl",
            "reboot_dispatch=validated",
            f"{VALIDATOR.USB_MARKER} service=nc status=listening",
        )
        for needle in needles:
            with self.subTest(needle=needle):
                text = make_capture().replace(needle, "MUTATED", 1)
                with self.assertRaises(ValueError):
                    validate_fixture(text)

    def test_expected_identity_hashes_are_not_self_calibrating(self) -> None:
        text = make_capture()
        self.assertEqual(
            VALIDATOR.EXPECTED_KEYMAP_OUTPUT,
            "keymap_readback=verified tables=8 payload_entries=1024 "
            "kernel_entries=2048 high_halves=K_HOLE table3=K_ALLOCATED "
            "undeclared_tables=K_NOSUCHMAP unicode_mode=K_UNICODE",
        )
        self.assertEqual(
            bytes.fromhex(VALIDATOR.EXPECTED_KEYMAP_OUTPUT_HEX).decode("ascii"),
            VALIDATOR.EXPECTED_KEYMAP_OUTPUT,
        )
        with self.assertRaises(ValueError):
            VALIDATOR.validate(text, "0" * 64, CONFIG_SHA256, FDT_SHA256)
        with self.assertRaises(ValueError):
            VALIDATOR.validate(text, INSTALLED_SHA256, "0" * 64, FDT_SHA256)
        with self.assertRaises(ValueError):
            VALIDATOR.validate(text, INSTALLED_SHA256, CONFIG_SHA256, "0" * 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
