#!/usr/bin/env python3
"""Static and mutation tests for Curie assembly, runtime, and installer tools."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import pathlib
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
import candidate_curie as co


def load(name: str):
    path = SCRIPT_DIR / name
    spec = importlib.util.spec_from_file_location(
        "curie_test_" + name.replace("-", "_").replace(".", "_"),
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dc = load("derive-candidate.py")
vc = load("verify-curie-reproducibility.py")
rc = load("run-curie-one-shot.py")
di = load("derive-installer.py")


def synthetic_record() -> dict[str, str]:
    raw = "1" * 64
    fields = {key: "unused" for key in di.REPRODUCIBILITY_KEYS}
    fields.update(
        {
            "validation": "curie-two-build-2x2-reproducibility",
            "experiment": co.EXPERIMENT,
            "verifier_sha256": di.REPRODUCIBILITY_VERIFIER_SHA256,
            "candidate_module_sha256": di.CANDIDATE_MODULE_SHA256,
            "package_validator_sha256": di.PACKAGE_VALIDATOR_SHA256,
            "lk_analyzer_sha256": co.ANALYZER_SHA256,
            "package_lane_count": "2",
            "candidate_lane_count": "4",
            "matrix": (
                "package-a/cassini-a,package-a/cassini-b,"
                "package-b/cassini-a,package-b/cassini-b"
            ),
            "package_directory_name": "linux-7.1.3-gemini-curie-synthetic",
            "package_a_manifest_sha256": "2" * 64,
            "package_b_manifest_sha256": "3" * 64,
            "package_a_generated_utc": "2026-07-28T18:00:00Z",
            "package_b_generated_utc": "2026-07-28T18:01:00Z",
            "package_normalized_file_count": "248",
            "package_normalized_inventory_sha256": "4" * 64,
            "package_a_normalized_inventory_sha256": "4" * 64,
            "package_b_normalized_inventory_sha256": "4" * 64,
            "package_normalized_build_sha256": "5" * 64,
            "package_a_normalized_build_sha256": "5" * 64,
            "package_b_normalized_build_sha256": "5" * 64,
            "candidate_directory_name": co.ARTIFACT_PREFIX + raw[:8],
            "candidate_file_count": "21",
            "candidate_inventory_sha256": "6" * 64,
            "candidate_a_a_inventory_sha256": "6" * 64,
            "candidate_a_b_inventory_sha256": "6" * 64,
            "candidate_b_a_inventory_sha256": "6" * 64,
            "candidate_b_b_inventory_sha256": "6" * 64,
            "candidate_raw_member": co.BOOT_MEMBER,
            "candidate_raw_size": "8000000",
            "candidate_raw_sha256": raw,
            "candidate_padded_member": co.PADDED_MEMBER,
            "candidate_padded_size": str(di.BOOT2_SIZE),
            "candidate_padded_sha256": "7" * 64,
            "candidate_manifest_sha256": "8" * 64,
            "candidate_boot_dtb_sha256": co.ORION_BOOT_DTB_SHA256,
            "candidate_initramfs_sha256": co.HUBBLE_INITRAMFS_SHA256,
            "candidate_lk_analysis_sha256": "9" * 64,
            "package_a_candidate_lanes": "2",
            "package_b_candidate_lanes": "2",
            "package_mode_byte_equality": "exact",
            "candidate_mode_byte_equality": "exact",
            "normalized_build_provenance": "exact-except-generated_utc",
            "candidate_lk_validation": "source-pinned-32-gates",
            "candidate_padded_construction": "raw-prefix-zero-tail",
            "device_access": "none",
            "runtime_result": "not-tested",
        }
    )
    return fields


def render_record(fields: dict[str, str]) -> bytes:
    return (
        "\n".join(f"{key}={fields[key]}" for key in sorted(fields)) + "\n"
    ).encode("ascii")


class CurieToolingContracts(unittest.TestCase):
    def test_production_entrypoints_are_executable(self) -> None:
        names = (
            "build-candidate-curie.sh",
            "derive-candidate.py",
            "derive-installer.py",
            "run-curie-one-shot.py",
            "validate-package-curie.py",
            "validate-curie-result.py",
            "verify-curie-reproducibility.py",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(
                    stat.S_IMODE((SCRIPT_DIR / name).stat().st_mode),
                    0o755,
                )

    def test_assembler_is_exact_fermi_derivative_and_storage_inert(self) -> None:
        fermi = dc.load_fermi_deriver(REPOSITORY)
        quasar = fermi.load_quasar_deriver(REPOSITORY)
        source_data = dc.read_regular(
            REPOSITORY / quasar.VEGA_BUILDER,
            "source-pinned Vega assembler",
        )
        quasar_text = quasar.derive_text(source_data.decode("utf-8", "strict"))
        fermi_text = fermi.derive_text(quasar_text)
        curie = dc.derive_text(fermi_text)
        self.assertIn("candidate=Curie", curie)
        self.assertIn(
            "diagnostic=fixed-root-only-read-only-board-control-stability",
            curie,
        )
        self.assertIn("hardware_write=none", curie)
        self.assertIn("device_access=none", curie)
        for forbidden in ("of=/dev/", "ssh ", "reboot ", "fermi-run-native"):
            self.assertNotIn(forbidden, curie)
        with self.assertRaises(ValueError):
            dc.derive_text(fermi_text.replace("hardware_write=none", "", 1))

    def test_reproducibility_verifier_pins_curie_tools(self) -> None:
        self.assertEqual(vc.LK_EXPECTED_NAME, "gemini-curie")
        self.assertEqual(vc.CANDIDATE_MODULE_SHA256, di.CANDIDATE_MODULE_SHA256)
        self.assertEqual(
            vc.PACKAGE_VALIDATOR_SHA256,
            di.PACKAGE_VALIDATOR_SHA256,
        )
        self.assertEqual(
            hashlib.sha256((SCRIPT_DIR / "candidate_curie.py").read_bytes()).hexdigest(),
            vc.CANDIDATE_MODULE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(
                (SCRIPT_DIR / "validate-package-curie.py").read_bytes()
            ).hexdigest(),
            vc.PACKAGE_VALIDATOR_SHA256,
        )

    def test_runtime_program_has_one_fixed_write_and_no_reset_action(self) -> None:
        validator = rc.load_result_validator()
        program = rc.static_runtime_contract(validator)
        self.assertEqual(program.count(b"printf 'run\\n' >\"$diag\""), 1)
        self.assertIn(b"curie-run-native", program)
        self.assertNotIn(b"fermi-run-native", program)
        self.assertNotIn(b"reboot ", program)
        self.assertEqual(rc._BASE.KERNEL_RELEASE, "7.1.3-gemini-curie")
        self.assertEqual(
            rc._BASE.DIAGNOSTIC_STATUS_PRE,
            validator.exact_ready_status(),
        )

    def test_installer_record_requires_inventory_and_lane_equality(self) -> None:
        fields = synthetic_record()
        accepted = di.validate_record(render_record(fields))
        self.assertEqual(accepted["candidate_raw_sha256"], "1" * 64)
        mutations = []
        extra = copy.deepcopy(fields)
        extra["unreviewed"] = "accepted"
        mutations.append(extra)
        wrong_verifier = copy.deepcopy(fields)
        wrong_verifier["verifier_sha256"] = "a" * 64
        mutations.append(wrong_verifier)
        wrong_candidate = copy.deepcopy(fields)
        wrong_candidate["candidate_module_sha256"] = "b" * 64
        mutations.append(wrong_candidate)
        wrong_package = copy.deepcopy(fields)
        wrong_package["package_validator_sha256"] = "c" * 64
        mutations.append(wrong_package)
        lane_drift = copy.deepcopy(fields)
        lane_drift["candidate_b_b_inventory_sha256"] = "d" * 64
        mutations.append(lane_drift)
        predecessor_equal = copy.deepcopy(fields)
        predecessor_equal["candidate_padded_sha256"] = di.FERMI_PADDED_SHA256
        mutations.append(predecessor_equal)
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    di.validate_record(render_record(mutated))

    def test_installer_derivation_pins_fermi_predecessor_and_boot2_only(self) -> None:
        quasar = di.load_quasar_deriver(REPOSITORY)
        with tempfile.TemporaryDirectory(prefix="curie-installer-test.") as raw:
            source = quasar.reconstruct_vega(pathlib.Path(raw))
        quasar_text = quasar.derive_text(source, quasar.io.production_pins())
        pins = di.ArtifactPins(
            artifact_dir=co.ARTIFACT_PREFIX + "11111111",
            raw_sha256="1" * 64,
            raw_size=8_000_000,
            padded_sha256="7" * 64,
            manifest_sha256="8" * 64,
        )
        installer = di.derive_text(quasar_text, pins, quasar)
        self.assertIn(
            "readonly EXPECTED_CURRENT_FERMI_PADDED_SHA256="
            + di.FERMI_PADDED_SHA256,
            installer,
        )
        self.assertEqual(installer.count('of="$target"'), 1)
        self.assertIn("[[ \"$(uname -r)\" == 3.18.41+ ]]", installer)
        self.assertIn("[[ \"$active_root\" == /dev/mmcblk0p29 ]]", installer)
        self.assertIn(
            "battery_capacity >= 81 && battery_capacity <= 100",
            installer,
        )
        self.assertIn('blockdev --flushbufs "$target"', installer)
        self.assertIn('cmp -s "$padded" "$readback_partial"', installer)
        for forbidden in ("of=/dev/mmc", "reboot ", "shutdown ", "poweroff "):
            self.assertNotIn(forbidden, installer)

    def test_installer_artifact_manifest_requires_canonical_members(self) -> None:
        with tempfile.TemporaryDirectory(prefix="curie-artifact-manifest.") as raw:
            root = pathlib.Path(raw)
            members = {
                co.BOOT_MEMBER: b"synthetic Curie boot",
                co.PADDED_MEMBER: b"synthetic padded boot",
            }
            lines = []
            for name, data in members.items():
                (root / name).write_bytes(data)
                lines.append(f"{hashlib.sha256(data).hexdigest()}  ./{name}\n")
            manifest = "".join(sorted(lines)).encode("ascii")
            (root / "SHA256SUMS").write_bytes(manifest)
            wanted = hashlib.sha256(manifest).hexdigest()
            di.validate_manifest(root, wanted)
            (root / "SHA256SUMS").write_bytes(manifest.replace(b"  ./", b"  ", 1))
            with self.assertRaisesRegex(ValueError, "canonical"):
                di.validate_manifest(
                    root,
                    hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest(),
                )

    def test_production_record_is_source_pinned_or_explicitly_unresolved(self) -> None:
        if di.REPRODUCIBILITY_RECORD_SHA256 == "UNRESOLVED":
            with self.assertRaisesRegex(ValueError, "unresolved"):
                di.parse_record(REPOSITORY)
            return
        data = di.regular(
            REPOSITORY / di.REPRODUCIBILITY_RECORD,
            "production Curie reproducibility record",
        )
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            di.REPRODUCIBILITY_RECORD_SHA256,
        )
        fields = di.parse_record(REPOSITORY)
        self.assertEqual(fields["runtime_result"], "not-tested")


if __name__ == "__main__":
    unittest.main(verbosity=2)
