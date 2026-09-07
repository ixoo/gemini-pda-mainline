#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline receipt integrity and refusal tests; no private access or hardware proof."""
import copy
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PINS = {
    "inputs.json": "32ac9645738278127ea0cc033a665476cc022fa313e2813d05a45bd8e0eed2c4",
    "inventory.json": "5fa2662168923535e4a82ca80c2801c18d65aeb6d99152558231ac29a2ac0d77",
    "evidence-matrix.json": "ba88273115fdd967d084c8a91a6ac75e4fd0dd44a035607ecad69a9f2f1aad4b",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def validate(blobs, overrides=None):
    require(set(blobs) == set(PINS), "record inventory changed")
    parsed = {}
    for name, expected in PINS.items():
        require(hashlib.sha256(blobs[name]).hexdigest() == expected,
                "frozen receipt changed: " + name)
        parsed[name] = json.loads(blobs[name], object_pairs_hook=unique_pairs)
    records = parsed["inputs.json"]["records"]
    require(len(records) == 15, "repository bound")
    for record in records:
        path = record["path"]
        data = (overrides or {}).get(path)
        if data is None:
            data = (ROOT / path).read_bytes()
        require(len(data) == record["size"], "input size: " + record["id"])
        require(hashlib.sha256(data).hexdigest() == record["sha256"],
                "input hash: " + record["id"])
    private = parsed["inventory.json"]["private"]
    require(private["entries_examined"] <= private["inventory_entry_cap"],
            "inventory cap")
    require(private["selected_count"] <= private["selection_cap_records"]
            and private["selected_bytes"] <= private["selection_cap_bytes"],
            "selection cap")
    require(private["selected_count"] == len(private["selected_records"]) == 0,
            "no selected private record")
    matrix = parsed["evidence-matrix.json"]
    ids = {row["id"] for row in matrix["predicates"]}
    require(len(ids) == len(matrix["predicates"]) == 5, "predicate inventory")
    require(matrix["accepted_predicates"] == 0 and matrix["cycle_id"] is None
            and matrix["cycle_success"] is None and not matrix["ordering_proved"],
            "unsupported cycle promotion")
    for row in matrix["predicates"]:
        require(row["verdict"] == "missing-runtime-join"
                and row["observation"] is None and row["cycle_id"] is None
                and row["success_predicate"] is None, "runtime promotion")
        require(set(row["source_records"]) <= {r["id"] for r in records},
                "unresolved citation")
    require(all(v is False for v in matrix["effects"].values()), "effect promotion")
    return parsed


def leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + (key,))
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaves(child, path + (index,))
    else:
        yield path, value


def changed(value):
    if isinstance(value, bool):
        return not value
    if value is None:
        return "unsupported"
    if isinstance(value, int):
        return value + 1
    if isinstance(value, list):
        return ["unsupported"]
    return value + "-mutated"


def put(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def expect_refusal(blobs, overrides=None):
    try:
        validate(blobs, overrides)
    except ValueError:
        return
    raise ValueError("mutation accepted")


def main():
    blobs = {name: (BASE / name).read_bytes() for name in PINS}
    parsed = validate(blobs)
    count = 0
    for name, document in parsed.items():
        for path, value in leaves(document):
            mutant = copy.deepcopy(document)
            put(mutant, path, changed(value))
            trial = dict(blobs)
            trial[name] = (json.dumps(mutant, indent=2) + "\n").encode()
            expect_refusal(trial)
            count += 1
        for key in document:
            mutant = copy.deepcopy(document)
            del mutant[key]
            trial = dict(blobs)
            trial[name] = (json.dumps(mutant, indent=2) + "\n").encode()
            expect_refusal(trial)
            count += 1
    for record in parsed["inputs.json"]["records"]:
        data = (ROOT / record["path"]).read_bytes()
        mutant = bytes([data[0] ^ 1]) + data[1:]
        expect_refusal(blobs, {record["path"]: mutant})
        count += 1
    print("receipt=pass repository_hashes=15 mutation_refusals=" + str(count))
    print("semantic_runtime_proof=none private_access=none")


if __name__ == "__main__":
    main()
