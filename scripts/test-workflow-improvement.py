#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Hardware-free refusal fixtures for the workflow improvement cohorts."""

from __future__ import annotations

import copy
import importlib.util
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "workflow_validator", ROOT / "scripts/validate-workflow-improvement.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
BASE = "63919a7ca33d1a0f5f6b5eaef9f33c58e79ec808"


def rejected(pointer: dict, config: dict, agents: dict, fragment: str) -> None:
    try:
        MODULE.validate(pointer, config, agents)
    except (MODULE.ValidationError, ValueError) as error:
        assert fragment in str(error), (fragment, str(error))
    else:
        raise AssertionError(f"expected refusal containing {fragment!r}")


def rejected_call(call, fragment: str) -> None:
    try:
        call()
    except MODULE.ValidationError as error:
        assert fragment in str(error), (fragment, str(error))
    else:
        raise AssertionError(f"expected refusal containing {fragment!r}")


def route(role: str, model: str, effort: str) -> dict:
    return {"role": role, "model": model, "effort": effort}


def accepted(pointer: dict, number: int, *, risk: str = "routine",
             accepted_first: bool = True, escalated: bool = False) -> dict:
    effective = pointer["effective_decision"]
    return {
        "considered_sequence": number + 1,
        "candidate_id": f"accepted-{number}",
        "disposition": "accepted",
        "accepted_sequence": number,
        "offline_eligible": True,
        "work_type": "implementation",
        "risk_class": risk,
        "acceptance_contract": "fixture-contract-v1",
        "parent": BASE,
        "owner_route": route("gemini_implementer", "gpt-5.6-luna", "high"),
        "review_route": copy.deepcopy(effective["coordinator"]),
        "result": {
            "first_review_accepted": accepted_first,
            "rework_cycles": 0 if accepted_first else 1,
            "started_at": "2026-09-05T00:00:00Z",
            "review_ready_at": "2026-09-05T00:08:00Z",
            "accepted_at": "2026-09-05T00:10:00Z",
            "elapsed_minutes": 10,
            "review_rework_minutes": 2,
            "timing_source": "fixture clock",
            "escalated": escalated,
            "escalation_reason": "unclear acceptance" if escalated else None,
            "escalation_packet": {
                "evidence": "project/WORKFLOW_IMPROVEMENT.md",
                "attempts": ["reviewed the frozen acceptance contract"],
                "unresolved_question": "which acceptance predicate applies?",
                "next_discriminating_check": "obtain the integration owner's ruling"
            } if escalated else None,
            "review_failure_class": None,
            "measured_credits": None,
            "credit_source": "unavailable",
            "credit_unit": None,
            "accepted_evidence": "project/WORKFLOW_IMPROVEMENT.md"
        }
    }


def add_items(pointer: dict, count: int) -> None:
    ledger_path = ROOT / pointer["cohorts"][0]["ledger"]
    ledger = MODULE.load_json(ledger_path)
    bootstrap = next(item for item in ledger["considered_items"]
                     if item.get("candidate_id") == "workflow-loop-bootstrap")
    ledger["considered_items"] = [copy.deepcopy(bootstrap)]
    ledger["checkpoints"] = []
    ledger["settings_decisions"] = []
    ledger["considered_items"].extend(accepted(pointer, number) for number in range(1, count + 1))
    ledger["accepted_count"] = count
    ledger["next_accepted_sequence"] = count + 1
    ledger["next_considered_sequence"] = count + 2
    pointer["_test_ledger"] = ledger


def use_test_ledger(pointer: dict):
    original = MODULE.load_json
    test_ledger = pointer.pop("_test_ledger")

    def load(path: Path) -> dict:
        if path.name == "ledger.json":
            return test_ledger
        return original(path)
    MODULE.load_json = load
    return original


def checkpoint(ledger: dict, after: int, trigger: str = "interval") -> None:
    ledger["checkpoints"].append({
        "id": f"checkpoint-{after}",
        "after_accepted_sequence": after,
        "after_considered_sequence": after + 1,
        "trigger": trigger,
        "trigger_item_ids": [f"accepted-{after}"],
        "comparable_item_ids": [f"accepted-{number}" for number in range(1, after + 1)],
        "conclusion": "no-change",
        "evidence": "experiments/2026-09-05-agent-routing-pilot/README.md"
    })


def decision(pointer: dict, ledger: dict, decision_id: str,
             state: str = "planned", before: dict | None = None) -> dict:
    before = copy.deepcopy(before or MODULE.route_snapshot(pointer["effective_decision"]))
    after = copy.deepcopy(before)
    after["coordinator"]["effort"] = "high"
    return {
        "id": decision_id, "state": state, "defect_class": None,
        "evidence_item_ids": [f"accepted-{number}" for number in range(1, 6)],
        "comparison_tuple": MODULE.comparison_tuple(ledger["considered_items"][1]),
        "settings_before": before, "settings_after": after,
        "changed_variable": "coordinator.effort", "pre_change_considered_sequence": 6,
        "change_parent_commit": BASE, "effective_commit": None,
        "affected_future_work": ["future implementation items"],
        "hypothesis": "reduce review rework", "observation_boundary": "five items",
        "rollback_condition": "lower first-review acceptance"
    }


def main() -> None:
    pointer = MODULE.load_json(MODULE.POINTER)
    config = tomllib.loads(MODULE.CONFIG.read_text())
    agents = {path.stem: tomllib.loads(path.read_text()) for path in MODULE.AGENTS.glob("*.toml")}
    MODULE.validate(pointer, config, agents)

    bad = copy.deepcopy(pointer)
    bad["effective_decision"]["coordinator"]["effort"] = "high"
    bad_config = copy.deepcopy(config)
    bad_config["model_reasoning_effort"] = "high"
    bad_agents = copy.deepcopy(agents)
    bad_agents["gemini_reasoner"]["model_reasoning_effort"] = "high"
    rejected(bad, bad_config, bad_agents, "baseline anchor")

    bad = copy.deepcopy(pointer)
    add_items(bad, 5)
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "item-five checkpoint")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 2)
    for item in bad["_test_ledger"]["considered_items"][-2:]:
        item["result"]["first_review_accepted"] = False
        item["result"]["rework_cycles"] = 1
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "consecutive review misses")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 2)
    ledger = bad["_test_ledger"]
    for item in ledger["considered_items"][-2:]:
        item["result"]["first_review_accepted"] = False
        item["result"]["rework_cycles"] = 1
    ledger["checkpoints"] = [{
        "id": "future-evidence", "after_accepted_sequence": 0,
        "after_considered_sequence": 0, "trigger": "early-signal",
        "trigger_item_ids": ["accepted-1", "accepted-2"],
        "comparable_item_ids": ["accepted-1", "accepted-2"],
        "conclusion": "no-change",
        "evidence": "experiments/2026-09-05-agent-routing-pilot/README.md"
    }]
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "occurs after checkpoint boundary")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 1)
    ledger = bad["_test_ledger"]
    ledger["considered_items"][-1]["candidate_id"] = "workflow-loop-bootstrap"
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "duplicate candidate")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 1)
    bad["_test_ledger"]["considered_items"][-1]["result"]["elapsed_minutes"] = float("inf")
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "finite and non-negative")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 1)
    result = bad["_test_ledger"]["considered_items"][-1]["result"]
    result["escalated"] = True
    result["escalation_reason"] = "unclear acceptance"
    result["escalation_packet"] = None
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "escalation packet")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 5)
    ledger = bad["_test_ledger"]
    ledger["considered_items"][-1]["risk_class"] = "cross-file"
    checkpoint(ledger, 5)
    before = MODULE.route_snapshot(bad["effective_decision"])
    after = copy.deepcopy(before)
    after["coordinator"]["effort"] = "high"
    ledger["settings_decisions"] = [{
        "id": "non-comparable", "state": "planned", "defect_class": None,
        "evidence_item_ids": [f"accepted-{number}" for number in range(1, 6)],
        "comparison_tuple": MODULE.comparison_tuple(ledger["considered_items"][1]),
        "settings_before": before, "settings_after": after,
        "changed_variable": "coordinator.effort", "pre_change_considered_sequence": 6,
        "change_parent_commit": BASE, "effective_commit": None,
        "affected_future_work": ["future implementation items"],
        "hypothesis": "reduce review rework", "observation_boundary": "five items",
        "rollback_condition": "lower first-review acceptance"
    }]
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "not comparable")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 5)
    ledger = bad["_test_ledger"]
    checkpoint(ledger, 5)
    before = MODULE.route_snapshot(bad["effective_decision"])
    after = copy.deepcopy(before)
    after["coordinator"]["effort"] = "high"
    ledger["settings_decisions"] = [{
        "id": "future-justifies-past", "state": "planned", "defect_class": None,
        "evidence_item_ids": [f"accepted-{number}" for number in range(1, 6)],
        "comparison_tuple": MODULE.comparison_tuple(ledger["considered_items"][1]),
        "settings_before": before, "settings_after": after,
        "changed_variable": "coordinator.effort", "pre_change_considered_sequence": 0,
        "change_parent_commit": BASE, "effective_commit": None,
        "affected_future_work": ["future implementation items"],
        "hypothesis": "reduce review rework", "observation_boundary": "five items",
        "rollback_condition": "lower first-review acceptance"
    }]
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "evidence occurs after pre-change boundary")
    MODULE.load_json = original

    bad = copy.deepcopy(pointer)
    add_items(bad, 5)
    ledger = bad["_test_ledger"]
    checkpoint(ledger, 5)
    first = decision(bad, ledger, "observing-one", state="observing")
    second = decision(bad, ledger, "observing-two", before=first["settings_after"])
    ledger["settings_decisions"] = [first, second]
    rejected_call(lambda: MODULE.validate_ledger(bad["cohorts"][0], ledger),
                  "prior settings experiment remains observing")

    snapshot = MODULE.route_snapshot(pointer["effective_decision"])
    rejected_call(lambda: MODULE.validate_inheritance(
        "successor", "baseline-01", snapshot, "adopted-route-01", snapshot),
        "did not inherit preceding effective decision")

    bad_snapshot = copy.deepcopy(snapshot)
    bad_snapshot["normal_active_worker_items"] = 3
    rejected_call(lambda: MODULE.validate_snapshot_shape(bad_snapshot, "worker norm"),
                  "unexpected fields")

    bad = copy.deepcopy(pointer)
    bad["effective_decision"].update({
        "id": "missing-decision", "state": "observing", "source_type": "decision",
        "source_commit": None, "source_cohort_id": bad["active_cohort_id"],
        "source_decision_id": "missing-decision"
    })
    rejected(bad, config, agents, "lack a recorded decision")

    bad = copy.deepcopy(pointer)
    add_items(bad, 9)
    ledger = bad["_test_ledger"]
    checkpoint(ledger, 5)
    bad["cohorts"][0]["state"] = "complete"
    successor = copy.deepcopy(bad["cohorts"][0])
    successor.update({"id": "successor", "state": "collecting"})
    bad["cohorts"].append(successor)
    bad["active_cohort_id"] = "successor"
    original = use_test_ledger(bad)
    rejected(bad, config, agents, "exactly ten accepted")
    MODULE.load_json = original

    bad_config = copy.deepcopy(config)
    bad_config["agents"]["max_concurrent_threads_per_session"] = 4
    rejected(pointer, bad_config, agents, "spawned-agent ceiling")

    print("workflow_improvement_refusals=pass cases=15")


if __name__ == "__main__":
    main()
