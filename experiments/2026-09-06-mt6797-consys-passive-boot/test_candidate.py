#!/usr/bin/env python3
"""Assert-free candidate/container refusal fixtures."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "scripts/validate-candidate.py"
SPEC = importlib.util.spec_from_file_location("consys_validator", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("validator unavailable")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
CANDIDATE = (HERE.parents[1] / "artifacts/consys-passive/candidates/"
             "candidate-a487c5b33d100e75271d56b02535cb2b31f951d745090a54e5ee1287af4c800d")


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise AssertionError(reason)


def refuse(fn, text: str) -> None:
    try:
        fn()
    except (ValueError, KeyError, OSError) as exc:
        check(text in str(exc), f"expected {text!r}, got {exc!r}")
    else:
        raise AssertionError(f"accepted mutation: {text}")


def clone_payload(target: Path) -> None:
    target.mkdir(mode=0o700)
    for name in ("boot2-padded.img", "Image.gz", "board.dtb", "initramfs.img"):
        shutil.copyfile(CANDIDATE / name, target / name)
        (target / name).chmod(0o600)


def rehash(manifest: dict, padded: bytes) -> None:
    raw = padded[:manifest["raw_size"]]
    manifest["raw_sha256"] = V.C.sha(raw)
    manifest["padded_sha256"] = V.C.sha(padded)


def main() -> int:
    check(CANDIDATE.is_dir(), "frozen private candidate is missing")
    manifest = json.loads((CANDIDATE / "candidate.json").read_text(encoding="utf-8"))
    V.validate_manifest(manifest, CANDIDATE.name)
    V.validate_container(CANDIDATE, manifest)
    cases = 2
    parse, _ = V.C.load_newc_tools(HERE.parents[1])
    stale_members = parse((CANDIDATE / "initramfs.img").read_bytes())
    refuse(lambda: V.validate_runtime_identities(stale_members, manifest["input_id"]),
           "passive release gate")
    cases += 1
    init_source = (HERE / "initramfs/init").read_bytes()
    gate = b'[ "$(/bin/busybox uname -r)" = 7.1.3-gemini-consys-passive ]'
    check(init_source.count(gate) == 1 and
          init_source.find(gate) < init_source.find(b"/bin/usb-auth &"),
          "authenticated USB is not reachable after the passive uname gate")
    check(not any(token in init_source for token in V.C.STALE_IDENTITY_TEXT),
          "published init retains a stale TOPRGU identity")
    cases += 1

    for key, value in (
        ("physical_admission", True), ("release", "wrong"),
        ("package_commit", "0" * 40), ("source_commit", "0" * 40),
        ("serviceability_dtb_sha256", "0" * 64), ("assembly_replays", 1),
    ):
        changed = dict(manifest)
        changed[key] = value
        refuse(lambda changed=changed: V.validate_manifest(changed, CANDIDATE.name),
               "manifest identity")
        cases += 1
    changed = dict(manifest)
    changed["unknown"] = 1
    refuse(lambda: V.validate_manifest(changed, CANDIDATE.name), "manifest schema")
    cases += 1

    with tempfile.TemporaryDirectory(prefix="consys-candidate-fixture-") as tmp:
        candidate = Path(tmp) / CANDIDATE.name
        clone_payload(candidate)
        original = (candidate / "boot2-padded.img").read_bytes()
        mutations = (
            (2048, "kernel/DTB payload"),
            (64, "cmdline or reserved"),
            (576, "payload ID"),
            (manifest["raw_size"] + 1, "padding is not zero"),
        )
        for offset, reason in mutations:
            padded = bytearray(original)
            padded[offset] ^= 1
            changed = json.loads(json.dumps(manifest))
            rehash(changed, padded)
            (candidate / "boot2-padded.img").write_bytes(padded)
            (candidate / "boot2-padded.img").chmod(0o600)
            refuse(lambda changed=changed: V.validate_container(candidate, changed), reason)
            cases += 1

    source = (HERE / "collect.py").read_text(encoding="utf-8")
    check("--output" not in source and "reboot" not in source,
          "collector gained an arbitrary output or reboot path")
    print(f"passive candidate fixtures: PASS cases={cases + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
