#!/usr/bin/env python3
"""Adversarial tests for the A72 secure CPU-off attribution audit."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Callable


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().with_name("validate_audit.py")
SPEC = importlib.util.spec_from_file_location("a72_secure_off_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("error: cannot load audit validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def mutate(rows: list[dict[str, str]], identifier: str, **changes: str) -> None:
    for row in rows:
        if row["id"] == identifier:
            row.update(changes)
            return
    raise AssertionError(f"missing row {identifier}")


def expect_rejected(label: str, expected: str, action: Callable[[], None]) -> None:
    try:
        action()
    except VALIDATOR.AuditError as error:
        if expected not in str(error):
            raise AssertionError(
                f"wrong rejection for {label}: expected {expected!r}, got {error!s}"
            ) from error
        return
    raise AssertionError(f"mutation accepted: {label}")


def check_rows(
    label: str,
    expected: str,
    source: list[dict[str, str]],
    validator: Callable[[list[dict[str, str]]], None],
    identifier: str,
    **changes: str,
) -> None:
    rows = copy.deepcopy(source)
    mutate(rows, identifier, **changes)
    expect_rejected(label, expected, lambda: validator(rows))


def main() -> int:
    callgraph = VALIDATOR.load_tsv(VALIDATOR.CALLGRAPH, VALIDATOR.CALLGRAPH_FIELDS)
    effects = VALIDATOR.load_tsv(VALIDATOR.EFFECTS, VALIDATOR.EFFECT_FIELDS)
    readme = VALIDATOR.README.read_text(encoding="utf-8")
    VALIDATOR.validate_callgraph(callgraph)
    VALIDATOR.validate_effects(effects)
    VALIDATOR.validate_readme(readme)

    mutations: list[Callable[[], None]] = [
        lambda: check_rows(
            "passive-affinity", "AFFINITY_INFO was made passive", callgraph,
            VALIDATOR.validate_callgraph, "CG10", semantic="passive-query"),
        lambda: check_rows(
            "bounded-affinity", "AFFINITY_INFO was falsely bounded", callgraph,
            VALIDATOR.validate_callgraph, "CG10", bounded="10x10ms"),
        lambda: check_rows(
            "unscoped-active-affinity", "AFFINITY_INFO active target gate changed", callgraph,
            VALIDATOR.validate_callgraph, "CG10", gate="always"),
        lambda: check_rows(
            "query-count-replay", "query count replaced the private replay gate", callgraph,
            VALIDATOR.validate_callgraph, "CG10", replay_control="single-query"),
        lambda: check_rows(
            "missing-big-on-replay", "hardware replay gate changed", callgraph,
            VALIDATOR.validate_callgraph, "CG11", replay_control="query-count"),
        lambda: check_rows(
            "retained-cpu-observer", "retained CPU8 AFFINITY_INFO prohibition missing", callgraph,
            VALIDATOR.validate_callgraph, "CG15", replay_control="safe-on-observer"),
        lambda: check_rows(
            "already-off-oracle", "already-off AFFINITY_INFO was promoted", callgraph,
            VALIDATOR.validate_callgraph, "CG16", bounded="bounded-readback"),
        lambda: check_rows(
            "wrong-cpu9-pwr-con", "CPU9 PWR_CON effect changed", effects,
            VALIDATOR.validate_effects, "EF07", target="0x10006240"),
        lambda: check_rows(
            "missing-diagnostic", "CPU9 diagnostic effect changed", effects,
            VALIDATOR.validate_effects, "EF05", action="read-only"),
        lambda: check_rows(
            "empty-shared-set", "CPU9 shared/private write subset was falsely made empty", effects,
            VALIDATOR.validate_effects, "EF12", action="empty-write-set"),
        lambda: check_rows(
            "cpu9-cluster-write", "CPU9 retained branch gained a cluster effect", effects,
            VALIDATOR.validate_effects, "EF11", action="cluster-power-off"),
        lambda: check_rows(
            "bounded-cpu9-wfi", "CPU9 WFI wait changed", effects,
            VALIDATOR.validate_effects, "EF06", wait="bounded-100ms"),
        lambda: check_rows(
            "extra-cpu9-unbounded-wait", "CPU9 retained unbounded-wait inventory changed", effects,
            VALIDATOR.validate_effects, "EF05", wait="unbounded-no-timeout"),
        lambda: check_rows(
            "hidden-cpu9-cluster-effect", "CPU9 retained row has a non-allowlisted effect scope: EF03", effects,
            VALIDATOR.validate_effects, "EF03", scope="cluster-power"),
        lambda: check_rows(
            "hidden-cpu9-clock-effect", "CPU9 retained row has a non-allowlisted effect scope: EF03", effects,
            VALIDATOR.validate_effects, "EF03", action="rmw-clear-bit0", scope="clock"),
        lambda: check_rows(
            "missing-isolation", "last-core external-isolation write missing", effects,
            VALIDATOR.validate_effects, "EF39", action="no-write"),
        lambda: check_rows(
            "invented-dcm-write", "negative direct-callgraph finding changed in EF41", effects,
            VALIDATOR.validate_effects, "EF41", action="rmw-clear-mask"),
        lambda: check_rows(
            "invented-sram-write", "negative direct-callgraph finding changed in EF42", effects,
            VALIDATOR.validate_effects, "EF42", action="disable"),
        lambda: check_rows(
            "bounded-last-core-wait", "last-core unbounded-wait inventory changed", effects,
            VALIDATOR.validate_effects, "EF38", wait="bounded"),
        lambda: check_rows(
            "local-mp2-status-address", "MP2 CCI global change-pending poll changed", effects,
            VALIDATOR.validate_effects, "EF24", target="0x1039600c"),
        lambda: expect_rejected(
            "payload-identity", "private payload identity changed",
            lambda: VALIDATOR.validate_readme(readme.replace(VALIDATOR.PAYLOAD_SHA256, "0" * 64))),
        lambda: expect_rejected(
            "cpu-off-authorized", "authorization marker missing: cpu_off_authorized=no",
            lambda: VALIDATOR.validate_readme(
                readme.replace("cpu_off_authorized=no", "cpu_off_authorized=yes"))),
        lambda: expect_rejected(
            "private-path", "private path or image name published: /home/",
            lambda: VALIDATOR.validate_readme(readme + "\n/home/private/image\n")),
    ]

    for mutation in mutations:
        mutation()

    print("validation=a72-secure-cpu-off-attribution-mutations")
    print("result=PASS")
    print(f"mutations_rejected={len(mutations)}")
    print("retained_cpu_affinity_info=forbidden")
    print("cpu_off_authorized=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
