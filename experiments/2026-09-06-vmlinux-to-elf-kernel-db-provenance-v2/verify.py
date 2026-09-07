#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate the frozen source-only audit, without package/database access."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PINS = {
    "inputs.json": "bb64c330fca2c2b3d48742d7897944d64a0f547d76d95ebc3e823f59411a914e",
    "inventory.json": "1f8da3d3ecb20a5c36e8a7deade2b12adeb4994793e2c46ce6daf9bf430862a3",
    "analysis.json": "deb75e89391a4e8c84e16d517975cea6dea3e73963c4e4e4c7be20a5fd2e44fa",
}
VERIFIED = (
    ("vmlinux_to_elf/kernel_db/README.md", "documentation"),
    ("vmlinux_to_elf/kernel_db/database.py", "python-source"),
    ("vmlinux_to_elf/kernel_db/database.sqlite3", "sqlite-data"),
)
CACHE = "vmlinux_to_elf/kernel_db/__pycache__/database.cpython-312.pyc"


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def validate(packet: dict, frozen: dict) -> None:
    inp, inv, audit = (packet[name] for name in PINS)
    require(inp == frozen["inputs.json"], "input/RECORD/source identity drift")
    require(inv["record_entries"] == 4 and len(inv["verified_files"]) == 3,
            "entry count drift")
    require(inv["excluded_files"] == [{"path": CACHE, "digest_present": False,
            "size_present": False, "content_read_hashed_or_loaded": False}],
            "excluded cache contract changed")
    for item, (path, role) in zip(inv["verified_files"], VERIFIED, strict=True):
        rel = PurePosixPath(item["path"])
        require(not rel.is_absolute() and ".." not in rel.parts and
                item["path"] == path and item["role"] == role,
                "source/data path or role changed")
        require(item["size"] > 0 and len(item["sha256"]) == 64,
                "file identity malformed")
    for key in ("all_paths_regular_nonsymlink_contained",
                "all_verified_record_digests_sizes_match",
                "verified_before_after_hash_size_mode_mtime_equal",
                "distribution_file_names_unchanged"):
        require(inv[key] is True, "inventory/path/state refusal")
    require(inv["new_cache_journal_temp_files"] == 0, "file side effect")
    db = audit["sqlite"]
    require(db["header_valid"] is True and db["connections"] == 1 and
            db["uri_mode"] == "ro" and db["immutable"] is True and
            db["query_only"] == 1, "database inspection mode changed")
    require(len(db["traced_models"]) == 6 and db["row_values_published"] is False
            and db["package_orm_queries_executed"] == 0,
            "schema/query/publication boundary changed")
    require(db["before_after_files_equal"] is True and
            db["distribution_file_names_unchanged"] is True and
            db["new_cache_journal_temp_files"] == 0, "database side effect")
    require(audit["source_forcing"]["ordinary_cache_discovery_allowed"] is False
            and audit["source_forcing"]["proved_in_this_audit"] is False,
            "source use falsely inferred")
    for key in ("ordinary_package_import_readonly_proved",
                "current_package_import_admitted", "current_query_execution_admitted"):
        require(audit["verdict"][key] is False, "conditional verdict promoted")
    require(all(v is False for v in audit["authority"].values()), "authority expansion")
    require(audit["observed_network_or_subprocess_attempts"] == 0 and
            audit["raw_outputs_exported"] is False, "effect/privacy boundary")
    require("PRIVATE_CONTENT_SENTINEL" not in json.dumps(packet), "private content")
    require(packet == frozen, "frozen schema/source/query/evidence changed")


def main() -> int:
    frozen = {}
    for name, expected in PINS.items():
        raw = (HERE / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, "fixed digest drift")
        frozen[name] = json.loads(raw)
    validate(copy.deepcopy(frozen), frozen)
    mutations = []

    def change(file: str, path: tuple, value: object) -> None:
        candidate = copy.deepcopy(frozen)
        item = candidate[file]
        for key in path[:-1]:
            item = item[key]
        item[path[-1]] = value
        mutations.append(candidate)

    for key in ("analysis_parent", "dispatch_head", "distribution", "version",
                "python", "METADATA", "RECORD", "kallsyms_source"):
        change("inputs.json", (key,), "drift")
    for key in frozen["inputs.json"]["excluded_predecessor"]:
        change("inputs.json", ("excluded_predecessor", key), "drift")
    for count in (3, 5):
        change("inventory.json", ("record_entries",), count)
    change("inventory.json", ("excluded_files",), [])
    change("inventory.json", ("excluded_files",), frozen["inventory.json"]["excluded_files"] * 2)
    for key in ("digest_present", "size_present", "content_read_hashed_or_loaded"):
        change("inventory.json", ("excluded_files", 0, key), True)
    change("inventory.json", ("excluded_files", 0, "sha256"), "invented")
    for idx in range(3):
        for key, value in (("sha256", "0" * 64), ("size", 0), ("mode", "0o777"),
                           ("mtime_ns", 0), ("role", "sqlite-data")):
            if value != frozen["inventory.json"]["verified_files"][idx][key]:
                change("inventory.json", ("verified_files", idx, key), value)
    change("inventory.json", ("verified_files", 0, "path"), "../escape")
    change("inventory.json", ("verified_files",), frozen["inventory.json"]["verified_files"] * 2)
    for key in ("all_paths_regular_nonsymlink_contained", "all_verified_record_digests_sizes_match",
                "verified_before_after_hash_size_mode_mtime_equal", "distribution_file_names_unchanged"):
        change("inventory.json", (key,), False)
    change("inventory.json", ("new_cache_journal_temp_files",), 1)
    for key, value in (("header_valid", False), ("connections", 2), ("uri_mode", "rw"),
                       ("immutable", False), ("query_only", 0), ("row_values_published", True),
                       ("package_orm_queries_executed", 1), ("before_after_files_equal", False),
                       ("new_cache_journal_temp_files", 1), ("index_count", 0),
                       ("table_names", []), ("traced_models", {})):
        change("analysis.json", ("sqlite", key), value)
    for key in frozen["analysis.json"]["source_trace"]:
        change("analysis.json", ("source_trace", key), "invented")
    change("analysis.json", ("queries", 0, "selection"), "write query")
    change("analysis.json", ("source_forcing", "ordinary_cache_discovery_allowed"), True)
    change("analysis.json", ("source_forcing", "proved_in_this_audit"), True)
    change("analysis.json", ("source_forcing", "fail_closed_future_method"), [])
    change("analysis.json", ("future_guards",), [])
    for key in ("ordinary_package_import_readonly_proved", "current_package_import_admitted",
                "current_query_execution_admitted"):
        change("analysis.json", ("verdict", key), True)
    for key in frozen["analysis.json"]["authority"]:
        change("analysis.json", ("authority", key), True)
    change("analysis.json", ("observed_network_or_subprocess_attempts",), 1)
    change("analysis.json", ("raw_outputs_exported",), True)
    change("analysis.json", ("private_content",), "PRIVATE_CONTENT_SENTINEL")
    change("analysis.json", ("mutable_expected_digest",), "0" * 64)
    for candidate in mutations:
        try:
            validate(candidate, frozen)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("mutation accepted")
    print(f"database provenance PASS; mutations={len(mutations)}; admission=conditional-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
