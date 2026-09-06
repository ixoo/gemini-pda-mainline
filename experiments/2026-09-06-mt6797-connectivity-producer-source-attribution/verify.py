#!/usr/bin/env python3
"""Offline metadata verification only; no source execution or hardware access."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "c5b0be85017ad0c599725e8273842efdbecdd88a"
PARENT = "45b57d265252e8b9068038b84e53b68624f3bab1"
# Independent literal freezes declared in FREEZE.md before construction.
SOURCE_HASH = "0e4a8b43331146d936b3c3c16f06d28cf5e9331a01a76b3435a119e944a707d4"
ANCHOR_HASH = "934b2dfbb3783770e1f2acd181ca007ea501301a2300b1df4977bc755f6e13c0"
REQUEST_HASH = "f57631177704a9b2d9d511ff153c2b9598723c8737d13148217cecfb1aab8151"
VERDICT_HASH = "9f7adc450d74c7cc9f760fac536a1ab4b2bd089060ee92671556fb9d2847009f"
LOCAL_HASHES = json.loads(r'''[{"path":"experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/inputs.json","sha256":"3e2b5c20a08cfd54d42a43587825aa65512cf012bb8b0b572a86e70cb5d4ef2b"},{"path":"experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/search.json","sha256":"c3097344aa612bdf14be3f9b75c946f65a36b813f8222fa09b99450d9ddae1bc"},{"path":"experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/verdicts.json","sha256":"618af79a8edc68e733efe37440d4714fe30853663c8e8c19957d869179b3a171"},{"path":"experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/FREEZE.md","sha256":"1c9ee0bd6298166a82abf2bcfd463758ac12f307e9640e7f2e25792246f5c710"},{"path":"experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/inputs.json","sha256":"c5e123769535553523f70ce0ad3bb15343bf6dfb9637d064059a896f43c5ae66"},{"path":"experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/search.json","sha256":"f744eb95aa2f181da5ab2e942b6d8c9b75cf1810a062056cdf9e27484804f8f9"},{"path":"experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/verdicts.json","sha256":"eae36049120463942aa22040f6111d81021831912a4a866b689681afd1b03b76"},{"path":"experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/FREEZE.md","sha256":"a138e6c12507118a81f8ac723be13796057577f9dcc085725596c288ffa5ebc4"}]''')
COUNTS = json.loads(r'''{"network_requests":6,"raw_successes":6,"raw_failures":0,"new_regular_files":6,"inherited_regular_files":13,"source_identity_tuples":19,"batches":2,"directory_inventories":0,"contextual_rereads":0,"no_hit_records":4}''')
PREV = "experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/inputs.json"
OLDER = "experiments/2026-09-06-mt6797-wlan-builtin-lifecycle-source-attribution/inputs.json"
EXTRA = {"init_h", "connectivity_make", "common_make"}
NEW = {"wmt_detect", "stub", "detect_h", "conn_h", "sdio_detect", "module_h"}
FIELDS = {"source_id", "path", "url", "sha256", "git_blob_sha1", "size", "line_count"}
PREDICATES = {
    "producer_corpus": "resolved", "direct_producer": "resolved",
    "chip_provenance": "unresolved", "aggregate_consumer": "resolved",
    "registration_order": "resolved", "teardown_join": "unresolved",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def predecessor(files, inherited):
    old = {}
    for name in (PREV, OLDER):
        raw = (ROOT / name).read_bytes()
        expected = next(r["sha256"] for r in LOCAL_HASHES if r["path"] == name)
        require(hashlib.sha256(raw).hexdigest() == expected, "independent predecessor file")
        for row in json.loads(raw)["source_files"]:
            if name == PREV or row["source_id"] in EXTRA:
                if row["source_id"] in old:
                    require(old[row["source_id"]] == row, "predecessor disagreement")
                old[row["source_id"]] = row
    require(set(inherited) == set(old) and len(inherited) == 13, "inherited selection")
    for sid, row in old.items():
        require(files[sid] == row, "field-for-field inherited tuple")


def validate(i, s, v):
    require(i["source_commit"] == v["source_commit"] == PIN, "source pin")
    require(i["repository_parent"] == v["repository_parent"] == PARENT, "parent pin")
    require(digest(s) == REQUEST_HASH, "independent complete request freeze")
    require(digest(v["citations"]) == ANCHOR_HASH, "independent citation freeze")
    require(digest(v) == VERDICT_HASH, "independent complete semantics/prose freeze")
    require(digest(sorted(i["source_files"], key=lambda r: r["source_id"])) ==
            SOURCE_HASH, "independent complete source freeze")
    require(i["counts"] == s["counts"] == COUNTS, "exact counts")
    require(i["local_inputs"] == LOCAL_HASHES, "independent local inputs")
    files = {r["source_id"]: r for r in i["source_files"]}
    require(len(files) == len(i["source_files"]) == 19, "source uniqueness")
    predecessor(files, i["inherited_source_ids"])
    require(set(files) == NEW | set(i["inherited_source_ids"]), "corpus coverage")
    require(i["rights"]["source_study_only"] is True and
            all(i["rights"][k] is False for k in (
                "source_bodies_retained", "source_excerpts_in_artifacts",
                "vendor_code_reusable")), "source rights")
    require(all(x is False for x in v["authority"].values()), "no authority")
    require(s["budgets"] == {"batches": 2, "new_regular_files": 7,
            "directory_inventories": 1, "contextual_rereads": 2}, "contract budget")
    require(len(s["requests"]) == 6 and len(s["batches"]) == 2 and
            len(s["no_hits"]) == 4 and s["contextual_rereads"] == [], "receipt coverage")
    require(s["preselection_revalidation"]["result"] == "pass" and
            s["preselection_revalidation"]["checked_before_batch"] == 1,
            "Makefile/config before selection")
    seen = set()
    for batch in s["batches"]:
        receipts = [r for r in s["requests"] if r["batch"] == batch["batch"]]
        require({r["path"] for r in receipts} == set(batch["files"]), "allowlist")
        before = datetime.datetime.strptime(batch["declared_utc"],
                    "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc)
        for r in receipts:
            require(r["kind"] == "raw" and r["status"] == 200, "successful raw receipt")
            require(not ({"lines", "selected_lines", "license_notice"} & set(r)),
                    "no retained source")
            require(before <= datetime.datetime.fromisoformat(r["started_utc"]) <=
                    datetime.datetime.fromisoformat(r["finished_utc"]), "chronology")
            require({k: r[k] for k in FIELDS} == files[r["source_id"]], "receipt tuple")
            require(r["response_sha256"] == r["sha256"] and
                    r["response_bytes"] == r["size"], "complete response identity")
            require(r["url"] == "https://raw.githubusercontent.com/lineage-geminipda/"
                    "android_kernel_planet_mt6797/" + PIN + "/" + r["path"],
                    "pinned source URL")
            seen.add(r["source_id"])
    require(seen == NEW, "new file coverage")
    for row in files.values():
        require(set(row) == FIELDS, "complete source identity fields")
    require({k: p["verdict"] for k, p in v["predicates"].items()} == PREDICATES,
            "six independent verdicts")
    for p in v["predicates"].values():
        for k in ("claim", "conditions", "missing", "next_discriminator"):
            require(isinstance(p[k], str) and len(p[k]) > 30, "bounded claim")
        require(bool(p["evidence"]) and set(p["evidence"]) <= set(v["citations"]),
                "evidence anchors")
    for c in v["citations"].values():
        require(1 <= c["lines"][0] <= c["lines"][1] <=
                files[c["source_id"]]["line_count"], "anchor range")
    require(s["stop"]["additional_source_reads_permitted"] is False, "closed budget")


def co_source(i, s, v):
    for row in i["source_files"] + s["requests"]:
        if row["source_id"] == "wmt_detect":
            row["sha256"] = "0" * 64
            if "response_sha256" in row:
                row["response_sha256"] = "0" * 64


def co_request(i, s, v):
    s["requests"][0]["path"] = "invented.c"
    s["batches"][0]["files"][0] = "invented.c"
    next(r for r in i["source_files"] if r["source_id"] == "wmt_detect")["path"] = "invented.c"


def co_anchor(i, s, v):
    v["citations"]["detect_ioctl"]["lines"] = [84, 147]
    v["predicates"]["direct_producer"]["claim"] = "Invented producer co-mutated with an in-bounds anchor."


def main():
    i, s, v = [json.loads((HERE / n).read_text())
               for n in ("inputs.json", "search.json", "verdicts.json")]
    for r in LOCAL_HASHES:
        require(hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest() ==
                r["sha256"], "inherited local file freeze")
    validate(i, s, v)
    mutations = [
        ("co-mutated source and receipt", co_source),
        ("co-mutated request and selection", co_request),
        ("co-mutated citation and claim", co_anchor),
        ("missing request", lambda a, b, c: b["requests"].pop()),
        ("no-hit deletion", lambda a, b, c: b["no_hits"].pop()),
        ("budget drift", lambda a, b, c: b["budgets"].update(batches=3)),
        ("failure invention", lambda a, b, c: b["requests"][0].update(status=404)),
        ("count drift", lambda a, b, c: a["counts"].update(new_regular_files=7)),
        ("wrong inherited list", lambda a, b, c: a["inherited_source_ids"].pop()),
        ("rights promotion", lambda a, b, c: a["rights"].update(vendor_code_reusable=True)),
        ("predicate deletion", lambda a, b, c: c["predicates"].pop("teardown_join")),
    ]
    # Each contract-bearing semantic field gets its own refusal, including order,
    # actual chip, config, aggregate loss/retry, registration and built-in unload.
    for key, value in v["state_model"].items():
        wrong = not value if isinstance(value, bool) else (
            list(reversed(value)) if isinstance(value, list) else "invented")
        mutations.append((key, lambda a, b, c, key=key, wrong=wrong:
                          c["state_model"].update({key: wrong})))
    for key in v["authority"]:
        mutations.append((key, lambda a, b, c, key=key:
                          c["authority"].update({key: True})))
    for name, mutate in mutations:
        a, b, c = copy.deepcopy((i, s, v))
        mutate(a, b, c)
        try:
            validate(a, b, c)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("refusal accepted: " + name)
    altered = {r["source_id"]: copy.deepcopy(r) for r in i["source_files"]}
    altered["init_h"]["line_count"] += 1
    try:
        predecessor(altered, i["inherited_source_ids"])
    except ValueError:
        pass
    else:
        raise ValueError("refusal accepted: independent inherited field mutation")
    print(f"PASS: 6 predicates; 19 source tuples; {len(v['citations'])} anchors; "
          f"6 receipts; {len(mutations) + 1} refusals. Source attribution only.")


if __name__ == "__main__":
    main()
