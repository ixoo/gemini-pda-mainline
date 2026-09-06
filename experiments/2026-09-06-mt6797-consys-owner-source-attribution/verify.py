#!/usr/bin/env python3
"""Offline integrity/refusal checks for a frozen, manually reviewed source audit.

No network, source retrieval, device access or semantic proof is performed here.
The independently pinned receipt digests prevent co-mutated JSON assertions from
silently becoming evidence; changing this verifier requires a fresh review.
"""

import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PARENT = "d56c4d8763d2b11f0521b945e890a9a108dbe16e"
SOURCE = "c5b0be85017ad0c599725e8273842efdbecdd88a"
PINS = {
    "inputs.json": "157c990f2f3a04099723ce7098e61840ec3756842381397e787b8ed5956e9496",
    "search-attempts.json": "408963b5f149130f507570448a868861d681096cca69be477105caee4ab73113",
    "verdicts.json": "beaa116bf405d8143353b98bb458143eb2ff1ad07020f72fb8006a0df3750af9",
}
EXPECTED = {
    "dynamic_reservation_producer": "resolved",
    "consys_power_reset_owner": "unresolved",
    "wlan_to_common_handoff": "unresolved",
    "shared_remap_writer": "unresolved",
    "emi_region18_requester": "unresolved",
}
FLAGS = {
    "linux_owner_established", "vendor_code_reusable", "vendor_api_reusable",
    "policy_selected", "runtime_authority", "device_action_allowed",
    "hardware_support_claim",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    encoded = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def verify(documents, check_local=True):
    require(set(documents) == set(PINS), "document inventory")
    for name, value in documents.items():
        require(digest(value) == PINS[name], "frozen content changed: " + name)
        require(value["repository_parent"] == PARENT, "parent identity")
        require(value["source_commit"] == SOURCE, "source identity")
    inputs = documents["inputs.json"]
    attempts = documents["search-attempts.json"]
    verdicts = documents["verdicts.json"]
    require((inputs["file_cap"], inputs["batch_cap"], inputs["reference_hop_cap"])
            == (120, 4, 2), "caps")
    allow = {item["id"]: item for item in inputs["allowlist"]}
    require(len(allow) == len(inputs["allowlist"]) == 32, "allowlist")
    raw = {item["source_id"]: item for item in inputs["raw_sources"]}
    require(set(raw) == set(allow), "whole-file union")
    for item in allow.values():
        path = Path(item["path"])
        require(not path.is_absolute() and ".." not in path.parts, "relative path")
        require(item["mode"] in {"100644", "100755"}, "regular source")
    batches = attempts["batches"]
    require([b["id"] for b in batches] == list("ABCD"), "batch inventory")
    require(attempts["search_complete"] is True, "unfinished searches")
    union, request_ids = set(), set()
    for batch in batches:
        require(batch["status"] == "completed", "batch state")
        require(batch["max_reference_hops"] == 2, "hop cap")
        require(set(batch["planned_sources"]) <= set(allow), "planned source")
        for receipt in batch["opens"]:
            sid = receipt["source_id"]
            require(sid in batch["planned_sources"], "unplanned body read")
            require(receipt["request_id"] not in request_ids, "duplicate request")
            request_ids.add(receipt["request_id"])
            union.add(sid)
            require(len(union) <= 120, "cumulative file cap")
            require(receipt["http_status"] == 200, "unsuccessful receipt")
            require(receipt["git_blob_sha1"] == allow[sid]["git_blob_sha1"], "blob identity")
            require(receipt["size"] == allow[sid]["size"], "source size")
            require(receipt["sha256"] == raw[sid]["sha256"], "raw response identity")
            require(re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]), "digest format")
            require(receipt["url"] == receipt["final_url"], "unexpected redirect")
            require("/" + SOURCE + "/" + allow[sid]["path"] in receipt["url"], "immutable URL")
            hits = receipt["query_hit_lines"]
            require(hits == sorted(set(hits)), "hit inventory")
            require(all(1 <= n <= raw[sid]["line_count"] for n in hits), "hit bounds")
            require(receipt["disposition"] == ("hit" if hits else "no-hit"), "hit disposition")
        require(set(batch["planned_sources"]) <= union, "missing planned source")
    lost = batches[0]["unavailable_receipt_attempt"]
    require(lost["disposition"] == "local-output-capture-failed", "lost receipt status")
    require(set(lost["source_ids"]) <= union, "lost receipt union")
    require(len(request_ids) == 41 and union == set(raw), "request accounting")
    require(set(verdicts["authority"]) == FLAGS, "authority flags")
    require(all(value is False for value in verdicts["authority"].values()), "false authority")
    require(verdicts["rights"] == {"source_study_only": True,
            "source_copy_permission": False, "firmware_redistribution_permission": False}, "rights")
    require(inputs["rights"] == {"source_study_only": True,
            "source_bodies_retained": False, "source_excerpts_in_artifacts": False,
            "vendor_code_reusable": False}, "source retention")
    require(set(verdicts["predicates"]) == set(EXPECTED), "predicate inventory")
    citations = verdicts["citations"]
    for citation in citations.values():
        sid = citation["source_id"]
        lo, hi = citation["lines"]
        require(sid in raw and 1 <= lo <= hi <= raw[sid]["line_count"], "citation bounds")
        require(bool(citation["symbol"]), "symbol locator")
    for key, predicate in verdicts["predicates"].items():
        require(predicate["verdict"] == EXPECTED[key], "unsupported promotion")
        require(set(predicate["evidence"]) <= set(citations), "missing citation")
        require(all(predicate[k] for k in ("claim", "boundary", "missing", "next_discriminator")), "incomplete verdict")
    if check_local:
        for item in inputs["local_inputs"]:
            require(hashlib.sha256((REPO / item["path"]).read_bytes()).hexdigest()
                    == item["sha256"], "local input changed: " + item["path"])


def refusals(documents):
    cases = []
    def changed(name, mutate):
        value = copy.deepcopy(documents)
        mutate(value)
        cases.append((name, value))
    def co_mutate(value):
        for document in value.values():
            document["source_commit"] = "0" * 40
    changed("co-mutated-source", co_mutate)
    changed("fabricated-search", lambda d: d["search-attempts.json"]["batches"][0]["opens"][0].update(query_hit_lines=[1]))
    changed("expanded-file-cap", lambda d: d["inputs.json"].update(file_cap=121))
    changed("expanded-batch-cap", lambda d: d["inputs.json"].update(batch_cap=5))
    changed("expanded-hop-cap", lambda d: d["inputs.json"].update(reference_hop_cap=3))
    changed("constant-promoted", lambda d: d["verdicts.json"]["predicates"]["emi_region18_requester"].update(verdict="resolved", evidence=["adapter_declaration"]))
    changed("string-promoted", lambda d: d["verdicts.json"]["predicates"]["shared_remap_writer"].update(verdict="resolved", evidence=["remap_offset"]))
    changed("source-copy-permission", lambda d: d["verdicts.json"]["rights"].update(source_copy_permission=True))
    changed("device-authority", lambda d: d["verdicts.json"]["authority"].update(device_action_allowed=True))
    changed("hardware-promotion", lambda d: d["verdicts.json"]["authority"].update(hardware_support_claim=True))
    changed("linux-owner-promotion", lambda d: d["verdicts.json"]["authority"].update(linux_owner_established=True))
    for name, value in cases:
        try:
            verify(value, check_local=False)
        except ValueError:
            continue
        raise ValueError("refusal fixture accepted: " + name)
    return len(cases)


if __name__ == "__main__":
    docs = {name: json.loads((ROOT / name).read_text()) for name in PINS}
    verify(docs)
    count = refusals(docs)
    print(f"PASS: 4 batches, 32 distinct files, 41 retained receipts; {count} refusal fixtures")
    print("Source-only: 1 resolved at API boundary; 4 unresolved; no device/build/support authority")
