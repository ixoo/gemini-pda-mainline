#!/usr/bin/env python3
"""Verify frozen offline source attribution, never vendor execution or hardware."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "c5b0be85017ad0c599725e8273842efdbecdd88a"
PARENT = "05e3e04afd0f00a6a2ed1fdb9a263af8c0fd1d0d"
# Declared before this verifier: wlan-builtin-lifecycle-evidence-v1, FREEZE.md.
SOURCE_HASH = "6bd252d81c02cbf7c87c14b160cbb6fd07d08f4858a6f749373e60901af0f8e1"
ANCHOR_HASH = "ab5ce53493e19f0326cabd9f13d5f330f5ecb6c918228ab61659df1c4e6f6220"
# First-review extension declared in FREEZE.md before verifier repair.
REQUEST_EVIDENCE_HASH = "243404485bfabccdb140a5b00cca58fa7ce11d9f285255939c03e610145257c0"
REQUEST_EVIDENCE_KEYS = (
    "budgets", "batches", "requests", "contextual_rereads", "inherited_contexts",
    "counts", "no_hits",
)
PREV = "experiments/2026-09-06-mt6797-wlan-common-lifetime-source-attribution/"
LOCAL_HASHES = {
    "FREEZE.md": "2f208177361a13afa0eb18ecf30e281d4b2500332d9f94970e2266c08addc673",
    "inputs.json": "67b821b2f67c719c25b6ff10c41c9946b339e4cbead8e83dd28b90ca50377944",
    "search.json": "a485f2eac7fe72002189aeff567bf7ee00af19bdba8a464d64178a4aa6df31b6",
    "verdicts.json": "6d85c932a465d2756beb4411b80364e468a5ff56eade665448e566b581102e67",
}
STATES = {
  "selected_mode": "built-in non-MODULE",
  "wifi_guard_value": 1,
  "wifi_guard_is_config_test": False,
  "wifi_table_entry": "wmt_func_wifi_ops",
  "initWlan_direct_caller": "mtk_wcn_wlan_gen3_init",
  "initWlan_return_observed_by_export": True,
  "outer_builtin_init_caller": None,
  "outer_builtin_init_return_handling": None,
  "exitWlan_direct_caller": "mtk_wcn_wlan_gen3_exit",
  "outer_builtin_exit_caller": None,
  "builtin_exit_invoked": None,
  "exit_p_result": "NULL",
  "platform_remove_initial_value": "NULL",
  "generic_driver_remove_initial_value": "NULL",
  "platform_bus_remove_initial_value": "NULL",
  "selected_static_unregister_dispatch_reaches_callback_clear": False,
  "actual_runtime_callback_clear": None,
  "wmt_wlan_unreg_body_clears_callbacks": True
}
VERDICTS = {
    "wifi_guard_table": "resolved", "builtin_init": "unresolved",
    "builtin_exit": "unresolved", "builtin_exit_pointer": "resolved",
    "unregister_clear_reachability": "resolved",
}
COUNTS = {
    "network_requests": 18, "raw_successes": 13, "raw_failures": 2,
    "directory_inventory_successes": 3, "new_regular_files": 12,
    "inherited_regular_files": 10, "source_identity_tuples": 22,
    "contextual_function_rereads": 0,
}
AUTHORITY = {
    "linux_owner_established", "vendor_code_reusable", "vendor_api_reusable",
    "runtime_authority", "device_action_allowed", "hardware_support_claim",
    "safe_reuse_established",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def predecessor(files, inherited):
    raw = (ROOT / PREV / "inputs.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == LOCAL_HASHES["inputs.json"],
            "independent predecessor pin")
    old = {r["source_id"]: r for r in json.loads(raw)["source_files"]}
    require(set(inherited) == set(files) & set(old) and len(inherited) == 10,
            "exact inherited selection")
    for sid in inherited:
        require(files[sid] == old[sid], "complete predecessor tuple")


def validate(i, s, v):
    require(digest({k: s[k] for k in REQUEST_EVIDENCE_KEYS}) == REQUEST_EVIDENCE_HASH,
            "independent immutable request evidence freeze")
    require(i["source_commit"] == v["source_commit"] == PIN, "source pin")
    require(i["repository_parent"] == v["repository_parent"] == PARENT, "parent pin")
    require(digest(v["state_model"]) == digest(STATES), "conditional reachability model")
    require(set(v["authority"]) == AUTHORITY and
            all(x is False for x in v["authority"].values()), "no authority")
    require(set(v["predicates"]) == set(VERDICTS), "five separate predicates")
    files = {r["source_id"]: r for r in i["source_files"]}
    require(len(files) == len(i["source_files"]) == 22, "source count")
    require(digest(sorted(i["source_files"], key=lambda r: r["source_id"])) ==
            SOURCE_HASH, "independent source freeze")
    require(digest(v["citations"]) == ANCHOR_HASH, "independent anchor freeze")
    predecessor(files, i["inherited_source_ids"])
    require(i["counts"] == s["counts"] == COUNTS, "exact accounting")
    require(i["rights"] == {"source_study_only": True, "source_bodies_retained": False,
            "source_excerpts_in_artifacts": False, "vendor_code_reusable": False}, "rights")
    require(s["budgets"] == {"batches": 3, "new_regular_files": 12,
                            "contextual_rereads": 2}, "budgets")
    require(len(s["batches"]) == 3 and len(s["requests"]) == 18 and
            s["contextual_rereads"] == [], "batch/request/reread accounting")
    tally = {"raw_successes": 0, "raw_failures": 0, "directory_inventory_successes": 0}
    new = set()
    for batch in s["batches"]:
        declared = {r["id"]: r for r in batch["requests"]}
        receipts = [r for r in s["requests"] if r["batch"] == batch["id"]]
        require(len(receipts) == len(declared) and
                {r["request_id"] for r in receipts} == set(declared), "allowlist receipts")
        sample = datetime.datetime.strptime(batch["clock_sample_before_freeze"],
                    "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc)
        for r in receipts:
            d = declared[r["request_id"]]
            require((r["kind"], r["path"]) == (d["kind"], d["path"]), "declared path")
            start = datetime.datetime.fromisoformat(r["started_utc"])
            end = datetime.datetime.fromisoformat(r["finished_utc"])
            require(sample <= start <= end, "measured chronology")
            require("selected_lines" not in r, "no retained source excerpt")
            if r["kind"] == "raw":
                require(r["url"] == "https://raw.githubusercontent.com/lineage-geminipda/"
                        "android_kernel_planet_mt6797/" + PIN + "/" + r["path"], "raw URL")
                if r["status"] == 200:
                    tally["raw_successes"] += 1
                    f = files[r["source_id"]]
                    for key in ("path", "url", "sha256", "git_blob_sha1", "size", "line_count"):
                        require(r[key] == f[key], "receipt/source identity")
                    require(r["response_sha256"] == f["sha256"] and
                            r["response_bytes"] == f["size"], "response identity")
                    new.add(r["source_id"])
                else:
                    tally["raw_failures"] += 1
                    require(r["status"] == "failed" and
                            r["error"] == "HTTP Error 404: Not Found", "explicit failed path")
            else:
                require(r["kind"] == "contents" and r["status"] == 200 and
                        isinstance(r["entries"], list), "directory inventory")
                tally["directory_inventory_successes"] += 1
    require(all(tally[k] == COUNTS[k] for k in tally), "receipt totals")
    require(len(new) == 12 and new | set(i["inherited_source_ids"]) == set(files),
            "new regular file cap and coverage")
    require(s["stop"]["additional_source_reads_permitted"] is False, "stop boundary")
    for name, p in v["predicates"].items():
        require(p["verdict"] == VERDICTS[name], "independent verdict")
        for k in ("claim", "conditions", "missing", "next_discriminator"):
            require(isinstance(p[k], str) and len(p[k]) > 30, "predicate boundary")
        require(bool(p["evidence"]) and set(p["evidence"]) <= set(v["citations"]),
                "predicate citations")
    for c in v["citations"].values():
        require(c["source_id"] in files and
                1 <= c["lines"][0] <= c["lines"][1] <= files[c["source_id"]]["line_count"],
                "citation range")


def coordinated(i, s, v):
    for r in i["source_files"] + s["requests"]:
        if r.get("source_id") == "platform_core":
            r["git_blob_sha1"] = "0" * 40


def mutate_inventory(i, s, v, empty=False):
    receipt = next(r for r in s["requests"] if r["kind"] == "contents")
    if empty:
        receipt["entries"] = []
    else:
        receipt["entries"][0].update(name="invented", path="invented", sha="0" * 40)
    # Coordinate mutable response identity with the modified entries. The fixed
    # evidence digest must refuse this even if all mutable fields agree.
    raw = json.dumps(receipt["entries"], sort_keys=True).encode()
    receipt["response_sha256"] = hashlib.sha256(raw).hexdigest()
    receipt["response_bytes"] = len(raw)


def mutate_contents_field(s, key, value):
    next(r for r in s["requests"] if r["kind"] == "contents")[key] = value


def main():
    i, s, v = [json.loads((HERE / f).read_text())
               for f in ("inputs.json", "search.json", "verdicts.json")]
    require({r["path"]: r["sha256"] for r in i["local_inputs"]} ==
            {PREV + k: h for k, h in LOCAL_HASHES.items()}, "fixed local inputs")
    for name, h in LOCAL_HASHES.items():
        require(hashlib.sha256((ROOT / PREV / name).read_bytes()).hexdigest() == h,
                "predecessor file digest")
    validate(i, s, v)
    mutations = []
    for key, wrong in [
        ("wifi_guard_value", 0), ("wifi_guard_is_config_test", True),
        ("wifi_table_entry", "NULL"), ("selected_mode", "module"),
        ("initWlan_direct_caller", "invented"), ("initWlan_return_observed_by_export", False),
        ("outer_builtin_init_caller", "invented"), ("outer_builtin_init_return_handling", "checked"),
        ("exitWlan_direct_caller", "invented"), ("outer_builtin_exit_caller", "invented"),
        ("builtin_exit_invoked", True), ("builtin_exit_invoked", False),
        ("exit_p_result", "HifAhbPltmRemove"),
        ("platform_remove_initial_value", "HifAhbPltmRemove"),
        ("generic_driver_remove_initial_value", "platform_drv_remove"),
        ("platform_bus_remove_initial_value", "platform_drv_remove"),
        ("selected_static_unregister_dispatch_reaches_callback_clear", True),
        ("actual_runtime_callback_clear", True), ("actual_runtime_callback_clear", False),
    ]:
        mutations.append((key, lambda a, b, c, key=key, wrong=wrong:
                          c["state_model"].update({key: wrong})))
    for key in AUTHORITY:
        mutations.append((key, lambda a, b, c, key=key: c["authority"].update({key: True})))
    mutations += [
        ("coordinated identity", coordinated),
        ("in-bounds anchor", lambda a, b, c: c["citations"]["exit_macro"].update(lines=[364, 367])),
        ("omitted predicate", lambda a, b, c: c["predicates"].pop("builtin_exit")),
        ("omitted receipt", lambda a, b, c: b["requests"].pop()),
        ("coordinated inventory mutation", mutate_inventory),
        ("coordinated inventory emptying", lambda a, b, c: mutate_inventory(a, b, c, True)),
        ("no-hit deletion", lambda a, b, c: b["no_hits"].clear()),
        ("contents URL mutation", lambda a, b, c: mutate_contents_field(b, "url", "https://example.invalid")),
        ("contents response hash mutation", lambda a, b, c: mutate_contents_field(b, "response_sha256", "0" * 64)),
        ("contents response size mutation", lambda a, b, c: mutate_contents_field(b, "response_bytes", 0)),
    ]
    for name, mutate in mutations:
        a, b, c = copy.deepcopy((i, s, v))
        mutate(a, b, c)
        try:
            validate(a, b, c)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("refusal accepted: " + name)
    altered = {r["source_id"]: copy.deepcopy(r) for r in i["source_files"]}
    altered["ahb"]["line_count"] += 1
    try:
        predecessor(altered, i["inherited_source_ids"])
    except ValueError:
        pass
    else:
        raise ValueError("refusal accepted: independent predecessor tuple")
    print(f"PASS: 5 predicates; 22 source tuples; 36 anchors; 18 requests; "
          f"{len(mutations) + 1} refusals. No source execution or runtime claim.")


if __name__ == "__main__":
    main()
