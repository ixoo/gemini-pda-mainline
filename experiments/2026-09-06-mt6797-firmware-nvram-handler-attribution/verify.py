#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify only the sanitized, frozen global-stop receipt; no private access."""

from datetime import datetime
import hashlib
import json
from pathlib import Path

EXPECTED_PARENT = "f43a702c107e3685c92c4d275dc3547acf7302ce"
EXPECTED_RECEIPT_SHA256 = "ded4e6a2b3aa5425e8acca2d5207eb3c7d594645c413e9a2f8412eaf7fac2dad"
EXPECTED_INPUTS = {
    "mtke": ("experiments/2026-09-05-mt6797-wifi-contract/results/firmware-mtke.json", "801a45dce0596675faaa67a693ca535b2256f687f4f9c7d25db9626ce681db0e", "Frozen whole firmware identity and structural section counts; not execution or pairing evidence."),
    "mapping": ("experiments/2026-09-05-mt6797-wifi-contract/FIRMWARE_EXECUTABLE_MAPPING.md", "f5689c16a79aa5d512da40b7f8309aa5b4941ecccc40494071e09d2435d609a8", "Frozen candidate mapping and prior decoder assumptions; not a new decoder run."),
    "caller-path": ("experiments/2026-09-05-mt6797-wifi-contract/FIRMWARE_NVRAM_PATH.md", "0ae5a47e5f5b728a0f350dacfa7aacc21a34ae1762815d72d79fd41e64320b6e", "Frozen local caller/reference hypotheses and prior bounded-flow limits."),
    "call-target": ("experiments/2026-09-05-mt6797-wifi-contract/FIRMWARE_NVRAM_CALL_TARGET.md", "1fa29b99340880c925a4c837ea10864c09ed936143a56247cc7ae491d03db40e", "Frozen conditional target candidate and prior target-prefix limitation."),
    "calibration-boundary": ("experiments/2026-09-05-mt6797-wifi-contract/FIRMWARE_CALIBRATION_BOUNDARY.md", "13c7ae780a6fef9c17d05c1ec0f70d0127c76fb48c2063cd1b46801cfd3eae29", "Frozen distinction between text references and firmware calibration semantics."),
    "record-applicability": ("experiments/2026-09-05-mt6797-wifi-contract/CALIBRATION_APPLICABILITY.md", "fe99c510f2291616257a33dbe3ace90ed3ba010bec2fb60a104d1ee853802c03", "Frozen local record applicability boundary; no new record/default inspection."),
    "storage-provenance": ("experiments/2026-09-05-mt6797-wifi-contract/PROVENANCE.md", "cc7fb7cbc162d9f3f3d6b8982faedd8557bfbfddc614ffede7090e9b39a842e1", "Frozen storage/producer limitations; no raw storage or producer-library access."),
    "host-submission": ("experiments/2026-09-05-mt6797-wifi-contract/NORMAL_COMMAND.md", "7cec7a6b00c8a499d32f6c16df4bbe1489a7a572035281c611424eaa27ceebf9", "Host framing/submission constraint only; not a firmware application receipt."),
}
INPUT_RIGHTS = "Existing sanitized project record; reference only, no new external source or private corpus admitted."
EXPECTED_VERDICTS = {
    "target_contract": ("entry_and_complete_slice_verified", "input_shape_and_consumer_verified"),
    "incoming_reachability": ("concrete_transfer_chain_verified", "exhaustive_alternative_dispatch_verified"),
    "record_application": ("resolved_foundations", "payload_to_consumer_def_use_verified"),
    "calibration_precedence": ("source_ordering_verified", "same_predicate_conflict_verified"),
}
EXPECTED_PRIVATE = {
    "firmware": "a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd",
    "retained_analysis": "140f2ab852c841774511861baaff543875da352060d5c44e0a1b3e52790b821b",
    "import_log": "ef4dde5d97b8b70a43a118fa1b9809d605560dd2675954b6ef14882278eaadbe",
    "scripts": "201a8e8241a5af6ed2555beb22c00bc1f75d38c83d40e3253c4f8c8533421ad9",
}
EXPECTED_BOUNDARIES = {
    "policy_selection_allowed", "runtime_claim_allowed", "record_application_observed",
    "hardware_support_claim", "device_access_performed", "firmware_execution_performed",
    "radio_action_performed", "decryption_performed", "emulation_performed",
    "private_material_published", "new_firmware_semantic_interpretation_performed",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_receipt():
    return json.loads((Path(__file__).resolve().parent / "results/attribution.json").read_text())


def verify(receipt=None):
    if receipt is None:
        receipt = load_receipt()
    require(receipt["schema_version"] == 1, "schema")
    require(receipt["parent_commit"] == EXPECTED_PARENT, "parent")
    require(receipt["state"] == "global-stop" and receipt["stop_reason"] == "required-scope-expansion", "stop state")
    inputs = receipt["inputs"]
    require(len(inputs) == 8 and {item["id"] for item in inputs} == set(EXPECTED_INPUTS), "input inventory")
    for item in inputs:
        require((item["path"], item["sha256"], item["purpose"]) == EXPECTED_INPUTS[item["id"]], "frozen input identity/purpose")
        require(item["rights"] == INPUT_RIGHTS, "input rights")
    private = receipt["private_identity"]
    for kind, expected in EXPECTED_PRIVATE.items():
        require(private[kind]["sha256"] == expected, "private identity")
    require(private["firmware"]["bytes"] == 411632, "firmware size")
    require(private["firmware"]["whole_file_hash_matches"] is True and private["firmware"]["whole_file_size_matches"] is True, "firmware verification")
    retained = private["retained_analysis"]
    require(retained["regular_files"] == 21 and retained["aggregate_bytes"] == 1619222, "retained inventory")
    for phase in ("before", "after"):
        for measurement in ("hash", "count", "size"):
            require(retained[measurement + "_matches_" + phase] is True, "retention verification")
        for kind in ("import_log", "scripts"):
            require(private[kind]["hash_matches_" + phase] is True, "private component verification")
    require(private["scripts"]["count"] == 5, "permitted script count")
    require(private["section_window_identity_independently_verified"] is False and private["stored_option_presence_independently_verified"] is False, "incomplete prerequisites")
    require(receipt["tooling_review"]["scripts_inspected"] == 5 and receipt["tooling_review"]["scripts_executed"] == 0, "tooling execution boundary")
    branches = receipt["branches"]
    require(len(branches) == 2 and {b["id"] for b in branches} == {"target-contract", "incoming-reachability"}, "branch inventory")
    for branch in branches:
        require(branch["state"] == "not-started-global-stop", "branch stop")
        require(branch["executed_attempt_count"] == 0 and branch["attempts"] == [], "no fabricated attempts")
        for field in ("node_measurements", "reference_measurements", "unknown_transfers", "cap_exhausted", "queue_exhausted"):
            require(branch[field] is None, "unmeasured graph counts")
    require(set(receipt["verdicts"]) == set(EXPECTED_VERDICTS), "verdict inventory")
    admitted_citations = set(EXPECTED_INPUTS) | {"private_identity.scripts", "branches.target-contract", "branches.incoming-reachability"}
    for name, predicates in EXPECTED_VERDICTS.items():
        verdict = receipt["verdicts"][name]
        require(verdict["verdict"] in {"resolved", "contradicted", "unresolved"}, "verdict enum")
        require(verdict["verdict"] == "unresolved" and verdict["evidence_class"] == "unresolved", "unresolved decision")
        require(all(verdict[p] is False for p in predicates), "unproved predicate")
        require(verdict["citations"] and set(verdict["citations"]) <= admitted_citations, "citation inventory")
        require(verdict["missing_link"] and verdict["next_discriminator"], "discriminator")
    require(set(receipt["boundaries"]) == EXPECTED_BOUNDARIES and all(v is False for v in receipt["boundaries"].values()), "no-policy/no-runtime boundary")
    times = receipt["times"]
    ordered = [datetime.fromisoformat(times[k].replace("Z", "+00:00")) for k in ("contract_analysis_start_utc", "observed_preflight_start_utc", "preservation_complete_and_stop_recorded_utc")]
    require(all(t.utcoffset().total_seconds() == 0 for t in ordered) and ordered == sorted(ordered), "UTC order")
    require(receipt["retention"] == {"existing_private_state_preserved": True, "post_directory_digest_matches_pre": True, "private_files_added": 0, "private_files_removed": 0, "re_shell_closed": True}, "preservation")
    # Freeze all remaining metadata, rights, purpose, timestamps and counts
    # independently of the mutable receipt, before following any file path.
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    require(hashlib.sha256(canonical).hexdigest() == EXPECTED_RECEIPT_SHA256, "frozen receipt")
    repository = Path(__file__).resolve().parents[2]
    for path, sha256, _ in EXPECTED_INPUTS.values():
        require(hashlib.sha256((repository / path).read_bytes()).hexdigest() == sha256, "local frozen record changed")
    return "Offline receipt verification passed: eight input records, two stopped branches, four unresolved verdicts"


if __name__ == "__main__":
    print(verify())
