#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the frozen V10 refusal using public records only; never execute inputs."""
import copy
import datetime
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED_BINDING = {"dispatch_commit": "f1fef5e6bb83d2a2e85b33f9a97e9256b8b11a55", "dispatch_inputs_sha256": "56efd71170f662acdcef0be79ad1fd39c7cc9159a929976535c3684aec35d842", "construction_dispatch_commit": "342438085bef1feb081b62961b3d4e8e1c7fb2fa", "construction_inputs_sha256": "c4f1f32781a6c0012a84fdbc01a331f5963c65a8de3d31d581530922199e4c91", "bootstrap_sha256": "4e599c07d3fad2aabc6982383dbbc92dc9796136f388263045e59593cfcc4d8c", "bootstrap_source_sha256": "bd42ce6c91e1733f2fd0e849fae43d090849453c89c4a6f302c714f04d1dd633", "method_sha256": "f85e00a2a2d0b64b9af7369be1ef6d564d5b28aa2dbd5d791f53f0dbd656ffe1", "method_source_sha256": "d461847e4195f8f2aa5613d1f5345c8fffe74accffb92ee5f07c732cd24518eb", "freeze_sha256": "ae6135ab45ffaf23c85af2df63bbd1ebc574d390e8362cabf1cd7d3db5a846fb", "amendment_26_sha256": "0811ed99093f8dff908fdb496abfab214cc00380fb68d5001ea359341c28a187", "accepted_v9_result_sha256": "334149f00090c18d6f51baf84d05d94844a15aece74da43aeb1282cf87b87fb3", "accepted_intervals_sha256": "e44de0d978edbaaccc5f5d05afc5fc913bd691c2ab56e2e03c02edbc23ebef0c", "private_elf_expected_sha256": "cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162"}
RESULT_HASHES = {
    "bootstrap-v10-result.json": "3e0caa5234b3bd1842e70cab0626929ea0ed044b59960fc03da84411c13fb193",
    "analysis.json": "7851369cee4966e0302ede5123da07c4e28f9e91b7bf14893984ed1d38293ff3",
    "edges.json": "d9df19be8b727d623f29edbef6fbddca13a15e03a49a7175eb47162e48868d45",
}
ROOT_FIELDS = ["schema_version", "status", "binding", "bootstrap_frozen_utc", "method_frozen_utc", "results_frozen_utc", "runs", "run_budget_consumed", "private_content_read", "analysis_accepted", "custody", "collector", "canonical_receipt_sha256", "receipt", "authority"]
RECEIPT_FIELDS = ["accepted_queue_identity_result_sha256", "accepted_queue_load_result_sha256", "accepted_tool_identity_sha256", "accepted_v9_result_sha256", "amendment_26_sha256", "analysis_accepted", "analysis_counts", "analysis_process_runs", "analysis_progress", "analysis_result", "asset_opens_by_phase", "binding", "callback_count", "callback_present", "completed_modules", "completed_utc", "construction_dispatch_commit", "construction_inputs_sha256", "engine_count", "entered_modules", "events", "first_failure", "map_counts", "mapping_checks", "method_counts", "method_metadata", "method_present", "method_state_checks", "mode", "module_budget", "package_inventory_counts", "page_reference", "page_value", "private_cleanup", "private_equality", "private_input_size", "private_reads", "profile_counts", "queue_audit", "queue_counts", "queue_event_sha256", "queue_identity", "queue_identity_reads_by_stage", "queue_import_restored", "queue_map_row_counts", "queue_search_presence", "queue_stage_outcomes", "queue_wrapper", "resource_counters", "resource_state", "restorations", "schema_version", "stage_outcomes", "started_utc", "status", "tool_identity"]
COLLECTOR_FIELDS = ["attempted", "child_completed_utc", "child_exited", "child_started_utc", "collector_completed_utc", "collector_started_utc", "directory_mode", "dispatch_commit", "exit_code", "logs", "method_sha256", "source_sha256", "timed_out", "timeout_seconds", "writer_broken_pipe", "writer_bytes", "writer_joined"]
ANALYSIS_FIELDS = ["schema_version", "status", "binding", "bootstrap_result_sha256", "results_frozen_utc", "first_failure", "private_input_verified", "private_reads", "parser_instances", "engine_instances", "callback_invocations", "mapping_status", "ranges", "range_hashes", "decoder_agreement", "traversals", "boundaries_proved", "accepted_semantics", "scope", "authority"]
EDGES_FIELDS = ["schema_version", "status", "binding", "bootstrap_result_sha256", "analysis_sha256", "results_frozen_utc", "source_records", "init_chain_edges", "exit_direct_callees", "traversal_complete", "candidate_scans", "negative_absence_proved", "reachable_call_proved", "teardown_join_proved", "authority"]
FIRST_FAILURE = {"analysis_phase": None, "analysis_target_index": None, "candidate_read_ordinal": None, "class": "validation-failure", "map_stage": None, "queue_stage": None, "stage": "initial-inventory"}
AUTHORITY = {"device": False, "runtime": False, "firmware": False, "radio": False, "network": False, "build": False, "hardware_support": False, "teardown_safety": False}
OUTER_STAGES = ["startup", "initial-inventory", "pre-entry-static", "pre-import-drift", "capstone-import", "capstone-closure", "resource-preload", "page-reference", "queue-preload", "pyelftools-import", "pyelftools-identity", "engine", "post-engine", "method-freeze", "pre-analysis-drift", "pre-analysis-maps", "private-read", "analysis-callback", "post-analysis-integrity", "post-analysis-maps", "named-restoration", "component-drift", "final-tree-drift", "final-maps", "final-stdlib-drift", "final-restoration", "final-counters"]
QUEUE_STAGES = ["lexical", "pre-lstat", "baseline-maps", "import-wrapper", "import-restoration", "import-audit", "module-object", "module-spec", "post-lstat", "post-maps", "mapping-delta", "final-counters"]
ZERO_RECEIPT_MAPS = {"analysis_counts": {"address_candidates": 0, "address_scans": 0, "address_words": 0, "basic_block_leaders": 0, "bl_candidates": 0, "bl_scans": 0, "bl_words": 0, "bytesio_closes": 0, "bytesio_instances": 0, "capstone_instructions": 0, "capstone_requests": 0, "elf_instances": 0, "memory_read_bytes": 0, "memory_reads": 0, "memory_seeks": 0, "memory_tells": 0, "py_get_section": 0, "py_num_sections": 0, "py_num_symbols": 0, "py_relocation_counts": 0, "py_relocation_iterators": 0, "py_relocation_kind_queries": 0, "py_relocations": 0, "py_symbol_iterators": 0, "py_symbols": 0, "raw_headers": 0, "raw_program_headers": 0, "raw_relocations": 0, "raw_section_headers": 0, "raw_symbols": 0, "raw_target_decodes": 0, "reachable_addresses": 0, "reachable_calls": 0, "relocation_candidates": 0, "relocation_scans": 0, "traversals": 0}, "method_counts": {"callback_completed": 0, "callback_constructions": 0, "compile": 0, "compile_audit": 0, "exec": 0, "exec_audit": 0, "json_loads": 0, "json_pair_hooks": 0, "pipe_close": 0, "pipe_fcntl": 0, "pipe_fstat": 0, "pipe_open_audit": 0, "pipe_read": 0, "private_close": 0, "private_component_lstat": 0, "private_final_lstat": 0, "private_fstat": 0, "private_hashes": 0, "private_open_audit": 0, "private_read": 0, "private_read_completed": 0}, "queue_counts": {"cached_requests": 0, "content_open": 0, "content_open_audit": 0, "content_read": 0, "fstat": 0, "lstat": 0, "refused_events": 0}, "queue_identity_reads_by_stage": {"component-drift": 0, "final": 0, "post-analysis": 0, "post-engine": 0, "post-pyelftools": 0, "pre-analysis": 0, "resource-c-call": 0}, "queue_wrapper": {"calls": 0, "delegations": 0, "rejections": 0}, "queue_audit": {"baseline_maps_open": 0, "candidate_open": 0, "discovery_import": 0, "dynamic_load": 0, "extension_import": 0, "import_rejected": 0, "mutation": 0, "network": 0, "other": 0, "other_open": 0, "post_maps_open": 0, "process": 0, "write": 0}, "profile_counts": {"install": 0, "rejected": 0, "restore": 0}, "resource_counters": {"cached_requests": 0, "create_module": 0, "exec_module": 0, "extension_audit": 0, "find_spec": 0, "function_attempts": 0, "function_exceptions": 0, "function_returns": 0}, "events": {"cache_write_attempts": 0, "native_requests": 0, "network_attempts": 0, "optional_requests": 0, "process_attempts": 0, "write_attempts": 0}, "asset_opens_by_phase": {"final-drift": 0, "initial-inventory": 0, "pre-analysis-drift": 0, "pre-import-drift": 0}}
STATIC_RECEIPT = {"accepted_queue_identity_result_sha256": "eac9d08935b88bb565d4bab87ed1d02699a79ac0f10bcc9198068a531ff66508", "accepted_queue_load_result_sha256": "155ddb7da5d3872c69393723a342a456a268fd6e819b51357543e20976534a21", "accepted_tool_identity_sha256": "4baaa1020f2d895a688c6675b5091aed77d63d3a9ad9103316c4dbb6e830b639", "accepted_v9_result_sha256": "334149f00090c18d6f51baf84d05d94844a15aece74da43aeb1282cf87b87fb3", "amendment_26_sha256": "0811ed99093f8dff908fdb496abfab214cc00380fb68d5001ea359341c28a187", "analysis_accepted": False, "analysis_process_runs": 1, "analysis_progress": {"phase": None, "target_index": None}, "analysis_result": None, "binding": None, "callback_count": 0, "callback_present": False, "completed_modules": 0, "construction_dispatch_commit": "342438085bef1feb081b62961b3d4e8e1c7fb2fa", "construction_inputs_sha256": "c4f1f32781a6c0012a84fdbc01a331f5963c65a8de3d31d581530922199e4c91", "engine_count": 0, "entered_modules": 0, "first_failure": {"analysis_phase": None, "analysis_target_index": None, "candidate_read_ordinal": None, "class": "validation-failure", "map_stage": None, "queue_stage": None, "stage": "initial-inventory"}, "map_counts": {"open": 1, "read": 1}, "mapping_checks": [{"nonexecuting_pseudo_rows": 14, "nonexecuting_rows_equal_to_baseline": True, "stage": "stdlib-baseline", "vdso_full_row_equal": True}], "method_metadata": None, "method_present": False, "method_state_checks": [{"callback_count": 0, "callback_present": False, "callback_state": "absent", "method_present": False, "mode": "analysis", "pipe_opens": 0, "private_opens": 0, "stage": "startup"}], "mode": "analysis", "module_budget": None, "package_inventory_counts": {}, "page_reference": None, "page_value": None, "private_cleanup": {"method_pipe": {"ok": None, "state": "not-applicable"}, "private_buffer": {"ok": True, "state": "attempted"}, "private_descriptor": {"ok": None, "state": "not-applicable"}}, "private_equality": {"final_buffer_sha256": False, "final_lstat": False, "initial_sha256": False, "post_callback_fstat": False, "post_read_fstat": False, "pre_open_fstat": False}, "private_input_size": None, "private_reads": 0, "queue_event_sha256": "1f44854434c4d88a28f07834aff0629e5de462ee8cbbb3a6a6d3cd9245e56cf1", "queue_identity": None, "queue_import_restored": False, "queue_map_row_counts": {"baseline": None, "post": None}, "queue_search_presence": [], "resource_state": "none", "restorations": {"finder": {"ok": True, "state": "attempted"}, "import": {"ok": True, "state": "attempted"}, "native": {"ok": None, "state": "not-applicable"}, "path": {"ok": True, "state": "attempted"}, "profile": {"ok": True, "state": "attempted"}, "resource_create": {"ok": None, "state": "not-applicable"}, "resource_exec": {"ok": None, "state": "not-applicable"}}, "schema_version": 10, "status": "refused", "tool_identity": None}
FAMILIES = (
    "identities-links", "chronology", "parser-engine-callback-private-counters",
    "map-queue-resource-budgets", "ranges-hashes", "decoder-agreement",
    "traversal-refusal-boundary", "edge-target-reachability",
    "candidate-count-class-completion", "cleanup", "authority",
)
CASE_COUNTS = {name: 0 for name in FAMILIES}

def need(value, label):
    if not value:
        raise ValueError(label)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii"))

def exact(value, expected, label):
    need(type(value) is type(expected), label + ":type")
    if isinstance(expected, dict):
        need(set(value) == set(expected), label + ":fields")
        for key, expected_child in expected.items():
            exact(value[key], expected_child, label + "/" + key)
    elif isinstance(expected, list):
        need(len(value) == len(expected), label + ":length")
        for index, expected_child in enumerate(expected):
            exact(value[index], expected_child, label + "/" + str(index))
    else:
        need(value == expected, label + ":value")

def fields(value, names, label):
    need(type(value) is dict and set(value) == set(names), label)

def stamp(value):
    need(type(value) is str, "timestamp type")
    result = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(result.tzinfo is not None and result.utcoffset().total_seconds() == 0,
         "timestamp UTC")
    return result

def verify(records):
    b, a, e = records
    fields(b, ROOT_FIELDS, "bootstrap result fields")
    fields(a, ANALYSIS_FIELDS, "analysis fields")
    fields(e, EDGES_FIELDS, "edges fields")
    for item in records:
        exact(item["schema_version"], 10, "schema")
        exact(item["binding"], EXPECTED_BINDING, "binding")
        exact(item["authority"], AUTHORITY, "authority")
    exact(b["status"], "refused", "bootstrap status")
    exact(b["runs"], 1, "one consumed run")
    exact(b["run_budget_consumed"], True, "consumed budget")
    exact(b["private_content_read"], False, "no private content")
    exact(b["analysis_accepted"], False, "no analysis")
    exact(b["custody"], {"custodian": "/root/runtime_identity_specialist",
          "child_exited": True, "re_shell_exited": True, "released": True,
          "released_before_results_freeze": True}, "custody")
    c = b["collector"]
    fields(c, COLLECTOR_FIELDS, "collector fields")
    for key, val in {
        "attempted": True, "child_exited": True, "directory_mode": "0o700",
        "dispatch_commit": EXPECTED_BINDING["dispatch_commit"], "exit_code": 2,
        "method_sha256": EXPECTED_BINDING["method_sha256"],
        "source_sha256": EXPECTED_BINDING["bootstrap_source_sha256"],
        "timed_out": False, "timeout_seconds": 180, "writer_broken_pipe": True,
        "writer_bytes": 65536, "writer_joined": True,
    }.items():
        exact(c[key], val, "collector/" + key)
    fields(c["logs"], ("stdout.json", "stderr.log"), "two logs")
    for entry in c["logs"].values():
        fields(entry, ("sha256", "size", "mode"), "log fields")
        exact(entry["mode"], "0o600", "log mode")
        need(type(entry["sha256"]) is str and
             re.fullmatch("[0-9a-f]{64}", entry["sha256"]) is not None, "log hash")
        need(type(entry["size"]) is int and entry["size"] >= 0, "log size")
    exact(c["logs"]["stderr.log"], {"mode": "0o600", "size": 0,
          "sha256": sha(b"")}, "empty stderr")
    r = b["receipt"]
    fields(r, RECEIPT_FIELDS, "receipt fields")
    for key, expected in STATIC_RECEIPT.items():
        exact(r[key], expected, "receipt/" + key)
    for key, expected in ZERO_RECEIPT_MAPS.items():
        exact(r[key], expected, "zero operation map/" + key)
    exact(r["stage_outcomes"], [
        {"stage": name, "outcome": "passed" if index == 0 else
         "refused" if index == 1 else "not-evaluated"}
        for index, name in enumerate(OUTER_STAGES)], "first refusal stages")
    exact(r["queue_stage_outcomes"], [
        {"stage": name, "outcome": "not-evaluated"} for name in QUEUE_STAGES],
        "no queue stages")
    exact(b["canonical_receipt_sha256"], canonical(r), "canonical receipt")
    raw = (json.dumps({"canonical_receipt_sha256": canonical(r), "receipt": r},
                      sort_keys=True) + "\n").encode("ascii")
    exact(c["logs"]["stdout.json"]["sha256"], sha(raw), "raw stdout hash")
    exact(c["logs"]["stdout.json"]["size"], len(raw), "raw stdout size")
    exact(b["bootstrap_frozen_utc"], "2026-09-07T09:07:05.938401Z", "bootstrap freeze")
    exact(b["method_frozen_utc"], "2026-09-07T09:10:03.722181Z", "method freeze")
    times = [b["bootstrap_frozen_utc"], b["method_frozen_utc"],
             c["collector_started_utc"], c["child_started_utc"],
             r["started_utc"], r["completed_utc"], c["child_completed_utc"],
             c["collector_completed_utc"], b["results_frozen_utc"]]
    parsed = [stamp(item) for item in times]
    need(all(left <= right for left, right in zip(parsed, parsed[1:])),
         "source-first result chronology")
    need(parsed[0] < parsed[1] < parsed[2] and parsed[-2] < parsed[-1],
         "strict freeze boundaries")
    for item in (a, e):
        exact(item["status"], "not-evaluated-after-bootstrap-refusal", "not evaluated")
        exact(item["bootstrap_result_sha256"],
              RESULT_HASHES["bootstrap-v10-result.json"], "result link")
        exact(item["results_frozen_utc"], b["results_frozen_utc"], "freeze linkage")
    exact(a["first_failure"], FIRST_FAILURE, "analysis refusal binding")
    for key in ("private_input_verified", "boundaries_proved", "accepted_semantics"):
        exact(a[key], False, "analysis false/" + key)
    for key in ("private_reads", "parser_instances", "engine_instances",
                "callback_invocations"):
        exact(a[key], 0, "analysis unused/" + key)
    for key in ("ranges", "range_hashes", "traversals"):
        exact(a[key], None, "missing rather than empty/" + key)
    exact(a["mapping_status"], "not-evaluated", "mapping unobserved")
    exact(a["decoder_agreement"], "not-evaluated", "decoder unobserved")
    exact(a["scope"], {"target_count": 4, "target_bytes": 1568, "target_words": 392,
          "range_authority": "accepted-v3-inspection-envelopes-not-exact-ends"},
          "inspection bounds")
    exact(e["analysis_sha256"], RESULT_HASHES["analysis.json"], "analysis link")
    exact(e["source_records"], {
        "bootstrap": "bootstrap-v10-result.json#/receipt/first_failure",
        "analysis": "analysis.json"}, "source references")
    for key in ("init_chain_edges", "exit_direct_callees"):
        exact(e[key], None, "unobserved edges/" + key)
    for key in ("traversal_complete", "negative_absence_proved",
                "reachable_call_proved", "teardown_join_proved"):
        exact(e[key], False, "no proof/" + key)
    exact(e["candidate_scans"], {
        name: {"status": "not-evaluated", "complete": False,
               "count": None, "candidates": None}
        for name in ("bl", "relocations", "address_words")}, "unobserved scan classes")

def load_records():
    records = []
    for name, digest in RESULT_HASHES.items():
        raw = (ROOT / name).read_bytes()
        need(sha(raw) == digest, "frozen result file/" + name)
        records.append(json.loads(raw))
    b = json.loads((ROOT / "bootstrap-v10.json").read_text())
    m = json.loads((ROOT / "method.json").read_text())
    for name, key in (("bootstrap-v10.json", "bootstrap_sha256"),
                      ("method.json", "method_sha256"), ("FREEZE.md", "freeze_sha256"),
                      ("AMENDMENT-26.md", "amendment_26_sha256"),
                      ("bootstrap-v9-result.json", "accepted_v9_result_sha256")):
        need(sha((ROOT / name).read_bytes()) == EXPECTED_BINDING[key], "source file/" + name)
    need(sha(b["source"].encode()) == EXPECTED_BINDING["bootstrap_source_sha256"], "bootstrap source")
    need(sha(m["source"].encode()) == EXPECTED_BINDING["method_source_sha256"], "method source")
    exact(b["source_sha256"], EXPECTED_BINDING["bootstrap_source_sha256"], "embedded bootstrap")
    exact(m["source_sha256"], EXPECTED_BINDING["method_source_sha256"], "embedded method")
    exact(m["bootstrap_sha256"], EXPECTED_BINDING["bootstrap_sha256"], "method bootstrap link")
    exact(m["accepted_v9_result_sha256"], EXPECTED_BINDING["accepted_v9_result_sha256"], "V9 link")
    exact(m["analysis_inputs"]["accepted_intervals_sha256"],
          EXPECTED_BINDING["accepted_intervals_sha256"], "interval link")
    exact(m["analysis_inputs"]["private_elf"]["sha256"],
          EXPECTED_BINDING["private_elf_expected_sha256"], "expected private identity")
    need(canonical(m["accepted_tool_identity"]) == m["accepted_tool_identity_sha256"],
         "literal tool identity")
    need(sha(b["construction_inputs_utf8"].encode()) ==
         EXPECTED_BINDING["construction_inputs_sha256"], "construction inputs")
    return records

def family(path):
    text = "/".join(str(item) for item in path)
    if "authority" in text or any(word in text for word in (
            "analysis_accepted", "accepted_semantics", "teardown_join_proved",
            "negative_absence_proved")):
        return "authority"
    if any(word in text for word in ("cleanup", "restoration", "custody",
                                     "writer_joined", "child_exited")):
        return "cleanup"
    if "candidate_scans" in text:
        return "candidate-count-class-completion"
    if any(word in text for word in ("init_chain_edges", "exit_direct_callees",
                                     "reachable_call", "source_records")):
        return "edge-target-reachability"
    if any(word in text for word in ("decoder", "capstone_")):
        return "decoder-agreement"
    if any(word in text for word in ("range", "mapping_status", "scope")):
        return "ranges-hashes"
    if any(isinstance(part, str) and part.endswith("_utc") for part in path):
        return "chronology"
    if any(word in text for word in ("binding", "sha256", "schema_version",
                                     "dispatch_commit")):
        return "identities-links"
    if any(word in text for word in ("map_", "mapping_checks", "queue",
                                     "resource", "profile", "asset")):
        return "map-queue-resource-budgets"
    if any(word in text for word in ("method", "private", "parser", "callback",
                                     "engine", "analysis_counts")):
        return "parser-engine-callback-private-counters"
    return "traversal-refusal-boundary"

def mutations(value, path=()):
    if isinstance(value, dict):
        yield path + ("__unexpected__",), True
        for key, child in value.items():
            yield from mutations(child, path + (key,))
    elif isinstance(value, list):
        if not value:
            yield path, ["unexpected"]
        for index, child in enumerate(value):
            yield from mutations(child, path + (index,))
    elif value is None:
        yield path, []
    elif type(value) is bool:
        yield path, not value
    elif type(value) is int:
        yield path, value + 1
    elif isinstance(value, str):
        yield path, "1900-01-01T00:00:00+00:00" if str(path[-1]).endswith("_utc") else value + "-mutated"

def mutation_tests(records):
    for path, value in mutations(records):
        mutant = copy.deepcopy(records)
        at = mutant
        for part in path[:-1]:
            at = at[part]
        at[path[-1]] = value
        # Rebind hashes when mutating receipt semantics so a generic hash failure
        # cannot be the sole rejection. No candidate source/parser is executed.
        if len(path) >= 2 and path[:2] == (0, "receipt"):
            r = mutant[0]["receipt"]
            digest = canonical(r)
            mutant[0]["canonical_receipt_sha256"] = digest
            raw = (json.dumps({"canonical_receipt_sha256": digest, "receipt": r},
                              sort_keys=True) + "\n").encode("ascii")
            mutant[0]["collector"]["logs"]["stdout.json"]["sha256"] = sha(raw)
            mutant[0]["collector"]["logs"]["stdout.json"]["size"] = len(raw)
        rejected = False
        try:
            verify(mutant)
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            rejected = True
        need(rejected, "mutation accepted/" + str(path))
        CASE_COUNTS[family(path)] += 1
    need(all(count > 0 for count in CASE_COUNTS.values()), "missing mutation family")

def main():
    records = load_records()
    verify(records)
    mutation_tests(records)
    print(json.dumps({"status": "passed", "scope": "frozen-public-refusal-only",
          "mutation_cases": sum(CASE_COUNTS.values()), "families": CASE_COUNTS,
          "private_byte_truth_recomputed": False, "candidate_execution": False},
          sort_keys=True))

if __name__ == "__main__":
    main()
