#!/usr/bin/env python3
"""Verify frozen source-attribution receipts without network or device access.

This checks integrity of manually interpreted source evidence, not source
semantics, deployed code, or independent proof that an HTTP request occurred.
"""

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PARENT = "cb035d7f8b9f782b1b8b1139352621fe2a38c025"
SOURCE = "c5b0be85017ad0c599725e8273842efdbecdd88a"
PINS = {
    "inputs.json": "b118e573457aa0b5b123150c8224fc3eca170fc4b6c237c0b120dcb7640777cf",
    "search-attempts.json": "403b2d2e23caaff8d5259e7b8dc9024f8ff336ee1d68c888fb390dcab5946152",
    "verdicts.json": "c11c9551446d3e585f463f20dce392a79c446be2f448c6dc0c14aa2bb7c4e215",
}
FLAGS = {
    "deployed_adapter_established", "secure_firmware_compatibility_established",
    "policy_selected", "vendor_code_reusable", "vendor_api_reusable",
    "linux_owner_established", "runtime_authority", "device_action_allowed",
    "hardware_support_claim",
}
PREDICATES = {
    "adapter_definition", "secure_call_mapping", "adapter_return_semantics",
    "region18_end_to_end",
}
CITATIONS = {
    "build_parent", "build_object", "build_outer", "config_arm64", "config_soc",
    "config_psci", "config_platform", "config_emi", "header_include",
    "adapter_body", "adapter_declaration", "secure_id", "secure_macro",
    "secure_arguments", "secure_return", "outer_pack_and_drop",
}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def canonical_hash(value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def time(value):
    return datetime.fromisoformat(value.replace(" UTC", "+00:00"))


def verify(documents, local_inputs=True):
    require(set(documents) == set(PINS), "document inventory")
    for name, document in documents.items():
        require(canonical_hash(document) == PINS[name], "frozen evidence: " + name)
        require(document["repository_parent"] == PARENT, "parent identity")
        require(document["source_commit"] == SOURCE, "source identity")
    inputs, attempts, verdicts = (documents[name] for name in PINS)
    require((inputs["file_cap"], inputs["batch_cap"], inputs["reference_hop_cap"])
            == (16, 2, 2), "caps")
    allow = {item["id"]: item for item in inputs["allowlist"]}
    raw = {item["source_id"]: item for item in inputs["raw_sources"]}
    require(len(allow) == len(inputs["allowlist"]) == 10, "allowlist size")
    require(set(allow) == set(raw), "raw file union")
    trees = {item["request_id"]: item for item in inputs["tree_requests"]}
    require(set(trees) == {"tree-1", "tree-2"}, "tree requests")
    frozen = time(inputs["allowlist_frozen_utc"])
    declared = time(attempts["predeclared_utc"])
    for tree in trees.values():
        require(tree["tree_sha"] == SOURCE and tree["truncated"] is False, "tree identity")
        require(tree["http_status"] == 200 and tree["url"] == tree["final_url"], "tree response")
        require(time(tree["started_utc"]) <= time(tree["finished_utc"]) <= frozen, "inventory before freeze")
    for item in allow.values():
        path = Path(item["path"])
        require(not path.is_absolute() and ".." not in path.parts, "relative source")
        require(item["mode"] in {"100644", "100755"}, "regular source")
        require(item["inventory_request"] in trees, "source inventory provenance")
    require([b["id"] for b in attempts["batches"]] == ["A", "B"], "batch inventory")
    require(attempts["search_complete"] is True, "search state")
    union, requests, contexts = set(), set(), {}
    for batch in attempts["batches"]:
        require(batch["status"] == "completed" and batch["max_reference_hops"] == 2, "batch state/bound")
        require(frozen <= declared <= time(batch["started_utc"]) <= time(batch["finished_utc"]), "predeclared batch")
        require({r["source_id"] for r in batch["opens"]} == set(batch["planned_sources"]), "planned opens")
        for receipt in batch["opens"]:
            sid = receipt["source_id"]
            require(sid in allow and sid in batch["planned_sources"], "source outside scope")
            require(receipt["request_id"] not in requests, "request uniqueness")
            requests.add(receipt["request_id"])
            union.add(sid)
            require(len(union) <= 16, "cumulative file cap")
            require(time(batch["started_utc"]) <= time(receipt["started_utc"])
                    <= time(receipt["finished_utc"]) <= time(batch["finished_utc"]), "request timestamps")
            expected_url = "https://raw.githubusercontent.com/lineage-geminipda/android_kernel_planet_mt6797/" + SOURCE + "/" + allow[sid]["path"]
            require(receipt["url"] == receipt["final_url"] == expected_url, "immutable raw URL")
            require(receipt["http_status"] == 200, "HTTP result")
            require(receipt["git_blob_sha1"] == allow[sid]["git_blob_sha1"] == raw[sid]["git_blob_sha1"], "blob identity")
            require(receipt["size"] == allow[sid]["size"] == raw[sid]["size"], "whole-file size")
            require(receipt["sha256"] == raw[sid]["sha256"], "raw digest")
            require(receipt["line_count"] == raw[sid]["line_count"], "source line count")
            for field in ("query_hit_lines", "inspected_context_lines"):
                lines = receipt[field]
                require(lines == sorted(set(lines)), "unique line inventory")
                require(all(1 <= n <= receipt["line_count"] for n in lines), "line bounds")
            require(receipt["disposition"] == ("hit" if receipt["query_hit_lines"] else "no-hit"), "hit disposition")
            contexts.setdefault(sid, set()).update(receipt["inspected_context_lines"])
    require(len(requests) == 11 and union == set(allow), "final request accounting")
    for chain in attempts["reference_chains"]:
        require(chain["batch"] in {"A", "B"}, "chain batch")
        require(all(edge["depth"] in {1, 2} for edge in chain["edges"]), "reference depth")
    require(set(verdicts["authority"]) == FLAGS, "authority inventory")
    require(all(flag is False for flag in verdicts["authority"].values()), "authority promotion")
    require(verdicts["rights"] == {"source_study_only": True, "source_copy_permission": False,
                                   "firmware_redistribution_permission": False}, "rights")
    require(inputs["rights"] == {"source_study_only": True, "source_bodies_retained": False,
                                 "source_excerpts_in_artifacts": False, "source_copy_permission": False}, "source retention")
    require(set(verdicts["citations"]) == CITATIONS, "citation keys")
    for citation in verdicts["citations"].values():
        lo, hi = citation["lines"]
        require(set(range(lo, hi + 1)) <= contexts[citation["source_id"]], "citation not inspected")
        require(bool(citation["symbol"]), "symbol locator")
    require(set(verdicts["predicates"]) == PREDICATES, "predicate keys")
    for predicate in verdicts["predicates"].values():
        require(predicate["verdict"] == "resolved", "frozen verdict")
        require(set(predicate["evidence"]) <= CITATIONS, "predicate references")
        require(all(predicate[k] for k in ("claim", "boundary", "unresolved", "next_discriminator")), "missing inference boundary")
    require(verdicts["mapping"]["function_id"] == "0x82000209", "function identifier")
    require(verdicts["mapping"]["region18_high_bits"] == "0x90000000", "region packing")
    if local_inputs:
        for item in inputs["local_inputs"]:
            require(hashlib.sha256((REPO / item["path"]).read_bytes()).hexdigest()
                    == item["sha256"], "local input changed: " + item["path"])
        previous = verdicts["predecessor_citations"]["wlan_region18"]
        prev_verdicts = json.loads((REPO / previous["verdicts_path"]).read_text())
        citation = prev_verdicts["citations"][previous["citation_key"]]
        require(citation == {k: previous[k] for k in ("source_id", "lines", "symbol")}, "predecessor locator")
        prev_inputs = json.loads((REPO / previous["inputs_path"]).read_text())
        source = next(r for r in prev_inputs["raw_sources"] if r["source_id"] == previous["source_id"])
        require(source["sha256"] == previous["source_sha256"], "predecessor source identity")


def refusals(documents):
    fixtures = []
    def add(name, mutate):
        value = copy.deepcopy(documents)
        mutate(value)
        fixtures.append((name, value))
    for field in ("repository_parent", "source_commit"):
        def mutate(value, field=field):
            for document in value.values():
                document[field] = "0" * 40
        add("co-mutated-" + field, mutate)
    add("fabricated-request", lambda d: d["search-attempts.json"]["batches"][0]["opens"][0].update(sha256="0" * 64))
    add("missing-request", lambda d: d["search-attempts.json"]["batches"][0]["opens"].pop())
    for field, value in (("file_cap", 17), ("batch_cap", 3), ("reference_hop_cap", 3)):
        add("expanded-" + field, lambda d, f=field, v=value: d["inputs.json"].update({f: v}))
    for predicate, only in (("adapter_definition", "adapter_declaration"),
                            ("secure_call_mapping", "secure_macro"),
                            ("adapter_return_semantics", "outer_pack_and_drop"),
                            ("region18_end_to_end", "outer_pack_and_drop")):
        add("insufficient-" + predicate, lambda d, p=predicate, c=only: d["verdicts.json"]["predicates"][p].update(evidence=[c]))
    add("source-copy", lambda d: d["verdicts.json"]["rights"].update(source_copy_permission=True))
    add("source-excerpts", lambda d: d["inputs.json"]["rights"].update(source_excerpts_in_artifacts=True))
    for flag in sorted(FLAGS):
        add("independent-" + flag, lambda d, f=flag: d["verdicts.json"]["authority"].update({f: True}))
    for name, value in fixtures:
        try:
            verify(value, local_inputs=False)
        except ValueError:
            continue
        raise ValueError("refusal accepted: " + name)
    return len(fixtures)


if __name__ == "__main__":
    documents = {name: json.loads((ROOT / name).read_text()) for name in PINS}
    verify(documents)
    count = refusals(documents)
    print(f"PASS: 2 batches, 10 files, 11 raw requests, 2 tree requests; {count} refusal fixtures")
    print("Four source predicates resolved; nine authority flags remain false")
