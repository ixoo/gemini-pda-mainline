#!/usr/bin/env python3
"""Offline frozen source audit; no source execution, fetch or hardware action."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "c5b0be85017ad0c599725e8273842efdbecdd88a"
PARENT = "30d414811724c25ebd4183c00f06cd8d27aebb0b"
# Explicit independent freeze declared before this verifier: see FREEZE.md.
SOURCE_HASH = "071f5eea45e49947ff3dce0c68d60f5aa0d9d26f84822da0829758a96105fd65"
ANCHOR_HASH = "f39c0cdd3eaf7e88cb6ea4e58487a45f230710373fdf5eacabbaf283e50f437c"
REQUEST_HASH = "3c44201852f69b65b5fabcc2dc993888e334cfdc928fbedab79757f88cc3b745"
PREV = "experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/"
LOCAL_HASHES = {
    "inputs.json": "c5e123769535553523f70ce0ad3bb15343bf6dfb9637d064059a896f43c5ae66",
    "search.json": "f744eb95aa2f181da5ab2e942b6d8c9b75cf1810a062056cdf9e27484804f8f9",
    "verdicts.json": "eae36049120463942aa22040f6111d81021831912a4a866b689681afd1b03b76",
    "FREEZE.md": "a138e6c12507118a81f8ac723be13796057577f9dcc085725596c288ffa5ebc4",
}
STATES = {
  "selected_mode": "built-in",
  "config_mtk_combo": "y",
  "config_mtk_combo_wifi": "y",
  "config_mtk_combo_chip": "CONSYS_6797",
  "selected_generation_macro": "MTK_WCN_WLAN_GEN3",
  "makefile_obj_y_order": [
    "conn_drv_init.o",
    "common_drv_init.o",
    "bluetooth_drv_init.o",
    "gps_drv_init.o",
    "fm_drv_init.o",
    "wlan_drv_init.o"
  ],
  "selected_audit_sources": [
    "conn_drv_init.c",
    "common_drv_init.c",
    "wlan_drv_init.c"
  ],
  "ant_standard_object_selection": None,
  "wlan_chip_argument_condition": "0x6797 (0x6630 shares this case)",
  "wlan_strong_definition": "wlan_drv_init.c:do_wlan_drv_init",
  "wlan_weak_fallback": "conn_drv_init.c:do_wlan_drv_init",
  "final_link_selection_observed": False,
  "gen3_direct_caller": "do_wlan_drv_init",
  "wlan_wrapper_direct_caller": "do_connectivity_driver_init",
  "outer_connectivity_caller": None,
  "init_registration_mechanism": None,
  "gen3_result_handling": "returned by gen3 export; added to WLAN aggregate; WLAN aggregate added to connection aggregate",
  "wifi_char_init_failure_stops_gen3": False,
  "common_result_handling": "four integer init results summed",
  "common_nonzero_stops_connection_sequence": True,
  "noncommon_failure_stops_connection_sequence": False,
  "zero_aggregate_proves_all_success": False,
  "connection_call_order": [
    "common",
    "Bluetooth",
    "GPS",
    "FM",
    "WLAN",
    "ANT"
  ],
  "common_call_order": [
    "set_chip_type",
    "HIF-SDIO",
    "common",
    "STP-UART",
    "STP-SDIO"
  ],
  "wlan_call_order": [
    "WMT-Wi-Fi character device",
    "gen3 WLAN"
  ],
  "exit_caller": None,
  "exit_registration_mechanism": None,
  "exit_invoked": None,
  "exit_call_order": None
}
VERDICTS = {
    "selected_objects": "resolved", "gen3_init_caller": "unresolved",
    "init_return_handling": "resolved", "gen3_exit_caller": "unresolved",
    "explicit_order": "resolved",
}
AUTHORITY = {
    "runtime_equivalence", "resource_ownership", "firmware_success", "radio_enablement",
    "vendor_code_reusable", "vendor_api_reusable", "device_action_allowed",
    "hardware_support_claim",
}
COUNTS = {
    "network_requests": 4, "raw_successes": 4, "raw_failures": 0,
    "new_regular_files": 4, "inherited_regular_files": 6, "source_identity_tuples": 10,
    "batches": 2, "directory_inventories": 0, "contextual_rereads": 0,
    "no_hit_records": 4,
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
    require(set(inherited) == set(files) & set(old) and len(inherited) == 6,
            "inherited selection")
    for sid in inherited:
        require(files[sid] == old[sid], "complete inherited identity")


def validate(i, s, v):
    require(i["source_commit"] == v["source_commit"] == PIN, "source pin")
    require(i["repository_parent"] == v["repository_parent"] == PARENT, "parent pin")
    require(digest(s) == REQUEST_HASH, "independent complete request freeze")
    require(digest(v["citations"]) == ANCHOR_HASH, "independent exact anchor freeze")
    require(digest(sorted(i["source_files"], key=lambda r: r["source_id"])) ==
            SOURCE_HASH, "independent complete source freeze")
    require(digest(v["state_model"]) == digest(STATES), "conditional semantic model")
    require(set(v["authority"]) == AUTHORITY and
            all(x is False for x in v["authority"].values()), "no authority")
    require(set(v["predicates"]) == set(VERDICTS), "five independent edges")
    require(i["counts"] == s["counts"] == COUNTS, "counts")
    files = {r["source_id"]: r for r in i["source_files"]}
    require(len(files) == len(i["source_files"]) == 10, "unique source inventory")
    predecessor(files, i["inherited_source_ids"])
    require(i["rights"]["source_study_only"] is True and
            all(i["rights"][k] is False for k in (
                "source_bodies_retained", "source_excerpts_in_artifacts",
                "vendor_code_reusable")), "rights/storage")
    require(s["budgets"] == {
        "batches": 2, "new_regular_files": 8, "directory_inventories": 1,
        "contextual_rereads": 2}, "budget contract")
    require(len(s["batches"]) == 2 and len(s["requests"]) == 4 and
            len(s["no_hits"]) == 4 and s["contextual_rereads"] == [], "receipt coverage")
    require(s["batches"][0]["requests"][0]["source_id"] == "drv_make" and
            len(s["batches"][0]["requests"]) == 1, "Makefile alone first")
    new = set()
    for batch in s["batches"]:
        declarations = {r["request_id"]: r for r in batch["requests"]}
        receipts = [r for r in s["requests"] if r["batch"] == batch["id"]]
        require(len(receipts) == len(declarations) and
                {r["request_id"] for r in receipts} == set(declarations), "complete allowlist")
        sample = datetime.datetime.strptime(batch["clock_sample_before_freeze"],
                    "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc)
        for r in receipts:
            d = declarations[r["request_id"]]
            require(r["kind"] == "raw" and r["status"] == 200 and
                    "selected_lines" not in r, "successful metadata-only receipt")
            require(d["path"] == r["path"] and d["source_id"] == r["source_id"],
                    "predeclared identity")
            require(d["expected_git_blob_sha1"] == r["git_blob_sha1"] and
                    d["expected_size"] == r["size"], "inventory identity match")
            require(sample <= datetime.datetime.fromisoformat(r["started_utc"]) <=
                    datetime.datetime.fromisoformat(r["finished_utc"]), "chronology")
            f = files[r["source_id"]]
            for k in ("path", "url", "sha256", "git_blob_sha1", "size", "line_count"):
                require(f[k] == r[k], "source/receipt tuple")
            require(r["url"] == "https://raw.githubusercontent.com/lineage-geminipda/"
                    "android_kernel_planet_mt6797/" + PIN + "/" + r["path"], "raw pinned URL")
            new.add(r["source_id"])
    require(new == {"drv_make", "conn_drv_init", "common_drv_init", "wlan_drv_init"},
            "Makefile-selected body corpus")
    require(new | set(i["inherited_source_ids"]) == set(files), "inventory coverage")
    require(s["makefile_selection"]["source_sha256"] == files["drv_make"]["sha256"] and
            s["makefile_selection"]["selected_audit_sources"] == STATES["selected_audit_sources"],
            "Makefile selection freeze")
    require(s["stop"]["additional_source_reads_permitted"] is False, "stop boundary")
    for name, p in v["predicates"].items():
        require(p["verdict"] == VERDICTS[name], "bounded verdict")
        for k in ("claim", "conditions", "missing", "next_discriminator"):
            require(isinstance(p[k], str) and len(p[k]) > 30, "explicit edge boundary")
        require(bool(p["evidence"]) and set(p["evidence"]) <= set(v["citations"]), "citations")
    for c in v["citations"].values():
        require(c["source_id"] in files and
                1 <= c["lines"][0] <= c["lines"][1] <= files[c["source_id"]]["line_count"],
                "exact source range")


def coordinated_identity(i, s, v):
    for r in i["source_files"] + s["requests"]:
        if r["source_id"] == "wlan_drv_init":
            r["git_blob_sha1"] = "0" * 40
    s["batches"][1]["requests"][2]["expected_git_blob_sha1"] = "0" * 40


def coordinated_receipt(i, s, v):
    r = s["requests"][0]
    r.update(url="https://example.invalid", sha256="0" * 64, size=0)
    s["batches"][0]["requests"][0]["expected_size"] = 0


def main():
    i, s, v = [json.loads((HERE / n).read_text())
               for n in ("inputs.json", "search.json", "verdicts.json")]
    require({r["path"]: r["sha256"] for r in i["local_inputs"]} ==
            {PREV + k: h for k, h in LOCAL_HASHES.items()}, "fixed predecessor files")
    for n, h in LOCAL_HASHES.items():
        require(hashlib.sha256((ROOT / PREV / n).read_bytes()).hexdigest() == h,
                "local input identity")
    validate(i, s, v)
    mutations = []
    for key, wrong in [
        ("selected_mode", "module"),
        ("selected_generation_macro", "MTK_WCN_WLAN_GEN2"),
        ("selected_audit_sources", ["conn_drv_init.c", "wlan_drv_init.c"]),
        ("makefile_obj_y_order", list(reversed(STATES["makefile_obj_y_order"]))),
        ("ant_standard_object_selection", True),
        ("gen3_direct_caller", "invented"),
        ("wlan_wrapper_direct_caller", "invented"),
        ("outer_connectivity_caller", "invented"),
        ("init_registration_mechanism", "module_init"),
        ("final_link_selection_observed", True),
        ("gen3_result_handling", "returned unchanged; no information loss"),
        ("wifi_char_init_failure_stops_gen3", True),
        ("common_result_handling", "individual errors preserved"),
        ("common_nonzero_stops_connection_sequence", False),
        ("noncommon_failure_stops_connection_sequence", True),
        ("zero_aggregate_proves_all_success", True),
        ("connection_call_order", list(reversed(STATES["connection_call_order"]))),
        ("common_call_order", list(reversed(STATES["common_call_order"]))),
        ("wlan_call_order", list(reversed(STATES["wlan_call_order"]))),
        ("exit_caller", "invented"),
        ("exit_registration_mechanism", "module_exit"),
        ("exit_invoked", True), ("exit_invoked", False),
        ("exit_call_order", list(reversed(STATES["connection_call_order"]))),
    ]:
        mutations.append((key, lambda a, b, c, key=key, wrong=wrong:
                          c["state_model"].update({key: wrong})))
    for key in AUTHORITY:
        mutations.append((key, lambda a, b, c, key=key: c["authority"].update({key: True})))
    mutations += [
        ("coordinated source identity", coordinated_identity),
        ("coordinated receipt identity", coordinated_receipt),
        ("in-bounds citation move", lambda a, b, c: c["citations"]["wlan_gen3_call"].update(lines=[39, 50])),
        ("missing request", lambda a, b, c: b["requests"].pop()),
        ("no-hit deletion", lambda a, b, c: b["no_hits"].pop()),
        ("budget drift", lambda a, b, c: b["budgets"].update(batches=3)),
        ("invented failure", lambda a, b, c: b["requests"][0].update(status="failed")),
        ("missing predicate", lambda a, b, c: c["predicates"].pop("gen3_exit_caller")),
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
    altered["gl_init"]["line_count"] += 1
    try:
        predecessor(altered, i["inherited_source_ids"])
    except ValueError:
        pass
    else:
        raise ValueError("refusal accepted: independent predecessor mutation")
    print(f"PASS: 5 predicates; 10 source tuples; 18 anchors; 4 receipts; "
          f"{len(mutations) + 1} refusals. Source reachability only.")


if __name__ == "__main__":
    main()
