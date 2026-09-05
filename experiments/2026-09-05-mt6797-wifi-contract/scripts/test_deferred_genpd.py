#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile actual patched SCPSYS functions against bounded host-only spies.

Fetch only pinned public source files. Apply the proposal to its exact source,
extract functions without rewriting their logic, and run the C fixture with
generic PM enabled and disabled. No kernel tree, builder or device is used.
"""

import argparse
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/proposals/0001-pmdomain-mediatek-defer-initial-activation.patch"
PATCH_SHA256 = "e2338d566150a9e5a929b6a37e1bf76e356c4989391dd8549ed36b8e7554bc7f"
PIN = "4d7d9486c04d917265f64c55bd23b2cc4fe7749c"
SOURCE = "drivers/pmdomain/mediatek/mtk-scpsys.c"
SOURCE_SHA256 = "9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226"
CORE_SOURCE = "drivers/pmdomain/core.c"
CORE_SHA256 = "32e2f6b0988eba52a2f662fdc2d7132022fbe980f281b2a82babcf3d7f46e18a"
PATCHED_SHA256 = "216b022e433b2a55b255d30933e313e296415c624306dd6b0c4f76ac65a51f54"
CHECKPATCH_INPUTS = {
    "scripts/checkpatch.pl": "2553cc1a601e70522e03fbce633d4e79fa5936f7f56a66de1899b7ddd247820a",
    "scripts/spelling.txt": "4095d4a8810f115bae1b7c0d8a1946beb3435f6e22d9a48ac009bb024bad1e68",
    "scripts/const_structs.checkpatch": "ea064f6916a74763468037494aeb270aae34b7c97617e84d424ca5b8733539b2",
}
FUNCTIONS = (
    "scpsys_domain_is_on", "scpsys_check_initially_off",
    "scpsys_withhold_domain", "init_clks", "init_scp",
    "scpsys_register_domain", "mtk_register_power_domains",
    "scpsys_check_deferred_topology", "scpsys_probe",
)


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def fetch(path, digest):
    url = "https://raw.githubusercontent.com/torvalds/linux/" + PIN + "/" + path
    with urllib.request.urlopen(url, timeout=45) as response:
        raw = response.read()
    require(hashlib.sha256(raw).hexdigest() == digest, "public source digest mismatch: " + path)
    return raw


def command(argv, work, success=True, timeout=60):
    result = subprocess.run(argv, cwd=work, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=timeout)
    if success:
        require(result.returncode == 0, "command failed: " + " ".join(argv[:2])
                + "\n" + result.stdout)
    return result


@contextlib.contextmanager
def workspace(root):
    """Lock one owned scratch root; remove stale and final regenerable state."""
    root = root.absolute()
    require(not root.is_symlink(), "scratch root must not be a symlink")
    marker = root / ".deferred-genpd-owner"
    identity = "Regenerable deferred-genpd host fixture state, version 1\n"
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
        marker.write_text(identity)
    require(not marker.is_symlink() and marker.is_file()
            and marker.read_text() == identity, "unrecognized scratch root")
    info = root.stat()
    require(info.st_uid == os.getuid() and not info.st_mode & 0o077,
            "scratch root must be private and owned by this user")
    lock_path = root / ".lock"
    require(not lock_path.is_symlink(), "scratch lock must not be a symlink")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = root / "run"
        require(not work.is_symlink(), "scratch run must not be a symlink")
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(mode=0o700)
        try:
            yield work
        finally:
            shutil.rmtree(work)


def function(source, name):
    match = re.search(r"(?m)^static [^\n]*\b" + re.escape(name) + r"\(", source)
    require(match is not None, "missing actual function: " + name)
    end = source.find("\n}\n", match.start())
    require(end >= 0, "unterminated actual function: " + name)
    return source[match.start():end + 3]


def mutate(functions, name, old, new):
    changed = dict(functions)
    require(changed[name].count(old) == 1, "mutation anchor changed: " + name)
    changed[name] = changed[name].replace(old, new)
    return changed


def run_fixture(work, cc, functions, pm, sanitizers=False):
    (work / "scpsys-under-test.inc").write_text("\n".join(functions.values()))
    args = [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            "-Wno-unused-parameter", "-Wno-unused-function",
            "-DCONFIG_PM_GENERIC_DOMAINS=" + str(pm),
            "deferred_genpd_test.c", "-o", "fixture"]
    if sanitizers:
        args[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    command(args, work)
    return command(["./fixture"], work, success=False, timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="cc", help="host C compiler executable")
    parser.add_argument("--work-root", type=Path,
                        default=Path(tempfile.gettempdir()) / "gemini-deferred-genpd-validation")
    parser.add_argument("--checkpatch", action="store_true",
                        help="also run pinned checkpatch with the intentional missing DCO exempted")
    args = parser.parse_args()
    require(hashlib.sha256(PATCH.read_bytes()).hexdigest() == PATCH_SHA256,
            "proposal digest changed; review and update its pin")

    def interrupted(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with workspace(args.work_root) as work:
        source_path = work / SOURCE
        source_path.parent.mkdir(parents=True)
        source_path.write_bytes(fetch(SOURCE, SOURCE_SHA256))
        patch_path = work / "proposal.patch"
        patch_path.write_bytes(PATCH.read_bytes())
        command(["git", "apply", "--check", "--whitespace=error", "proposal.patch"], work)
        command(["git", "apply", "--whitespace=error", "proposal.patch"], work)
        patched = source_path.read_bytes()
        require(hashlib.sha256(patched).hexdigest() == PATCHED_SHA256,
                "patched source digest mismatch")
        functions = {name: function(patched.decode(), name) for name in FUNCTIONS}
        core = fetch(CORE_SOURCE, CORE_SHA256).decode()
        functions["genpd_xlate_onecell"] = function(core, "genpd_xlate_onecell")
        shutil.copyfile(EXPERIMENT / "src/deferred_genpd_test.c", work / "deferred_genpd_test.c")
        print("source_pin=" + PIN)
        print("patch_application=pass")
        print("actual_C_functions_compiled=" + str(len(functions)))
        print("compiler=" + command([args.cc, "--version"], work).stdout.splitlines()[0])
        for pm in (1, 0):
            result = run_fixture(work, args.cc, functions, pm)
            require(result.returncode == 0, "fixture failed\n" + result.stdout)
            print("generic_pm=" + str(pm) + " " + result.stdout.strip())
        result = run_fixture(work, args.cc, functions, 1, sanitizers=True)
        require(result.returncode == 0, "sanitizer fixture failed\n" + result.stdout)
        print("address_undefined_sanitizers=pass")

        mutations = (
            ("accept_on", "scpsys_check_initially_off", "return ret > 0 ? -EBUSY : ret;", "return ret < 0 ? ret : 0;", 1),
            ("accept_mixed", "scpsys_domain_is_on", "return -EINVAL;", "return 0;", 1),
            ("keep_refused_slot", "scpsys_withhold_domain", "scp->pd_data.domains[index] = NULL;", "(void)index;", 1),
            ("stop_after_refusal", "mtk_register_power_domains", "scpsys_withhold_domain(scp, i, ret);\n\t\t\tcontinue;", "scpsys_withhold_domain(scp, i, ret);\n\t\t\tbreak;", 1),
            ("omit_registration_recheck", "scpsys_register_domain", "ret = scpsys_check_initially_off(scpd);", "ret = 0;", 1),
            ("initial_power_callback", "scpsys_register_domain", "return pm_genpd_init(genpd, NULL, true);", "genpd->power_on(genpd);\n\t\treturn pm_genpd_init(genpd, NULL, true);", 1),
            ("ignore_genpd_init_error", "scpsys_register_domain", "return pm_genpd_init(genpd, NULL, true);", "pm_genpd_init(genpd, NULL, true);\n\t\treturn 0;", 1),
            ("global_regulator_refusal", "init_scp", "scpsys_withhold_domain(scp, i, PTR_ERR(scpd->supply));", "return ERR_CAST(scpd->supply);", 1),
            ("global_clock_refusal", "init_scp", "scpsys_withhold_domain(scp, i, PTR_ERR(c));", "return ERR_CAST(c);", 1),
            ("accept_zero_mask", "scpsys_check_initially_off", "if (!scpd->data->sta_mask)\n\t\treturn -EINVAL;", "/* guard omitted */", 1),
            ("accept_linked_domain", "scpsys_check_deferred_topology", "return -EINVAL;", "return 0;", 1),
            ("ignore_pm_availability", "scpsys_check_initially_off", "if (!IS_ENABLED(CONFIG_PM_GENERIC_DOMAINS))\n\t\treturn -EOPNOTSUPP;", "/* guard omitted */", 0),
        )
        for label, name, old, new, pm in mutations:
            result = run_fixture(work, args.cc, mutate(functions, name, old, new), pm)
            require(result.returncode != 0, "unsafe mutation escaped: " + label)
            require(result.returncode == 1 and result.stdout.startswith("FAIL "),
                    "mutation failed outside fixture assertions: " + label + "\n" + result.stdout)
        print("unsafe_mutations_rejected=" + str(len(mutations)))

        if args.checkpatch:
            for path, digest in CHECKPATCH_INPUTS.items():
                target = work / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(fetch(path, digest))
            result = command(["perl", "scripts/checkpatch.pl", "--no-tree",
                              "--no-signoff", "--show-types", "proposal.patch"], work)
            print(result.stdout.strip())
            print("checkpatch=pass_missing_DCO_exemption_only_not_submission_ready")
        print("kernel_build_and_hardware_validation=not_run")
    print("temporary_source_and_binaries=removed")


if __name__ == "__main__":
    main()
