#!/usr/bin/env python3
"""Derive Candidate AJ's guarded boot2 installer from exact Candidate AI."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass


sys.dont_write_bytecode = True


CANDIDATE_AJ_SOURCE_SHA256 = (
    "77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1"
)


def verify_candidate_aj_source(path: pathlib.Path) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Candidate AJ identity module is unsafe")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    if hasher.hexdigest() != CANDIDATE_AJ_SOURCE_SHA256:
        raise RuntimeError("Candidate AJ identity module changed")


_candidate_aj_path = pathlib.Path(__file__).resolve().with_name("candidate_aj.py")
verify_candidate_aj_source(_candidate_aj_path)
_candidate_aj_spec = importlib.util.spec_from_file_location(
    "candidate_aj_installer_pinned_identities", _candidate_aj_path
)
if _candidate_aj_spec is None or _candidate_aj_spec.loader is None:
    raise RuntimeError("cannot load pinned Candidate AJ identity module")
aj = importlib.util.module_from_spec(_candidate_aj_spec)
sys.modules[_candidate_aj_spec.name] = aj
_candidate_aj_spec.loader.exec_module(aj)


BOOT2_SIZE = 16 * 1024 * 1024
AI_DERIVER_SHA256 = (
    "7f9a912f1a9cc05372ad95b5fb6a9dcc8253eda85635358572556362a504e99e"
)
AI_INSTALLER_SHA256 = (
    "8d9d0ac258fdb031e840b2042c7abc1fc1fdf01cf6c6893bc24c234b6d9054f6"
)
AI_SOURCE_PREDECESSOR_SHA256 = (
    "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012"
)
EXPECTED_AI_PADDED_SHA256 = (
    "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
)
EXPECTED_AI_ARTIFACT_MANIFEST_SHA256 = (
    "b8c2953dd07e2a84a05e99f7bd0a981cbe593e928ba7507f16691279d82fa8cc"
)
AI_ARTIFACT_DIR = "candidate-AI-a72-reject-gate-1ecfc787"
AI_BOOT_FILENAME = "gemini-a72-reject-gate-kernel-split.boot.img"
AJ_ARTIFACT_PREFIX = "candidate-AJ-a72-reject-cpu8-"
AJ_BOOT_FILENAME = "gemini-a72-reject-cpu8-request.boot.img"

HEX256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Calibration:
    raw_sha256: str
    raw_size: str
    artifact_manifest_sha256: str
    padded_sha256: str


_ai_deriver = None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer foundation token count changed: {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def validate_production_pins() -> None:
    """Reject unresolved or drifted identities before caller-path I/O."""

    aj.require_artifact_pins()
    exact = (
        (
            aj.AI_SCRIPT_HASHES.get("derive-installer.py"),
            AI_DERIVER_SHA256,
            "Candidate AI installer deriver pin",
        ),
        (aj.AI_INSTALLER_SHA256, AI_INSTALLER_SHA256, "Candidate AI installer pin"),
        (
            aj.AI_PADDED_SHA256,
            EXPECTED_AI_PADDED_SHA256,
            "Candidate AI installed predecessor pin",
        ),
        (
            aj.AI_ARTIFACT_MANIFEST_SHA256,
            EXPECTED_AI_ARTIFACT_MANIFEST_SHA256,
            "Candidate AI artifact manifest pin",
        ),
        (aj.EXPERIMENT, "2026-07-22-a72-reject-cpu8-request", "AJ experiment"),
        (aj.CANDIDATE, "AJ", "AJ label"),
        (aj.BOOT_MEMBER, AJ_BOOT_FILENAME, "AJ boot member"),
    )
    for actual, expected, label in exact:
        if actual != expected:
            raise ValueError(f"{label} changed")


def production_calibration() -> Calibration:
    validate_production_pins()
    return Calibration(
        aj.RAW_SHA256,
        aj.RAW_SIZE,
        aj.ARTIFACT_MANIFEST_SHA256,
        aj.PADDED_SHA256,
    )


def artifact_directory(calibration: Calibration) -> str:
    return AJ_ARTIFACT_PREFIX + calibration.raw_sha256[:8]


def validate_calibration(calibration: Calibration) -> None:
    values = (
        ("AJ_RAW_SHA256", calibration.raw_sha256),
        ("AJ_RAW_SIZE", calibration.raw_size),
        ("AJ_ARTIFACT_MANIFEST_SHA256", calibration.artifact_manifest_sha256),
        ("AJ_PADDED_SHA256", calibration.padded_sha256),
    )
    for name, value in values:
        if value.startswith("TO_PIN_"):
            raise ValueError(f"Candidate AJ calibration remains unpinned: {name}")
    for name, value in (
        ("raw", calibration.raw_sha256),
        ("artifact manifest", calibration.artifact_manifest_sha256),
        ("padded", calibration.padded_sha256),
    ):
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AJ {name} SHA-256 is malformed")
    if not calibration.raw_size.isdecimal():
        raise ValueError("Candidate AJ raw size is malformed")
    raw_size = int(calibration.raw_size)
    if not 0 < raw_size <= BOOT2_SIZE:
        raise ValueError("Candidate AJ raw size is invalid or exceeds boot2")
    if calibration.raw_sha256 == aj.AI_RAW_SHA256:
        raise ValueError("Candidate AJ raw identity equals Candidate AI")
    if calibration.artifact_manifest_sha256 == aj.AI_ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AJ artifact manifest identity equals Candidate AI")
    if calibration.padded_sha256 == EXPECTED_AI_PADDED_SHA256:
        raise ValueError(
            "Candidate AJ padded identity equals installed Candidate AI"
        )


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parents[2]


def ai_deriver_path(root: pathlib.Path | None = None) -> pathlib.Path:
    base = root if root is not None else repo_root()
    return (
        base
        / "experiments/2026-07-22-a72-reject-gate-kernel-split"
        / "scripts/derive-installer.py"
    )


def verify_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is unsafe")


def load_ai_deriver():
    global _ai_deriver
    if _ai_deriver is not None:
        return _ai_deriver
    if aj.AI_SCRIPT_HASHES.get("derive-installer.py") != AI_DERIVER_SHA256:
        raise ValueError("Candidate AI installer deriver pin table changed")
    path = ai_deriver_path()
    verify_regular(path, "Candidate AI installer deriver")
    if digest_path(path) != AI_DERIVER_SHA256:
        raise ValueError("Candidate AI installer deriver identity changed")
    spec = importlib.util.spec_from_file_location("candidate_aj_exact_ai_deriver", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load exact Candidate AI installer deriver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _ai_deriver = module
    return module


def identity_replacements(calibration: Calibration) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{AI_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(calibration)}"',
            1,
        ),
        ("gemini-a72-reject-gate-kernel-split", "gemini-a72-reject-cpu8-request", 1),
        (
            "2026-07-22-a72-reject-gate-kernel-split",
            "2026-07-22-a72-reject-cpu8-request",
            2,
        ),
        ("Candidate AI", "Candidate AJ", 7),
        ("candidate-ai", "candidate-aj", 14),
        ("AI_RAW", "AJ_RAW", 16),
        ("AI_PADDED", "AJ_PADDED", 11),
        (
            "EXPECTED_CURRENT_AH_PADDED_SHA256",
            "EXPECTED_CURRENT_AI_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AI", "candidate_label=AJ", 2),
        (
            "AH-installed-readback-verified",
            "AI-installed-readback-verified",
            4,
        ),
    )


def aj_contract_additions(calibration: Calibration) -> tuple[tuple[str, str], ...]:
    manifest_guard = (
        '[[ -f "$candidate_manifest" && ! -L "$candidate_manifest" ]] || \\\n'
        "\tdie 'candidate directory lacks a regular non-symlink SHA256SUMS manifest'\n"
    )
    guarded_manifest = manifest_guard + (
        'candidate_manifest_sha256="$(checked_sha256_file "$candidate_manifest")"\n'
        '[[ "$candidate_manifest_sha256" == "$AJ_ARTIFACT_MANIFEST_SHA256" ]] || \\\n'
        "\tdie 'candidate SHA256SUMS manifest is not the exact reproduced Candidate AJ manifest'\n"
    )
    initial_arch = (
        '[[ "$(uname -m)" == aarch64 ]] || {\n'
        "\tprintf 'error: remote architecture is not aarch64\\n' >&2\n"
        "\texit 2\n"
        "}\n"
    )
    initial_gemian = initial_arch + (
        '[[ "$(uname -r)" == 3.18.41+ ]] || {\n'
        "\tprintf 'error: remote kernel is not exact known-good Gemian 3.18.41+\\n' >&2\n"
        "\texit 2\n"
        "}\n"
    )
    initial_root_parent = (
        '[[ "$(lsblk -dnro TYPE "$active_root")" == part && \\\n'
        '\t"$(lsblk -dnro PKNAME "$active_root")" == mmcblk0 ]] || {\n'
        "\tprintf 'error: active root is not a partition of the expected internal MMC\\n' >&2\n"
        "\texit 2\n"
        "}\n"
    )
    initial_exact_root = initial_root_parent + (
        '[[ "$active_root" == /dev/mmcblk0p29 ]] || {\n'
        "\tprintf 'error: active root is not exact known-good Gemian /dev/mmcblk0p29: %s\\n' "
        '"$active_root" >&2\n'
        "\texit 2\n"
        "}\n"
    )
    gate_arch = (
        '[[ "$(uname -m)" == aarch64 ]] || fail '
        "'remote architecture is not aarch64'\n"
    )
    gate_gemian = gate_arch + (
        '[[ "$(uname -r)" == 3.18.41+ ]] || fail '
        "'remote kernel is not exact known-good Gemian 3.18.41+'\n"
        '[[ "$EXPECTED_ROOT" == /dev/mmcblk0p29 ]] || fail '
        "'expected root is not exact known-good Gemian /dev/mmcblk0p29'\n"
    )
    return (
        (
            "The candidate raw size/hash, padded hash, and exact current "
            "AI-installed-readback-verified\n",
            "The candidate raw size/hash, exact artifact-manifest hash, padded hash, "
            "and exact\ncurrent AI-installed-readback-verified\n",
        ),
        (
            f"readonly AJ_PADDED_SHA256={calibration.padded_sha256}\n",
            f"readonly AJ_PADDED_SHA256={calibration.padded_sha256}\n"
            f"readonly AJ_ARTIFACT_MANIFEST_SHA256={calibration.artifact_manifest_sha256}\n",
        ),
        (
            "\tAJ_RAW_SHA256 AJ_RAW_SIZE AJ_PADDED_SHA256 "
            "EXPECTED_CURRENT_AI_PADDED_SHA256\n",
            "\tAJ_RAW_SHA256 AJ_RAW_SIZE AJ_ARTIFACT_MANIFEST_SHA256 "
            "AJ_PADDED_SHA256 EXPECTED_CURRENT_AI_PADDED_SHA256\n",
        ),
        (
            "for name in AJ_RAW_SHA256 AJ_PADDED_SHA256 "
            "EXPECTED_CURRENT_AI_PADDED_SHA256; do\n",
            "for name in AJ_RAW_SHA256 AJ_ARTIFACT_MANIFEST_SHA256 "
            "AJ_PADDED_SHA256 EXPECTED_CURRENT_AI_PADDED_SHA256; do\n",
        ),
        (manifest_guard, guarded_manifest),
        (initial_arch, initial_gemian),
        (initial_root_parent, initial_exact_root),
        (gate_arch, gate_gemian),
    )


def expected_transform(source_text: str, calibration: Calibration) -> str:
    validate_calibration(calibration)
    text = source_text
    for old, new, count in identity_replacements(calibration):
        text = replace_exact(text, old, new, count)

    pins = (
        (
            f"readonly AJ_RAW_SHA256={aj.AI_RAW_SHA256}",
            f"readonly AJ_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AJ_RAW_SIZE={aj.AI_RAW_SIZE}",
            f"readonly AJ_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AJ_PADDED_SHA256={aj.AI_PADDED_SHA256}",
            f"readonly AJ_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            "readonly EXPECTED_CURRENT_AI_PADDED_SHA256="
            f"{AI_SOURCE_PREDECESSOR_SHA256}",
            "readonly EXPECTED_CURRENT_AI_PADDED_SHA256="
            f"{EXPECTED_AI_PADDED_SHA256}",
        ),
    )
    for old, new in pins:
        text = replace_exact(text, old, new, 1)
    for old, new in aj_contract_additions(calibration):
        text = replace_exact(text, old, new, 1)
    return text


def restore_ai_contract(text: str, calibration: Calibration) -> str:
    """Map AJ identity and its manifest pin back to exact AI executable bytes."""

    validate_calibration(calibration)
    restored = text
    for old, new in reversed(aj_contract_additions(calibration)):
        restored = replace_exact(restored, new, old, 1)

    pins = (
        (
            f"readonly AJ_RAW_SHA256={calibration.raw_sha256}",
            f"readonly AJ_RAW_SHA256={aj.AI_RAW_SHA256}",
        ),
        (
            f"readonly AJ_RAW_SIZE={calibration.raw_size}",
            f"readonly AJ_RAW_SIZE={aj.AI_RAW_SIZE}",
        ),
        (
            f"readonly AJ_PADDED_SHA256={calibration.padded_sha256}",
            f"readonly AJ_PADDED_SHA256={aj.AI_PADDED_SHA256}",
        ),
        (
            "readonly EXPECTED_CURRENT_AI_PADDED_SHA256="
            f"{EXPECTED_AI_PADDED_SHA256}",
            "readonly EXPECTED_CURRENT_AI_PADDED_SHA256="
            f"{AI_SOURCE_PREDECESSOR_SHA256}",
        ),
    )
    for old, new in pins:
        restored = replace_exact(restored, old, new, 1)
    for old, new, count in reversed(identity_replacements(calibration)):
        restored = replace_exact(restored, new, old, count)
    return restored


def validate_safety(text: str, calibration: Calibration) -> None:
    """Require exact AJ identity over AI's complete executable contract."""

    ai = load_ai_deriver()
    restored = restore_ai_contract(text, calibration)
    ai.validate_safety(restored, ai.PRODUCTION_CALIBRATION)
    if digest(restored.encode("utf-8")) != AI_INSTALLER_SHA256:
        raise ValueError("Candidate AJ installer changed executable AI contract")


def validate_exact_delta(
    source_text: str, text: str, calibration: Calibration
) -> None:
    if text != expected_transform(source_text, calibration):
        raise ValueError("Candidate AJ installer is not the exact narrow AI transform")


def derive_text(source_data: bytes, calibration: Calibration) -> str:
    if digest(source_data) != AI_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AI installer foundation changed")
    try:
        source_text = source_data.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Candidate AI installer is not UTF-8") from exc
    text = expected_transform(source_text, calibration)
    validate_exact_delta(source_text, text, calibration)
    validate_safety(text, calibration)
    return text


def run_lineage(command: list[str], cwd: pathlib.Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"Candidate AI installer lineage command failed ({result.returncode}): "
            f"{error}"
        )


def verify_lineage_output(path: pathlib.Path) -> None:
    verify_regular(path, "Candidate AI installer lineage output")
    info = path.lstat()
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Candidate AI installer lineage mode changed")
    if digest_path(path) != AI_INSTALLER_SHA256:
        raise ValueError("Candidate AI installer lineage identity changed")


def reconstruct_ai_installer(root: pathlib.Path, work: pathlib.Path) -> pathlib.Path:
    """Reproduce exact AI after pinning its deriver and final bytes."""

    deriver = ai_deriver_path(root)
    verify_regular(deriver, "Candidate AI installer deriver")
    if digest_path(deriver) != AI_DERIVER_SHA256:
        raise ValueError("Candidate AI installer deriver identity changed")
    output = work / "install-candidate-ai-boot2.sh"
    run_lineage(
        [sys.executable, os.fspath(deriver), "--output", os.fspath(output)],
        root,
    )
    verify_lineage_output(output)
    return output


def read_exact_source(path: pathlib.Path) -> bytes:
    verify_regular(path, "Candidate AI installer foundation")
    data = path.read_bytes()
    if digest(data) != AI_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AI installer foundation changed")
    return data


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."}:
        raise ValueError("Candidate AJ installer output name is invalid")
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite Candidate AJ installer")
    parent_info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Candidate AJ installer output parent is unsafe")
    parent = path.parent.resolve(strict=True)
    return parent / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)


def produce(source_path: pathlib.Path | None, output_path: pathlib.Path) -> tuple[pathlib.Path, str, Calibration]:
    """Derive one production installer; the pin gate deliberately runs first."""

    calibration = production_calibration()
    output = validate_output_path(output_path)
    root = repo_root()
    if source_path is not None:
        source_data = read_exact_source(source_path)
    else:
        with tempfile.TemporaryDirectory(
            prefix=".candidate-aj-ai-foundation.", dir=output.parent
        ) as raw_temp:
            source = reconstruct_ai_installer(root, pathlib.Path(raw_temp))
            source_data = read_exact_source(source)
    text = derive_text(source_data, calibration)
    publish(output, text)
    return output, text, calibration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        help="exact validated AI installer; omit to reconstruct tracked lineage",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        output, text, calibration = produce(args.source, args.output)
        print("validation=candidate-aj-installer-derivation")
        print(f"foundation_installer_sha256={AI_INSTALLER_SHA256}")
        print(f"installer_sha256={digest(text.encode('utf-8'))}")
        print(f"candidate_raw_sha256={calibration.raw_sha256}")
        print(f"candidate_raw_size={calibration.raw_size}")
        print(
            "candidate_artifact_manifest_sha256="
            f"{calibration.artifact_manifest_sha256}"
        )
        print(f"candidate_padded_sha256={calibration.padded_sha256}")
        print(f"expected_predecessor_sha256={EXPECTED_AI_PADDED_SHA256}")
        print(f"artifact_directory={artifact_directory(calibration)}")
        print(f"boot_filename={AJ_BOOT_FILENAME}")
        print(f"output={output}")
        print("sole_target_write=one-bounded-16MiB-write")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
