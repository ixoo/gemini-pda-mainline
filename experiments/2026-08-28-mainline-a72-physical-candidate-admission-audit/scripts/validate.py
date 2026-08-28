#!/usr/bin/env python3
"""Validate the exact CPU8 physical-candidate admission audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXP = Path(__file__).resolve().parent.parent
ROOT = EXP.parents[1]
CONTRACT = json.loads((EXP / "contract.json").read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


require(CONTRACT["schema"] == 2, "schema")
require(CONTRACT["experiment"] == EXP.name, "experiment")
series = ROOT / "patches/series"
manifest = ROOT / "kernel/manifest.json"
require(len(series.read_text(encoding="utf-8").splitlines()) ==
        CONTRACT["integrated_canonical_series_entries"], "series entries")
require(sha256(series) == CONTRACT["integrated_canonical_series_sha256"],
        "series hash")
require(sha256(manifest) == CONTRACT["integrated_manifest_sha256"],
        "manifest hash")
require(CONTRACT["audited_canonical_series_entries"] == 398,
        "audited series entries")
require(CONTRACT["integrated_canonical_series_entries"] == 404,
        "integrated series entries")
require(CONTRACT["integrated_profile"] == "a72-admission-controller-kunit",
        "integrated profile")

direct = CONTRACT["direct_design"]
require(direct == {
    "binder_dt_enable": True,
    "late_add_cpu8": True,
    "safe": False,
    "reason": "unsourced-a36-and-ledger-watchdog-order-cycle",
}, "direct design rejection")
require(set(CONTRACT["external_production_callers"]) == {
    "publish_bootstrap", "membership_begin_up", "membership_derive_cpu8",
    "membership_publish_up", "add_cpu8",
}, "external caller inventory")
require(CONTRACT["external_production_callers"] == {
    "publish_bootstrap": 0,
    "membership_begin_up": 0,
    "membership_derive_cpu8": 1,
    "membership_publish_up": 1,
    "add_cpu8": 1,
}, "controller production caller inventory")
require(CONTRACT["obsolete_a36_caller_assertions"] == [
    "da921x_page", "secure_sentinels_stable", "pstore_console_available",
    "watchdog_owned",
], "obsolete A36 assertions")
require(CONTRACT["required_order"] == [
    "exact-source-capture", "a34-bootstrap-publication",
    "owner-derived-cpu8-transaction", "p17-p18-publication",
    "one-add-cpu8", "retained-ledger-begin", "watchdog-takeover",
    "p27-first-mutation",
], "required order")
require(CONTRACT["selected_implementation"] == [
    "derived-membership-admission-compositor",
    "read-only-binder-ready-gate",
    "one-task-consumed-before-mutation-controller",
    "hardware-free-kunit-and-no-network-qemu",
    "separate-one-boot-physical-candidate",
], "selected implementation")
require(CONTRACT["model_cases"] == 6, "model cases")
require(CONTRACT["model_result"] == "pass", "model result")
require(CONTRACT["planned_generated_patches"] == 2, "planned patches")
require(CONTRACT["planned_derived_kunit_cases"] == 5,
        "planned derived KUnit cases")
require(CONTRACT["source_generator_execution"] ==
        "passed-on-buildbox-exact-prepared-source",
        "source generator execution")
require(CONTRACT["initial_review_rejection"] ==
        "success-fixture-used-seeded-owner-while-production-owner-starts-closed",
        "initial review rejection")
require(CONTRACT["accepted_generator_commit"] ==
        "d1d1c2134345dbf8ebfe433d233d7318437108f9",
        "accepted generator commit")

generated_patches = {
    "0407": ROOT / "patches/v7.1.3/0407-arm64-mediatek-derive-CPU8-admission-from-current-boot-state.patch",
    "0408": ROOT / "patches/v7.1.3/0408-arm64-mediatek-test-source-derived-CPU8-admission.patch",
    "0409": ROOT / "patches/v7.1.3/0409-arm64-mediatek-isolate-derived-admission-KUnit-fixtures.patch",
    "0410": ROOT / "patches/v7.1.3/0410-arm64-mediatek-select-owner-model-for-derived-admission-tests.patch",
    "0411": ROOT / "patches/v7.1.3/0411-soc-mediatek-add-one-shot-CPU8-admission-controller.patch",
    "0412": ROOT / "patches/v7.1.3/0412-soc-mediatek-test-one-shot-CPU8-admission-controller.patch",
}
for number, path in generated_patches.items():
    require(sha256(path) == CONTRACT["generated_patch_sha256"][number],
            f"generated patch {number} hash")

generation = EXP / "results/buildbox-generation-20260828.txt"
require(sha256(generation) == CONTRACT["buildbox_generation_sha256"],
        "Buildbox generation hash")
generation_text = generation.read_text(encoding="utf-8")
for token in (
    "initial_review_rejection=success-fixture-used-seeded-owner-while-production-owner-starts-closed",
    "strict_checkpatch=pass", "fresh_exact_source_replay=pass",
    "source_semantic_validation=pass", "derived_kunit_cases=5",
    "success_starts_closed=true", "production_cpu_requests=0",
    "cpu_off_call_sites=0", "retry_call_sites=0",
    "native_vm_build=none", "device_action=none", "boot_candidate=false",
):
    require(token in generation_text, f"Buildbox generation token: {token}")

runtime = EXP / "results/buildbox-kernel-qemu-attempt1-20260828.txt"
require(sha256(runtime) == CONTRACT["qemu_attempt_1_receipt_sha256"],
        "Buildbox/QEMU attempt 1 hash")
runtime_text = runtime.read_text(encoding="utf-8")
for token in (
    "build_result=pass",
    "suite_mt6797-a72-derived-admission=pass:5_fail:0_skip:0_total:5",
    "suite_mt6797-a72-p24-owner=pass:22_fail:4_skip:0_total:26",
    "owner_failure_class=unrelated-owner-suite-selected-with-public-hooks-intentionally-absent",
    "stack_fault=false",
    "selected_repair=select-hidden-owner-test-seed-without-owner-kunit-suite",
    "production_cpu_requests=0", "native_vm_build=none",
    "device_action=none", "boot_candidate=false",
):
    require(token in runtime_text, f"Buildbox/QEMU token: {token}")
require(CONTRACT["qemu_attempt_1"] == {
    "derived_pass": 5,
    "derived_fail": 0,
    "owner_pass": 22,
    "owner_fail": 4,
    "stack_fault": False,
    "result": "derived-suite-pass-profile-regression-suite-fail",
}, "QEMU attempt 1 result")
require(CONTRACT["selected_runtime_isolation_repair"] ==
        "select-hidden-owner-test-seed-without-owner-kunit-suite",
        "runtime isolation repair")

isolation = EXP / "results/runtime-isolation-generation-20260828.txt"
require(sha256(isolation) == CONTRACT["runtime_isolation_generation_sha256"],
        "runtime isolation generation hash")
isolation_text = isolation.read_text(encoding="utf-8")
for token in (
    "strict_checkpatch=pass", "exact_source_replay=pass",
    "semantic_validation=pass", "owner_kunit_suite_selected=false",
    "owner_test_seed_selected=true", "production_semantics_changed=false",
    "physical_operations=0", "native_vm_build=none", "device_action=none",
    "boot_candidate=false", "result=pass",
):
    require(token in isolation_text, f"runtime isolation token: {token}")
require(CONTRACT["runtime_isolation_patch_integrated"] is True,
        "runtime isolation patch integrated")
require(CONTRACT["runtime_isolation_kernel_build"] is True,
        "runtime isolation rebuild")

failed_rebuild = EXP / "results/runtime-isolation-build-attempt-20260828.txt"
require(sha256(failed_rebuild) ==
        CONTRACT["runtime_isolation_build_attempt_receipt_sha256"],
        "runtime isolation failed rebuild hash")
failed_rebuild_text = failed_rebuild.read_text(encoding="utf-8")
for token in (
    "build_result=fail", "package_created=false",
    "failure_class=unmet-owner-model-test-dependency",
    "owner_model_config=n", "owner_kunit_suite_selected=false",
    "selected_repair=select-base-owner-model-before-hidden-test-seed",
    "production_semantics_changed=false", "native_vm_build=none",
    "device_action=none", "boot_candidate=false",
):
    require(token in failed_rebuild_text,
            f"runtime isolation failed rebuild token: {token}")
require(CONTRACT["runtime_isolation_build_attempt"] == {
    "commit": "8f58958a1083001ce20bb7f531cbd248cc3794af",
    "result": "fail-before-package",
    "failure_class": "unmet-owner-model-test-dependency",
    "device_action": False,
}, "runtime isolation failed rebuild")
require(CONTRACT["selected_dependency_repair"] ==
        "select-base-owner-model-before-hidden-test-seed",
        "selected dependency repair")

dependency_generation = (
    EXP / "results/owner-model-dependency-generation-20260828.txt"
)
require(sha256(dependency_generation) ==
        CONTRACT["dependency_generation_sha256"],
        "owner-model dependency generation hash")
dependency_generation_text = dependency_generation.read_text(encoding="utf-8")
for token in (
    "strict_checkpatch=pass", "exact_source_replay=pass",
    "semantic_validation=pass", "owner_model_selected=true",
    "owner_test_seed_selected=true", "owner_kunit_suite_selected=false",
    "production_semantics_changed=false", "physical_operations=0",
    "native_vm_build=none", "device_action=none", "boot_candidate=false",
    "result=pass",
):
    require(token in dependency_generation_text,
            f"owner-model dependency generation token: {token}")
require(CONTRACT["dependency_patch_integrated"] is True,
        "dependency patch integrated")

isolated_runtime = (
    EXP / "results/buildbox-kernel-qemu-isolated-20260828.txt"
)
require(sha256(isolated_runtime) ==
        CONTRACT["isolated_runtime_receipt_sha256"],
        "isolated Buildbox/QEMU receipt hash")
isolated_runtime_text = isolated_runtime.read_text(encoding="utf-8")
for token in (
    "build_result=pass", "kconfig_unmet_dependency_warnings=0",
    "focused_kunit_symbol_count=1", "owner_model_selected=true",
    "owner_test_seed_selected=true", "owner_kunit_suite_selected=false",
    "known_good_control_under_timeout=invalid-no-guest-output",
    "selected_observation_path=explicit-serial-file-supervised-terminal-marker",
    "suites=1", "tests=5", "failed=0", "skipped=0",
    "tap_summary=pass:5_fail:0_skip:0_total:5", "stack_fault=false",
    "network=false", "mmio=false", "retained_ram=false",
    "watchdog=false", "smc=false", "production_cpu_requests=0",
    "native_vm_build=none", "device_action=none", "boot_candidate=false",
    "result=pass",
):
    require(token in isolated_runtime_text,
            f"isolated Buildbox/QEMU token: {token}")
require(CONTRACT["isolated_qemu"] == {
    "suites": 1,
    "tests": 5,
    "failed": 0,
    "skipped": 0,
    "owner_kunit_suite": False,
    "stack_fault": False,
    "device_action": False,
}, "isolated QEMU result")
require(CONTRACT["durable_qemu_runner"] is True,
        "durable QEMU runner")

controller_generation = EXP / "results/controller-generation-20260828.txt"
require(sha256(controller_generation) ==
        CONTRACT["controller_generation_receipt_sha256"],
        "controller generation receipt hash")
controller_generation_text = controller_generation.read_text(encoding="utf-8")
for token in (
    "repository_commit=d95c42fe7c8f63aa220039a3bd56e1afd6832aef",
    "strict_checkpatch=pass", "checkpatch_errors=0",
    "checkpatch_warnings=0", "checkpatch_checks=0",
    "fresh_exact_source_replay=pass", "production_source_validation=pass",
    "test_source_validation=pass", "manual_patch_review=pass",
    "controller_kunit_cases=5", "derived_kunit_cases=5",
    "consumed_before_owner_mutation=true", "same_task_request=true",
    "production_cpu8_request_call_sites=1",
    "production_cpu9_request_call_sites=0", "cpu_off_call_sites=0",
    "retry_call_sites=0", "base_dt_enablements=0",
    "rejected_generation_attempts=4", "kernel_build=none",
    "native_vm_build=none", "device_action=none", "boot_candidate=false",
    "result=pass",
):
    require(token in controller_generation_text,
            f"controller generation token: {token}")
require(CONTRACT["controller_prepared_source_state"] ==
        "eb0dc301848f9c37aee2cf104e89f5c84c8059ce1b859c30f1c4ef6f3bd1f3af",
        "controller prepared source state")
require(CONTRACT["controller_prepared_source_integrity"] ==
        "63c919e841dcce5c6885f0a4976f4d13b40849af8cf1a8dcb66fd699eba88445",
        "controller prepared source integrity")
require(CONTRACT["controller_patch_count"] == 2,
        "controller patch count")
require(CONTRACT["controller_kunit_cases"] == 5,
        "controller KUnit cases")
require(CONTRACT["controller_source_integrated"] is True,
        "controller source integrated")
require(CONTRACT["controller_kernel_build"] is False,
        "controller build pending")
require(CONTRACT["controller_qemu"] == "pending",
        "controller QEMU pending")

receipt = EXP / "results/source-admission-audit-20260828.txt"
require(CONTRACT["source_receipt_sha256"] != "pending", "receipt hash pending")
require(sha256(receipt) == CONTRACT["source_receipt_sha256"], "receipt hash")
receipt_text = receipt.read_text(encoding="utf-8")
for token in (
    "A36_watchdog_owned_before_add_cpu=impossible",
    "A36_da921x_page_source=absent-no-PAGE_CON-read",
    "binder_entry=inside-add_cpu-MT6797-cpu_boot",
    "binder_recovery_order=ledger-begin-before-watchdog-takeover-before-P27",
    "direct_late_caller_safe=no",
    "controller=consumed-before-mutation-one-task-one-add_cpu8",
    "native_vm_build=none", "device_access=none", "cpu_request=none",
    "boot_candidate=false",
):
    require(token in receipt_text, f"receipt token: {token}")

local_validation = EXP / "results/local-definition-validation-20260828.txt"
require(CONTRACT["local_validation_sha256"] != "pending",
        "local validation hash pending")
require(sha256(local_validation) == CONTRACT["local_validation_sha256"],
        "local validation hash")
local_text = local_validation.read_text(encoding="utf-8")
for token in (
    "bash_syntax=pass", "shellcheck=pass", "python_syntax=pass",
    "model_validation=pass", "model_cases=6",
    "source_generator_execution=deferred-until-signed-pushed-clean-commit",
    "buildbox_kernel_build=none", "native_vm_build=none",
    "device_action=none", "cpu_request=none", "boot_candidate=false",
):
    require(token in local_text, f"local validation token: {token}")

readme = (EXP / "README.md").read_text(encoding="utf-8")
design = (EXP / "DESIGN.md").read_text(encoding="utf-8")
combined = (readme + design + receipt_text + local_text + generation_text +
            runtime_text + isolation_text + failed_rebuild_text +
            dependency_generation_text + isolated_runtime_text +
            controller_generation_text)
words = " ".join(combined.split())
for token in (
    "No direct caller can satisfy the current graph",
    "The obsolete A36 page/recovery assertions must no longer authorize anything",
    "consumed flag before the first owner mutation",
    "one synchronous `add_cpu(8)` call",
    "zero CPU9, CPU_OFF, or retry operations",
):
    require(token in words, f"documentation token: {token}")
require("/Users/" not in combined, "no personal absolute path")
require(CONTRACT["kernel_build"] is True, "kernel build")
require(CONTRACT["device_action"] is False, "no device action")
require(CONTRACT["result"] ==
        "controller-source-integrated-build-pending",
        "result")

print("definition_validation=pass")
print("direct_late_caller=rejected")
print("selected_implementation=one-shot-admission-controller")
print("model_cases=6")
print("generated_patches=2")
print("derived_kunit_cases=5")
print("kernel_build=pass")
print("qemu_derived_cases=pass:5_fail:0")
print("runtime_isolation_repair=integrated")
print("runtime_isolation_rebuild=pass")
print("owner_model_dependency_repair=integrated")
print("isolated_qemu=pass:5_fail:0")
print("controller_patches=integrated:2")
print("controller_kunit_cases=5")
print("selected_next=controller-build-and-qemu")
print("native_vm_build=none")
print("device_action=none")
