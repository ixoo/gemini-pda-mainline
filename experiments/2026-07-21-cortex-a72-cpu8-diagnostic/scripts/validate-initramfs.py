#!/usr/bin/env python3
"""Validate Candidate AF's exact Candidate-AD initramfs-only CPU8 delta."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import re
import stat
import sys
from dataclasses import dataclass, replace


AD_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AD_INIT_SHA256 = "c938a65e963dae815c5fa9e51442026b8464d470a10bb9615d8de73599295222"
AF_INIT_SHA256 = "TO_PIN"
AF_WORKER_SHA256 = "TO_PIN"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
MARKER = "GEMINI_CORTEX_A72_CPU8_20260721_AF"
SOURCE_TO_MEMBER = {"init": "init", "af-cpu8": "bin/af-cpu8"}


@dataclass(frozen=True)
class Member:
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    devmajor: int
    devminor: int
    rdevmajor: int
    rdevminor: int
    data: bytes


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot stat {label}: {path}") from exc
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError(f"{label} is not a regular non-symlink file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read {label}: {path}") from exc


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(compressed: bytes) -> dict[str, Member]:
    if len(compressed) < 10 or compressed[:10] != b"\x1f\x8b\x08\0\0\0\0\0\x02\x03":
        raise ValueError("archive is not a canonical gzip -n -9 stream")
    try:
        raw = gzip.decompress(compressed)
    except (EOFError, OSError) as exc:
        raise ValueError("archive gzip stream is invalid") from exc
    offset = 0
    previous = ""
    members: dict[str, Member] = {}
    while True:
        if offset + 110 > len(raw):
            raise ValueError("truncated newc header")
        header = raw[offset : offset + 110]
        if header[:6] != b"070701":
            raise ValueError("archive is not crc-free newc")
        try:
            fields = [
                int(header[6 + index * 8 : 14 + index * 8], 16)
                for index in range(13)
            ]
        except ValueError as exc:
            raise ValueError("invalid newc numeric field") from exc
        (
            _inode,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            size,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            namesize,
            check,
        ) = fields
        if check or namesize < 2:
            raise ValueError("invalid newc checksum or name size")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("truncated or unterminated newc name")
        try:
            stored_name = raw[name_start : name_end - 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("newc member name is not UTF-8") from exc
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc data")
        if stored_name == "TRAILER!!!":
            if size or any(raw[align4(data_end) :]):
                raise ValueError("invalid newc trailer or trailing bytes")
            break
        name = stored_name.removeprefix("./") or "."
        parts = pathlib.PurePosixPath(name).parts
        if stored_name.startswith("/") or ".." in parts or name in members:
            raise ValueError("unsafe or duplicate newc member")
        if previous and name < previous:
            raise ValueError("newc members are not canonically sorted")
        previous = name
        members[name] = Member(
            mode,
            uid,
            gid,
            nlink,
            mtime,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            raw[data_start:data_end],
        )
        offset = align4(data_end)
    return members


def text_member(members: dict[str, Member], name: str) -> str:
    try:
        return members[name].data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"non-UTF-8 script: {name}") from exc


def require_once(text: str, token: str, label: str) -> None:
    if text.count(token) != 1:
        raise ValueError(f"required {label} is absent or duplicated")


def validate_sources(source_dir: pathlib.Path, candidate: dict[str, Member]) -> None:
    if not source_dir.is_dir() or source_dir.is_symlink():
        raise ValueError("Candidate AF source directory is missing or unsafe")
    source_names = {path.name for path in source_dir.iterdir()}
    if source_names != set(SOURCE_TO_MEMBER):
        raise ValueError(f"Candidate AF source inventory changed: {sorted(source_names)}")
    for source_name, member_name in SOURCE_TO_MEMBER.items():
        source = read_regular(source_dir / source_name, f"AF source {source_name}")
        if candidate[member_name].data != source:
            raise ValueError(f"embedded AF member differs from source: {source_name}")


def validate_init(text: str) -> None:
    checks = (
        (
            "mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys",
            "inherited read-only sysfs mount",
        ),
        ("/bin/busybox mkdir -p /run/af-sys", "private AF sysfs mountpoint"),
        (
            "mount -t sysfs -o rw,nosuid,nodev,noexec sysfs /run/af-sys",
            "private read-write AF sysfs mount",
        ),
        ("baseline=candidate-AD", "exact Candidate AD lineage"),
        ("cpu_policy=maxcpus-8", "Candidate AD eight-CPU policy"),
        ("/bin/x-probe &", "inherited observation worker"),
        ("/bin/usb-net &", "inherited USB network worker"),
        ("/bin/af-cpu8 &", "sole CPU8 diagnostic worker"),
        ("exec /bin/busybox init", "inherited BusyBox init handoff"),
        ("tty1_shell=supervised", "inherited local console shell"),
        ("keyboard_map=tty1-synchronous", "inherited keyboard path"),
        ("manual_reboot=busybox-no-sync-force", "inherited reboot dispatch"),
        ("usb_network=background-nc-2323", "inherited USB shell"),
    )
    for token, label in checks:
        require_once(text, token, label)
    if text.count("mount -t sysfs") != 2:
        raise ValueError("Candidate AF must have exactly two sysfs mounts")
    if "mount -t sysfs -o rw,nosuid,nodev,noexec sysfs /sys" in text:
        raise ValueError("inherited Candidate AD sysfs view became writable")
    if text.index("sysfs /sys") >= text.index("sysfs /run/af-sys"):
        raise ValueError("private AF sysfs is mounted before inherited read-only sysfs")
    if text.count("watchdog_userspace=af-cpu8-one-ping") != 2:
        raise ValueError("Candidate AF watchdog ownership attribution changed")
    if text.index("/bin/x-probe &") >= text.index("/bin/usb-net &"):
        raise ValueError("inherited Candidate AC service ordering changed")
    if text.index("/bin/usb-net &") >= text.index("/bin/af-cpu8 &"):
        raise ValueError("CPU8 worker does not follow inherited AC service launches")
    if text.index("/bin/af-cpu8 &") >= text.index("exec /bin/busybox init"):
        raise ValueError("CPU8 worker is not launched before BusyBox init")


def validate_worker(text: str) -> None:
    checks = (
        (f"readonly MARKER='{MARKER}'", "unique AF marker"),
        ("readonly SYSFS=/run/af-sys", "private AF sysfs root"),
        ("readonly CPU8_ONLINE=$SYSFS/devices/system/cpu/cpu8/online", "CPU8 control"),
        ("readonly CPU9_ONLINE=$SYSFS/devices/system/cpu/cpu9/online", "CPU9 observation"),
        ("readonly CPU8_DT=$SYSFS/firmware/devicetree/base/cpus/cpu@200", "CPU8 DT node"),
        ("readonly WATCHDOG_TIMEOUT_SECONDS=31", "31-second watchdog"),
        ("readonly LATEST_REQUEST_SECONDS=22", "bounded request budget"),
        ("readonly LATEST_ACCOUNTING_SECONDS=25", "bounded accounting budget"),
        ("printf '<6>%s\\n' \"$line\" >/dev/kmsg", "durable kmsg markers"),
        ("[ \"$possible\" != 0-9 ]", "possible-mask gate"),
        ("[ \"$present\" != 0-9 ]", "present-mask gate"),
        ("[ \"$online\" != 0-7 ]", "initial online-mask gate"),
        ("[ \"$offline\" != 8-9 ]", "initial offline-mask gate"),
        ("compatible\" != arm,cortex-a72", "CPU8 compatible gate"),
        ("enable_method\" != mediatek,mt6797-psci", "CPU8 MT6797 PSCI gate"),
        ("*/cpus/cpu@200)", "CPU8 logical mapping gate"),
        ("cpu8_stat_sample=1", "first CPU8 accounting sample"),
        ("cpu8_stat_sample=2", "second CPU8 accounting sample"),
        ("[ \"$stat_first\" != \"$stat_second\" ]", "advancing accounting gate"),
        ("boot_count_before=$boot_before_count", "pre-write CPU8 boot-line count"),
        ("gic_count_before=$gic_before_count", "pre-write CPU8 GIC-line count"),
        ("[ \"$boot_after_count\" = 1 ]", "unique post-write CPU8 boot line"),
        ("[ \"$gic_after_count\" = 1 ]", "unique post-write CPU8 GIC line"),
        ("cpu8_fault_scan=no-new-signature", "post-write fault-delta gate"),
        (
            "cpu8_result=PASS online=0-8 offline=9 cpu8_mpidr=0x200 "
            "cpu8_midr=0x410fd080 gic_redistributor=200 accounting=advanced "
            "cpu9=offline-untouched",
            "exact CPU8 success marker",
        ),
        ("if run_cpu8_diagnostic 3>/dev/watchdog0; then", "guarded watchdog open"),
        ("if ! printf '.' >&3; then", "single watchdog handoff ping"),
        ("watchdog_identity\" != mtk-wdt", "watchdog identity gate"),
        ("watchdog_timeout\" != \"$WATCHDOG_TIMEOUT_SECONDS\"", "watchdog timeout gate"),
        ("watchdog_pretimeout\" != unavailable", "no-IRQ pretimeout gate"),
        ("watchdog_driver\" != mtk-wdt", "watchdog driver gate"),
        ("*10007000.watchdog)", "watchdog device gate"),
        ("[ -e \"$live_watchdog_node/interrupts\" ]", "live no-IRQ DT gate"),
        (
            'for ready_path in "$SYSFS"/bus/platform/drivers/mt6797-a72-power/*/ready; do',
            "A72 provider ready-file discovery",
        ),
        ("[ -f \"$ready_path\" ]", "regular provider ready-file gate"),
        ("[ \"$ready_count\" != 1 ]", "unique provider ready-file gate"),
        ("provider_device=${ready_path%/ready}", "provider device derivation"),
        ("driver_name \"$provider_device/driver\"", "provider driver binding"),
        ("[ \"$provider_ready\" != 1 ]", "provider ready-value gate"),
        ("[ \"$provider_driver\" != mt6797-a72-power ]", "provider driver-name gate"),
        ("provider_abi_path=$provider_device/abi", "provider ABI attribute"),
        ("provider_hooks_armed_path=$provider_device/hooks_armed", "provider hooks attribute"),
        ("[ ! -f \"$provider_abi_path\" ]", "regular provider ABI gate"),
        ("[ ! -f \"$provider_hooks_armed_path\" ]", "regular provider hooks gate"),
        (
            "readonly PROVIDER_ABI_EXPECTED='TO_PIN_PROVIDER_ABI'",
            "unfinalized provider ABI value",
        ),
        (
            "readonly PROVIDER_HOOKS_ARMED_EXPECTED='TO_PIN_PROVIDER_HOOKS_ARMED'",
            "unfinalized provider hooks value",
        ),
        ("[ \"$provider_abi\" != \"$PROVIDER_ABI_EXPECTED\" ]", "provider ABI value gate"),
        (
            "[ \"$provider_hooks_armed\" != \"$PROVIDER_HOOKS_ARMED_EXPECTED\" ]",
            "provider hooks value gate",
        ),
        (
            "grep -E 'mt6797-a72-power: provider ready$'",
            "exact provider dmesg readiness marker",
        ),
        (
            "a72_power_provider=not-ready cpu8_request=withheld watchdog=armed action=wait-for-reset",
            "provider auto-recovery decision",
        ),
    )
    for token, label in checks:
        require_once(text, token, label)

    boot_pattern = "CPU8: Booted secondary processor 0x0*200 \\[0x410fd080\\]"
    gic_pattern = "GICv3: CPU8: found redistributor 200([[:space:]]|$)"
    if text.count(boot_pattern) != 2 or text.count(gic_pattern) != 2:
        raise ValueError("pre/post CPU8 MPIDR/MIDR/GIC evidence patterns changed")

    if text.count('>"$CPU8_ONLINE"') != 1:
        raise ValueError("CPU8 online control does not have exactly one write site")
    if '>"$CPU9_ONLINE"' in text:
        raise ValueError("CPU9 online control gained a write site")
    if text.count(">&3") != 1:
        raise ValueError("watchdog fd 3 does not have exactly one ping site")
    if text.count("run_cpu8_diagnostic 3>/dev/watchdog0") != 1:
        raise ValueError("watchdog open does not have exactly one source site")
    if re.search(r"\bexec\s+[0-9]*>/dev/watchdog", text):
        raise ValueError("ash exec special builtin may not own the watchdog")

    if "/sys/" in text:
        raise ValueError("AF worker gained access through inherited /sys")

    provider_function_start = text.index("validate_a72_power_provider()")
    provider_function_end = text.index("\nrecord_cpu8_boot_evidence()", provider_function_start)
    provider_function = text[provider_function_start:provider_function_end]
    if provider_function.count('"$SYSFS"/bus/platform/drivers/mt6797-a72-power/*/ready') != 1:
        raise ValueError("A72 provider discovery path changed")
    if ">" in "\n".join(
        line for line in provider_function.splitlines() if "record " not in line
    ):
        raise ValueError("A72 provider readiness gate gained a write")

    initial_start = text.index("validate_initial_cpu_contract()")
    initial_end = text.index("\nvalidate_cpu8_dtb_contract()", initial_start)
    initial_contract = text[initial_start:initial_end]
    for token in ('[ "$cpu8_state" != 0 ]', '[ "$cpu9_state" != 0 ]'):
        if initial_contract.count(token) != 1:
            raise ValueError(f"initial CPU contract lost: {token}")

    wait_start = text.index("wait_for_watchdog_reset()")
    wait_end = text.index("\nrequest_cpu8_online()", wait_start)
    reset_wait = text[wait_start:wait_end]
    if reset_wait.count("while :; do") != 1 or "done" not in reset_wait:
        raise ValueError("watchdog reset wait is no longer unbounded")

    function_start = text.index("run_cpu8_diagnostic()")
    function_end = text.index(
        "\nrecord 'entry initramfs_baseline=candidate-AD", function_start
    )
    armed_function = text[function_start:function_end]
    if "static_hold" in armed_function:
        raise ValueError("an armed CPU8 path can enter a static hold instead of reset wait")
    if armed_function.count("wait_for_watchdog_reset") != 7:
        raise ValueError("an armed CPU8 result path lost its watchdog reset wait")
    provider_gate = "if ! validate_a72_power_provider; then"
    if armed_function.count(provider_gate) != 1:
        raise ValueError("armed CPU8 function lost its provider readiness gate")
    if armed_function.index("watchdog0=armed handoff_ping=sent") >= armed_function.index(
        provider_gate
    ):
        raise ValueError("provider readiness is checked before watchdog arming evidence")
    if armed_function.index(provider_gate) >= armed_function.index(
        "if ! validate_initial_cpu_contract; then"
    ):
        raise ValueError("provider readiness is checked after CPU preconditions")

    request_start = text.index("request_cpu8_online()")
    request_end = text.index("\nrun_cpu8_diagnostic()", request_start)
    request = text[request_start:request_end]
    if request.index("cpu8_request=begin") >= request.index('>"$CPU8_ONLINE"'):
        raise ValueError("durable pre-write CPU8 marker does not precede CPU_ON")
    if request.index('>"$CPU8_ONLINE"') >= request.index("cpu8_request=returned"):
        raise ValueError("CPU8 return marker does not follow CPU_ON")
    if request.count("if ! validate_no_new_faults; then") != 1:
        raise ValueError("CPU8 request path lost its post-write fault-delta gate")
    if request.index("record_cpu8_accounting") >= request.index("validate_no_new_faults"):
        raise ValueError("CPU8 fault-delta gate precedes the accounting dwell")
    for token in (
        '[ "$cpu9_state" != 0 ]',
        '[ "$online" != 0-8 ]',
        '[ "$offline" != 9 ]',
        '[ "$stable_cpu9" != 0 ]',
    ):
        if token not in request:
            raise ValueError(f"CPU8 return contract lost: {token}")

    forbidden = (
        "/dev/mmc",
        "/dev/block",
        "/sys/block",
        "/proc/partitions",
        "/proc/sysrq-trigger",
        "/sys/class/net",
        "/proc/sys/net",
        "udhcpc",
        "ifconfig",
        " route ",
        " ip ",
        " nc ",
        "telnet",
        "wget",
        "tftp",
        "reboot",
        "poweroff",
        "halt",
        "kexec",
        "mknod",
        "swapon",
        "mkfs",
        "fdisk",
    )
    lowered = text.lower()
    for token in forbidden:
        if token.lower() in lowered:
            raise ValueError(f"AF worker gained forbidden storage/network/reset path: {token}")
    if re.search(r"(?m)^\s*(?:/bin/busybox\s+)?(?:dd|sync)(?:\s|$)", text):
        raise ValueError("AF worker gained storage-oriented command execution")
    if re.search(r"(?m)^\s*(?:exec\s+)?/bin/busybox\s+(?:ash|sh)\s+-[cil]", text):
        raise ValueError("AF worker gained an interactive shell")


def validate_candidate(
    baseline_data: bytes, candidate_data: bytes, source_dir: pathlib.Path
) -> None:
    if digest_bytes(baseline_data) != AD_INITRAMFS_SHA256:
        raise ValueError("baseline is not exact hardware-passed Candidate AD initramfs")
    baseline = parse_newc(baseline_data)
    candidate = parse_newc(candidate_data)
    if "bin/af-cpu8" in baseline:
        raise ValueError("exact Candidate AD already contains bin/af-cpu8")
    expected_names = set(baseline) | {"bin/af-cpu8"}
    if set(candidate) != expected_names:
        extra = sorted(set(candidate) - expected_names)
        missing = sorted(expected_names - set(candidate))
        raise ValueError(f"AF archive inventory changed: extra={extra} missing={missing}")

    if digest_bytes(baseline["init"].data) != AD_INIT_SHA256:
        raise ValueError("exact Candidate AD init bytes changed")
    for name, member in baseline.items():
        if name == "init":
            continue
        if candidate[name] != member:
            raise ValueError(f"inherited Candidate AD member changed: {name}")

    validate_sources(source_dir, candidate)
    expected_init = replace(baseline["init"], data=candidate["init"].data)
    if candidate["init"] != expected_init:
        raise ValueError("Candidate AF init metadata changed")
    worker = candidate["bin/af-cpu8"]
    if not stat.S_ISREG(worker.mode) or stat.S_IMODE(worker.mode) != 0o755:
        raise ValueError("Candidate AF worker type/mode changed")
    if (
        worker.uid
        or worker.gid
        or worker.nlink != 1
        or worker.mtime
        or worker.devmajor
        or worker.devminor
        or worker.rdevmajor
        or worker.rdevminor
    ):
        raise ValueError("Candidate AF worker metadata is not canonical")
    if digest_bytes(candidate["init"].data) != AF_INIT_SHA256:
        raise ValueError("tracked Candidate AF init bytes changed")
    if digest_bytes(worker.data) != AF_WORKER_SHA256:
        raise ValueError("tracked Candidate AF worker bytes changed")
    if digest_bytes(candidate["bin/busybox"].data) != BUSYBOX_SHA256:
        raise ValueError("inherited Candidate AD BusyBox changed")

    validate_init(text_member(candidate, "init"))
    validate_worker(text_member(candidate, "bin/af-cpu8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline_data = read_regular(args.baseline, "Candidate AD initramfs")
        candidate_data = read_regular(args.candidate, "Candidate AF initramfs")
        validate_candidate(baseline_data, candidate_data, args.source_dir)
    except (KeyError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-af-initramfs")
    print(f"candidate_initramfs_sha256={digest_bytes(candidate_data)}")
    print(f"baseline_initramfs_sha256={AD_INITRAMFS_SHA256}")
    print("changed_members=init")
    print("added_regular_members=bin/af-cpu8")
    print("all_other_member_payloads=exact-candidate-AD")
    print("all_other_member_type_mode_owner_link_mtime_device_metadata=exact-candidate-AD")
    print(f"marker={MARKER}")
    print("a72_provider_gate=one-ready-file,value-1,driver,abi,hooks-armed,exact-dmesg-marker")
    print("a72_provider_expected_values=TO_PIN")
    print("cpu8_enable_method=mediatek,mt6797-psci")
    print("inherited_sysfs=read-only")
    print("af_private_sysfs=/run/af-sys,read-write")
    print("watchdog=mtk-wdt,no-irq,31s,open-fd3,one-ping,no-further-pings")
    print("cpu8_request=one-standard-online-write")
    print("cpu8_success=online-0-8,offline-9,mpidr-200,midr-410fd080,gic-200,accounting-advanced")
    print("cpu9=validated-offline,never-written")
    print("storage_access=none")
    print("network_delta=none")
    print("candidate_ac_console_keyboard_reboot_usb=preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
