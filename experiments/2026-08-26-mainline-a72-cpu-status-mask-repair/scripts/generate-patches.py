#!/usr/bin/env python3
"""Generate exact CPU-status-mask repair format-patches."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PREVIOUS = REPO_ROOT / "experiments/2026-08-26-mainline-a72-platform-movement-attribution/scripts"
PREVIOUS_GENERATOR = PREVIOUS / "generate-patches.py"
PREVIOUS_EDITS = PREVIOUS / "source_edits.py"
PREVIOUS_GENERATOR_SHA256 = "90747ed66668f48ef0b55c87fe4c6f1d5247aab7515b58b355f966c5345f7d8f"
PREVIOUS_EDITS_SHA256 = "84637d024e632cd0e3d3a5000b71dc1b3a2d5b4a163abbacf4051e2f4c963230"
POST_0381_HASHES = {
    "drivers/soc/mediatek/mt6797-a72-platform-state.c":
        "976bbc5fff9730c789e2c79b54d751ec6b109f983d654cddeca2f68f14477a73",
    "drivers/soc/mediatek/mt6797-a72-platform-state-test.c":
        "635d133a46d89a9b6bb9145467c579f5cd88dc68865324141836c5791eb7fdb8",
    "include/linux/soc/mediatek/mt6797-a72-platform-state.h":
        "534f654cb122a51776ad4512c08bdeced28948c58898d7e0a25aa55662dfa30e",
}
PATCHES = (
    "0382-soc-mediatek-mask-A72-CPU-status-stability.patch",
    "0383-soc-mediatek-test-A72-CPU-status-stability-mask.patch",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def load_previous():
    if sha256(PREVIOUS_GENERATOR) != PREVIOUS_GENERATOR_SHA256:
        raise SystemExit("previous generator changed")
    if sha256(PREVIOUS_EDITS) != PREVIOUS_EDITS_SHA256:
        raise SystemExit("previous source edits changed")
    spec = importlib.util.spec_from_file_location("movement_generator", PREVIOUS_GENERATOR)
    if spec is None or spec.loader is None:
        raise SystemExit("previous generator import unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_parent(source: Path) -> None:
    previous = load_previous()
    previous.prepare_parent(source)
    run("python3", str(PREVIOUS_EDITS), "--source-root", str(source),
        "--phase", "production", cwd=REPO_ROOT)
    run("python3", str(PREVIOUS_EDITS), "--source-root", str(source),
        "--phase", "tests", cwd=REPO_ROOT)
    for relative, expected in POST_0381_HASHES.items():
        if sha256(source / relative) != expected:
            raise SystemExit(f"post-0381 reconstruction changed: {relative}")


def commit(root: Path, subject: str, body: str, timestamp: str) -> None:
    run("git", "add", "--", ".", cwd=root)
    run("git", "diff", "--cached", "--check", cwd=root)
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Gemini Mainline Experiment",
        "GIT_AUTHOR_EMAIL": "gemini-mainline@example.invalid",
        "GIT_COMMITTER_NAME": "Gemini Mainline Experiment",
        "GIT_COMMITTER_EMAIL": "gemini-mainline@example.invalid",
        "GIT_AUTHOR_DATE": timestamp,
        "GIT_COMMITTER_DATE": timestamp,
    })
    run("git", "commit", "--quiet", "--no-gpg-sign", "-m", subject, "-m", body,
        cwd=root, env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")

    with tempfile.TemporaryDirectory(prefix="a72-cpu-status-mask-generation-") as temp:
        source = Path(temp) / "source"
        prepare_parent(source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=source)
        commit(source, "A72 CPU-status mask post-0381 parent",
               "Exact relevant source reconstructed from canonical patches through 0381.",
               "2026-08-26T10:20:00Z")
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root", str(source),
            "--phase", "production", cwd=REPO_ROOT)
        run("python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root", str(source),
            "--phase", "production", cwd=REPO_ROOT)
        commit(source, "soc: mediatek: mask A72 CPU-status stability",
               "Use only the source-backed CPU8/CPU9 identity bits for movement\n"
               "while preserving both complete raw status words.",
               "2026-08-26T10:21:00Z")

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root", str(source),
            "--phase", "tests", cwd=REPO_ROOT)
        run("python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root", str(source),
            "--phase", "tests", cwd=REPO_ROOT)
        commit(source, "soc: mediatek: test A72 CPU-status stability mask",
               "Prove all four A72 identity-bit movements and accept the exact\n"
               "observed unrelated-bit pair without losing raw evidence.",
               "2026-08-26T10:22:00Z")

        generated = run("git", "format-patch", "--no-signature", "--output-directory",
                        str(Path(temp) / "patches"), f"{parent}..HEAD", cwd=source).splitlines()
        if len(generated) != 2:
            raise SystemExit("generated patch count changed")
        package = Path(temp) / "package"
        package.mkdir()
        for generated_name, final_name in zip(generated, PATCHES):
            shutil.move(generated_name, package / final_name)
        (package / "series").write_text("\n".join(PATCHES) + "\n", encoding="utf-8")
        run("python3", str(SCRIPT_DIR / "validate_patch.py"), "--patch-dir", str(package),
            cwd=REPO_ROOT)
        sums = [f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())]
        (package / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        shutil.copytree(package, output)
    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("device_action=none")


if __name__ == "__main__":
    main()
