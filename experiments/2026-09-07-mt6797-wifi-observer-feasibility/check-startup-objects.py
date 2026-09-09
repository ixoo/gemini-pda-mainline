#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Buildbox-only compilation check of five files; does not build a kernel image."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile


REVISION = "59e00a9144d782e148332009a835b99c43382467"
TOOLCHAIN = "a45d945f092461a611d276ad7d0a0fea1ea8a7f93db413908bcb892c12817d14"
RELATIVE = "drivers/misc/mediatek/connectivity/common/common_main/"
FILES = ("core/wmt_ic_soc", "core/wmt_core", "core/wmt_ctrl", "core/wmt_lib", "linux/wmt_dev")


def run(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_logged(args, stream, **kwargs):
    result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, **kwargs)
    if result.returncode:
        stream.flush()
        print(Path(stream.name).read_text()[-12000:], file=sys.stderr)
        result.check_returncode()


def symbols(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            name, value = line.split("=", 1)
            values[name] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[2:-11]] = "n"
    return values


def main():
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    experiment = Path(__file__).resolve().parent
    project = experiment.parents[1]
    commit = run(["git", "-C", str(project), "rev-parse", "HEAD"])
    assert len(sys.argv) == 2 and sys.argv[1] == commit
    assert not run(["git", "-C", str(project), "status", "--porcelain"])
    root = Path("/workspace/gemini-pda")
    source = root / "gemian-source/gemian-baseline" / REVISION
    assert run(["git", "-C", str(source), "rev-parse", "HEAD"]) == REVISION
    assert not run(["git", "-C", str(source), "status", "--porcelain"])
    toolchain = root / "gemian-toolchains" / TOOLCHAIN
    assert (toolchain / "validated").read_text().strip() == TOOLCHAIN
    compiler = toolchain / "wrappers/aarch64-linux-gnu-gcc"
    assert run([str(compiler), "--version"]).splitlines()[0] == (
        "aarch64-linux-gnu-gcc-6 (Debian 6.3.0-18) 6.3.0 20170516")
    config = project / "experiments/2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config"
    assert digest(config) == "231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4"
    recorded = root / "gemian-artifacts/gemian-observer-a98ffc90f979/outputs/build.log"
    assert digest(recorded) == "cc43a28e3856325f3087dbc0c6b0a32e5cc0d8034074d851a0e0e33dd9da1a39"
    old_source = str(root / "gemian-source/gemian-observer/a98ffc90f979eabe4e927b0d478199673b62781c")
    assert shutil.disk_usage(root).free > 2 * 1024 ** 3
    package = root / "gemian-artifacts" / ("wifi-startup-objects-" + commit)
    assert not package.exists(), "refusing to overwrite a result"
    environment = dict(os.environ, LD_LIBRARY_PATH=str(toolchain / "root/usr/lib/x86_64-linux-gnu"),
                       HOST_EXTRACFLAGS="-fcommon")
    with tempfile.TemporaryDirectory(prefix="wifi-startup-objects-", dir=root / "build") as tmp:
        work = Path(tmp)
        output = work / "output"
        output.mkdir()
        shutil.copyfile(config, output / ".config")
        command = ["make", "-C", str(source), "O=" + str(output), "ARCH=arm64",
                   "CROSS_COMPILE=" + str(toolchain / "wrappers/aarch64-linux-gnu-"),
                   "python=" + str(toolchain / "wrappers/python2.7"), "KCFLAGS=-fstack-usage"]
        log = work / "build.log"
        with log.open("w") as stream:
            compile_logged(command + ["olddefconfig"], stream, env=environment, timeout=120)
            before, after = symbols(config), symbols(output / ".config")
            delta = {key: [before.get(key), after.get(key)] for key in before.keys() | after.keys()
                     if before.get(key) != after.get(key)}
            assert delta == {"CONFIG_ANBOX": [None, "n"]}, delta
            compile_logged(command + ["-j2", "V=1", "prepare"],
                           stream, env=environment, timeout=300)
        patched = work / "patched"
        for name in FILES:
            dest = patched / (RELATIVE + name + ".c")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / (RELATIVE + name + ".c"), dest)
        # Copy neighboring headers so quoted includes resolve to the patched header.
        headers = RELATIVE + "core/include"
        shutil.copytree(source / headers, patched / headers)
        patches = sorted((experiment / "patches").glob("*.patch"))
        assert len(patches) == 3
        for patch in patches:
            subprocess.run(["git", "apply", str(patch)], cwd=patched, check=True)
        records = []
        header = headers + "/wmt_ctrl.h"
        assert digest(source / header) != digest(patched / header)
        for relative_name in FILES:
            name = Path(relative_name).name
            suffix = RELATIVE + relative_name + ".c"
            lines = [line for line in recorded.read_text().splitlines()
                     if " -c " in line and line.endswith("/" + suffix)]
            assert len(lines) == 1, (name, len(lines))
            args = shlex.split(lines[0])
            assert args[0] == str(compiler) and args[-1] == old_source + "/" + suffix
            assert args[args.index("-o") + 1] == RELATIVE + relative_name + ".o"
            args = [a.replace(old_source, str(source)) for a in args]
            baseline = work / (name + "-baseline.o")
            args[args.index("-o") + 1] = str(baseline)
            args = ["-Wp,-MD," + str(work / (name + "-baseline.d")) if a.startswith("-Wp,-MD,") else a
                    for a in args]
            with (work / (name + "-baseline.log")).open("w") as stream:
                compile_logged(args, stream, cwd=output, env=environment, timeout=120)
            result = work / (name + ".o")
            args[args.index("-o") + 1] = str(result)
            args[-1] = str(patched / suffix)
            args.insert(1, "-I" + str(patched / headers))
            args = ["-Wp,-MD," + str(work / (name + ".d")) if a.startswith("-Wp,-MD,") else a
                    for a in args]
            with (work / (name + ".log")).open("w") as stream:
                compile_logged(args, stream, cwd=output, env=environment, timeout=120)
            dependencies = (work / (name + ".d")).read_text().replace("\\\n", " ").split()
            assert str(patched / header) in dependencies, name
            assert str(source / header) not in dependencies, name
            assert "AArch64" in run(["readelf", "-h", str(result)])
            records.append({"file": suffix, "baseline_source_sha256": digest(source / suffix),
                            "baseline_object_sha256": digest(baseline),
                            "patched_source_sha256": digest(patched / suffix),
                            "object_sha256": digest(result),
                            "baseline_command_sha256": hashlib.sha256(lines[0].encode()).hexdigest(),
                            "patched_header_dependency_verified": True,
                            "diagnostics_bytes": (work / (name + ".log")).stat().st_size})
        receipt = {"project_commit": commit, "source_commit": REVISION,
                   "scope": "five complete translation units; no kernel link or device execution",
                   "patched_header_sha256": digest(patched / header),
                   "toolchain_manifest_sha256": TOOLCHAIN,
                   "config_sha256": digest(output / ".config"), "config_delta": delta,
                   "patches": {p.name: digest(p) for p in patches}, "objects": records}
        package.mkdir()
        for file in [log, *work.glob("wmt_*.o"), *work.glob("wmt_*.log")]:
            shutil.copyfile(file, package / file.name)
        (package / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (package / "SHA256SUMS").write_text("".join(
            digest(p) + "  " + p.name + "\n" for p in sorted(package.iterdir())))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
