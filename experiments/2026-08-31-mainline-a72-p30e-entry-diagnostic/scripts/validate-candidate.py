#!/usr/bin/env python3
"""Source-pin the independent validator to the P30E entry candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "29b35ea8c07abcfa840e868a7b23075a49d1b0323f39faa0ffedb1e605f8ac96"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-28-mainline-a72-live-image-runtime-dt-control"
    / "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("current-Image/runtime-proven-DT control", "P30E entry-publication diagnostic candidate", 1),
    ("RAW_SIZE = 6_934_528", "RAW_SIZE = 6_955_008", 1),
    ("KERNEL_SIZE = 4_857_270", "KERNEL_SIZE = 4_878_149", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "967841597ace9128fded320c85d2c8f919bc11323ac092af0c631955910bd0ec", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "135703294fb2dfdecbf200b83e6dfb5d4e49241cbe64a27712d6e055772b35bc", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa", 1),
    ("a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1", "28b5e3eff190e5299da9594cd3ac5de8ad48b0787fc1c913195e74375a88c3e1", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-p30e-entry-diagnostic.boot.img", 1),
    ("b\"gemini-a72dtctl\"", "b\"gemini-a72prov\"", 1),
    (
        'require(provenance["repository_commit"] == "c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "commit changed")',
        'require(provenance["repository_commit"] == "23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51", "commit changed")',
        1,
    ),
    (
        'require(provenance["kernel_release"] == "7.1.3-gemini-a72-admission-live", "release changed")',
        'require(provenance["kernel_release"] == "7.1.3-gemini-a72-admission-live", "release changed")\n'
        '    config_text = config.decode("ascii")\n'
        '    require("CONFIG_ARM64_MT6797_A72_P30E_WIRE=y\\n" in config_text, "P30E production wire absent")\n'
        '    require("CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y\\n" in config_text, "live trigger absent")\n'
        '    require("# CONFIG_KUNIT is not set\\n" in config_text, "KUnit leaked into production Image")\n'
        '    map_text = system_map.decode("ascii")\n'
        '    for symbol in ("arm64_mt6797_a72_p30e_arm", "arm64_mt6797_a72_p30e_readback", "arm64_mt6797_a72_p30e_target_claim", "arm64_mt6797_a72_p30e_target_publish"):\n'
        '        require(any(line.endswith(f" {symbol}") for line in map_text.splitlines()), f"P30E symbol absent: {symbol}")',
        1,
    ),
    (
        'require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")\n'
        '    require(dtb.count(b"mediatek,mt6797-a72-platform-provider-clock-observer") == 1, "observer compatible changed")\n'
        '    require(b"mt6797-a72-admission-controller" not in dtb and b"mt6797-a72-admission-binder" not in dtb, "admission node leaked into DT")',
        'require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")\n'
        '    require(dtb.count(b"mediatek,mt6797-a72-admission-controller") == 1, "admission-controller compatible changed")\n'
        '    require(dtb.count(b"mediatek,mt6797-a72-binder") == 1, "binder compatible changed")\n'
        '    require(dtb.count(b"planet,gemini-a72-runtime-binding-v1") == 1, "runtime binding changed")\n'
        '    require(b"mediatek,mt6797-a72-platform-provider-clock-observer" not in dtb, "standalone observer leaked into DT")\n'
        '    binding = subprocess.run(["fdtget", "-tbx", str(args.control_dtb), "/chosen/gemini-late-cpu-provenance", "record-identity"], check=True, capture_output=True, text=True).stdout.strip()\n'
        '    require(binding == "96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55", "runtime binding identity changed")\n'
        '    for node_path in ("/usb@11271000", "/t-phy@11290000", "/t-phy@11290000/usb-phy@11290800", "/i2c@1101c000", "/i2c@1101c000/gpio-expander@5b", "/keyboard-matrix", "/dvfsp-clock-backend@1001a000", "/dvfsp-bigidvfs-backend"):\n'
        '        status = subprocess.run(["fdtget", "-ts", str(args.control_dtb), node_path, "status"], check=True, capture_output=True, text=True).stdout.strip()\n'
        '        require(status == "okay", f"serviceability/admission node disabled: {node_path}")',
        1,
    ),
    ("validation=a72-live-image-runtime-dt-control-independent", "validation=a72-p30e-entry-diagnostic-independent", 1),
    ("controller_nodes=0", "controller_nodes=1", 1),
    ("binder_nodes=0", "binder_nodes=1", 1),
    ('print("cpu8_requests=0")', 'print("candidate_cpu8_request_paths=1")\n    print("cpu8_requests=0")\n    print("cpu9_requests=0")\n    print("cpu_off_requests=0")\n    print("retries=0")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "a72_p30e_entry_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
