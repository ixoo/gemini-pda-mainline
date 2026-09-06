#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic refusal and privacy fixtures; never contacts a device."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_collect", HERE / "collect.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

BOOT = "c8e2c5cb-ab22-4c2f-b5ab-51c1e0ee5831"
DIGESTS = {
    "release": MODULE.EXPECTED_RELEASE,
    "architecture": MODULE.EXPECTED_ARCH,
    "boot_id": BOOT,
    "wifi_sha256": "a" * 64,
    "nvram_daemon_sha256": "b" * 64,
    "libnvram_sha256": "c" * 64,
}


def valid_stream(*, wifi_size=514, wifi_envelope="valid", boot_end=BOOT,
                 wifi_digest="a" * 64, daemon_digest="b" * 64,
                 lib_digest="c" * 64) -> bytes:
    return (f"""release_start={MODULE.EXPECTED_RELEASE}
arch_start={MODULE.EXPECTED_ARCH}
boot_id_start={BOOT}
container_state=running
pid_status=one
admission_ready=yes
mountinfo_status=valid
mount_nvdata_count=1
mount_data_nvram_count=1
mount_relation=yes
wifi_status=present
wifi_size={wifi_size}
wifi_envelope={wifi_envelope}
wifi_digest={wifi_digest}
daemon_status=present
daemon_size=123
daemon_digest={daemon_digest}
lib_status=present
lib_size=456
lib_digest={lib_digest}
release_end={MODULE.EXPECTED_RELEASE}
arch_end={MODULE.EXPECTED_ARCH}
boot_id_end={boot_end}
""").encode()


def refused(call, fragment: str) -> None:
    try:
        call()
    except MODULE.CollectionError as error:
        assert fragment in str(error), (fragment, str(error))
    else:
        raise AssertionError(f"expected refusal containing {fragment!r}")


def write_admission(path: Path, mode: int = 0o600) -> None:
    path.write_text(json.dumps(DIGESTS), encoding="utf-8")
    os.chmod(path, mode)


def envelope(payload: bytes) -> bool:
    if len(payload) != 514 or payload[512] != 0xAA:
        return False
    check = 0
    for index, value in enumerate(payload[:512]):
        check = ((check + value) & 0xFF) if index % 2 == 0 else check ^ value
    return payload[513] == check


def main() -> None:
    dry_output = io.StringIO()
    with patch.object(MODULE.subprocess, "Popen", side_effect=AssertionError("SSH in dry run")):
        with redirect_stdout(dry_output):
            assert MODULE.main([]) == 0
    assert "no SSH" in dry_output.getvalue()
    raw = valid_stream()
    info = MODULE.validate_process(raw, 0)
    result = MODULE.sanitized_record(info, DIGESTS, consumed=True)
    assert result["narrow_pass"] and result["attempt_consumed"]
    assert not any(secret in json.dumps(result) for secret in (BOOT, "a" * 64, "b" * 64, "c" * 64))

    refused(lambda: MODULE.validate_process(raw.rsplit(b"boot_id_end", 1)[0], 0), "boot_id_end")
    refused(lambda: MODULE.validate_process(valid_stream(boot_end="0" * 36), 0), "boot identity changed")
    refused(lambda: MODULE.validate_process(valid_stream(wifi_size=513), 0), "present WIFI record")
    assert not MODULE.sanitized_record(
        MODULE.validate_process(valid_stream(wifi_envelope="invalid"), 0), DIGESTS,
        consumed=True)["narrow_pass"]
    for mutated in (
        raw.replace(b"daemon_status=present", b"daemon_status=symlink").replace(
            b"daemon_digest=" + b"b" * 64 + b"\n", b""),
        raw.replace(b"lib_status=present", b"lib_status=nonregular").replace(
            b"lib_digest=" + b"c" * 64 + b"\n", b""),
        raw.replace(b"daemon_status=present", b"daemon_status=read-error").replace(
            b"daemon_digest=" + b"b" * 64 + b"\n", b""),
        raw.replace(b"mount_relation=yes", b"mount_relation=no"),
    ):
        mutated_info = MODULE.validate_process(mutated, 0)
        assert not MODULE.sanitized_record(mutated_info, DIGESTS, consumed=True)["narrow_pass"]
    mismatch_info = MODULE.validate_process(valid_stream(lib_digest="d" * 64), 0)
    assert not MODULE.sanitized_record(mismatch_info, DIGESTS, consumed=True)["lib_digest_match"]
    oversize = valid_stream().replace(b"daemon_status=present", b"daemon_status=oversize").replace(
        b"daemon_size=123", b"daemon_size=4194305").replace(
        b"daemon_digest=" + b"b" * 64 + b"\n", b"")
    assert not MODULE.sanitized_record(MODULE.validate_process(oversize, 0), DIGESTS,
                                       consumed=True)["narrow_pass"]
    for field, size in ((b"daemon_size=123", b"daemon_size=0"),
                        (b"daemon_size=123", b"daemon_size=4194305"),
                        (b"lib_size=456", b"lib_size=0"),
                        (b"lib_size=456", b"lib_size=4194305")):
        refused(lambda field=field, size=size: MODULE.validate_process(
            raw.replace(field, size), 0), "present size outside bound")
    refused(lambda: MODULE.validate_process(raw, 124), "after identity")
    wrong_boot = raw.replace(BOOT.encode(), b"0" * 36)
    refused(lambda: MODULE.validate_process(wrong_boot, 0, expected_boot_id=BOOT), "does not match")
    refused(lambda: MODULE.validate_process(b"x" * (MODULE.MAX_OUTPUT + 1), 0), "8 KiB")
    refused(lambda: MODULE.validate_process(raw, 0, timed_out=True), "20 second")
    refused(lambda: MODULE.parse_output(raw + b"unexpected=x\n"), "trailing")
    refused(lambda: MODULE.parse_output(raw.replace(b"mount_relation=yes", b"mount_relation=maybe")), "invalid field")
    refused(lambda: MODULE.parse_output(raw.replace(b"wifi_digest=" + b"a" * 64, b"wifi_digest=" + b"A" * 64)), "digest")

    # Every truncation and extension of the fixed storage envelope is rejected.
    storage = bytearray(512)
    storage.extend((0xAA, 0))
    check = 0
    for index, value in enumerate(storage[:512]):
        check = ((check + value) & 0xFF) if index % 2 == 0 else check ^ value
    storage[513] = check
    assert envelope(bytes(storage))
    assert all(not envelope(bytes(storage[:length])) for length in range(514))
    assert not envelope(bytes(storage) + b"x")
    for index in range(514):
        mutated = bytearray(storage)
        mutated[index] ^= 1
        assert not envelope(bytes(mutated))

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        admission = root / "admission.json"
        write_admission(admission)
        assert MODULE.load_admission(admission) == DIGESTS
        os.chmod(admission, 0o644)
        refused(lambda: MODULE.load_admission(admission), "unsafe mode")
        os.chmod(admission, 0o600)
        attempt = root / "attempt"
        MODULE.create_attempt_dir(attempt)
        assert stat.S_IMODE(attempt.stat().st_mode) == 0o700
        MODULE._write_private(attempt / "raw-stream.txt", raw)
        assert stat.S_IMODE((attempt / "raw-stream.txt").stat().st_mode) == 0o600
        refused(lambda: MODULE.create_attempt_dir(attempt), "already exists")

        over_raw, over_code, over_timed = MODULE.run_bounded(
            [sys.executable, "-c", "import sys;sys.stdout.write('x'*9000)"], b"",
            local_seconds=2, max_output=MODULE.MAX_OUTPUT)
        assert len(over_raw) == MODULE.MAX_OUTPUT and over_code != 0 and not over_timed
        seen = []
        def ack(stream):
            seen.append(True)
            stream.write(b"GEMINI-WIFI-NVRAM-CONSUME-v1\n")
            stream.flush()
            stream.close()
        barrier_raw, barrier_code, barrier_timed = MODULE.run_bounded(
            [sys.executable, "-c", "import sys; print('admission_ready=yes', flush=True); print('ack='+sys.stdin.readline().strip(), flush=True)"],
            b"", local_seconds=2, on_admission=ack)
        assert seen and barrier_code == 0 and not barrier_timed and b"ack=GEMINI-WIFI-NVRAM-CONSUME-v1" in barrier_raw
        timed_raw, timed_code, timed_out = MODULE.run_bounded(
            [sys.executable, "-c", "import time;time.sleep(2)"], b"",
            local_seconds=0.05, max_output=MODULE.MAX_OUTPUT)
        assert timed_out
        refused(lambda: MODULE.validate_process(timed_raw, timed_code, timed_out=True), "deadline")

    command = MODULE.ssh_command(Path("/repo"), BOOT)
    for required in ("BatchMode=yes", "IdentitiesOnly=yes", "IdentityAgent=none",
                     "StrictHostKeyChecking=yes", "UpdateHostKeys=no",
                     "GlobalKnownHostsFile=/dev/null", "-F", "/dev/null",
                     "gemini@192.168.1.50"):
        assert required in command
    assert any("a53-recovery-known_hosts" in item for item in command)
    remote = (HERE / "remote-collect.sh").read_text(encoding="utf-8")
    for forbidden in ("lib64", "lxc-attach", "sudo", "\nmount ", "/proc/mounts"):
        assert forbidden not in remote
    assert "lxc-info -n android -sH -pH" in remote
    print("live_nvram_identity_fixtures=pass cases=41")


if __name__ == "__main__":
    main()
