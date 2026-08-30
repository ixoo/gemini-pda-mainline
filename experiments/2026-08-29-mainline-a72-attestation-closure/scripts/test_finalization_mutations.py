#!/usr/bin/env python3
"""Prove representative unsafe finalization mutations are rejected."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
FILES = (
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/cpufeature.c",
    "arch/arm64/kernel/proton-pack.c",
    "arch/arm64/kernel/mt6797_psci.c",
)


def replace(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor changed: {relative}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    mutations = (
        ("restore-attestation-blocker", "arch/arm64/kernel/mt6797_psci.c",
         "\t(ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)",
         "\t(ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |\n"
         "\t ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)"),
        ("block-production-prepare", "arch/arm64/kernel/mt6797_psci.c",
         "#else\n\treturn 0;\n#endif", "#else\n\treturn -EAGAIN;\n#endif"),
        ("drop-system-callback", "arch/arm64/kernel/mt6797_psci.c",
         "\t.verify_system = mt6797_a72_verify_system,\n", ""),
        ("drop-user-callback", "arch/arm64/kernel/mt6797_psci.c",
         "\t.finalize_user = mt6797_a72_finalize_user,\n", ""),
        ("skip-finalized-system-gate", "arch/arm64/kernel/cpufeature.c",
         "!plan || !receipt || !system_capabilities_finalized() ||",
         "!plan || !receipt ||"),
        ("omit-required-capabilities", "arch/arm64/kernel/cpufeature.c",
         "bitmap_or(expected_caps, plan->early_local_caps,\n"
         "\t\t  plan->required_local_caps, ARM64_NCAPS);",
         "bitmap_copy(expected_caps, plan->early_local_caps, ARM64_NCAPS);"),
        ("accept-uncompiled-live-caps", "arch/arm64/kernel/cpufeature.c",
         "bitmap_and(live_caps, system_cpucaps, plan->compiled_local_caps,\n"
         "\t\t   ARM64_NCAPS);",
         "bitmap_copy(live_caps, system_cpucaps, ARM64_NCAPS);"),
        ("drop-alternative-proof", "arch/arm64/kernel/cpufeature.c",
         "\tfor_each_set_bit(cap, plan->compiled_local_caps, ARM64_NCAPS)\n"
         "\t\tif (alternative_is_applied(cap) !=\n"
         "\t\t    test_bit(cap, expected_caps))\n"
         "\t\t\treturn -EINVAL;\n", ""),
        ("invert-alternative-proof", "arch/arm64/kernel/cpufeature.c",
         "alternative_is_applied(cap) !=", "alternative_is_applied(cap) =="),
        ("drop-v2-exactness", "arch/arm64/kernel/proton-pack.c",
         "ret || READ_ONCE(spectre_v2_state) != v2", "ret"),
        ("drop-bhb-method-exactness", "arch/arm64/kernel/proton-pack.c",
         "\t\t    READ_ONCE(system_bhb_mitigations) !=\n"
         "\t\t\t    effects->bhb.system_method ||\n", ""),
        ("drop-native-subset-gate", "arch/arm64/kernel/cpufeature.c",
         "\tif (!bitmap_subset(expected, elf_hwcap, MAX_CPU_FEATURES))\n"
         "\t\treturn -EINVAL;\n", ""),
        ("expand-native-hwcap", "arch/arm64/kernel/cpufeature.c",
         "bitmap_copy(elf_hwcap, expected, MAX_CPU_FEATURES);",
         "bitmap_or(elf_hwcap, elf_hwcap, expected, MAX_CPU_FEATURES);"),
        ("drop-compat-subset-gate", "arch/arm64/kernel/cpufeature.c",
         "plan->expected_compat_hwcap & ~compat_elf_hwcap ||",
         "plan->expected_compat_hwcap != compat_elf_hwcap ||"),
        ("drop-compat-postwrite-proof", "arch/arm64/kernel/cpufeature.c",
         "\tif (compat_elf_hwcap != plan->expected_compat_hwcap ||\n"
         "\t    compat_elf_hwcap2 != plan->expected_compat_hwcap2 ||\n"
         "\t    compat_elf_hwcap3)\n"
         "\t\tpanic(\"late CPU compat HWCAP finalization changed outside its plan\");\n",
         ""),
        ("publish-receipt-in-helper", "arch/arm64/kernel/cpufeature.c",
         "\treturn 0;\n}\n#endif\n\nstatic void cap_set_elf_hwcap",
         "\treceipt->user_hwcaps_finalized = 1;\n\treturn 0;\n}\n#endif\n\n"
         "static void cap_set_elf_hwcap"),
        ("add-cpu-request", "arch/arm64/kernel/mt6797_psci.c",
         "\treturn arm64_verify_late_cpu_system(plan, receipt);",
         "\tcpu_up(8);\n\treturn arm64_verify_late_cpu_system(plan, receipt);"),
    )

    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="a72-finalization-mutation-") as tmp:
            root = Path(tmp)
            for item in FILES:
                destination = root / item
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / item, destination)
            replace(root, relative, old, new)
            result = subprocess.run(
                (sys.executable, str(SCRIPT_DIR / "validate_finalization_source.py"),
                 "--source-root", str(root)),
                check=False, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                print(f"accepted_mutation={name}")
                return 1
            rejected += 1

    print(f"rejected_mutations={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
