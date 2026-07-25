#!/usr/bin/env python3
"""Validate Candidate Z's dispatch-only initramfs delta from exact Candidate Y."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import re
import stat
import sys
from dataclasses import dataclass


Y_INITRAMFS_SHA256 = "11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
MARKER = "GEMINI_KEYBOARD_REBOOT_DISPATCH_20260719_Z"
CHANGED_MEMBERS = {"init", "bin/local-shell", "bin/reboot", "bin/x-record"}
ADDED_MEMBER = "bin/reboot-dispatch.env"
DISPATCH_BYTES = b"alias reboot='/bin/reboot'\n"
OVERLAY_SHA256 = {
    "init": "f5af474a9119dbd13e9bc88ab8b2b315cb4611f66bbb6b6e733ba36e3cba9b86",
    "local-shell": "5f80bd81838eaf4ac9a179959b4883efdfd4c4240105e7d1165eadeaf8b1777c",
    "reboot": "29ccd527fdf5fb6bb36fd09d41f76080df48ba608a239eb04c70de896b3349a2",
    "x-record": "1c5de956b09b242976039e181fa8fc6a6fe715540853079b7843c5db0146327d",
    "reboot-dispatch.env": (
        "8255ad7ab034cd3d760690a8b57eebcb67c974d321249ed8ee3a4f142f53e90a"
    ),
}


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


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(compressed: bytes) -> dict[str, Member]:
    if len(compressed) < 10 or compressed[:3] != b"\x1f\x8b\x08" or \
            compressed[4:8] != b"\0\0\0\0":
        raise ValueError("archive is not a deterministic gzip stream")
    raw = gzip.decompress(compressed)
    offset = 0
    members: dict[str, Member] = {}
    previous = ""
    while True:
        if offset + 110 > len(raw):
            raise ValueError("truncated newc header")
        header = raw[offset:offset + 110]
        if header[:6] != b"070701":
            raise ValueError("archive is not crc-free newc")
        try:
            fields = [int(header[6 + index * 8:14 + index * 8], 16)
                      for index in range(13)]
        except ValueError as exc:
            raise ValueError("invalid newc numeric field") from exc
        (_ino, mode, uid, gid, nlink, mtime, size, devmajor, devminor,
         rdevmajor, rdevminor, namesize, check) = fields
        if check != 0 or namesize < 2:
            raise ValueError("invalid newc checksum/name size")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("truncated or unterminated newc name")
        try:
            stored_name = raw[name_start:name_end - 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("non-UTF-8 newc member name") from exc
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc member data")
        if stored_name == "TRAILER!!!":
            if size != 0 or any(raw[align4(data_end):]):
                raise ValueError("invalid newc trailer or nonzero trailing padding")
            break
        name = stored_name.removeprefix("./") or "."
        parts = pathlib.PurePosixPath(name).parts
        if stored_name.startswith("/") or ".." in parts or name in members:
            raise ValueError("unsafe or duplicate newc member")
        if previous and name < previous:
            raise ValueError("newc members are not canonically sorted")
        previous = name
        members[name] = Member(
            mode, uid, gid, nlink, mtime, devmajor, devminor,
            rdevmajor, rdevminor, raw[data_start:data_end]
        )
        offset = align4(data_end)
    return members


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def text_member(members: dict[str, Member], name: str) -> str:
    member = members[name]
    if not stat.S_ISREG(member.mode):
        raise ValueError(f"script member is not regular: {name}")
    try:
        return member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"script member is not UTF-8: {name}") from exc


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        raise ValueError(f"required {label} is absent")


def require_once(text: str, token: str, label: str) -> None:
    if text.count(token) != 1:
        raise ValueError(f"required {label} is absent or duplicated")


def canonical_overlay(member: Member, mode: int, label: str) -> None:
    if not stat.S_ISREG(member.mode) or stat.S_IMODE(member.mode) != mode:
        raise ValueError(f"overlay type/mode changed: {label}")
    if member.uid or member.gid or member.mtime or member.devmajor or \
            member.devminor or member.rdevmajor or member.rdevminor or member.nlink != 1:
        raise ValueError(f"overlay metadata changed: {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline_data = read_regular(args.baseline, "Candidate Y initramfs")
        candidate_data = read_regular(args.candidate, "Candidate Z initramfs")
        if digest(baseline_data) != Y_INITRAMFS_SHA256:
            raise ValueError("baseline is not exact Candidate Y initramfs")
        baseline = parse_newc(baseline_data)
        candidate = parse_newc(candidate_data)
        expected_inventory = set(baseline) | {ADDED_MEMBER}
        if set(candidate) != expected_inventory or ADDED_MEMBER in baseline:
            raise ValueError("Candidate Z archive inventory is not exact Y plus dispatch ENV")

        changed = {name for name in baseline if candidate[name] != baseline[name]}
        if changed != CHANGED_MEMBERS:
            raise ValueError("Candidate Z does not change exactly four inherited members")
        for name in baseline:
            if name not in CHANGED_MEMBERS and candidate[name] != baseline[name]:
                raise ValueError(f"unapproved inherited archive member changed: {name}")
        for name in CHANGED_MEMBERS:
            canonical_overlay(candidate[name], 0o755, name)
        canonical_overlay(candidate[ADDED_MEMBER], 0o444, ADDED_MEMBER)
        if candidate[ADDED_MEMBER].data != DISPATCH_BYTES:
            raise ValueError("dispatch ENV is not the exact absolute reboot alias")
        if digest(candidate["bin/busybox"].data) != BUSYBOX_SHA256:
            raise ValueError("exact Candidate Y BusyBox changed")
        if digest(candidate["bin/input-event-capture"].data) != HELPER_SHA256:
            raise ValueError("exact Candidate Y input helper changed")

        init = text_member(candidate, "init")
        local_shell = text_member(candidate, "bin/local-shell")
        reboot = text_member(candidate, "bin/reboot")
        recorder = text_member(candidate, "bin/x-record")
        probe = text_member(candidate, "bin/x-probe")
        inittab = text_member(candidate, "etc/inittab")
        require(init, f"readonly MARKER='{MARKER}'", "Z init marker")
        require(recorder, f"readonly MARKER='{MARKER}'", "Z recorder marker")
        require(init, "entry profile=keyboard-reboot-dispatch", "Z profile")
        require(init, "clean_tty1_background=yes reboot_dispatch=env-alias",
                "clean tty1/dispatch policy")
        require(local_shell, "export PS1='GEMINI-Z# '", "Z prompt")
        require(local_shell, f"printf '%s\\n' '{MARKER}'", "visible Z marker")
        require(init, "/bin/x-probe &", "independent probe")
        if probe != text_member(baseline, "bin/x-probe"):
            raise ValueError("Candidate Y probe is not byte-exact")
        if inittab != text_member(baseline, "etc/inittab") or inittab != \
                "tty1::respawn:/bin/local-shell\n::ctrlaltdel:/bin/busybox true\n":
            raise ValueError("inittab or inert ctrl-alt-del policy changed")

        # The foreground local shell intentionally owns tty1. No background
        # path may write a visible tty, and no automatically started path,
        # including local-shell before user input, may touch the watchdog or
        # invoke a reset.
        background = "\n".join((init, recorder, probe, inittab))
        automatic_control = "\n".join((init, local_shell, recorder, probe, inittab))
        for token in ("/dev/tty0", "/dev/tty1", "/dev/tty2", "/dev/console"):
            if token in background:
                raise ValueError(f"automatic/background path writes visible tty: {token}")
        for token in ("/dev/watchdog", "/sys/class/watchdog", "10007000.watchdog"):
            if token in automatic_control:
                raise ValueError(f"automatic/background path gained watchdog access: {token}")
        if "/bin/busybox reboot" in automatic_control or re.search(
                r"(?m)^[ \t]*(?:/bin/)?reboot(?:[ \t]|$)", automatic_control):
            raise ValueError("automatic/background path gained reboot invocation")
        require_once(recorder, "output=/dev/ttyS0", "serial-only recorder output")
        if re.search(r"/dev/tty[0-9]+", recorder) or "/dev/console" in recorder:
            raise ValueError("recorder gained a virtual-console sink")
        if re.search(
                r"(?m)^[ \t]*(?:(?:/bin/)?busybox[ \t]+)?(?:printf|echo)(?:[ \t]|$)",
                probe):
            raise ValueError("background probe gained direct terminal output")

        # The exported ENV must be inherited by both the runtime oracle and the
        # final interactive non-login ash. Explicit command-scoped ENV would
        # mask a broken export and is therefore forbidden.
        local_required = (
            "readonly DISPATCH_ENV=/bin/reboot-dispatch.env",
            "readonly EXPECTED_DISPATCH='reboot is an alias for /bin/reboot'",
            "ENV=$DISPATCH_ENV",
            "readonly ENV",
            "export ENV",
            "/bin/busybox ash -ic 'type reboot' 2>/dev/null",
            "/bin/busybox tail -n 1",
            "reboot_dispatch=invalid",
            "tty1_shell=withheld",
            "reboot_dispatch=validated method=ENV-alias target=/bin/reboot",
            "exec /bin/busybox ash -i",
        )
        for token in local_required:
            require_once(local_shell, token, f"local-shell dispatch token {token}")
        if "ENV=\"$DISPATCH_ENV\" /bin/busybox" in local_shell or \
                "ash -il" in local_shell or "reboot()" in local_shell:
            raise ValueError("local shell masks ENV export or uses profile/function dispatch")
        env_line = local_shell.index("ENV=$DISPATCH_ENV")
        export_line = local_shell.index("export ENV")
        oracle_line = local_shell.index("ash -ic 'type reboot'")
        failure_line = local_shell.index("reboot_dispatch=invalid")
        prompt_line = local_shell.index("export PS1='GEMINI-Z# '")
        ready_line = local_shell.index("reboot_dispatch=validated")
        shell_line = local_shell.index("exec /bin/busybox ash -i")
        if not env_line < export_line < oracle_line < failure_line < prompt_line < ready_line < shell_line:
            raise ValueError("ENV/oracle/failure/prompt/interactive-shell ordering changed")
        failure_start = local_shell.index(
            'if [ "$dispatch" != "$EXPECTED_DISPATCH" ]; then'
        )
        failure_end = local_shell.index("\nfi\n", failure_start)
        failure_branch = local_shell[failure_start:failure_end]
        failure_hold = (
            "\twhile :; do\n"
            "\t\t/bin/busybox sleep 3600\n"
            "\tdone"
        )
        require_once(failure_branch, failure_hold, "dispatch-failure infinite hold")
        if not failure_branch.rstrip().endswith(failure_hold):
            raise ValueError("dispatch-failure hold is not the terminal failure action")

        refuse_definition = (
            "refuse() {\n"
            "\treason=$1\n"
            "\t/bin/x-record \"manual_reboot=refused reason=$reason "
            "watchdog_armed=no\"\n"
            "\tprintf 'Candidate Z: reboot refused; watchdog was not armed "
            "(%s).\\n' \"$reason\" >&2\n"
            "\texit 1\n"
            "}"
        )
        hold_armed_definition = (
            "hold_armed() {\n"
            "\t/bin/x-record \"$*; STATIC HOLD\"\n"
            "\tprintf '\\nCandidate Z: watchdog reset is overdue; fd3 remains "
            "open with no further writes.\\n' >&2\n"
            "\twhile :; do\n"
            "\t\t/bin/busybox sleep 3600\n"
            "\tdone\n"
            "}"
        )
        hold_after_return_definition = (
            "hold_after_session_return() {\n"
            "\t/bin/x-record \"$* fd3=closed-by-shell; STATIC HOLD\"\n"
            "\tprintf '\\nCandidate Z: watchdog session returned unexpectedly; "
            "fd3 is closed; STATIC HOLD.\\n' >&2\n"
            "\twhile :; do\n"
            "\t\t/bin/busybox sleep 3600\n"
            "\tdone\n"
            "}"
        )
        for definition, label in (
            (refuse_definition, "fail-closed refusal function"),
            (hold_armed_definition, "armed-watchdog infinite hold function"),
            (hold_after_return_definition, "returned-session infinite hold function"),
        ):
            require_once(reboot, definition, label)

        required_reboot = (
            "manual_reboot=requested trigger=bare-reboot dispatch=absolute-wrapper method=mtk-wdt-expiry watchdog_armed=no storage_access=none",
            "[ ! -e \"$LIVE_WATCHDOG/interrupts\" ]",
            "[ ! -e \"$LIVE_WATCHDOG/interrupts-extended\" ]",
            "[ -c /dev/watchdog0 ]",
            "[ -c /dev/kmsg ]",
            "ramoops_driver\" = ramoops",
            "[ -n \"$class_device\" ]",
            "[ -n \"$platform_device\" ]",
            "[ \"$class_device\" = \"$platform_device\" ]",
            "[ \"$platform_driver\" = mtk-wdt ]",
            "[ \"$identity\" = mtk-wdt ]",
            "[ \"$timeout\" = \"$WATCHDOG_TIMEOUT_SECONDS\" ]",
            "0|unavailable",
            "manual_reboot=validated",
            "observation-channel identity contracts passed",
            "trap '' HUP INT QUIT TERM TSTP",
            "watchdog_session() {",
            "if watchdog_session 3>/dev/watchdog0; then",
            "printf '.' >&3",
            "manual_reboot=armed watchdog0=armed handoff_ping=sent",
            "5|10|15|20|25|30|35|40",
            "manual_reboot=watchdog-expiry-failed boundary_seconds=40",
            "hold_after_session_return",
            "fd3=closed-by-shell",
        )
        for token in required_reboot:
            require(reboot, token, f"typed watchdog contract token {token}")
        require_once(reboot, "watchdog_session() {", "nonreturning watchdog session")
        require_once(reboot, "if watchdog_session 3>/dev/watchdog0; then",
                     "function-call watchdog open")
        require_once(reboot, "printf '.' >&3", "watchdog handoff write")
        open_result_block = (
            "if watchdog_session 3>/dev/watchdog0; then\n"
            "\thold_after_session_return "
            "'manual_reboot=watchdog-session-returned status=zero'\n"
            "else\n"
            "\trefuse watchdog0-open-failed\n"
            "fi"
        )
        require_once(
            reboot, open_result_block,
            "watchdog-open success hold and failure refusal branches",
        )
        if re.search(r"\bexec\b", reboot):
            raise ValueError("reboot wrapper gained forbidden exec syntax")

        request_line = reboot.index("manual_reboot=requested")
        ordered_preflight = [
            reboot.index("[ -d \"$LIVE_WATCHDOG\" ]", request_line),
            reboot.index("[ ! -e \"$LIVE_WATCHDOG/interrupts\" ]", request_line),
            reboot.index(
                "[ ! -e \"$LIVE_WATCHDOG/interrupts-extended\" ]", request_line
            ),
            reboot.index("[ -c /dev/watchdog0 ]", request_line),
            reboot.index("[ -c /dev/kmsg ]", request_line),
            reboot.index("[ -d \"$LIVE_RAMOOPS\" ]", request_line),
            reboot.index("[ -d \"$PLATFORM_RAMOOPS\" ]", request_line),
            reboot.index("[ \"$ramoops_driver\" = ramoops ]", request_line),
            reboot.index("[ -n \"$class_device\" ]", request_line),
            reboot.index("[ -n \"$platform_device\" ]", request_line),
            reboot.index("[ \"$class_device\" = \"$platform_device\" ]", request_line),
            reboot.index("[ \"$platform_driver\" = mtk-wdt ]", request_line),
            reboot.index("[ \"$identity\" = mtk-wdt ]", request_line),
            reboot.index("[ \"$timeout\" = \"$WATCHDOG_TIMEOUT_SECONDS\" ]", request_line),
            reboot.index("case \"$pretimeout\" in", request_line),
            reboot.index("manual_reboot=validated", request_line),
            reboot.index("trap '' HUP INT QUIT TERM TSTP", request_line),
            reboot.index("if watchdog_session 3>/dev/watchdog0; then", request_line),
        ]
        if ordered_preflight != sorted(ordered_preflight) or request_line >= ordered_preflight[0]:
            raise ValueError("request/preflight/validation/trap/open ordering changed")

        session_start = reboot.index("watchdog_session() {")
        session_end = reboot.index("\n}\n\nprintf", session_start)
        session = reboot[session_start:session_end]
        ping_failure_block = (
            "if ! printf '.' >&3; then\n"
            "\t\thold_armed 'manual_reboot=armed-uncertain "
            "watchdog0=handoff-ping-failed fd3=retained further_pings=none'\n"
            "\tfi"
        )
        require_once(session, ping_failure_block, "handoff-ping failure infinite hold")
        if len(re.findall(r"(?m)^[ \t]*hold_armed(?:[ \t]|$)", session)) != 2:
            raise ValueError("watchdog session does not have exactly two armed hold calls")
        if re.search(r"(?m)^[ \t]*(?:return|exit|break)(?:[ \t]|$)", session):
            raise ValueError("watchdog session gained a returning control-flow command")
        if not session.index("printf '.' >&3") < session.index("manual_reboot=armed") < \
                session.index("while [ \"$elapsed\" -lt") < \
                session.index("manual_reboot=watchdog-expiry-failed"):
            raise ValueError("ping/armed/countdown/failure execution order changed")
        if "readonly WATCHDOG_TIMEOUT_SECONDS=31" not in reboot or \
                "readonly WATCHDOG_FAILURE_SECONDS=40" not in reboot:
            raise ValueError("watchdog countdown bounds changed")
        if len(re.findall(r"(?m)^[ \t]*/bin/busybox sleep 1$", session)) != 1:
            raise ValueError("watchdog countdown does not contain exact one-second sleeps")
        countdown_prints = (
            "\tprintf 'Candidate Z: hardware watchdog armed; reset expected in %2s seconds.' \"$remaining\"",
            "\t\t\tprintf '\\rCandidate Z: hardware watchdog armed; reset expected in %2s seconds.' \"$remaining\"",
            "\t\t\tprintf '\\rCandidate Z: reset overdue by %2s seconds; fd3 retained, no ping.  ' \\\n"
            "\t\t\t\t\"$((elapsed - WATCHDOG_TIMEOUT_SECONDS))\"",
        )
        for visible_print in countdown_prints:
            require_once(
                session, visible_print + "\n", "exact foreground countdown printf line"
            )
        if len(re.findall(
                r"(?m)^[ \t]*printf ['\"](?:\\r)?Candidate Z: "
                r"(?:hardware watchdog armed|reset overdue)", session)) != 3:
            raise ValueError("visible watchdog countdown printf inventory changed")
        ordered_session = [
            session.index("printf '.' >&3"),
            session.index("manual_reboot=armed"),
            session.index("elapsed=0"),
            session.index(countdown_prints[0]),
            session.index('while [ "$elapsed" -lt "$WATCHDOG_FAILURE_SECONDS" ]; do'),
            session.index("/bin/busybox sleep 1"),
            session.index("elapsed=$((elapsed + 1))"),
            session.index(countdown_prints[1]),
            session.index(countdown_prints[2]),
            session.index('case "$elapsed" in'),
            session.index("5|10|15|20|25|30|35|40"),
            session.index("manual_reboot=waiting"),
            session.index("manual_reboot=watchdog-expiry-failed"),
        ]
        if ordered_session != sorted(ordered_session):
            raise ValueError("watchdog ping/countdown/marker/failure ordering changed")
        final_hold = (
            "\thold_armed 'manual_reboot=watchdog-expiry-failed "
            "boundary_seconds=40 fd3=retained further_pings=none'"
        )
        require_once(session, final_hold, "unconditional final watchdog hold")
        if not session.rstrip().endswith(final_hold):
            raise ValueError("watchdog session does not terminate in its static hold")

        # Normalize horizontal whitespace so alternate spellings such as
        # `1> & 3` cannot evade the exactly-one-write rule.
        fd3_outputs = re.findall(r"(?:\b[0-9]+[ \t]*)?>[ \t]*&[ \t]*3\b", reboot)
        watchdog_redirections = re.findall(
            r"(?:\b[0-9]+[ \t]*)?(?:>>?|<<?)[ \t]*/dev/watchdog[0-9]*\b", reboot
        )
        if len(fd3_outputs) != 1 or len(watchdog_redirections) != 1:
            raise ValueError("watchdog wrapper does not have exactly one open and one fd3 write")
        if re.search(r"(?:<|>>)[ \t]*&[ \t]*3\b|3[ \t]*>[ \t]*&[ \t]*-", reboot):
            raise ValueError("watchdog fd gained input, append, or close syntax")
        if re.search(r"(?:>|<)[ \t]*&[ \t]*(?:\"?\$|\$\{)", reboot) or re.search(
                r"(?m)^[ \t]*(?:(?:local|readonly)[ \t]+)?"
                r"[A-Za-z_][A-Za-z0-9_]*=3(?:[ \t]|$)", reboot):
            raise ValueError("watchdog fd gained variable redirection indirection")

        forbidden_patterns = {
            "BusyBox reboot": r"(?:/bin/)?busybox[ \t]+reboot\b",
            "direct reboot command": r"(?m)^[ \t]*(?:command[ \t]+)?(?:/sbin/|/bin/)?reboot(?:[ \t]|$)",
            "software reset fallback": r"\b(?:shutdown|poweroff|halt|kexec)\b|sysrq-trigger",
            "dynamic shell syntax": r"(?m)^[ \t]*(?:eval|source|\.)[ \t]+",
            "raw or block storage": (
                r"/dev/(?:mem|mmc|block)|(?m:(?:^|[;&|])[ \t]*"
                r"(?:(?:/bin/)?busybox[ \t]+|command[ \t]+)?"
                r"(?:/bin/)?(?:dd|sync|tee)(?:[ \t]|$))"
            ),
            "magic close": r"printf[ \t]+['\"]V['\"]",
        }
        for label, pattern in forbidden_patterns.items():
            if re.search(pattern, reboot):
                raise ValueError(f"forbidden reboot-wrapper behavior present: {label}")

        # Keep the exact reviewed sources pinned, but run the independent
        # semantic gates above first so mutation tests prove those rules rather
        # than merely tripping this checksum/equality backstop.
        for name in CHANGED_MEMBERS:
            source_name = pathlib.PurePosixPath(name).name
            source = read_regular(args.source_dir / source_name, name)
            if digest(source) != OVERLAY_SHA256[source_name]:
                raise ValueError(f"hash-pinned overlay source changed: {source_name}")
            if candidate[name].data != source:
                raise ValueError(f"archive/source mismatch: {name}")
        dispatch_source = read_regular(
            args.source_dir / "reboot-dispatch.env", ADDED_MEMBER
        )
        if digest(dispatch_source) != OVERLAY_SHA256["reboot-dispatch.env"] or \
                dispatch_source != DISPATCH_BYTES or \
                candidate[ADDED_MEMBER].data != dispatch_source:
            raise ValueError("dispatch source pin or archive/source equality changed")

        print("validation=candidate-z-initramfs")
        print(f"candidate_sha256={digest(candidate_data)}")
        print("baseline=exact-candidate-y")
        print("changed_members=init,bin/local-shell,bin/reboot,bin/x-record")
        print("added_member=bin/reboot-dispatch.env:0444")
        print(f"marker={MARKER}")
        print("reboot_dispatch=ENV-alias-absolute-wrapper")
        print("runtime_dispatch_oracle=inherited-exported-ENV")
        print("clean_tty1_background_policy=passed")
        print("watchdog_ownership=typed-only")
        print("watchdog_open=function-call-redirection")
        print("userspace_handoff_pings=one")
        print("software_reboot_fallback=none")
        print("hardware_write=none")
        return 0
    except (EOFError, OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
