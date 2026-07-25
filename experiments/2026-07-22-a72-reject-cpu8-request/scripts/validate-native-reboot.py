#!/usr/bin/env python3
"""Validate AJ's boot-ID-gated invocation of the inherited native reboot path."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CANDIDATE_AJ_SHA256 = "77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1"
RUNTIME_VALIDATOR_SHA256 = "e7ec6aa3d9d00fdec8c5d7669956c3c979c21bc228278bcc24d973ef85eff089"
REBOOT_SHA256 = "3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7"
AJ_RAW_SHA256 = "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
AJ_RAW_SIZE = "7380992"
AJ_ARTIFACT_MANIFEST_SHA256 = "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
AJ_PADDED_SHA256 = "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
AI_PADDED_SHA256 = "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
USB_CONTINUATION_PROMPT = "> "
HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1/24"
DEVICE_ENDPOINT = "10.15.19.82:2323"
WRAPPER_LINE = "Candidate AB: kernel restart requested now (BusyBox reboot -n -f)."
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
HEX256 = re.compile(r"[0-9a-f]{64}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pinned(name: str, expected: str, module_name: str) -> ModuleType:
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


# Pin the identity module before loading the validator which interprets evidence.
AJ = load_pinned("candidate_aj.py", CANDIDATE_AJ_SHA256, "aj_native_identity")
RUNTIME = load_pinned(
    "validate-runtime.py", RUNTIME_VALIDATOR_SHA256, "aj_native_runtime_validator"
)


def normalized_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r", "").splitlines():
        line = raw
        # BusyBox ash is interactive because the development service must also
        # remain usable by a person.  A multi-line ``if`` therefore emits one
        # PS2 prompt for each continued line before printing the branch result;
        # netcat can coalesce PS1, PS2, and the first result onto one line in
        # either prompt order.  Strip only exact leading prompt tokens and stop
        # at the first non-prompt byte.  Prompt-like text inside a value remains
        # evidence.
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
    begin = f"__AJ_NATIVE_{name}_BEGIN__"
    end = f"__AJ_NATIVE_{name}_END__"
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


def runtime_boot_id(runtime_text: str, expected_hash: str) -> str:
    RUNTIME.validate(runtime_text, expected_hash)
    identity = RUNTIME.key_values(
        RUNTIME.section(runtime_text, "IDENTITY"), "runtime identity"
    )
    boot_id = identity.get("boot_id", "")
    if UUID.fullmatch(boot_id) is None:
        raise ValueError("validated runtime boot ID is malformed")
    return boot_id


def validate(
    text: str,
    runtime_text: str,
    expected_installed_full_sha256: str,
) -> str:
    AJ.require_artifact_pins()
    identities = (
        AJ.RAW_SHA256,
        AJ.RAW_SIZE,
        AJ.ARTIFACT_MANIFEST_SHA256,
        AJ.PADDED_SHA256,
        AJ.AI_PADDED_SHA256,
    )
    expected_identities = (
        AJ_RAW_SHA256,
        AJ_RAW_SIZE,
        AJ_ARTIFACT_MANIFEST_SHA256,
        AJ_PADDED_SHA256,
        AI_PADDED_SHA256,
    )
    if identities != expected_identities:
        raise ValueError("Candidate AJ/AI artifact identity set changed")
    if expected_installed_full_sha256 != AJ_PADDED_SHA256:
        raise ValueError("expected installed full-partition SHA-256 is not Candidate AJ")
    boot_id = runtime_boot_id(runtime_text, expected_installed_full_sha256)

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
        "runtime_validation": "candidate-aj-usb-cpu-runtime-subgate",
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
            (key for key in sorted(set(request) | set(expected_request))
             if request.get(key) != expected_request.get(key)),
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
    if "__AJ_NATIVE_REBOOT_RETURNED__" in lines:
        raise ValueError("native reboot wrapper returned unexpectedly")
    request_end = lines.index("__AJ_NATIVE_REQUEST_END__")
    wrapper_index = lines.index(WRAPPER_LINE)
    result_begin = lines.index("__AJ_NATIVE_RESULT_BEGIN__")
    if not request_end < wrapper_index < result_begin:
        raise ValueError("native reboot request/result sequence changed")
    forbidden = ("/dev/watchdog", "shutdown", "poweroff", "reboot -d", "sync_requested=yes")
    haystack = "\n".join(lines).lower()
    if any(token in haystack for token in forbidden):
        raise ValueError("native reboot transcript contains a forbidden fallback")
    return boot_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    parser.add_argument("--runtime-capture", type=pathlib.Path, required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    args = parser.parse_args()
    try:
        # read_bytes().decode() deliberately preserves CRLF byte identity for
        # the runtime_capture_sha256 binding; Path.read_text() would translate it.
        text = args.capture.read_bytes().decode("utf-8", errors="strict")
        runtime_text = args.runtime_capture.read_bytes().decode("utf-8", errors="strict")
        boot_id = validate(text, runtime_text, args.expected_installed_full_sha256)
        print("validation=candidate-aj-native-reboot-request")
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
