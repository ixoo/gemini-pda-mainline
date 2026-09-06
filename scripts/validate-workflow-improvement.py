#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Validate recurring workflow cohorts and their effective Codex settings."""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POINTER = ROOT / "project/workflow-improvement.json"
CONFIG = ROOT / ".codex/config.toml"
AGENTS = ROOT / ".codex/agents"
ROUTE_LABELS = ("coordinator", "executor", "implementer", "specialist")
WORK_TYPES = {"execution", "implementation", "reasoning", "integration"}
RISKS = {"routine", "cross-file", "hard-uncertainty"}
DECISION_STATES = {"planned", "observing", "adopted", "reverted", "inconclusive"}
CHECKPOINT_TRIGGERS = {"interval", "early-signal", "cohort-close"}
CHECKPOINT_CONCLUSIONS = {"no-change", "change-proposed", "too-small", "retain",
                          "rollback", "inconclusive"}
IMMEDIATE_DEFECTS = {"safety", "publication", "provenance", "scope-containment"}
EXCLUSION_REASONS = {"cohort-bootstrap", "device-session", "build-only", "review-only",
                     "pre-cohort", "abandoned", "missing-contract", "other"}
COMMIT = re.compile(r"[0-9a-f]{40}")
INITIAL_BASELINE_COMMIT = "63919a7ca33d1a0f5f6b5eaef9f33c58e79ec808"


class ValidationError(RuntimeError):
    """A workflow cohort, decision or effective setting is inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(
        ValueError(f"non-finite JSON number: {value}")))


def repo_file(name: str, label: str) -> Path:
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(),
            f"{label} is missing or escapes repository")
    return path


def git_text(commit: str, name: str) -> str:
    require(COMMIT.fullmatch(commit) is not None, f"invalid commit id for {name}")
    result = subprocess.run(["git", "show", f"{commit}:{name}"], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(result.returncode == 0, f"{name} is unavailable at baseline commit")
    return result.stdout


def route_snapshot(decision: dict) -> dict:
    snapshot = {label: decision[label] for label in ROUTE_LABELS}
    snapshot["maximum_spawned_agent_threads_excluding_primary"] = \
        decision["maximum_spawned_agent_threads_excluding_primary"]
    return snapshot


def comparison_tuple(item: dict) -> dict:
    return {
        "work_type": item["work_type"],
        "risk_class": item["risk_class"],
        "acceptance_contract": item["acceptance_contract"],
        "review_route": item["review_route"],
    }


def flatten(value: object, prefix: str = "") -> dict[str, object]:
    if not isinstance(value, dict):
        return {prefix: value}
    output: dict[str, object] = {}
    for key in sorted(value):
        name = f"{prefix}.{key}" if prefix else key
        output.update(flatten(value[key], name))
    return output


def validate_snapshot_shape(snapshot: dict, label: str) -> None:
    expected = set(ROUTE_LABELS) | {"maximum_spawned_agent_threads_excluding_primary"}
    require(isinstance(snapshot, dict) and set(snapshot) == expected,
            f"{label}: settings snapshot has unexpected fields")
    for route_label in ROUTE_LABELS:
        route = snapshot[route_label]
        require(isinstance(route, dict) and set(route) == {"role", "model", "effort"} and
                all(isinstance(route[key], str) and route[key]
                    for key in ("role", "model", "effort")),
                f"{label}: invalid {route_label} route")
    for field in ("maximum_spawned_agent_threads_excluding_primary",):
        require(isinstance(snapshot[field], int) and not isinstance(snapshot[field], bool),
                f"{label}: {field} must be an integer")


def validate_route_snapshot(snapshot: dict, config: dict, agents: dict[str, dict],
                            label: str) -> None:
    validate_snapshot_shape(snapshot, label)
    for route_label in ROUTE_LABELS:
        route = snapshot.get(route_label, {})
        require(all(isinstance(route.get(key), str) and route[key]
                    for key in ("role", "model", "effort")),
                f"{label}: incomplete {route_label} route")
        agent = agents.get(route["role"], {})
        require(agent.get("model") == route["model"] and
                agent.get("model_reasoning_effort") == route["effort"],
                f"{label}: {route['role']} agent file differs from effective decision")
    require(config.get("model") == snapshot["coordinator"]["model"],
            f"{label}: coordinator model differs from effective decision")
    require(config.get("model_reasoning_effort") == snapshot["coordinator"]["effort"],
            f"{label}: coordinator effort differs from effective decision")
    require(config["agents"]["default_subagent_model"] == snapshot["executor"]["model"],
            f"{label}: default worker model differs from effective decision")
    require(config["agents"]["default_subagent_reasoning_effort"] ==
            snapshot["executor"]["effort"],
            f"{label}: default worker effort differs from effective decision")
    ceiling = snapshot["maximum_spawned_agent_threads_excluding_primary"]
    require(isinstance(ceiling, int) and not isinstance(ceiling, bool) and ceiling > 0,
            f"{label}: invalid spawned-agent ceiling")
    require(config["agents"]["max_concurrent_threads_per_session"] == ceiling,
            f"{label}: spawned-agent ceiling differs from effective decision")


def validate_baseline(decision: dict) -> None:
    commit = decision["source_commit"]
    require(commit == INITIAL_BASELINE_COMMIT,
            "baseline-01 source commit differs from the frozen initial baseline")
    historical_config = tomllib.loads(git_text(commit, ".codex/config.toml"))
    historical_agents = {
        route["role"]: tomllib.loads(git_text(commit, f".codex/agents/{route['role']}.toml"))
        for route in (decision[label] for label in ROUTE_LABELS)
    }
    validate_route_snapshot(route_snapshot(decision), historical_config, historical_agents,
                            "baseline anchor")


def validate_snapshot_at_commit(snapshot: dict, commit: str, label: str) -> None:
    historical_config = tomllib.loads(git_text(commit, ".codex/config.toml"))
    historical_agents = {
        snapshot[name]["role"]:
            tomllib.loads(git_text(commit, f".codex/agents/{snapshot[name]['role']}.toml"))
        for name in ROUTE_LABELS
    }
    validate_route_snapshot(snapshot, historical_config, historical_agents, label)


def validate_number(value: object, label: str) -> None:
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(value) and value >= 0, f"{label} must be finite and non-negative")


def validate_inheritance(cohort_id: str, baseline_id: str, settings: dict,
                         expected_id: str, expected_settings: dict | None) -> None:
    require(baseline_id == expected_id,
            f"{cohort_id}: successor did not inherit preceding effective decision")
    if expected_settings is not None:
        require(settings == expected_settings,
                f"{cohort_id}: settings baseline differs from preceding cohort")


def timestamp(value: object, label: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{label} must be UTC ISO-8601")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValidationError(f"{label} must be UTC ISO-8601") from error


def validate_accepted(item: dict, expected_sequence: int) -> None:
    item_id = item["candidate_id"]
    require(item.get("accepted_sequence") == expected_sequence,
            f"{item_id}: non-contiguous accepted sequence")
    require(item.get("offline_eligible") is True, f"{item_id}: item is not offline eligible")
    require(item.get("work_type") in WORK_TYPES, f"{item_id}: invalid work_type")
    require(item.get("risk_class") in RISKS, f"{item_id}: invalid risk_class")
    require(isinstance(item.get("acceptance_contract"), str) and item["acceptance_contract"],
            f"{item_id}: acceptance contract is required")
    require(isinstance(item.get("parent"), str) and COMMIT.fullmatch(item["parent"]) is not None,
            f"{item_id}: parent must be a full commit id")
    git_text(item["parent"], "AGENTS.md")
    for route_name in ("owner_route", "review_route"):
        route = item.get(route_name, {})
        require(all(isinstance(route.get(key), str) and route[key]
                    for key in ("role", "model", "effort")),
                f"{item_id}: incomplete {route_name}")
    result = item.get("result", {})
    require(isinstance(result.get("first_review_accepted"), bool),
            f"{item_id}: first_review_accepted must be boolean")
    for name in ("rework_cycles", "elapsed_minutes", "review_rework_minutes"):
        validate_number(result.get(name), f"{item_id}: {name}")
    started = timestamp(result.get("started_at"), f"{item_id}: started_at")
    review_ready = timestamp(result.get("review_ready_at"), f"{item_id}: review_ready_at")
    accepted_at = timestamp(result.get("accepted_at"), f"{item_id}: accepted_at")
    require(started <= review_ready <= accepted_at, f"{item_id}: timestamps are unordered")
    elapsed = (accepted_at - started).total_seconds() / 60
    require(abs(elapsed - result["elapsed_minutes"]) < 0.01,
            f"{item_id}: elapsed minutes disagree with timestamps")
    require(result["review_rework_minutes"] <= result["elapsed_minutes"],
            f"{item_id}: review/rework time exceeds elapsed time")
    require(isinstance(result.get("timing_source"), str) and result["timing_source"],
            f"{item_id}: timing source is required")
    require(isinstance(result.get("escalated"), bool), f"{item_id}: escalated must be boolean")
    reason = result.get("escalation_reason")
    packet = result.get("escalation_packet")
    if result["escalated"]:
        require(isinstance(reason, str) and reason, f"{item_id}: escalation reason is required")
        require(isinstance(packet, dict), f"{item_id}: escalation packet is required")
        repo_file(packet.get("evidence", ""), f"{item_id}: escalation evidence")
        require(isinstance(packet.get("attempts"), list) and packet["attempts"] and
                all(isinstance(value, str) and value for value in packet["attempts"]),
                f"{item_id}: escalation attempts are required")
        for field in ("unresolved_question", "next_discriminating_check"):
            require(isinstance(packet.get(field), str) and packet[field],
                    f"{item_id}: escalation {field} is required")
    else:
        require(reason is None and packet is None,
                f"{item_id}: non-escalated item contains escalation data")
    failure_class = result.get("review_failure_class")
    require(failure_class is None or failure_class in IMMEDIATE_DEFECTS,
            f"{item_id}: invalid review failure class")
    credits = result.get("measured_credits")
    source = result.get("credit_source")
    unit = result.get("credit_unit")
    if credits is None:
        require(source == "unavailable" and unit is None,
                f"{item_id}: unavailable credits need null unit")
    else:
        validate_number(credits, f"{item_id}: measured credits")
        require(isinstance(source, str) and source != "unavailable" and
                isinstance(unit, str) and unit,
                f"{item_id}: measured credits require source and unit")
    repo_file(result.get("accepted_evidence", ""), f"{item_id}: accepted evidence")


def validate_checkpoint(checkpoint: dict, accepted_by_id: dict[str, dict],
                        accepted_count: int, considered_count: int) -> None:
    checkpoint_id = checkpoint["id"]
    require(checkpoint.get("trigger") in CHECKPOINT_TRIGGERS,
            f"{checkpoint_id}: invalid checkpoint trigger")
    require(checkpoint.get("conclusion") in CHECKPOINT_CONCLUSIONS,
            f"{checkpoint_id}: invalid checkpoint conclusion")
    accepted_at = checkpoint.get("after_accepted_sequence")
    considered_at = checkpoint.get("after_considered_sequence")
    require(isinstance(accepted_at, int) and 0 <= accepted_at <= accepted_count,
            f"{checkpoint_id}: invalid accepted boundary")
    require(isinstance(considered_at, int) and 0 <= considered_at <= considered_count,
            f"{checkpoint_id}: invalid considered boundary")
    for field in ("trigger_item_ids", "comparable_item_ids"):
        values = checkpoint.get(field)
        require(isinstance(values, list) and values and len(values) == len(set(values)) and
                set(values) <= set(accepted_by_id), f"{checkpoint_id}: invalid {field}")
        require(all(accepted_by_id[item_id]["accepted_sequence"] <= accepted_at and
                    accepted_by_id[item_id]["considered_sequence"] <= considered_at
                    for item_id in values),
                f"{checkpoint_id}: {field} occurs after checkpoint boundary")
    if checkpoint["trigger"] == "interval":
        require(accepted_at == 5, f"{checkpoint_id}: interval checkpoint must close item five")
    if checkpoint["trigger"] == "cohort-close":
        require(accepted_at == 10, f"{checkpoint_id}: close checkpoint must close item ten")
    repo_file(checkpoint.get("evidence", ""), f"{checkpoint_id}: checkpoint evidence")


def validate_decision(decision: dict, accepted_by_id: dict[str, dict],
                      considered_count: int) -> None:
    decision_id = decision["id"]
    require(decision.get("state") in DECISION_STATES, f"{decision_id}: invalid state")
    evidence = decision.get("evidence_item_ids", [])
    require(isinstance(evidence, list) and evidence and len(evidence) == len(set(evidence)) and
            set(evidence) <= set(accepted_by_id), f"{decision_id}: unknown evidence item")
    defect = decision.get("defect_class")
    require(defect is None or defect in IMMEDIATE_DEFECTS, f"{decision_id}: invalid defect class")
    require(len(evidence) >= 5 or defect in IMMEDIATE_DEFECTS,
            f"{decision_id}: insufficient comparable evidence")
    declared = decision.get("comparison_tuple")
    require(isinstance(declared, dict), f"{decision_id}: comparison tuple is required")
    require(all(comparison_tuple(accepted_by_id[item_id]) == declared for item_id in evidence),
            f"{decision_id}: evidence is not comparable")
    before = decision.get("settings_before")
    after = decision.get("settings_after")
    require(isinstance(before, dict) and isinstance(after, dict),
            f"{decision_id}: before/after settings are required")
    validate_snapshot_shape(before, f"{decision_id}: before settings")
    validate_snapshot_shape(after, f"{decision_id}: after settings")
    before_flat = flatten(before)
    after_flat = flatten(after)
    changed = [key for key in sorted(set(before_flat) | set(after_flat))
               if before_flat.get(key) != after_flat.get(key)]
    require(changed == [decision.get("changed_variable")],
            f"{decision_id}: exactly the declared setting must change")
    require(isinstance(decision.get("pre_change_considered_sequence"), int) and
            0 <= decision["pre_change_considered_sequence"] <= considered_count,
            f"{decision_id}: invalid pre-change sequence")
    require(max(accepted_by_id[item_id]["considered_sequence"] for item_id in evidence) <=
            decision["pre_change_considered_sequence"],
            f"{decision_id}: evidence occurs after pre-change boundary")
    require(isinstance(decision.get("affected_future_work"), list) and
            decision["affected_future_work"] and
            all(isinstance(value, str) and value for value in decision["affected_future_work"]),
            f"{decision_id}: affected future work is required")
    for field in ("hypothesis", "observation_boundary", "rollback_condition"):
        require(isinstance(decision.get(field), str) and decision[field],
                f"{decision_id}: missing {field}")
    change_parent = decision.get("change_parent_commit", "")
    git_text(change_parent, "AGENTS.md")
    validate_snapshot_at_commit(before, change_parent,
                                f"{decision_id}: change-parent settings")
    effective_commit = decision.get("effective_commit")
    if decision["state"] == "adopted":
        git_text(effective_commit or "", "AGENTS.md")
        validate_snapshot_at_commit(after, effective_commit,
                                    f"{decision_id}: effective settings")
    else:
        require(effective_commit is None or COMMIT.fullmatch(effective_commit) is not None,
                f"{decision_id}: invalid effective commit")


def validate_ledger(cohort: dict, ledger: dict) -> tuple[
        dict[str, dict], dict[str, dict], dict, str, bool, set[str]]:
    require(ledger.get("schema_version") == 1, f"{cohort['id']}: unsupported ledger schema")
    require(cohort["id"] == ledger["cohort_id"], f"{cohort['id']}: ledger id mismatch")
    require(cohort["baseline_commit"] == ledger["baseline_commit"],
            f"{cohort['id']}: baseline mismatch")
    require(cohort["baseline_decision_id"] == ledger["baseline_decision_id"],
            f"{cohort['id']}: baseline decision mismatch")
    require(isinstance(ledger.get("settings_baseline"), dict),
            f"{cohort['id']}: settings baseline is required")
    validate_snapshot_at_commit(ledger["settings_baseline"], ledger["baseline_commit"],
                                f"{cohort['id']}: settings baseline")
    if ledger["baseline_decision_id"] == "baseline-01":
        require(ledger["baseline_commit"] == INITIAL_BASELINE_COMMIT,
                f"{cohort['id']}: initial baseline is not frozen")
    require(ledger["target_accepted_offline_items"] == 10, "pilot target must remain ten")
    require(ledger["checkpoint_interval"] == 5, "checkpoint interval must remain five")
    require(ledger["rolling_window_after_pilot"] == 10, "rolling window must remain ten")

    candidate_ids: set[str] = set()
    accepted_by_id: dict[str, dict] = {}
    accepted_sequence = 0
    for considered_sequence, item in enumerate(ledger["considered_items"], 1):
        candidate_id = item.get("candidate_id")
        require(item.get("considered_sequence") == considered_sequence,
                f"considered item {considered_sequence}: non-contiguous sequence")
        require(isinstance(candidate_id, str) and candidate_id and candidate_id not in candidate_ids,
                f"considered item {considered_sequence}: missing or duplicate candidate id")
        candidate_ids.add(candidate_id)
        disposition = item.get("disposition")
        require(disposition in {"accepted", "excluded"}, f"{candidate_id}: invalid disposition")
        if disposition == "accepted":
            accepted_sequence += 1
            validate_accepted(item, accepted_sequence)
            accepted_by_id[candidate_id] = item
        else:
            require("accepted_sequence" not in item, f"{candidate_id}: excluded item is accepted")
            require(item.get("reason") in EXCLUSION_REASONS,
                    f"{candidate_id}: invalid exclusion reason")
            require(isinstance(item.get("note"), str) and item["note"],
                    f"{candidate_id}: exclusion note is required")
            repo_file(item.get("evidence", ""), f"{candidate_id}: exclusion evidence")
    require(ledger["accepted_count"] == accepted_sequence, "accepted_count does not match stream")
    require(ledger["next_accepted_sequence"] == accepted_sequence + 1,
            "next accepted sequence is not contiguous")
    require(ledger["next_considered_sequence"] == len(ledger["considered_items"]) + 1,
            "next considered sequence is not contiguous")
    require(accepted_sequence <= 10, "cohort exceeds ten accepted items")

    checkpoint_ids: set[str] = set()
    checkpoints = ledger["checkpoints"]
    previous_boundary = (-1, -1)
    for checkpoint in checkpoints:
        checkpoint_id = checkpoint.get("id")
        require(isinstance(checkpoint_id, str) and checkpoint_id and
                checkpoint_id not in checkpoint_ids, "checkpoint has missing or duplicate id")
        checkpoint_ids.add(checkpoint_id)
        validate_checkpoint(checkpoint, accepted_by_id, accepted_sequence,
                            len(ledger["considered_items"]))
        boundary = (checkpoint["after_considered_sequence"],
                    checkpoint["after_accepted_sequence"])
        require(boundary[0] >= previous_boundary[0] and
                boundary[1] >= previous_boundary[1],
                "checkpoint boundaries are not monotonic")
        previous_boundary = boundary
    if accepted_sequence >= 5:
        require(any(checkpoint["trigger"] == "interval" and
                    checkpoint["after_accepted_sequence"] == 5 for checkpoint in checkpoints),
                "missing required item-five checkpoint")
    if cohort["state"] == "complete":
        require(accepted_sequence == 10, "completed cohort must contain exactly ten accepted items")
        require(any(checkpoint["trigger"] == "cohort-close" and
                    checkpoint["after_accepted_sequence"] == 10 for checkpoint in checkpoints),
                "completed cohort lacks item-ten close checkpoint")
    else:
        require(cohort["state"] == "collecting" and accepted_sequence < 10,
                "collecting cohort must have fewer than ten accepted items")

    def covered(item_ids: set[str], sequence: int) -> bool:
        return any(checkpoint["trigger"] == "early-signal" and
                   checkpoint["after_accepted_sequence"] >= sequence and
                   item_ids <= set(checkpoint["trigger_item_ids"])
                   for checkpoint in checkpoints)

    last_by_comparison: dict[str, dict] = {}
    escalations: dict[tuple[str, str], dict] = {}
    for item in accepted_by_id.values():
        key = json.dumps(comparison_tuple(item), sort_keys=True)
        result = item["result"]
        previous = last_by_comparison.get(key)
        if previous and not previous["result"]["first_review_accepted"] and \
                not result["first_review_accepted"]:
            require(covered({previous["candidate_id"], item["candidate_id"]},
                            item["accepted_sequence"]), "unreviewed consecutive review misses")
        last_by_comparison[key] = item
        if result["escalated"]:
            escalation_key = (key, result["escalation_reason"])
            previous = escalations.get(escalation_key)
            if previous:
                require(covered({previous["candidate_id"], item["candidate_id"]},
                                item["accepted_sequence"]), "unreviewed repeated escalation")
            escalations[escalation_key] = item
        if result["review_failure_class"] in IMMEDIATE_DEFECTS:
            require(covered({item["candidate_id"]}, item["accepted_sequence"]),
                    "unreviewed immediate failure class")

    decisions: dict[str, dict] = {}
    current_settings = ledger["settings_baseline"]
    current_decision_id = ledger["baseline_decision_id"]
    observing = False
    for decision in ledger["settings_decisions"]:
        decision_id = decision.get("id")
        require(isinstance(decision_id, str) and decision_id and decision_id not in decisions,
                "settings decision has missing or duplicate id")
        require(not observing,
                f"{decision_id}: prior settings experiment remains observing")
        validate_decision(decision, accepted_by_id, len(ledger["considered_items"]))
        require(decision["settings_before"] == current_settings,
                f"{decision_id}: before settings do not continue the cohort chain")
        if decision["state"] in {"observing", "adopted"}:
            current_settings = decision["settings_after"]
            current_decision_id = decision_id
        observing = decision["state"] == "observing"
        decisions[decision_id] = decision
    require(cohort["state"] != "complete" or not observing,
            f"{cohort['id']}: completed cohort retains an observing experiment")
    return (accepted_by_id, decisions, current_settings, current_decision_id,
            observing, candidate_ids)


def validate(pointer: dict, config: dict, agents: dict[str, dict]) -> None:
    require(pointer.get("schema_version") == 1, "unsupported pointer schema_version")
    cohorts = pointer["cohorts"]
    require(isinstance(cohorts, list) and cohorts, "at least one cohort is required")
    cohort_ids: set[str] = set()
    all_decisions: dict[tuple[str, str], dict] = {}
    global_candidate_ids: set[str] = set()
    global_decision_ids: set[str] = set()
    active = None
    expected_baseline_id = "baseline-01"
    expected_settings = None
    terminal_decision_id = "baseline-01"
    terminal_settings = None
    terminal_observing = False
    for cohort_index, cohort in enumerate(cohorts):
        cohort_id = cohort.get("id")
        require(isinstance(cohort_id, str) and cohort_id and cohort_id not in cohort_ids,
                "cohort has missing or duplicate id")
        cohort_ids.add(cohort_id)
        repo_file(cohort["record"], f"{cohort_id}: record")
        ledger = load_json(repo_file(cohort["ledger"], f"{cohort_id}: ledger"))
        (_, decisions, cohort_terminal_settings, cohort_terminal_id,
         cohort_observing, candidate_ids) = validate_ledger(cohort, ledger)
        require(global_candidate_ids.isdisjoint(candidate_ids),
                f"{cohort_id}: candidate identity reused across cohorts")
        global_candidate_ids.update(candidate_ids)
        require(global_decision_ids.isdisjoint(decisions),
                f"{cohort_id}: decision identity reused across cohorts")
        global_decision_ids.update(decisions)
        baseline_id = cohort["baseline_decision_id"]
        validate_inheritance(cohort_id, baseline_id, ledger["settings_baseline"],
                             expected_baseline_id, expected_settings)
        all_decisions.update({(cohort_id, decision_id): decision
                              for decision_id, decision in decisions.items()})
        terminal_decision_id = cohort_terminal_id
        terminal_settings = cohort_terminal_settings
        terminal_observing = cohort_observing
        expected_baseline_id = cohort_terminal_id
        expected_settings = cohort_terminal_settings
        if cohort_id == pointer["active_cohort_id"]:
            active = cohort
            require(cohort_index == len(cohorts) - 1,
                    "active collecting cohort must be the last registered cohort")
    require(active is not None and active["state"] == "collecting",
            "active cohort must name one collecting cohort")
    require(sum(cohort["state"] == "collecting" for cohort in cohorts) == 1,
            "exactly one cohort must be collecting")

    effective = pointer["effective_decision"]
    require(effective.get("normal_active_worker_items") == 2,
            "two-worker staffing norm changed through runtime settings")
    snapshot = route_snapshot(effective)
    source_type = effective.get("source_type")
    if source_type == "baseline":
        require(effective.get("id") == "baseline-01" and effective.get("state") == "retained",
                "baseline effective decision identity changed")
        require(effective.get("source_cohort_id") is None and
                effective.get("source_decision_id") is None,
                "baseline decision must not cite a cohort decision")
        validate_baseline(effective)
    else:
        require(source_type == "decision", "invalid effective decision source")
        source = (effective.get("source_cohort_id"), effective.get("source_decision_id"))
        decision = all_decisions.get(source)
        require(decision is not None, "effective settings lack a recorded decision")
        require(decision["state"] in {"observing", "adopted"},
                "effective settings cite a non-effective decision")
        require(snapshot == decision["settings_after"],
                "effective settings differ from adopted decision")
        require(effective["id"] == decision["id"] and
                effective["state"] == decision["state"],
                "effective decision metadata mismatch")
    require(effective["id"] == terminal_decision_id and snapshot == terminal_settings,
            "live effective decision does not match active cohort chain")
    require((effective["state"] == "observing") == terminal_observing,
            "live observing state does not match active cohort chain")
    validate_route_snapshot(snapshot, config, agents, "live settings")


def main() -> None:
    pointer = load_json(POINTER)
    config = tomllib.loads(CONFIG.read_text())
    agents = {path.stem: tomllib.loads(path.read_text()) for path in AGENTS.glob("*.toml")}
    validate(pointer, config, agents)
    active = pointer["active_cohort_id"]
    ledger_path = next(cohort["ledger"] for cohort in pointer["cohorts"]
                       if cohort["id"] == active)
    ledger = load_json(repo_file(ledger_path, "active ledger"))
    print(f"workflow_improvement=pass cohort={active} "
          f"considered_items={len(ledger['considered_items'])} "
          f"accepted_items={ledger['accepted_count']} decisions={len(ledger['settings_decisions'])}")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
