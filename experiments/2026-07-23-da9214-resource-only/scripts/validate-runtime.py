#!/usr/bin/env python3
"""Validate AL's exact AH runtime plus resource-only I2C6/DA9214 binding."""

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

import candidate_al as al


SECTION_ORDER = ("HOST", "IDENTITY", "STATE1", "STAT1", "STATE2", "STAT2", "DMESG")
I2C_ERROR = re.compile(
    r"^.*(?:1100e000\.i2c|i2c-mt65xx|mtk-i2c|\bi2c6\b|"
    r"[0-9]+-0068|da9211|da9214).*"
    r"(?:timed? ?out|timeout|NACK|NAK|I/O error|transfer[^ \n]* (?:failed|error)|"
    r"probe (?:failed|error)|error -[0-9]+|"
    r"(?:read|write|transfer|transaction|probe)[^\n]*(?:failed|failure|error)|"
    r"(?:failed|failure|error)[^\n]*(?:read|write|transfer|transaction|probe)).*$",
    re.IGNORECASE | re.MULTILINE,
)
REGULATOR_STATES = {"enabled", "disabled"}
VOLTAGE_MIN_UV = 300_000
VOLTAGE_MAX_UV = 1_570_000
VOLTAGE_STEP_UV = 10_000


def load_ah_runtime() -> ModuleType:
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-22-ad-contract-af-kernel-split/scripts/validate-runtime.py"
    )
    data = al.read_regular(source, "Candidate AH runtime validator")
    if hashlib.sha256(data).hexdigest() != al.AH_RUNTIME_VALIDATOR_SHA256:
        raise ValueError("source-pinned Candidate AH runtime validator changed")
    spec = importlib.util.spec_from_file_location("candidate_al_ah_runtime", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AH runtime validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AH = load_ah_runtime()


def validate_structure(text: str) -> None:
    previous_end = -1
    for name in SECTION_ORDER:
        begin = f"__AL_{name}_BEGIN__"
        end = f"__AL_{name}_END__"
        if text.count(begin) != 1 or text.count(end) != 1:
            raise ValueError(f"runtime marker is not unique: {name}")
        begin_at = text.index(begin)
        end_at = text.index(end)
        if begin_at <= previous_end or end_at <= begin_at:
            raise ValueError("runtime section chronology is not exact")
        previous_end = end_at + len(end)


def section(text: str, name: str) -> str:
    begin = f"__AL_{name}_BEGIN__"
    end = f"__AL_{name}_END__"
    begin_at = text.index(begin) + len(begin)
    end_at = text.index(end, begin_at)
    body = text[begin_at:end_at].lstrip("\r\n")
    lines: list[str] = []
    for raw_line in body.replace("\r", "").splitlines():
        line = raw_line
        while line.startswith(AH.USB_PROMPT):
            line = line.removeprefix(AH.USB_PROMPT)
        lines.append(line)
    return "\n".join(lines).strip()


def key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError("runtime key/value inventory is malformed or duplicated")
        result[key] = value
    return result


def stat_sample(text: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"cpu([0-9]+)\s+(.+)", line.strip())
        if match is None:
            raise ValueError("malformed per-CPU accounting line")
        cpu = int(match.group(1))
        fields = match.group(2).split()
        if cpu in values or not fields or any(not field.isdecimal() for field in fields):
            raise ValueError("per-CPU accounting is duplicated or malformed")
        values[cpu] = sum(int(field) for field in fields)
    return values


def accepted_installed_hash(synthetic_override: str | None) -> str:
    if synthetic_override is None:
        al.require_artifact_pins()
        return al.PADDED_SHA256
    if al.HEX256.fullmatch(synthetic_override) is None:
        raise ValueError("synthetic installed hash is malformed")
    return synthetic_override


def regulator_value(values: dict[str, str], prefix: str) -> tuple[str, int]:
    state = values[f"{prefix}_state"]
    raw_uv = values[f"{prefix}_microvolts"]
    if state not in REGULATOR_STATES:
        raise ValueError(f"{prefix} state is not readable or driver-valid")
    if not raw_uv.isdecimal():
        raise ValueError(f"{prefix} microvolts is not readable")
    microvolts = int(raw_uv)
    if not VOLTAGE_MIN_UV <= microvolts <= VOLTAGE_MAX_UV:
        raise ValueError(f"{prefix} microvolts is outside the DA9211 range")
    if (microvolts - VOLTAGE_MIN_UV) % VOLTAGE_STEP_UV:
        raise ValueError(f"{prefix} microvolts is not on the 10-mV selector grid")
    return state, microvolts


def validate_state(text: str) -> dict[str, str]:
    values = key_values(text)
    expected = dict(AH.EXPECTED_STATE)
    expected.update(
        {
            "i2c6_status_hex": "6f6b617900",
            "i2c6_platform_count": "1",
            "i2c6_adapter_count": "1",
            "da9214_dt_count": "1",
            "da9214_client_total": "1",
            "da9214_client_count": "1",
            "da9214_bucka_count": "1",
            "vproc_big_count": "1",
            "i2c6_clock_frequency_hex": "0033e140",
            "i2c6_push_pull_present": "1",
            "i2c6_pinctrl_names_hex": "64656661756c7400",
            "i2c6_pinctrl_0_hex": "0000002c",
            "i2c6_pins_phandle_hex": "0000002c",
            "da9214_dt_compatible_hex": "646c672c64613932313400",
            "da9214_dt_reg_hex": "00000068",
            "da9214_bucka_name_hex": "6461393231342d6275636b6100",
            "da9214_buckb_name_hex": "7670726f632d62696700",
            "i2c6_driver": "i2c-mt65xx",
            "da9214_driver": "da9211",
            "da9214_parent": "i2c@1100e000",
        }
    )
    dynamic = {
        "i2c6_device",
        "i2c6_adapter",
        "da9214_device",
        "da9214_bucka_class",
        "da9214_bucka_parent",
        "da9214_bucka_state",
        "da9214_bucka_microvolts",
        "vproc_big_class",
        "vproc_big_parent",
        "vproc_big_state",
        "vproc_big_microvolts",
        "aw9523_device",
        "boot_id",
        "uptime_seconds",
    }
    if set(values) != set(expected) | dynamic:
        raise ValueError("Candidate AL runtime state inventory changed")
    for key, wanted in expected.items():
        if values.get(key) != wanted:
            raise ValueError(f"Candidate AL AH/resource contract differs: {key}")
    if re.fullmatch(r"[0-9a-f]+\.i2c", values["i2c6_device"]) is None:
        raise ValueError("I2C6 platform device identity is malformed")
    if re.fullmatch(r"[0-9]+", values["i2c6_adapter"]) is None:
        raise ValueError("I2C6 adapter identity is malformed")
    expected_da9214_device = f"{values['i2c6_adapter']}-0068"
    if values["da9214_device"] != expected_da9214_device:
        raise ValueError("DA9214 client is not on the live I2C6 adapter")
    if re.fullmatch(r"regulator\.[0-9]+", values["da9214_bucka_class"]) is None:
        raise ValueError("DA9214 BUCKA regulator-class identity is malformed")
    if re.fullmatch(r"regulator\.[0-9]+", values["vproc_big_class"]) is None:
        raise ValueError("DA9214 BUCKB regulator-class identity is malformed")
    if values["da9214_bucka_class"] == values["vproc_big_class"]:
        raise ValueError("DA9214 BUCKA and BUCKB collapsed to one class device")
    if values["da9214_bucka_parent"] != values["da9214_device"]:
        raise ValueError("DA9214 BUCKA regulator belongs to another device")
    if values["vproc_big_parent"] != values["da9214_device"]:
        raise ValueError("DA9214 BUCKB regulator belongs to another device")
    if re.fullmatch(r"[0-9]+-005b", values["aw9523_device"]) is None:
        raise ValueError("AW9523 live client identity is malformed")
    regulator_value(values, "da9214_bucka")
    regulator_value(values, "vproc_big")
    if AH.UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("Candidate AL boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("Candidate AL uptime is malformed")
    return values


def validate(
    text: str,
    expected_installed_full_sha256: str,
    *,
    synthetic_installed_full_sha256_override: str | None = None,
) -> dict[str, str]:
    if al.HEX256.fullmatch(expected_installed_full_sha256) is None:
        raise ValueError("expected installed full-partition hash is malformed")
    if expected_installed_full_sha256 != accepted_installed_hash(
        synthetic_installed_full_sha256_override
    ):
        raise ValueError("expected installed hash is not Candidate AL")
    validate_structure(text)
    identity_begin = text.index("__AL_IDENTITY_BEGIN__")
    if AH.USB_MARKER not in text[:identity_begin].replace("\r", "").splitlines():
        raise ValueError("exact inherited AD USB session banner is absent")

    host = key_values(section(text, "HOST"))
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "mac": "42:00:15:19:82:00",
        "host_address": "10.15.19.1",
        "regulator_access_path": "regulator-sysfs-driver-regmap-serialized",
        "regulator_sysfs_may_be_regcache": "yes",
        "physical_readback_claim": "none",
    }
    if set(host) != set(expected_host) | {"interface", "route_interface"}:
        raise ValueError("Candidate AL host attestation inventory changed")
    for key, wanted in expected_host.items():
        if host[key] != wanted:
            raise ValueError(f"Candidate AL host attestation differs: {key}")
    if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
        raise ValueError("Candidate AL host interface is malformed")
    if host["route_interface"] != host["interface"]:
        raise ValueError("Candidate AL route differs from the exact USB interface")

    identity = key_values(section(text, "IDENTITY"))
    if set(identity) != set(AH.EXPECTED_IDENTITY) | {"boot_id", "uptime_seconds"}:
        raise ValueError("Candidate AL identity inventory changed")
    for key, wanted in AH.EXPECTED_IDENTITY.items():
        if identity.get(key) != wanted:
            raise ValueError(f"Candidate AL exact AH identity differs: {key}")
    if AH.UUID.fullmatch(identity["boot_id"]) is None:
        raise ValueError("Candidate AL identity boot ID is malformed")
    if not identity["uptime_seconds"].isdecimal() or int(identity["uptime_seconds"]) < 45:
        raise ValueError("Candidate AL capture predates the 45-second boundary")
    tokens = identity["cmdline"].split()
    for token in ("maxcpus=8", "regulator_ignore_unused", AH.BLACKLIST_TOKEN):
        if tokens.count(token) != 1:
            raise ValueError(f"Candidate AL forced-command-line token differs: {token}")
    if "nosmp" in tokens or any(
        token in {"maxcpus=1", "maxcpus=9", "maxcpus=10"}
        or token.startswith("nr_cpus=")
        for token in tokens
    ):
        raise ValueError("Candidate AL live CPU policy contains a conflicting cap")

    first = validate_state(section(text, "STATE1"))
    second = validate_state(section(text, "STATE2"))
    if first["boot_id"] != identity["boot_id"] or second["boot_id"] != identity["boot_id"]:
        raise ValueError("boot ID changed during Candidate AL collection")
    if int(first["uptime_seconds"]) < 45:
        raise ValueError("first Candidate AL state sample predates 45 seconds")
    if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
        raise ValueError("Candidate AL state samples are not five seconds apart")
    stable = set(first) - {"uptime_seconds"}
    if any(first[key] != second[key] for key in stable):
        raise ValueError("Candidate AL board/regulator/CPU state changed across reads")

    first_stat = stat_sample(section(text, "STAT1"))
    second_stat = stat_sample(section(text, "STAT2"))
    expected_cpus = set(range(8))
    if set(first_stat) != expected_cpus or set(second_stat) != expected_cpus:
        raise ValueError("per-CPU accounting inventory is not CPU0 through CPU7")
    stalled = [cpu for cpu in sorted(expected_cpus) if second_stat[cpu] <= first_stat[cpu]]
    if stalled:
        raise ValueError(f"per-CPU accounting did not advance: {stalled}")

    dmesg = section(text, "DMESG")
    if dmesg.count(AH.BLACKLIST_DMESG) != 1:
        raise ValueError("unique observer initcall-blacklist line is absent")
    if dmesg.count("smp: Brought up 1 node, 8 CPUs") != 1:
        raise ValueError("unique eight-CPU SMP completion line is absent")
    for cpu, mpidr in AH.EXPECTED_BOOT_NODES.items():
        pattern = rf"CPU{cpu}: Booted secondary processor 0x{mpidr} \[0x410fd034\]"
        if len(re.findall(pattern, dmesg)) != 1 or dmesg.count(f"GICv3: CPU{cpu}:") != 1:
            raise ValueError(f"Candidate AL CPU{cpu} startup evidence differs")
    AH.require_unique_ordered_pair(
        dmesg, AH.SIMPLEFB_CALL, AH.SIMPLEFB_RETURN, "simplefb"
    )
    AH.require_unique_ordered_pair(
        dmesg, AH.DA9211_CALL, AH.DA9211_RETURN, "DA9211"
    )
    if AH.SIMPLEFB_ERROR.search(dmesg):
        raise ValueError("Candidate AL simplefb clock/probe error is present")
    i2c_error = I2C_ERROR.search(dmesg)
    if i2c_error is not None:
        raise ValueError(f"Candidate AL I2C6/DA9214 error is present: {i2c_error.group(0)}")
    if "observer resources ready:" in dmesg or re.search(
        r"mt6797-a72-power.*(?:probe|resources ready)", dmesg, re.IGNORECASE
    ):
        raise ValueError("A72 observer registered or probed despite blacklist/absent DT")

    inherited_lines = (
        "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
        "(32320 KiB) nomap non-reusable mblock-3-framebuffer",
        "simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
        "input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0",
        "matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
        "matrix_platform_device=keyboard-matrix driver=matrix-keypad",
        "matrix_input_name=keyboard-matrix event_node=/dev/input/event0",
        "watchdog_userspace=none",
    )
    for line in inherited_lines:
        if dmesg.count(line) != 1:
            raise ValueError(f"unique inherited AH runtime line is absent: {line}")
    aw9523_lines = re.findall(
        r"aw9523_client=([0-9]+-005b) driver=aw9523-pinctrl",
        dmesg,
    )
    if len(aw9523_lines) != 1 or aw9523_lines[0] != second["aw9523_device"]:
        raise ValueError(
            "unique inherited AW9523 marker does not match its live adapter"
        )
    keymap = re.compile(
        r"keyboard_map=loaded.*sha256="
        r"02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
        r".*tty1_shell=ready.*prompt=GEMINI-AB#.*reboot_dispatch=validated"
    )
    if len(keymap.findall(dmesg)) != 1:
        raise ValueError("unique inherited keymap/readback marker is absent")
    usb_service = (
        f"{AH.USB_MARKER} service=nc status=listening address=10.15.19.82 "
        "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
        "direct_link_only=yes"
    )
    if dmesg.count(usb_service) != 1:
        raise ValueError("unique inherited USB listener line is absent")
    if len(
        re.findall(
            rf"{AH.USB_MARKER} usb_shell=ready reboot_dispatch=validated "
            r"privilege=root authentication=none encryption=none direct_link_only=yes",
            dmesg,
        )
    ) != 1:
        raise ValueError("exact sole Candidate AL USB shell session is not unique")
    request = AH.A72_REQUEST.search(dmesg)
    if request is not None:
        raise ValueError(f"CPU8/9 request or startup activity is present: {request.group(0)}")
    fault = AH.FAULT.search(dmesg)
    if fault is not None:
        raise ValueError(f"kernel fault signature is present: {fault.group(0)}")
    return {
        "boot_id": identity["boot_id"],
        "uptime_seconds": second["uptime_seconds"],
        "i2c6_adapter": second["i2c6_adapter"],
        "da9214_device": second["da9214_device"],
        "aw9523_device": second["aw9523_device"],
        "bucka_state": second["da9214_bucka_state"],
        "bucka_microvolts": second["da9214_bucka_microvolts"],
        "buckb_state": second["vproc_big_state"],
        "buckb_microvolts": second["vproc_big_microvolts"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=pathlib.Path)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument(
        "--synthetic-installed-full-sha256",
        help="storage-inert test-only accepted identity",
    )
    args = parser.parse_args()
    try:
        info = args.capture.lstat()
        if args.capture.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
            raise ValueError("runtime capture is missing, empty, or unsafe")
        result = validate(
            args.capture.read_text(encoding="utf-8", errors="strict"),
            args.expected_installed_full_sha256,
            synthetic_installed_full_sha256_override=args.synthetic_installed_full_sha256,
        )
        print("validation=candidate-al-da9214-resource-only-runtime")
        print(f"boot_id={result['boot_id']}")
        print(f"uptime_seconds={result['uptime_seconds']}")
        print("installed_full_sha256_input=exact-prior-readback-attestation")
        print("ah_kernel_config_initramfs_board_contract=exact")
        print("final_dtb=exact-ah-plus-0089")
        print("i2c6=bound-3400000hz-push-pull")
        print(f"i2c6_adapter={result['i2c6_adapter']}")
        print(f"da9214_client={result['da9214_device']}-bound-da9211")
        print(f"aw9523_client={result['aw9523_device']}-bound-aw9523-pinctrl")
        print("da9214_regulators=bucka-plus-buckb-exact-parent")
        print(f"bucka_state={result['bucka_state']}")
        print(f"bucka_microvolts={result['bucka_microvolts']}")
        print(f"buckb_state={result['buckb_state']}")
        print(f"buckb_microvolts={result['buckb_microvolts']}")
        print("regulator_values=stable-driver-sysfs")
        print("regulator_access_path=driver-regmap-serialized")
        print("regulator_sysfs_may_be_regcache=yes")
        print("physical_readback_claim=none")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("cpu0_cpu7_accounting=advanced")
        print("cpu8_cpu9_request=none")
        print("observer=blacklisted-dt-device-driver-absent")
        print("watchdog_userspace_fd=absent")
        print("automatic_reboot_through_observation_boundary=absent")
        print("i2c_fault_signatures=absent")
        print("collector_explicit_operations=read-only")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
