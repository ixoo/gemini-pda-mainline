#!/usr/bin/env python3
"""Exercise Candidate AK's pre-build identity and safety boundaries."""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True

import candidate_ak as ak

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = pathlib.Path(__file__).resolve().parent


def fail(message: str) -> None:
    raise ValueError(message)


def expect_rejection(action, fragment: str) -> None:
    try:
        action()
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        if fragment not in str(exc):
            fail(f"wrong rejection for {fragment!r}: {exc}")
    else:
        fail(f"mutation was accepted: {fragment}")


def load_local(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"candidate_ak_test_{path.stem}", path)
    if spec is None or spec.loader is None:
        fail(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    fragment = ak.read_regular(ROOT / ak.FRAGMENT_REL, "AK fragment")
    if fragment != ak.EXPECTED_FRAGMENT or ak.digest_bytes(fragment) != ak.FRAGMENT_SHA256:
        fail("AK fragment identity changed")
    tokens = ak.CMDLINE.split()
    if tokens.count("maxcpus=10") != 1 or "maxcpus=1" in tokens:
        fail("maxcpus=10 was confused with its maxcpus=1 prefix")

    manifest = ak.read_regular(ROOT / "kernel/manifest.json", "kernel manifest")
    ak.validate_manifest_profile(manifest, "kernel manifest")
    value = json.loads(manifest)
    mutated = json.loads(manifest)
    mutated["config"]["profiles"][ak.PROFILE]["fragments"][-1] = (
        "configs/gemini-a72-reject-cpu8-request.fragment"
    )
    expect_rejection(
        lambda: ak.validate_manifest_profile(
            (json.dumps(mutated) + "\n").encode(), "mutated manifest"
        ),
        "lacks exact Candidate AK profile",
    )
    if value["config"]["profiles"][ak.PROFILE]["patch_series"] != ak.SERIES_REL:
        fail("AK profile does not select the exact rejection series")
    package_validator = load_local("validate-package.py")
    synthetic_image = ak.CMDLINE.encode() + b"\0" + ak.CMDLINE.encode()
    if b"maxcpus=1" not in synthetic_image:
        fail("prefix-collision fixture is ineffective")
    package_validator.validate_plaintext_cmdline(synthetic_image)
    aj_manifest = json.loads(manifest)
    del aj_manifest["config"]["profiles"][ak.PROFILE]
    package_validator.validate_manifest_delta(
        (json.dumps(aj_manifest) + "\n").encode(), manifest
    )
    drifted = json.loads(manifest)
    drifted["config"]["profiles"][ak.PROFILE]["base"] = "tinyconfig"
    expect_rejection(
        lambda: package_validator.validate_manifest_delta(
            (json.dumps(aj_manifest) + "\n").encode(),
            (json.dumps(drifted) + "\n").encode(),
        ),
        "not exact AJ plus one profile",
    )
    series = ak.read_regular(ROOT / ak.SERIES_REL, "AK series")
    if ak.digest_bytes(series) != ak.SERIES_SHA256 or b"0093" in series:
        fail("AK series changed or selected unsafe patch 0093")

    # Reject a preloaded namesake module even when it copies AJ's label.
    original = sys.modules.pop("candidate_aj", None)
    fake = types.ModuleType("candidate_aj")
    fake.EXPERIMENT = ak.AJ_EXPERIMENT
    fake.__file__ = __file__
    sys.modules["candidate_aj"] = fake
    try:
        expect_rejection(
            lambda: ak.load_aj_module("validate-profile.py", "poisoned_aj_helper"),
            "unexpected candidate_aj module",
        )
    finally:
        sys.modules.pop("candidate_aj", None)
        if original is not None:
            sys.modules["candidate_aj"] = original

    package_unpinned = any(
        value.startswith("TO_PIN_")
        for value in (
            ak.IMAGE_SHA256, ak.IMAGE_SIZE, ak.IMAGE_GZ_SHA256, ak.IMAGE_GZ_SIZE,
            ak.SYSTEM_MAP_SHA256, ak.PACKAGE_DTB_SHA256, ak.GATE_AUDIT_SHA256,
            *ak.PACKAGE_MANIFEST_SHA256S,
        )
    )
    if package_unpinned:
        expect_rejection(ak.require_package_pins, "package identities remain unpinned")
    else:
        ak.require_package_pins()
    artifact_unpinned = any(
        value.startswith("TO_PIN_")
        for value in (ak.RAW_SHA256, ak.RAW_SIZE, ak.ARTIFACT_MANIFEST_SHA256, ak.PADDED_SHA256)
    )
    if package_unpinned or artifact_unpinned:
        expect_rejection(
            ak.require_artifact_pins,
            "package identities remain unpinned" if package_unpinned else "artifact identities remain unpinned",
        )
    else:
        ak.require_artifact_pins()

    for shell in ("build-candidate-ak.sh", "verify-padding-reproduction.sh"):
        result = subprocess.run(["bash", "-n", SCRIPTS / shell], capture_output=True)
        if result.returncode or result.stderr:
            fail(f"shell syntax failed: {shell}")

    profile = subprocess.run(
        [sys.executable, SCRIPTS / "validate-profile.py", "--repository", ROOT],
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if profile.returncode or b"validation=candidate-ak-profile\n" not in profile.stdout:
        fail("AK profile validator did not pass exact repository inputs")

    # The AK adapter must obtain AJ's generic finalizer without accidentally
    # re-applying AJ binary pins or AJ member names to the AK tree.
    finalizer = load_local("finalize-artifact.py")
    with tempfile.TemporaryDirectory(prefix="candidate-ak-finalizer-") as raw:
        root = pathlib.Path(raw)
        for member in finalizer.PRE_MANIFEST_MEMBERS:
            path = root / member
            path.write_bytes(b"fixture\n")
            path.chmod(0o755 if member in finalizer.EXECUTABLE_MEMBERS else 0o600)
        generic = finalizer.foundation()
        generic.finalize(root)
        members = generic.verify(root)
        if set(members) != finalizer.EXPECTED_MEMBERS:
            fail("AK finalizer adapter retained AJ member names")

    installer = load_local("derive-installer.py")
    calibration = installer.Calibration("1" * 64, ak.AJ_RAW_SIZE, "2" * 64, "3" * 64)
    with tempfile.TemporaryDirectory(prefix="candidate-ak-static-") as raw:
        aj_installer = pathlib.Path(raw) / "install-candidate-aj-boot2.sh"
        result = subprocess.run(
            [
                sys.executable,
                ROOT / "experiments" / ak.AJ_EXPERIMENT / "scripts/derive-installer.py",
                "--output",
                aj_installer,
            ],
            capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if result.returncode:
            fail("exact Candidate AJ installer did not reconstruct")
        source = aj_installer.read_bytes()
        text = installer.derive_text(source, calibration)
        if installer.restore_aj_contract(text, calibration).encode() != source:
            fail("AK installer does not restore the exact AJ executable contract")
        required = (
            "install-candidate-ak-boot2.sh",
            f"readonly EXPECTED_CURRENT_AJ_PADDED_SHA256={ak.AJ_PADDED_SHA256}",
            "candidate-AK-a72-reject-cpu9-11111111",
            "gemini-a72-reject-cpu9-request.boot.img",
            "reboot_or_shutdown_performed=no",
        )
        if any(marker not in text for marker in required):
            fail("AK installer transform lacks an exact safety/identity marker")
        if "candidate-AJ-a72-reject-cpu8-a3c649b5" in text:
            fail("AK installer retained AJ candidate identity as its target")
    if installer.AK_IDENTITY_SHA256.startswith("TO_PIN_"):
        expect_rejection(installer.production_calibration, "identity source remains unpinned")
    else:
        selected = installer.production_calibration()
        if selected.padded_sha256 == installer.AJ_PADDED_SHA256:
            fail("production installer accepts AJ as AK output")

    print("validation=candidate-ak-static-mutations")
    print("profile=exact-aj-plus-one-fragment")
    print("maxcpus-prefix-collision=rejected")
    print("preloaded-aj-module-poisoning=rejected")
    print("packaged-manifest-delta=exact-aj-plus-ak")
    print("package-and-artifact-pin-gates=validated")
    print("installer-foundation=exact-aj-restorable")
    print("artifact-finalizer=ak-member-contract")
    print("installer-predecessor=exact-aj-padded")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
