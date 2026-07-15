#!/usr/bin/env python3
"""Summarize a private first-boot UART log without publishing identifiers."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REDACTIONS = (
    (re.compile(r"(?i)(androidboot\.serialno=|serial(?:no)?[=:])(\S+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(imei[=:])(\S+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(mac(?:address)?[=:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}"), r"\1<redacted>"),
    (re.compile(r"(?i)(partuuid=)[0-9a-f-]+"), r"\1<redacted>"),
    (re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f-]{27}\b"), "<redacted-uuid>"),
)

FIELD_PATTERNS = {
    "kernel": re.compile(r"^kernel=(\S+)$"),
    "candidate_console": re.compile(r"^candidate_console=(\S+)$"),
    "cmdline_console": re.compile(r"^cmdline_console=(\S+)$"),
    "cmdline_earlycon": re.compile(r"^cmdline_earlycon=(\S+)$"),
    "cmdline_maxcpus": re.compile(r"^cmdline_maxcpus=(\S+)$"),
    "cmdline_printk_disable_uart": re.compile(
        r"^cmdline_printk\.disable_uart=(\S+)$"
    ),
    "cmdline_root": re.compile(r"^cmdline_root=(\S+)$"),
    "cpu_online": re.compile(r"^cpu_online=(\S+)$"),
    "cpu_present": re.compile(r"^cpu_present=(\S+)$"),
    "mem_total_kb": re.compile(r"^mem_total_kb=(\d+)$"),
}


def sanitize(line: str) -> str:
    for pattern, replacement in REDACTIONS:
        line = pattern.sub(replacement, line)
    return line.rstrip("\n")


def read_lines(path: str) -> list[str]:
    if path == "-":
        return [sanitize(line) for line in sys.stdin]
    return [sanitize(line) for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", help="private UART log path, or - for stdin")
    args = parser.parse_args()
    lines = read_lines(args.log)

    fields: dict[str, str] = {}
    for line in lines:
        for name, pattern in FIELD_PATTERNS.items():
            match = pattern.search(line)
            if match:
                fields[name] = match.group(1)

    joined = "\n".join(lines).lower()
    initramfs_marker = "gemini mainline initramfs" in joined
    early_console = "earlycon" in joined or "early console" in joined
    normal_console = "console [ttys" in joined or "serial8250" in joined
    panic = bool(re.search(r"\b(oops|panic|kernel bug|call trace)\b", joined))
    error_lines = sum(
        bool(re.search(r"\b(error|failed|timeout|timed out)\b", line.lower()))
        for line in lines
    )
    reservation_conflict = bool(
        re.search(r"reserved.*(overlap|conflict)|mblock.*(overlap|conflict)", joined)
    )
    watchdog = "watchdog" in joined or "toprgu" in joined
    emmc = "mmc" in joined or "msdc" in joined

    print("validation=first-boot-log-summary")
    print("input_private_log=yes")
    print(f"initramfs_marker={'yes' if initramfs_marker else 'no'}")
    for name in FIELD_PATTERNS:
        if name in fields:
            print(f"{name}={fields[name]}")
    print(f"early_console_seen={'yes' if early_console else 'no'}")
    print(f"normal_console_seen={'yes' if normal_console else 'no'}")
    print(f"watchdog_evidence={'yes' if watchdog else 'no'}")
    print(f"emmc_or_msdc_evidence={'yes' if emmc else 'no'}")
    print(f"error_line_count={error_lines}")
    print(f"panic_seen={'yes' if panic else 'no'}")
    print(f"reservation_conflict_seen={'yes' if reservation_conflict else 'no'}")
    print("decision=manual_review_required")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
