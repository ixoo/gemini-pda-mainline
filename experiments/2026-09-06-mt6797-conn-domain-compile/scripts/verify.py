#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Verify the inert, typed MT6797 CONN domain-data compile artifact."""

import ast
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.request


HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
SPEC = json.loads((HERE / "inputs.json").read_text())


class VerifyInterrupted(Exception):
    """Raised so context managers can remove temporary verification state."""


def handle_sigterm(signum, frame):
    del signum, frame
    raise VerifyInterrupted


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def fetch(path, expected):
    url = "https://raw.githubusercontent.com/torvalds/linux/" + \
        SPEC["linux_commit"] + "/" + path
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read()
    require(digest(data) == expected, "public source digest changed: " + path)
    return data


@contextlib.contextmanager
def scratch():
    # Keep the temporary checkout outside this repository so git-apply cannot
    # discover the worktree's .git directory and redirect the patch.
    managed = Path(tempfile.gettempdir()) / "gemini-conn-domain-compile"
    require(not managed.is_symlink(), "managed scratch root is a symlink")
    managed.mkdir(parents=True, exist_ok=True)
    lock_path = managed / ".verify.lock"
    require(not lock_path.is_symlink(), "scratch lock is a symlink")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for stale in managed.glob("verify-*"):
            require(stale.is_dir() and not stale.is_symlink(),
                    "unexpected stale scratch entry")
            marker = stale / ".owner"
            require(marker.is_file() and not marker.is_symlink() and
                    marker.read_text() == "conn-domain-compile-v1\n",
                    "unowned stale scratch entry")
            require(all(not path.is_symlink() for path in stale.rglob("*")),
                    "symlink in stale scratch entry")
            shutil.rmtree(stale)
        with tempfile.TemporaryDirectory(prefix="verify-", dir=managed) as name:
            path = Path(name)
            (path / ".owner").write_text("conn-domain-compile-v1\n")
            yield path


def compile_fixture(work, actual_types, source_path, output_name):
    object_file = work / (output_name + ".o")
    binary = work / output_name
    flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Wconversion",
             "-Wsign-conversion", "-pedantic", "-O2", "-g",
             "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
             "-fno-omit-frame-pointer", "-include", str(actual_types),
             "-I", str(HERE / "src")]
    subprocess.run(["cc", *flags, "-c", str(source_path), "-o",
                    str(object_file)], check=True, timeout=60)
    subprocess.run(["cc", *flags, str(object_file),
                    str(HERE / "src" / "conn-domain-test.c"), "-o",
                    str(binary)], check=True, timeout=60)
    return binary, flags


def block(text, start):
    begin = text.index(start)
    end = text.index("\n};", begin) + 3
    return text[begin:end]


def provider_snapshot(text):
    callbacks = "\n".join(line.strip() for line in text.splitlines()
                             if re.search(r"genpd->power_(off|on)\s*=", line))
    match = re.search(
        r'\{\s*\.compatible = "mediatek,mt6797-scpsys",\s*'
        r'\.data = &mt6797_data,\s*\}', text, re.S)
    require(match is not None, "MT6797 match entry missing")
    return {
        "domain_table": block(
            text, "static const struct scp_domain_data scp_domain_data_mt6797[]"),
        "soc_data": block(text, "static const struct scp_soc_data mt6797_data"),
        "subdomains": block(
            text, "static const struct scp_subdomain scp_subdomain_mt6797[]"),
        "match": match.group(0),
        "callbacks": callbacks,
    }


def binding_ids(text):
    pairs = re.findall(
        r"^#define\s+(MT6797_POWER_DOMAIN_[A-Z0-9_]+)\s+(\d+)\s*$",
        text, re.M)
    return {name: int(value) for name, value in pairs}


def verify_provider(original, patched, binding):
    before = provider_snapshot(original)
    after = provider_snapshot(patched)
    for key in before:
        require(before[key] == after[key],
                "provider snapshot changed: " + key)
    require(after["callbacks"].count("genpd->power_off") == 1 and
            after["callbacks"].count("genpd->power_on") == 1,
            "existing callback wiring changed")
    require(".num_domains = ARRAY_SIZE(scp_domain_data_mt6797)" in
            after["soc_data"], "registered domain count changed")
    ids = binding_ids(binding)
    require(sorted(ids.values()) == list(range(12)),
            "existing binding IDs are not exactly 0..11")
    require(ids["MT6797_POWER_DOMAIN_MJC"] == 11,
            "last existing binding ID changed")
    table = after["domain_table"]
    for name in ("vdec", "venc", "isp", "mm", "audio", "mfg_async", "mjc"):
        require('.name = "' + name + '"' in table,
                "existing domain data missing: " + name)
    require("scp_domain_data_mt6797" in after["soc_data"] and
            "scp_subdomain_mt6797" in after["soc_data"] and
            "&mt6797_data" in after["match"],
            "existing registration references changed")
    return before


def extract_types(provider):
    enum_match = re.search(r"(?ms)^enum clk_id \{.*?^};", provider)
    struct_match = re.search(r"(?ms)^struct scp_domain_data \{.*?^};", provider)
    require(enum_match is not None and struct_match is not None,
            "actual provider type definitions missing")
    return """#include <stdint.h>
typedef uint8_t u8;
typedef uint32_t u32;
#define BIT(_n) (1U << (_n))
#define MAX_CLKS 3
%s
%s
""" % (enum_match.group(0), struct_match.group(0))


def check_candidate_text(text):
    forbidden = (
        "scp_domain_data_mt6797", "mt6797_data", "scp_subdomain_mt6797",
        "of_scpsys_match_tbl", "MT6797_POWER_DOMAIN_CONN", "pm_genpd",
        "power_on", "power_off", "platform_driver", "module_init",
        "EXPORT_SYMBOL", "of_genpd", "subdomain",
    )
    for token in forbidden:
        require(token not in text, "candidate reaches forbidden path: " + token)
    require(text.count(".id = 12") == 1, "local proposed ID changed")
    require(text.count('static const struct scp_domain_data') == 1,
            "typed descriptor is not exactly one local object")


def expect_refusal(label, callback):
    try:
        callback()
    except (AssertionError, RuntimeError, ValueError):
        return label
    raise RuntimeError("unsafe mutation escaped: " + label)


def run_deferred_runner(work):
    runner = ROOT / SPEC["deferred_runner"]
    fixture = ROOT / SPEC["deferred_fixture"]
    require(digest(runner.read_bytes()) == SPEC["deferred_runner_sha256"],
            "deferred runner changed")
    require(digest(fixture.read_bytes()) == SPEC["deferred_fixture_sha256"],
            "deferred fixture changed")
    deferred_root = work / "deferred-runner"
    result = subprocess.run(
        ["python3", "-B", str(runner), "--work-root", str(deferred_root)],
        cwd=ROOT, capture_output=True, text=True, timeout=240, check=False)
    require(result.returncode == 0,
            "deferred registration runner failed\n" + result.stdout + result.stderr)
    require("generic_pm=1" in result.stdout and "generic_pm=0" in result.stdout,
            "deferred runner missed PM enabled/disabled paths")
    require("unsafe_mutations_rejected=12" in result.stdout,
            "deferred runner mutation coverage changed")
    return [line for line in result.stdout.splitlines()
            if line.startswith(("source_pin=", "patch_application=",
                                "actual_C_functions_compiled=", "generic_pm=",
                                "address_undefined_sanitizers=",
                                "unsafe_mutations_rejected="))]


def run_interrupt_worker():
    signal.signal(signal.SIGTERM, handle_sigterm)
    with scratch() as work:
        (work / "worker-started").write_text("interruption test\n")
        os.kill(os.getpid(), signal.SIGTERM)


def run_interruption_self_test():
    managed = Path(tempfile.gettempdir()) / "gemini-conn-domain-compile"
    result = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()),
         "--interrupt-worker"],
        cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    remaining = sorted(managed.glob("verify-*")) if managed.exists() else []
    require(result.returncode == 143,
            "interruption worker did not unwind with status 143\n" +
            result.stdout + result.stderr)
    require(not remaining,
            "interruption left verify-* temporary state: " +
            ", ".join(str(path) for path in remaining))
    return {
        "label": "handled_sigterm_cleanup",
        "worker_exit": result.returncode,
        "verify_temp_dirs_remaining": len(remaining),
        "result": "PASS",
    }


def main():
    require(digest((ROOT / SPEC["deferred_registration_patch"]).read_bytes()) ==
            SPEC["deferred_registration_patch_sha256"],
            "deferred registration proposal changed")
    for path, expected in SPEC["evidence_documents"].items():
        require(digest((ROOT / path).read_bytes()) == expected,
                "evidence document changed: " + path)

    candidate = ((HERE / "src" / "conn-domain.c").read_text() +
                 (HERE / "src" / "conn-domain.h").read_text())
    check_candidate_text(candidate)
    provider = fetch(SPEC["provider_path"], SPEC["provider_sha256"])
    binding = fetch(SPEC["binding_path"], SPEC["binding_sha256"])
    proposal = (ROOT / SPEC["deferred_registration_patch"]).read_bytes()

    report = {
        "state": "review-ready",
        "parent": SPEC["parent"],
        "linux_commit": SPEC["linux_commit"],
        "kernel_patch": "NOT APPLICABLE; Astra rejected kernel patch/public binding changes",
        "checkpatch": "NOT APPLICABLE; no kernel patch is generated",
        "buildbox": "NOT APPLICABLE; no provider/profile integration is authorized",
        "hardware": "NOT ACCESSED",
        "backend": "NOT ACCESSED",
        "runtime_caller": "NONE; descriptor is unreachable from provider data",
    }
    with scratch() as work:
        source_path = work / SPEC["provider_path"]
        source_path.parent.mkdir(parents=True)
        source_path.write_bytes(provider)
        patch_path = work / "deferred-registration.patch"
        patch_path.write_bytes(proposal)
        subprocess.run(["git", "apply", "--check", "--whitespace=error",
                        patch_path.name], cwd=work, check=True, timeout=30)
        subprocess.run(["git", "apply", "--whitespace=error", patch_path.name],
                       cwd=work, check=True, timeout=30)
        patched = source_path.read_bytes()
        require(digest(patched) == SPEC["provider_patched_sha256"],
                "patched provider digest changed")
        require("mt6797_conn_domain_experiment" not in patched.decode(),
                "local descriptor reached the provider source")
        snapshot = verify_provider(provider.decode(), patched.decode(),
                                   binding.decode())
        report["provider_source_sha256"] = digest(provider)
        report["provider_patched_sha256"] = digest(patched)
        report["binding_sha256"] = digest(binding)
        report["provider_snapshot"] = {
            "domain_data": digest(snapshot["domain_table"].encode()),
            "soc_data": digest(snapshot["soc_data"].encode()),
            "subdomains": digest(snapshot["subdomains"].encode()),
            "match_and_callbacks": digest((snapshot["match"] +
                                             snapshot["callbacks"]).encode()),
            "existing_ids": 12,
            "registered_count": 12,
        }

        actual_types = work / "actual-provider-types.h"
        actual_types.write_text(extract_types(patched.decode()))
        binary, flags = compile_fixture(
            work, actual_types, HERE / "src" / "conn-domain.c", "conn-domain-test")
        env = dict(os.environ, ASAN_OPTIONS="halt_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1")
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                env=env, timeout=60, check=False)
        require(result.returncode == 0 and not result.stderr,
                result.stdout + result.stderr)
        report["host_test"] = result.stdout.strip()
        report["compiler"] = subprocess.check_output(
            ["cc", "--version"], text=True).splitlines()[0]
        report["sanitizer_flags"] = [
            item.replace(str(ROOT), "<project>").replace(str(work),
                                                            "<managed-temp>")
            for item in flags
        ]

        mutations = []
        unsafe_third_slot = work / "unsafe-third-slot.c"
        unsafe_third_slot.write_text(
            (HERE / "src" / "conn-domain.c").read_text().replace(
                ".clk_id = {CLK_NONE},",
                ".clk_id = {CLK_NONE, CLK_NONE, CLK_MM},", 1))
        unsafe_binary, _ = compile_fixture(
            work, actual_types, unsafe_third_slot, "unsafe-third-slot-test")
        unsafe_result = subprocess.run([str(unsafe_binary)], capture_output=True,
                                       text=True, env=env, timeout=60,
                                       check=False)
        require(unsafe_result.returncode != 0 and
                "FAIL:" in unsafe_result.stderr,
                "third CLK slot mutation escaped the field fixture")
        mutations.append("third_slot_clk_id")
        mutations.append(expect_refusal(
            "wire_descriptor_into_mt6797_data",
            lambda: check_candidate_text(candidate +
                "\nstatic const struct scp_domain_data "
                "scp_domain_data_mt6797[] = { };\n")))
        mutations.append(expect_refusal(
            "increase_registered_count",
            lambda: verify_provider(provider.decode(), patched.decode().replace(
                ".num_domains = ARRAY_SIZE(scp_domain_data_mt6797)",
                ".num_domains = ARRAY_SIZE(scp_domain_data_mt6797) + 1"),
                binding.decode())))
        mutations.append(expect_refusal(
            "add_public_consumer_id",
            lambda: check_candidate_text(candidate +
                "\n#define MT6797_POWER_DOMAIN_CONN 12\n")))
        mutations.append(expect_refusal(
            "change_existing_binding_id",
            lambda: verify_provider(provider.decode(), patched.decode(),
                binding.decode().replace(
                    "MT6797_POWER_DOMAIN_MJC\t\t11",
                    "MT6797_POWER_DOMAIN_MJC\t\t12"))))
        report["unsafe_mutations_rejected"] = mutations
        report["mutation_results"] = {
            "third_slot_clk_id": "fixture_rejected",
            "wire_descriptor_into_mt6797_data": "verifier_rejected",
            "increase_registered_count": "verifier_rejected",
            "add_public_consumer_id": "verifier_rejected",
            "change_existing_binding_id": "verifier_rejected",
        }
        report["deferred_registration_reuse"] = run_deferred_runner(work)

    report["interruption_cleanup"] = run_interruption_self_test()
    report["source_hashes"] = {
        path.name: digest(path.read_bytes())
        for path in sorted((HERE / "src").iterdir())
    }
    report["evidence_documents"] = SPEC["evidence_documents"]
    report["limitations"] = [
        "The descriptor is compiled against extracted actual provider types; no kernel tree is retained.",
        "The local proposed ID is not added to the public binding or registered provider data.",
        "Compile and deferred fixtures do not establish CONN ownership, sequencing, recovery or hardware behavior.",
        "No Buildbox build, device action or runtime Wi-Fi claim is made.",
    ]
    (HERE / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        if sys.argv[1:] == ["--interrupt-worker"]:
            run_interrupt_worker()
        elif sys.argv[1:]:
            raise SystemExit("unexpected arguments")
        else:
            main()
    except VerifyInterrupted:
        print("verify_interrupted=handled")
        raise SystemExit(143)
