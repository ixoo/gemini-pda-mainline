#!/usr/bin/env python3
"""Validate AK's fresh-boot-ID-gated inherited native reboot request."""

from __future__ import annotations

import argparse
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

# Calibrate these only after Candidate AK's identity module and exact runtime
# validator are final.  The production validator refuses evidence while either
# source pin remains unresolved.
CANDIDATE_AK_SHA256 = "c52e133767f305045664b2274883e8f145170ee4fd8ae34418b7a14ed42360a0"
RUNTIME_VALIDATOR_SHA256 = "a92e64259e60f05ce5a8b96d2582307fd3d4167eafe9e60295a9bdb8491bdf83"

REBOOT_SHA256 = "3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7"
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
USB_CONTINUATION_PROMPT = "> "
HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1/24"
DEVICE_ENDPOINT = "10.15.19.82:2323"
WRAPPER_LINE = "Candidate AB: kernel restart requested now (BusyBox reboot -n -f)."
EXPECTED_USB_PRELUDE = (
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
        "operstate=down carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} service=nc status=listening address=10.15.19.82 "
        "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
        "direct_link_only=yes"
    ),
    (
        f"{USB_BANNER} usb_shell=session-entry usb0_operstate=up "
        "usb0_carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} usb_shell=ready reboot_dispatch=validated privilege=root "
        "authentication=none encryption=none direct_link_only=yes"
    ),
    (
        f"{USB_BANNER} usb_shell=session-entry usb0_operstate=up "
        "usb0_carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} usb_shell=ready reboot_dispatch=validated privilege=root "
        "authentication=none encryption=none direct_link_only=yes"
    ),
    "",
    "",
    "BusyBox v1.36.1 (Ubuntu 1:1.36.1-6ubuntu3.1) built-in shell (ash)",
    "Enter 'help' for a list of built-in commands.",
    "",
)
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
HEX256 = re.compile(r"[0-9a-f]{64}")


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


def load_dependencies() -> tuple[ModuleType, ModuleType]:
    # Load identity first so evidence interpretation is always downstream of
    # the selected production artifact identity.
    ak = load_pinned("candidate_ak.py", CANDIDATE_AK_SHA256, "ak_native_identity")
    runtime = load_pinned(
        "validate-runtime.py",
        RUNTIME_VALIDATOR_SHA256,
        "ak_native_runtime_validator",
    )
    return ak, runtime


def normalized_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r", "").splitlines():
        line = raw
        # The development service is an interactive BusyBox shell. Strip only
        # exact leading PS1/PS2 tokens; prompt-like bytes inside a value remain
        # part of the evidence.
        while True:
            if line.startswith(USB_PROMPT):
                line = line.removeprefix(USB_PROMPT)
            elif line.startswith(USB_CONTINUATION_PROMPT):
                line = line.removeprefix(USB_CONTINUATION_PROMPT)
            else:
                break
        lines.append(line)
    return lines


def section(text: str, name: str) -> str:
    lines = normalized_lines(text)
    begin = f"__AK_NATIVE_{name}_BEGIN__"
    end = f"__AK_NATIVE_{name}_END__"
    if lines.count(begin) != 1 or lines.count(end) != 1:
        raise ValueError(f"native reboot section is absent or duplicated: {name}")
    start = lines.index(begin)
    finish = lines.index(end)
    if finish <= start:
        raise ValueError(f"native reboot section order changed: {name}")
    return "\n".join(lines[start + 1 : finish])


def key_values(text: str, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result or "\x00" in value:
            raise ValueError(f"{label} is malformed or duplicated")
        result[key] = value
    return result


def require_ak_artifact(ak: Any, expected_hash: str) -> None:
    if HEX256.fullmatch(expected_hash) is None:
        raise ValueError("expected installed full-partition SHA-256 is malformed")
    ak.require_artifact_pins()
    if HEX256.fullmatch(ak.PADDED_SHA256) is None:
        raise ValueError("Candidate AK padded identity is malformed")
    if expected_hash != ak.PADDED_SHA256:
        raise ValueError(
            "expected installed full-partition SHA-256 is not Candidate AK"
        )
    if expected_hash == ak.AJ_PADDED_SHA256:
        raise ValueError("Candidate AK identity collapsed to its AJ predecessor")


def runtime_boot_id(runtime: Any, runtime_text: str, expected_hash: str) -> str:
    runtime.validate(runtime_text, expected_hash)
    identity = runtime.key_values(
        runtime.section(runtime_text, "IDENTITY"), "runtime identity"
    )
    boot_id = identity.get("boot_id", "")
    if UUID.fullmatch(boot_id) is None:
        raise ValueError("validated runtime boot ID is malformed")
    return boot_id


def validate(
    text: str,
    runtime_text: str,
    expected_installed_full_sha256: str,
    *,
    dependencies: tuple[Any, Any] | None = None,
) -> str:
    ak, runtime = dependencies if dependencies is not None else load_dependencies()
    require_ak_artifact(ak, expected_installed_full_sha256)
    boot_id = runtime_boot_id(runtime, runtime_text, expected_installed_full_sha256)

    lines = normalized_lines(text)
    if lines.count(USB_BANNER) != 1:
        raise ValueError("exact inherited AC standalone USB banner is absent or duplicated")

    host = key_values(section(text, "HOST"), "native reboot host attestation")
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "installed_full_hash_reverified_during_request": "no",
        "device_partition_read_during_request": "no",
        "runtime_capture_sha256": digest(runtime_text.encode("utf-8")),
        "runtime_validation": "candidate-ak-usb-cpu-runtime-subgate",
        "native_runtime_preflight": "candidate-ak-native-reboot-preflight",
        "mac": HOST_MAC,
        "host_address": HOST_ADDRESS,
        "device_endpoint": DEVICE_ENDPOINT,
        "storage_access": "none",
    }
    if set(host) != set(expected_host) | {"interface", "route_interface"}:
        raise ValueError("native reboot host inventory changed")
    for key, value in expected_host.items():
        if host[key] != value:
            raise ValueError(f"native reboot host attestation changed: {key}")
    if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
        raise ValueError("native reboot interface is malformed")
    if host["route_interface"] != host["interface"]:
        raise ValueError("native reboot route is not bound to the USB interface")

    request = key_values(section(text, "REQUEST"), "native reboot request")
    expected_request = {
        "candidate_boot_id": boot_id,
        "live_boot_id": boot_id,
        "reboot_sha256": REBOOT_SHA256,
        "reboot_dispatch": "/bin/reboot",
        "reboot_method": "/bin/busybox reboot -n -f",
        "request_authorized": "yes",
        "storage_access": "none",
        "sync_requested": "no",
        "watchdog_userspace": "none",
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

    result = key_values(section(text, "RESULT"), "native reboot result")
    expected_result = {
        "connection_closed_after_request": "yes",
        "mac_absence_observation_1": "absent",
        "mac_absence_observation_2": "absent",
        "disconnect_confirmed": "yes",
        "requestor_reboot_command_issued": "yes",
        "device_partition_reads": "none",
        "device_write_operations": "none",
    }
    if set(result) != set(expected_result) | {"nc_exit_status"}:
        raise ValueError("native reboot result inventory changed")
    for key, value in expected_result.items():
        if result[key] != value:
            raise ValueError(f"native reboot result changed: {key}")
    if re.fullmatch(r"0|[1-9][0-9]{0,2}", result["nc_exit_status"]) is None:
        raise ValueError("native reboot nc exit status is malformed")
    if int(result["nc_exit_status"]) > 255:
        raise ValueError("native reboot nc exit status is out of range")

    if lines.count(WRAPPER_LINE) != 1:
        raise ValueError("exact inherited native reboot wrapper line is absent or duplicated")
    if "__AK_NATIVE_REBOOT_RETURNED__" in lines:
        raise ValueError("native reboot wrapper returned unexpectedly")
    host_begin = lines.index("__AK_NATIVE_HOST_BEGIN__")
    host_end = lines.index("__AK_NATIVE_HOST_END__")
    banner_index = lines.index(USB_BANNER)
    request_begin = lines.index("__AK_NATIVE_REQUEST_BEGIN__")
    request_end = lines.index("__AK_NATIVE_REQUEST_END__")
    wrapper_index = lines.index(WRAPPER_LINE)
    result_begin = lines.index("__AK_NATIVE_RESULT_BEGIN__")
    result_end = lines.index("__AK_NATIVE_RESULT_END__")
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
    if usb_prelude != EXPECTED_USB_PRELUDE:
        differing = next(
            (
                index
                for index, (actual, expected) in enumerate(
                    zip(usb_prelude, EXPECTED_USB_PRELUDE, strict=False),
                    start=1,
                )
                if actual != expected
            ),
            min(len(usb_prelude), len(EXPECTED_USB_PRELUDE)) + 1,
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
    forbidden = (
        "/dev/watchdog",
        "shutdown",
        "poweroff",
        "reboot -d",
        "sync_requested=yes",
    )
    haystack = "\n".join(lines).lower()
    if any(token in haystack for token in forbidden):
        raise ValueError("native reboot transcript contains a forbidden fallback")
    return boot_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path)
    parser.add_argument("--runtime-capture", type=pathlib.Path, required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument(
        "--preflight-runtime",
        action="store_true",
        help="validate pinned dependencies and the exact runtime only",
    )
    args = parser.parse_args()
    try:
        runtime_text = args.runtime_capture.read_bytes().decode(
            "utf-8", errors="strict"
        )
        if args.preflight_runtime:
            if args.capture is not None:
                raise ValueError("--capture is incompatible with --preflight-runtime")
            ak, runtime = load_dependencies()
            require_ak_artifact(ak, args.expected_installed_full_sha256)
            boot_id = runtime_boot_id(
                runtime,
                runtime_text,
                args.expected_installed_full_sha256,
            )
            print("validation=candidate-ak-native-reboot-preflight")
            print(f"candidate_boot_id={boot_id}")
            print("exact_runtime_binding=passed")
            print("device_access=none")
            return 0
        if args.capture is None:
            raise ValueError("--capture is required without --preflight-runtime")
        # Decode bytes explicitly so CRLF is retained for the runtime SHA bind.
        text = args.capture.read_bytes().decode("utf-8", errors="strict")
        boot_id = validate(text, runtime_text, args.expected_installed_full_sha256)
        print("validation=candidate-ak-native-reboot-request")
        print(f"candidate_boot_id={boot_id}")
        print(f"reboot_sha256={REBOOT_SHA256}")
        print("dispatch=/bin/reboot")
        print("method=/bin/busybox-reboot-n-f")
        print("fresh_runtime_boot_id_gate=passed")
        print("disconnect=two-exact-mac-absence-observations")
        print("device_partition_reads=none")
        print("device_write_operations=none")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
