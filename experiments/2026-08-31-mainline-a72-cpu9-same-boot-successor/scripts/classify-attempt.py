#!/usr/bin/env python3
"""Classify one exact same-boot CPU8-to-CPU9 controller attempt."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re


SOURCE_SHA256 = "4a17b7bf12beda716141884d6dae26c54d38a04dcd574c61e591e78d27a0dcdf"
VALIDATOR_SHA256 = "5bdf84f1ef47796a1e87f3208922f5ec5c088e48765138acef5e34764a6844c9"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-expected-pair-model-contract-repair"
    / "scripts/classify-attempt.py"
)
VALIDATOR = SCRIPT.with_name("validate-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")
if hashlib.sha256(VALIDATOR.read_bytes()).hexdigest() != VALIDATOR_SHA256:
    raise SystemExit("CPU9 pre-trigger validator changed")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


source = load("cpu8_parent_classifier", SOURCE)
PRE = load("cpu9_pretrigger", VALIDATOR)
Classification = source.Classification
BEGIN = source.BEGIN
END = source.END
COMMIT = source.COMMIT
TOKEN_SHA256 = source.TOKEN_SHA256
STATUS_PREFIX = source.STATUS_PREFIX
CPU9_STATUS_KEYS = (
    "cpu9_controller_consumed",
    "cpu9_operation_ret",
    "cpu9_failure_stage",
    "cpu9_derive_stage",
    "cpu9_binder_snapshot_ret",
    "cpu9_abi",
    "cpu9_lifecycle",
    "cpu9_terminal",
    "cpu9_last_stage",
    "cpu9_stage_errno",
    "cpu9_checkpoint_errno",
    "cpu9_attempted",
    "cpu9_membership_published",
    "cpu9_cpu_requests",
    "cpu9_cpu_off_requests",
    "cpu9_retries",
    "cpu9_retained_mask",
)
FAILURE_STAGES = {
    0: "none",
    1: "cpu8",
    2: "cpu8-proof",
    3: "ready-token",
    4: "derive",
    5: "publish",
    6: "prepare",
    7: "cpu9-request",
}
EXECUTOR_STAGES = {
    0: "none",
    1: "prestate",
    2: "cpu-on",
    3: "online-wait",
    4: "ipi",
    5: "membership",
}


def fields(section: str) -> dict[str, str]:
    return source.fields(section)


def combined_status(status: str) -> tuple[dict[str, str], dict[str, str]]:
    tokens = status.split()
    if not tokens or tokens[0] != STATUS_PREFIX:
        raise Classification("terminal-status-prefix-mismatch")
    pairs = []
    for token in tokens[1:]:
        if token.count("=") != 1:
            raise Classification("terminal-status-token-malformed")
        pairs.append(tuple(token.split("=", 1)))
    expected = tuple(source.STATUS_KEYS) + CPU9_STATUS_KEYS
    if tuple(key for key, _ in pairs) != expected:
        raise Classification("terminal-status-field-inventory-or-order-changed")
    values = dict(pairs)
    outer_cpu9_requests = values["cpu9_requests"]
    cpu9 = {key: values[key] for key in CPU9_STATUS_KEYS}
    for key, value in cpu9.items():
        pattern = r"0x[0-9a-f]+" if key == "cpu9_retained_mask" else r"-?\d+"
        if re.fullmatch(pattern, value) is None:
            raise Classification(f"terminal-field-malformed-{key}")

    base_pairs = []
    for key, value in pairs[: len(source.STATUS_KEYS)]:
        if key == "cpu9_requests":
            value = "0"
        base_pairs.append(f"{key}={value}")
    base = source.terminal_fields(STATUS_PREFIX + " " + " ".join(base_pairs))
    # The source classifier predates the controller's outer CPU9 request
    # counter and therefore validates a compatibility-normalized zero. Restore
    # the exact raw value after those inherited structural checks.
    base["cpu9_requests"] = outer_cpu9_requests
    return base, cpu9


def cpu_stat(value: str, cpu: int) -> tuple[int, ...]:
    if re.fullmatch(rf"cpu{cpu}(?: +[0-9]+){{10}}", value) is None:
        raise Classification(f"CPU{cpu}-accounting-sample-malformed")
    return tuple(int(field) for field in value.split()[1:])


def accounting_delta(observed: dict[str, str], cpu: int) -> int:
    first = cpu_stat(observed.get(f"cpu{cpu}_stat_first", ""), cpu)
    second = cpu_stat(observed.get(f"cpu{cpu}_stat_second", ""), cpu)
    if any(after < before for before, after in zip(first, second)):
        raise Classification(f"CPU{cpu}-accounting-counter-regressed")
    delta = sum(second) - sum(first)
    if delta <= 0:
        raise Classification(f"CPU{cpu}-accounting-did-not-advance")
    return delta


def cpu8_terminal_exact(status: dict[str, str], online: str | None) -> bool:
    expected = {
        "core_consumed": "1",
        "cpu_requests": "1",
        "binder_snapshot_ret": "0",
        # The source-pinned ABI-5 parser deliberately returns its ABI-4
        # compatibility-normalized view after validating the raw ABI-5 token.
        "binder_abi": "4",
        "lifecycle": "6",
        "terminal": "5",
        "last_stage": "10",
        "stage_errno": "0",
        "rollback_errno": "0",
        "checkpoint_errno": "0",
        "attempted": "1",
        "watchdog_armed": "1",
        "p27_owned": "1",
        "rollback_mask": "0x0",
        "retained_mask": "0x7",
    }
    return online in {"0-8", "0-9"} and all(
        status[key] == value for key, value in expected.items()
    )


def require_safety(status: dict[str, str], cpu9: dict[str, str]) -> None:
    if status["cpu_off_requests"] != "0" or status["retries"] != "0":
        raise Classification("CPU8-CPU_OFF-or-retry-nonzero")
    if cpu9["cpu9_cpu_off_requests"] != "0" or cpu9["cpu9_retries"] != "0":
        raise Classification("CPU9-CPU_OFF-or-retry-nonzero")
    if status["cpu_requests"] not in {"0", "1"}:
        raise Classification("CPU8-request-bound-exceeded")
    if status["cpu9_requests"] not in {"0", "1"}:
        raise Classification("CPU9-controller-request-bound-exceeded")
    if cpu9["cpu9_cpu_requests"] not in {"0", "1"}:
        raise Classification("CPU9-executor-request-bound-exceeded")
    if status["operation_ret"] != cpu9["cpu9_operation_ret"]:
        raise Classification("outer-and-CPU9-operation-result-disagree")


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    _, pretrigger_boot_id = PRE.classify(pretrigger)
    normalized = trigger.replace("\r", "")
    if normalized.count(COMMIT) != 1:
        raise Classification("exact-trigger-commit-absent-or-duplicated")
    if normalized.count(BEGIN) != 1:
        raise Classification("trigger-begin-absent-or-duplicated")
    after_begin = normalized[normalized.index(BEGIN) + len(BEGIN):]
    observed = fields(
        after_begin if END not in after_begin else after_begin[:after_begin.index(END)]
    )
    if observed.get("boot_id") != pretrigger_boot_id:
        raise Classification("trigger-boot-id-mismatch")
    if normalized.count(END) == 0:
        return (
            "trigger-boundary-transport-loss",
            "boot-bound-commit-observed-terminal-frame-absent",
        )
    if normalized.count(END) != 1 or normalized.index(END) < normalized.index(BEGIN):
        raise Classification("trigger-boundaries-invalid")

    expected = {
        "boot_id": pretrigger_boot_id,
        "pre_status": PRE.ARMED,
        "trigger_commit": "yes",
        "token_sha256": TOKEN_SHA256,
        "trigger_write_status": "0",
        "remount_ro_status": "0",
        "cpu9_request": "conditional-controller-one-shot",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
    }
    for key, value in expected.items():
        if observed.get(key) != value:
            raise Classification(f"{key}-mismatch")

    status, cpu9 = combined_status(observed.get("post_status", ""))
    require_safety(status, cpu9)
    if status["trigger_consumed"] != "1" or status["trigger_executions"] != "1":
        raise Classification("outer-trigger-not-exactly-once")
    online = observed.get("cpu_online")
    offline = observed.get("cpu_offline")
    if (online, offline) not in {("0-7", "8-9"), ("0-8", "9"), ("0-9", "")}:
        raise Classification("live-CPU-mask-outside-decision-set")

    failure = int(cpu9["cpu9_failure_stage"])
    if failure not in FAILURE_STAGES:
        raise Classification("CPU9-controller-failure-stage-out-of-range")
    last_stage = int(cpu9["cpu9_last_stage"])
    if last_stage not in EXECUTOR_STAGES:
        raise Classification("CPU9-executor-stage-out-of-range")

    if not cpu8_terminal_exact(status, online):
        if (
            cpu9["cpu9_controller_consumed"] != "1"
            or failure != 1
            or status["cpu9_requests"] != "0"
            or cpu9["cpu9_cpu_requests"] != "0"
            or online != "0-7"
            or offline != "8-9"
        ):
            raise Classification("CPU8-failure-and-CPU9-veto-inconsistent")
        return (
            "cpu8-failed-before-cpu9",
            f"operation-ret={status['operation_ret']}-CPU8-stage={status['failure_stage']}",
        )

    if cpu9["cpu9_controller_consumed"] != "1":
        raise Classification("CPU9-controller-not-consumed-after-CPU8-proof")
    if status["cpu9_requests"] == "0":
        if failure not in {2, 3, 4, 5, 6} or status["operation_ret"] == "0":
            raise Classification("CPU9-pre-request-result-inconsistent")
        if cpu9["cpu9_cpu_requests"] != "0" or (online, offline) != ("0-8", "9"):
            raise Classification("CPU9-pre-request-veto-or-CPU-mask-inconsistent")
        return (
            f"cpu9-pre-request-failure-{FAILURE_STAGES[failure]}",
            f"operation-ret={status['operation_ret']}-derive-stage={cpu9['cpu9_derive_stage']}",
        )

    success = {
        "cpu9_operation_ret": "0",
        "cpu9_failure_stage": "0",
        "cpu9_derive_stage": "9",
        "cpu9_binder_snapshot_ret": "0",
        "cpu9_abi": "1",
        "cpu9_lifecycle": "6",
        "cpu9_terminal": "3",
        "cpu9_last_stage": "5",
        "cpu9_stage_errno": "0",
        "cpu9_checkpoint_errno": "0",
        "cpu9_attempted": "1",
        "cpu9_membership_published": "1",
        "cpu9_cpu_requests": "1",
        "cpu9_cpu_off_requests": "0",
        "cpu9_retries": "0",
        "cpu9_retained_mask": "0x7",
    }
    if all(cpu9[key] == value for key, value in success.items()):
        if (online, offline) != ("0-9", ""):
            raise Classification("CPU9-terminal-proof-and-CPU-mask-disagree")
        cpu8_delta = accounting_delta(observed, 8)
        cpu9_delta = accounting_delta(observed, 9)
        return (
            "cpu8-cpu9-online-accounting-advanced",
            f"exact-dual-terminal-proof-CPU8-delta={cpu8_delta}-CPU9-delta={cpu9_delta}",
        )

    if failure != 7 or status["operation_ret"] == "0":
        raise Classification("CPU9-request-result-inconsistent")
    if cpu9["cpu9_binder_snapshot_ret"] not in {"0", "-11"}:
        raise Classification("CPU9-request-binder-snapshot-invalid")
    return (
        f"cpu9-request-failure-{EXECUTOR_STAGES[last_stage]}",
        "-".join(
            (
                f"operation-ret={status['operation_ret']}",
                f"terminal={cpu9['cpu9_terminal']}",
                f"stage-errno={cpu9['cpu9_stage_errno']}",
                f"checkpoint-errno={cpu9['cpu9_checkpoint_errno']}",
                f"online={online}",
            )
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", type=Path, required=True)
    parser.add_argument("--trigger", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, reason = classify(
            args.pretrigger.read_text(encoding="utf-8", errors="replace"),
            args.trigger.read_text(encoding="utf-8", errors="replace"),
        )
    except (Classification, PRE.Classification) as error:
        result, reason = "rejected", str(error)
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=1" if result != "rejected" else "trigger_attempts=unknown")
    print("cpu8_request_maximum=1")
    print("cpu9_request_maximum=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 0 if result != "rejected" else 3


if __name__ == "__main__":
    raise SystemExit(main())
