#!/usr/bin/env python3
"""Validate sanitized v3 evidence offline, without opening any retained binary."""
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
# Literal independent expectations declared in FREEZE.md before construction.
INPUT_HASH = "1c94495b7e6fbc0faa3641d7e6c6f2c12806f8c2f920efd8dcdcbae9b4fbd8df"
ANCHOR_HASH = "850a5d0520ac9c8ccbd78dca9df872930c277c495c2d9966966daaa1592cb133"
ANALYSIS_HASH = "1daad911f3b3527590d80ab110d98d40083eab07004ca5555d6bc5647a72df97"
VERDICT_HASH = "a85468a71102136da837cc27b2662016dc87b90059e28c236925f9ab6a2d1226"
LOCAL_HASHES = json.loads(r'''[{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/inputs.json","sha256":"9893687d6bef1b80c0c6e6a0a87216635ddb6490609e58bbc25c838bda0d88a8"},{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/search.json","sha256":"eee3545c527b8758048a7fd0b311f26923491c1241602d322ff2cf2dc275e029"},{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/verdicts.json","sha256":"955ccc161572baa4c02c8c68bf6292159119eb6786e4237dcdc8db6196c4800b"},{"path":"experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/FREEZE.md","sha256":"e1a6f37c3bf6e8eeedd59592d9814671e4db6eb5571725b2e284bbd92d4d8517"}]''')
ARGS = json.loads(r'''[["sha256sum","system/vendor/bin/wmt_loader"],["sha256sum","--version"],["aarch64-linux-gnu-objdump","--version"],["readelf","--version"],["readelf","-h","-SW","system/vendor/bin/wmt_loader"],["aarch64-linux-gnu-objdump","-d","--no-show-raw-insn","--start-address=0xb10","--stop-address=0x14d0","system/vendor/bin/wmt_loader"]]''')
COUNTS = json.loads(r'''{"analysis_batches":1,"static_children":6,"controllers":1,"re_shell_sessions":1,"disassemblies":1,"replays":0,"analyzed_function_regions":1,"code_intervals":1,"code_bytes":2496,"literal_intervals":2,"literal_bytes":44,"total_selected_bytes":2540,"instructions":624,"basic_blocks":108,"direct_call_sites":62,"ioctl_call_sites":14,"analysis_tool_diagnostics":0,"temporary_files":0}''')
CODE = {"start": "0xb10", "end_exclusive": "0x14d0", "bytes": 2496}
LITERALS = [
    {"start": "0x14d0", "end_exclusive": "0x14df", "bytes": 15},
    {"start": "0x1510", "end_exclusive": "0x152d", "bytes": 29},
]
BUDGETS = {
    "analysis_batches": 1, "static_children_max": 8, "controllers": 1,
    "re_shell_sessions": 1, "disassemblies": 1, "replays": 0,
    "code_bytes": 2496, "literal_bytes": 44,
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def predecessor(i, v):
    old_sources, old_anchors = {}, {}
    for item in LOCAL_HASHES:
        raw = (ROOT / item["path"]).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == item["sha256"], "predecessor file")
        if item["path"].endswith("/inputs.json"):
            old_sources = {r["source_id"]: r for r in json.loads(raw)["source_files"]}
        if item["path"].endswith("/verdicts.json"):
            old_anchors = json.loads(raw)["citations"]
    require({r["source_id"] for r in i["inherited_source_files"]} ==
            {"conn_h", "detect_h", "wmt_detect"}, "inherited selection")
    for row in i["inherited_source_files"]:
        require(row == old_sources[row["source_id"]], "inherited complete tuple")
    require(set(v["inherited_source_citations"]) == {
        "detect_commands", "detect_ioctl", "connection_declaration", "detect_header_guard"},
        "inherited anchor selection")
    for key, anchor in v["inherited_source_citations"].items():
        require(anchor == old_anchors[key], "inherited complete anchor")


def scope_guard(a):
    require(a["budgets"] == BUDGETS and a["accounting"] == COUNTS, "frozen budget/counts")
    require(a["batch"]["id"] == 1 and a["batch"]["static_children"] == ARGS,
            "one predeclared batch")
    require(a["batch"]["code_interval"] == CODE and
            a["batch"]["literal_intervals"] == LITERALS, "prospective exact intervals")
    require(a["batch"]["controller_argv"] == ["python3", "-"] and
            a["controller_receipt"]["argv"] == ["python3", "-"], "one controller")
    require(len(a["requests"]) == 6, "no additional child/replay")
    for index, r in enumerate(a["requests"]):
        require(r["id"] == index + 1 and r["batch"] == 1, "single batch receipt")
        require(r["args"] == ARGS[index], "exact child arguments")
        for arg in r["args"][1:]:
            require(not arg.startswith(("--dwarf", "--debug-dump", "--follow-links")) and
                    not (arg.startswith("-") and not arg.startswith("--") and "w" in arg),
                    "forbidden debug option")
        require(r["environment"] == {"DEBUGINFOD_URLS": ""}, "no symbol server")
        require(r["returncode"] == 0 and r["stderr_empty"] is True and
                r["external_file_evidence"] == [], "diagnostic/external-file refusal")
        require(r["raw_output_retained"] is False, "no raw response retention")
    require(a["safety"]["debug_server_urls"] == "" and
            a["safety"]["external_file_evidence"] == [], "no external evidence")
    require(all(x is False for k, x in a["safety"].items()
                if k not in {"debug_server_urls", "external_file_evidence"}),
            "static-only fresh boundary")
    actual = [{k: row[k] for k in ("start", "end_exclusive", "bytes")}
              for row in a["literals"]]
    require(actual == LITERALS, "no literal expansion")
    require(a["stop"]["closed"] is True and a["stop"]["further_analysis_permitted"] is False,
            "closed handoff")


def validate(i, a, v):
    scope_guard(a)
    require(digest(i) == INPUT_HASH, "independent inputs")
    require(digest(a) == ANALYSIS_HASH, "independent complete receipts")
    require(digest({"binary": v["anchors"], "source": v["inherited_source_citations"]}) ==
            ANCHOR_HASH, "independent anchors")
    require(digest(v) == VERDICT_HASH, "independent semantics and verdicts")
    require(i["repository_parent"] == v["repository_parent"] == PARENT, "parent")
    require(i["binary"]["logical_path"] == BINARY and
            i["binary"]["sha256"] == v["binary_sha256"] == BINARY_HASH, "binary pin")
    require(i["local_inputs"] == LOCAL_HASHES, "independent predecessor files")
    predecessor(i, v)
    before = datetime.datetime.strptime(a["batch"]["declared_utc"],
                "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc)
    for r in a["requests"]:
        require(before <= datetime.datetime.fromisoformat(r["started_utc"]) <=
                datetime.datetime.fromisoformat(r["finished_utc"]), "chronology")
        require(len(r["stdout_sha256"]) == 64 and r["stdout_bytes"] > 0, "response identity")
    cfg = a["cfg"]
    require(cfg["interval"] == ["0xb10", "0x14d0"] and
            len(cfg["basic_block_starts"]) == 108 and len(cfg["direct_calls"]) == 62 and
            len(cfg["ioctl_sites"]) == len(set(cfg["ioctl_sites"])) == 14, "fresh CFG counts")
    require(all(0xb10 <= int(x, 16) < 0x14d0 for x in cfg["basic_block_starts"]), "block bounds")
    require([r["address"] for r in cfg["direct_calls"] if r["target"] == "ioctl@plt"] ==
            cfg["ioctl_sites"], "direct ioctl count")
    for anchor in v["anchors"].values():
        lo, hi = int(anchor["start"], 16), int(anchor["end_exclusive"], 16)
        require((0xb10 <= lo < hi <= 0x14d0) or
                (lo, hi) in {(0x14d0, 0x14df), (0x1510, 0x152d)}, "anchor interval")
    require(len(v["requests"]) == 9, "command definitions")
    for row in v["requests"]:
        direction = 1 if row["number"] == 1 else 2
        require(int(row["request"], 16) ==
                (direction << 30) | (4 << 16) | (119 << 8) | row["number"],
                "numeric request encoding")
    require({k: p["verdict"] for k, p in v["predicates"].items()} == {
        "identity_fd": "resolved", "init_request": "resolved", "scalar_origin": "resolved",
        "local_return": "resolved", "command_order": "resolved", "mainline_boundary": "unresolved"},
        "six independent scoped verdicts")
    for p in v["predicates"].values():
        for k in ("claim", "conditions", "missing", "next_discriminator"):
            require(isinstance(p[k], str) and len(p[k]) > 30, "explicit boundary")
        require(bool(p["evidence"]) and set(p["evidence"]) <= set(v["anchors"]), "evidence")
    require(all(x is False for x in v["authority"].values()), "no authority")
    require(i["rights"]["private_binary"] is True and
            all(x is False for k, x in i["rights"].items() if k != "private_binary"),
            "privacy/rights")


def main():
    i, a, v = [json.loads((HERE / name).read_text())
               for name in ("inputs.json", "analysis.json", "verdicts.json")]
    validate(i, a, v)
    cases = [
        ("binary drift", lambda x, y, z: x["binary"].update(sha256="0" * 64)),
        ("callsite invention", lambda x, y, z: z["anchors"]["module_init"].update(start="0x12a0")),
        ("request invention", lambda x, y, z: z["requests"][4].update(request="0x80047705")),
        ("missing receipt", lambda x, y, z: y["requests"].pop()),
        ("co-mutated identity", lambda x, y, z:
         (x["binary"].update(sha256="0" * 64), z.update(binary_sha256="0" * 64))),
        ("no-hit deletion", lambda x, y, z: y["bounded_absences"].pop()),
        ("mainline prose promotion", lambda x, y, z:
         z["predicates"]["mainline_boundary"].update(claim="An upstream ABI has been established.")),
    ]
    for key, value in v["state_model"].items():
        wrong = not value if isinstance(value, bool) else "invented"
        if isinstance(value, list):
            wrong = list(reversed(value))
        cases.append((key, lambda x, y, z, key=key, wrong=wrong:
                      z["state_model"].update({key: wrong})))
    for key in v["authority"]:
        cases.append((key, lambda x, y, z, key=key: z["authority"].update({key: True})))
    for name, mutate in cases:
        x, y, z = copy.deepcopy((i, a, v))
        mutate(x, y, z)
        try:
            validate(x, y, z)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("refusal accepted: " + name)
    # These tests bypass complete hashes and exercise scope policy independently.
    guards = [
        ("second batch", lambda y: y["requests"][0].update(batch=2)),
        ("replay", lambda y: y["requests"].append(copy.deepcopy(y["requests"][-1]))),
        ("extra tool", lambda y: y["requests"].append(copy.deepcopy(y["requests"][1]))),
        ("extra interval", lambda y: y["batch"]["literal_intervals"].append(CODE)),
        ("expanded code", lambda y: y["batch"]["code_interval"].update(start="0xb00")),
        ("budget drift", lambda y: y["budgets"].update(analysis_batches=2)),
        ("second controller", lambda y: y["accounting"].update(controllers=2)),
        ("external file", lambda y: y["requests"][5]["args"].__setitem__(-1, "other-binary")),
        ("external evidence", lambda y: y["requests"][5].update(external_file_evidence=["other-file"])),
        ("diagnostic", lambda y: y["requests"][5].update(stderr_empty=False)),
        ("symbol server", lambda y: y["requests"][5]["environment"].update(DEBUGINFOD_URLS="server")),
    ]
    for option in ("-w", "-wf", "--debug-dump=frames", "--dwarf=follow-links",
                   "--dwarf-depth=1", "--dwarf-start=0"):
        guards.append((option, lambda y, option=option: y["requests"][5]["args"].insert(1, option)))
    for name, mutate in guards:
        y = copy.deepcopy(a)
        mutate(y)
        try:
            scope_guard(y)
        except ValueError:
            continue
        raise ValueError("independent scope refusal accepted: " + name)
    x = copy.deepcopy(i)
    x["inherited_source_files"][0]["size"] += 1
    try:
        predecessor(x, v)
    except ValueError:
        pass
    else:
        raise ValueError("independent predecessor refusal accepted")
    print(f"PASS: 6 predicates; 19 binary anchors; 6 receipts; "
          f"{len(cases) + len(guards) + 1} refusals; one fresh batch only.")


if __name__ == "__main__":
    main()
