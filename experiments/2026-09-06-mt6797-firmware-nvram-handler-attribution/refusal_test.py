#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise refusals using in-memory copies of the sanitized receipt only."""

from copy import deepcopy
from pathlib import Path
import runpy


def main():
    api = runpy.run_path(str(Path(__file__).with_name("verify.py")))
    baseline = api["load_receipt"]()
    verify, require = api["verify"], api["require"]
    verify(baseline)
    cases = []

    def add(name, mutate, reason):
        cases.append((name, mutate, reason))

    def swap_input(record):
        a, b = record["inputs"][:2]
        a["path"], a["sha256"] = b["path"], b["sha256"]

    add("valid-path/hash-swap", swap_input, "frozen input identity/purpose")
    add("input-rights", lambda r: r["inputs"][0].__setitem__("rights", "expanded"), "input rights")
    add("input-purpose", lambda r: r["inputs"][0].__setitem__("purpose", "expanded"), "frozen input identity/purpose")
    add("extra-input", lambda r: r["inputs"].append(deepcopy(r["inputs"][0])), "input inventory")
    add("missing-input", lambda r: r["inputs"].pop(), "input inventory")
    add("parent", lambda r: r.__setitem__("parent_commit", "0" * 40), "parent")
    for kind in ("firmware", "retained_analysis", "import_log", "scripts"):
        add(kind + "-identity", lambda r, k=kind: r["private_identity"][k].__setitem__("sha256", "0" * 64), "private identity")
        add(kind + "-rights", lambda r, k=kind: r["private_identity"][k].__setitem__("rights", "redistributable"), "frozen receipt")
    add("private-path", lambda r: r["private_identity"]["firmware"].__setitem__("path", "unadmitted"), "frozen receipt")
    for field in ("section_window_identity_independently_verified", "stored_option_presence_independently_verified"):
        add(field, lambda r, f=field: r["private_identity"].__setitem__(f, True), "incomplete prerequisites")
    add("fake-attempt", lambda r: r["branches"][0]["attempts"].append({"number": 1}), "no fabricated attempts")
    add("extra-branch", lambda r: r["branches"].append(deepcopy(r["branches"][0])), "branch inventory")
    add("invented-zero-nodes", lambda r: r["branches"][0].__setitem__("node_measurements", 0), "unmeasured graph counts")
    add("invented-exhaustion", lambda r: r["branches"][1].__setitem__("queue_exhausted", True), "unmeasured graph counts")
    for name, predicates in api["EXPECTED_VERDICTS"].items():
        add(name + "-resolved", lambda r, n=name: r["verdicts"][n].__setitem__("verdict", "resolved"), "unresolved decision")
        add(name + "-contradicted", lambda r, n=name: r["verdicts"][n].__setitem__("verdict", "contradicted"), "unresolved decision")
        add(name + "-predicate", lambda r, n=name, p=predicates[0]: r["verdicts"][n].__setitem__(p, True), "unproved predicate")
    for field in sorted(api["EXPECTED_BOUNDARIES"]):
        add(field, lambda r, f=field: r["boundaries"].__setitem__(f, True), "no-policy/no-runtime boundary")
    add("retention-changed", lambda r: r["retention"].__setitem__("private_files_added", 1), "preservation")
    add("next-check-changed", lambda r: r["verdicts"]["target_contract"].__setitem__("next_discriminator", "unreviewed action"), "frozen receipt")
    for name, mutate, reason in cases:
        candidate = deepcopy(baseline)
        mutate(candidate)
        try:
            verify(candidate)
        except ValueError as error:
            require(str(error) == reason, name + ": wrong refusal")
        else:
            raise ValueError(name + ": accepted mutation")
    verify(baseline)
    require(baseline == api["load_receipt"](), "original receipt changed")
    print(f"Refusal fixtures passed: {len(cases)} mutations rejected; unchanged controls passed")


if __name__ == "__main__":
    main()
