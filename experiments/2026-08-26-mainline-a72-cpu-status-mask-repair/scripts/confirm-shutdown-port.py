#!/usr/bin/env python3
"""Require consecutive TCP connection failures before declaring shutdown."""

from __future__ import annotations

import argparse
import socket
import time
from collections.abc import Callable


Probe = Callable[[], bool]


def wait_for_closed(
    probe_open: Probe,
    *,
    attempts: int,
    required_consecutive: int,
    interval: float,
    sleep: Callable[[float], None] = time.sleep,
) -> int | None:
    if attempts < 1 or required_consecutive < 1 or required_consecutive > attempts:
        raise ValueError("invalid shutdown observation bounds")
    consecutive = 0
    for attempt in range(1, attempts + 1):
        if probe_open():
            consecutive = 0
        else:
            consecutive += 1
            if consecutive == required_consecutive:
                return attempt
        if attempt != attempts:
            sleep(interval)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--attempts", type=int, default=20)
    parser.add_argument("--required-consecutive", type=int, default=3)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or args.interval < 0 or args.timeout <= 0:
        raise SystemExit("invalid TCP shutdown observation argument")

    def probe_open() -> bool:
        try:
            with socket.create_connection(
                (args.address, args.port), timeout=args.timeout
            ):
                return True
        except OSError:
            return False

    try:
        used = wait_for_closed(
            probe_open,
            attempts=args.attempts,
            required_consecutive=args.required_consecutive,
            interval=args.interval,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if used is None:
        print("shutdown_tcp_port=still-open-or-inconclusive")
        return 3
    print("shutdown_tcp_22=confirmed-closed")
    print(f"shutdown_tcp_consecutive_failures={args.required_consecutive}")
    print(f"shutdown_tcp_attempts_used={used}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
