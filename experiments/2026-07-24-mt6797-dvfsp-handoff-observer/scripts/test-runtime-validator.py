#!/usr/bin/env python3
"""Storage- and device-inert tests for Candidate AN's snapshot oracle."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import pathlib
import re
import sys
import unittest


sys.dont_write_bytecode = True

SOURCE = pathlib.Path(__file__).with_name("validate-runtime.py")
SPEC = importlib.util.spec_from_file_location("candidate_an_runtime_validator", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AN runtime validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

FIXTURE_INSTALLED_SHA256 = VALIDATOR.AN.PADDED_SHA256
FIXTURE_CONFIG_SHA256 = VALIDATOR.AN.CONFIG_SHA256
FIXTURE_FDT_SHA256 = VALIDATOR.EXPECTED_LIVE_FDT_SHA256
BOOT_ID = "12345678-1234-4abc-8def-1234567890ab"


def stopped(index: int) -> VALIDATOR.Snapshot:
    return VALIDATOR.Snapshot(
        index=index,
        timer_before=0x12345678,
        timer_after=0x12345678,
        pcm_con1=0,
        pcm_pwr_io_en=0,
        pcm_reg15_data=0x1028,
        pcm_fsm_sta=0x00048490,
        sw_rsv=(1, 2, 3, 4, 5, 6, 7),
        infra2_pdn_sta_valid=True,
        infra2_pdn_sta=0x00000002,
    )


def triplet() -> tuple[VALIDATOR.Snapshot, ...]:
    return tuple(stopped(index) for index in range(3))


def sysfs_line(snapshot: VALIDATOR.Snapshot) -> str:
    rsv = ",".join(f"{value:08x}" for value in snapshot.sw_rsv)
    return (
        f"snapshot={snapshot.index} "
        f"timer_before={snapshot.timer_before:08x} "
        f"timer_after={snapshot.timer_after:08x} "
        f"pcm_con1={snapshot.pcm_con1:08x} "
        f"pcm_pwr_io_en={snapshot.pcm_pwr_io_en:08x} "
        f"pcm_reg15_data={snapshot.pcm_reg15_data:08x} "
        f"pcm_fsm_sta={snapshot.pcm_fsm_sta:08x} "
        f"sw_rsv={rsv} "
        f"infra2_pdn_sta_valid={int(snapshot.infra2_pdn_sta_valid)} "
        f"infra2_pdn_sta={snapshot.infra2_pdn_sta:08x}"
    )


def dmesg_snapshot_line(snapshot: VALIDATOR.Snapshot) -> str:
    rsv = ",".join(f"{value:08x}" for value in snapshot.sw_rsv)
    return (
        "[    1.000000] mt6797-dvfsp-handoff-observer "
        "11015000.dvfsp-observer: "
        f"snapshot={snapshot.index} "
        f"timer={snapshot.timer_before:08x}/{snapshot.timer_after:08x} "
        f"con1={snapshot.pcm_con1:08x} "
        f"pwr_io={snapshot.pcm_pwr_io_en:08x} "
        f"pc={snapshot.pcm_reg15_data:08x} "
        f"fsm={snapshot.pcm_fsm_sta:08x} "
        f"rsv={rsv} "
        f"gate_valid={int(snapshot.infra2_pdn_sta_valid)} "
        f"gate={snapshot.infra2_pdn_sta:08x}"
    )


def key_value_lines(values: dict[str, str]) -> str:
    return "\n".join(f"{key}={value}" for key, value in values.items())


def make_capture(
    *,
    snapshot_payload: bytes | None = None,
    observer_state: str = "quiescent-stopped",
    usb_shell_sessions: int = 1,
) -> str:
    samples = triplet()
    if snapshot_payload is None:
        snapshot_payload = (
            "\n".join(sysfs_line(snapshot) for snapshot in samples) + "\n"
        ).encode()

    snapshot_lines = [dmesg_snapshot_line(snapshot) for snapshot in samples]
    state_line = (
        "[    1.021000] mt6797-dvfsp-handoff-observer "
        "11015000.dvfsp-observer: "
        f"state={observer_state} i2c6_policy=disabled"
    )
    probe_lines = snapshot_lines + [state_line]
    probe_sha256 = hashlib.sha256(
        ("\n".join(probe_lines) + "\n").encode()
    ).hexdigest()

    dmesg_lines = [
        VALIDATOR.BLACKLIST_DMESG,
        "smp: Brought up 1 node, 8 CPUs",
    ]
    for cpu, mpidr in VALIDATOR.EXPECTED_BOOT_NODES.items():
        dmesg_lines.extend(
            (
                f"CPU{cpu}: Booted secondary processor 0x{mpidr} [0x410fd034]",
                f"GICv3: CPU{cpu}: found redistributor 100 region 0:0x00000000",
            )
        )
    dmesg_lines.extend(
        (
            "calling  simplefb_driver_init+0x0/0x100",
            "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
            "(32320 KiB) nomap non-reusable mblock-3-framebuffer",
            "simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
            "initcall simplefb_driver_init+0x0/0x100 returned 0 after 1 usecs",
            "calling  da9211_regulator_driver_init+0x0/0x100",
            "initcall da9211_regulator_driver_init+0x0/0x100 returned 0 "
            "after 1 usecs",
            "calling  mt6797_dvfsp_observer_driver_init+0x0/0x100",
            *probe_lines,
            "initcall mt6797_dvfsp_observer_driver_init+0x0/0x100 "
            "returned 0 after 21000 usecs",
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
        )
    )
    for _ in range(usb_shell_sessions):
        dmesg_lines.extend(
            (
                f"{VALIDATOR.USB_MARKER} usb_shell=session-entry "
                "usb0_operstate=up usb0_carrier=1 udc=11271000.usb "
                "udc_state=configured",
                f"{VALIDATOR.USB_MARKER} usb_shell=ready "
                "reboot_dispatch=validated privilege=root authentication=none "
                "encryption=none direct_link_only=yes",
            )
        )
    dmesg = "\n".join(dmesg_lines)

    host = {
        "installed_full_sha256_input": FIXTURE_INSTALLED_SHA256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "observer_access_path": "platform-device-read-only-sysfs",
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
    identity["config_sha256"] = FIXTURE_CONFIG_SHA256
    identity["boot_id"] = BOOT_ID
    identity["uptime_seconds"] = "45"

    state_base = dict(VALIDATOR.EXPECTED_STATE)
    state_base.update(
        {
            "live_fdt_sha256": FIXTURE_FDT_SHA256,
            "live_fdt_size": VALIDATOR.EXPECTED_LIVE_FDT_SIZE,
            "observer_state": observer_state,
            "observer_snapshots_hex": snapshot_payload.hex(),
            "observer_snapshots_sha256": hashlib.sha256(
                snapshot_payload
            ).hexdigest(),
            "observer_probe_log_sha256": probe_sha256,
            "ac_ready_count": str(usb_shell_sessions),
            "boot_id": BOOT_ID,
        }
    )
    state1 = dict(state_base)
    state1["uptime_seconds"] = "45"
    state2 = dict(state_base)
    state2["uptime_seconds"] = "50"

    stat1 = "\n".join(
        f"cpu{cpu} {100 + cpu} 0 0 900 0 0 0 0 0 0" for cpu in range(8)
    )
    stat2 = "\n".join(
        f"cpu{cpu} {110 + cpu} 0 0 900 0 0 0 0 0 0" for cpu in range(8)
    )
    return "\n".join(
        (
            "__AN_HOST_BEGIN__",
            key_value_lines(host),
            "__AN_HOST_END__",
            VALIDATOR.USB_MARKER,
            "__AN_IDENTITY_BEGIN__",
            key_value_lines(identity),
            "__AN_IDENTITY_END__",
            "__AN_STATE1_BEGIN__",
            key_value_lines(state1),
            "__AN_STATE1_END__",
            "__AN_STAT1_BEGIN__",
            stat1,
            "__AN_STAT1_END__",
            "__AN_STATE2_BEGIN__",
            key_value_lines(state2),
            "__AN_STATE2_END__",
            "__AN_STAT2_BEGIN__",
            stat2,
            "__AN_STAT2_END__",
            "__AN_DMESG_BEGIN__",
            dmesg,
            "__AN_DMESG_END__",
            "",
        )
    )


def validate_fixture(text: str) -> dict[str, str]:
    return VALIDATOR.validate(text, FIXTURE_INSTALLED_SHA256)


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"fixture replacement count changed: expected {count}, found {actual}"
        )
    return text.replace(old, new)


class ClassificationTests(unittest.TestCase):
    def test_strict_quiescent_stopped(self) -> None:
        self.assertEqual(VALIDATOR.classify(triplet()), "quiescent-stopped")

    def test_unrelated_infracfg_bits_do_not_change_gate_evidence(self) -> None:
        samples = list(triplet())
        samples[1] = dataclasses.replace(samples[1], infra2_pdn_sta=0xFFFFFFFE)
        samples[2] = dataclasses.replace(samples[2], infra2_pdn_sta=0x00001002)
        self.assertEqual(
            VALIDATOR.classify(tuple(samples)), "quiescent-stopped"
        )

    def test_each_direct_activity_bit_wins(self) -> None:
        mutations = (
            {"pcm_fsm_sta": 0x00248490},
            {"pcm_pwr_io_en": 0x80},
            {"timer_after": 0x12345679},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                samples = list(triplet())
                samples[0] = dataclasses.replace(samples[0], **mutation)
                self.assertEqual(VALIDATOR.classify(tuple(samples)), "active")

    def test_inter_snapshot_timer_pc_and_rsv_changes_are_active(self) -> None:
        mutations = (
            {"timer_before": 0x12345679, "timer_after": 0x12345679},
            {"pcm_reg15_data": 0x1029},
            {"sw_rsv": (1, 2, 3, 4, 5, 6, 8)},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                samples = list(triplet())
                samples[1] = dataclasses.replace(samples[1], **mutation)
                self.assertEqual(VALIDATOR.classify(tuple(samples)), "active")

    def test_fail_closed_unknown_conditions(self) -> None:
        mutations = (
            {"pcm_con1": 1 << 5},
            {"pcm_con1": 1},
            {"pcm_fsm_sta": 0x00048491},
            {"infra2_pdn_sta_valid": False},
            {"infra2_pdn_sta": 0},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                samples = list(triplet())
                samples[0] = dataclasses.replace(samples[0], **mutation)
                self.assertEqual(VALIDATOR.classify(tuple(samples)), "unknown")

    def test_control_drift_without_positive_activity_is_unknown(self) -> None:
        samples = list(triplet())
        samples[1] = dataclasses.replace(samples[1], pcm_con1=1)
        self.assertEqual(VALIDATOR.classify(tuple(samples)), "unknown")


class ParserTests(unittest.TestCase):
    def test_exact_three_line_sysfs_payload(self) -> None:
        expected = triplet()
        raw = ("\n".join(sysfs_line(snapshot) for snapshot in expected) + "\n").encode()
        parsed = VALIDATOR.parse_sysfs_snapshots(
            raw.hex(), hashlib.sha256(raw).hexdigest()
        )
        self.assertEqual(parsed, expected)

    def test_rejects_wrong_count_order_hash_and_termination(self) -> None:
        expected = triplet()
        good = "\n".join(sysfs_line(snapshot) for snapshot in expected) + "\n"
        cases = (
            "\n".join(sysfs_line(snapshot) for snapshot in expected[:2]) + "\n",
            "\n".join(
                sysfs_line(snapshot)
                for snapshot in (expected[0], expected[2], expected[1])
            )
            + "\n",
            good.rstrip("\n"),
        )
        for text in cases:
            with self.subTest(text=text):
                raw = text.encode()
                with self.assertRaises(ValueError):
                    VALIDATOR.parse_sysfs_snapshots(
                        raw.hex(), hashlib.sha256(raw).hexdigest()
                    )
        raw = good.encode()
        with self.assertRaises(ValueError):
            VALIDATOR.parse_sysfs_snapshots(raw.hex(), "0" * 64)

    def test_dmesg_mapping_is_identical(self) -> None:
        expected = triplet()
        lines = [dmesg_snapshot_line(snapshot) for snapshot in expected]
        self.assertEqual(VALIDATOR.parse_dmesg_snapshots("\n".join(lines)), expected)


class LineageTests(unittest.TestCase):
    def test_runtime_identities_are_tied_to_candidate_an(self) -> None:
        self.assertEqual(VALIDATOR.AN.artifact_pin_state(), "source-pinned")
        self.assertEqual(
            VALIDATOR.EXPECTED_INSTALLED_FULL_SHA256,
            VALIDATOR.AN.PADDED_SHA256,
        )
        self.assertEqual(
            VALIDATOR.EXPECTED_CONFIG_SHA256,
            VALIDATOR.AN.CONFIG_SHA256,
        )
        self.assertEqual(
            VALIDATOR.EXPECTED_ARTIFACT_DTB_SHA256,
            VALIDATOR.AN.FINAL_DTB_SHA256,
        )
        self.assertNotEqual(
            VALIDATOR.EXPECTED_LIVE_FDT_SHA256,
            VALIDATOR.EXPECTED_ARTIFACT_DTB_SHA256,
        )
        self.assertRegex(VALIDATOR.EXPECTED_LIVE_FDT_SHA256, r"^[0-9a-f]{64}$")
        self.assertEqual(VALIDATOR.EXPECTED_LIVE_FDT_SIZE, "52547")

    def test_bash_collector_padded_pin_matches_candidate_an(self) -> None:
        collector = SOURCE.with_name("collect-runtime.sh").read_text()
        matches = re.findall(
            r"^readonly EXPECTED_INSTALLED_FULL_SHA256=(\S+)$",
            collector,
            re.MULTILINE,
        )
        self.assertEqual(matches, [VALIDATOR.AN.PADDED_SHA256])

    def test_live_fdt_identity_matches_semantic_delta_validator(self) -> None:
        delta_source = SOURCE.with_name("validate-live-fdt-delta.py")
        spec = importlib.util.spec_from_file_location(
            "candidate_an_runtime_live_fdt_delta", delta_source
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load Candidate AN live-FDT validator")
        delta_validator = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = delta_validator
        spec.loader.exec_module(delta_validator)
        self.assertEqual(
            VALIDATOR.EXPECTED_LIVE_FDT_SHA256,
            delta_validator.EXPECTED_LIVE_FDT_SHA256,
        )
        self.assertEqual(
            int(VALIDATOR.EXPECTED_LIVE_FDT_SIZE),
            delta_validator.EXPECTED_LIVE_FDT_SIZE,
        )

    def test_bash_collector_opens_snapshots_once_and_uses_sentinel(self) -> None:
        collector = SOURCE.with_name("collect-runtime.sh").read_text()
        snapshot_opens = re.findall(
            r'/bin/busybox cat "\$observer_device_path/snapshots"',
            collector,
        )
        self.assertEqual(len(snapshot_opens), 1)
        self.assertIn(
            r"observer_snapshots_sentinel=$(/bin/busybox printf '\001')",
            collector,
        )
        self.assertIn(
            'observer_snapshots=${observer_snapshots_capture%'
            '"$observer_snapshots_sentinel"}',
            collector,
        )
        self.assertIn(
            'observer_snapshots_hex=$(printf \'%s\' "$observer_snapshots"',
            collector,
        )

    def test_production_path_rejects_wrong_installed_identity(self) -> None:
        with self.assertRaises((RuntimeError, ValueError)):
            VALIDATOR.validate(make_capture(), "d" * 64)

    def test_remote_pass_wording_withholds_physical_execution_claims(self) -> None:
        source = SOURCE.read_text()
        required = (
            "physical_console_visibility=not-observed-by-remote-collector",
            "physical_keypress_execution=not-observed-by-remote-collector",
            "physical_reboot_execution=not-observed-by-remote-collector",
            "keymap_helper_tty_open=O_RDWR",
            "keymap_helper_mutating_ioctl=none",
        )
        for wording in required:
            self.assertIn(wording, source)
        self.assertNotIn("console_usb_keyboard=inherited-and-validated", source)


class EndToEndTests(unittest.TestCase):
    def test_complete_valid_capture_passes_validate(self) -> None:
        result = validate_fixture(make_capture())
        self.assertEqual(result["boot_id"], BOOT_ID)
        self.assertEqual(result["uptime_seconds"], "50")
        self.assertEqual(result["state"], "quiescent-stopped")

    def test_repeated_diagnostic_usb_shell_sessions_pass_when_counted(self) -> None:
        result = validate_fixture(make_capture(usb_shell_sessions=4))
        self.assertEqual(result["state"], "quiescent-stopped")

    def test_usb_shell_ready_count_mismatch_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(usb_shell_sessions=4),
            "ac_ready_count=4",
            "ac_ready_count=3",
            count=2,
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_usb_shell_unpaired_session_is_rejected(self) -> None:
        line = (
            f"{VALIDATOR.USB_MARKER} usb_shell=session-entry "
            "usb0_operstate=up usb0_carrier=1 udc=11271000.usb "
            "udc_state=configured\n"
        )
        mutated = replace_exact(make_capture(), line, "")
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_exact_snapshot_terminal_newline_is_required(self) -> None:
        raw = "\n".join(sysfs_line(snapshot) for snapshot in triplet()).encode()
        with self.assertRaises(ValueError):
            validate_fixture(make_capture(snapshot_payload=raw))

    def test_driver_classification_must_match_independent_oracle(self) -> None:
        with self.assertRaises(ValueError):
            validate_fixture(make_capture(observer_state="unknown"))

    def test_live_fdt_identity_mutation_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            f"live_fdt_sha256={FIXTURE_FDT_SHA256}",
            f"live_fdt_sha256={'d' * 64}",
            count=2,
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_resolved_config_identity_mutation_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            f"config_sha256={FIXTURE_CONFIG_SHA256}",
            f"config_sha256={'e' * 64}",
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_i2c6_adapter_activity_mutation_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            "i2c6_adapter_count=0",
            "i2c6_adapter_count=1",
            count=2,
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_observer_link_change_between_reads_is_rejected(self) -> None:
        original = make_capture()
        state2 = VALIDATOR.section(original, "STATE2")
        changed_state2 = replace_exact(
            state2,
            "observer_driver_target="
            "/sys/bus/platform/drivers/mt6797-dvfsp-handoff-observer",
            "observer_driver_target=/sys/bus/platform/drivers/wrong-observer",
        )
        mutated = replace_exact(original, state2, changed_state2)
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_dmesg_snapshot_mutation_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            "snapshot=1 timer=12345678/12345678",
            "snapshot=1 timer=12345679/12345679",
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_extra_observer_probe_log_is_rejected(self) -> None:
        injected = (
            "[    1.030000] mt6797-dvfsp-handoff-observer "
            "11015000.dvfsp-observer: state=unknown i2c6_policy=disabled\n"
        )
        mutated = replace_exact(
            make_capture(),
            "__AN_DMESG_END__",
            injected + "__AN_DMESG_END__",
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_per_cpu_stall_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            "cpu7 117 0 0 900 0 0 0 0 0 0",
            "cpu7 107 0 0 900 0 0 0 0 0 0",
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_boot_id_change_between_reads_is_rejected(self) -> None:
        original = make_capture()
        state2 = VALIDATOR.section(original, "STATE2")
        changed_state2 = replace_exact(
            state2,
            f"boot_id={BOOT_ID}",
            "boot_id=87654321-4321-4abc-8def-1234567890ab",
        )
        mutated = replace_exact(original, state2, changed_state2)
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_usb_session_anchor_removal_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            VALIDATOR.USB_MARKER + "\n__AN_IDENTITY_BEGIN__",
            "__AN_IDENTITY_BEGIN__",
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)

    def test_keymap_helper_mutation_claim_is_rejected(self) -> None:
        mutated = replace_exact(
            make_capture(),
            "keymap_helper_mutating_ioctl=none",
            "keymap_helper_mutating_ioctl=KDSKBENT",
        )
        with self.assertRaises(ValueError):
            validate_fixture(mutated)


if __name__ == "__main__":
    unittest.main()
