#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one private, deterministic TOPRGU Android-v0 candidate.

This command never installs or selects a candidate.  Credential contents are
read only to embed the reviewed public transport files in the private output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_lib as C  # noqa: E402

PACKAGE_COMMIT = "745ecaea21c004a377a01287bea8ac3b58c2d6e2"
FOUNDATION_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"
SOURCE_DIGESTS = {
    "init": "533fbf455e418d35973a6651d882b6d3c5240e5ef8594804109cde70adc05e4b",
    "inittab": "6b3bcd89055fa50cdf5c5d973611c9e5f30719197b50ad059079e649906fec6f",
    "usb-auth": "3b292c1af12e18437254af49e321b968cddd348b3a5846dd9165927b6a81c672",
    "console-status": "82dcf6d37295560a4c151f9d94e18376ea6baab469ac39b3f30d76e963c1c995",
    "admin-shell": "862edd23f60971b3fb777ba2b613d6bffbff99f32362dc40014311016de44c0e",
    "reboot-toprgu": "0011b9cc729cc04886228fb5f1f56c8243a10179f1d030647f8ac36f735b6318",
}

def require(ok: bool, reason: str) -> None:
    if not ok: raise ValueError(reason)

def check_sources() -> None:
    root = HERE / "initramfs"
    expected = set(SOURCE_DIGESTS)
    require({p.name for p in root.iterdir()} == expected, "initramfs source inventory changed")
    for name, expected_sha in SOURCE_DIGESTS.items():
        path = root / name
        require(C.sha(C.regular(path)) == expected_sha, f"published init source changed: {name}")
    wrapper = C.regular(root / "reboot-toprgu")
    require(wrapper.count(b"[ \"$#\" -eq 1 ]") == 1 and
            wrapper.count(b"expected_boot=$1") == 1 and
            wrapper.count(b"/proc/sys/kernel/random/boot_id") >= 2 and
            wrapper.count(b"/run/a53/boot-id") >= 2 and
            wrapper.count(b'[ "$boot_id" = "$expected_boot" ]') >= 2 and
            wrapper.count(b"exec /bin/busybox reboot -n -f") == 1 and
            wrapper.count(b"wrapper=busybox-reboot-n-f-v1") == 1 and b"GEMINI_TOPRGU_V1" in wrapper,
            "candidate-specific reboot wrapper changed")
    non_wrapper = b"".join(C.regular(root / name) for name in expected if name != "reboot-toprgu")
    require(b"reboot -n" not in non_wrapper and b"reboot -f" not in non_wrapper,
            "force/now reboot action leaked into executable sources")
    require(b"pwrap-reset" not in b"".join(C.regular(root / name) for name in expected),
            "old release leaked into executable sources")

def package_files(package: Path) -> tuple[Path, Path]:
    C.validate_package(package)
    dtb = package / "dtbs/mediatek/mt6797-gemini-pda.dtb"
    require(C.sha(C.regular(dtb)) == C.BASE_DTB_SHA256, "base package DTB identity changed")
    require(C.sha(C.regular(package / "Image.gz")) == C.IMAGE_GZ_SHA256, "Image.gz identity changed")
    return package / "Image.gz", dtb

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--foundation-candidate", type=Path, required=True)
    p.add_argument("--userspace", type=Path, required=True)
    p.add_argument("--credentials", type=Path, required=True)
    p.add_argument("--serviceability-dtb-sha256", required=True)
    p.add_argument("--output-root", type=Path, default=REPO / "artifacts/toprgu/candidates")
    a = p.parse_args()
    require(a.serviceability_dtb_sha256.isascii() and len(a.serviceability_dtb_sha256) == 64 and
            all(c in "0123456789abcdef" for c in a.serviceability_dtb_sha256), "DTB output identity required")
    check_sources()
    C.validate_source_pins(REPO)
    package = a.package.resolve(strict=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "HEAD"], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()
    origin_head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify",
                                  "refs/remotes/origin/main"], check=True,
                                 text=True, stdout=subprocess.PIPE).stdout.strip()
    require(head == origin_head, "source HEAD is not the exact pushed origin/main")
    require(not subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], check=True,
                               text=True, stdout=subprocess.PIPE).stdout.strip(), "source checkout is dirty")
    image_gz, base_dtb = package_files(package)
    userspace = a.userspace.resolve(strict=True)
    require(userspace.name == "userspace-dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60" and
            userspace.parent.name == "e9c028005b88ef8536ecb58c095e8d172253fa12", "unexpected userspace fetch")
    C.validate_userspace(a.userspace)
    credentials = a.credentials.resolve(strict=True)
    require(credentials == REPO / "artifacts/credentials/a53-auth", "unexpected credential bundle")
    foundation = a.foundation_candidate.resolve(strict=True)
    initramfs = foundation / "gemini-pwrap-reset-serviceability-initramfs.img"
    require(C.sha(C.regular(initramfs)) == FOUNDATION_INITRAMFS_SHA256, "foundation initramfs identity changed")
    origin = subprocess.run(["git", "-C", str(REPO), "remote", "get-url", "origin"], check=True,
                            text=True, stdout=subprocess.PIPE).stdout.strip()
    require(origin == "https://github.com/ixoo/gemini-pda-mainline.git", "origin changed")
    dtb_script = HERE / "scripts/build-serviceability-dtb.sh"
    out = a.output_root.resolve()
    require(out == REPO / "artifacts/toprgu/candidates" or REPO / "artifacts" in out.parents,
            "candidate output must remain below artifacts")
    require(not out.is_symlink() and (not out.exists() or out.is_dir()), "candidate output root is unsafe")
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(stat.S_IMODE(out.stat().st_mode) == 0o700 and out.stat().st_uid == os.getuid(),
            "candidate output root must be private")
    require(subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", "--", str(out)],
                           check=False).returncode == 0, "candidate output is not ignored")
    stage = Path(tempfile.mkdtemp(prefix=".toprgu-candidate-", dir=out))
    try:
        # Replay every composed layer twice from independently reopened inputs.
        # Only byte-identical first outputs are retained in the final directory.
        builds = []
        for suffix in ("one", "two"):
            dtb_path = stage / f"board-{suffix}.dtb"
            subprocess.run(["/bin/bash", str(dtb_script), "--base-dtb", str(base_dtb),
                            "--output", str(dtb_path), "--expected-sha256",
                            a.serviceability_dtb_sha256], check=True)
            subprocess.run([sys.executable, str(HERE / "scripts/validate-dtb.py"),
                            "--base", str(base_dtb), "--derived", str(dtb_path),
                            "--expected-sha256", a.serviceability_dtb_sha256], check=True)
            input_value = C.compute_input_id(C.regular(image_gz), C.regular(dtb_path),
                                             C.regular(initramfs), userspace, credentials)
            ramdisk_value, member_values = C.compose_initramfs(
                REPO, initramfs, userspace, credentials, input_value)
            ramdisk_path = stage / f"initramfs-{suffix}.img"
            C.write_exclusive(ramdisk_path, ramdisk_value)
            raw_value, metadata_value = C.android_v0(image_gz, ramdisk_path, dtb_path, REPO)
            padded_value = C.pad(raw_value)
            builds.append((C.regular(dtb_path), input_value, ramdisk_value,
                           member_values, raw_value, padded_value, metadata_value))
        require(builds[0] == builds[1],
                "independent DT/initramfs/Android-v0/padded constructions differ")
        dtb, input_id, ramdisk, members, raw, padded, metadata = builds[0]
        C.write_exclusive(stage / "board.dtb", dtb)
        C.write_exclusive(stage / "initramfs.img", ramdisk)
        C.write_exclusive(stage / "Image.gz", C.regular(image_gz))
        C.write_exclusive(stage / "kernel.config", C.regular(package / "kernel.config"))
        C.write_exclusive(stage / "boot2-padded.img", padded)
        manifest = {"schema": 1, "experiment": HERE.name, "profile": C.PROFILE, "release": C.RELEASE,
                    "preparation_state": "preparing", "physical_admission": False,
                    "source_commit": head, "package_commit": PACKAGE_COMMIT,
                    "package_inventory_sha256": C.PACKAGE_INVENTORY_SHA256,
                    "userspace_revision": "e9c028005b88ef8536ecb58c095e8d172253fa12",
                    "userspace_manifest_sha256": C.USERSPACE_MANIFEST_SHA256,
                    "base_dtb_sha256": C.BASE_DTB_SHA256, "serviceability_dtb_sha256": C.sha(dtb),
                    "input_id": input_id,
                    "initramfs_sha256": C.sha(ramdisk), "raw_sha256": C.sha(raw),
                    "padded_sha256": C.sha(padded), "raw_size": len(raw), "padded_size": len(padded),
                    "android_v0": metadata, "members": members, "secret_bearing": True,
                    "physical_action": "none"}
        name = out / ("candidate-" + C.sha(padded))
        require(not name.exists(), "candidate already exists; refusing overwrite")
        for path in stage.glob("board-*.dtb"):
            path.unlink()
        for path in stage.glob("initramfs-*.img"):
            path.unlink()
        (stage / "candidate.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "candidate.json").chmod(0o600)
        stage.rename(name)
        try:
            subprocess.run([sys.executable, str(HERE / "scripts/validate-candidate.py"),
                            "--candidate", str(name), "--base-dtb", str(base_dtb),
                            "--foundation-initramfs", str(initramfs), "--userspace", str(userspace),
                            "--credentials", str(credentials)], check=True)
        except BaseException:
            shutil.rmtree(name)
            raise
        print(f"candidate={name.relative_to(REPO)}\nphysical_admission=no\nraw_sha256={manifest['raw_sha256']}\npadded_sha256={manifest['padded_sha256']}")
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return 0
if __name__ == "__main__": raise SystemExit(main())
