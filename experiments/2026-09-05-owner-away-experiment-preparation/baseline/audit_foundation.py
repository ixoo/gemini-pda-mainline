#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only validation of the retained, runtime-proven PWRAP foundation."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import stat
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_size > 0,
            f"missing, empty or nonregular member: {path.name}")
    return path.read_bytes()


def safe_directory(path):
    path = Path(os.path.abspath(path))
    for component in (path, *path.parents):
        require(not component.is_symlink(), "symlink in input directory path")
    require(path.is_dir(), "input directory missing")
    return path


def inventory(root, expected):
    """Validate every member, exact inventory and each path without extraction."""
    root = safe_directory(root)
    raw = regular(root / "SHA256SUMS")
    require(digest(raw) == expected["manifest_sha256"], "inventory manifest digest")
    seen = set()
    for line in raw.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  \./(.+)", line)
        require(match is not None, "malformed checksum line")
        sha, relative = match.groups()
        path = PurePosixPath(relative)
        require(not path.is_absolute() and path.as_posix() == relative and
                all(part not in ("", ".", "..") for part in relative.split("/")),
                "unsafe inventory path")
        require(relative not in seen and relative != "SHA256SUMS", "duplicate inventory path")
        seen.add(relative)
        for parent in (root / relative).parents:
            if parent == root:
                break
            require(not parent.is_symlink(), "symlink inventory parent")
        require(digest(regular(root / relative)) == sha, "member checksum mismatch")
    require(len(seen) == expected["inventory_count"], "inventory count")
    actual = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            require(not (Path(directory) / name).is_symlink(), "symlink directory")
        for name in files:
            path = Path(directory) / name
            require(stat.S_ISREG(path.lstat().st_mode), "nonregular inventory member")
            actual.add(path.relative_to(root).as_posix())
    require(actual == seen | {"SHA256SUMS"}, "unlisted or missing inventory member")
    for name, identity in expected.get("identities", {}).items():
        data = regular(root / name)
        require(len(data) == identity["size"] and digest(data) == identity["sha256"],
                f"pinned identity changed: {name}")
    return root


def git_bytes(repository, revision, path):
    return subprocess.check_output(["git", "-C", str(repository), "show", f"{revision}:{path}"])


def selected(data):
    return [line for line in data.decode().splitlines() if line and not line.startswith("#")]


def audit(repository, package, candidate, foundation):
    require(foundation["schema_version"] == 1, "foundation schema")
    revision = foundation["repository_build_commit"]
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "historical revision")
    manifest_raw = git_bytes(repository, revision, "kernel/manifest.json")
    require(digest(manifest_raw) == foundation["historical_manifest_sha256"], "historical manifest")
    manifest = json.loads(manifest_raw)
    require(manifest["kernel"] == foundation["upstream"], "upstream input")
    require(manifest["config"]["profiles"][foundation["profile_name"]] ==
            foundation["historical_profile"], "historical profile")
    series_raw = git_bytes(repository, revision, foundation["historical_series"]["path"])
    require(digest(series_raw) == foundation["historical_series"]["sha256"], "historical series")
    series = selected(series_raw)
    require(len(series) == foundation["historical_series"]["patch_count"] and
            len(series) == len(set(series)), "historical patch count or duplicate")
    canonical = selected(regular(repository / "patches/series"))
    indices = [canonical.index(path) for path in series]
    require(indices == sorted(indices), "foundation is no longer a canonical subsequence")
    package = inventory(package, foundation["package"])
    candidate = inventory(candidate, foundation["candidate"])
    require(package.name == foundation["package"]["directory_name"], "package name")
    require(candidate.name == foundation["candidate"]["directory_name"], "candidate name")
    require(regular(package / "provenance/kernel-manifest.json") == manifest_raw,
            "packaged historical manifest")
    require(regular(package / "provenance/series") == series_raw, "packaged historical series")
    for path in series:
        historical = git_bytes(repository, revision, "patches/" + path)
        require(regular(package / "provenance/patches" / path) == historical,
                "packaged historical patch")
        require(regular(repository / "patches" / path) == historical, "current historical patch drift")
    for path, sha in foundation["fragments"].items():
        historical = git_bytes(repository, revision, path)
        require(digest(historical) == sha, "fragment pin")
        require(regular(package / "provenance" / path) == historical and
                regular(repository / path) == historical, "fragment content drift")
    build = json.loads(regular(package / "provenance/build.json"))
    require(build == foundation["build"] and build["repository_commit"] == revision and
            build["repository_dirty"] is False, "exact build provenance")
    require(regular(candidate / "source-build.json") == regular(package / "provenance/build.json"),
            "candidate build provenance")
    require(gzip.decompress(regular(package / "Image.gz")) == regular(package / "Image"),
            "compressed kernel differs")
    for name in ("Image.gz", "kernel.config", "System.map"):
        require(regular(candidate / name) == regular(package / name), "candidate kernel package differs")
    init_name = "gemini-pwrap-reset-serviceability-initramfs.img"
    dt_name = "mt6797-gemini-pda-pwrap-reset-serviceability.dtb"
    raw_name = "gemini-mt6797-pwrap-reset-serviceability.boot.img"
    raw, padded = regular(candidate / raw_name), regular(candidate / "boot2-padded.img")
    require(padded == raw + bytes(16777216 - len(raw)), "exact boot2 padding")
    parser = runpy.run_path(str(repository / "experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py"))["parse_newc"]
    members = parser(regular(candidate / init_name))
    require(set(members) == set(foundation["initramfs_members"]), "inherited member inventory")
    for name, member in members.items():
        expected = foundation["initramfs_members"][name]
        actual = {"mode": oct(member.mode), "size": len(member.data), "sha256": digest(member.data),
                  "uid": member.uid, "gid": member.gid, "mtime": member.mtime, "nlink": member.nlink}
        if stat.S_ISLNK(member.mode):
            actual["target"] = member.data.decode()
        require(actual == expected, "inherited member changed")
    dt_parser = runpy.run_path(str(repository / "experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts/build_dtb.py"))["properties"]
    properties = dt_parser(regular(candidate / dt_name))
    for resource in foundation["dt_resource_properties"]:
        require(properties[(resource["path"], resource["property"])][1].hex() == resource["hex"],
                "documented DT resource changed")
    analyzer = repository / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    require(digest(regular(analyzer)) == "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95",
            "LK analyzer changed")
    subprocess.run(["python3", str(analyzer), "--validate-lk", "--expected-image-gz", str(candidate / "Image.gz"),
                    "--expected-ramdisk", str(candidate / init_name), "--expected-dtb", str(candidate / dt_name),
                    "--expected-name", foundation["container"]["name"], "--expected-cmdline",
                    foundation["container"]["cmdline"], str(candidate / raw_name)],
                   check=True, stdout=subprocess.DEVNULL)
    return {"result": "historical-foundation-pass", "repository_build_commit": revision,
            "patch_count": len(series), "package_members": foundation["package"]["inventory_count"],
            "candidate_members": foundation["candidate"]["inventory_count"],
            "initramfs_members": len(members), "device_access": "none", "boot_admission": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=REPO)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(safe_directory(args.repository), args.package, args.candidate,
                       json.loads(regular(HERE / "foundation.json")))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"foundation refused: {error}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
