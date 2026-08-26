#!/usr/bin/env python3
"""Generate the exact platform-movement attribution format-patches."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT.parents[1]
PREDECESSOR = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution"
TEMPLATE_PARENT = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/source"
PLATFORM_PATCH = REPO_ROOT / "patches/v7.1.3/0310-soc-mediatek-add-MT6797-A72-platform-state-source.patch"
PREDECESSOR_EDITS = PREDECESSOR / "scripts/source_edits.py"
PATCHES = (
    "0380-soc-mediatek-report-A72-platform-state-movement.patch",
    "0381-soc-mediatek-test-A72-platform-state-movement.patch",
)
TEMPLATE_HASHES = {
    "mt6797-a72-platform-provider-clock-observer.c": "ae6e8b8f801902ea846bb700eb27269246115acf0d9eb011af5499309c6c1fd2",
    "mt6797-a72-platform-provider-clock-observer-internal.h": "0da8cad93307270a31ff08f4f87d4b28c392fc7247fc6d0a5652c56b81e1452c",
    "mt6797-a72-platform-provider-clock-observer-test.c": "eeb38232b0daa27e43de6bb936e7c362e81957ff74b49582e6e2818f93b232ea",
}
POST_0379_HASHES = {
    "mt6797-a72-platform-provider-clock-observer.c": "4f61f692da9c1da94fa1fe6ca5324cd384cc8c0cc86abf80ca4001d492998a2a",
    "mt6797-a72-platform-provider-clock-observer-internal.h": "ed3fe927f2b7b65ff5b257323e3683f1eb278ce1d554153b1b011669bdbb413e",
    "mt6797-a72-platform-provider-clock-observer-test.c": "3e60f976cc509e2e017ea402c7033775474473a4aa33f5fd61ed2a82e70ba938",
}
EXTRACTED_HASHES = {
    "drivers/soc/mediatek/mt6797-a72-platform-state.c": "214ae21bf98e7d47e8ec8c24d0c542ebb27e3ba110694f81e04482ff78b108b6",
    "include/linux/soc/mediatek/mt6797-a72-platform-state.h": "1131bce832164f6b9b8e4849bdcdf6345960e07a1e6e4d1b3dbece5c3ff24b90",
}
PREDECESSOR_EDITS_SHA256 = "a152597ec51d6a5c5738564b0e035c2490d22200ddc5cdb842c8284389a6dc2c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def extract_created_file(patch: str, target: str) -> bytes:
    marker = f"diff --git a/{target} b/{target}\n"
    if patch.count(marker) != 1:
        raise SystemExit(f"canonical extraction marker changed: {target}")
    section = patch.split(marker, 1)[1]
    if "\ndiff --git " in section:
        section = section.split("\ndiff --git ", 1)[0]
    lines = section.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("@@ ")), None)
    if start is None:
        raise SystemExit(f"canonical extraction hunk missing: {target}")
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("+") and not line.startswith("+++"):
            body.append(line[1:])
        elif line.startswith("\\ No newline"):
            continue
        else:
            raise SystemExit(f"canonical new-file extraction changed: {target}: {line}")
    return ("\n".join(body) + "\n").encode()


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


def write_build_fixtures(soc: Path) -> None:
    (soc / "Kconfig").write_text(dedent("""\
        config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER
        \tbool "MediaTek MT6797 A72 platform/provider/protected-clock observer"
        \tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
        \tdepends on MTK_MT6797_A72_PLATFORM_STATE
        \tdepends on MTK_MT6797_DVFSP_CLOCK_BACKEND
        \tdefault n
        \thelp
        \t  Build the candidate-only observer that takes one stable platform snapshot,
        \t  one stable read-only DA921x provider snapshot, two retained checkpoints,
        \t  and exactly one bounded protected-clock snapshot with no caller retry.

        \t  The clock call uses one balanced clock-gate pair plus the existing CSPM
        \t  power-on/semaphore protocol. It adds no DA921x register-data write,
        \t  BigiDVFS or secure call, provider action, publisher, owner mutation, CPU
        \t  request, reset, or power action. If unsure, say N.

        config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST
        \tbool "KUnit tests for MT6797 A72 platform/provider/clock observer"
        \tdepends on KUNIT=y
        \tdepends on MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER
        \tdefault n
        \thelp
        \t  Exercise exact source order, dependency refusal, every prefix failure,
        \t  terminal clock errors, terminal after-checkpoint failure, identity failure,
        \t  and all-zero pre-clock failure output with injected in-memory operations.

        \t  No MMIO, retained RAM, I2C, clock, SMC, provider registry, owner,
        \t  publisher, or CPU action occurs in these tests. If unsure, say N.

        config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER
        \tbool "MediaTek MT6797 A72 platform/provider snapshot observer"
        \tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
        """), encoding="utf-8")
    (soc / "Makefile").write_text(dedent("""\
        obj-$(CONFIG_MTK_DEVAPC) += mtk-devapc.o
        obj-$(CONFIG_MTK_DVFSRC) += mtk-dvfsrc.o
        obj-$(CONFIG_MTK_INFRACFG) += mtk-infracfg.o
        obj-$(CONFIG_MTK_MT6797_A72_POWER) += mt6797-a72-power.o
        obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += mt6797-a72-platform-state.o
        obj-$(CONFIG_MTK_MT6797_DVFSP_HANDOFF) += mt6797-dvfsp-handoff.o
        obj-$(CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND) += mt6797-dvfsp-clock-backend.o
        obj-$(CONFIG_MTK_MT6797_DVFSP_STATE_DECODERS) += mt6797-dvfsp-cspm-state.o
        obj-$(CONFIG_MTK_MT6797_DVFSP_HANDOFF) += mt6797-dvfsp-ppm.o
        obj-$(CONFIG_MTK_MT6797_DVFSP_HANDOFF) += mt6797-dvfsp-ppm-policy.o
        obj-$(CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND) += mt6797-bigidvfs-backend.o
        obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER) += mt6797-a72-platform-provider-clock-observer.o
        obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST) += mt6797-a72-platform-provider-clock-observer-test.o
        obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER) += mt6797-a72-platform-provider-snapshot-observer.o
        obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_KUNIT_TEST) += mt6797-a72-platform-provider-snapshot-observer-test.o
        obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER) += mt6797-a72-platform-snapshot-observer.o
        """), encoding="utf-8")


def prepare_parent(source: Path) -> None:
    soc = source / "drivers/soc/mediatek"
    include = source / "include/linux/soc/mediatek"
    soc.mkdir(parents=True)
    include.mkdir(parents=True)
    for name, expected in TEMPLATE_HASHES.items():
        path = TEMPLATE_PARENT / name
        if sha256(path) != expected:
            raise SystemExit(f"post-0377 template changed: {name}")
        shutil.copyfile(path, soc / name)
    if sha256(PREDECESSOR_EDITS) != PREDECESSOR_EDITS_SHA256:
        raise SystemExit("predecessor source edits changed")
    run("python3", str(PREDECESSOR_EDITS), "--source-root", str(source),
        "--phase", "production", cwd=REPO_ROOT)
    run("python3", str(PREDECESSOR_EDITS), "--source-root", str(source),
        "--phase", "tests", cwd=REPO_ROOT)
    for name, expected in POST_0379_HASHES.items():
        if sha256(soc / name) != expected:
            raise SystemExit(f"post-0379 reconstruction changed: {name}")

    patch = PLATFORM_PATCH.read_text(encoding="utf-8")
    for target, expected in EXTRACTED_HASHES.items():
        data = extract_created_file(patch, target)
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f"platform source extraction changed: {target}")
        destination = source / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    for later in sorted((REPO_ROOT / "patches/v7.1.3").glob("*.patch")):
        if later.name <= PLATFORM_PATCH.name or later.name >= PATCHES[0]:
            continue
        text = later.read_text(encoding="utf-8")
        for target in EXTRACTED_HASHES:
            if f"diff --git a/{target} b/{target}" in text:
                raise SystemExit(f"unaccounted later platform-source edit: {later.name}")
    write_build_fixtures(soc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")

    with tempfile.TemporaryDirectory(prefix="a72-platform-movement-generation-") as temp:
        source = Path(temp) / "source"
        prepare_parent(source)
        run("git", "init", "--quiet", cwd=source)
        run("git", "config", "user.name", "Gemini Mainline Experiment", cwd=source)
        run("git", "config", "user.email", "gemini-mainline@example.invalid", cwd=source)
        commit(source, "A72 platform movement post-0379 parent",
               "Exact relevant source reconstructed from canonical patches through 0379.",
               "2026-08-26T02:10:00Z")
        parent = run("git", "rev-parse", "HEAD", cwd=source)

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root", str(source),
            "--phase", "production", cwd=REPO_ROOT)
        run("python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root", str(source),
            "--phase", "production", cwd=REPO_ROOT)
        commit(source, "soc: mediatek: report A72 platform-state movement",
               "Preserve the exact two-sample transaction and expose a bounded failure\n"
               "detail that identifies which existing comparison moved.",
               "2026-08-26T02:11:00Z")

        run("python3", str(SCRIPT_DIR / "source_edits.py"), "--source-root", str(source),
            "--phase", "tests", cwd=REPO_ROOT)
        run("python3", str(SCRIPT_DIR / "validate_source.py"), "--source-root", str(source),
            "--phase", "tests", cwd=REPO_ROOT)
        commit(source, "soc: mediatek: test A72 platform-state movement",
               "Prove read bounds, CCI-busy precedence, every movement bit, masked\n"
               "noise exclusion, and composed propagation with injected memory.",
               "2026-08-26T02:12:00Z")

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
        sums = [
            f"{sha256(path)}  {path.name}" for path in sorted(package.iterdir())
        ]
        (package / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        shutil.copytree(package, output)
    print(f"generated_package={output}")
    print("generated_patch_count=2")
    print("device_action=none")


if __name__ == "__main__":
    main()
