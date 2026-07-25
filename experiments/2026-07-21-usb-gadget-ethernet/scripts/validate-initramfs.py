#!/usr/bin/env python3
"""Validate Candidate AC as a narrow, canonical transform of exact AB."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import re
import stat
import sys
from dataclasses import dataclass, replace


AB_INITRAMFS_SHA256 = "b57dc3143e7ca7df90d742bcacc692221b4d7b6d346e5192d7bc68acaac00ea7"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
DISPATCH_ENV_SHA256 = "8255ad7ab034cd3d760690a8b57eebcb67c974d321249ed8ee3a4f142f53e90a"
MARKER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
ADDRESS = "10.15.19.82/24"
INTERFACE = "usb0"
PORT = 2323
WAIT_SECONDS = 30

SOURCE_HASHES = {
    "init": "c938a65e963dae815c5fa9e51442026b8464d470a10bb9615d8de73599295222",
    "ac-record": "56a2e0944e77cbf18ab9b1146c14ee0bc3a3ac800fb13a72fe8136aa32ae608a",
    "usb-net": "2144721bf4344f5af04fe59133f9848e54bd9315a9b51cd96534774242603ead",
    "usb-shell": "a16caea4c54196041175254bef26d165b214efd1c1f9bc1d0e2ecad83670aa71",
}
SOURCE_TO_MEMBER = {
    "init": "init",
    "ac-record": "bin/ac-record",
    "usb-net": "bin/usb-net",
    "usb-shell": "bin/usb-shell",
}
ADDED_REGULAR = frozenset({"bin/ac-record", "bin/usb-net", "bin/usb-shell"})
ADDED_SYMLINKS = frozenset({"bin/ip", "bin/nc", "bin/ping"})
DISPATCH_BYTES = b"alias reboot='/bin/reboot'\n"

INIT_REPLACEMENTS = (
    (
        ": >/run/x-status\n"
        "/bin/x-record 'entry profile=mt6797-kernel-restart cpu_policy=maxcpus-1'",
        ": >/run/x-status\n"
        ": >/run/ac-status\n"
        "/bin/ac-record 'entry profile=usb-gadget-ethernet baseline=candidate-AB "
        "storage_access=none runtime_networking=usb0-static'\n"
        "/bin/x-record 'entry profile=mt6797-kernel-restart cpu_policy=maxcpus-1'",
    ),
    (
        '/bin/x-record "cpu_online=${online:-unavailable} storage_access=none '
        'runtime_networking=none"',
        '/bin/x-record "cpu_online=${online:-unavailable} storage_access=none '
        'runtime_networking=usb0-static-10.15.19.82/24 service=nc-2323"',
    ),
    ("/bin/x-probe &\n", "/bin/x-probe &\n/bin/usb-net &\n"),
    (
        "/bin/x-record 'services=launched probe=independent tty1_shell=supervised "
        "clean_tty1_background=yes reboot_dispatch=env-alias watchdog_userspace=none "
        "keyboard_map=tty1-synchronous manual_reboot=busybox-no-sync-force'",
        "/bin/x-record 'services=launched probe=independent tty1_shell=supervised "
        "clean_tty1_background=yes reboot_dispatch=env-alias watchdog_userspace=none "
        "keyboard_map=tty1-synchronous manual_reboot=busybox-no-sync-force "
        "usb_network=background-nc-2323'\n"
        "/bin/ac-record 'services=launched usb_network=background worker_wait_seconds=30 "
        "address=10.15.19.82/24 tcp_port=2323 local_console=unchanged "
        "watchdog_userspace=none'",
    ),
)


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
                int(header[6 + index * 8 : 14 + index * 8], 16) for index in range(13)
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


def exact_init_transform(baseline: Member) -> Member:
    try:
        text = baseline.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("exact AB init is not UTF-8") from exc
    for old, new in INIT_REPLACEMENTS:
        if text.count(old) != 1:
            raise ValueError(f"exact AB init transformation token changed: {old!r}")
        text = text.replace(old, new)
    return replace(baseline, data=text.encode("utf-8"))


def validate_sources(source_dir: pathlib.Path, candidate: dict[str, Member]) -> None:
    if not source_dir.is_dir() or source_dir.is_symlink():
        raise ValueError("AC source directory is missing or unsafe")
    source_names = {path.name for path in source_dir.iterdir()}
    if source_names != set(SOURCE_TO_MEMBER):
        raise ValueError(f"AC source inventory changed: {sorted(source_names)}")
    for source_name, member_name in SOURCE_TO_MEMBER.items():
        source = read_regular(source_dir / source_name, f"AC source {source_name}")
        if candidate[member_name].data != source:
            raise ValueError(f"embedded AC member differs from source: {source_name}")


def validate_recorder(text: str) -> None:
    require_once(text, f"readonly MARKER='{MARKER}'", "AC recorder marker")
    require_once(text, '>>/run/ac-status', "AC status append")
    require_once(text, '>/dev/kmsg', "AC kmsg attribution")
    require_once(text, "output=/dev/ttyS0", "AC serial attribution")
    for forbidden in ("/dev/tty0", "/dev/tty1", "/dev/tty2", "/dev/console"):
        if forbidden in text:
            raise ValueError(f"AC recorder gained a visible-console sink: {forbidden}")


def validate_network_worker(text: str) -> None:
    checks = (
        (f"readonly WAIT_SECONDS={WAIT_SECONDS}", "30-second USB wait bound"),
        (
            'while [ ! -d /sys/class/net/usb0 ] && [ "$waited" -lt "$WAIT_SECONDS" ]; do',
            "bounded usb0 discovery loop",
        ),
        ("/bin/busybox sleep 1", "one-second discovery interval"),
        ("usb0=timeout wait_seconds=30 worker=exit", "bounded timeout exit record"),
        (
            "/bin/busybox ip link set usb0 up >/run/ac-ip-link.status 2>&1",
            "exact usb0 link-up command",
        ),
        (
            "/bin/busybox ip address add 10.15.19.82/24 dev usb0 \\\n"
            "\t\t>/run/ac-ip-address.status 2>&1",
            "exact USB address command",
        ),
        ("for udc_path in /sys/class/udc/*; do", "UDC discovery"),
        ('[ -r "$udc_path/state" ]', "UDC state capture"),
        (
            "/bin/busybox nc -ll -p 2323 -e /bin/usb-shell "
            "2>/run/ac-nc.status",
            "exact persistent TCP shell listener",
        ),
        ('status=$?', "listener exit-status capture"),
        (
            '/bin/ac-record "service=nc status=exited code=$status worker=exit"',
            "listener fatal-exit attribution",
        ),
        ('exit "$status"', "listener status return"),
    )
    for token, label in checks:
        require_once(text, token, label)
    if text.count("/sys/class/net/usb0/operstate") != 2:
        raise ValueError("usb0 operstate capture changed")
    if text.count("/sys/class/net/usb0/carrier") != 2:
        raise ValueError("usb0 carrier capture changed")
    if text.index("ip link set usb0 up") >= text.index("ip address add 10.15.19.82/24"):
        raise ValueError("USB address setup precedes link-up")
    if text.index("ip address add 10.15.19.82/24") >= text.index("usb0=configured"):
        raise ValueError("USB state is recorded before address setup")
    if text.index("usb0=configured") >= text.index("/bin/busybox nc -ll"):
        raise ValueError("listener starts before USB state attribution")
    if text.index("service=nc status=listening") >= text.index("/bin/busybox nc -ll"):
        raise ValueError("listener invocation precedes its start attribution")
    if text.index("/bin/busybox nc -ll") >= text.index("service=nc status=exited"):
        raise ValueError("listener exit is not attributed after return")
    last = next(line for line in reversed(text.splitlines()) if line.strip())
    if last != 'exit "$status"':
        raise ValueError("USB network worker does not return the listener status")


def validate_usb_shell(text: str) -> None:
    checks = (
        ("readonly DISPATCH_ENV=/bin/reboot-dispatch.env", "inherited dispatch path"),
        (
            "readonly EXPECTED_DISPATCH='reboot is an alias for /bin/reboot'",
            "absolute reboot alias expectation",
        ),
        ("ENV=$DISPATCH_ENV", "dispatch ENV assignment"),
        ("export ENV", "dispatch ENV export"),
        ("/bin/busybox ash -ic 'type reboot'", "reboot dispatch self-check"),
        ('if [ "$dispatch" != "$EXPECTED_DISPATCH" ]; then', "dispatch failure gate"),
        ("usb_shell=withheld reboot_dispatch=invalid", "dispatch failure attribution"),
        ("export PS1='GEMINI-AC-USB# '", "AC USB prompt"),
        (
            "usb_shell=ready reboot_dispatch=validated privilege=root "
            "authentication=none encryption=none direct_link_only=yes",
            "remote-shell security attribution",
        ),
        ("Direct USB link only: device 10.15.19.82/24, TCP port 2323.", "link warning"),
        (
            "Security: unauthenticated and unencrypted root shell; trusted host only.",
            "security warning",
        ),
        ("/bin/busybox cat /run/ac-status", "AC status display"),
        ("exec /bin/busybox ash -i", "interactive BusyBox shell"),
        (
            "usb_shell=session-entry usb0_operstate=${operstate:-unavailable} "
            "usb0_carrier=${carrier:-unavailable} udc=${udc_name:-absent} "
            "udc_state=${udc_state:-unavailable}",
            "per-connection USB state attribution",
        ),
        ("for udc_path in /sys/class/udc/*; do", "per-connection UDC discovery"),
        ('[ -r "$udc_path/state" ]', "per-connection UDC state capture"),
    )
    for token, label in checks:
        require_once(text, token, label)
    if text.count("/sys/class/net/usb0/operstate") != 2:
        raise ValueError("per-connection usb0 operstate capture changed")
    if text.count("/sys/class/net/usb0/carrier") != 2:
        raise ValueError("per-connection usb0 carrier capture changed")
    if text.count(f"'{MARKER}'") != 2:
        raise ValueError("AC shell marker count changed")
    if text.index('if [ "$dispatch" != "$EXPECTED_DISPATCH" ]') >= text.index(
        "exec /bin/busybox ash -i"
    ):
        raise ValueError("remote shell is exposed before dispatch validation")
    if not text.rstrip().endswith("exec /bin/busybox ash -i"):
        raise ValueError("remote shell does not end in exact interactive ash exec")


def validate_forbidden_paths(init: str, recorder: str, network: str, shell: str) -> None:
    control = "\n".join((init, recorder, network, shell))
    forbidden_tokens = (
        "/dev/watchdog",
        "/sys/class/watchdog",
        "watchdog0",
        "watchdog@10007000",
        "10007000.watchdog",
        "/dev/mmc",
        "/dev/block",
        "/sys/block",
        "/proc/partitions",
        "sysrq-trigger",
        "/bin/busybox udhcpc",
        "/bin/busybox udhcpd",
        "/bin/busybox route",
        "/bin/busybox ifconfig",
        "/bin/busybox brctl",
        "/bin/busybox telnetd",
        "/bin/busybox httpd",
        "/proc/sys/net",
        "iptables",
        "nftables",
    )
    for token in forbidden_tokens:
        if token in control:
            raise ValueError(f"AC gained a forbidden runtime path: {token}")
    if re.search(
        r"(?i)(?:^|[^a-z0-9_])"
        r"(?:dhcp|default[ -]?route|forwarding|bridge|nat|ipv6|dns)"
        r"(?:[^a-z0-9_]|$)",
        control,
    ):
        raise ValueError("AC gained DHCP/routing/forwarding/bridge/IPv6 policy")
    command_forbidden = re.compile(
        r"(?m)^[ \t]*(?:exec[ \t]+)?(?:/bin/)?(?:busybox[ \t]+)?"
        r"(?:reboot|poweroff|halt|kexec|watchdog|sync|dd|mount|swapon|fdisk|mkfs)"
        r"(?:[ \t]|$)"
    )
    if command_forbidden.search("\n".join((init, recorder, network))):
        raise ValueError("an automatic/background AC path gained reset or storage I/O")
    if command_forbidden.search(shell):
        raise ValueError("AC remote shell wrapper gained reset or storage I/O")
    background = "\n".join((init, recorder, network))
    for sink in ("/dev/tty0", "/dev/tty1", "/dev/tty2", "/dev/console"):
        if sink in background:
            raise ValueError(f"AC background path gained a visible-console sink: {sink}")


def validate_candidate(
    baseline_data: bytes,
    candidate_data: bytes,
    source_dir: pathlib.Path,
) -> None:
    if digest_bytes(baseline_data) != AB_INITRAMFS_SHA256:
        raise ValueError("baseline is not exact hardware-passed Candidate AB initramfs")
    baseline = parse_newc(baseline_data)
    candidate = parse_newc(candidate_data)
    expected_names = set(baseline) | ADDED_REGULAR | ADDED_SYMLINKS
    if set(candidate) != expected_names:
        extra = sorted(set(candidate) - expected_names)
        missing = sorted(expected_names - set(candidate))
        raise ValueError(f"AC archive inventory changed: extra={extra} missing={missing}")

    for name, member in baseline.items():
        if name == "init":
            continue
        if candidate[name] != member:
            raise ValueError(f"inherited Candidate AB member changed: {name}")
    if candidate["init"] != exact_init_transform(baseline["init"]):
        raise ValueError("AC init differs beyond the audited Candidate AB transform")

    validate_sources(source_dir, candidate)
    for name in {"init"} | ADDED_REGULAR:
        member = candidate[name]
        if not stat.S_ISREG(member.mode) or stat.S_IMODE(member.mode) != 0o755:
            raise ValueError(f"AC regular-member type/mode changed: {name}")
        if (
            member.uid
            or member.gid
            or member.nlink != 1
            or member.mtime
            or member.devmajor
            or member.devminor
            or member.rdevmajor
            or member.rdevminor
        ):
            raise ValueError(f"AC regular-member metadata changed: {name}")
    for name in ADDED_SYMLINKS:
        member = candidate[name]
        if not stat.S_ISLNK(member.mode) or stat.S_IMODE(member.mode) != 0o777:
            raise ValueError(f"AC BusyBox-link type/mode changed: {name}")
        if member.data != b"busybox":
            raise ValueError(f"AC BusyBox-link target changed: {name}")
        if (
            member.uid
            or member.gid
            or member.nlink != 1
            or member.mtime
            or member.devmajor
            or member.devminor
            or member.rdevmajor
            or member.rdevminor
        ):
            raise ValueError(f"AC BusyBox-link metadata changed: {name}")

    if digest_bytes(candidate["bin/busybox"].data) != BUSYBOX_SHA256:
        raise ValueError("exact Candidate AB BusyBox changed")
    if digest_bytes(candidate["bin/reboot-dispatch.env"].data) != DISPATCH_ENV_SHA256:
        raise ValueError("exact Candidate AB reboot-dispatch environment changed")
    if candidate["bin/reboot-dispatch.env"].data != DISPATCH_BYTES:
        raise ValueError("absolute reboot-dispatch alias changed")

    init = text_member(candidate, "init")
    recorder = text_member(candidate, "bin/ac-record")
    network = text_member(candidate, "bin/usb-net")
    shell = text_member(candidate, "bin/usb-shell")
    require_once(init, ": >/run/ac-status", "AC status initialization")
    require_once(init, "/bin/usb-net &", "independent USB network worker")
    require_once(init, "/bin/x-probe &", "inherited independent AB probe")
    require_once(init, "runtime_networking=usb0-static-10.15.19.82/24", "AC networking policy")
    require_once(init, "usb_network=background-nc-2323", "AC service policy")
    if init.index(": >/run/ac-status") >= init.index("/bin/ac-record 'entry"):
        raise ValueError("AC status file is initialized after first attribution")
    validate_recorder(recorder)
    validate_network_worker(network)
    validate_usb_shell(shell)
    validate_forbidden_paths(init, recorder, network, shell)

    # Semantic checks above give focused mutation failures. These final pins
    # make the allowlist byte-exact, rejecting any otherwise unmodeled source
    # addition or comment drift.
    for source_name, member_name in SOURCE_TO_MEMBER.items():
        if digest_bytes(candidate[member_name].data) != SOURCE_HASHES[source_name]:
            raise ValueError(f"AC source bytes changed outside the exact allowlist: {source_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline_data = read_regular(args.baseline, "Candidate AB initramfs")
        candidate_data = read_regular(args.candidate, "Candidate AC initramfs")
        validate_candidate(baseline_data, candidate_data, args.source_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-ac-initramfs")
    print(f"candidate_initramfs_sha256={digest_bytes(candidate_data)}")
    print(f"baseline_initramfs_sha256={AB_INITRAMFS_SHA256}")
    print("changed_members=init")
    print("added_regular_members=bin/ac-record,bin/usb-net,bin/usb-shell")
    print("added_busybox_links=bin/ip,bin/nc,bin/ping")
    print(f"busybox_sha256={BUSYBOX_SHA256}")
    print(f"marker={MARKER}")
    print(f"interface={INTERFACE}")
    print(f"address={ADDRESS}")
    print(f"wait_seconds={WAIT_SECONDS}")
    print(f"tcp_port={PORT}")
    print("tcp_service=busybox-nc-ll-usb-shell")
    print("listener_exit=attributed-and-returned")
    print("session_entry=usb0-and-udc-state-attributed")
    print("reboot_dispatch=exact-inherited-ENV-alias")
    print("authentication=none")
    print("encryption=none")
    print("direct_link_only=yes")
    print("dhcp=none")
    print("routes=none")
    print("forwarding=none")
    print("bridge=none")
    print("ipv6=none")
    print("storage_access=none")
    print("watchdog_userspace=none")
    print("automatic_reboot=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
