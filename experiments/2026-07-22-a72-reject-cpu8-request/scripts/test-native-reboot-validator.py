#!/usr/bin/env python3
"""Storage-inert mutation tests for AJ's native reboot evidence validator."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys

sys.dont_write_bytecode = True


def load(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixture(native: object, runtime_text: str, boot_id: str) -> str:
    runtime_sha = hashlib.sha256(runtime_text.encode()).hexdigest()
    return "".join(
        (
            "__AJ_NATIVE_HOST_BEGIN__\n",
            f"installed_full_sha256_input={native.AJ.PADDED_SHA256}\n",
            "attestation_basis=caller-supplied-prior-full-partition-readback\n",
            "installed_full_hash_reverified_during_request=no\n",
            "device_partition_read_during_request=no\n",
            f"runtime_capture_sha256={runtime_sha}\n",
            "runtime_validation=candidate-aj-usb-cpu-runtime-subgate\n",
            "interface=en9\n",
            "mac=42:00:15:19:82:00\n",
            "host_address=10.15.19.1/24\n",
            "route_interface=en9\n",
            "device_endpoint=10.15.19.82:2323\n",
            "storage_access=none\n",
            "__AJ_NATIVE_HOST_END__\n",
            "GEMINI_USB_GADGET_ETHERNET_20260721_AC\n",
            "GEMINI-AC-USB# __AJ_NATIVE_REQUEST_BEGIN__\n",
            f"GEMINI-AC-USB# candidate_boot_id={boot_id}\n",
            f"GEMINI-AC-USB# live_boot_id={boot_id}\n",
            f"GEMINI-AC-USB# reboot_sha256={native.REBOOT_SHA256}\n",
            "GEMINI-AC-USB# reboot_dispatch=/bin/reboot\n",
            "GEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n",
            # Real BusyBox ash emits four PS2 prompts while parsing the
            # requester's multi-line if/else/fi before this result.
            "GEMINI-AC-USB# > > > > request_authorized=yes\n",
            "GEMINI-AC-USB# storage_access=none\n",
            "GEMINI-AC-USB# sync_requested=no\n",
            "GEMINI-AC-USB# watchdog_userspace=none\n",
            "GEMINI-AC-USB# request_count=1\n",
            "GEMINI-AC-USB# __AJ_NATIVE_REQUEST_END__\n",
            f"GEMINI-AC-USB# > > GEMINI-AC-USB# {native.WRAPPER_LINE}\n",
            "__AJ_NATIVE_RESULT_BEGIN__\n",
            "nc_exit_status=0\n",
            "connection_closed_after_request=yes\n",
            "mac_absence_observation_1=absent\n",
            "mac_absence_observation_2=absent\n",
            "disconnect_confirmed=yes\n",
            "requestor_reboot_command_issued=yes\n",
            "device_partition_reads=none\n",
            "device_write_operations=none\n",
            "__AJ_NATIVE_RESULT_END__\n",
        )
    )


def rejected(native: object, text: str, runtime_text: str) -> None:
    try:
        native.validate(text, runtime_text, native.AJ.PADDED_SHA256)
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
        return
    raise ValueError("native reboot mutation unexpectedly passed")


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    native = load(script_dir / "validate-native-reboot.py", "aj_native_test_validator")
    runtime_tests = load(script_dir / "test-runtime-validator.py", "aj_native_runtime_fixture")
    runtime_text = runtime_tests.fixture(native.RUNTIME)
    boot_id = native.runtime_boot_id(runtime_text, native.AJ.PADDED_SHA256)
    text = fixture(native, runtime_text, boot_id)
    if native.validate(text, runtime_text, native.AJ.PADDED_SHA256) != boot_id:
        raise ValueError("valid native reboot fixture lost its boot ID")

    mutations = (
        text.replace(f"live_boot_id={boot_id}", "live_boot_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", 1),
        text.replace(native.REBOOT_SHA256, "0" * 64, 1),
        text.replace("request_authorized=yes", "request_authorized=no", 1),
        text.replace("request_count=1", "request_count=2", 1),
        text.replace("disconnect_confirmed=yes", "disconnect_confirmed=no", 1),
        text.replace(native.WRAPPER_LINE + "\n", "", 1),
        text.replace("__AJ_NATIVE_RESULT_BEGIN__", "__AJ_NATIVE_REBOOT_RETURNED__\n__AJ_NATIVE_RESULT_BEGIN__", 1),
        text.replace("mac_absence_observation_2=absent", "mac_absence_observation_2=present", 1),
        text.replace("runtime_capture_sha256=", "runtime_capture_sha256=0", 1),
        text.replace("device_partition_reads=none", "device_partition_reads=boot2", 1),
        text.replace(
            "> > > > request_authorized=yes",
            "> > > > injected request_authorized=yes",
            1,
        ),
        text.replace(
            "> > > > request_authorized=yes",
            "> > > > request_authorized=> yes",
            1,
        ),
    )
    for mutation in mutations:
        rejected(native, mutation, runtime_text)
    rejected(native, text, runtime_text.replace(native.RUNTIME.EXPECTED_CONFIG_SHA256, "0" * 64, 1))

    print("validation=candidate-aj-native-reboot-mutations")
    print("fresh_runtime_boot_id_gate=passed")
    print("exact_reboot_wrapper_hash_and_dispatch=passed")
    print(f"mutations_rejected={len(mutations) + 1}")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
