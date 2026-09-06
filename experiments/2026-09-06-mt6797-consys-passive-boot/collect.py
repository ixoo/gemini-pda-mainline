#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify one bounded, already-captured passive CONSYS log stream.

The collector has no device command path: it reads a caller-supplied bounded
capture and writes only a mode-0600 sanitized result below the ignored output
root.  In particular, it cannot reach the inherited TOPRGU restart wrapper.
"""
from __future__ import annotations
import argparse, json, os, re, stat
from pathlib import Path

EXPECTED_RELEASE = "7.1.3-gemini-consys-passive"
EXPECTED_ARCH = "aarch64"
MAX_INPUT = 64 * 1024
RECORD = re.compile(r"^mt6797-consys-passive: state=BOUND generation=([1-9][0-9]*) client=wlan-passive power=0 reset=0 remap=0 protection=0 firmware=0 radio=0 dma=0$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
# Empty until the corrected passive-specific initramfs candidate is rebuilt
# and independently accepted. An empty pin makes every write refuse.
EXPECTED_CANDIDATE = ""
EXPECTED_INPUT_ID = ""
REPO = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO / "artifacts/consys-passive"
OUTPUT_ROOT = ARTIFACT_ROOT / "evidence"

class CollectionError(RuntimeError): pass
def require(ok, reason):
    if not ok: raise CollectionError(reason)

def classify(raw: bytes) -> dict[str, object]:
    require(len(raw) <= MAX_INPUT, "capture exceeded 64 KiB")
    try: lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc: raise CollectionError("capture is not ASCII") from exc
    require(len(lines) == 7, "capture schema/record count changed")
    fields = {}
    keys = ("release", "architecture", "boot_id", "transport", "logger_healthy")
    for line, expected in zip(lines[:5], keys, strict=True):
        require(line.startswith(expected + "=") and line.count("=") == 1,
                f"missing or reordered {expected}")
        key, value = line.split("=", 1)
        fields[key] = value
    require(lines[5] == "log_begin", "missing log begin")
    match = RECORD.fullmatch(lines[6]); require(match is not None, "passive BOUND record mismatch")
    require(fields.get("release") == EXPECTED_RELEASE and fields.get("architecture") == EXPECTED_ARCH, "kernel identity mismatch")
    require(UUID.fullmatch(fields.get("boot_id", "")) is not None, "boot identity malformed")
    require(fields.get("transport") == "authenticated" and fields.get("logger_healthy") == "yes", "transport/logger admission failed")
    return {"release": fields["release"], "architecture": fields["architecture"], "boot_id": fields["boot_id"], "generation": int(match.group(1)), "client": "wlan-passive", "state": "BOUND", "effect_counters": {k: 0 for k in ("power", "reset", "remap", "protection", "firmware", "radio", "dma")}}

def private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = path.lstat()
    require(not path.is_symlink() and stat.S_ISDIR(info.st_mode) and
            stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid(),
            "output directory is not private")


def write_result(result: dict, deployment_id: str) -> Path:
    require(SHA256.fullmatch(EXPECTED_CANDIDATE) is not None and
            SHA256.fullmatch(EXPECTED_INPUT_ID) is not None and
            UUID.fullmatch(deployment_id) is not None,
            "fixed candidate/input/deployment binding is malformed")
    private_directory(ARTIFACT_ROOT)
    private_directory(OUTPUT_ROOT)
    candidate_root = OUTPUT_ROOT / ("candidate-" + EXPECTED_CANDIDATE)
    private_directory(candidate_root)
    deployment_root = candidate_root / ("deployment-" + deployment_id)
    private_directory(deployment_root)
    result.update({"candidate_sha256": EXPECTED_CANDIDATE,
                   "input_id": EXPECTED_INPUT_ID,
                   "deployment_id": deployment_id})
    path = deployment_root / ("boot-" + str(result["boot_id"]) + ".json")
    fd = path.open("x", encoding="utf-8")
    try: fd.write(json.dumps(result, sort_keys=True) + "\n")
    finally: fd.close()
    path.chmod(0o600)
    return path

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--input-log", type=Path, required=True)
    p.add_argument("--deployment-id", required=True); a=p.parse_args()
    st=a.input_log.lstat(); require(stat.S_ISREG(st.st_mode) and not a.input_log.is_symlink() and st.st_nlink == 1 and st.st_size <= MAX_INPUT, "input log is unsafe")
    result=classify(a.input_log.read_bytes())
    path=write_result(result, a.deployment_id)
    print(f"classification=pass\nresult={path}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
