#!/usr/bin/env python3
"""Run Quasar's fixed native-path diagnostic once and preserve evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys
from types import ModuleType

sys.dont_write_bytecode = True


VEGA_RUNNER = (
    "experiments/2026-07-27-mt6797-i2c6-vega/"
    "scripts/run-vega-one-shot.py"
)
VEGA_RUNNER_SHA256 = (
    "508f08eaeac9437aa6c93d05141ce830f06d8ff50b95523c4d8966d9eaa4d2ba"
)
VEGA_PACKAGE_VALIDATOR_SHA256 = (
    "ef07f12d82c4db233f30a535500e0a688bcb13228b94fea7f8618fa4a6344eee"
)
PACKAGE_VALIDATOR_SHA256 = (
    "bdf18fcf4b8dd1668ff80d50645ea57488e98eee05bb6eb65520faaad40602d5"
)
RESULT_VALIDATOR_SHA256 = (
    "0a2c532dae2ff19438cdfecc0b12ac8c473b23a4b7a40dfce1c151cd9acc19f5"
)


class RunnerError(ValueError):
    """The local or remote Quasar runtime contract changed."""


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise RunnerError(
            f"runner token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise RunnerError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def derive_base_source(source: str) -> str:
    replacements = (
        ("VEGA", "QUASAR", 138),
        ("Vega", "Quasar", 96),
        ("vega", "quasar", 36),
        ("orion-run-all", "quasar-run-native", 4),
        (
            VEGA_PACKAGE_VALIDATOR_SHA256,
            PACKAGE_VALIDATOR_SHA256,
            1,
        ),
    )
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    restored = text
    for old, new, count in reversed(replacements):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise RunnerError("Quasar runner cannot restore exact Vega foundation")
    required = {
        "import candidate_quasar as co": 1,
        '"validate-package-quasar.py"': 1,
        'KERNEL_RELEASE = "7.1.3-gemini-quasar"': 1,
        "GEMINI_QUASAR_20260727": 1,
        "quasar-run-native": 4,
        "guard_path=/run/quasar-run-all.invoked": 1,
        "debugfs_root=/run/quasar-debugfs": 1,
        "printf 'run\\n' >\"$diag\"": 2,
        "run_transport(args.interface, program)": 1,
        "post_capture=unconditional-even-after-negative-write": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise RunnerError(
                f"derived Quasar runner contract changed for {token!r}"
            )
    for stale in (
        "candidate_vega",
        "validate-package-vega.py",
        "gemini-vega",
        "GEMINI_VEGA_20260727",
        "orion-run-all",
    ):
        if stale in text:
            raise RunnerError(f"derived Quasar runner retained stale token: {stale}")
    return text


def load_base() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    source_data = regular(repository / VEGA_RUNNER, "source-pinned Vega runner")
    if hashlib.sha256(source_data).hexdigest() != VEGA_RUNNER_SHA256:
        raise RunnerError("source-pinned Vega one-shot runner changed")
    source = derive_base_source(source_data.decode("utf-8", "strict"))
    name = "quasar_runner_derived_base"
    module = ModuleType(name)
    module.__file__ = os.fspath(script)
    module.__package__ = ""
    sys.modules[name] = module
    sys.path.insert(0, os.fspath(script.parent))
    try:
        exec(compile(source, os.fspath(script), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        del sys.path[0]
    module.PACKAGE_VALIDATOR_SHA256 = PACKAGE_VALIDATOR_SHA256
    return module


_BASE = load_base()


def load_result_validator() -> ModuleType:
    path = pathlib.Path(__file__).with_name("validate-quasar-result.py")
    return _BASE.load_source_pinned_module(
        path,
        RESULT_VALIDATOR_SHA256,
        "Quasar result validator",
        "quasar_result_validator_runtime",
    )


def configure_base(result_validator: ModuleType) -> None:
    _BASE.DIAGNOSTIC_STATUS_PRE = result_validator.exact_ready_status()
    if _BASE.KERNEL_RELEASE != "7.1.3-gemini-quasar":
        raise RunnerError("derived Quasar kernel identity changed")
    if (
        _BASE.KERNEL_CMDLINE.count("GEMINI_QUASAR_20260727") != 1
        or "GEMINI_VEGA" in _BASE.KERNEL_CMDLINE
    ):
        raise RunnerError("derived Quasar command-line identity changed")


def classify_kernel_log(log: str) -> dict[str, int]:
    patterns = {
        "fatal": re.compile(
            r"BUG:|WARNING:|Oops:|Kernel panic|Call trace:|"
            r"Unhandled fault|Internal error"
        ),
        "i2c_timeout": re.compile(r"i2c.*timeout|timeout.*i2c", re.IGNORECASE),
        "quasar_ready": re.compile(
            r"GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready "
            r"one_shot=unused mode=none forced_length_mode=none "
            r"forced_engine=none reset_pending=0"
        ),
        "orion_ready": re.compile(r"GEMINI_ORION_DIAGNOSTIC state=ready"),
    }
    return {
        label: sum(bool(pattern.search(line)) for line in log.splitlines())
        for label, pattern in patterns.items()
    }


def validate_i2c_status(
    text: str,
    header: dict[str, str],
) -> None:
    section = _BASE.unique_section(
        text,
        "__QUASAR_I2C_STATUS_POST_BEGIN__",
        "__QUASAR_I2C_STATUS_POST_END__",
    )
    values = _BASE.marker_values(section)
    expected_fields = {
        "handoff",
        "probe_attempts",
        "init_attempts",
        "init_successes",
        "clock_ungated_checks",
        "clock_gated_checks",
        "clock_validation_failures",
        "runtime_pm_link",
        "clock_domains",
        "transfer_attempts",
        "dma_starts",
        "nonzero_starts",
        "irq_count",
        "suspend_checks",
        "resume_checks",
        "resume_failures",
    }
    if set(values) != expected_fields:
        raise RunnerError("Quasar post-run I2C status inventory changed")
    exact = {
        "handoff": "ready",
        "probe_attempts": "1",
        "init_attempts": header["init_attempts_after"],
        "init_successes": header["init_successes_after"],
        "clock_ungated_checks": "1",
        "clock_gated_checks": "1",
        "clock_validation_failures": "0",
        "runtime_pm_link": "1",
        "clock_domains": "i2c-appm,ap-dma",
        "transfer_attempts": header["transfer_attempts_after"],
        "dma_starts": header["dma_starts_after"],
        "nonzero_starts": header["nonzero_starts_after"],
        "irq_count": header["irqs_after"],
        "suspend_checks": "0",
        "resume_checks": "0",
        "resume_failures": "0",
    }
    for key, wanted in exact.items():
        if values.get(key) != wanted:
            raise RunnerError(f"Quasar post-run I2C status changed: {key}")


def validate_post_state(
    text: str,
    gate: dict[str, str],
    classification: str,
) -> str:
    post = _BASE.key_values(
        _BASE.unique_section(
            text,
            "__QUASAR_POST_BEGIN__",
            "__QUASAR_POST_END__",
        ),
        "Quasar post state",
    )
    required = {
        "quasar_final_rc": "0",
        "i2c_status_post_rc": "0",
        "dmesg_rc": "0",
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
    if set(post) != set(required) | {"boot_id_post", "write_rc"}:
        raise RunnerError("Quasar post-run field inventory changed")
    for key, wanted in required.items():
        if post.get(key) != wanted:
            raise RunnerError(f"Quasar post-run state changed: {key}")
    if post["boot_id_post"] != gate["boot_id_pre"]:
        raise RunnerError("Quasar boot ID changed during the one-shot")
    write_rc = post["write_rc"]
    if not write_rc.isdecimal() or int(write_rc, 10) > 255:
        raise RunnerError("Quasar debugfs write status is malformed")
    if classification == "complete-success" and write_rc != "0":
        raise RunnerError("successful Quasar result had a negative write")
    if classification != "complete-success" and write_rc == "0":
        raise RunnerError("failed Quasar result had a successful write")
    complete = next(
        line
        for line in text.splitlines()
        if line.startswith("__QUASAR_COMPLETE__")
    )
    expected = (
        f"__QUASAR_COMPLETE__ write_rc={write_rc} "
        "invocation_count=1 guard_mode=400:0:0 "
        "post_capture=unconditional"
    )
    if complete != expected:
        raise RunnerError("Quasar completion marker changed")
    return write_rc


def validate_capture(
    data: bytes,
    config_sha256: str,
    result_validator: ModuleType,
) -> tuple[str, bytes, str]:
    if not data or len(data) > 8 * 1024 * 1024 or b"\0" in data:
        raise RunnerError("transport output is empty, oversized, or binary")
    try:
        text = data.decode("ascii", "strict")
    except UnicodeError as exc:
        raise RunnerError("transport output is not ASCII") from exc
    session_count, topology = _BASE.validate_capture_envelope(text, config_sha256)
    if "__QUASAR_ABORT__" in text:
        raise RunnerError("remote Quasar gate aborted")
    _BASE.validate_success_transcript_framing(text)
    ordered = (
        "__QUASAR_ADAPTER_TOPOLOGY_BEGIN__",
        "__QUASAR_ADAPTER_TOPOLOGY_END__",
        "__QUASAR_GATE_BEGIN__",
        "__QUASAR_FINAL_REVALIDATION_BEGIN__",
        "__QUASAR_FINAL_REVALIDATION_END__",
        "__QUASAR_GATE_END__",
        "__QUASAR_GATE_PASS__",
        "__QUASAR_FINAL_BEGIN__",
        "__QUASAR_FINAL_END__",
        "__QUASAR_I2C_STATUS_POST_BEGIN__",
        "__QUASAR_I2C_STATUS_POST_END__",
        "__QUASAR_POST_BEGIN__",
        "__QUASAR_POST_END__",
        "__QUASAR_AC_STATUS_POST_BEGIN__",
        "__QUASAR_AC_STATUS_POST_END__",
        "__QUASAR_DMESG_RAW_BEGIN__",
        "__QUASAR_DMESG_RAW_END__",
        "__QUASAR_COMPLETE__",
    )
    positions: list[int] = []
    for marker in ordered:
        if text.count(marker) != 1:
            raise RunnerError(f"capture marker is absent or duplicated: {marker}")
        positions.append(text.index(marker))
    if positions != sorted(positions):
        raise RunnerError("Quasar capture marker order changed")

    gate = _BASE.parse_gate_revalidation(
        _BASE.exact_line_section(
            text,
            "__QUASAR_GATE_BEGIN__",
            "__QUASAR_GATE_END__",
            "Quasar gate",
        ),
        config_sha256,
        topology,
        session_count,
        None,
    )
    final_text = _BASE.unique_section(
        text,
        "__QUASAR_FINAL_BEGIN__",
        "__QUASAR_FINAL_END__",
    )
    final_data = (final_text + "\n").encode("ascii")
    result = result_validator.validate_text(final_data)
    validate_i2c_status(text, result.header)
    write_rc = validate_post_state(text, gate, result.classification)

    log = _BASE.unique_section(
        text,
        "__QUASAR_DMESG_RAW_BEGIN__",
        "__QUASAR_DMESG_RAW_END__",
    )
    counts = classify_kernel_log(log)
    if counts["quasar_ready"] != 1:
        raise RunnerError("Quasar ready kernel marker is absent or duplicated")
    if counts["orion_ready"]:
        raise RunnerError("Quasar kernel log exposes the compiled-out Orion endpoint")
    if counts["fatal"]:
        raise RunnerError("Quasar kernel log contains a fatal warning signature")
    sanitized = "\n".join(
        (
            "validation=quasar-runtime-one-shot",
            f"classification={result.classification}",
            f"config_sha256={config_sha256}",
            f"raw_kernel_log_sha256={hashlib.sha256(log.encode('ascii')).hexdigest()}",
            f"raw_kernel_log_fatal_count={counts['fatal']}",
            f"raw_kernel_log_i2c_timeout_count={counts['i2c_timeout']}",
            f"raw_kernel_log_quasar_ready_count={counts['quasar_ready']}",
            f"raw_kernel_log_orion_ready_count={counts['orion_ready']}",
            f"boot_id_sha256={hashlib.sha256(gate['boot_id_pre'].encode()).hexdigest()}",
            f"write_rc={write_rc}",
            "invocation_count=1",
            "post_capture=unconditional",
            "raw_dmesg_address_lines=private-not-copied",
            *result.summary_lines,
            "",
        )
    )
    return result.classification, final_data, sanitized


def static_runtime_contract(result_validator: ModuleType) -> bytes:
    configure_base(result_validator)
    program = _BASE.build_remote_program("0" * 64)
    text = program.decode("ascii")
    if text.count("printf 'run\\n' >\"$diag\"") != 1:
        raise RunnerError("Quasar remote program does not contain one exact write")
    if "/bin/busybox nc " in text or "ssh " in text or "reboot " in text:
        raise RunnerError("Quasar remote program gained an extra session or reboot")
    if "quasar-run-native" not in text or "orion-run-all" in text:
        raise RunnerError("Quasar runtime endpoint changed")
    return program


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        repository = pathlib.Path(__file__).resolve().parents[3]
        result_validator = load_result_validator()
        configure_base(result_validator)
        package = args.package.resolve(strict=True)
        config_sha256 = _BASE.validate_package(repository, package)
        program = _BASE.build_remote_program(config_sha256)
        static_runtime_contract(result_validator)
        _BASE.verify_host_link(args.interface)
        output = _BASE.prepare_output(repository, args.output_dir)
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        transport = _BASE.run_transport(args.interface, program)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        _BASE.write_private(output / _BASE.TRANSCRIPT_NAME, stdout)
        _BASE.write_private(output / _BASE.STDERR_NAME, stderr or b"\n")
        print(
            f"error: transport timed out; private raw evidence preserved in {output}",
            file=sys.stderr,
        )
        return 2

    # Preserve raw bytes before any parsing. The dmesg frame may contain
    # physical or DMA addresses and remains beneath the private mode-0700 root.
    _BASE.write_private(output / _BASE.TRANSCRIPT_NAME, transport.stdout)
    _BASE.write_private(
        output / _BASE.STDERR_NAME,
        transport.stderr or b"\n",
    )
    try:
        classification, final_data, sanitized = validate_capture(
            transport.stdout,
            config_sha256,
            result_validator,
        )
        _BASE.write_private(output / _BASE.RESULT_NAME, final_data)
        _BASE.write_private(
            output / _BASE.SUMMARY_NAME,
            sanitized.encode("ascii"),
        )
        if transport.returncode:
            raise RunnerError(
                f"network transport exited {transport.returncode} after capture"
            )
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(
            f"error: {exc}; private raw evidence preserved in {output}",
            file=sys.stderr,
        )
        return 2

    print("validation=quasar-exact-serviceability-gated-one-shot")
    print(f"classification={classification}")
    print(f"config_sha256={config_sha256}")
    print(f"raw_transcript_sha256={hashlib.sha256(transport.stdout).hexdigest()}")
    stderr = transport.stderr or b"\n"
    print(f"raw_stderr_sha256={hashlib.sha256(stderr).hexdigest()}")
    print(f"private_output={output}")
    print("invocation_count=1")
    print("initial_observation_session=none")
    print("post_capture=unconditional-even-after-negative-write")
    print("raw_dmesg=private-only-address-bearing-lines-not-sanitized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
