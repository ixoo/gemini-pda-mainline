#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Hardware-free refusal fixtures for the bounded Gemian collector."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("consys_collect", HERE / "collect.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_output() -> bytes:
    return (f"""release_start={MODULE.EXPECTED_RELEASE}
boot_id_start={MODULE.EXPECTED_BOOT_ID}
model_start={MODULE.EXPECTED_MODEL}
reserved_context_begin
reserved_address_cells_status=present
reserved_address_cells_bytes=4
reserved_address_cells_hex=00000002
reserved_context_end
reserved_nodes_begin
reserved_nodes_end
platform_owners_begin
platform_owners_end
iomem_begin
iomem_status=present
iomem_end
release_end={MODULE.EXPECTED_RELEASE}
boot_id_end={MODULE.EXPECTED_BOOT_ID}
model_end={MODULE.EXPECTED_MODEL}
""").encode()


def refused(call, fragment: str) -> None:
    try:
        call()
    except MODULE.CollectionError as error:
        assert fragment in str(error), (fragment, str(error))
    else:
        raise AssertionError(f"expected refusal containing {fragment!r}")


def main() -> None:
    raw = valid_output()
    assert MODULE.accept_process_result(raw, 0).endswith(
        f"model_end={MODULE.EXPECTED_MODEL}\n")

    refused(lambda: MODULE.validate_output(
        raw.replace(MODULE.EXPECTED_RELEASE.encode(), b"wrong", 1)), "release_start")
    refused(lambda: MODULE.validate_output(
        raw.replace(MODULE.EXPECTED_BOOT_ID.encode(), b"wrong", 1)), "boot_id_start")
    refused(lambda: MODULE.validate_output(
        raw.replace(MODULE.EXPECTED_MODEL.encode(), b"wrong", 1)), "model_start")
    refused(lambda: MODULE.validate_output(raw.replace(
        f"boot_id_end={MODULE.EXPECTED_BOOT_ID}\n".encode(), b"")), "boot_id_end")
    refused(lambda: MODULE.validate_output(
        raw.replace(b"reserved_nodes_end\n", b"")), "reserved_nodes_end")
    refused(lambda: MODULE.validate_output(
        raw + f"model_end={MODULE.EXPECTED_MODEL}\n".encode()), "model_end")
    refused(lambda: MODULE.validate_output(
        raw + b"x" * (MODULE.MAX_OUTPUT - len(raw) + 1)), "64 KiB")
    refused(lambda: MODULE.accept_process_result(raw, 124), "exited 124")
    refused(lambda: MODULE.accept_process_result(raw, -1, timed_out=True), "deadline")

    command = MODULE.remote_command()
    assert command.startswith("exec timeout 10 sh -s -- ")
    assert MODULE.EXPECTED_RELEASE in command
    assert MODULE.EXPECTED_BOOT_ID in command
    assert MODULE.EXPECTED_MODEL in command
    ssh_command = MODULE.ssh_command()
    assert ssh_command.count("UpdateHostKeys=no") == 1
    assert ssh_command[-2:] == ["gemini", command]
    print("consys_passive_collector_fixtures=pass cases=9")


if __name__ == "__main__":
    main()
