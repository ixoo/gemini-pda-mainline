#!/usr/bin/env python3
"""Offline handoff integrity/refusal checks; does not execute or refetch vendor code."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "c5b0be85017ad0c599725e8273842efdbecdd88a"
PARENT = "a770a606ef28244d143fe270f76264ea6d0391d0"
# Explicit first-review freeze: wlan-common-lifetime-evidence-v1, see FREEZE.md.
# Never regenerate these expected values from mutable handoff records at runtime.
SOURCE_IDENTITIES_SHA256 = "babc630b39828d21513dec6c727ed5a2009409a48b0cd1254c9273123bb103ca"
CITATION_ANCHORS_SHA256 = "f47ee47c50e76874537b33e0f357584073763e9f45106780a8855eab9c3b3fe0"
PREDECESSOR_PATH = "experiments/2026-09-06-mt6797-consys-owner-source-attribution/inputs.json"
PREDECESSOR_SHA256 = "157c990f2f3a04099723ce7098e61840ec3756842381397e787b8ed5956e9496"
EXPECTED_STATES = {
  "callback_direction": "common-to-wlan",
  "normal_before": "WMT_FUNC_ON",
  "normal_during": "no common release in synchronous call chain",
  "normal_after": "WIFI_FUNC_ON on zero return",
  "callback_failure_wifi_state": "POWER_OFF",
  "missing_callback_result": -2,
  "missing_callback_pending_flag": 1,
  "state_reset_clears_pending_flag": False,
  "late_registration_reacquires_common_power": False,
  "late_registration_promotes_wifi_state": False,
  "host_awake_reference": "released after queue wait returns, including timeout",
  "function_off_wifi_state": "POWER_OFF even on callback failure",
  "wmt_wlan_unreg_body_clears_callbacks": True,
  "built_in_unregister_reaches_callback_clear": None,
  "unregister_calls_function_off": False,
  "probe_failure_calls_full_hif_remove": False,
  "universal_lifetime_retained": False
}
EXPECTED_VERDICTS = {
    "callback_assignment": "resolved",
    "function_on_to_firmware": "unresolved",
    "common_lifetime": "contradicted",
    "failure_propagation": "resolved",
    "cleanup_order": "unresolved",
}
AUTHORITY_KEYS = {
    "linux_owner_established", "vendor_code_reusable", "vendor_api_reusable",
    "runtime_authority", "device_action_allowed", "hardware_support_claim",
    "safe_reuse_established",
}
REQUIRED_EVIDENCE = {
    "callback_assignment": {"callback_type", "registration", "assignment", "wifi_on"},
    "function_on_to_firmware": {"queue", "worker", "wifi_table", "wifi_ops", "probe",
                               "firmware_caller", "firmware_mapping", "adapter"},
    "common_lifetime": {"common_on", "func_on", "wifi_on", "state_reset", "assignment"},
    "failure_propagation": {"func_on", "wifi_on", "common_off", "queue", "power_bits"},
    "cleanup_order": {"func_off", "remove", "probe_failure", "bus_register",
                      "assignment", "platform_driver", "init_exit"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf-8")).hexdigest()


def validate_predecessor(files):
    raw = (ROOT / PREDECESSOR_PATH).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PREDECESSOR_SHA256,
            "independent predecessor pin")
    previous = json.loads(raw)
    require(previous["source_commit"] == PIN and previous["source_repository"] ==
            "https://github.com/lineage-geminipda/android_kernel_planet_mt6797",
            "predecessor repository/pin")
    paths = {r["id"]: r["path"] for r in previous["allowlist"]}
    sources = {r["source_id"]: r for r in previous["raw_sources"]}
    reused = set(files) & set(sources)
    require(len(reused) == 13 and len(set(files) - set(sources)) == 4,
            "predecessor/new counts")
    for sid in reused:
        expected = dict(sources[sid], path=paths[sid])
        expected["url"] = ("https://raw.githubusercontent.com/lineage-geminipda/"
                           "android_kernel_planet_mt6797/" + PIN + "/" + paths[sid])
        require(files[sid] == expected, "predecessor complete identity tuple")


def validate(inputs, search, verdicts):
    require(inputs["source_commit"] == verdicts["source_commit"] == PIN, "source pin")
    require(inputs["repository_parent"] == verdicts["repository_parent"] == PARENT,
            "parent pin")
    require(set(verdicts["authority"]) == AUTHORITY_KEYS and
            all(value is False for value in verdicts["authority"].values()), "authority")
    require(verdicts["state_model"] == EXPECTED_STATES, "lifetime/state model")
    predicates = verdicts["predicates"]
    require(set(predicates) == set(EXPECTED_VERDICTS), "all five independent edges")
    files = {row["source_id"]: row for row in inputs["source_files"]}
    require(len(files) == len(inputs["source_files"]) == 17, "source inventory")
    require(canonical_sha256(sorted(inputs["source_files"],
                                    key=lambda r: r["source_id"])) ==
            SOURCE_IDENTITIES_SHA256, "independently frozen source identities")
    validate_predecessor(files)
    require(canonical_sha256(verdicts["citations"]) == CITATION_ANCHORS_SHA256,
            "independently frozen citation anchors")
    require(inputs["counts"] == {
        "requests": 26, "unique_files": 17, "new_regular_files": 4,
        "predecessor_files": 13, "batches": 3, "deliberate_contextual_rereads": 2},
        "count claims")
    require(inputs["rights"] == {
        "source_study_only": True, "source_bodies_retained": False,
        "source_excerpts_in_artifacts": False, "vendor_code_reusable": False}, "rights")
    require(search["budgets"] == {
        "batches": 3, "new_regular_files": 16, "contextual_rereads": 2}, "budgets")
    require(len(search["batches"]) == 3 and len(search["contextual_rereads"]) == 2,
            "declared budget accounting")
    require(len(search["requests"]) == 26, "request receipts")
    seen = set()
    for batch in search["batches"]:
        bid = batch["id"]
        require(batch["freeze_order"] == bid and "frozen_utc" not in batch,
                "no invented freeze timestamp")
        declared = {f["id"]: f for f in batch["files"]}
        receipts = [r for r in search["requests"] if r["batch"] == bid]
        require(len(receipts) == len(declared), "one receipt per declared request")
        require({r["source_id"] for r in receipts} == set(declared), "request allowlist")
        for row in receipts:
            sid = row["source_id"]
            require((bid, sid) not in seen, "duplicate request")
            seen.add((bid, sid))
            require(row["status"] == 200, "recorded response status")
            require(row["started_utc"] <= row["finished_utc"], "measured chronology")
            file = files[sid]
            for key in ("path", "url", "sha256", "git_blob_sha1", "size", "line_count"):
                require(row[key] == file[key], "file/receipt identity")
            require(declared[sid]["path"] == file["path"], "frozen path")
            if "expected_blob" in declared[sid]:
                require(declared[sid]["expected_blob"] == file["git_blob_sha1"],
                        "predecessor blob")
            require(file["url"] ==
                    "https://raw.githubusercontent.com/lineage-geminipda/"
                    "android_kernel_planet_mt6797/" + PIN + "/" + file["path"], "raw pin")
            require(len(file["sha256"]) == 64 and len(file["git_blob_sha1"]) == 40,
                    "digest format")
            require(all(c in "0123456789abcdef" for c in
                        file["sha256"] + file["git_blob_sha1"]), "hex identities")
    require({sid for _, sid in seen} == set(files), "all sources have receipts")
    require(search["stop"]["additional_fetches_permitted"] is False, "stop boundary")
    require(len(search["accounting_notes"]) >= 4, "accounting caveats")
    for name, p in predicates.items():
        require(p["verdict"] == EXPECTED_VERDICTS[name], "separate bounded verdict")
        require(REQUIRED_EVIDENCE[name] <= set(p["evidence"]), "required source edges")
        for key in ("claim", "boundary", "missing", "next_discriminator"):
            require(isinstance(p[key], str) and len(p[key]) > 30, "edge explanation")
        require(set(p["evidence"]) <= set(verdicts["citations"]), "citation keys")
    for c in verdicts["citations"].values():
        require(c["source_id"] in files, "citation source")
        a, b = c["lines"]
        require(type(a) is int and type(b) is int and
                1 <= a <= b <= files[c["source_id"]]["line_count"], "citation range")
        require(bool(c["symbol"]), "citation symbol")
    require(set(verdicts["escalation"]) ==
            {"evidence", "attempts", "unresolved_question", "next_discriminating_check"},
            "escalation packet")


def coordinated_identity_mutation(inputs, search, verdicts):
    """Keep all editable identity copies consistent; the independent freeze must refuse."""
    sid = "hif_h"  # A new source: predecessor comparison alone cannot catch this.
    for row in inputs["source_files"] + search["requests"]:
        if row["source_id"] == sid:
            row.update(sha256="0" * 64, git_blob_sha1="0" * 40,
                       size=row["size"] + 1, line_count=row["line_count"] + 1)
    for batch in search["batches"]:
        for row in batch["files"]:
            if row["id"] == sid and "expected_blob" in row:
                row["expected_blob"] = "0" * 40


def main():
    inputs, search, verdicts = [
        json.loads((HERE / name).read_text())
        for name in ("inputs.json", "search.json", "verdicts.json")]
    validate(inputs, search, verdicts)
    for local in inputs["local_inputs"]:
        require(hashlib.sha256((ROOT / local["path"]).read_bytes()).hexdigest() ==
                local["sha256"], "predecessor input digest")
    # Test the independent predecessor check directly, not only behind the digest gate.
    previous_mutation = {r["source_id"]: copy.deepcopy(r) for r in inputs["source_files"]}
    previous_mutation["ahb"]["line_count"] += 1
    try:
        validate_predecessor(previous_mutation)
    except ValueError:
        pass
    else:
        raise ValueError("refusal accepted: predecessor tuple mutation")

    mutations = [
        ("omitted edge", lambda i, s, v: v["predicates"].pop("cleanup_order")),
        ("reverse callback", lambda i, s, v:
         v["state_model"].update(callback_direction="wlan-to-common")),
        ("failure promoted", lambda i, s, v:
         v["state_model"].update(callback_failure_wifi_state="FUNC_ON")),
        ("invented retention", lambda i, s, v:
         v["state_model"].update(universal_lifetime_retained=True)),
        ("pending flag erased", lambda i, s, v:
         v["state_model"].update(state_reset_clears_pending_flag=True)),
        ("late reacquisition", lambda i, s, v:
         v["state_model"].update(late_registration_reacquires_common_power=True)),
        ("late promotion", lambda i, s, v:
         v["state_model"].update(late_registration_promotes_wifi_state=True)),
        ("unregister power-off", lambda i, s, v:
         v["state_model"].update(unregister_calls_function_off=True)),
        ("ownership authority", lambda i, s, v:
         v["authority"].update(linux_owner_established=True)),
        ("reuse authority", lambda i, s, v:
         v["authority"].update(safe_reuse_established=True)),
        ("runtime authority", lambda i, s, v:
         v["authority"].update(runtime_authority=True)),
        ("missing receipt", lambda i, s, v: s["requests"].pop()),
        ("changed source", lambda i, s, v:
         i["source_files"][0].update(git_blob_sha1="0" * 40)),
        ("omitted evidence", lambda i, s, v:
         v["predicates"]["function_on_to_firmware"].update(evidence=[])),
        ("outside citation", lambda i, s, v:
         v["citations"]["probe"].update(lines=[1, 999999])),
        ("invented freeze time", lambda i, s, v:
         s["batches"][0].update(frozen_utc="2026-09-06T00:00:00Z")),
        ("coordinated source identity", coordinated_identity_mutation),
        ("in-bounds citation relocation", lambda i, s, v:
         v["citations"]["probe"].update(lines=[1413, 1459])),
        ("unregister body erasure", lambda i, s, v:
         v["state_model"].update(wmt_wlan_unreg_body_clears_callbacks=False)),
        ("built-in cleanup promotion", lambda i, s, v:
         v["state_model"].update(built_in_unregister_reaches_callback_clear=True)),
        ("built-in cleanup negative execution claim", lambda i, s, v:
         v["state_model"].update(built_in_unregister_reaches_callback_clear=False)),
    ]
    for name, mutate in mutations:
        i, s, v = copy.deepcopy((inputs, search, verdicts))
        mutate(i, s, v)
        try:
            validate(i, s, v)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("refusal accepted: " + name)
    print("PASS: 5 predicates; 3 batches; 26 receipts; 17 files (4 new); "
          "22 refusal fixtures. Source semantics require independent review.")


if __name__ == "__main__":
    main()
