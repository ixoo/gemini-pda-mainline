#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mutate in-memory evidence records; never rewrite evidence or access hardware."""

from copy import deepcopy
from pathlib import Path
import runpy


def main():
    api = runpy.run_path(str(Path(__file__).with_name("decode.py")))
    verify = api["verify"]
    require = api["require"]
    baseline = api["load_records"]()
    verify(records=baseline, quiet=True)
    cases = []

    def add(name, mutate, diagnostic):
        cases.append((name, mutate, diagnostic))

    def replace_record_pair(records):
        # Both point at an existing admitted file and its correct checksum.
        # Identity of the named record must nevertheless refuse the swap.
        first, second = records["inputs"]["records"][:2]
        first["path"], first["sha256"] = second["path"], second["sha256"]

    add("record-path-and-valid-sha-co-mutation", replace_record_pair, "frozen metadata: records")
    for group in ("sources", "records", "private_artifacts"):
        for field in ("rights", "purpose"):
            add(group + "-" + field, lambda r, g=group, f=field: r["inputs"][g][0].__setitem__(f, "expanded authority"), "frozen metadata: " + group)
        add(group + "-extra", lambda r, g=group: r["inputs"][g].append(deepcopy(r["inputs"][g][0])), "frozen metadata: " + group)
        add(group + "-missing", lambda r, g=group: r["inputs"][g].pop(), "frozen metadata: " + group)
    for name in ("ap", "consys", "wlan"):
        add(name + "-routing-true", lambda r, n=name: r["verdicts"]["verdicts"][n].__setitem__("hardware_routing_established", True), "unestablished routing: " + name)
        add(name + "-routing-missing", lambda r, n=name: r["verdicts"]["verdicts"][n].pop("hardware_routing_established"), "unestablished routing: " + name)
    for name in ("priority_rule_established", "active_region_applicability_established"):
        add(name + "-true", lambda r, n=name: r["verdicts"]["verdicts"]["overlap_priority"].__setitem__(n, True), "unestablished overlap: " + name)
        add(name + "-missing", lambda r, n=name: r["verdicts"]["verdicts"]["overlap_priority"].pop(n), "unestablished overlap: " + name)
    add("runtime-region-promoted", lambda r: r["verdicts"].__setitem__("runtime_region_state", "active regions verified"), "unknown runtime region state")
    add("policy-allowed", lambda r: r["verdicts"].__setitem__("policy_selection_allowed", True), "policy must remain blocked")
    add("selected-path-extra", lambda r: r["inputs"]["tree"]["selected_paths"].append(deepcopy(r["inputs"]["tree"]["selected_paths"][0])), "exact selected tree entries")
    add("selected-path-missing", lambda r: r["inputs"]["tree"]["selected_paths"].pop(), "exact selected tree entries")
    add("selected-path-value", lambda r: r["inputs"]["tree"]["selected_paths"][0].__setitem__("path", "unadmitted.c"), "exact selected tree entries")
    add("source-path-and-sha", lambda r: r["inputs"]["sources"][0].update(path=r["inputs"]["sources"][1]["path"], sha256=r["inputs"]["sources"][1]["sha256"]), "frozen metadata: sources")
    add("private-path-added", lambda r: r["inputs"]["private_artifacts"][0].__setitem__("path", "not-an-admitted-path"), "frozen metadata: private_artifacts")
    add("private-interpretation-promoted", lambda r: r["inputs"]["private_artifacts"][0].__setitem__("new_interpretation", True), "frozen metadata: private_artifacts")
    add("unknown-supporting-record", lambda r: r["search-attempts"]["branches"][0]["attempts"][0]["supporting_record_ids"].append("unadmitted"), "supporting record membership")
    add("supporting-record-queried", lambda r: r["search-attempts"]["branches"][0]["attempts"][0].__setitem__("supporting_records_queried", True), "supporting records not queried")
    add("query-inventory-missing", lambda r: r["search-attempts"]["branches"][0]["attempts"][0]["inventory"].pop(), "query inventory cardinality")

    for name, mutate, diagnostic in cases:
        candidate = deepcopy(baseline)
        mutate(candidate)
        try:
            verify(records=candidate, quiet=True)
        except ValueError as error:
            require(str(error) == diagnostic, name + ": unexpected refusal: " + str(error))
        else:
            raise ValueError(name + ": mutation accepted")
    verify(records=baseline, quiet=True)
    require(baseline == api["load_records"](), "fixtures changed baseline evidence")
    print(f"Refusal fixtures passed: {len(cases)} mutations rejected; unchanged controls passed")


if __name__ == "__main__":
    main()
