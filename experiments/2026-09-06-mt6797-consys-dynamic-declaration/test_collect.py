#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Hardware-free refusal fixtures for the dynamic declaration collector."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("dynamic_collect", HERE / "collect.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_output() -> bytes:
    return f"""release_start={MODULE.EXPECTED_RELEASE}
boot_id_start={MODULE.EXPECTED_BOOT_ID}
model_start={MODULE.EXPECTED_MODEL}
declaration_begin
root_address_cells_status=present
root_address_cells_bytes=4
root_address_cells_hex=00000002
root_size_cells_status=present
root_size_cells_bytes=4
root_size_cells_hex=00000002
reserved_address_cells_status=present
reserved_address_cells_bytes=4
reserved_address_cells_hex=00000002
reserved_size_cells_status=present
reserved_size_cells_bytes=4
reserved_size_cells_hex=00000002
reserved_ranges_status=present
reserved_ranges_bytes=0
reserved_ranges_hex=
node_reg_status=missing
node_size_status=present
node_size_bytes=8
node_size_hex=0000000000200000
node_alignment_status=missing
node_alloc_ranges_status=missing
node_no_map=yes
node_reusable=no
declaration_end
release_end={MODULE.EXPECTED_RELEASE}
boot_id_end={MODULE.EXPECTED_BOOT_ID}
model_end={MODULE.EXPECTED_MODEL}
""".encode()


def refused(call, fragment: str) -> None:
    try:
        call()
    except MODULE.CollectionError as error:
        assert fragment in str(error)
    else:
        raise AssertionError(f"expected refusal containing {fragment!r}")


def main() -> None:
    raw = valid_output()
    assert MODULE.accept_process_result(raw, 0)
    refused(lambda: MODULE.validate_output(raw.replace(
        MODULE.EXPECTED_RELEASE.encode(), b"wrong", 1)), "release_start")
    refused(lambda: MODULE.validate_output(raw.replace(
        f"boot_id_end={MODULE.EXPECTED_BOOT_ID}\n".encode(), b"")), "boot_id_end")
    refused(lambda: MODULE.validate_output(raw.replace(
        b"node_alignment_status=missing\n", b"")), "node_alignment_status")
    refused(lambda: MODULE.validate_output(raw.replace(
        b"node_size_bytes=8\n", b"node_size_bytes=7\n")), "byte/hex mismatch")
    refused(lambda: MODULE.validate_output(raw.replace(
        b"node_reg_status=missing\n", b"node_reg_status=bad\n")),
            "invalid property status")
    refused(lambda: MODULE.validate_output(raw + b"exact_node_status=missing\n"),
            "trailing structured")
    refused(lambda: MODULE.validate_output(raw + b"unexpected=value\n"),
            "trailing structured")
    refused(lambda: MODULE.accept_process_result(raw, 124), "exited 124")
    refused(lambda: MODULE.accept_process_result(raw, -1, timed_out=True),
            "deadline")
    assert MODULE.ssh_command().count("UpdateHostKeys=no") == 1
    refused(lambda: MODULE.run_bounded(
        [sys.executable, "-c", "import sys;sys.stdout.write('x'*4096)"], b"",
        local_seconds=2, max_output=1024), "configured maximum")
    refused(lambda: MODULE.run_bounded(
        [sys.executable, "-c", "import time;time.sleep(2)"], b"",
        local_seconds=0.05, max_output=1024), "deadline")
    assert MODULE.remote_command().startswith("exec timeout -s KILL 10 sh -s -- ")
    print("dynamic_declaration_collector_fixtures=pass cases=12")


if __name__ == "__main__":
    main()
