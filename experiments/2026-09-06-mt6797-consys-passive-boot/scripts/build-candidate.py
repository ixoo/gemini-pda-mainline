#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build two identical private passive-CON SYS Android-v0 candidates."""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent; REPO = HERE.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent)); import candidate_lib as C  # noqa: E402

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--package", type=Path, required=True)
    p.add_argument("--foundation-initramfs", type=Path, required=True); p.add_argument("--userspace", type=Path, required=True)
    p.add_argument("--credentials", type=Path, required=True); p.add_argument("--serviceability-dtb", type=Path, required=True)
    a = p.parse_args()
    C.validate_source_pins(REPO)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()
    published = subprocess.run(["git", "-C", str(REPO), "rev-parse", "origin/main"],
                               check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    clean = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                           check=True, text=True, stdout=subprocess.PIPE).stdout
    C.require(head == published and not clean, "candidate builder requires exact clean origin/main")
    package = a.package.resolve(strict=True); C.validate_package(package)
    base = package / "dtbs/mediatek/mt6797-gemini-pda.dtb"; C.require(C.sha(C.regular(base)) == C.BASE_DTB_SHA256, "base DTB identity changed")
    foundation = a.foundation_initramfs.resolve(strict=True); C.require(C.sha(C.regular(foundation)) == C.FOUNDATION_INITRAMFS_SHA256, "foundation identity changed")
    C.validate_userspace(a.userspace); C.validate_credentials(a.credentials)
    dtb = a.serviceability_dtb.resolve(strict=True); C.require(C.sha(C.regular(dtb)) == C.SERVICEABILITY_DTB_SHA256, "serviceability DTB identity changed")
    out = C.validate_private_root(C.ARTIFACT_ROOT / "candidates", "candidates")
    stage = Path(tempfile.mkdtemp(prefix=".consys-candidate-", dir=out)); builds = []
    try:
        for n in ("one", "two"):
            image = package / "Image.gz"; input_id = C.compute_input_id(C.regular(image), C.regular(dtb), C.regular(foundation), a.userspace, a.credentials)
            ramdisk, members = C.compose_initramfs(REPO, foundation, a.userspace, a.credentials, input_id)
            rp = stage / f"ramdisk-{n}"; C.write_exclusive(rp, ramdisk); raw, meta = C.android_v0(image, rp, dtb, REPO); padded = C.pad(raw)
            builds.append((input_id, ramdisk, members, raw, padded, meta))
        C.require(builds[0] == builds[1], "independent candidate assemblies differ")
        input_id, ramdisk, members, raw, padded, meta = builds[0]
        for name, data in (("Image.gz", C.regular(package/"Image.gz")), ("kernel.config", C.regular(package/"kernel.config")), ("board.dtb", C.regular(dtb)), ("initramfs.img", ramdisk), ("boot2-padded.img", padded)):
            C.write_exclusive(stage / name, data)
        manifest = {"schema": 1, "experiment": HERE.name, "profile": C.PROFILE, "release": C.RELEASE, "preparation_state": "preparing", "physical_admission": False,
          "source_commit": "f9981eaf63381a558f77be251da4c2320cb4321b", "package_commit": "f9981eaf63381a558f77be251da4c2320cb4321b", "package_inventory_sha256": C.PACKAGE_INVENTORY_SHA256,
          "userspace_revision": "e9c028005b88ef8536ecb58c095e8d172253fa12", "userspace_manifest_sha256": C.USERSPACE_MANIFEST_SHA256,
          "base_dtb_sha256": C.BASE_DTB_SHA256, "serviceability_dtb_sha256": C.sha(C.regular(dtb)), "input_id": input_id, "initramfs_sha256": C.sha(ramdisk), "raw_sha256": C.sha(raw), "padded_sha256": C.sha(padded), "raw_size": len(raw), "padded_size": len(padded), "assembly_replays": 2, "android_v0": meta, "members": members, "secret_bearing": True, "physical_action": "none"}
        (stage / "candidate.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n"); (stage/"candidate.json").chmod(0o600)
        for temporary in stage.glob("ramdisk-*"): temporary.unlink()
        name = out / ("candidate-" + C.sha(padded)); C.require(not name.exists(), "candidate already exists; refusing overwrite"); stage.rename(name)
        try:
            subprocess.run([
                sys.executable, str(HERE / "scripts/validate-candidate.py"),
                "--candidate", str(name), "--package", str(package),
                "--foundation-initramfs", str(foundation),
                "--userspace", str(a.userspace.resolve(strict=True)),
                "--credentials", str(a.credentials.resolve(strict=True)),
            ], check=True, stdout=subprocess.DEVNULL)
        except Exception:
            shutil.rmtree(name)
            raise
        print(f"candidate={name}\nphysical_admission=no\npadded_sha256={C.sha(padded)}")
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return 0
if __name__ == "__main__": raise SystemExit(main())
