#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify frozen sanitized v3 evidence; never run the parser or access private inputs.

Self-tests mutate evidence in memory. They test verifier refusals, not injected
runtime failures or a second package/image execution.
"""
import argparse
import ast
from collections import Counter
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parent
RAW_HASHES = json.loads("{\"inputs.json\":\"c5dffb7323e7eb25626704d3310565b1ca9252e0dd9f349eff66ed04fc3d4e31\",\"loader.json\":\"54763f55f63b12fd47e32931c13f6fe7f617d807a161da9f77e223abc4f43557\",\"method.json\":\"9b4ce1dfe5773c2264ebe302ea17b62fb502793589e05dc6243ac753adbdc51c\",\"analysis.json\":\"e1ebec2e0080d70fd8e5e0d59801d20c874821f25f99c3a4e62d5effd35652ea\",\"intervals.json\":\"e44de0d978edbaaccc5f5d05afc5fc913bd691c2ab56e2e03c02edbc23ebef0c\"}")
CANONICAL_HASHES = json.loads("{\"inputs.json\":\"f0017ed3b4edcdcda3384569a7d2a26458b5a76e88468f087a79ea501152a324\",\"loader.json\":\"d7966528a1e7b42d2eefdc2328c7e9abf404e867b12dcc4c1c71362c1e47cf72\",\"method.json\":\"2dd07763bb368d30549928e0be96cd499fd899159d06cb3bb440c79e45f7dbad\",\"analysis.json\":\"36596d20152835613adb3afec4f76cf6b81bddec11a6710155e7a58a1988d192\",\"intervals.json\":\"720e44a20d81919b97bdf523c9d2a4416e2722ea998c61979099d31b1a6bf84f\"}")
SOURCE_EXPECTATIONS = json.loads("[{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121753597608\",\"name\":\"vmlinux_to_elf\",\"path\":\"vmlinux_to_elf/__init__.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\",\"size\":0},{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121753597608\",\"name\":\"vmlinux_to_elf.core.architecture_detecter\",\"path\":\"vmlinux_to_elf/core/architecture_detecter.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"3eb32a79485120c4eef6a59212bcddc286b43f7d31091ef9240c94579fb36563\",\"size\":9159},{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121753597608\",\"name\":\"vmlinux_to_elf.core.auto_unpack\",\"path\":\"vmlinux_to_elf/core/auto_unpack.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"1e1d9c55c6ce3f2af954c1688c04e10182334c2a1b63ca02643d9f35d87d5995\",\"size\":19337},{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121753597608\",\"name\":\"vmlinux_to_elf.core.kallsyms\",\"path\":\"vmlinux_to_elf/core/kallsyms.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"2bff550d9486e90782a4320cec7bc26b249ead5048f58839eec6578b52c06c2d\",\"size\":66664},{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121858600379\",\"name\":\"vmlinux_to_elf.utils\",\"path\":\"vmlinux_to_elf/utils/__init__.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\",\"size\":0},{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121858600379\",\"name\":\"vmlinux_to_elf.utils.elf\",\"path\":\"vmlinux_to_elf/utils/elf.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"f974b1189155d2cea4773d378990e1b20be866f27719be0593fef3110c56891d\",\"size\":41704},{\"exec_count\":1,\"loader\":\"ForcedSourceLoader\",\"mode\":436,\"mtime_ns\":\"1785068121859600405\",\"name\":\"vmlinux_to_elf.utils.pretty_print\",\"path\":\"vmlinux_to_elf/utils/pretty_print.py\",\"record_sha256\":true,\"record_size\":true,\"sha256\":\"0c043bf20f7fa2d642856465fad2dd473d44fd770d7b0339febcd9b716acc873\",\"size\":3598}]")
TARGETS = json.loads("[\"do_connectivity_driver_init\",\"do_wlan_drv_init\",\"mtk_wcn_wlan_gen3_init\",\"mtk_wcn_wlan_gen3_exit\"]")
DB_NAMES = json.loads("[\"KernelVersion\",\"KernelRelevantFile\",\"EMachineValue\",\"ArchitectureEMachineLink\",\"KnownArchitecture\",\"DebianRelease\"]")
ARCHITECTURE = json.loads("{\"architecture\":{\"type\":\"ArchitectureName\",\"member\":\"aarch64\",\"value\":11},\"elf_machine\":{\"type\":\"int\",\"value\":183},\"is_64_bits\":{\"type\":\"bool\",\"value\":true},\"is_big_endian\":{\"type\":\"bool\",\"value\":false}}")
GUARDS = json.loads("[\"bytecode_open\",\"database_path\",\"detector\",\"filesystem_write\",\"finder_fallback\",\"network\",\"shell\",\"subprocess\",\"unexpected_directory_discovery\",\"unexpected_import\",\"unexpected_read\",\"unrecorded_package_code\"]")
DEPENDENCY_DIRS = {
    "excluded_original": "2026-09-06-vmlinux-to-elf-symbol-provenance",
    "excluded_architecture_bypass_v2": "2026-09-06-vmlinux-to-elf-symbol-provenance-v2",
    "excluded_database_v1": "2026-09-06-vmlinux-to-elf-kernel-db-provenance",
    "accepted_database_v2": "2026-09-06-vmlinux-to-elf-kernel-db-provenance-v2",
    "zero_size_dependency": "2026-09-06-mt6797-wlan-final-linkage-teardown-attribution",
}
TRUE_POSTCONDITIONS = (
    "cache_empty", "core_metadata_unchanged", "detector_restored",
    "inherited_methods_unchanged", "source_snapshots_unchanged")
FALSE_AUTHORITIES = (
    "build", "database_directory_enumerated_or_statted", "device_action",
    "global_external_file_absence_claimed", "instruction_analysis",
    "private_content_before_method_freeze")

class Invalid(ValueError):
    pass

def require(value, reason):
    if not value:
        raise Invalid(reason)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def same(actual, expected, reason):
    require(canonical(actual) == canonical(expected), reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result

def forbidden_constant(value):
    raise Invalid("nonfinite JSON constant")

def utc(value):
    result = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset() == datetime.timedelta(0), "timestamp timezone")
    return result

def address(value):
    require(isinstance(value, str) and re.fullmatch(r"0x[0-9a-f]{16}", value), "tuple address format")
    return int(value, 16)

def load_records():
    records = {}
    for name, expected in RAW_HASHES.items():
        data = (BASE / name).read_bytes()
        require(sha(data) == expected, "frozen file identity: " + name)
        records[name] = json.loads(data, object_pairs_hook=unique_object,
                                  parse_constant=forbidden_constant)
    require(sha((BASE / "WORK_ITEM.md").read_bytes()) == records["inputs.json"]["contract_sha256"], "contract identity")
    require(sha((BASE / "AMENDMENT.md").read_bytes()) == records["analysis.json"]["amendment_sha256"], "amendment identity")
    count = 0
    for group, directory in DEPENDENCY_DIRS.items():
        for name, expected in records["inputs.json"][group].items():
            # Identity-only access: no predecessor JSON is parsed or reused.
            data = (BASE.parent / directory / name).read_bytes()
            require(sha(data) == expected, "dependency identity: " + group + "/" + name)
            count += 1
    require(count == 20, "dependency inventory")
    return records

def validate(records, final_identity=True):
    inp, loader, method, analysis, intervals = (
        records[n + ".json"] for n in ("inputs", "loader", "method", "analysis", "intervals"))
    same(inp["targets"], TARGETS, "identity targets")
    same(inp["database_import_names"], DB_NAMES, "stub names")
    require(sha(canonical(inp).encode()) == CANONICAL_HASHES["inputs.json"], "input identity")
    runtime = loader["runtime_config"]
    audit = analysis["runtime_audit"]
    same(runtime["tool"], inp["tool"], "tool identity")
    same(runtime["kernel"], inp["kernel"], "kernel identity")
    same(audit["kernel_hashes_verified"], inp["kernel"], "runtime kernel identity")
    same(runtime["targets"], TARGETS, "loader targets")
    same(runtime["database_import_names"], DB_NAMES, "stub import namespace")
    for name in ("runner", "collector"):
        source = loader[name + "_source"]
        require(sha(source.encode()) == loader[name + "_sha256"], "loader source hash")
        require(not any(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(source))), "inactive assert check")
    require(sha(method["subclass_source"].encode()) == method["subclass_sha256"], "method source hash")
    same(method["subclass_source"], runtime["subclass_source"], "method source consistency")
    same(method["subclass_sha256"], runtime["subclass_sha256"], "method hash consistency")
    same(method["architecture_fields"], ARCHITECTURE, "method architecture state")
    same(method["overrides"], ["guess_architecture", "extract_db_information"], "method override set")
    tree = ast.parse(method["subclass_source"])
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.ClassDef), "method subclass shape")
    subclass = tree.body[0]
    same([n.name for n in subclass.body if isinstance(n, ast.FunctionDef)], method["overrides"], "method extra overrides")
    same([ast.unparse(n) for n in subclass.bases], ["KallsymsFinder"], "method base")
    same(runtime["method_names"], method["inherited_method_names"], "method inherited inventory")
    require(len(method["architecture_references"]) == 24, "method state inventory")
    for key in ("parser_state_writes", "returns", "parser_method_calls", "downstream_parser_references"):
        same(method["database_proof"][key], 0, "database semantic independence")
    same(method["database_proof"]["self_reads"], ["version_number", "elf_machine"], "database self inputs")
    policy = loader["source_policy"]
    same(policy["source_limit"], 16, "loader source cap")
    same(policy["executable_sources"], 7, "loader source count")
    same(policy["static_inspected_sources"], 9, "loader inspection count")
    for key in ("ordinary_get_code", "bytecode", "namespace_loader"):
        same(policy[key], False, "loader forbidden source route")
    for key in ("terminal_prefix_finder", "record_digest_and_size_required", "recursive_code_identity_tracking"):
        same(policy[key], True, "loader provenance predicate")
    source_expected = {x["name"]: x for x in SOURCE_EXPECTATIONS}
    same(audit["source_inventory"], SOURCE_EXPECTATIONS, "loader source identity/snapshot")
    require(len({x["path"] for x in runtime["source_inventory"]}) == 7, "loader duplicate origin")
    for item in runtime["source_inventory"]:
        expected = source_expected[item["name"]]
        same(item, {key: expected[key] for key in ("name", "path", "sha256", "size")}, "loader RECORD whitelist")
    same(audit["source_code_objects"], 160, "loader code provenance count")
    core = loader["synthetic_core"]
    same(core["name"], "vmlinux_to_elf.core", "core name")
    same(core["package"], core["name"], "core package")
    same(core["origin"], "synthetic-metadata-only", "core origin")
    same(core["loader"], None, "core loader")
    for key in ("has_file", "has_cached", "executes_code", "preexisting_module_or_descendants", "preexisting_top_binding"):
        same(core[key], False, "core forbidden state")
    same(core["path_type"], "tuple", "core mutable path")
    same(core["spec_locations_type"], "separate tuple", "core locations")
    same(core["path_entries"], 1, "core path count")
    same(core["allowed_added_attributes"], "exact loaded child-module identities only", "core child boundary")
    same(loader["dependency_policy"]["third_party"], [], "dependency semantic expansion")
    same(loader["dependency_policy"]["bootstrap_package_modules"], 0, "dependency preloaded package")
    same(loader["dependency_policy"]["dependency_source_inspection"], False, "dependency source expansion")
    same(sorted(audit["bootstrap_dependencies"]), sorted(runtime["parser_dependencies"]), "dependency inventory")
    for value in audit["bootstrap_dependencies"].values():
        same(value, {"kind": "stdlib", "version": "3.12.3"}, "dependency version")
    same(analysis["status"], "pass-pending-independent-review", "result status")
    same(audit["status"], "pass", "runtime status")
    same(audit["phase"], "complete", "runtime completion")
    same(audit["guard_counts"], {name: 0 for name in GUARDS}, "guard attempts")
    same(audit["stub_import_counts"], {name: (0 if name == "ArchitectureEMachineLink" else 1) for name in DB_NAMES}, "stub retrieval counts")
    same(audit["stub_operation_counts"], {name: 0 for name in DB_NAMES}, "sentinel operations")
    same(audit["bypass_counts"], {"architecture": 1, "metadata": 1}, "method bypass counts")
    same(audit["construction_count"], 1, "construction count")
    calls = audit["package_call_counts"]
    same(calls["vmlinux_to_elf.core.kallsyms:KallsymsFinder.__init__"], 1, "constructor call provenance")
    for item in SOURCE_EXPECTATIONS:
        same(calls[item["name"] + ":<module>"], 1, "module execution count")
    for name, count in calls.items():
        require(name.split(":", 1)[0] in source_expected, "unrecorded package code")
        require(type(count) is int and count > 0, "package call counter")
        require("ArchitectureDetector.guess" not in name, "detector call")
        require("KallsymsFinder.extract_db_information" not in name, "database method execution")
        require("KallsymsFinder.guess_architecture" not in name, "original guess execution")
        require("KallsymsFinder.print_symbols_debug" not in name, "whole-table output")
    for key in TRUE_POSTCONDITIONS:
        same(audit[key], True, "postcondition " + key)
    for key in FALSE_AUTHORITIES:
        same(audit[key], False, "authority " + key)
    same(audit["filesystem_claim_scope"], "guarded-process-only", "filesystem claim scope")
    fs = loader["filesystem_scope"]
    for key in ("database_directory_enumeration", "database_directory_stat", "global_external_package_or_database_file_absence_claim"):
        same(fs[key], False, "filesystem authority expansion")
    receipt = analysis["receipt"]
    same(receipt["returncode"], 0, "process status")
    same(receipt["cache_empty_after_process"], True, "collector cache")
    same(receipt["collector_private_output_writes"], 2, "collector output boundary")
    same(receipt["private_raw_stderr_size"], 0, "stderr evidence")
    for key in ("private_raw_stdout_sha256", "private_raw_stderr_sha256", "private_parser_log_sha256"):
        require(re.fullmatch("[0-9a-f]{64}", receipt[key]), "raw log identity format")
    freeze = analysis["pre_execution_freeze"]
    same(freeze["loader_json_sha256"], RAW_HASHES["loader.json"], "pre-execution loader freeze")
    same(freeze["method_json_sha256"], RAW_HASHES["method.json"], "pre-execution method freeze")
    for key in ("runner", "collector"):
        same(freeze[key + "_sha256"], loader[key + "_sha256"], "pre-execution executable hash")
    same(freeze["subclass_sha256"], method["subclass_sha256"], "pre-execution subclass hash")
    same(freeze["utc"], loader["pre_private_content_freeze_utc"], "freeze chronology")
    same(freeze["utc"], method["pre_private_content_freeze_utc"], "method chronology")
    require(utc(freeze["utc"]) < utc(receipt["started_utc"]) <= utc(receipt["finished_utc"]) < utc(analysis["result_json_frozen_utc"]), "execution chronology")
    same(analysis["execution_head"], loader["execution_head"], "dispatch identity")
    same(loader["lineage"]["authorized_successor"], loader["execution_head"], "successor identity")
    same(loader["lineage"]["successor_delta"], [".github/workflows/repository-checks.yml"], "successor scope")
    same(loader["lineage"]["v3_and_dependencies_unchanged"], True, "successor content drift")
    proof = analysis["postconditions_proved_by_passing_frozen_checks"]
    same(proof["mro"], ["FrozenNoDatabaseAArch64Finder", "KallsymsFinder", "object"], "method MRO")
    for key in ("constructor_identity", "all_base_function_and_code_identities", "exact_two_override_function_and_code_identities", "synthetic_core_spec_path_binding_and_children_unchanged"):
        same(proof[key], True, "method identity")
    same(proof["architecture"], {"enum_member": "ArchitectureName.aarch64", "enum_value": 11, "elf_machine": 183, "is_64_bits": True, "is_big_endian": False}, "final architecture")
    same(intervals["kernel_image_sha256"], inp["kernel"]["Image"], "interval image identity")
    same(intervals["retained_elf_sha256"], inp["kernel"]["vmlinux"], "interval ELF identity")
    same(audit["symbol_count"], 64417, "tuple count")
    same(intervals["symbol_count"], audit["symbol_count"], "interval tuple count")
    same(audit["tuple_order"], "monotonic-nondecreasing", "tuple ordering")
    same(intervals["tuple_order"], audit["tuple_order"], "interval ordering")
    same([x["target"]["name"] for x in intervals["neighborhoods"]], TARGETS, "target inventory")
    for row in intervals["neighborhoods"]:
        target, previous, following = (row[k] for k in ("target", "previous_distinct", "next_distinct"))
        start, before, end = (address(x["address"]) for x in (target, previous, following))
        same(row["exact_name_count"], 1, "target uniqueness")
        require(before < start < end, "neighbor boundary")
        aliases = row["aliases"]
        require(len(aliases) <= 4, "alias overflow")
        seen = {target["name"]}
        for alias in aliases:
            require(alias["name"] not in seen, "alias duplicate/name")
            seen.add(alias["name"])
            require(address(alias["address"]) == start, "alias address")
            require(alias["kallsyms_type"] in ("T", "t", "W"), "alias type")
        kind = target["kallsyms_type"]
        require(kind in ("T", "t", "W"), "target type")
        same(row["strength"], {"T": "ordinary-global", "t": "ordinary-local", "W": "weak-defined"}[kind], "strength transformation")
        elf = row["retained_elf"]
        require(address(elf["address"]) == start, "ELF start equality")
        same(elf["size"], 0, "ELF zero-size evidence")
        same(elf["type"], 2, "ELF text type")
        same(elf["binding"], {"T": 1, "t": 0, "W": 2}[kind], "ELF binding transformation")
        region = row["region"]
        same(region["index"], elf["section_index"], "region identity")
        same(region["type"], 1, "region file backing")
        require(type(region["flags"]) is int and region["flags"] & 4, "region executable")
        require(address(region["start"]) <= start < end < address(region["start"]) + region["size"], "cross-region boundary")
        envelope = row["interval"]
        same(envelope["start"], target["address"], "interval start")
        same(envelope["end_exclusive"], following["address"], "interval next-symbol end")
        same(envelope["size"], end - start, "interval size")
        same(envelope["classification"], "conservative-inspection-envelope", "interval classification")
        same(envelope["exact_end"], False, "exact-end promotion")
    for key in ("exact_function_ends", "instruction_semantics"):
        same(intervals[key], False, "interval authority")
    acceptance = analysis["acceptance"]
    for key in ("exact_function_ends", "instruction_or_control_flow_analysis", "runtime_or_teardown_safety"):
        same(acceptance[key], False, "authority promotion")
    same(acceptance["later_instruction_contract_may_use_envelopes"], True, "later conditional admission")
    if final_identity:
        for name, data in records.items():
            require(sha(canonical(data).encode()) == CANONICAL_HASHES[name], "frozen document identity: " + name)

def mutate(records, path, value):
    changed = copy.deepcopy(records)
    cursor = changed
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return changed

def self_test(records):
    cases = []
    def add(category, path, value):
        cases.append((category, path, value))
    for group in ("kernel", "tool", *DEPENDENCY_DIRS):
        for key in records["inputs.json"][group]:
            add("identity", ["inputs.json", group, key], "drift")
    for name in ("runner", "collector"):
        add("loader", ["loader.json", name + "_source"], records["loader.json"][name + "_source"] + "\n# drift\n")
        add("loader", ["loader.json", name + "_sha256"], "0" * 64)
    for key in ("ordinary_get_code", "bytecode", "namespace_loader"):
        add("loader", ["loader.json", "source_policy", key], True)
    for key in ("terminal_prefix_finder", "record_digest_and_size_required", "recursive_code_identity_tracking"):
        add("loader", ["loader.json", "source_policy", key], False)
    add("loader", ["loader.json", "source_policy", "source_limit"], 17)
    add("loader", ["analysis.json", "runtime_audit", "source_code_objects"], 161)
    for index in range(7):
        for key, value in (("sha256", "0" * 64), ("size", -1), ("mode", 0), ("mtime_ns", "1"), ("loader", "SourceFileLoader"), ("record_sha256", False), ("record_size", False), ("exec_count", 2)):
            add("loader", ["analysis.json", "runtime_audit", "source_inventory", index, key], value)
    for key, value in (("name", "other"), ("package", "other"), ("origin", "namespace"), ("loader", "NamespaceLoader"), ("has_file", True), ("has_cached", True), ("executes_code", True), ("preexisting_module_or_descendants", True), ("preexisting_top_binding", True), ("path_type", "list"), ("spec_locations_type", "shared tuple"), ("path_entries", 2), ("allowed_added_attributes", "any")):
        add("synthetic-parent", ["loader.json", "synthetic_core", key], value)
    add("stub", ["loader.json", "runtime_config", "database_import_names"], DB_NAMES[:-1])
    for name in DB_NAMES:
        add("stub", ["analysis.json", "runtime_audit", "stub_import_counts", name], 99)
        add("sentinel", ["analysis.json", "runtime_audit", "stub_operation_counts", name], 1)
    for name in GUARDS:
        add("guard", ["analysis.json", "runtime_audit", "guard_counts", name], 1)
    add("dependency", ["loader.json", "dependency_policy", "third_party"], ["unadmitted"])
    add("dependency", ["loader.json", "dependency_policy", "dependency_source_inspection"], True)
    add("dependency", ["loader.json", "dependency_policy", "bootstrap_package_modules"], 1)
    add("method", ["method.json", "subclass_source"], records["method.json"]["subclass_source"] + "\n# drift\n")
    add("method", ["method.json", "overrides"], ["guess_architecture", "extract_db_information", "__init__"])
    for key in ARCHITECTURE:
        add("method", ["method.json", "architecture_fields", key, "value"], None)
    for key in ("parser_state_writes", "returns", "parser_method_calls", "downstream_parser_references"):
        add("method", ["method.json", "database_proof", key], 1)
    for key in ("architecture", "metadata"):
        add("method", ["analysis.json", "runtime_audit", "bypass_counts", key], 2)
    add("method", ["analysis.json", "runtime_audit", "construction_count"], 2)
    add("method", ["analysis.json", "postconditions_proved_by_passing_frozen_checks", "mro"], ["other", "object"])
    for key in TRUE_POSTCONDITIONS:
        add("method", ["analysis.json", "runtime_audit", key], False)
    for index, row in enumerate(records["intervals.json"]["neighborhoods"]):
        base = ["intervals.json", "neighborhoods", index]
        add("target", base + ["target", "name"], "other")
        add("target", base + ["exact_name_count"], 2)
        add("target", base + ["retained_elf", "address"], row["next_distinct"]["address"])
        add("target", base + ["retained_elf", "size"], 4)
        add("target", base + ["target", "kallsyms_type"], "D")
        add("alias", base + ["aliases"], [{"name": "alias" + str(i), "address": row["target"]["address"], "kallsyms_type": "T"} for i in range(5)])
        add("alias", base + ["aliases"], [{"name": "alias", "address": row["next_distinct"]["address"], "kallsyms_type": "T"}])
        add("alias", base + ["aliases"], [{"name": "alias", "address": row["target"]["address"], "kallsyms_type": "D"}])
        add("alias", base + ["aliases"], [{"name": row["target"]["name"], "address": row["target"]["address"], "kallsyms_type": "T"}])
        add("boundary", base + ["next_distinct", "address"], row["target"]["address"])
        add("boundary", base + ["previous_distinct", "address"], row["target"]["address"])
        add("boundary", base + ["region", "size"], 1)
        add("boundary", base + ["region", "flags"], 0)
        add("boundary", base + ["region", "index"], 9)
        add("strength", base + ["strength"], "weak-defined")
        add("strength", base + ["retained_elf", "binding"], 2)
        add("interval", base + ["interval", "size"], -1)
        add("interval", base + ["interval", "end_exclusive"], row["target"]["address"])
        add("interval", base + ["interval", "classification"], "exact-function")
        add("interval", base + ["interval", "exact_end"], True)
    add("boundary", ["analysis.json", "runtime_audit", "tuple_order"], "unsorted")
    add("boundary", ["analysis.json", "runtime_audit", "symbol_count"], 0)
    for key in FALSE_AUTHORITIES:
        add("authority", ["analysis.json", "runtime_audit", key], True)
    for key in ("database_directory_enumeration", "database_directory_stat", "global_external_package_or_database_file_absence_claim"):
        add("authority", ["loader.json", "filesystem_scope", key], True)
    for key in ("exact_function_ends", "instruction_or_control_flow_analysis", "runtime_or_teardown_safety"):
        add("authority", ["analysis.json", "acceptance", key], True)
    for key in ("exact_function_ends", "instruction_semantics"):
        add("authority", ["intervals.json", key], True)
    add("authority", ["analysis.json", "runtime_audit", "filesystem_claim_scope"], "global")
    add("chronology", ["analysis.json", "pre_execution_freeze", "utc"], records["analysis.json"]["result_json_frozen_utc"])
    add("identity", ["analysis.json", "receipt", "private_raw_stdout_sha256"], "0" * 64)
    rejected = Counter()
    reasons = Counter()
    for category, path, value in cases:
        try:
            validate(mutate(records, path, value))
        except (Invalid, KeyError, TypeError, ValueError) as error:
            rejected[category] += 1
            reasons[str(error).split(":", 1)[0]] += 1
        else:
            raise Invalid("mutation accepted: " + category + "/" + "/".join(map(str, path)))
    return {"mutation_rejections": len(cases), "categories": dict(sorted(rejected.items())),
            "rejection_reasons": dict(sorted(reasons.items()))}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    records = load_records()
    validate(records)
    result = {"status": "pass", "optimized": sys.flags.optimize,
              "frozen_json_files": len(records), "dependency_hash_checks": 20,
              "private_input_accesses": 0, "parser_constructions": 0, "hardware_tests": 0}
    if args.self_test:
        result.update(self_test(records))
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    try:
        main()
    except (Invalid, KeyError, TypeError, ValueError, OSError) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        raise SystemExit(1)
