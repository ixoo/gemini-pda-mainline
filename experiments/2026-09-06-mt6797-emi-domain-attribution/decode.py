#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce packed three-bit fields; this makes no routing assertion."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

COMMIT = "c5b0be85017ad0c599725e8273842efdbecdd88a"
REPOSITORY = "https://github.com/lineage-geminipda/android_kernel_planet_mt6797.git"
TREE_URL = "https://api.github.com/repos/lineage-geminipda/android_kernel_planet_mt6797/git/trees/" + COMMIT + "?recursive=1"
TREE_RESPONSE_SHA256 = "aa447a91303a94b3711c4bf8193b9e10e5f32ca744bc84adff62d875c0e8a34e"
EXPECTED_SELECTED = [
    ("drivers/misc/mediatek/devapc/mt6797/devapc.c", 29835, "67fe4f735480753434898411bc753e4976dff165"),
    ("drivers/misc/mediatek/devapc/mt6797/devapc.h", 4132, "d8c1b46f6f59585f325ede8ff8ef13f111f7931d"),
    ("drivers/misc/mediatek/eccci/mt6797/ccci_platform.c", 38764, "e9fb8a381f16f4796933540baf665f3a374121bb"),
    ("drivers/misc/mediatek/eccci/mt6797/ccci_platform.h", 2915, "e0162849b144dd7fc6b4756cd2b93c92e2998b5d"),
    ("drivers/misc/mediatek/emi_mpu/mt6797/emi_mpu.c", 93439, "96128217defbfb79950deeb6443f82d17f2025b8"),
    ("drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h", 9747, "f6372c0b9271d90a59079e7c1004ed198bbe23c4"),
]
EXPECTED_RECORD_IDS = {
    "emi-abi", "retained-abi", "shared-owner", "retained-windows",
    "public-source-ledger", "historical-tee-identity", "historical-mapping",
}
# Independent frozen expectations, never learned from the records at runtime.
# Each digest covers the complete list, including exact paths, hashes, purpose,
# rights, license notices and every private-artifact field. Canonical JSON uses
# sort_keys=True, separators=(",", ":"), UTF-8 and original list order.
EXPECTED_METADATA_SHA256 = {
    "sources": "568e3cd7566fe7e2f9d3d394a93d3e707f5b964b26dde60972f4904d9d7ce46b",
    "records": "6a8370d2eb728752aa154c47ce826e5d1fdfddabf2e6f98cf4836e95b35c5466",
    "private_artifacts": "0576a64b1cbaab84bad38c8e59e46d8de37c0e0143d9f7f31208afcda125989b",
}
EXPECTED_RECORD_IDENTITIES = {
    "emi-abi": ("experiments/2026-09-05-mt6797-wifi-contract/EMI_ABI.md", "60bd8c436b22495719512b8a1cd9dae0bffb062511811d67cff436d94a0f0c71"),
    "retained-abi": ("experiments/2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md", "8c4963c1d9e63b98bb7dcdad8ed41e442f1f6171e8c599869758f4984e7a7f06"),
    "shared-owner": ("experiments/2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md", "a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021"),
    "retained-windows": ("experiments/2026-09-05-mt6797-wifi-contract/results/retained-emi-secure-abi.json", "fc1f249aa50b975298d559f8446dce7de24068a3aa88fab3b81ad83f1f3bcfe2"),
    "public-source-ledger": ("experiments/2026-09-05-mt6797-wifi-contract/results/whole-image-emi-sources.json", "f69382b0ddaa09f9dd1f5eebf76d55f4b2e41734f1e9cd199e9fe2346b20d9ef"),
    "historical-tee-identity": ("experiments/2026-07-22-a72-firmware-power-contract/results/live-tee-identity-20260723.txt", "3f2753800637a9650ce210b57f2d531f62b62daeef095262deff86c4a1f25b55"),
    "historical-mapping": ("experiments/2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt", "d7b3b7848dc6e0df9e11845193a3e77e72d2fd64034454b194c9f9e340ccd5a2"),
}
EXPECTED_RUNTIME_REGION_STATE = "Unknown for every region 0 through 23; source setters and default rows are not active-state receipts."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_records():
    experiment = Path(__file__).resolve().parent
    return {
        name: json.loads((experiment / "results" / (name + ".json")).read_text())
        for name in ("inputs", "verdicts", "search-attempts")
    }


def verify(online=False, records=None, quiet=False):
    repository = Path(__file__).resolve().parents[2]
    if records is None:
        records = load_records()
    inputs, verdicts, searches = (records[n] for n in ("inputs", "verdicts", "search-attempts"))
    require(all(r["schema_version"] == 1 for r in records.values()), "schema version")
    # Reject co-mutated path/hash or rights metadata before opening any path.
    for name, expected in EXPECTED_METADATA_SHA256.items():
        canonical = json.dumps(inputs[name], sort_keys=True, separators=(",", ":")).encode()
        require(hashlib.sha256(canonical).hexdigest() == expected, "frozen metadata: " + name)
    require(inputs["parent_commit"] == "82405bb9eafb3af37cafb331e1bc0eaeb2518f3f", "parent commit")
    require(inputs["commit"] == COMMIT and inputs["repository"] == REPOSITORY, "public repository/commit")
    require(inputs["tree"]["url"] == TREE_URL, "tree URL")
    require(inputs["tree"]["api_reported_sha"] == COMMIT, "API reported identity")
    require(inputs["tree"]["response_sha256"] == TREE_RESPONSE_SHA256, "tree raw-response identity")
    expected_selected = [
        {"path": path, "mode": "100644", "type": "blob", "sha": sha, "size": size}
        for path, size, sha in EXPECTED_SELECTED
    ]
    require(inputs["tree"]["selected_paths"] == expected_selected, "exact selected tree entries")
    sources = {s["id"]: s for s in inputs["sources"]}
    require(set(sources) == {"emi-c", "emi-h", "devapc-c", "devapc-h", "ccci-c", "ccci-h"}, "corpus IDs")
    require(len(inputs["sources"]) == 6, "duplicate source")
    require({s["path"] for s in sources.values()} == {e[0] for e in EXPECTED_SELECTED}, "exact source paths")
    require(len(inputs["records"]) == 7 and {r["id"] for r in inputs["records"]} == EXPECTED_RECORD_IDS, "exact record IDs")
    identities = dict(sources)
    for record in inputs["records"]:
        require((record["path"], record["sha256"]) == EXPECTED_RECORD_IDENTITIES[record["id"]], "frozen record path/hash")
        path = repository / record["path"]
        require(path.resolve().is_relative_to(repository), "record containment")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], "record hash: " + record["id"])
        identities[record["id"]] = record
    for source in sources.values():
        require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), "source digest")
        require(source["size"] > 0 and source["file_level_license"] == "GPL-2.0-only", "source metadata")
        require(source["purpose"] and source["rights"], "purpose/rights")
        entries = [e for e in inputs["tree"]["selected_paths"] if e["path"] == source["path"]]
        require(len(entries) == 1, "tree source membership")
        require(entries[0]["sha"] == source["git_blob_sha1"] and entries[0]["size"] == source["size"], "tree blob identity")
    require(inputs["tree"]["truncated"] is False and inputs["tree"]["entry_count"] == 59243, "tree completeness")
    require(len(inputs["private_artifacts"]) == 1, "private artifact count")
    artifact = inputs["private_artifacts"][0]
    require(artifact["id"] == "retained-tee" and artifact["size"] == 5242880, "exact private artifact")
    require(artifact["sha256"] == "2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3", "exact private hash")
    require(artifact["window_record_id"] == "retained-windows", "private window authority")
    require(artifact["verified_windows"] == ["range-and-selector", "region18", "region19", "shared-store", "region-table"], "exact verified windows")
    require("path" not in artifact and artifact["new_interpretation"] is False, "private boundary")
    frozen = json.loads((repository / identities[artifact["window_record_id"]]["path"]).read_text())
    require(artifact["sha256"] == frozen["image_sha256"] and artifact["size"] == frozen["image_bytes"], "private identity")
    require(set(artifact["verified_windows"]) <= {w["name"] for w in frozen["windows"]}, "private window names")
    require(set(verdicts["verdicts"]) == {"ap", "consys", "wlan", "overlap_priority"}, "verdict IDs")
    require(verdicts["allowed_verdicts"] == ["resolved", "contradicted", "unresolved"], "declared verdict enum")
    for name in ("ap", "consys", "wlan"):
        require(verdicts["verdicts"][name].get("hardware_routing_established") is False, "unestablished routing: " + name)
    for predicate in ("priority_rule_established", "active_region_applicability_established"):
        require(verdicts["verdicts"]["overlap_priority"].get(predicate) is False, "unestablished overlap: " + predicate)
    require(verdicts["runtime_region_state"] == EXPECTED_RUNTIME_REGION_STATE, "unknown runtime region state")
    for verdict in verdicts["verdicts"].values():
        require(verdict["verdict"] in {"resolved", "contradicted", "unresolved"}, "verdict enum")
        require(verdict["evidence_class"] in {"observed-source-fact", "cross-source-inference", "contradiction", "unresolved"}, "evidence enum")
        require(verdict["missing_link"] and verdict["next_discriminator"] and verdict["citations"], "verdict evidence")
        for citation in verdict["citations"]:
            require(citation["sha256"] == identities[citation["source_id"]]["sha256"] and citation["locator"], "citation identity")
    require(verdicts["policy_selection_allowed"] is False, "policy must remain blocked")
    require(all(v["verdict"] == "unresolved" for v in verdicts["verdicts"].values()), "frozen unresolved decision")
    require({b["id"] for b in searches["branches"]} == {"domain-routing", "overlap-priority"}, "branch IDs")
    require(len(searches["branches"]) == 2, "branch count")
    for branch in searches["branches"]:
        require(1 <= len(branch["attempts"]) <= 2, "attempt budget")
        for number, attempt in enumerate(branch["attempts"], 1):
            require(attempt["number"] == number, "attempt order")
            require(attempt["predeclared"] is False and attempt["predeclaration_status"] == "unavailable", "historical declaration honesty")
            require(attempt["started_utc"] is None and attempt["stopped_utc"] is None and attempt["timestamp_status"] == "unavailable", "historical timestamp honesty")
            query_ids = attempt["query_corpus_source_ids"]
            require(len(query_ids) == len(set(query_ids)) == len(attempt["inventory"]), "query inventory cardinality")
            require(set(query_ids) <= set(sources), "query corpus membership")
            require(set(query_ids) == {h["source_id"] for h in attempt["inventory"]}, "exact query inventory coverage")
            require(attempt["supporting_records_queried"] is False, "supporting records not queried")
            require(all(record_id in EXPECTED_RECORD_IDS for record_id in attempt["supporting_record_ids"]), "supporting record membership")
            require(attempt["objective"] and attempt["query"] and attempt["conclusion"], "attempt content")
            for hit in attempt["inventory"]:
                require(hit["sha256"] == sources[hit["source_id"]]["sha256"], "inventory identity")
                require(hit["hit_lines"] == sorted(set(hit["hit_lines"])), "hit ordering")
                require(hit["hit_count"] == len(hit["hit_lines"]), "hit count")
                require(hit["status"] == ("hit" if hit["hit_count"] else "no-hit"), "hit status")
    if online:
        base = "https://raw.githubusercontent.com/lineage-geminipda/android_kernel_planet_mt6797/" + inputs["commit"] + "/"
        texts = {}
        for source_id, source in sources.items():
            data = urllib.request.urlopen(base + source["path"], timeout=30).read()
            require(len(data) == source["size"] and hashlib.sha256(data).hexdigest() == source["sha256"], "download identity")
            require(hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == source["git_blob_sha1"], "git blob")
            texts[source_id] = data.decode().splitlines()
            require("GNU General Public License version 2" in "\n".join(texts[source_id][:12]), "file license notice")
        for branch in searches["branches"]:
            for attempt in branch["attempts"]:
                for hit in attempt["inventory"]:
                    actual = [i for i, line in enumerate(texts[hit["source_id"]], 1) if re.search(attempt["query"], line, re.I)]
                    require(actual == hit["hit_lines"], "replayed hit inventory")
        for hit in searches["literal_priority_overlap_scan"]["inventory"]:
            actual = [i for i, line in enumerate(texts[hit["source_id"]], 1) if re.search("priority|overlap", line, re.I)]
            require(actual == hit["hit_lines"] == [], "literal priority/overlap scan")
        tree_data = urllib.request.urlopen(inputs["tree"]["url"], timeout=30).read()
        require(hashlib.sha256(tree_data).hexdigest() == TREE_RESPONSE_SHA256, "remote raw tree response identity")
        tree = json.loads(tree_data)
        require(tree["sha"] == COMMIT, "remote API tree identity")
        require(tree["truncated"] is False and len(tree["tree"]) == inputs["tree"]["entry_count"], "remote tree completeness")
        inventory = [{k: e[k] for k in ("path", "mode", "type", "sha", "size") if k in e} for e in tree["tree"]]
        canonical = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
        require(hashlib.sha256(canonical).hexdigest() == inputs["tree"]["inventory_sha256"], "remote tree inventory identity")
    if not quiet:
        print("Record validation passed" + (" with public identity/search replay" if online else " (offline)"))


def decode(word):
    return [(word >> (3 * field)) & 7 for field in range(8)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="Also verify the frozen public files and replay search inventories in memory")
    args = parser.parse_args()
    expected = {
        0xB6DA2D: [5, 5, 0, 5, 5, 5, 5, 5],
        0xB6DA28: [0, 5, 0, 5, 5, 5, 5, 5],
    }
    for word, fields in expected.items():
        actual = decode(word)
        require(actual == fields, "packed field vector")
        # Recompose with multiplication, independently of extraction shifts.
        require(sum(value * 8**index for index, value in enumerate(fields)) == word, "base-eight reconstruction")
        print(json.dumps({"word": hex(word), "fields_0_through_7": actual}))
    require(0xB6DA2D ^ 0xB6DA28 == 5, "changed-bit identity")
    verify(args.online)


if __name__ == "__main__":
    main()
