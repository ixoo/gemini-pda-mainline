#!/usr/bin/env python3
"""No-device tests for Candidate AN's exact-MAC one-shot watcher."""

from __future__ import annotations

import difflib
import importlib.util
import os
import pathlib
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest


sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
FOUNDATION = (
    REPOSITORY
    / "experiments/2026-07-22-ad-contract-af-kernel-split/scripts/collect-cycle.sh"
)
DERIVER = SCRIPT_DIR / "derive-cycle-watcher.py"
WRAPPER = SCRIPT_DIR / "collect-cycle.sh"
COLLECTOR = SCRIPT_DIR / "collect-runtime.sh"


def load_deriver():
    sys.path.insert(0, os.fspath(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "candidate_an_cycle_watcher_test", DERIVER
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load Candidate AN cycle-watcher deriver")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(os.fspath(SCRIPT_DIR))


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"fixture token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def independently_expected(
    source: str,
    padded_sha256: str,
    repository: pathlib.Path,
    collector: pathlib.Path,
) -> str:
    old_location = '''script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-runtime.sh"
readonly script_dir repo_root collector'''
    new_location = (
        f"repo_root={shlex.quote(os.fspath(repository))}\n"
        f"collector={shlex.quote(os.fspath(collector))}\n"
        "readonly repo_root collector"
    )
    old_wait = (
        '[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || '
        "die '--wait-seconds must be positive'"
    )
    new_wait = (
        '[[ "$wait_seconds" =~ ^[1-9][0-9]*$ && '
        '"$wait_seconds" -le 900 ]] || \\\n'
        "\tdie '--wait-seconds must be in 1..900'"
    )
    replacements = (
        (
            "readonly EXPECTED_INSTALLED_FULL_SHA256="
            "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012",
            f"readonly EXPECTED_INSTALLED_FULL_SHA256={padded_sha256}",
            1,
        ),
        (old_location, new_location, 1),
        ("Candidate AH", "Candidate AN", 2),
        (
            "2026-07-22-ad-contract-af-kernel-split",
            "2026-07-24-mt6797-dvfsp-handoff-observer",
            1,
        ),
        ("candidate_label=AH", "candidate_label=AN", 1),
        (
            "exact-ah-runtime-validator-passed",
            "exact-an-runtime-validator-passed",
            1,
        ),
        (old_wait, new_wait, 1),
    )
    result = source
    for old, new, count in replacements:
        result = replace_exact(result, old, new, count)
    return result


def write_executable(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o700)


class CycleWatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.deriver = load_deriver()
        cls.workspace = tempfile.TemporaryDirectory(
            prefix="candidate-an-cycle-watcher-test."
        )
        cls.work = pathlib.Path(cls.workspace.name)
        cls.source = cls.deriver.load_foundation(FOUNDATION)
        cls.repository = REPOSITORY.resolve(strict=True)
        cls.collector = COLLECTOR.resolve(strict=True)
        cls.derived = cls.deriver.derive(
            cls.source, cls.repository, cls.collector
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.workspace.cleanup()

    def test_source_pinned_reversible_identity_and_paths(self) -> None:
        self.deriver.an.require_artifact_pins()
        self.assertEqual(
            self.deriver.digest_bytes(FOUNDATION.read_bytes()),
            self.deriver.AH_WATCHER_SHA256,
        )
        expected = independently_expected(
            self.source,
            self.deriver.an.PADDED_SHA256,
            self.repository,
            self.collector,
        )
        if self.derived != expected:
            delta = "".join(
                difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    self.derived.splitlines(keepends=True),
                    fromfile="permitted-transform",
                    tofile="actual-transform",
                )
            )
            self.fail(f"watcher has a non-permitted foundation delta:\n{delta}")

        self.assertIn(
            "readonly EXPECTED_INSTALLED_FULL_SHA256="
            f"{self.deriver.an.PADDED_SHA256}",
            self.derived,
        )
        self.assertIn(
            f"repo_root={shlex.quote(os.fspath(self.repository))}", self.derived
        )
        self.assertIn(
            f"collector={shlex.quote(os.fspath(self.collector))}", self.derived
        )
        self.assertIn(f"readonly HOST_MAC={self.deriver.HOST_MAC}", self.derived)
        self.assertIn(f"experiment={self.deriver.an.EXPERIMENT}", self.derived)
        self.assertIn("candidate_label=AN", self.derived)
        self.assertNotIn("Candidate AH", self.derived)

        mutated = self.work / "mutated-ah-watcher.sh"
        mutated.write_text(self.source + "\n# mutation\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source-pinned"):
            self.deriver.load_foundation(mutated)

    def test_static_one_shot_bounded_and_no_device_controls(self) -> None:
        generated = self.work / "generated-an-cycle-watcher.sh"
        self.deriver.publish(generated, self.derived)
        self.assertEqual(stat.S_IMODE(generated.stat().st_mode), 0o700)
        syntax = subprocess.run(
            ["bash", "-n", os.fspath(generated)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

        invocation = '"$collector" --interface "$interface" --output "$capture"'
        self.assertEqual(self.derived.count(invocation), 1)
        self.assertEqual(self.derived.count("collector_invocations=1\n"), 1)
        self.assertIn("wait_seconds=600", self.derived)
        self.assertIn('"$wait_seconds" -le 900', self.derived)
        self.assertIn("-c 1 -W 1000", self.derived)
        runtime_source = COLLECTOR.read_text(encoding="utf-8")
        self.assertIn("nc -4 -b", runtime_source)
        self.assertIn("-G 5 -w 90", runtime_source)
        self.assertIn(
            "readonly EXPECTED_INSTALLED_FULL_SHA256="
            f"{self.deriver.an.PADDED_SHA256}",
            runtime_source,
        )

        forbidden_fragments = (
            "/dev/mmc",
            "/dev/i2c",
            "/sys/class/regulator",
            "/sys/devices/system/cpu/online",
            "echo 1 >",
            "echo 0 >",
            "tee /sys/",
            "blockdev",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, self.derived)

        dangerous = re.compile(
            r"^\s*(?:(?:sudo|doas)\s+(?:-\S+\s+)*)?"
            r"(?:/[A-Za-z0-9_.-]+/)*(?:dd|reboot|shutdown|poweroff|halt|"
            r"kexec|bootctl|fastboot|i2cget|i2cset|cpupower)(?:\s|$)"
        )
        self.assertEqual(
            [
                line
                for line in self.derived.splitlines()
                if dangerous.match(line) is not None
            ],
            [],
        )
        sudo_lines = [
            line.strip()
            for line in self.derived.splitlines()
            if line.lstrip().startswith("sudo ")
        ]
        self.assertEqual(len(sudo_lines), 2)
        self.assertTrue(all(line.startswith("sudo -n ifconfig ") for line in sudo_lines))

        existing = self.work / "existing-derived-watcher.sh"
        existing.write_text("preserve\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.deriver.validate_output(existing)
        with self.assertRaises(FileExistsError):
            self.deriver.publish(existing, self.derived)
        self.assertEqual(existing.read_text(encoding="utf-8"), "preserve\n")

    def make_runtime_fixture(
        self, name: str
    ) -> tuple[pathlib.Path, pathlib.Path, dict[str, str], pathlib.Path]:
        root = self.work / name
        root.mkdir()
        root = root.resolve(strict=True)
        subprocess.run(
            ["git", "init", "-q", os.fspath(root)],
            check=True,
            capture_output=True,
        )
        (root / ".gitignore").write_text("/artifacts/\n", encoding="utf-8")
        (root / "artifacts").mkdir(mode=0o700)
        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        collector = root / "collect-runtime.sh"
        collector_log = root / "collector.log"
        interface_state = root / "ifconfig.state"

        write_executable(
            collector,
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                interface=
                output=
                installed=
                while (($#)); do
                    case "$1" in
                    --interface) interface=$2; shift 2 ;;
                    --output) output=$2; shift 2 ;;
                    --installed-full-sha256) installed=$2; shift 2 ;;
                    *) exit 91 ;;
                    esac
                done
                printf 'interface=%s installed=%s\\n' "$interface" "$installed" \
                    >>"$FAKE_COLLECTOR_LOG"
                printf 'synthetic-runtime-capture\\n' >"$output"
                exit "${FAKE_COLLECTOR_RC:-0}"
                """
            ),
        )
        write_executable(
            fake_bin / "ifconfig",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                case "${1:-}" in
                -a)
                    printf 'lo0: flags=8049<UP,LOOPBACK,RUNNING>\\n'
                    printf 'en9: flags=8863<UP,BROADCAST,RUNNING>\\n'
                    ;;
                -l)
                    count=0
                    if [[ -f "$FAKE_IFCONFIG_STATE" ]]; then
                        read -r count <"$FAKE_IFCONFIG_STATE"
                    fi
                    count=$((count + 1))
                    printf '%s\\n' "$count" >"$FAKE_IFCONFIG_STATE"
                    if ((count == 1)); then
                        printf 'lo0\\n'
                    else
                        printf 'lo0 en9\\n'
                    fi
                    ;;
                lo0)
                    printf 'lo0: flags=8049<UP,LOOPBACK,RUNNING>\\n'
                    printf '\\tinet 127.0.0.1 netmask 0xff000000\\n'
                    ;;
                en9)
                    printf 'en9: flags=8863<UP,BROADCAST,RUNNING>\\n'
                    printf '\\tether 42:00:15:19:82:00\\n'
                    printf '\\tinet 10.15.19.1 netmask 0xffffff00\\n'
                    ;;
                *)
                    exit 92
                    ;;
                esac
                """
            ),
        )
        write_executable(
            fake_bin / "ioreg",
            "#!/usr/bin/env bash\nprintf 'GEMINI_OBSERVABILITY_20260717_L\\n'\n",
        )
        write_executable(
            fake_bin / "route",
            "#!/usr/bin/env bash\nprintf 'interface: en9\\n'\n",
        )
        write_executable(fake_bin / "ping", "#!/usr/bin/env bash\nexit 0\n")
        write_executable(fake_bin / "sleep", "#!/usr/bin/env bash\nexit 0\n")
        write_executable(
            fake_bin / "sudo",
            "#!/usr/bin/env bash\nprintf 'unexpected sudo\\n' >&2\nexit 93\n",
        )

        watcher_text = self.deriver.derive(self.source, root, collector)
        watcher = root / "watcher.sh"
        self.deriver.publish(watcher, watcher_text)
        environment = {
            **os.environ,
            "PATH": os.fspath(fake_bin) + os.pathsep + os.environ["PATH"],
            "FAKE_COLLECTOR_LOG": os.fspath(collector_log),
            "FAKE_IFCONFIG_STATE": os.fspath(interface_state),
        }
        return root, watcher, environment, collector_log

    def invoke_fixture(
        self,
        root: pathlib.Path,
        watcher: pathlib.Path,
        environment: dict[str, str],
        output_name: str,
        *,
        collector_rc: int = 0,
        wait_seconds: int = 5,
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
        output = root / "artifacts/runtime-captures" / output_name
        run_environment = {
            **environment,
            "FAKE_COLLECTOR_RC": str(collector_rc),
        }
        result = subprocess.run(
            [
                os.fspath(watcher),
                "--output",
                os.fspath(output),
                "--installed-full-sha256",
                self.deriver.an.PADDED_SHA256,
                "--wait-seconds",
                str(wait_seconds),
            ],
            cwd=root,
            env=run_environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result, output

    def test_exact_mac_transition_and_single_successful_invocation(self) -> None:
        root, watcher, environment, collector_log = self.make_runtime_fixture(
            "exact-mac-success"
        )
        result, output = self.invoke_fixture(
            root, watcher, environment, "one-shot-success"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = collector_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            invocations,
            [
                "interface=en9 installed="
                f"{self.deriver.an.PADDED_SHA256}"
            ],
        )
        events = (output / "events.txt").read_text(encoding="utf-8")
        self.assertIn("exact_mac_interface=absent", events)
        self.assertIn(
            "interface=en9 mac=42:00:15:19:82:00 "
            "route_interface=en9 ping=passed",
            events,
        )
        status = (output / "status.env").read_text(encoding="utf-8")
        self.assertIn(f"experiment={self.deriver.an.EXPERIMENT}\n", status)
        self.assertIn("candidate_label=AN\n", status)
        self.assertIn("result=passed\n", status)
        self.assertIn("collector_invocations=1\n", status)
        self.assertIn("interface=en9\nmac=42:00:15:19:82:00\n", status)

    def test_failure_is_not_retried_and_existing_output_is_refused(self) -> None:
        root, watcher, environment, collector_log = self.make_runtime_fixture(
            "one-shot-failure"
        )
        result, output = self.invoke_fixture(
            root,
            watcher,
            environment,
            "collector-failure",
            collector_rc=7,
        )
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(
            len(collector_log.read_text(encoding="utf-8").splitlines()), 1
        )
        status = (output / "status.env").read_text(encoding="utf-8")
        self.assertIn("result=failed\n", status)
        self.assertIn("collector_invocations=1\n", status)
        self.assertIn("collector_rc=7\n", status)

        existing = root / "artifacts/runtime-captures/existing"
        existing.mkdir()
        before = collector_log.read_text(encoding="utf-8")
        refused, _ = self.invoke_fixture(
            root, watcher, environment, "existing"
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn("refusing to overwrite runtime evidence", refused.stderr)
        self.assertEqual(collector_log.read_text(encoding="utf-8"), before)

    def test_wait_timeout_is_strictly_bounded(self) -> None:
        root, watcher, environment, collector_log = self.make_runtime_fixture(
            "bounded-timeout"
        )
        result, output = self.invoke_fixture(
            root,
            watcher,
            environment,
            "too-long",
            wait_seconds=self.deriver.MAX_WAIT_SECONDS + 1,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("wait-seconds must be in 1..900", result.stderr)
        self.assertFalse(output.exists())
        self.assertFalse(collector_log.exists())

    def test_wrapper_paths_and_no_direct_device_action(self) -> None:
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertIn(self.deriver.AH_WATCHER_SHA256, wrapper)
        self.assertIn(
            "experiments/2026-07-22-ad-contract-af-kernel-split/"
            "scripts/collect-cycle.sh",
            wrapper,
        )
        self.assertIn('deriver="$script_dir/derive-cycle-watcher.py"', wrapper)
        self.assertIn('collector="$script_dir/collect-runtime.sh"', wrapper)
        self.assertIn('identity="$script_dir/candidate_an.py"', wrapper)
        self.assertIn('bash -n "$temporary"', wrapper)
        self.assertIn('"$temporary" "$@"', wrapper)
        self.assertNotIn("ssh ", wrapper)
        self.assertNotIn(" nc ", wrapper)
        self.assertNotIn("/dev/mmc", wrapper)
        self.assertNotRegex(
            wrapper,
            re.compile(
                r"^\s*(?:reboot|shutdown|poweroff|dd|i2cset|cpupower)(?:\s|$)",
                re.MULTILINE,
            ),
        )
        syntax = subprocess.run(
            ["bash", "-n", os.fspath(WRAPPER)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)


if __name__ == "__main__":
    unittest.main()
