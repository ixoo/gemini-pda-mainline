#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Buildbox-only WMT, DMA, pstore or capture primitive compile; no kernel image."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import struct
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


def compile_capture_dt(project, source, patched, work, output, compiler, environment):
    """Compile the full native board twice and require only the PMSG split."""
    dts = "arch/arm64/boot/dts"
    board = "aeon6797_6m_n.dts"
    cust = Path("/workspace/gemini-pda/gemian-artifacts/gemian-observer-a98ffc90f979/outputs/cust.dtsi")
    assert digest(cust) == "7a7eb416499346afff30c15f967ccb9cf79323c076204b6a953515db74811632"
    (output / dts).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cust, output / dts / "cust.dtsi")
    shutil.copyfile(source / dts / board, patched / dts / board)
    dtc = Path(shutil.which("dtc"))
    dtc_version = run([str(dtc), "--version"])
    parser_path = project / "experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts/build_dtb.py"
    spec = importlib.util.spec_from_file_location("capture_dtb_parser", parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    trees, dtbs = [], []
    for label, tree in (("baseline", source), ("capture", patched)):
        preprocessed = work / (label + ".dts")
        dtb = work / (label + ".dtb")
        args = [str(compiler), "-E", "-nostdinc", "-I" + str(tree / dts),
                "-I" + str(source / dts), "-I" + str(output / dts),
                "-I" + str(source / dts / "include"), "-I" + str(output / "include"),
                "-I" + str(source / "drivers/of/testcase-data"),
                "-undef", "-D__DTS__", "-x", "assembler-with-cpp",
                "-o", str(preprocessed), str(tree / dts / board)]
        with (work / (label + "-dt.log")).open("w") as stream:
            compile_logged(args, stream, cwd=output, env=environment, timeout=120)
            compile_logged([str(dtc), "-I", "dts", "-O", "dtb", "-b", "0",
                            "-i", str(source / dts), "-o", str(dtb), str(preprocessed)],
                           stream, cwd=output, env=environment, timeout=120)
        trees.append({key: value for key, (_, value) in parser.properties(dtb.read_bytes()).items()})
        dtbs.append(dtb)
    expected = dict(trees[0])
    parent = "/reserved-memory/pstore-reserved-memory@44410000"
    child = "/reserved-memory/pmsg-capture-reserved-memory@444e0000"
    assert expected[(parent, "reg")] == struct.pack(">4I", 0, 0x44410000, 0, 0xe0000)
    assert not any(key[0] == child for key in expected)
    expected[(parent, "reg")] = struct.pack(">4I", 0, 0x44410000, 0, 0xd0000)
    expected[(child, "reg")] = struct.pack(">4I", 0, 0x444e0000, 0, 0x10000)
    expected[(child, "no-map")] = b""
    assert trees[1] == expected, "unexpected native board property change"
    return {"board_source_sha256": digest(source / dts / board),
            "cust_dtsi_sha256": digest(cust), "dtc_version": dtc_version,
            "dtc_sha256": digest(dtc), "parser_sha256": digest(parser_path),
            "baseline_dtb_sha256": digest(dtbs[0]), "capture_dtb_sha256": digest(dtbs[1]),
            "property_delta": "one existing reg change; one new reg and empty no-map; all other properties equal",
            "combined_extent": "0x44410000..0x444f0000 unchanged; PMSG 0x444e0000..0x444f0000"}


def main():
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    experiment = Path(__file__).resolve().parent
    project = experiment.parents[1]
    commit = run(["git", "-C", str(project), "rev-parse", "HEAD"])
    assert len(sys.argv) in (2, 3) and sys.argv[1] == commit
    mode = sys.argv[2] if len(sys.argv) == 3 else "--wmt"
    assert mode in ("--wmt", "--pstore", "--capture-writer", "--dma", "--stop",
                    "--firmware-read", "--firmware-read-safe", "--firmware-image", "--emi", "--provider-off",
                    "--common-off-safe", "--common-off", "--operation-ownership", "--request-capture", "--request-firmware", "--tx-payload")
    tx_payload = mode == "--tx-payload"
    request_firmware = mode == "--request-firmware" or tx_payload
    request_capture = mode == "--request-capture" or request_firmware
    ownership = mode == "--operation-ownership" or request_capture
    common_off = mode == "--common-off" or ownership
    common_off_safe = mode == "--common-off-safe"
    capture = mode == "--capture-writer"
    provider_off = mode == "--provider-off" or common_off
    emi_capture = mode == "--emi" or provider_off
    firmware_image = mode == "--firmware-image" or emi_capture
    firmware_safe = mode == "--firmware-read-safe" or firmware_image
    firmware_read = mode == "--firmware-read" or firmware_safe
    stop = mode == "--stop" or firmware_read
    dma = mode == "--dma" or stop
    pstore = mode in ("--pstore", "--capture-writer")
    relative = "fs/pstore/" if pstore else RELATIVE
    files = ("pmsg", "inode", "ram_core", "ram") if pstore else FILES
    label = "wifi-pstore-objects-" if pstore else "wifi-startup-objects-"
    if common_off_safe:
        label = "wifi-common-off-safe-objects-"
    if capture:
        files = ("ram_core",)
        label = "wifi-capture-writer-objects-"
    if dma:
        relative = "drivers/misc/mediatek/connectivity/wlan/gen3/"
        hif = "os/linux/hif/ahb_sdioLike/"
        files = tuple(hif + name for name in ("ahb", "ahb_pdma", "hif_capture"))
        label = "wifi-dma-objects-"
        if stop:
            files = ("common/wlan_lib", "os/linux/gl_init", hif + "ahb", hif + "hif_stop_capture")
            label = "wifi-stop-objects-"
        if firmware_read:
            files = ("os/linux/gl_kal",)
            label = "wifi-firmware-read-safe-objects-" if firmware_safe else "wifi-firmware-read-objects-"
        if firmware_image:
            files = ("os/linux/gl_kal", "os/linux/gl_init", "common/wlan_lib", "nic/nic_pwr_mgt", hif + "hif_fw_capture")
            label = "wifi-firmware-image-objects-"
    if emi_capture:
        files += ("drivers/misc/mediatek/emi_mpu/emi_reg_rw",
                  "drivers/misc/mediatek/emi_mpu/mt6797/emi_mpu")
        label = "wifi-emi-objects-"
    if provider_off:
        files += ("drivers/clk/mediatek/clk-mt6797-pg",)
        label = "wifi-provider-off-objects-"
    common_headers = RELATIVE + "core/include"
    if common_off:
        files += tuple(RELATIVE + name for name in FILES)
        files += (RELATIVE + "mt6797/mtk_wcn_consys_hw",)
        label = "wifi-common-off-objects-"
    if ownership:
        files += (RELATIVE + "core/wmt_exp",)
        label = "wifi-operation-ownership-objects-"
    if request_capture:
        label = "wifi-request-capture-objects-"
    if request_firmware:
        label = "wifi-request-firmware-objects-"
    if tx_payload:
        files += ("nic/nic_tx", hif + "ahb")
        label = "wifi-tx-payload-objects-"
    def unit_path(name):
        return name if name.startswith("drivers/") else relative + name
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
    package = root / "gemian-artifacts" / (label + commit)
    assert not package.exists(), "refusing to overwrite a result"
    environment = dict(os.environ, LD_LIBRARY_PATH=str(toolchain / "root/usr/lib/x86_64-linux-gnu"),
                       HOST_EXTRACFLAGS="-fcommon")
    with tempfile.TemporaryDirectory(prefix=label, dir=root / "build") as tmp:
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
        for name in files:
            if dma and Path(name).name in ("hif_capture", "hif_stop_capture", "hif_fw_capture"):
                continue
            dest = patched / (unit_path(name) + ".c")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / (unit_path(name) + ".c"), dest)
        # Copy neighboring headers so quoted includes resolve to the patched header.
        headers = relative + hif + "include" if dma else relative if pstore else RELATIVE + "core/include"
        if pstore:
            for path in (source / headers).glob("*.h"):
                shutil.copyfile(path, patched / headers / path.name)
            if not capture:
                for extra in ("include/linux/pstore_ram.h", "arch/arm64/boot/dts/mt6797.dtsi"):
                    (patched / extra).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source / extra, patched / extra)
        else:
            shutil.copytree(source / headers, patched / headers)
        patch_dir = experiment / "patches" / "pstore" if pstore else experiment / "patches"
        patches = [] if capture else sorted(patch_dir.glob("*.patch"))
        if common_off_safe:
            patches += sorted((experiment / "patches/common-off-errors").glob("*.patch"))
        if dma:
            patches = sorted((experiment / "patches/pstore").glob("*.patch"))
            patches += sorted((experiment / "patches/dma").glob("*.patch"))
            if stop:
                patches += sorted((experiment / "patches/stop").glob("*.patch"))
                shutil.copytree(source / relative / "include", patched / relative / "include")
                shutil.copyfile(source / relative / hif / "ahb_pdma.c", patched / relative / hif / "ahb_pdma.c")
            if firmware_read:
                patches += sorted((experiment / "patches/firmware-read").glob("*.patch"))
                if firmware_safe:
                    patches += sorted((experiment / "patches/firmware-read-safety").glob("*.patch"))
                for extra in ("common/wlan_lib.c", "os/linux/gl_init.c", hif + "ahb.c"):
                    dest = patched / relative / extra
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source / relative / extra, dest)
            if firmware_image:
                patches += sorted((experiment / "patches/firmware-image").glob("*.patch"))
                shutil.copytree(source / relative / "os/linux/include", patched / relative / "os/linux/include")
            if emi_capture:
                patches += sorted((experiment / "patches/emi").glob("*.patch"))
                emi_header = "drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h"
                (patched / emi_header).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / emi_header, patched / emi_header)
            if provider_off:
                patches += sorted((experiment / "patches/provider-off").glob("*.patch"))
                for path in (source / "drivers/clk/mediatek").glob("*.h"):
                    shutil.copyfile(path, patched / "drivers/clk/mediatek" / path.name)
            if common_off:
                shutil.copytree(source / common_headers, patched / common_headers)
                for path in (source / RELATIVE / "mt6797").glob("*.h"):
                    shutil.copyfile(path, patched / RELATIVE / "mt6797" / path.name)
                patches += sorted((experiment / "patches").glob("*.patch"))
                patches += sorted((experiment / "patches/common-off-errors").glob("*.patch"))
                patches += sorted((experiment / "patches/common-off").glob("*.patch"))
                if ownership:
                    patches += sorted((experiment / "patches/operation-ownership").glob("*.patch"))
                if request_capture:
                    patches += sorted((experiment / "patches/request-capture").glob("*.patch"))
                if request_firmware:
                    patches += sorted((experiment / "patches/request-firmware").glob("*.patch"))
                if tx_payload:
                    patches += sorted((experiment / "patches/tx-payload").glob("*.patch"))
            for extra in ("include/linux/pstore_ram.h", "arch/arm64/boot/dts/mt6797.dtsi",
                          "drivers/misc/mediatek/connectivity/wlan/gen3/Makefile",
                          "fs/pstore/ram.c", "fs/pstore/ram_core.c", "fs/pstore/internal.h",
                          "fs/pstore/pmsg.c", "fs/pstore/inode.c"):
                (patched / extra).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / extra, patched / extra)
        assert len(patches) == (27 if tx_payload else 26 if request_firmware else 25 if request_capture else 24 if ownership else 23 if common_off else 17 if provider_off else 16 if emi_capture else 15 if firmware_image else 14 if firmware_safe else 13 if firmware_read else 12 if stop else 11 if dma else 0 if capture else 10 if pstore else 5 if common_off_safe else 4)
        for patch in patches:
            if tx_payload and patch.parent.name == "tx-payload":
                tx_pins = json.loads((experiment / "results/tx-payload-sources.json").read_text())
                assert digest(patch) == tx_pins["patch_sha256"]
                tx_parent = work / "tx-parent"
                for path, expected in tx_pins["parents"].items():
                    assert digest(patched / path) == expected, path
                    (tx_parent / path).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(patched / path, tx_parent / path)
            if request_firmware and patch.parent.name == "request-firmware":
                request_fw_pins = json.loads((experiment / "results/request-firmware-sources.json").read_text())
                assert digest(patch) == request_fw_pins["patch_sha256"]
                for path, expected in request_fw_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if request_capture and patch.parent.name == "request-capture":
                request_pins = json.loads((experiment / "results/request-capture-sources.json").read_text())
                assert digest(patch) == request_pins["patch_sha256"]
                for path, expected in request_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if ownership and patch.parent.name == "operation-ownership":
                ownership_pins = json.loads((experiment / "results/operation-ownership-sources.json").read_text())
                assert digest(patch) == ownership_pins["patch_sha256"]
                for path, expected in ownership_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if (common_off_safe or common_off) and patch.parent.name == "common-off-errors":
                common_pins = json.loads((experiment / "results/common-off-errors-sources.json").read_text())
                assert digest(patch) == common_pins["patch_sha256"]
                for path, expected in common_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if common_off and patch.parent.name == "common-off":
                common_capture_pins = json.loads((experiment / "results/common-off-capture-sources.json").read_text())
                assert digest(patch) == common_capture_pins["patch_sha256"]
                for path, expected in common_capture_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if stop and patch.parent.name == "stop":
                stop_pins = json.loads((experiment / "results/stop-capture-sources.json").read_text())
                for path, expected in stop_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if firmware_read and patch.parent.name == "firmware-read":
                read_pins = json.loads((experiment / "results/firmware-read-capture-sources.json").read_text())
                assert digest(patch) == read_pins["patch_sha256"]
                for path, expected in read_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if firmware_safe and patch.parent.name == "firmware-read-safety":
                safe_pins = json.loads((experiment / "results/firmware-read-safety-sources.json").read_text())
                assert digest(patch) == safe_pins["patch_sha256"]
                assert digest(patched / safe_pins["parent"]["path"]) == safe_pins["parent"]["sha256"]
                for path, expected in read_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if firmware_image and patch.parent.name == "firmware-image":
                image_pins = json.loads((experiment / "results/firmware-image-capture-sources.json").read_text())
                assert digest(patch) == image_pins["patch_sha256"]
                for path, expected in image_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if emi_capture and patch.parent.name == "emi":
                emi_pins = json.loads((experiment / "results/emi-capture-sources.json").read_text())
                assert digest(patch) == emi_pins["patch_sha256"]
                for path, expected in emi_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            if provider_off and patch.parent.name == "provider-off":
                off_pins = json.loads((experiment / "results/provider-off-capture-sources.json").read_text())
                assert digest(patch) == off_pins["patch_sha256"]
                for path, expected in off_pins["parents"].items():
                    assert digest(patched / path) == expected, path
            subprocess.run(["git", "apply", str(patch)], cwd=patched, check=True)
            if tx_payload and patch.parent.name == "tx-payload":
                for path, expected in tx_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
                support = work / "tx-support"
                support.mkdir()
                for entry in json.loads((experiment / "results/dma-hook-sources.json").read_text())["sources"]:
                    shutil.copyfile(source / entry["path"], support / Path(entry["path"]).name)
                shutil.copyfile(patched / relative / hif / "ahb_pdma.c", support / "ahb_pdma-capture.c")
                subprocess.run(["python3", str(experiment / "test-tx-payload.py"),
                                "--parent", str(tx_parent), "--tree", str(patched),
                                "--support", str(support)], check=True)
            if request_firmware and patch.parent.name == "request-firmware":
                for path, expected in request_fw_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
                subprocess.run(["python3", str(experiment / "test-request-firmware.py"),
                                "--tree", str(patched)], check=True)
            if request_capture and patch.parent.name == "request-capture":
                for path, expected in request_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
                subprocess.run(["python3", str(experiment / "test-request-capture.py"),
                                "--tree", str(patched)], check=True)
            if ownership and patch.parent.name == "operation-ownership":
                for path, expected in ownership_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if (common_off_safe or common_off) and patch.parent.name == "common-off-errors":
                for path, expected in common_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if common_off and patch.parent.name == "common-off":
                for path, expected in common_capture_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if provider_off and patch.parent.name == "provider-off":
                for path, expected in off_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if firmware_image and patch.parent.name == "firmware-image":
                for path, expected in image_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if stop and patch.parent.name == "stop":
                for path, expected in stop_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
            if firmware_safe and patch.parent.name == "firmware-read-safety":
                assert digest(patched / safe_pins["parent"]["path"]) == safe_pins["output_sha256"]
        if dma and not stop:
            pinned = json.loads((experiment / "results" / (
                "stop-capture-sources.json" if stop else "dma-capture-sources.json")).read_text())
            sections = (("outputs", patched),) if stop else (("parents", source), ("outputs", patched))
            for section, tree in sections:
                for path, expected in pinned[section].items():
                    assert digest(tree / path) == expected, path
        if emi_capture:
            final_sources = dict(emi_pins["outputs"])
            if request_firmware:
                final_sources.update(request_fw_pins["outputs"])
            if tx_payload:
                final_sources.update(tx_pins["outputs"])
            for path, expected in final_sources.items():
                assert digest(patched / path) == expected, path
        elif firmware_image:
            for path, expected in image_pins["outputs"].items():
                assert digest(patched / path) == expected, path
        elif firmware_read:
            if firmware_safe:
                assert digest(patched / safe_pins["parent"]["path"]) == safe_pins["output_sha256"]
            else:
                for path, expected in read_pins["outputs"].items():
                    assert digest(patched / path) == expected, path
        if capture:
            shutil.copyfile(experiment / "capture-slot-writer.h",
                            patched / relative / "capture-slot-writer.h")
            # External wrappers force emission of both static prototype bodies.
            with (patched / relative / "ram_core.c").open("a") as stream:
                stream.write('''
#include "capture-slot-writer.h"
int wfc_compile_begin(struct wfc_writer *w, u8 __iomem *p, size_t n,
                      const u8 *c, const u8 *id)
{ return wfc_writer_begin(w, p, n, c, id); }
int wfc_compile_append(struct wfc_writer *w, unsigned int k, u32 tx,
                       const u8 *p, size_t n)
{ return wfc_slot_write(w, k, tx, p, n); }
''')
        records = []
        header = headers + ("/hif.h" if dma else "/wmt_ctrl.h")
        if not pstore:
            assert digest(source / header) != digest(patched / header)
        for relative_name in files:
            name = Path(relative_name).name
            suffix = unit_path(relative_name) + ".c"
            wlan_unit = dma and suffix.startswith(relative)
            common_unit = common_off and suffix.startswith(RELATIVE)
            template = relative + hif + "ahb.c" if dma and name in ("hif_capture", "hif_stop_capture", "hif_fw_capture") else suffix
            lines = [line for line in recorded.read_text().splitlines()
                     if " -c " in line and line.endswith("/" + template)]
            assert len(lines) == 1, (name, len(lines))
            args = shlex.split(lines[0])
            assert args[0] == str(compiler) and args[-1] == old_source + "/" + template
            assert args[args.index("-o") + 1] == template[:-2] + ".o"
            args = [a.replace(old_source, str(source)) for a in args]
            baseline = work / (name + "-baseline.o")
            args[args.index("-o") + 1] = str(baseline)
            args = ["-Wp,-MD," + str(work / (name + "-baseline.d")) if a.startswith("-Wp,-MD,") else a
                    for a in args]
            if not (dma and name in ("hif_capture", "hif_stop_capture", "hif_fw_capture")):
                with (work / (name + "-baseline.log")).open("w") as stream:
                    compile_logged(args, stream, cwd=output, env=environment, timeout=120)
            result = work / (name + ".o")
            args[args.index("-o") + 1] = str(result)
            args[-1] = str(patched / suffix)
            args.insert(1, "-I" + str(patched / headers))
            if common_unit:
                args.insert(1, "-I" + str(patched / common_headers))
            if emi_capture:
                args.insert(1, "-I" + str((patched / emi_header).parent.parent))
            if firmware_image:
                args.insert(1, "-I" + str(patched / relative / "os/linux/include"))
            if stop:
                # precomp.h includes "hal.h" by basename from include/nic.
                args.insert(1, "-I" + str(patched / relative / "include/nic"))
                args.insert(1, "-I" + str(patched / relative / "include"))
            if (pstore and not capture) or dma:
                args.insert(1, "-I" + str(patched / "include"))
            args = ["-Wp,-MD," + str(work / (name + ".d")) if a.startswith("-Wp,-MD,") else a
                    for a in args]
            with (work / (name + ".log")).open("w") as stream:
                compile_logged(args, stream, cwd=output, env=environment, timeout=120)
            dependencies = (work / (name + ".d")).read_text().replace("\\\n", " ").split()
            if ownership and name in ("wmt_lib", "wmt_exp"):
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / (name + "-ownership.disasm")).write_text(disassembly + "\n")
                if name == "wmt_lib":
                    for symbol in ("wmt_op_complete", "wmt_op_put", "mutex_lock", "mutex_unlock"):
                        assert symbol in disassembly, symbol
            if request_capture and name in ("wmt_lib", "wmt_exp", "wmt_dev", "clk-mt6797-pg"):
                assert str(patched / "include/linux/mt6797_wifi_capture.h") in dependencies
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                if name == "wmt_dev":
                    (work / "wmt_dev-request.disasm").write_text(disassembly + "\n")
                calls = {"wmt_lib": ("begin", "bind", "end", "common_begin", "common_end"),
                         "wmt_exp": ("bind",), "wmt_dev": ("begin", "end"),
                         "clk-mt6797-pg": ("common_begin", "common_end")}
                for call in calls[name]:
                    assert "mt6797_wfc_request_" + call in disassembly, (name, call)
                if name == "wmt_lib":
                    assert str(patched / RELATIVE / "core/wmt-request-capture.h") in dependencies
                    for symbol in ("ramoops_capture_active", "ramoops_capture_append", "wfc_request_"):
                        assert symbol in disassembly, symbol
            if (common_off_safe or common_off) and name == "wmt_core":
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / "wmt_core-errors.disasm").write_text(disassembly + "\n")
            if common_unit:
                assert "-DMODULE" not in args
                if name != "mtk_wcn_consys_hw":
                    assert str(patched / common_headers / "wmt_ctrl.h") in dependencies
                    assert str(source / common_headers / "wmt_ctrl.h") not in dependencies
                if name in ("wmt_core", "mtk_wcn_consys_hw"):
                    assert str(patched / "include/linux/mt6797_wifi_capture.h") in dependencies
                    disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                       "-dr", str(result)], env=environment)
                    calls = ("common_off_begin", "common_off_end") if name == "wmt_core" else ("clock_off_begin", "clock_off_end")
                    for call in calls:
                        assert "mt6797_wfc_" + call in disassembly
                    if name == "mtk_wcn_consys_hw":
                        (work / "mtk_wcn_consys_hw-common.disasm").write_text(disassembly + "\n")
            if not pstore and (not dma or wlan_unit) and name not in ("hif_capture", "hif_stop_capture", "hif_fw_capture"):
                assert str(patched / header) in dependencies, name
                assert str(source / header) not in dependencies, name
            if wlan_unit:
                assert "-DMODULE" not in args
                assert str(patched / headers / "hif_capture.h") in dependencies
                if stop:
                    if name != "hif_fw_capture":
                        assert str(patched / headers / "hif_stop_capture.h") in dependencies
                    if name in ("wlan_lib", "gl_init", "gl_kal", "nic_pwr_mgt"):
                        assert str(patched / relative / "include/nic/hal.h") in dependencies, name
                    if name not in ("hif_stop_capture", "hif_fw_capture"):
                        assert str(patched / relative / "include/wlan_lib.h") in dependencies, name
                if name in ("hif_capture", "hif_stop_capture", "hif_fw_capture"):
                    assert str(patched / "include/linux/pstore_ram.h") in dependencies
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / (name + "-capture.disasm")).write_text(disassembly + "\n")
                assert ({"gl_kal": "kalFirmwareLoadCapture", "gl_init": "kalFirmwareImageMapping",
                         "wlan_lib": "wfc_fw_image_begin", "nic_pwr_mgt": "kalFirmwareImageMapping", "hif_fw_capture": "wfc_fw_image_begin",
                         "nic_tx": "wfc_fw_tx_staged", "ahb": "wfc_fw_tx_payload"}[name] if firmware_image else
                        "kalFirmwareLoadCapture" if firmware_read else "wlanAdapterStop" if stop and name == "gl_init" else
                        "wfc_stop_" if stop else "wfc_dma_") in disassembly
                if firmware_image:
                    assert str(patched / headers / "hif_fw_capture.h") in dependencies
                    if name != "hif_fw_capture":
                        assert str(patched / relative / "os/linux/include/gl_kal.h") in dependencies
                if firmware_read and name == "gl_kal":
                    assert str(patched / "include/linux/pstore_ram.h") in dependencies
                if (firmware_read and name == "gl_kal") or name in ("hif_capture", "hif_stop_capture", "hif_fw_capture"):
                    assert "ramoops_capture_active" in disassembly
                    assert "ramoops_capture_append" in disassembly
            if emi_capture and name in ("wlan_lib", "hif_fw_capture"):
                assert "wfc_fw_emi_begin" in disassembly
                assert "wfc_fw_emi_mapping" in disassembly
                assert "wfc_fw_emi_copy" in disassembly
                if name == "wlan_lib":
                    assert str(patched / emi_header) in dependencies
                    assert str(source / emi_header) not in dependencies
                    assert "emi_mpu_set_region_protection_capture" in disassembly
            if emi_capture and suffix.startswith("drivers/misc/mediatek/emi_mpu/"):
                assert str(patched / emi_header) in dependencies
                assert str(source / emi_header) not in dependencies
                assert "-DMODULE" not in args
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / (name + "-capture.disasm")).write_text(disassembly + "\n")
                assert "mt_emi_mpu_set_region_protection_capture" in disassembly
                if name == "emi_reg_rw":
                    assert str(patched / "include/linux/pstore_ram.h") in dependencies
                    assert "ramoops_capture_append" in disassembly
                    assert "ramoops_capture_active" in disassembly
            if provider_off and name == "clk-mt6797-pg":
                for included in ("clk-mt6797-wfc.h", "clk-mt6797-pg.h", "clk-mtk-v1.h"):
                    assert str(patched / "drivers/clk/mediatek" / included) in dependencies
                    assert str(source / "drivers/clk/mediatek" / included) not in dependencies
                if common_off:
                    for included in ("drivers/clk/mediatek/clk-mt6797-wfc-common.h",
                                     "include/linux/mt6797_wifi_capture.h"):
                        assert str(patched / included) in dependencies
                assert str(patched / "include/linux/pstore_ram.h") in dependencies
                assert "-DMODULE" not in args
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / (name + "-capture.disasm")).write_text(disassembly + "\n")
                # Static provider helpers may be inlined into their callers.
                for symbol in ("ramoops_capture_active", "ramoops_capture_append", "wfc_off_",
                               "pg_unprepare"):
                    assert symbol in disassembly, symbol
            if request_firmware and name in ("wmt_lib", "gl_kal", "hif_fw_capture"):
                assert str(patched / "include/linux/mt6797_wifi_capture.h") in dependencies
                assert "mt6797_wfc_request_firmware" in disassembly, name
            if tx_payload and name in ("wlan_lib", "nic_tx", "ahb", "hif_fw_capture"):
                assert str(patched / headers / "hif_fw_capture.h") in dependencies
                calls = {"wlan_lib": ("wfc_fw_tx_begin", "wfc_fw_tx_command", "wfc_fw_tx_finish", "nicTxInitCmdCapture"),
                         "nic_tx": ("wfc_fw_tx_staged", "kalDevPortWriteCapture"),
                         "ahb": ("wfc_fw_tx_payload", "wfc_fw_tx_dma", "wfc_fw_tx_port_return"),
                         "hif_fw_capture": ("wfc_fw_tx_payload", "crypto_shash_digest")}[name]
                for symbol in calls:
                    assert symbol in disassembly, (name, symbol)
            if capture:
                assert str(patched / relative / "capture-slot-writer.h") in dependencies
                table = run(["readelf", "-Ws", str(result)])
                assert "wfc_compile_begin" in table and "wfc_compile_append" in table
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / "capture-writer.disasm").write_text(disassembly + "\n")
            if pstore and not capture and name in ("ram", "ram_core"):
                assert str(patched / "include/linux/pstore_ram.h") in dependencies
                if name == "ram":
                    assert str(patched / "fs/pstore/wifi_capture.h") in dependencies
                disassembly = run([str(toolchain / "wrappers/aarch64-linux-gnu-objdump"),
                                   "-dr", str(result)], env=environment)
                (work / (name + "-capture.disasm")).write_text(disassembly + "\n")
            assert "AArch64" in run(["readelf", "-h", str(result)])
            records.append({"file": suffix, "baseline_source_sha256": digest(source / suffix) if (source / suffix).exists() else None,
                            "baseline_object_sha256": digest(baseline) if baseline.exists() else None,
                            "patched_source_sha256": digest(patched / suffix),
                            "object_sha256": digest(result),
                            "baseline_command_sha256": hashlib.sha256(lines[0].encode()).hexdigest(),
                            "patched_header_dependency_verified": None if pstore else True,
                            "diagnostics_bytes": (work / (name + ".log")).stat().st_size})
        receipt = {"project_commit": commit, "source_commit": REVISION,
                   "scope": f"{len(files)} complete translation units; no kernel link or device execution",
                   "patched_header_sha256": None if pstore else digest(patched / header),
                   "toolchain_manifest_sha256": TOOLCHAIN,
                   "config_sha256": digest(output / ".config"), "config_delta": delta,
                   "patches": {p.name: digest(p) for p in patches}, "objects": records}
        if capture:
            receipt["capture_header_sha256"] = digest(experiment / "capture-slot-writer.h")
            receipt["scope"] = "Native ARM64 header/object check with emitted wrappers; no owner integration, kernel link or device execution"
        if pstore and not capture:
            receipt["capture_header_sha256"] = digest(patched / "fs/pstore/wifi_capture.h")
            assert receipt["capture_header_sha256"] == digest(experiment / "capture-slot-writer.h")
            receipt["dt"] = compile_capture_dt(project, source, patched, work, output, compiler, environment)
        package.mkdir()
        for file in [log, *work.glob("*.o"), *work.glob("*.disasm"), *work.glob("*.dtb"),
                     *work.glob("*-dt.log"), *work.glob("*-baseline.log"),
                     *(work / (Path(name).name + ".log") for name in files)]:
            shutil.copyfile(file, package / file.name)
        (package / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (package / "SHA256SUMS").write_text("".join(
            digest(p) + "  " + p.name + "\n" for p in sorted(package.iterdir())))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
