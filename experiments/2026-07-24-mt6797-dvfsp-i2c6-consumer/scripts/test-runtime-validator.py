#!/usr/bin/env python3
"""Device-inert unit and mutation tests for Candidate AP runtime validation."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True

SOURCE = pathlib.Path(__file__).with_name("validate-runtime.py")
SPEC = importlib.util.spec_from_file_location("candidate_ap_runtime_validator", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AP runtime validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

INSTALLED_SHA256 = "a" * 64
CONFIG_SHA256 = "b" * 64
FDT_SHA256 = "c" * 64
BOOT_ID = "12345678-1234-4abc-8def-1234567890ab"
DMA_UNGATED = 0x0242C876
DMA_GATED = 0x0246C876
FIRST_DMA_GATED = 5


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
        "dma_gate_valid": True,
        "dma_gate": DMA_GATED,
    }
    values.update(changes)
    return VALIDATOR.Snapshot(**values)


def ready_snapshots() -> tuple[VALIDATOR.Snapshot, ...]:
    result: list[VALIDATOR.Snapshot] = []
    for name in VALIDATOR.SAMPLE_ORDER:
        result.append(
            snapshot(
                name,
                gated=name in {"post", "late", "consumer-post"},
                dma_gate=DMA_UNGATED if name == "consumer-held" else DMA_GATED,
            )
        )
    return tuple(result)


def inconclusive_snapshots() -> tuple[VALIDATOR.Snapshot, ...]:
    return tuple(snapshot(name, gated=True) for name in VALIDATOR.PRE_SAMPLE_ORDER)


def faulted_snapshots() -> tuple[VALIDATOR.Snapshot, ...]:
    samples = list(ready_snapshots())
    index = VALIDATOR.SAMPLE_ORDER.index("consumer-post")
    samples[index] = dataclasses.replace(
        samples[index],
        dma_gate=DMA_UNGATED,
    )
    return tuple(samples)


def snapshot_line(sample: VALIDATOR.Snapshot) -> str:
    rsv = ",".join(f"{value:08x}" for value in sample.sw_rsv)
    return (
        f"sample={sample.name} "
        f"timer={sample.timer_before:08x}/{sample.timer_after:08x} "
        f"con0={sample.pcm_con0:08x} con1={sample.pcm_con1:08x} "
        f"pwr_io={sample.pcm_pwr_io_en:08x} "
        f"r15={sample.pcm_reg15_data:08x} "
        f"fsm={sample.pcm_fsm_sta:08x} rsv={rsv} "
        f"gate_valid={int(sample.gate_valid)} gate={sample.gate:08x} "
        f"dma_gate_valid={int(sample.dma_gate_valid)} "
        f"dma_gate={sample.dma_gate:08x}"
    )


def payload(samples: tuple[VALIDATOR.Snapshot, ...]) -> bytes:
    return ("\n".join(snapshot_line(sample) for sample in samples) + "\n").encode()


def cleanup_samples() -> tuple[VALIDATOR.CleanupSample, ...]:
    return tuple(
        VALIDATOR.CleanupSample(
            index=index,
            main_valid=True,
            main=0x00001002,
            dma_valid=True,
            dma=DMA_UNGATED if index < FIRST_DMA_GATED else DMA_GATED,
        )
        for index in range(32)
    )


def cleanup(outcome: str) -> VALIDATOR.Cleanup:
    if outcome == "ready":
        samples = cleanup_samples()
        return VALIDATOR.Cleanup(
            attempts=1,
            samples=samples,
            pcm_failures=0,
            main_failures=0,
            dma_invalid=0,
            dma_gated=len(samples) - FIRST_DMA_GATED,
            selected=FIRST_DMA_GATED,
            result="passed",
        )
    if outcome == "faulted":
        samples = tuple(
            dataclasses.replace(sample, dma=DMA_UNGATED)
            for sample in cleanup_samples()
        )
        return VALIDATOR.Cleanup(
            attempts=1,
            samples=samples,
            pcm_failures=0,
            main_failures=0,
            dma_invalid=0,
            dma_gated=0,
            selected=31,
            result="failed",
        )
    return VALIDATOR.Cleanup(
        attempts=0,
        samples=(),
        pcm_failures=0,
        main_failures=0,
        dma_invalid=0,
        dma_gated=0,
        selected=0,
        result="not-run",
    )


def cleanup_payload(value: VALIDATOR.Cleanup) -> bytes:
    lines = [
        " ".join(
            (
                f"attempts={value.attempts}",
                f"samples={len(value.samples)}",
                f"pcm_failures={value.pcm_failures}",
                f"main_failures={value.main_failures}",
                f"dma_invalid={value.dma_invalid}",
                f"dma_gated={value.dma_gated}",
                f"selected={value.selected}",
                f"result={value.result}",
            )
        )
    ]
    lines.extend(
        " ".join(
            (
                f"i={sample.index:02d}",
                f"main_valid={int(sample.main_valid)}",
                f"main={sample.main:08x}",
                f"dma_valid={int(sample.dma_valid)}",
                f"dma={sample.dma:08x}",
            )
        )
        for sample in value.samples
    )
    return ("\n".join(lines) + "\n").encode()


def status_line(outcome: str, value: VALIDATOR.Cleanup) -> str:
    if outcome == "ready":
        return (
            "state=ready reason=late-validation-passed initial_gate=ungated "
            "supplier_bound=yes access_grant=ready "
            "transition_attempts=1 enable_successes=1 disable_count=1 "
            "late=passed late_checks=1 faults=0 suspend_checks=0 "
            "suspend_failures=0 resume_checks=0 resume_failures=0 pm_fault=none "
            "consumer_ungated_checks=1 "
            "consumer_gated_checks=1 consumer_validation_failures=0 "
            f"cleanup_attempts=1 cleanup_samples=32 cleanup_pcm_failures=0 "
            f"cleanup_main_failures=0 cleanup_dma_invalid=0 "
            f"cleanup_dma_gated={value.dma_gated} "
            f"cleanup_selected={value.selected} cleanup_result=passed "
            "i2c6_policy=requires-ready"
        )
    if outcome == "faulted":
        return (
            "state=faulted reason=consumer-cleanup-validation-failed "
            "initial_gate=ungated supplier_bound=yes access_grant=denied "
            "transition_attempts=1 enable_successes=1 disable_count=1 "
            "late=passed late_checks=1 faults=1 suspend_checks=0 "
            "suspend_failures=0 resume_checks=0 resume_failures=0 pm_fault=none "
            "consumer_ungated_checks=1 consumer_gated_checks=1 "
            "consumer_validation_failures=1 cleanup_attempts=1 "
            "cleanup_samples=32 cleanup_pcm_failures=0 "
            "cleanup_main_failures=0 cleanup_dma_invalid=0 "
            "cleanup_dma_gated=0 cleanup_selected=31 cleanup_result=failed "
            "i2c6_policy=requires-ready"
        )
    return (
        "state=inconclusive reason=initial-gate-already-gated "
        "initial_gate=gated supplier_bound=yes access_grant=denied "
        "transition_attempts=0 enable_successes=0 "
        "disable_count=0 late=not-scheduled late_checks=0 faults=0 "
        "suspend_checks=0 suspend_failures=0 resume_checks=0 "
        "resume_failures=0 pm_fault=none "
        "consumer_ungated_checks=0 consumer_gated_checks=0 "
        "consumer_validation_failures=0 cleanup_attempts=0 cleanup_samples=0 "
        "cleanup_pcm_failures=0 cleanup_main_failures=0 cleanup_dma_invalid=0 "
        "cleanup_dma_gated=0 cleanup_selected=0 cleanup_result=not-run "
        "i2c6_policy=requires-ready"
    )


def i2c_guard_line(*, include_pm: bool, include_domains: bool = False) -> str:
    line = (
        "handoff=ready probe_attempts=1 init_attempts=1 init_successes=1 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
    )
    if include_domains:
        line += "clock_domains=i2c-appm,ap-dma "
    line += (
        "transfer_attempts=0 dma_starts=0 "
        "nonzero_starts=0 irq_count=0"
    )
    if include_pm:
        line += " suspend_checks=0 resume_checks=0 resume_failures=0"
    return line


def key_value_lines(values: dict[str, str]) -> str:
    return "\n".join(f"{key}={value}" for key, value in values.items())


def handoff_dmesg(
    outcome: str,
    samples: tuple[VALIDATOR.Snapshot, ...],
    cleanup_value: VALIDATOR.Cleanup,
) -> list[str]:
    prefix = (
        "[    1.000000] mt6797-dvfsp-handoff "
        "11015000.dvfsp-handoff: "
    )
    by_name = {sample.name: sample for sample in samples}
    lines = [
        prefix
        + "state=validating operation=one-way-handoff "
        "i2c6_policy=requires-ready",
        prefix + snapshot_line(by_name["pre0"]),
        prefix + snapshot_line(by_name["pre1"]),
        prefix + snapshot_line(by_name["pre2"]),
    ]
    if outcome in {"ready", "faulted"}:
        lines.extend(
            (
                prefix
                + "state=normalizing transition=ccf-temporary-reference attempt=1",
                prefix + snapshot_line(by_name["enabled"]),
                prefix + snapshot_line(by_name["post"]),
                prefix
                + "state=provisional normalization=ungated-to-gated "
                "enable_successes=1 disable_count=1 late_validation=pending "
                "delay_ms=45000 i2c6_policy=requires-ready",
                prefix + snapshot_line(by_name["late"]),
                prefix
                + "state=ready normalization=ungated-to-gated "
                "late_validation=passed i2c6_policy=requires-ready",
                prefix
                + "supplier_bound=yes access_grant=ready state=ready "
                "late_validation=passed "
                "access_controller=enabled",
                prefix + snapshot_line(by_name["consumer-held"]),
                prefix
                + "consumer_clock_check=held clocks=i2c-appm,ap-dma "
                "validation=passed "
                "i2c6_policy=requires-ready",
                prefix + snapshot_line(by_name["consumer-post"]),
            )
        )
        if outcome == "ready":
            lines.append(
                prefix
                + "consumer_clock_check=cleanup clocks=i2c-appm,ap-dma "
                f"validation=passed samples=32 "
                f"dma_gated={cleanup_value.dma_gated} "
                f"selected={cleanup_value.selected} "
                "i2c6_policy=requires-ready"
            )
        else:
            lines.extend(
                (
                    prefix
                    + "consumer_clock_check=cleanup clocks=i2c-appm,ap-dma "
                    "validation=failed samples=32 pcm_failures=0 "
                    "main_failures=0 dma_invalid=0 dma_gated=0 selected=31 "
                    "i2c6_policy=requires-ready",
                    prefix
                    + "state=faulted "
                    "reason=consumer-cleanup-validation-failed "
                    "i2c6_policy=requires-ready",
                )
            )
    else:
        lines.extend(
            (
                prefix
                + "state=inconclusive reason=initial-gate-already-gated "
                "transition_attempts=0 i2c6_policy=requires-ready",
                prefix
                + "supplier_bound=yes access_grant=denied state=inconclusive "
                "reason=initial-gate-already-gated access_controller=enabled",
            )
        )
    return lines


def make_capture(outcome: str = "ready") -> str:
    if outcome == "ready":
        samples = ready_snapshots()
    elif outcome == "faulted":
        samples = faulted_snapshots()
    else:
        samples = inconclusive_snapshots()
    raw = payload(samples)
    cleanup_value = cleanup(outcome)
    cleanup_raw = cleanup_payload(cleanup_value)
    host = {
        "installed_full_sha256_input": INSTALLED_SHA256,
        "expected_boot_id_input": BOOT_ID,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "handoff_access_path": "platform-device-read-only-sysfs",
        "i2c_transaction_or_controller_control": "none",
        "regulator_control_or_value_read": "none",
        "cpu_online_control_access": "none",
        "watchdog_control_access": "none",
        "reboot_executed": "no",
        "power_state_transition_requested": "no",
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
            "handoff_status": status_line(outcome, cleanup_value),
            "i2c6_handoff_status": i2c_guard_line(
                include_pm=True, include_domains=True
            ),
            "handoff_snapshots_hex": raw.hex(),
            "handoff_snapshots_sha256": hashlib.sha256(raw).hexdigest(),
            "handoff_snapshot_line_count": str(len(samples)),
            "handoff_consumer_cleanup_hex": cleanup_raw.hex(),
            "handoff_consumer_cleanup_sha256": hashlib.sha256(
                cleanup_raw
            ).hexdigest(),
            "handoff_consumer_cleanup_line_count": str(
                len(cleanup_value.samples)
            ),
            "handoff_device_canonical": (
                "/sys/devices/platform/soc/11015000.dvfsp-handoff"
            ),
            "i2c6_device_canonical": (
                "/sys/devices/platform/soc/1100e000.i2c"
            ),
            "i2c6_handoff_link_consumer_target": (
                "/sys/devices/platform/soc/1100e000.i2c"
            ),
            "i2c6_handoff_link_supplier_target": (
                "/sys/devices/platform/soc/11015000.dvfsp-handoff"
            ),
            "ac_ready_count": "1",
            "boot_id": BOOT_ID,
            "uptime_seconds": "50",
        }
    )
    if outcome == "inconclusive":
        state.update(VALIDATOR.INCONCLUSIVE_STATE_OVERRIDES)
        state["i2c6_handoff_status"] = ""
    elif outcome == "faulted":
        state.update(VALIDATOR.FAULTED_STATE_OVERRIDES)
        state["i2c6_handoff_status"] = ""
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
            *handoff_dmesg(outcome, samples, cleanup_value),
            "initcall mt6797_dvfsp_handoff_driver_init+0x0/0x100 "
            "returned 0 after 22000 usecs",
            *(
                (
                    "i2c-mt65xx 1100e000.i2c: "
                    "GEMINI_MT6797_I2C6_GUARD "
                    + i2c_guard_line(
                        include_pm=False, include_domains=True
                    ),
                )
                if outcome == "ready"
                else (
                    "i2c-mt65xx 1100e000.i2c: "
                    "GEMINI_MT6797_I2C6_GUARD handoff=denied "
                    "probe_attempts=1 reason=supplier-not-ready",
                )
                if outcome == "inconclusive"
                else (
                    "[   48.197516] i2c-mt65xx 1100e000.i2c: "
                    "probe with driver i2c-mt65xx failed with error -5",
                    "[   48.198822] probe of 1100e000.i2c returned 5 "
                    "after 61526 usecs",
                )
            ),
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
            "__AP_HOST_BEGIN__",
            key_value_lines(host),
            "__AP_HOST_END__",
            VALIDATOR.USB_MARKER,
            "__AP_IDENTITY_BEGIN__",
            key_value_lines(identity),
            "__AP_IDENTITY_END__",
            "__AP_STATE1_BEGIN__",
            key_value_lines(state),
            "__AP_STATE1_END__",
            "__AP_STAT1_BEGIN__",
            stat1,
            "__AP_STAT1_END__",
            "__AP_STATE2_BEGIN__",
            key_value_lines(state2),
            "__AP_STATE2_END__",
            "__AP_STAT2_BEGIN__",
            stat2,
            "__AP_STAT2_END__",
            "__AP_DMESG_BEGIN__",
            "\n".join(dmesg),
            "__AP_DMESG_END__",
            "",
        )
    )


def validate_fixture(text: str) -> VALIDATOR.ValidationResult:
    return VALIDATOR.validate(
        text,
        INSTALLED_SHA256,
        CONFIG_SHA256,
        FDT_SHA256,
        BOOT_ID,
    )


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"fixture replacement count changed: expected {count}, found {actual}"
        )
    return text.replace(old, new, 1)


class ClassificationTests(unittest.TestCase):
    def test_ready_requires_exact_eight_sample_transition(self) -> None:
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
            (6, {"gate": 0x1002}),
            (7, {"gate": 0x1000}),
            (6, {"dma_gate_valid": False}),
            (6, {"dma_gate": DMA_GATED}),
            (7, {"dma_gate_valid": False}),
        )
        for index, mutation in mutations:
            with self.subTest(index=index, mutation=mutation):
                samples = list(ready_snapshots())
                samples[index] = dataclasses.replace(samples[index], **mutation)
                with self.assertRaises(ValueError):
                    VALIDATOR.classify(tuple(samples))

    def test_consumer_post_dma_ungated_is_exact_faulted_classification(
        self,
    ) -> None:
        self.assertEqual(VALIDATOR.classify(faulted_snapshots()), "faulted")

    def test_only_i2c_appm_gate_bit_has_semantic_weight(self) -> None:
        samples = list(ready_snapshots())
        unrelated = (
            0x00000000,
            0xFFFFFFFC,
            0x13579BD9,
            0x2468ACF0,
            0x2,
            0xFFFFFFFE,
            0xAAAAAAA8,
            0x55555554,
        )
        for index, value in enumerate(unrelated):
            gated = samples[index].name in {"post", "late", "consumer-post"}
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
            samples[:3] + (samples[4], samples[3]) + samples[5:],
            samples[:3] + (samples[3], samples[3]) + samples[5:],
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

    def test_cleanup_payloads_and_ready_oracle_are_exact(self) -> None:
        for outcome in ("ready", "inconclusive", "faulted"):
            with self.subTest(outcome=outcome):
                expected = cleanup(outcome)
                raw = cleanup_payload(expected)
                parsed = VALIDATOR.parse_cleanup(
                    raw.hex(), hashlib.sha256(raw).hexdigest()
                )
                self.assertEqual(parsed, expected)
                if outcome == "ready":
                    VALIDATOR.validate_ready_cleanup(
                        parsed, ready_snapshots()[-1]
                    )
                elif outcome == "inconclusive":
                    VALIDATOR.validate_inconclusive_cleanup(parsed)
                else:
                    VALIDATOR.validate_faulted_cleanup(
                        parsed, faulted_snapshots()[-1]
                    )

    def test_cleanup_parser_rejects_reorder_hash_and_termination(self) -> None:
        raw = cleanup_payload(cleanup("ready"))
        lines = raw.decode("ascii").splitlines()
        cases = (
            ("\n".join((lines[0], lines[2], lines[1], *lines[3:])) + "\n").encode(),
            raw.replace(b"samples=32", b"samples=31", 1),
            raw.rstrip(b"\n"),
        )
        for mutated in cases:
            with self.subTest():
                with self.assertRaises(ValueError):
                    VALIDATOR.parse_cleanup(
                        mutated.hex(), hashlib.sha256(mutated).hexdigest()
                    )
        with self.assertRaises(ValueError):
            VALIDATOR.parse_cleanup(raw.hex(), "0" * 64)

    def test_cleanup_oracle_rejects_each_dma_and_main_lie(self) -> None:
        base = cleanup("ready")
        samples = list(base.samples)
        mutations: tuple[VALIDATOR.Cleanup, ...] = (
            dataclasses.replace(
                base,
                samples=(
                    dataclasses.replace(samples[0], main=0x00001000),
                    *samples[1:],
                ),
            ),
            dataclasses.replace(
                base,
                samples=(
                    dataclasses.replace(samples[0], dma_valid=False),
                    *samples[1:],
                ),
            ),
            dataclasses.replace(base, dma_gated=base.dma_gated - 1),
            dataclasses.replace(base, selected=base.selected + 1),
            dataclasses.replace(
                base,
                samples=tuple(
                    dataclasses.replace(sample, dma=DMA_UNGATED)
                    for sample in samples
                ),
                dma_gated=0,
                selected=0,
            ),
        )
        for mutated in mutations:
            with self.subTest(mutation=mutated):
                with self.assertRaises(ValueError):
                    VALIDATOR.validate_ready_cleanup(
                        mutated, ready_snapshots()[-1]
                    )

    def test_status_requires_exact_counter_inventory(self) -> None:
        cleanup_value = cleanup("ready")
        status = VALIDATOR.parse_status(status_line("ready", cleanup_value))
        VALIDATOR.validate_status(status, "ready", cleanup_value)
        for field in (
            "enable_successes",
            "suspend_checks",
            "resume_checks",
            "resume_failures",
            "consumer_validation_failures",
        ):
            with self.subTest(field=field):
                mutated = dataclasses.replace(status, **{field: 2})
                with self.assertRaises(ValueError):
                    VALIDATOR.validate_status(
                        mutated, "ready", cleanup_value
                    )

    def test_i2c_sysfs_and_log_payloads_are_distinct_and_quiet(self) -> None:
        VALIDATOR.parse_i2c_guard(
            i2c_guard_line(include_pm=True, include_domains=True),
            include_pm=True,
            include_domains=True,
        )
        VALIDATOR.parse_i2c_guard(
            i2c_guard_line(include_pm=False, include_domains=True),
            include_pm=False,
            include_domains=True,
        )
        with self.assertRaises(ValueError):
            VALIDATOR.parse_i2c_guard(
                "GEMINI_MT6797_I2C6_GUARD "
                + i2c_guard_line(include_pm=True, include_domains=True),
                include_pm=True,
                include_domains=True,
            )
        for counter in (
            "transfer_attempts",
            "dma_starts",
            "nonzero_starts",
            "irq_count",
            "suspend_checks",
            "resume_checks",
            "resume_failures",
        ):
            with self.subTest(counter=counter):
                bad = i2c_guard_line(
                    include_pm=True, include_domains=True
                ).replace(f"{counter}=0", f"{counter}=1")
                with self.assertRaises(ValueError):
                    VALIDATOR.parse_i2c_guard(
                        bad, include_pm=True, include_domains=True
                    )


class FullValidationTests(unittest.TestCase):
    def test_runtime_collector_source_is_exact_and_fail_closed(self) -> None:
        collector = SOURCE.with_name("collect-runtime.sh")
        self.assertEqual(
            hashlib.sha256(collector.read_bytes()).hexdigest(),
            VALIDATOR.COLLECTOR_SHA256,
        )
        VALIDATOR.validate_collector_source(collector)
        with tempfile.TemporaryDirectory() as directory:
            mutated = pathlib.Path(directory) / "collect-runtime.sh"
            mutated.write_bytes(
                collector.read_bytes().replace(
                    b"device_partition_read_during_collection=no",
                    b"device_partition_read_during_collection=yes",
                    1,
                )
            )
            with self.assertRaisesRegex(ValueError, "source identity changed"):
                VALIDATOR.validate_collector_source(mutated)

    def test_ready_capture_passes(self) -> None:
        result = validate_fixture(make_capture("ready"))
        self.assertEqual(result.outcome, "PASS")
        self.assertEqual(result.boot_id, BOOT_ID)

    def test_initially_gated_capture_is_structured_inconclusive(self) -> None:
        result = validate_fixture(make_capture("inconclusive"))
        self.assertEqual(result.outcome, "INCONCLUSIVE")

    def test_cleanup_dma_ungated_capture_is_structured_fail(self) -> None:
        result = validate_fixture(make_capture("faulted"))
        self.assertEqual(result.outcome, "FAIL")
        self.assertEqual(result.boot_id, BOOT_ID)

    def test_faulted_capture_requires_exact_stable_failure_oracle(self) -> None:
        good = make_capture("faulted")
        mutations = (
            good.replace(
                "reason=consumer-cleanup-validation-failed",
                "reason=unexpected-failure",
                1,
            ),
            good.replace("cleanup_selected=31", "cleanup_selected=30", 1),
            good.replace("dma_gated=0 selected=31", "dma_gated=1 selected=31", 1),
            good.replace(
                "probe with driver i2c-mt65xx failed with error -5",
                "probe with driver i2c-mt65xx failed with error -6",
                1,
            ),
            good.replace(
                "state=faulted reason=consumer-cleanup-validation-failed "
                "i2c6_policy=requires-ready",
                "state=faulted reason=consumer-cleanup-validation-failed "
                "i2c6_policy=requires-ready\n"
                "state=faulted reason=consumer-cleanup-validation-failed "
                "i2c6_policy=requires-ready",
                1,
            ),
        )
        for text in mutations:
            with self.subTest():
                with self.assertRaises(ValueError):
                    validate_fixture(text)

    def test_prompt_prefixes_are_normalized(self) -> None:
        text = make_capture("ready")
        text = text.replace(
            "__AP_IDENTITY_BEGIN__",
            "GEMINI-AC-USB# GEMINI-AC-USB# > > "
            "GEMINI-AC-USB# GEMINI-AC-USB# __AP_IDENTITY_BEGIN__",
        )
        text = text.replace("__AP_STATE1_BEGIN__", "GEMINI-AC-USB# __AP_STATE1_BEGIN__")
        self.assertEqual(validate_fixture(text).outcome, "PASS")

    def test_malformed_prompt_prefixes_fail_closed(self) -> None:
        good = make_capture("ready")
        cases = (
            good.replace(
                "__AP_IDENTITY_BEGIN__",
                "GEMINI-AC-USB# > unexpected __AP_IDENTITY_BEGIN__",
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
                "__AP_STATE1_END__\n__AP_STAT1_BEGIN__",
                "__AP_STAT1_BEGIN__\n__AP_STATE1_END__",
            ),
            good.replace("__AP_STATE1_BEGIN__", "__AP_STATE1_BEGIN__\n__AP_STATE1_BEGIN__"),
            good.replace("__AP_STATE1_BEGIN__", "__AP_EXTRA_BEGIN__\n__AP_STATE1_BEGIN__"),
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
        first = drift.index("__AP_STATE2_BEGIN__")
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

    def test_i2c6_transfer_da9214_and_a72_activity_each_fail(self) -> None:
        additions = (
            "i2c-mt65xx 1100e000.i2c: transfer timed out",
            "da9214 6-0068: probe complete",
            "CPU8: Booted secondary processor 0x0000000200 [0x410fd091]",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                text = make_capture().replace(
                    "__AP_DMESG_END__", addition + "\n__AP_DMESG_END__"
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
            "__AP_STAT2_END__",
            "cpu8 1 0 0 1 0 0 0 0 0 0\n__AP_STAT2_END__",
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
            VALIDATOR.validate(
                text, "0" * 64, CONFIG_SHA256, FDT_SHA256, BOOT_ID
            )
        with self.assertRaises(ValueError):
            VALIDATOR.validate(
                text, INSTALLED_SHA256, "0" * 64, FDT_SHA256, BOOT_ID
            )
        with self.assertRaises(ValueError):
            VALIDATOR.validate(
                text, INSTALLED_SHA256, CONFIG_SHA256, "0" * 64, BOOT_ID
            )
        different_boot_id = "87654321-4321-4abc-8def-1234567890ab"
        with self.assertRaisesRegex(ValueError, "expected_boot_id_input"):
            VALIDATOR.validate(
                text,
                INSTALLED_SHA256,
                CONFIG_SHA256,
                FDT_SHA256,
                different_boot_id,
            )
        relabeled = replace_exact(
            text,
            f"expected_boot_id_input={BOOT_ID}",
            f"expected_boot_id_input={different_boot_id}",
        )
        with self.assertRaisesRegex(ValueError, "validated live-FDT boot"):
            VALIDATOR.validate(
                relabeled,
                INSTALLED_SHA256,
                CONFIG_SHA256,
                FDT_SHA256,
                different_boot_id,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
