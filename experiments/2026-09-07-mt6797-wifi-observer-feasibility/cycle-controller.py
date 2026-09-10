#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Unselected minimal-startup controller; import only from an admitted candidate.

The caller owns kernel/input provenance, fixed firmware lookups, actor isolation,
capture storage and the approved recovery session. No candidate supplies these
yet. Returning or raising never authorizes retry, cleanup, disarm or restart.
"""
import fcntl
import importlib.util
import os
from pathlib import Path
import platform
import select
import threading
import time
import uuid


spec = importlib.util.spec_from_file_location("cycle_responder", Path(__file__).with_name("respond-once.py"))
responder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(responder)

CAPTURE_INIT = 0x40607709
CAPTURE_ABI = 0x770A
CAPTURE_ABI_VERSION = 0x57464301
SET_STP_MODE = 0x4004A005
FUNC_ONOFF = 0x4004A006
WLAN_ON = 0x80000003
WLAN_OFF = 3


def checked_ioctl(fd, request, argument, deadline):
    responder.check_deadline(deadline)
    result = fcntl.ioctl(fd, request, argument)
    responder.check_deadline(deadline)
    if result != 0:
        raise RuntimeError(f"controller ioctl 0x{request:x} returned {result}")


def receive(fd, expected, deadline):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    remaining = responder.check_deadline(deadline)
    events = poller.poll((remaining + 999999) // 1000000)
    responder.check_deadline(deadline)
    if len(events) != 1 or events[0][0] != fd or not events[0][1] & select.POLLIN:
        raise RuntimeError("responder did not report the required stage")
    if events[0][1] & ~(select.POLLIN | select.POLLHUP):
        raise RuntimeError("responder status pipe failed")
    stage = os.read(fd, 1)
    if stage == b"F":
        reason = os.read(fd, 240).decode("utf-8", "replace")
        raise RuntimeError(f"responder failed: {reason}")
    if stage != expected:
        raise RuntimeError("responder failed or reported an unexpected stage")
    responder.check_deadline(deadline)


def request_pair(fd, records, chip, version, deadline):
    """Run ON on this task, join the one responder child, then run OFF."""
    # Poll observes the pending bit without consuming a command.
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    if poller.poll(0):
        raise RuntimeError("pending command or WMT poll error before ON")
    response_deadline = min(deadline, time.monotonic_ns() + 1500000000)
    responder.check_deadline(response_deadline)
    read_fd, write_fd = os.pipe()
    child = None
    joined = False
    try:
        os.set_blocking(read_fd, False)
        os.set_blocking(write_fd, False)
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            status = 1
            try:
                responder.check_deadline(response_deadline)
                if os.write(write_fd, b"R") != 1:
                    raise RuntimeError("short readiness write")
                result = responder.serve(fd, response_deadline, records, chip, version)
                if result["stage"] != "reply-written" or os.write(write_fd, b"S") != 1:
                    raise RuntimeError("responder did not complete")
                status = 0
            except BaseException as error:
                try:
                    reason = f"{type(error).__name__}: {error}".encode("utf-8", "replace")[:240]
                    # One bounded atomic pipe write keeps the error with its stage.
                    os.write(write_fd, b"F" + reason)
                except OSError:
                    pass
            os._exit(status)
        os.close(write_fd)
        write_fd = None
        receive(read_fd, b"R", response_deadline)
        exited, _ = os.waitpid(child, os.WNOHANG)
        if exited:
            joined = True
            raise RuntimeError("responder exited before ON")
        responder.check_deadline(response_deadline)
        checked_ioctl(fd, FUNC_ONOFF, WLAN_ON, deadline)
        receive(read_fd, b"S", deadline)
        responder.check_deadline(deadline)
        exited, status = os.waitpid(child, 0)
        joined = True
        responder.check_deadline(deadline)
        if exited != child or not os.WIFEXITED(status) or os.WEXITSTATUS(status):
            raise RuntimeError("responder did not exit successfully")
        checked_ioctl(fd, FUNC_ONOFF, WLAN_OFF, deadline)
        return {"stage": "producer-completed", "responder_joined": True,
                "result": "requires recovered capture and independent classification"}
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if child and not joined:
            # Reap an already exited child only. No kill, blocking failure cleanup
            # or replacement request; the armed watchdog owns a stalled attempt.
            try:
                os.waitpid(child, os.WNOHANG)
            except ChildProcessError:
                pass


def run_cycle(detector_fd, identity, expected_release, firmware_directory, chip, version):
    """Caller supplies the reviewed 96-byte cycle/candidate/boot/input identity."""
    responder.check_abi(chip, version)
    if (platform.machine() != "aarch64" or not expected_release or
            platform.release() != expected_release or threading.active_count() != 1):
        raise RuntimeError("requires the selected ARM64 kernel and a single-threaded controller")
    if (not isinstance(identity, bytes) or len(identity) != 96 or
            any(not any(identity[start:end]) for start, end in ((0, 16), (16, 48), (48, 64), (64, 96)))):
        raise ValueError("requires complete nonzero cycle/candidate/boot/input identities")
    boot = uuid.UUID(Path("/proc/sys/kernel/random/boot_id").read_text().strip()).bytes
    if identity[48:64] != boot:
        raise ValueError("capture identity does not match this boot")
    responder.check_descriptor(detector_fd, "wmtdetect")
    if fcntl.ioctl(detector_fd, CAPTURE_ABI, 0) != CAPTURE_ABI_VERSION:
        raise RuntimeError("detector does not implement the recorded controller protocol")
    records = responder.prepare_patches(firmware_directory)
    # Start software accounting before takeover. Never extend the hardware cutoff.
    deadline = time.monotonic_ns() + 12000000000
    checked_ioctl(detector_fd, CAPTURE_INIT, bytearray(identity), deadline)
    fd = os.open("/dev/stpwmt", os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        responder.check_descriptor(fd)
        checked_ioctl(fd, SET_STP_MODE, 0x23, deadline)
        return request_pair(fd, records, chip, version, deadline)
    finally:
        os.close(fd)  # Descriptor release is not hardware teardown.


if __name__ == "__main__":
    raise SystemExit("Import-only controller: no admitted candidate or standalone run command exists.")
