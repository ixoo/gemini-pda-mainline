#!/usr/bin/env python3
"""Execute Candidate Z's exact BusyBox ash dispatch gate on Linux arm64."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import pathlib
import platform
import shlex
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass


BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
DISPATCH_BYTES = b"alias reboot='/bin/reboot'\n"
EXPECTED_BASELINE = "reboot is reboot"
EXPECTED_CONFIGURED = "reboot is an alias for /bin/reboot"
ORACLE_PASS = "CANDIDATE_Z_RUNTIME_ORACLE_PASSED"


@dataclass(frozen=True)
class Member:
    mode: int
    uid: int
    gid: int
    mtime: int
    data: bytes


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_members(compressed: bytes) -> dict[str, Member]:
    raw = gzip.decompress(compressed)
    offset = 0
    members: dict[str, Member] = {}
    while True:
        if offset + 110 > len(raw) or raw[offset:offset + 6] != b"070701":
            raise ValueError("invalid or truncated newc archive")
        header = raw[offset:offset + 110]
        try:
            fields = [int(header[6 + index * 8:14 + index * 8], 16)
                      for index in range(13)]
        except ValueError as exc:
            raise ValueError("invalid newc header field") from exc
        (_ino, mode, uid, gid, _nlink, mtime, size, _devmajor, _devminor,
         _rdevmajor, _rdevminor, namesize, check) = fields
        if check or namesize < 2:
            raise ValueError("invalid newc checksum or name size")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("unterminated newc member name")
        name = raw[name_start:name_end - 1].decode("utf-8").removeprefix("./")
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc member")
        if name == "TRAILER!!!":
            break
        if not name or name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts \
                or name in members:
            raise ValueError("unsafe or duplicate newc member")
        members[name] = Member(mode, uid, gid, mtime, raw[data_start:data_end])
        offset = align4(data_end)
    return members


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def compatible_host() -> bool:
    return platform.system() == "Linux" and platform.machine() in {"aarch64", "arm64"}


def last_nonempty(output: bytes) -> str:
    lines = [line for line in output.decode("utf-8").splitlines() if line]
    if not lines:
        raise ValueError("ash produced no nonempty stdout line")
    return lines[-1]


def run_ash(busybox: pathlib.Path, dispatch_env: pathlib.Path | None,
            command: str, *, interactive: bool = True) -> subprocess.CompletedProcess[bytes]:
    environment = {
        "HOME": "/",
        "LC_ALL": "C",
        "PATH": "/bin",
        "PS1": "",
    }
    if dispatch_env is not None:
        environment["ENV"] = os.fspath(dispatch_env)
    option = "-ic" if interactive else "-c"
    return subprocess.run(
        [os.fspath(busybox), "ash", option, command],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=environment, check=False, timeout=10,
    )


def run_script(busybox: pathlib.Path, script: pathlib.Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [os.fspath(busybox), "ash", os.fspath(script)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={"HOME": "/", "LC_ALL": "C", "PATH": "/bin", "PS1": ""},
        check=False, timeout=10,
    )


def runtime_oracle_probe(local_shell: bytes, busybox: pathlib.Path,
                         dispatch_env: pathlib.Path, root: pathlib.Path) -> None:
    try:
        shell_text = local_shell.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Candidate Z local-shell is not UTF-8") from exc
    condition = 'if [ "$dispatch" != "$EXPECTED_DISPATCH" ]; then'
    failure_start = shell_text.index(condition)
    condition_end = shell_text.index("\n", failure_start) + 1
    # Execute the candidate's exact assignment/export/oracle/condition prefix.
    # Replace only absolute archive paths with controlled extracted paths, and
    # turn the failure body into a distinct status so a broken inherited export
    # fails quickly instead of entering the candidate's intentional static hold.
    probe_text = shell_text[:condition_end]
    probe_text += "\texit 91\nfi\n"
    probe_text += f"printf '%s\\n' '{ORACLE_PASS}'\nexit 0\n"
    probe_text = probe_text.replace(
        "readonly DISPATCH_ENV=/bin/reboot-dispatch.env",
        f"readonly DISPATCH_ENV={shlex.quote(os.fspath(dispatch_env))}",
    )
    probe_text = probe_text.replace("/bin/busybox", shlex.quote(os.fspath(busybox)))
    probe = root / "local-shell-runtime-oracle"
    probe.write_text(probe_text, encoding="utf-8")
    probe.chmod(0o700)
    completed = run_script(busybox, probe)
    if completed.returncode != 0 or last_nonempty(completed.stdout) != ORACLE_PASS:
        raise ValueError(
            "Candidate Z local-shell runtime oracle did not inherit exported ENV"
        )


def expected_result(initramfs_hash: str) -> bytes:
    fields = (
        "validation=candidate-z-ash-dispatch",
        f"candidate_initramfs_sha256={initramfs_hash}",
        f"busybox_sha256={BUSYBOX_SHA256}",
        f"dispatch_env_sha256={digest(DISPATCH_BYTES)}",
        "execution_host=Linux-aarch64",
        f"baseline_type={EXPECTED_BASELINE}",
        f"configured_type={EXPECTED_CONFIGURED}",
        "runtime_oracle=inherited-exported-ENV-passed",
        "noninteractive_env=ignored-no-wrapper-recursion",
        "bare_reboot_probe=absolute-bin-reboot-wrapper-invoked",
        "bare_reboot_parent_shell=continued-status-73",
        "probe_exit_status=73",
        "function_redirection_failure=else-continued",
        "profile_policy=ENV-nonlogin-interactive",
        "device_contact=none",
        "hardware_write=none",
    )
    return ("\n".join(fields) + "\n").encode("utf-8")


def execute(initramfs: bytes, busybox_data: bytes, local_shell: bytes) -> bytes:
    if not compatible_host():
        raise ValueError("exact BusyBox dispatch execution requires Linux aarch64")
    with tempfile.TemporaryDirectory(prefix="candidate-z-ash-dispatch.") as raw_dir:
        root = pathlib.Path(raw_dir)
        busybox = root / "busybox"
        actual_env = root / "reboot-dispatch.env"
        probe_dir = root / "bin"
        probe = probe_dir / "reboot"
        probe_env = root / "probe.env"
        probe_dir.mkdir(mode=0o700)
        busybox.write_bytes(busybox_data)
        busybox.chmod(0o700)
        actual_env.write_bytes(DISPATCH_BYTES)
        actual_env.chmod(0o444)
        probe.write_text(
            f"#!{busybox} sh\n"
            "printf 'CANDIDATE_Z_ABSOLUTE_WRAPPER argv=<%s>\\n' \"$*\"\n"
            "exit 73\n",
            encoding="utf-8",
        )
        probe.chmod(0o700)
        probe_env.write_text(f"alias reboot='{probe}'\n", encoding="utf-8")
        probe_env.chmod(0o444)

        runtime_oracle_probe(local_shell, busybox, actual_env, root)

        baseline = run_ash(busybox, None, "type reboot")
        if baseline.returncode != 0 or last_nonempty(baseline.stdout) != EXPECTED_BASELINE:
            raise ValueError("exact BusyBox baseline reboot collision changed")
        configured = run_ash(busybox, actual_env, "type reboot")
        if configured.returncode != 0 or \
                last_nonempty(configured.stdout) != EXPECTED_CONFIGURED:
            raise ValueError("ENV alias did not resolve bare reboot to /bin/reboot")
        noninteractive = run_ash(
            busybox, actual_env, "type reboot", interactive=False,
        )
        if noninteractive.returncode != 0 or \
                last_nonempty(noninteractive.stdout) != EXPECTED_BASELINE:
            raise ValueError(
                "noninteractive ash unexpectedly sourced ENV; wrapper could recurse"
            )
        invoked = run_ash(
            busybox,
            probe_env,
            "reboot; rc=$?; printf 'CANDIDATE_Z_PARENT_CONTINUED status=%s\\n' "
            '"$rc"; exit "$rc"',
        )
        invoked_lines = [
            line for line in invoked.stdout.decode("utf-8").splitlines() if line
        ]
        expected_invoked_tail = [
                "CANDIDATE_Z_ABSOLUTE_WRAPPER argv=<>",
                "CANDIDATE_Z_PARENT_CONTINUED status=73",
        ]
        if invoked.returncode != 73 or invoked_lines[-2:] != expected_invoked_tail or \
                any(invoked_lines.count(line) != 1 for line in expected_invoked_tail):
            raise ValueError(
                "bare reboot did not execute /bin/reboot and return to its parent shell"
            )
        missing_watchdog = root / "missing" / "watchdog0"
        redirection_probe = (
            "probe() { printf 'CANDIDATE_Z_FUNCTION_BODY_RAN\\n'; }; "
            f"if probe 3>{shlex.quote(os.fspath(missing_watchdog))}; then "
            "printf 'CANDIDATE_Z_WRONG_BRANCH\\n'; else "
            "printf 'CANDIDATE_Z_REDIRECTION_FAILURE_CONTINUED\\n'; fi"
        )
        redirected = run_ash(
            busybox, None, redirection_probe, interactive=False,
        )
        if redirected.returncode != 0 or \
                last_nonempty(redirected.stdout) != \
                "CANDIDATE_Z_REDIRECTION_FAILURE_CONTINUED" or \
                b"CANDIDATE_Z_FUNCTION_BODY_RAN" in redirected.stdout or \
                b"CANDIDATE_Z_WRONG_BRANCH" in redirected.stdout:
            raise ValueError(
                "failed function-call redirection did not reach the else branch"
            )
    return expected_result(digest(initramfs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--verify-saved", type=pathlib.Path)
    args = parser.parse_args()
    try:
        initramfs = read_regular(args.initramfs, "Candidate Z initramfs")
        members = parse_members(initramfs)
        busybox = members.get("bin/busybox")
        dispatch = members.get("bin/reboot-dispatch.env")
        local_shell = members.get("bin/local-shell")
        if busybox is None or not stat.S_ISREG(busybox.mode) or \
                digest(busybox.data) != BUSYBOX_SHA256:
            raise ValueError("exact Candidate BusyBox is absent or changed")
        if dispatch is None or not stat.S_ISREG(dispatch.mode) or \
                stat.S_IMODE(dispatch.mode) != 0o444 or dispatch.uid or dispatch.gid or \
                dispatch.mtime or dispatch.data != DISPATCH_BYTES:
            raise ValueError("immutable reboot-dispatch ENV member changed")
        if local_shell is None or not stat.S_ISREG(local_shell.mode):
            raise ValueError("Candidate Z local-shell is absent or not regular")
        expected = expected_result(digest(initramfs))
        if args.verify_saved is not None:
            saved = read_regular(args.verify_saved, "saved ash dispatch validation")
            if saved != expected:
                raise ValueError("saved ash dispatch validation does not match its inputs")
            if compatible_host():
                if execute(initramfs, busybox.data, local_shell.data) != saved:
                    raise ValueError("fresh ash dispatch result differs from saved result")
                print("ash_dispatch_rerun=passed")
            else:
                print("ash_dispatch_rerun=skipped-incompatible-host")
            print("saved_dispatch_validation=passed")
        else:
            sys.stdout.buffer.write(execute(initramfs, busybox.data, local_shell.data))
        return 0
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
