#!/usr/bin/env python3
"""Validate AP's exact-runtime-bound inherited native reboot request."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

# Production stays disabled until the final AP identity, runtime validator, and
# private-live-FDT validator have all stopped changing. Tests inject explicit
# fake dependencies and cannot relax this production source gate.
CANDIDATE_AP_SHA256 = (
    "c17ceffbd015f1ed7dca2e6d170839a2c4f0df38c921ee87f8806643c3132914"
)
RUNTIME_VALIDATOR_SHA256 = (
    "ea426aadb4a7bc9b47d3d11baa71a5f61545ebf803eeb51cf078753b62ef2ffe"
)
LIVE_FDT_VALIDATOR_SHA256 = (
    "b8511f4543b2b683971ea60f84fa1f1d064b9c151eead7f9fc0c4d5921776a4a"
)

AP_PADDED_SHA256 = (
    "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
)
REBOOT_SHA256 = (
    "3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7"
)
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
USB_CONTINUATION_PROMPT = "> "
HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1/24"
DEVICE_ENDPOINT = "10.15.19.82:2323"
WRAPPER_LINE = "Candidate AB: kernel restart requested now (BusyBox reboot -n -f)."
USB_PRELUDE_PREFIX = (
    "Direct USB link only: device 10.15.19.82/24, TCP port 2323.",
    "Security: unauthenticated and unencrypted root shell; trusted host only.",
    "Candidate AC status follows:",
    (
        f"{USB_BANNER} entry profile=usb-gadget-ethernet "
        "baseline=candidate-AB storage_access=none "
        "runtime_networking=usb0-static"
    ),
    f"{USB_BANNER} usb0=present wait_seconds=0",
    (
        f"{USB_BANNER} services=launched usb_network=background "
        "worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 "
        "local_console=unchanged watchdog_userspace=none"
    ),
    (
        f"{USB_BANNER} usb0=configured address=10.15.19.82/24 "
        "operstate=up carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} service=nc status=listening address=10.15.19.82 "
        "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
        "direct_link_only=yes"
    ),
)
USB_SESSION_PAIR = (
    (
        f"{USB_BANNER} usb_shell=session-entry usb0_operstate=up "
        "usb0_carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} usb_shell=ready reboot_dispatch=validated privilege=root "
        "authentication=none encryption=none direct_link_only=yes"
    ),
)
USB_PRELUDE_SUFFIX = (
    "",
    "",
    "BusyBox v1.36.1 (Ubuntu 1:1.36.1-6ubuntu3.1) built-in shell (ash)",
    "Enter 'help' for a list of built-in commands.",
    "",
)


def expected_usb_prelude(prior_sessions: int) -> tuple[str, ...]:
    if not 1 <= prior_sessions <= 64:
        raise ValueError("validated prior USB session count is out of range")
    return (
        *USB_PRELUDE_PREFIX,
        *(USB_SESSION_PAIR * (prior_sessions + 1)),
        *USB_PRELUDE_SUFFIX,
    )


# The device-inert fixture starts with one validated prior session. Production
# derives its exact cardinality from the already validated runtime capture.
EXPECTED_USB_PRELUDE = expected_usb_prelude(1)

UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
HEX256 = re.compile(r"[0-9a-f]{64}")


@dataclasses.dataclass(frozen=True)
class Dependencies:
    identity: Any
    runtime: Any
    live_fdt: Any
    identity_sha256: str
    runtime_sha256: str
    live_fdt_sha256: str
    collector_path: pathlib.Path | None


@dataclasses.dataclass(frozen=True)
class RuntimeBinding:
    boot_id: str
    interface: str
    capture_sha256: str
    live_fdt_sha256: str
    live_fdt_size: int
    outcome: str
    prior_usb_sessions: int


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pinned(name: str, expected: str, module_name: str) -> ModuleType:
    if HEX256.fullmatch(expected) is None:
        raise ValueError(f"pinned source identity is unresolved: {name}")
    path = SCRIPT_DIR / name
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"pinned source is absent or unsafe: {name}")
    if digest(path.read_bytes()) != expected:
        raise ValueError(f"pinned source identity changed: {name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load pinned source: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_dependencies() -> Dependencies:
    # Identity is loaded first so every later interpretation is downstream of
    # the exact selected AP artifact.
    identity = load_pinned(
        "candidate_ap.py",
        CANDIDATE_AP_SHA256,
        "candidate_ap_native_reboot_identity",
    )
    runtime = load_pinned(
        "validate-runtime.py",
        RUNTIME_VALIDATOR_SHA256,
        "candidate_ap_native_reboot_runtime",
    )
    live_fdt = load_pinned(
        "validate-live-fdt-delta.py",
        LIVE_FDT_VALIDATOR_SHA256,
        "candidate_ap_native_reboot_live_fdt",
    )
    return Dependencies(
        identity=identity,
        runtime=runtime,
        live_fdt=live_fdt,
        identity_sha256=CANDIDATE_AP_SHA256,
        runtime_sha256=RUNTIME_VALIDATOR_SHA256,
        live_fdt_sha256=LIVE_FDT_VALIDATOR_SHA256,
        collector_path=SCRIPT_DIR / "collect-runtime.sh",
    )


def require_source_hashes(dependencies: Dependencies) -> None:
    for label, value in (
        ("Candidate AP identity", dependencies.identity_sha256),
        ("runtime validator", dependencies.runtime_sha256),
        ("live-FDT validator", dependencies.live_fdt_sha256),
    ):
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"{label} source identity is unresolved")


def require_ap_artifact(identity: Any, expected_hash: str) -> None:
    if HEX256.fullmatch(expected_hash) is None:
        raise ValueError("expected installed full-partition SHA-256 is malformed")
    identity.require_artifact_pins()
    if identity.PADDED_SHA256 != AP_PADDED_SHA256:
        raise ValueError("Candidate AP identity source has an unexpected padded hash")
    if expected_hash != identity.PADDED_SHA256:
        raise ValueError(
            "expected installed full-partition SHA-256 is not Candidate AP"
        )
    if expected_hash == identity.AO_PADDED_SHA256:
        raise ValueError("Candidate AP identity collapsed to Candidate AO")
    if HEX256.fullmatch(identity.CONFIG_SHA256) is None:
        raise ValueError("Candidate AP configuration identity is malformed")


def live_fdt_identity(live_fdt: Any) -> tuple[str, int]:
    live_hash = getattr(live_fdt, "EXPECTED_LIVE_FDT_SHA256", "")
    live_size = str(getattr(live_fdt, "EXPECTED_LIVE_FDT_SIZE", ""))
    if HEX256.fullmatch(live_hash) is None:
        raise ValueError("Candidate AP private live-FDT identity is not pinned")
    if (
        not live_size.isdecimal()
        or (len(live_size) > 1 and live_size.startswith("0"))
        or int(live_size) <= 0
    ):
        raise ValueError("Candidate AP private live-FDT size is not pinned")
    return live_hash, int(live_size)


def runtime_binding(
    runtime_text: str,
    expected_installed_full_sha256: str,
    expected_runtime_outcome: str,
    *,
    dependencies: Dependencies,
) -> RuntimeBinding:
    require_source_hashes(dependencies)
    identity = dependencies.identity
    runtime = dependencies.runtime
    require_ap_artifact(identity, expected_installed_full_sha256)
    live_hash, live_size = live_fdt_identity(dependencies.live_fdt)
    if expected_runtime_outcome not in {"PASS", "FAIL"}:
        raise ValueError("expected runtime outcome must be PASS or FAIL")

    normalized = runtime.normalize_capture(runtime_text)
    runtime.validate_structure(normalized)
    identity_values = runtime.key_values(runtime.section(normalized, "IDENTITY"))
    host_values = runtime.key_values(runtime.section(normalized, "HOST"))
    state_values = runtime.key_values(runtime.section(normalized, "STATE1"))
    boot_id = identity_values.get("boot_id", "")
    interface = host_values.get("interface", "")
    if UUID.fullmatch(boot_id) is None:
        raise ValueError("validated Candidate AP runtime boot ID is malformed")
    if (
        re.fullmatch(r"[A-Za-z0-9]+", interface) is None
        or host_values.get("route_interface") != interface
    ):
        raise ValueError("validated Candidate AP runtime USB interface is malformed")
    prior_usb_sessions_value = state_values.get("ac_ready_count", "")
    if (
        not prior_usb_sessions_value.isdecimal()
        or not 1 <= int(prior_usb_sessions_value) <= 64
    ):
        raise ValueError("validated Candidate AP runtime USB session count is malformed")

    if dependencies.collector_path is not None:
        runtime.validate_collector_source(dependencies.collector_path)
    result = runtime.validate(
        runtime_text,
        expected_installed_full_sha256,
        identity.CONFIG_SHA256,
        live_hash,
        boot_id,
    )
    if (
        getattr(result, "outcome", None) != expected_runtime_outcome
        or getattr(result, "boot_id", None) != boot_id
    ):
        raise ValueError(
            "Candidate AP runtime does not have the exact expected outcome"
        )
    return RuntimeBinding(
        boot_id=boot_id,
        interface=interface,
        capture_sha256=digest(runtime_text.encode("utf-8")),
        live_fdt_sha256=live_hash,
        live_fdt_size=live_size,
        outcome=expected_runtime_outcome,
        prior_usb_sessions=int(prior_usb_sessions_value),
    )


def normalized_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r", "").splitlines():
        line = raw
        # The inherited service is an interactive BusyBox shell. Strip only
        # exact leading prompt tokens; prompt-like bytes inside values remain.
        while True:
            if line.startswith(USB_PROMPT):
                line = line.removeprefix(USB_PROMPT)
            elif line.startswith(USB_CONTINUATION_PROMPT):
                line = line.removeprefix(USB_CONTINUATION_PROMPT)
            else:
                break
        lines.append(line)
    return lines


def section_lines(lines: list[str], name: str) -> list[str]:
    begin = f"__AP_NATIVE_{name}_BEGIN__"
    end = f"__AP_NATIVE_{name}_END__"
    if lines.count(begin) != 1 or lines.count(end) != 1:
        raise ValueError(f"native reboot section is absent or duplicated: {name}")
    start = lines.index(begin)
    finish = lines.index(end)
    if finish <= start:
        raise ValueError(f"native reboot section order changed: {name}")
    return lines[start + 1 : finish]


def ordered_fields(
    lines: list[str],
    label: str,
    expected_keys: tuple[str, ...],
) -> dict[str, str]:
    result: dict[str, str] = {}
    order: list[str] = []
    for line in lines:
        key, separator, value = line.partition("=")
        if (
            not separator
            or not key
            or not value
            or key in result
            or "\x00" in value
        ):
            raise ValueError(f"{label} is malformed or duplicated")
        order.append(key)
        result[key] = value
    if tuple(order) != expected_keys:
        raise ValueError(f"{label} order or inventory changed")
    return result


HOST_KEYS = (
    "installed_full_sha256_input",
    "attestation_basis",
    "installed_full_hash_reverified_during_request",
    "device_partition_read_during_request",
    "runtime_capture_sha256",
    "runtime_validation",
    "runtime_outcome",
    "runtime_boot_id",
    "candidate_identity_source_sha256",
    "runtime_validator_source_sha256",
    "live_fdt_validator_source_sha256",
    "live_fdt_sha256",
    "live_fdt_size",
    "native_runtime_preflight",
    "direct_usb_binding",
    "interface",
    "mac",
    "host_address",
    "route_interface",
    "device_endpoint",
    "storage_access",
    "watchdog_access",
    "i2c_access",
    "regulator_access",
    "cpu_control_access",
    "power_state_access",
)
REQUEST_KEYS = (
    "candidate_boot_id",
    "live_boot_id",
    "reboot_sha256",
    "reboot_dispatch",
    "reboot_method",
    "request_authorized",
    "storage_access",
    "device_partition_reads",
    "watchdog_access",
    "i2c_access",
    "regulator_access",
    "cpu_control_access",
    "power_state_access",
    "sync_requested",
    "request_count",
)
RESULT_KEYS = (
    "nc_exit_status",
    "connection_closed_after_request",
    "return_marker_observed",
    "mac_absence_observation_1",
    "mac_absence_observation_2",
    "disconnect_confirmed",
    "requestor_reboot_command_issued",
    "device_partition_reads",
    "device_write_operations",
    "watchdog_access",
    "i2c_access",
    "regulator_access",
    "cpu_control_access",
    "power_state_access",
)


def validate(
    text: str,
    runtime_text: str,
    expected_installed_full_sha256: str,
    expected_runtime_outcome: str,
    *,
    dependencies: Dependencies | None = None,
) -> RuntimeBinding:
    selected = dependencies if dependencies is not None else load_dependencies()
    binding = runtime_binding(
        runtime_text,
        expected_installed_full_sha256,
        expected_runtime_outcome,
        dependencies=selected,
    )

    lines = normalized_lines(text)
    if lines.count(USB_BANNER) != 1:
        raise ValueError(
            "exact inherited AC standalone USB banner is absent or duplicated"
        )

    host = ordered_fields(
        section_lines(lines, "HOST"),
        "native reboot host attestation",
        HOST_KEYS,
    )
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "installed_full_hash_reverified_during_request": "no",
        "device_partition_read_during_request": "no",
        "runtime_capture_sha256": binding.capture_sha256,
        "runtime_validation": (
            "candidate-ap-mt6797-dvfsp-i2c6-consumer-runtime"
        ),
        "runtime_outcome": binding.outcome,
        "runtime_boot_id": binding.boot_id,
        "candidate_identity_source_sha256": selected.identity_sha256,
        "runtime_validator_source_sha256": selected.runtime_sha256,
        "live_fdt_validator_source_sha256": selected.live_fdt_sha256,
        "live_fdt_sha256": binding.live_fdt_sha256,
        "live_fdt_size": str(binding.live_fdt_size),
        "native_runtime_preflight": "candidate-ap-native-reboot-preflight",
        "direct_usb_binding": "yes",
        "mac": HOST_MAC,
        "host_address": HOST_ADDRESS,
        "device_endpoint": DEVICE_ENDPOINT,
        "storage_access": "none",
        "watchdog_access": "none",
        "i2c_access": "none",
        "regulator_access": "none",
        "cpu_control_access": "none",
        "power_state_access": "none",
    }
    for key, value in expected_host.items():
        if host[key] != value:
            raise ValueError(f"native reboot host attestation changed: {key}")
    if (
        re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None
        or host["interface"] != binding.interface
        or host["route_interface"] != host["interface"]
    ):
        raise ValueError("native reboot route is not bound to the validated USB interface")

    request = ordered_fields(
        section_lines(lines, "REQUEST"),
        "native reboot request",
        REQUEST_KEYS,
    )
    expected_request = {
        "candidate_boot_id": binding.boot_id,
        "live_boot_id": binding.boot_id,
        "reboot_sha256": REBOOT_SHA256,
        "reboot_dispatch": "/bin/reboot",
        "reboot_method": "/bin/busybox reboot -n -f",
        "request_authorized": "yes",
        "storage_access": "none",
        "device_partition_reads": "none",
        "watchdog_access": "none",
        "i2c_access": "none",
        "regulator_access": "none",
        "cpu_control_access": "none",
        "power_state_access": "none",
        "sync_requested": "no",
        "request_count": "1",
    }
    if request != expected_request:
        differing = next(
            (
                key
                for key in sorted(set(request) | set(expected_request))
                if request.get(key) != expected_request.get(key)
            ),
            "inventory",
        )
        raise ValueError(f"native reboot request changed: {differing}")

    result = ordered_fields(
        section_lines(lines, "RESULT"),
        "native reboot result",
        RESULT_KEYS,
    )
    expected_result = {
        "connection_closed_after_request": "yes",
        "return_marker_observed": "no",
        "mac_absence_observation_1": "absent",
        "mac_absence_observation_2": "absent",
        "disconnect_confirmed": "yes",
        "requestor_reboot_command_issued": "yes",
        "device_partition_reads": "none",
        "device_write_operations": "none",
        "watchdog_access": "none",
        "i2c_access": "none",
        "regulator_access": "none",
        "cpu_control_access": "none",
        "power_state_access": "none",
    }
    for key, value in expected_result.items():
        if result[key] != value:
            raise ValueError(f"native reboot result changed: {key}")
    if (
        re.fullmatch(r"0|[1-9][0-9]{0,2}", result["nc_exit_status"]) is None
        or int(result["nc_exit_status"]) > 255
    ):
        raise ValueError("native reboot nc exit status is malformed or out of range")

    if lines.count(WRAPPER_LINE) != 1:
        raise ValueError(
            "exact inherited native reboot wrapper line is absent or duplicated"
        )
    if "__AP_NATIVE_REBOOT_RETURNED__" in lines:
        raise ValueError("native reboot wrapper returned unexpectedly")

    host_begin = lines.index("__AP_NATIVE_HOST_BEGIN__")
    host_end = lines.index("__AP_NATIVE_HOST_END__")
    banner_index = lines.index(USB_BANNER)
    request_begin = lines.index("__AP_NATIVE_REQUEST_BEGIN__")
    request_end = lines.index("__AP_NATIVE_REQUEST_END__")
    wrapper_index = lines.index(WRAPPER_LINE)
    result_begin = lines.index("__AP_NATIVE_RESULT_BEGIN__")
    result_end = lines.index("__AP_NATIVE_RESULT_END__")
    if not (
        host_begin
        < host_end
        < banner_index
        < request_begin
        < request_end
        < wrapper_index
        < result_begin
        < result_end
    ):
        raise ValueError("native reboot host/request/result sequence changed")
    usb_prelude = tuple(lines[banner_index + 1 : request_begin])
    wanted_usb_prelude = expected_usb_prelude(binding.prior_usb_sessions)
    if usb_prelude != wanted_usb_prelude:
        differing = next(
            (
                index
                for index, (actual, expected) in enumerate(
                    zip(usb_prelude, wanted_usb_prelude, strict=False),
                    start=1,
                )
                if actual != expected
            ),
            min(len(usb_prelude), len(wanted_usb_prelude)) + 1,
        )
        raise ValueError(
            "native reboot inherited USB prelude changed "
            f"at normalized line {differing}"
        )
    outside_components = (
        lines[:host_begin],
        lines[host_end + 1 : banner_index],
        lines[request_end + 1 : wrapper_index],
        lines[wrapper_index + 1 : result_begin],
        lines[result_end + 1 :],
    )
    if any(line for gap in outside_components for line in gap):
        raise ValueError("native reboot transcript envelope changed")

    haystack = "\n".join(lines).lower()
    forbidden = (
        "/dev/mmc",
        "/dev/watchdog",
        "/dev/i2c-",
        "/dev/mem",
        "/dev/port",
        "/sys/power",
        "/sys/class/regulator",
        "/sys/devices/system/cpu",
        "i2cget",
        "i2cset",
        "i2ctransfer",
        "devmem",
        "chcpu",
        "shutdown",
        "poweroff",
        "sync_requested=yes",
    )
    if any(token in haystack for token in forbidden):
        raise ValueError("native reboot transcript contains forbidden hardware access")
    return binding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path)
    parser.add_argument("--runtime-capture", type=pathlib.Path, required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument(
        "--expected-runtime-outcome",
        required=True,
        choices=("PASS", "FAIL"),
    )
    parser.add_argument(
        "--preflight-runtime",
        action="store_true",
        help="validate pinned dependencies and the exact AP runtime only",
    )
    args = parser.parse_args()
    try:
        runtime_bytes = args.runtime_capture.read_bytes()
        runtime_text = runtime_bytes.decode("utf-8", errors="strict")
        if args.preflight_runtime:
            if args.capture is not None:
                raise ValueError("--capture is incompatible with --preflight-runtime")
            dependencies = load_dependencies()
            binding = runtime_binding(
                runtime_text,
                args.expected_installed_full_sha256,
                args.expected_runtime_outcome,
                dependencies=dependencies,
            )
            print("validation=candidate-ap-native-reboot-preflight")
            print(f"candidate_boot_id={binding.boot_id}")
            print(f"runtime_capture_sha256={binding.capture_sha256}")
            print(f"interface={binding.interface}")
            print(f"live_fdt_sha256={binding.live_fdt_sha256}")
            print(f"live_fdt_size={binding.live_fdt_size}")
            print(f"candidate_identity_source_sha256={dependencies.identity_sha256}")
            print(f"runtime_validator_source_sha256={dependencies.runtime_sha256}")
            print(f"live_fdt_validator_source_sha256={dependencies.live_fdt_sha256}")
            print(f"runtime_outcome={binding.outcome}")
            print("exact_runtime_boot_id_and_live_fdt_binding=passed")
            print("device_access=none")
            return 0
        if args.capture is None:
            raise ValueError("--capture is required without --preflight-runtime")
        capture_text = args.capture.read_bytes().decode("utf-8", errors="strict")
        binding = validate(
            capture_text,
            runtime_text,
            args.expected_installed_full_sha256,
            args.expected_runtime_outcome,
        )
        print("validation=candidate-ap-native-reboot-request")
        print(f"candidate_boot_id={binding.boot_id}")
        print(f"runtime_capture_sha256={binding.capture_sha256}")
        print(f"live_fdt_sha256={binding.live_fdt_sha256}")
        print(f"runtime_outcome={binding.outcome}")
        print(f"reboot_sha256={REBOOT_SHA256}")
        print("dispatch=/bin/reboot")
        print("method=/bin/busybox-reboot-n-f")
        print("fresh_runtime_boot_id_gate=passed")
        print("connection_closed_after_request=passed")
        print("disconnect=two-stable-exact-mac-absence-observations")
        print("device_partition_reads=none")
        print("device_write_operations=none")
        print("watchdog_i2c_regulator_cpu_power_state_access=none")
        return 0
    except (
        AttributeError,
        KeyError,
        OSError,
        OverflowError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
