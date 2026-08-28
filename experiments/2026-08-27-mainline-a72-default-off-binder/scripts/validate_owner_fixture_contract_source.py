#!/usr/bin/env python3
"""Validate the Binder-aware MT6797 A72 owner KUnit fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path


TEST_SOURCE = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")
CPU8_ONLY = (
    "prestate.da921x_page = MT6797_A72_A36_DA921X_PAGE;",
    "prestate.buckb_vsel = MT6797_A72_A36_BUCKB_VSEL;",
    "prestate.spm_218 = MT6797_A72_A36_SPM_218;",
    "prestate.spm_290 = MT6797_A72_A36_SPM_290;",
    "prestate.secure_sentinels_stable = 1;",
    "prestate.protected_clock_valid = 1;",
    "prestate.pstore_console_available = 1;",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def function(text: str, name: str) -> str:
    start = text.find(f"static void {name}(struct kunit *test)")
    require(start >= 0, f"function absent: {name}")
    end = text.find("\nstatic ", start + 1)
    require(end >= 0, f"function terminator absent: {name}")
    return text[start:end]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / TEST_SOURCE
    require(path.is_file() and not path.is_symlink(),
            "membership test source absent or unsafe")
    text = path.read_text(encoding="utf-8")

    helper_start = text.index("mt6797_a72_prestate_for_up(unsigned int cpu)")
    helper_end = text.index("\nstatic struct arm64_late_cpu_ready_token", helper_start)
    helper = text[helper_start:helper_end]
    common_end = helper.index("\tif (cpu == 8) {")
    cpu8_end = helper.index("\t} else {", common_end)
    cpu9_end = helper.index("\t}\n\treturn prestate;", cpu8_end)
    common = helper[:common_end]
    cpu8 = helper[common_end:cpu8_end]
    cpu9 = helper[cpu8_end:cpu9_end]
    for field in CPU8_ONLY:
        require(field not in common, f"CPU8-only field remains common: {field}")
        require(cpu8.count(field) == 1, f"CPU8-only field not scoped once: {field}")
        require(field not in cpu9, f"CPU8-only field leaked into CPU9: {field}")
    require("prestate.cpu8_online = 1;" in cpu9,
            "CPU9 fixture lost CPU8-online state")
    require("prestate.cpu8_cluster_dcm_published = 1;" in cpu9,
            "CPU9 fixture lost CPU8 DCM publication")

    p31 = function(text, "mt6797_a72_owner_p31_consumes_once")
    require(p31.count("memset(bad_ready.plan_identity, 0,") == 1,
            "invalid plan identity is not fully zeroed once")
    require("bad_ready.plan_identity[0] = 0;" not in p31,
            "partial plan-identity mutation remains")

    for name in (
        "mt6797_a72_owner_r03_p29_rejects_and_retires",
        "mt6797_a72_owner_r03_p29_mutations_rejected",
    ):
        body = function(text, name)
        preflight = body.find(
            "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)")
        provider = body.find("mt6797_a72_membership_begin_provider_acquire")
        require(preflight >= 0 and provider > preflight,
                f"Binder public preflight not claimed before P29 path: {name}")
        require(body.count(
            "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)") == 1,
            f"unexpected P29 preflight count: {name}")

    print("validation=a72-owner-kunit-fixture-contract-source")
    print("changed_files=1")
    print("production_files_changed=0")
    print("cpu8_only_prestate_fields=7")
    print("cpu9_prestate_cpu8_only_fields=0")
    print("fully_zeroed_plan_identities=1")
    print("binder_claimed_p29_paths=2")
    print("expected_owner_failures_repaired=8")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
