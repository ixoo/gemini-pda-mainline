#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Adopt one pinned public snapshot on Buildbox; inspect unless --execute.

No network, extraction, source-tree synchronization or device access. The CLI
has no path/digest overrides. Both existing cooperating locks are required.
The internal Spec/adopt interface exists solely for small synthetic fixtures.
"""
import argparse
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import signal
import stat

REVISION = "4d7d9486c04d917265f64c55bd23b2cc4fe7749c"
SHA256 = "45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d"
SIZE = 269814253
HEADROOM = 64 * 1024 * 1024
CHUNK = 1024 * 1024
WORKSPACE = Path("/workspace/gemini-pda")


@dataclass(frozen=True)
class Spec:
    source: Path
    destination: Path
    build_lock: Path
    acquire_lock: Path
    size: int
    sha256: str


def production_spec():
    # Do not let HOME or command-line options redirect cache mutation.
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    source_cache = WORKSPACE / "cache/upstream-snapshots"
    return Spec(source_cache / ("linux-" + REVISION + ".tar.gz"),
                home / ".cache/gemini-pda" / ("linux-" + SHA256 + ".tar.gz"),
                home / "gemini-pda-buildbox/build.lock",
                source_cache / ".acquire.lock", SIZE, SHA256)


def identity(info):
    return {key: getattr(info, "st_" + key) for key in
            ("dev", "ino", "size", "mtime_ns", "ctime_ns")}


def same_file(left, right):
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def valid_identity(value, size):
    keys = {"dev", "ino", "size", "mtime_ns", "ctime_ns"}
    return (isinstance(value, dict) and set(value) == keys
            and all(type(number) is int and number >= 0 for number in value.values())
            and value["size"] == size)


def directory(path):
    """Open every absolute path component without following symlinks."""
    if not path.is_absolute() or any(p in (".", "..") for p in path.parts):
        raise ValueError("absolute canonical directory required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=fd)
            os.close(fd)
            fd = following
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError("managed directory must be owned and not writable by others")
        return fd
    except BaseException:
        os.close(fd)
        raise


def lookup(parent, name):
    try:
        return os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None


def regular(info, *, links=1):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022 or info.st_nlink != links):
        raise ValueError("unsafe file type, ownership, permissions or links")


def open_regular(parent, name, *, links=1):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        regular(os.fstat(fd), links=links)
        return fd
    except BaseException:
        os.close(fd)
        raise


def check_name(parent, name, expected):
    current = lookup(parent, name)
    if current is None or identity(current) != identity(expected):
        raise ValueError("file identity changed")
    return current


def digest(fd, size, expected_sha):
    before = os.fstat(fd)
    if before.st_size != size:
        raise ValueError("archive size mismatch")
    os.lseek(fd, 0, os.SEEK_SET)
    sha = hashlib.sha256()
    remaining = size
    while remaining:
        chunk = os.read(fd, min(CHUNK, remaining))
        if not chunk:
            raise ValueError("short archive read")
        remaining -= len(chunk)
        sha.update(chunk)
    if os.read(fd, 1) or identity(os.fstat(fd)) != identity(before):
        raise ValueError("archive changed during read")
    if sha.hexdigest() != expected_sha:
        raise ValueError("archive digest mismatch")
    return before


def partial_state(parent, name, final, bound):
    """Only this helper's exact, private, bounded temporary files qualify."""
    info = lookup(parent, name)
    if info is None:
        return None
    links = 2 if final is not None and same_file(info, final) else 1
    regular(info, links=links)
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > bound:
        raise ValueError("unsafe managed partial")
    return info


def remove_partial(parent, name, info):
    if info is not None:
        check_name(parent, name, info)
        os.unlink(name, dir_fd=parent)
        os.fsync(parent)


def read_receipt(parent, name, *, links=1):
    fd = open_regular(parent, name, links=links)
    try:
        before = os.fstat(fd)
        if before.st_size > 16384:
            raise ValueError("oversized adoption receipt")
        data = os.read(fd, 16385)
        if len(data) != before.st_size or identity(os.fstat(fd)) != identity(before):
            raise ValueError("adoption receipt changed during read")
        check_name(parent, name, before)
        return json.loads(data), before
    finally:
        os.close(fd)


@contextmanager
def bounded_signals():
    def interrupted(number, _frame):
        raise InterruptedError("archive adoption interrupted by signal " + str(number))

    signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGALRM)
    previous = {number: signal.getsignal(number) for number in signals}
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise ValueError("refuse to replace an existing process timer")
    try:
        for number in signals:
            signal.signal(number, interrupted)
        signal.setitimer(signal.ITIMER_REAL, 300)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for number, handler in previous.items():
            signal.signal(number, handler)


def adopt(spec, *, execute=False, event=lambda _name: None):
    """One bounded transaction; test callbacks never enter the production CLI."""
    partial = ".adopt-" + spec.sha256 + ".partial"
    receipt_name = spec.destination.name + ".adoption.json"
    receipt_partial = ".adopt-" + spec.sha256 + ".receipt.partial"
    with ExitStack() as stack:
        stack.enter_context(bounded_signals())
        parents = {}
        for path in (spec.build_lock.parent, spec.acquire_lock.parent,
                     spec.source.parent, spec.destination.parent):
            if path not in parents:
                parents[path] = directory(path)
                stack.callback(os.close, parents[path])
        # Use the normal build lock first. Existing locks only: inspection
        # must not create files, and a missing lock is an unprepared backend.
        for path in (spec.build_lock, spec.acquire_lock):
            fd = open_regular(parents[path.parent], path.name)
            stack.callback(os.close, fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            check_name(parents[path.parent], path.name, os.fstat(fd))
        event("locked")
        src, dst = parents[spec.source.parent], parents[spec.destination.parent]
        source_info, final_info = lookup(src, spec.source.name), lookup(dst, spec.destination.name)
        source_fd = final_fd = None
        if source_info is not None:
            source_fd = open_regular(src, spec.source.name)
            stack.callback(os.close, source_fd)
            source_info = digest(source_fd, spec.size, spec.sha256)
            check_name(src, spec.source.name, source_info)
        if final_info is not None:
            staged_info = partial_state(dst, partial, final_info, spec.size)
            links = 2 if staged_info is not None and same_file(staged_info, final_info) else 1
            final_fd = open_regular(dst, spec.destination.name, links=links)
            stack.callback(os.close, final_fd)
            final_info = digest(final_fd, spec.size, spec.sha256)
            check_name(dst, spec.destination.name, final_info)
        else:
            staged_info = partial_state(dst, partial, None, spec.size)
        if source_info is None and final_info is None:
            raise ValueError("no verified archive remains")

        receipt_info = lookup(dst, receipt_name)
        receipt_staged = partial_state(dst, receipt_partial, receipt_info, 16384)
        receipt = None
        if receipt_info is not None:
            links = 2 if receipt_staged is not None and same_file(receipt_staged, receipt_info) else 1
            receipt, receipt_info = read_receipt(dst, receipt_name, links=links)
            expected_keys = {"schema", "source", "destination", "bytes", "sha256",
                             "source_identity", "destination_identity", "state"}
            if (not isinstance(receipt, dict) or set(receipt) != expected_keys
                    or receipt["schema"] != 1 or receipt["source"] != str(spec.source)
                    or receipt["destination"] != str(spec.destination)
                    or receipt["bytes"] != spec.size or receipt["sha256"] != spec.sha256
                    or receipt["state"] != "destination-verified-before-source-removal"
                    or not valid_identity(receipt["source_identity"], spec.size)
                    or final_info is None
                    or receipt["destination_identity"] != identity(final_info)
                    or (source_info is not None
                        and receipt["source_identity"] != identity(source_info))):
                raise ValueError("adoption receipt does not match the verified state")
        if source_info is None and receipt is None:
            raise ValueError("missing source requires a matching durable receipt")

        space = os.fstatvfs(dst)
        available = space.f_bavail * space.f_frsize
        needed = HEADROOM + (spec.size if final_info is None else 0)
        if available < needed:
            raise ValueError("insufficient destination space including headroom")
        result = {"execute": execute, "source_present": source_info is not None,
                  "destination_present": final_info is not None,
                  "bytes": spec.size, "sha256": spec.sha256,
                  "destination": str(spec.destination), "receipt": str(spec.destination.parent / receipt_name),
                  "stale_partial": staged_info is not None or receipt_staged is not None,
                  "available_bytes": available, "required_bytes": needed}
        if not execute:
            return result

        # All existing source/final/receipt state has been classified before
        # deleting even a stale managed partial. A published copy is retained.
        remove_partial(dst, partial, staged_info)
        remove_partial(dst, receipt_partial, receipt_staged)
        # Removing a temporary hard link changes ctime on a published file.
        if final_fd is not None:
            final_info = os.fstat(final_fd)
        if receipt is not None and receipt["destination_identity"] != identity(final_info):
            raise ValueError("receipt predates recovered link cleanup; reconcile before removal")

        owned = {}
        try:
            if final_info is None:
                fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=dst)
                owned[partial] = os.fstat(fd)
                try:
                    os.lseek(source_fd, 0, os.SEEK_SET)
                    copied, sha = 0, hashlib.sha256()
                    while copied < spec.size:
                        chunk = os.read(source_fd, min(CHUNK, spec.size - copied))
                        if not chunk:
                            raise ValueError("short source during copy")
                        copied += len(chunk)
                        sha.update(chunk)
                        view = memoryview(chunk)
                        while view:
                            written = os.write(fd, view)
                            if written <= 0:
                                raise OSError("short destination write")
                            view = view[written:]
                        event("copy-chunk")
                    if os.read(source_fd, 1) or sha.hexdigest() != spec.sha256:
                        raise ValueError("source changed during copy")
                    check_name(src, spec.source.name, source_info)
                    if identity(os.fstat(source_fd)) != identity(source_info):
                        raise ValueError("source descriptor changed during copy")
                    os.fsync(fd)
                finally:
                    os.close(fd)
                # Atomic no-replace publication on the destination filesystem.
                os.link(partial, spec.destination.name, src_dir_fd=dst, dst_dir_fd=dst,
                        follow_symlinks=False)
                os.fsync(dst)
                event("published-with-partial")
                os.unlink(partial, dir_fd=dst)
                owned.pop(partial)
                os.fsync(dst)
                event("published")
                final_fd = open_regular(dst, spec.destination.name)
                stack.callback(os.close, final_fd)
                final_info = digest(final_fd, spec.size, spec.sha256)
                check_name(dst, spec.destination.name, final_info)

            if receipt is None:
                receipt = {"schema": 1, "source": str(spec.source),
                           "destination": str(spec.destination), "bytes": spec.size,
                           "sha256": spec.sha256, "source_identity": identity(source_info),
                           "destination_identity": identity(final_info),
                           "state": "destination-verified-before-source-removal"}
                data = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
                fd = os.open(receipt_partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=dst)
                owned[receipt_partial] = os.fstat(fd)
                try:
                    with os.fdopen(fd, "wb", closefd=False) as output:
                        output.write(data)
                        output.flush()
                        os.fsync(fd)
                finally:
                    os.close(fd)
                os.link(receipt_partial, receipt_name, src_dir_fd=dst, dst_dir_fd=dst,
                        follow_symlinks=False)
                os.fsync(dst)
                event("receipt-published-with-partial")
                os.unlink(receipt_partial, dir_fd=dst)
                owned.pop(receipt_partial)
                os.fsync(dst)
            event("receipt-durable")
            reread, receipt_info = read_receipt(dst, receipt_name)
            if reread != receipt:
                raise ValueError("published receipt failed readback")
            os.fsync(dst)
            # Confirm canonical directory paths still name our held descriptors.
            for path, fd in parents.items():
                verify_fd = directory(path)
                try:
                    if not same_file(os.fstat(fd), os.fstat(verify_fd)):
                        raise ValueError("managed directory identity changed")
                finally:
                    os.close(verify_fd)
            check_name(dst, spec.destination.name, final_info)
            digest(final_fd, spec.size, spec.sha256)
            if source_info is not None:
                digest(source_fd, spec.size, spec.sha256)
                check_name(src, spec.source.name, source_info)
                check_name(dst, spec.destination.name, final_info)
                check_name(dst, receipt_name, receipt_info)
                os.unlink(spec.source.name, dir_fd=src)
                os.fsync(src)
            if lookup(src, spec.source.name) is not None:
                raise ValueError("old source unexpectedly remains")
            check_name(dst, spec.destination.name, final_info)
            result.update(source_present=False, destination_present=True,
                          stale_partial=False, state="adopted")
            return result
        finally:
            for name, info in owned.items():
                current = lookup(dst, name)
                if current is not None and same_file(current, info):
                    os.unlink(name, dir_fd=dst)
                    os.fsync(dst)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="migrate the fixed public snapshot after all refusal checks")
    args = parser.parse_args()
    here = Path(__file__).resolve()
    if platform.system() != "Linux" or WORKSPACE not in here.parents:
        parser.error("run from the managed Buildbox checkout")
    try:
        print(json.dumps(adopt(production_spec(), execute=args.execute), sort_keys=True, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, "archive adoption refused: " + str(error) + "\n")


if __name__ == "__main__":
    main()
