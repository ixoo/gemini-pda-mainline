#!/usr/bin/env python3
"""Offline sanitized metadata/refusal checks; never reads the retained binary."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = "65f1b43333b727f0d5bbddf900cd38486a896e4d"
BINARY = "system/vendor/bin/wmt_loader"
BINARY_HASH = "446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa"
# Literal independent freezes were declared in FREEZE.md before construction.
INPUT_HASH = "b66fb7e2934fa1965754ca52e9b40d9b377f16e058ace6003c111fded8744bc2"
ANCHOR_HASH = "9cd60ff515c67e6d99d558810efcdfc9d5d91bdb828f2045a233a0f78aee5af2"
ANALYSIS_HASH = "e6c02cdf79fccb0b91297988843a28b804e5aeaa8496a3432c1bbbde942a7317"
VERDICT_HASH = "0df00cda55346a7e0c539e880494d92efe922b9130de91a54936f8a53c8cfb02"
LOCAL_HASHES = json.loads(r'''[{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/inputs.json","sha256":"9893687d6bef1b80c0c6e6a0a87216635ddb6490609e58bbc25c838bda0d88a8"},{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/search.json","sha256":"eee3545c527b8758048a7fd0b311f26923491c1241602d322ff2cf2dc275e029"},{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/verdicts.json","sha256":"955ccc161572baa4c02c8c68bf6292159119eb6786e4237dcdc8db6196c4800b"},{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/FREEZE.md","sha256":"e1a6f37c3bf6e8eeedd59592d9814671e4db6eb5571725b2e284bbd92d4d8517"}]''')
ALLOWED_ARGS = json.loads(r'''[["sha256sum","system/vendor/bin/wmt_loader"],["aarch64-linux-gnu-objdump","--version"],["readelf","--version"],["readelf","-h","-SW","system/vendor/bin/wmt_loader"],["aarch64-linux-gnu-objdump","-d","--no-show-raw-insn","--start-address=0xb00","--stop-address=0x1200","system/vendor/bin/wmt_loader"],["aarch64-linux-gnu-objdump","-d","--no-show-raw-insn","--start-address=0xb10","--stop-address=0x1200","system/vendor/bin/wmt_loader"],["aarch64-linux-gnu-objdump","-d","--no-show-raw-insn","--start-address=0x1200","--stop-address=0x14d0","system/vendor/bin/wmt_loader"],["sha256sum","--version"]]''')
COUNTS = json.loads(r'''{"batches":2,"admitted_binaries":1,"static_tool_children":8,"controller_invocations":2,"guest_shell_sessions":1,"analyzed_function_regions":1,"incidental_function_tail_fragments":1,"selected_basic_blocks":108,"incidental_partial_blocks":1,"selected_instructions":624,"incidental_instructions":4,"unique_ioctl_call_sites":14,"selected_direct_call_sites":62,"batch2_regions":3,"batch2_region_bytes":2525,"disassembly_bytes_across_requests":4288,"unique_disassembled_bytes":2512,"unique_literal_bytes":44,"tool_failures":0,"external_file_diagnostics":0,"temporary_files":0}''')
EXPECTED_VERDICTS = {
    "identity_fd": "resolved", "init_request": "resolved",
    "argument_origin": "resolved", "return_handling": "unresolved",
    "command_order": "resolved", "mainline_boundary": "unresolved",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def inherited(i, v):
    files = {}
    for row in LOCAL_HASHES:
        raw = (ROOT / row["path"]).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == row["sha256"],
                "independent predecessor file identity")
        if row["path"].endswith("/inputs.json"):
            files = {r["source_id"]: r for r in json.loads(raw)["source_files"]}
        if row["path"].endswith("/verdicts.json"):
            anchors = json.loads(raw)["citations"]
    require({r["source_id"] for r in i["inherited_source_files"]} ==
            {"conn_h", "detect_h", "wmt_detect"}, "inherited corpus")
    for r in i["inherited_source_files"]:
        require(r == files[r["source_id"]], "field-for-field inherited tuple")
    require(set(v["inherited_source_citations"]) == {
        "detect_commands", "detect_ioctl", "connection_declaration", "detect_header_guard"},
        "inherited citation selection")
    for key, anchor in v["inherited_source_citations"].items():
        require(anchor == anchors[key], "field-for-field inherited anchor")


def tool_guard(a):
    require(len(a["requests"]) == 8, "complete static-child receipts")
    for index, receipt in enumerate(a["requests"]):
        args = receipt["args"]
        require(args == ALLOWED_ARGS[index], "exact predeclared tool arguments")
        for arg in args[1:]:
            require(not arg.startswith(("--dwarf", "--debug-dump", "--follow-links")) and
                    not (arg.startswith("-") and not arg.startswith("--") and "w" in arg),
                    "debug/DWARF option forbidden")
        require(receipt["environment"] == {"DEBUGINFOD_URLS": ""}, "no symbol server")
        require(receipt["external_file_evidence"] == [] and receipt["stderr_empty"] is True,
                "external-file or diagnostic refusal")
        require(receipt["returncode"] == 0, "tool status")
    require(a["safety"]["external_file_evidence"] == [] and
            a["safety"]["debug_server_urls"] == "", "closed environment")
    require(all(a["safety"][key] is False for key in (
        "debug_options_used", "unwind_requested", "debug_links_used", "build_ids_used",
        "binary_executed", "ioctl_invoked", "live_process_inspected", "network_used",
        "v1_output_reused", "raw_output_retained")), "static-only/no-follow boundary")


def validate(i, a, v):
    tool_guard(a)
    require(digest(i) == INPUT_HASH, "independent complete inputs freeze")
    require(digest(a) == ANALYSIS_HASH, "independent complete analysis freeze")
    require(digest({"binary": v["anchors"], "source": v["inherited_source_citations"]}) ==
            ANCHOR_HASH, "independent semantic anchor freeze")
    require(digest(v) == VERDICT_HASH, "independent complete verdict freeze")
    require(i["repository_parent"] == v["repository_parent"] == PARENT, "parent")
    require(i["binary"]["logical_path"] == BINARY and
            i["binary"]["sha256"] == v["binary_sha256"] == BINARY_HASH, "binary identity")
    require(i["local_inputs"] == LOCAL_HASHES, "predecessor file set")
    inherited(i, v)
    require(i["tools"]["environment"] == {"DEBUGINFOD_URLS": ""}, "tool environment")
    require(a["counts"] == COUNTS, "complete budget accounting")
    require(a["budgets"] == {"batches": 2, "admitted_binaries": 1,
        "static_tool_children": 14, "ioctl_call_sites": 20,
        "batch2_regions": 4, "batch2_region_bytes": 4096}, "fixed contract limits")
    require(a["counts"]["static_tool_children"] <= a["budgets"]["static_tool_children"] and
            a["counts"]["unique_ioctl_call_sites"] <= a["budgets"]["ioctl_call_sites"],
            "tool/site budget")
    require(len(a["batches"]) == 2 and len(a["controller_receipts"]) == 2, "two batches")
    for batch in a["batches"]:
        rows = [r for r in a["requests"] if r["batch"] == batch["id"]]
        require([r["args"] for r in rows] == batch["static_children"], "complete allowlist")
        before = datetime.datetime.strptime(batch["declared_utc"],
                    "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc)
        for r in rows:
            require(before <= datetime.datetime.fromisoformat(r["started_utc"]) <=
                    datetime.datetime.fromisoformat(r["finished_utc"]), "predeclaration chronology")
            require(len(r["stdout_sha256"]) == 64 and r["stdout_bytes"] > 0,
                    "response identity receipt")
    regions = a["batches"][1]["regions"]
    require(len(regions) == 3 and sum(r["bytes"] for r in regions) == 2525 <= 4096,
            "bounded direct-edge regions")
    for region in regions:
        require(int(region["end_exclusive"], 16) - int(region["start"], 16) ==
                region["bytes"], "exact interval size")
    cfg = a["cfg_accounting"]
    require(len(cfg["basic_block_starts"]) == cfg["basic_block_count"] == 108,
            "counted basic blocks")
    require(len(cfg["ioctl_sites"]) == len(set(cfg["ioctl_sites"])) == 14,
            "unique ioctl sites, not repeated disassembly appearances")
    require(cfg["instruction_count"] == 624 and cfg["region"] == ["0xb10", "0x14d0"],
            "selected routine coverage")
    require(all(0xb10 <= int(x, 16) < 0x14d0 for x in cfg["basic_block_starts"]),
            "block bounds")
    for anchor in v["anchors"].values():
        lo, hi = int(anchor["start"], 16), int(anchor["end_exclusive"], 16)
        require((0xb10 <= lo < hi <= 0x14d0) or (lo, hi) == (0x1510, 0x152d),
                "admitted anchor interval")
    require(len(v["commands"]) == 9, "command inventory")
    for row in v["commands"]:
        direction = 1 if row["number"] == 1 else 2
        require(row["size"] == 4 and row["type"] == 119, "ioctl encoding fields")
        require(int(row["request"], 16) ==
                ((direction << 30) | (4 << 16) | (119 << 8) | row["number"]),
                "numeric command encoding")
    require(v["state_model"]["init_site"] in cfg["ioctl_sites"] and
            v["state_model"]["cleanup_site"] in cfg["ioctl_sites"], "actual call sites")
    require({key: p["verdict"] for key, p in v["predicates"].items()} ==
            EXPECTED_VERDICTS, "six bounded independent predicates")
    for p in v["predicates"].values():
        for key in ("claim", "conditions", "missing", "next_discriminator"):
            require(isinstance(p[key], str) and len(p[key]) > 30, "explicit boundary")
        require(bool(p["evidence"]) and set(p["evidence"]) <= set(v["anchors"]),
                "normalized evidence anchors")
    require(all(x is False for x in v["authority"].values()), "no authority promotion")
    require(i["rights"]["retained_binary_is_private"] is True and
            all(value is False for key, value in i["rights"].items()
                if key != "retained_binary_is_private"), "rights/retention boundary")
    require(a["stop"]["analysis_closed"] is True, "closed analysis budget")


def co_identity(i, a, v):
    i["binary"]["sha256"] = v["binary_sha256"] = "0" * 64
    a["batches"][0]["expected_sha256"] = "0" * 64


def co_call(i, a, v):
    v["state_model"]["init_site"] = "0x12a0"
    a["cfg_accounting"]["ioctl_sites"][-2] = "0x12a0"
    v["anchors"]["init_call"]["start"] = "0x12a0"


def main():
    i, a, v = [json.loads((HERE / name).read_text())
               for name in ("inputs.json", "analysis.json", "verdicts.json")]
    validate(i, a, v)
    cases = [
        ("co-mutated identity", co_identity),
        ("co-mutated callsite and anchor", co_call),
        ("missing receipt", lambda x, y, z: y["requests"].pop()),
        ("budget drift", lambda x, y, z: y["budgets"].update(static_tool_children=15)),
        ("no-hit deletion", lambda x, y, z: y["no_hits"].pop()),
        ("wrong architecture", lambda x, y, z: x["binary"].update(machine="ARM")),
        ("raw dump retention", lambda x, y, z: x["rights"].update(instruction_listings_retained=True)),
        ("inherited anchor move", lambda x, y, z:
         z["inherited_source_citations"]["detect_ioctl"].update(lines=[84, 148])),
        ("invented standard contract prose", lambda x, y, z:
         z["predicates"]["mainline_boundary"].update(claim="This establishes an upstream ABI.")),
        ("count drift", lambda x, y, z: y["counts"].update(selected_basic_blocks=107)),
    ]
    for key, value in v["state_model"].items():
        wrong = not value if isinstance(value, bool) else "invented"
        if isinstance(value, list):
            wrong = list(reversed(value))
        cases.append((key, lambda x, y, z, key=key, wrong=wrong:
                      z["state_model"].update({key: wrong})))
    for key in v["authority"]:
        cases.append((key, lambda x, y, z, key=key: z["authority"].update({key: True})))
    for index in range(9):
        cases.append(("wrong request " + str(index), lambda x, y, z, index=index:
                      z["commands"][index].update(request="0x00000000")))
    for name, mutate in cases:
        x, y, z = copy.deepcopy((i, a, v))
        mutate(x, y, z)
        try:
            validate(x, y, z)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("refusal accepted: " + name)
    # Test policy and inherited comparisons independently of complete hash gates.
    guard_cases = []
    for flag in ("-w", "-wf", "--debug-dump=frames", "--dwarf=follow-links",
                 "--dwarf-depth=1", "--dwarf-start=0"):
        guard_cases.append((flag, lambda y, flag=flag: y["requests"][4]["args"].insert(1, flag)))
    guard_cases += [
        ("external input", lambda y: y["requests"][4]["args"].__setitem__(-1, "other-binary")),
        ("external evidence", lambda y: y["requests"][4].update(external_file_evidence=["other-file"])),
        ("debug server", lambda y: y["requests"][4]["environment"].update(DEBUGINFOD_URLS="server")),
        ("diagnostic", lambda y: y["requests"][4].update(stderr_empty=False)),
    ]
    for name, mutate in guard_cases:
        y = copy.deepcopy(a)
        mutate(y)
        try:
            tool_guard(y)
        except ValueError:
            continue
        raise ValueError("independent tool refusal accepted: " + name)
    x = copy.deepcopy(i)
    x["inherited_source_files"][0]["size"] += 1
    try:
        inherited(x, v)
    except ValueError:
        pass
    else:
        raise ValueError("independent predecessor mutation accepted")
    print(f"PASS: 6 predicates; 22 binary anchors; 8 receipts; 14 ioctl sites; "
          f"{len(cases) + len(guard_cases) + 1} refusals. Static compatibility only.")


if __name__ == "__main__":
    main()
