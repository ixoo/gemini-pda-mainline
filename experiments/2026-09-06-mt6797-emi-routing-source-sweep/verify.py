#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline frozen-record verification; no network, device or source execution."""

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = {
    "inputs.json": "f1214d6d599db2fa49ffcf1c2d7d76e81aa6c0bd2b9cd187237bc425ab6bbe4f",
    "search-attempts.json": "54360f28a66137a6be7926d3ff9ade9dfd0ca523a85269f20d865d13f1a13eb1",
    "verdicts.json": "a2c6afcfff113d4c0ab11c7b83a2e595cf7ca3b0aa3a097fb009f75ffafdea9e",
}
CORPUS_IDENTITIES = [
    ("tfa-mt8192-emi-c", "plat/mediatek/mt8192/drivers/emi_mpu/emi_mpu.c", "201f7a19ba54f574a20bc17b0a01bcfcbd411a661ffc47f3f3e94d69d21166eb", 3146),
    ("tfa-mt8192-emi-h", "plat/mediatek/mt8192/drivers/emi_mpu/emi_mpu.h", "d5781374df318930a4c80bdccae6411869a8b9cd90c47d0abf473eed1c55f7f3", 3371),
]
RETAINED_IDENTITIES = [
    ("experiments/2026-09-06-mt6797-emi-domain-attribution/results/verdicts.json", "458bbd8b15b59dc40663315c8c305829fc1ca9df4d144a2b61166726daf8a63f", 4561),
    ("experiments/2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md", "8c4963c1d9e63b98bb7dcdad8ed41e442f1f6171e8c599869758f4984e7a7f06", 8912),
    ("experiments/2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md", "a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021", 20811),
]
ROUTING_PREDICATES = {
    "ap": ("transaction_to_assignment_chain_established", "bridge_security_override_established"),
    "consys": ("transaction_to_assignment_chain_established", "bridge_security_override_established"),
    "wlan": ("attributable_firmware_transaction_established", "joined_to_exact_consys_master"),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def utc(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def validate_routing_contract(routes):
    """Check conditional evidence dependencies before this sweep's fixed result.

    A hypothetical complete CONSYS chain may satisfy this structural contract;
    it never admits a change to the frozen sweep or supplies source evidence.
    """
    require(set(routes) == set(ROUTING_PREDICATES), "routing inventory")
    for name, predicates in ROUTING_PREDICATES.items():
        route = routes[name]
        require(set(route) == {"verdict", "effective_domain", "citations", "reason", *predicates}, name + " routing shape")
        require(route["verdict"] in ("resolved", "contradicted", "unresolved"), name + " verdict enum")
        for key in predicates:
            require(type(route[key]) is bool, name + " boolean type: " + key)
    # Check WLAN first so a generic CONSYS proof cannot mask this discriminator.
    wlan, consys = routes["wlan"], routes["consys"]
    if wlan["verdict"] == "resolved":
        require(
            consys["verdict"] == "resolved"
            and all(consys[k] is True for k in ROUTING_PREDICATES["consys"])
            and type(consys["effective_domain"]) is int
            and type(wlan["effective_domain"]) is int
            and wlan["effective_domain"] == consys["effective_domain"]
            and all(wlan[k] is True for k in ROUTING_PREDICATES["wlan"]),
            "WLAN prerequisite: complete CONSYS chain plus attributable WLAN fetch/data joined to exact master/domain",
        )
    for name, predicates in ROUTING_PREDICATES.items():
        route = routes[name]
        if route["verdict"] == "resolved":
            require(type(route["effective_domain"]) is int and route["effective_domain"] >= 0, name + " resolved domain")
            require(all(route[k] is True for k in predicates), name + " resolved chain prerequisites")
        elif route["verdict"] == "unresolved":
            require(route["effective_domain"] is None, name + " unresolved domain")
            for key in predicates:
                require(route[key] is False, name + " unresolved predicate: " + key)


def validate(records, check_retained=True, check_frozen=True):
    require(set(records) == set(FROZEN), "record inventory changed")
    # Independent constants prevent co-mutating paths, hashes, evidence and
    # verdicts into a self-consistent replacement corpus. They are a review
    # boundary, not a cryptographic signature against editing this program.
    if check_frozen:
        for name, expected in FROZEN.items():
            require(digest(encoded(records[name])) == expected, "frozen " + name)
    inputs = records["inputs.json"]
    ledger = records["search-attempts.json"]
    verdicts = records["verdicts.json"]
    require(len(inputs["corpus"]) == 2, "corpus cardinality")
    require([tuple(c[k] for k in ("id", "path", "sha256", "bytes")) for c in inputs["corpus"]] == CORPUS_IDENTITIES, "corpus identity")
    require([tuple(c[k] for k in ("path", "sha256", "bytes")) for c in inputs["frozen_records"]] == RETAINED_IDENTITIES, "retained identity")
    for source in inputs["corpus"]:
        require(source["license"] == "BSD-3-Clause" and source["rights"] == "public-primary-inspection-only; no source body retained or redistributed", "source rights")
        require(source["mt6797_compatibility_established"] is False, "source compatibility")
    require(ledger["totals"] == {
        "executed_requests": 10, "completed_attempts": 3, "new_primary_files": 2
    }, "totals")
    require([a["id"] for a in ledger["attempts"]] == ["A1", "B1", "B2"], "attempt inventory")
    require(len(ledger["attempts"]) <= 4, "attempt cap")
    branch_counts = {}
    global_order = 0
    previous = None
    fetched = set()
    for attempt in ledger["attempts"]:
        branch = attempt["branch"]
        count, requests = branch_counts.get(branch, (0, 0))
        branch_counts[branch] = (count + 1, requests + len(attempt["requests"]))
        require(len(attempt["requests"]) == len(attempt["predeclared_requests"]), "missing request")
        require(len(attempt["requests"]) <= attempt["maximum_requests"] <= 4, "request cap")
        start, stop = utc(attempt["started_utc"]), utc(attempt["stopped_utc"])
        for order, (plan, request) in enumerate(zip(attempt["predeclared_requests"], attempt["requests"]), 1):
            global_order += 1
            require(plan["order"] == request["order"] == order, "local order")
            require(request["global_order"] == global_order, "global order")
            require(all(request[k] == v for k, v in plan.items()), "undeclared request")
            began, ended = utc(request["started_utc"]), utc(request["completed_utc"])
            require(start <= began <= ended <= stop, "timestamp bounds")
            require(previous is None or previous <= began, "request chronology")
            previous = ended
            require(request["reported_result_count"] == len(request["dispositions"]), "hit inventory")
            require(not request["redirects_reported"], "unaccounted redirect")
            if request["kind"] == "source-fetch":
                fetched.add(request["result_identity"]["corpus_id"])
    require(all(a <= 2 and r <= 8 for a, r in branch_counts.values()), "branch cap")
    require(global_order == 10 and global_order <= 16, "item request cap")
    require(fetched == {c["id"] for c in inputs["corpus"]}, "fetched inventory")
    require(len(fetched) <= 12, "source cap")
    citations = {"attempt:" + a["id"] for a in ledger["attempts"]}
    citations |= {"source:" + c["id"] for c in inputs["corpus"]}
    validate_routing_contract(verdicts["routing"])
    for routing in verdicts["routing"].values():
        require(routing["verdict"] == "unresolved", "routing promotion")
        require(routing["effective_domain"] is None, "domain selection")
        require(set(routing["citations"]) <= citations, "unknown routing citation")
    overlap = verdicts["overlap"]
    require(overlap["verdict"] == "unresolved", "overlap promotion")
    require(overlap["winning_region_rule"] is None and overlap["rule_applicability_conditions"] is None, "unresolved overlap shape")
    for key in ("priority_rule_established", "active_region_applicability_established", "mt6797_compatibility_established"):
        require(overlap[key] is False, key)
    require(set(overlap["citations"]) <= citations, "unknown overlap citation")
    for key in ("policy_selection_allowed", "device_action_allowed", "hardware_support_claim", "source_copy_allowed"):
        require(verdicts[key] is False, key)
    if check_retained:
        for record in inputs["frozen_records"]:
            data = (ROOT / record["path"]).read_bytes()
            require(len(data) == record["bytes"] and digest(data) == record["sha256"], "retained input changed")


def refusal_fixtures(records):
    fixtures = []

    def fixture(name, mutate, expected_reason=None):
        modified = copy.deepcopy(records)
        mutate(modified)
        fixtures.append((name, modified, expected_reason))

    fixture("co-mutated corpus path/hash", lambda r: r["inputs.json"]["corpus"][0].update(path="replacement.c", sha256="0" * 64))
    fixture("co-mutated frozen record path/hash", lambda r: r["inputs.json"]["frozen_records"][0].update(path="replacement.json", sha256="0" * 64))
    fixture("missing corpus item", lambda r: r["inputs.json"]["corpus"].pop())
    fixture("extra corpus item", lambda r: r["inputs.json"]["corpus"].append(copy.deepcopy(r["inputs.json"]["corpus"][0])))
    for name in ("ap", "consys", "wlan"):
        fixture(name + " routing promotion", lambda r, n=name: r["verdicts.json"]["routing"][n].update(verdict="resolved", effective_domain=2))

    def generic_consys_only(r):
        routes = r["verdicts.json"]["routing"]
        routes["consys"].update(verdict="resolved", effective_domain=2, transaction_to_assignment_chain_established=True, bridge_security_override_established=True)
        routes["wlan"].update(verdict="resolved", effective_domain=2)

    fixture("WLAN promoted from generic CONSYS-to-D2 only", generic_consys_only,
            "WLAN prerequisite: complete CONSYS chain plus attributable WLAN fetch/data joined to exact master/domain")
    # A positive structural control proves the generic CONSYS record is valid
    # independently of WLAN, while never accepting it as this sweep's result.
    control = copy.deepcopy(records["verdicts.json"]["routing"])
    control["consys"].update(verdict="resolved", effective_domain=2, transaction_to_assignment_chain_established=True, bridge_security_override_established=True)
    validate_routing_contract(control)
    print("CONTROL: generic CONSYS-to-D2 contract valid with WLAN unresolved")
    for name, predicates in ROUTING_PREDICATES.items():
        for key in predicates:
            fixture(name + " unresolved predicate promotion: " + key,
                    lambda r, n=name, k=key: r["verdicts.json"]["routing"][n].update({k: True}),
                    name + " unresolved predicate: " + key)
            fixture(name + " non-boolean predicate: " + key,
                    lambda r, n=name, k=key: r["verdicts.json"]["routing"][n].update({k: 0}),
                    name + " boolean type: " + key)
    for key in ("priority_rule_established", "active_region_applicability_established", "mt6797_compatibility_established"):
        fixture(key + " promotion", lambda r, k=key: r["verdicts.json"]["overlap"].update({k: True}))
    for key in ("policy_selection_allowed", "device_action_allowed", "hardware_support_claim", "source_copy_allowed"):
        fixture(key + " expansion", lambda r, k=key: r["verdicts.json"].update({k: True}))
    fixture("source rights expansion", lambda r: r["inputs.json"]["corpus"][0].update(rights="unrestricted-copy"))
    fixture("fabricated attempt", lambda r: r["search-attempts.json"]["attempts"].append(copy.deepcopy(r["search-attempts.json"]["attempts"][0])))
    fixture("undeclared query", lambda r: r["search-attempts.json"]["attempts"][0]["predeclared_requests"][0].update(query="replacement"))
    fixture("missing discovery hit", lambda r: r["search-attempts.json"]["attempts"][0]["requests"][0]["dispositions"].pop())
    fixture("reordered requests", lambda r: r["search-attempts.json"]["attempts"][0]["requests"].reverse())
    fixture("changed citation", lambda r: r["verdicts.json"]["overlap"]["citations"].append("source:invented"))
    for name, modified, expected_reason in fixtures:
        try:
            validate(modified, check_retained=False, check_frozen=False)
        except ValueError as error:
            if expected_reason is not None:
                require(str(error) == expected_reason, "wrong refusal reason for " + name + ": " + str(error))
            print("REFUSED:", name, "--", error)
        else:
            raise ValueError("fixture accepted: " + name)
    return len(fixtures)


def main():
    records = {}
    for name, expected in FROZEN.items():
        raw = (HERE / name).read_bytes()
        require(digest(raw) == expected, "raw record changed: " + name)
        records[name] = json.loads(raw)
    validate(records)
    count = refusal_fixtures(records)
    print(f"PASS: 3 attempts, 10 requests, 2 primary files; {count} in-memory refusals; all predicates unresolved; no policy/device authority")


if __name__ == "__main__":
    main()
