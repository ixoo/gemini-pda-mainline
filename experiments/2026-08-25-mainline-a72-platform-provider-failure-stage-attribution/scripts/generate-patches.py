#!/usr/bin/env python3
"""Generate the two exact failure-stage format-patches from pinned templates."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PARENT = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/source"
HASHES = {
    "mt6797-a72-platform-provider-clock-observer.c": "ae6e8b8f801902ea846bb700eb27269246115acf0d9eb011af5499309c6c1fd2",
    "mt6797-a72-platform-provider-clock-observer-internal.h": "0da8cad93307270a31ff08f4f87d4b28c392fc7247fc6d0a5652c56b81e1452c",
    "mt6797-a72-platform-provider-clock-observer-test.c": "eeb38232b0daa27e43de6bb936e7c362e81957ff74b49582e6e2818f93b232ea",
}
PATCHES = (
    "0378-soc-mediatek-report-A72-platform-provider-failure-stage.patch",
    "0379-soc-mediatek-test-A72-platform-provider-failure-stage.patch",
)


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


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
    for name, expected in HASHES.items():
        actual = hashlib.sha256((PARENT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"parent template changed: {name}")

    with tempfile.TemporaryDirectory(prefix="a72-failure-stage-generation-") as temp:
        source = Path(temp) / "source"
        soc = source / "drivers/soc/mediatek"
        soc.mkdir(parents=True)
        for name in HASHES:
            shutil.copyfile(PARENT / name, soc / name)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=source)
        commit(source, "A72 platform/provider/clock post-0377 parent",
               "Exact source templates generated and admitted as canonical patches 0376 and 0377.",
               "2026-08-26T00:10:00Z")
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root", str(source),
            "--phase", "production", cwd=REPO_ROOT)
        run("python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root", str(source),
            "--phase", "production", cwd=REPO_ROOT)
        commit(source, "soc: mediatek: report A72 platform/provider failure stage",
               "Preserve the zeroed pre-clock result while identifying the exact prefix\n"
               "boundary that returned an error.",
               "2026-08-26T00:11:00Z")

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root", str(source),
            "--phase", "tests", cwd=REPO_ROOT)
        run("python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root", str(source),
            "--phase", "tests", cwd=REPO_ROOT)
        commit(source, "soc: mediatek: test A72 platform/provider failure stage",
               "Assert every pre-clock stage and preserve terminal no-retry behavior with\n"
               "injected in-memory operations.",
               "2026-08-26T00:12:00Z")

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
        sums = []
        for path in sorted(package.iterdir()):
            sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
        (package / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        shutil.copytree(package, output)
    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("device_action=none")


if __name__ == "__main__":
    main()
