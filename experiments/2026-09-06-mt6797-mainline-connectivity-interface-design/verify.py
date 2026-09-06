#!/usr/bin/env python3
"""Offline consistency and policy verifier for the MT6797 lifecycle design."""
import copy
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = "7daaf3811a95e7187bd378e0ce345bf4b536630c"
HASHES = {
    "inputs.json": "a82211e63b3d84b4114ec4c05109c3f39f173e11a3263a54ce9aaa9ae7d2d80b",
    "decisions.json": "f3a5155184ca713c96145bbe1a3d8a3e3639734b527d79b6bd6d29700c15696f",
    "state-model.json": "a05217eae1da5f1065048179ae061e1003656cc2a30cf824650c9fb9b8ecdd19",
    "proposal-map.json": "2ab26995d3a5407496c7221ba631d51b8722c7769aa3e2901adec71268dff3a8",
}
DECISION_IDS = [
    "userspace_abi", "owner_boundary", "probe_and_firmware", "typed_errors",
    "teardown", "pm_and_recovery", "proposal_disposition", "upstream_structure",
]
STATE_IDS = [
    "UNBOUND", "BOUND", "OWNER_ACTIVE", "ORDINARY_SUBMITTED", "ORDINARY_DONE",
    "EMI_WRITABLE", "EMI_COPY_SUBMITTED", "EMI_COPIED", "EMI_SEALED",
    "START_SUBMITTED", "FIRMWARE_READY", "READY", "QUIESCING", "OFF",
    "FAULT_HELD",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode()
    return hashlib.sha256(data).hexdigest()


def decision_map(decisions):
    return {row["id"]: row for row in decisions["decisions"]}


def validate_structure(inputs, decisions, states, proposals):
    require(all(x["repository_parent"] == PARENT
                for x in (inputs, decisions, states, proposals)), "parent drift")
    require(inputs["manifest_linux"] == {
        "release": "7.1.3",
        "commit": "4d7d9486c04d917265f64c55bd23b2cc4fe7749c",
    }, "manifest Linux drift")
    require(inputs["linux_inspection_budget"] == {
        "maximum_precisely_named_files_or_pages": 6, "used": 0, "inspected": []
    }, "Linux inspection scope drift")
    require(len(inputs["frozen_files"]) == 42 and
            len({x["path"] for x in inputs["frozen_files"]}) == 42,
            "frozen input coverage")
    require(all(re.fullmatch(r"[0-9a-f]{64}", x["sha256"])
                for x in inputs["frozen_files"]), "input identity")
    require(decisions["default_hypothesis"]["statement"] ==
            "No new userspace lifecycle ABI is needed." and
            decisions["default_hypothesis"]["result"] == "supported",
            "default hypothesis not tested")
    require(set(decisions["default_hypothesis"]["test"]) == {
        "dependency_and_bind", "firmware_acquisition", "network_registration",
        "operator_activation", "diagnostics", "remove_suspend_resume",
    }, "standard-interface coverage")
    require([x["id"] for x in decisions["decisions"]] == DECISION_IDS,
            "decision coverage/order")
    for row in decisions["decisions"]:
        require(isinstance(row["classification"], str) and
                len(row["classification"]) > 5, "decision classification incomplete")
        for field in ("rationale", "responsibility", "unresolved_prerequisite"):
            require(isinstance(row[field], str) and len(row[field]) > 30,
                    "decision field incomplete")
        require(len(row["inputs"]) >= 2 and len(row["rejected_alternatives"]) >= 2,
                "decision evidence/alternatives")
    dm = decision_map(decisions)
    require(dm["userspace_abi"]["classification"] ==
            "no_new_userspace_lifecycle_abi", "vendor ABI copied")
    require(dm["owner_boundary"]["classification"] ==
            "one_consys_provider_many_clients", "dual shared ownership")
    responsibility = " ".join(dm["owner_boundary"]["responsibility"].split())
    require("WLAN receives no raw physical addresses" in responsibility,
            "WLAN raw resource responsibility")
    require(set(dm["owner_boundary"].get("no_export_acceptance", [])) == {
        "raw_physical_addresses", "shared_mmio_pointers", "reset_controls",
        "protection_permission_words",
    }, "WLAN explicit no-export acceptance")
    require(dm["typed_errors"]["classification"] ==
            "first_error_with_separate_containment", "aggregate/discarded error")
    require(dm["teardown"]["classification"] == "quiescence_proven_release",
            "unproven reverse teardown")
    require(dm["pm_and_recovery"]["classification"] ==
            "owner_epoch_recovery_only", "automatic retry authority")
    require(all(value is False for value in decisions["authority"].values()),
            "authority promotion")
    require([x["id"] for x in states["states"]] == STATE_IDS, "state coverage/order")
    require(states["invariants"]["first_error"].startswith("Preserve the first primary errno"),
            "aggregate errno")
    require(states["invariants"]["start_readiness"] ==
            "START_SUBMITTED is never firmware READY.", "START/readiness conflation")
    require(states["invariants"]["release"].startswith(
            "No effect-bearing resource is released before observable"),
            "release before quiescence")
    require(states["invariants"]["retry"].startswith("No automatic firmware"),
            "automatic retry")
    require(states["invariants"]["activation_failure"].startswith(
            "An activation rejection proven effect-free remains BOUND"),
            "partial activation failure")
    require(states["invariants"]["registration"].startswith(
            "FIRMWARE_READY is distinct from wireless registration"),
            "wireless registration boundary")
    require(states["invariants"]["poison_basis"].startswith(
            "Effect history and ownership certainty determine poisoning"),
            "errno-only poisoning")
    require(states["invariants"]["lifetime"].startswith(
            "Consumer callbacks, transaction objects, module/code lifetime"),
            "consumer/code lifetime release")
    edges={(x["from"], x["event"], x["to"]) for x in states["transitions"]}
    require(len(edges) == len(states["transitions"]) == 32, "missing/duplicate state edge")
    for edge in {
        ("BOUND", "activation_rejected_no_effect", "BOUND"),
        ("BOUND", "activation_failed_after_effect", "FAULT_HELD"),
        ("ORDINARY_SUBMITTED", "ordinary_fail", "FAULT_HELD"),
        ("EMI_COPY_SUBMITTED", "emi_copy_fail", "FAULT_HELD"),
        ("START_SUBMITTED", "readiness_observed", "FIRMWARE_READY"),
        ("START_SUBMITTED", "start_or_readiness_fail", "FAULT_HELD"),
        ("FIRMWARE_READY", "wireless_registration_succeeded", "READY"),
        ("FIRMWARE_READY", "wireless_registration_failed", "FAULT_HELD"),
        ("QUIESCING", "quiescence_proven", "OFF"),
        ("QUIESCING", "quiescence_fail", "FAULT_HELD"),
        ("FAULT_HELD", "explicit_owner_recover", "QUIESCING"),
    }:
        require(edge in edges, "required state edge")
    require(len(states["error_classes"]) == 9 and
            all("poisons_epoch" not in x and "effect_free_disposition" in x and
                "after_effect_attempt" in x for x in states["error_classes"]),
            "effect-sensitive typed error model")
    unsupported = next(x for x in states["error_classes"]
                       if x["errno"] == "-EOPNOTSUPP")
    require("may remain BOUND" in unsupported["effect_free_disposition"] and
            "enters FAULT_HELD" in unsupported["after_effect_attempt"],
            "effectful unsupported secure operation")
    by_state = {x["id"]: x for x in states["states"]}
    lifetime = {"consumer_callbacks", "transaction_object", "module_code_reference",
                "provider_reference", "client_reference"}
    require(lifetime <= set(by_state["FAULT_HELD"]["held_resources"]) and
            lifetime <= set(by_state["QUIESCING"]["held_resources"]),
            "premature consumer/code lifetime release")
    require("Only now may failed-probe/unbind callbacks" in
            by_state["OFF"]["cleanup_obligations"], "OFF lifetime release point")
    wifi = proposals["wifi_series"]
    require([x["order"] for x in wifi] == list(range(1, 13)),
            "twelve proposal order")
    require(all(re.search(fr"/{x['order']:04d}-wifi-", x["path"])
                for x in wifi), "Wi-Fi proposal identity")
    require(len(proposals["companion_0001_proposals"]) == 3 and
            all("/0001-" in x["path"] for x in proposals["companion_0001_proposals"]),
            "companion inventory")
    require(proposals["summary"] == {
        "wifi_series_entries": 12, "companions_inventoried": 3,
        "runtime_ready_entries": 0, "upstream_submission_ready_entries": 0,
        "new_userspace_abi_entries": 0,
    }, "proposal-status inflation")
    require(all(x["observed_status"].startswith(("compile_only", "unselected"))
                or x["observed_status"] == "independent_proposal"
                for x in wifi + proposals["companion_0001_proposals"]),
            "proposal runtime promotion")


def validate_files(inputs):
    for row in inputs["frozen_files"]:
        raw = (ROOT / row["path"]).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == row["sha256"],
                "frozen input file drift")


def validate_readme():
    text = (HERE / "README.md").read_text()
    normalized = " ".join(text.split())
    for phrase in (
        "needs no new userspace lifecycle ABI", "START_SUBMITTED", "FAULT_HELD",
        "cfg80211", "request_firmware()", "All twelve Wi-Fi-series proposals",
        "No proposal is promoted to runtime-ready", "Measured credits: unavailable",
    ):
        require(phrase in normalized, "README required boundary")
    require(not re.search(r"hardware support (?:is|has been) (?:complete|established)|"
                          r"runtime support (?:is|has been) (?:complete|established)", text,
                          re.IGNORECASE), "README support promotion")


def main():
    objects = {name: json.loads((HERE / name).read_text()) for name in HASHES}
    for name, expected in HASHES.items():
        require(digest(objects[name]) == expected, "canonical freeze: " + name)
    i, d, s, p = (objects[name] for name in
                  ("inputs.json", "decisions.json", "state-model.json", "proposal-map.json"))
    validate_structure(i, d, s, p)
    validate_files(i)
    validate_readme()

    cases = []
    def case(name, target, mutate):
        cases.append((name, target, mutate))
    case("copied vendor ABI", "d", lambda x: x["authority"].update(vendor_ioctl_compatibility=True))
    case("dual ownership", "d", lambda x: decision_map(x)["owner_boundary"].update(classification="dual_owner"))
    case("WLAN raw EMI/remap writes", "d", lambda x: decision_map(x)["owner_boundary"].update(responsibility="WLAN receives raw addresses and writes shared registers directly."))
    case("aggregate errno", "s", lambda x: x["invariants"].update(first_error="Add every errno into one aggregate."))
    case("init-result discard", "d", lambda x: decision_map(x)["typed_errors"].update(classification="log_and_discard"))
    case("START/readiness conflation", "s", lambda x: x["invariants"].update(start_readiness="START submission means READY."))
    case("reverse-order teardown", "d", lambda x: decision_map(x)["teardown"].update(classification="reverse_vendor_init"))
    case("release before quiescence", "s", lambda x: x["invariants"].update(release="Release on timeout."))
    case("automatic retry/radio", "s", lambda x: x["invariants"].update(retry="Automatically retry START and radio."))
    case("compile/runtime promotion", "p", lambda x: x["summary"].update(runtime_ready_entries=1))
    case("missing state edge", "s", lambda x: x["transitions"].pop())
    case("proposal-status inflation", "p", lambda x: x["wifi_series"][0].update(observed_status="runtime_ready"))
    case("scope/input drift", "i", lambda x: x["linux_inspection_budget"].update(used=7))
    case("partial activation released", "s", lambda x: x["transitions"].__setitem__(
         next(n for n, e in enumerate(x["transitions"])
              if e["event"] == "activation_failed_after_effect"),
         {"from": "BOUND", "event": "activation_failed_after_effect", "to": "BOUND"}))
    case("registration failure released", "s", lambda x: x["transitions"].__setitem__(
         next(n for n, e in enumerate(x["transitions"])
              if e["event"] == "wireless_registration_failed"),
         {"from": "FIRMWARE_READY", "event": "wireless_registration_failed", "to": "OFF"}))
    case("effectful unsupported released", "s", lambda x: next(
         e for e in x["error_classes"] if e["errno"] == "-EOPNOTSUPP").update(
         after_effect_attempt="Return to BOUND and release everything."))
    case("premature callback/code release", "s", lambda x: next(
         e for e in x["states"] if e["id"] == "FAULT_HELD")["held_resources"].remove(
         "module_code_reference"))
    originals = {"i": i, "d": d, "s": s, "p": p}
    for name, target, mutate in cases:
        changed = copy.deepcopy(originals)
        mutate(changed[target])
        try:
            validate_structure(changed["i"], changed["d"], changed["s"], changed["p"])
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("refusal accepted: " + name)
    print("PASS: 8 decisions; 15 states; 32 edges; 12 Wi-Fi proposals; "
          "3 companions; 17 policy refusals; no new userspace ABI.")


if __name__ == "__main__":
    main()
