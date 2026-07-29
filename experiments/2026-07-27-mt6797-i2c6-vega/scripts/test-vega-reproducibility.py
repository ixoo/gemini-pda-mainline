#!/usr/bin/env python3
"""Offline mutation tests for Vega's two-build and 2x2 matrix record."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import pathlib
import struct
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import installer_vega as iv

SPEC = importlib.util.spec_from_file_location(
    "vega_reproducibility_verifier_test",
    SCRIPT_DIR / "verify-vega-reproducibility.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Vega reproducibility verifier")
VERIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFIER
SPEC.loader.exec_module(VERIFIER)


def align(value: int, page: int = 2048) -> int:
    return (value + page - 1) // page * page


def synthetic_lk_inputs() -> tuple[bytes, bytes, bytes, bytes]:
    arm64 = bytearray(4096)
    struct.pack_into("<3Q", arm64, 8, 0x00200000, len(arm64), 0x0A)
    arm64[56:60] = b"ARM\x64"
    arm64[64:] = b"synthetic Vega kernel".ljust(len(arm64) - 64, b"\0")
    image_gz = gzip.compress(bytes(arm64), mtime=0)
    dtb = struct.pack(
        ">10I",
        0xD00DFEED,
        40,
        40,
        40,
        40,
        17,
        16,
        0,
        0,
        0,
    )
    initramfs = b"synthetic Vega initramfs"
    kernel = image_gz + dtb
    fields = (
        len(kernel),
        0x40200000,
        len(initramfs),
        0x45000000,
        0,
        0x40F00000,
        0x44000000,
        2048,
        0,
        0,
    )
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, initramfs, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    header = bytearray(2048)
    struct.pack_into("<8s10I", header, 0, b"ANDROID!", *fields)
    header[48:64] = VERIFIER.LK_EXPECTED_NAME.encode("ascii").ljust(
        16, b"\0"
    )
    command = VERIFIER.LK_EXPECTED_CMDLINE.encode("ascii")
    header[64:576] = command[:512].ljust(512, b"\0")
    header[576:596] = image_id.digest()
    header[608:1632] = command[512:].ljust(1024, b"\0")
    raw = bytes(header) + kernel
    raw += b"\0" * (align(len(raw)) - len(raw))
    raw += initramfs
    raw += b"\0" * (align(len(raw)) - len(raw))
    return raw, image_gz, dtb, initramfs


def fixture_pins() -> iv.ArtifactPins:
    return iv.ArtifactPins(
        raw_sha256="1" * 64,
        raw_size=7_800_001,
        padded_sha256="2" * 64,
        manifest_sha256="3" * 64,
    )


def valid_record(pins: iv.ArtifactPins) -> bytes:
    package_inventory = {
        "Image": VERIFIER.InventoryMember(
            mode=0o600,
            size=123,
            sha256="4" * 64,
        )
    }
    candidate_inventory = {
        iv.BOOT_MEMBER: VERIFIER.InventoryMember(
            mode=0o600,
            size=pins.raw_size,
            sha256=pins.raw_sha256,
        )
    }
    packages = (
        VERIFIER.PackageResult(
            directory_name="linux-7.1.3-gemini-vega-fixture",
            manifest_sha256="5" * 64,
            generated_utc="2026-07-27T01:00:00Z",
            normalized_build=b'{"fixture":true}\n',
            normalized_inventory=package_inventory,
        ),
        VERIFIER.PackageResult(
            directory_name="linux-7.1.3-gemini-vega-fixture",
            manifest_sha256="6" * 64,
            generated_utc="2026-07-27T02:00:00Z",
            normalized_build=b'{"fixture":true}\n',
            normalized_inventory=package_inventory,
        ),
    )
    candidate = VERIFIER.CandidateResult(
        directory_name=pins.artifact_dir,
        inventory=candidate_inventory,
        raw_size=pins.raw_size,
        raw_sha256=pins.raw_sha256,
        padded_sha256=pins.padded_sha256,
        manifest_sha256=pins.manifest_sha256,
        analysis_sha256="9" * 64,
    )
    return VERIFIER.render_record(
        iv.REPRODUCIBILITY_VERIFIER_SHA256,
        packages,
        (candidate, candidate, candidate, candidate),
    )


class VegaReproducibilityContracts(unittest.TestCase):
    def test_source_pinned_verifier_identity(self) -> None:
        verifier = SCRIPT_DIR / "verify-vega-reproducibility.py"
        self.assertEqual(
            iv.digest_path(verifier),
            iv.REPRODUCIBILITY_VERIFIER_SHA256,
        )

    def test_transitive_validator_identities_are_source_pinned(self) -> None:
        repository = SCRIPT_DIR.parents[2]
        self.assertEqual(
            VERIFIER.CANDIDATE_MODULE_SHA256,
            iv.REPRODUCIBILITY_CANDIDATE_MODULE_SHA256,
        )
        self.assertEqual(
            VERIFIER.PACKAGE_VALIDATOR_SHA256,
            iv.REPRODUCIBILITY_PACKAGE_VALIDATOR_SHA256,
        )
        self.assertEqual(
            VERIFIER.LK_ANALYZER_SHA256,
            iv.REPRODUCIBILITY_LK_ANALYZER_SHA256,
        )
        self.assertTrue(callable(VERIFIER.load_package_validator().validate))
        self.assertTrue(
            callable(VERIFIER.load_lk_analyzer(repository).parse)
        )
        sources = (
            (
                SCRIPT_DIR / "candidate_vega.py",
                VERIFIER.CANDIDATE_MODULE_SHA256,
            ),
            (
                SCRIPT_DIR / "validate-package-vega.py",
                VERIFIER.PACKAGE_VALIDATOR_SHA256,
            ),
            (
                repository / VERIFIER.LK_ANALYZER_RELATIVE,
                VERIFIER.LK_ANALYZER_SHA256,
            ),
        )
        with tempfile.TemporaryDirectory(
            prefix="vega-source-pin-mutations."
        ) as raw:
            root = pathlib.Path(raw)
            for index, (source, wanted) in enumerate(sources):
                mutated = root / f"source-{index}.py"
                mutated.write_bytes(source.read_bytes() + b"\n# mutation\n")
                with self.subTest(source=source.name):
                    with self.assertRaisesRegex(
                        VERIFIER.ContractError,
                        "source identity changed",
                    ):
                        VERIFIER.load_source_pinned_module(
                            mutated,
                            wanted,
                            source.name,
                            f"vega_mutated_source_{index}",
                        )

    def test_lk_analyzer_binds_all_embedded_payloads(self) -> None:
        repository = SCRIPT_DIR.parents[2]
        analyzer = VERIFIER.load_lk_analyzer(repository)
        raw_image, image_gz, dtb, initramfs = synthetic_lk_inputs()
        with tempfile.TemporaryDirectory(prefix="vega-lk-artifact.") as raw:
            root = pathlib.Path(raw)
            paths = {
                "raw": root / "candidate.boot.img",
                "image": root / "Image.gz",
                "dtb": root / "candidate.dtb",
                "initramfs": root / "initramfs.img",
                "analysis": root / "analysis.txt",
            }
            paths["raw"].write_bytes(raw_image)
            paths["image"].write_bytes(image_gz)
            paths["dtb"].write_bytes(dtb)
            paths["initramfs"].write_bytes(initramfs)
            result, failures = analyzer.parse(
                paths["raw"],
                expected_dtb=paths["dtb"],
                expected_image_gz=paths["image"],
                expected_ramdisk=paths["initramfs"],
                expected_name=VERIFIER.LK_EXPECTED_NAME,
                expected_cmdline=VERIFIER.LK_EXPECTED_CMDLINE,
            )
            self.assertEqual(failures, [])
            analysis = (
                "".join(
                    f"{key}={value}\n" for key, value in result.items()
                )
                + "hardware_write=none\n"
            ).encode("ascii")
            paths["analysis"].write_bytes(analysis)
            self.assertEqual(
                VERIFIER.verify_lk_artifact(
                    paths["raw"],
                    paths["image"],
                    paths["initramfs"],
                    paths["dtb"],
                    paths["analysis"],
                    analyzer,
                    "synthetic Vega candidate",
                ),
                hashlib.sha256(analysis).hexdigest(),
            )
            mutations = (
                ("raw", raw_image[:-1] + bytes([raw_image[-1] ^ 1])),
                ("image", image_gz + b"changed"),
                ("dtb", dtb + b"changed"),
                ("initramfs", initramfs + b"changed"),
                ("analysis", analysis + b"forged=1\n"),
            )
            originals = {
                key: path.read_bytes()
                for key, path in paths.items()
            }
            for key, mutated in mutations:
                with self.subTest(member=key):
                    paths[key].write_bytes(mutated)
                    with self.assertRaisesRegex(
                        VERIFIER.ContractError,
                        "LK analysis|LK gates",
                    ):
                        VERIFIER.verify_lk_artifact(
                            paths["raw"],
                            paths["image"],
                            paths["initramfs"],
                            paths["dtb"],
                            paths["analysis"],
                            analyzer,
                            "synthetic Vega candidate",
                        )
                    paths[key].write_bytes(originals[key])

    def test_padded_image_is_raw_prefix_plus_zero_tail(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="vega-padded-contract."
        ) as raw:
            root = pathlib.Path(raw)
            raw_path = root / "raw.img"
            padded_path = root / "padded.img"
            raw_bytes = b"synthetic raw Vega candidate"
            padded_bytes = raw_bytes + b"\0" * 97
            raw_path.write_bytes(raw_bytes)
            padded_path.write_bytes(padded_bytes)
            VERIFIER.verify_padded_construction(
                raw_path,
                padded_path,
                len(raw_bytes),
                len(padded_bytes),
                "synthetic Vega candidate",
            )
            prefix_mutation = bytearray(padded_bytes)
            prefix_mutation[0] ^= 1
            padded_path.write_bytes(prefix_mutation)
            with self.assertRaisesRegex(
                VERIFIER.ContractError,
                "prefix differs",
            ):
                VERIFIER.verify_padded_construction(
                    raw_path,
                    padded_path,
                    len(raw_bytes),
                    len(padded_bytes),
                    "synthetic Vega candidate",
                )
            tail_mutation = bytearray(padded_bytes)
            tail_mutation[-1] = 1
            padded_path.write_bytes(tail_mutation)
            with self.assertRaisesRegex(
                VERIFIER.ContractError,
                "tail is not all zero",
            ):
                VERIFIER.verify_padded_construction(
                    raw_path,
                    padded_path,
                    len(raw_bytes),
                    len(padded_bytes),
                    "synthetic Vega candidate",
                )

    def test_installer_derivation_requires_pinned_matrix_record(self) -> None:
        source = (SCRIPT_DIR / "derive-installer.py").read_text()
        ordered = (
            "io.require_artifact_pins(pins)",
            "io.require_reproducibility_record(",
            "io.require_installer_pin()",
            "text = derive_text(source, pins)",
        )
        positions = [source.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(
            source.count("io.require_reproducibility_record("),
            1,
        )
        self.assertRegex(
            iv.REPRODUCIBILITY_RECORD_SHA256,
            iv.HEX256,
        )
        record = SCRIPT_DIR.parents[0] / "results/build-reproducibility.txt"
        self.assertEqual(
            iv.digest_path(record),
            iv.REPRODUCIBILITY_RECORD_SHA256,
        )
        self.assertRegex(iv.INSTALLER_SHA256, iv.HEX256)

    def test_requires_two_distinct_packages_and_all_four_matrix_lanes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="vega-reproducibility-lanes."
        ) as raw:
            root = pathlib.Path(raw)
            packages = (root / "package-a", root / "package-b")
            candidates = tuple(
                root / f"candidate-{index}"
                for index in range(4)
            )
            for path in packages + candidates:
                path.mkdir()
            VERIFIER.require_distinct_lanes(packages, candidates)
            with self.assertRaisesRegex(
                VERIFIER.ContractError,
                "two package lanes and four matrix lanes",
            ):
                VERIFIER.require_distinct_lanes(
                    packages[:1],
                    candidates,
                )
            with self.assertRaisesRegex(
                VERIFIER.ContractError,
                "candidate matrix lanes are not distinct",
            ):
                VERIFIER.require_distinct_lanes(
                    packages,
                    candidates[:3] + (candidates[0],),
                )

    def test_mode_byte_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            VERIFIER.ContractError,
            "mode-byte inventory mismatch",
        ):
            VERIFIER.require_identical(
                "Vega candidate mode-byte inventory",
                ({"Image": (0o600, "a")}, {"Image": (0o755, "a")}),
            )

    def test_valid_strict_record_matches_artifact_pins(self) -> None:
        pins = fixture_pins()
        fields = iv.validate_reproducibility_record(
            valid_record(pins),
            pins,
        )
        self.assertEqual(fields["package_lane_count"], "2")
        self.assertEqual(fields["candidate_lane_count"], "4")
        self.assertEqual(fields["candidate_raw_sha256"], pins.raw_sha256)

    def test_one_lane_mismatch_and_forged_records_are_rejected(self) -> None:
        pins = fixture_pins()
        record = valid_record(pins)
        fields = iv.parse_reproducibility_record(record)
        candidate_inventory = fields["candidate_inventory_sha256"].encode()
        mutations = (
            record.replace(
                b"package_lane_count=2\n",
                b"package_lane_count=1\n",
                1,
            ),
            record.replace(
                f"candidate_raw_sha256={pins.raw_sha256}\n".encode(),
                b"candidate_raw_sha256=" + b"7" * 64 + b"\n",
                1,
            ),
            record.replace(
                b"validation=vega-two-build-2x2-reproducibility\n",
                b"validation=forged\n",
                1,
            ),
            record.replace(
                (
                    "candidate_module_sha256="
                    f"{VERIFIER.CANDIDATE_MODULE_SHA256}\n"
                ).encode(),
                b"candidate_module_sha256=" + b"a" * 64 + b"\n",
                1,
            ),
            record.replace(
                (
                    "package_validator_sha256="
                    f"{VERIFIER.PACKAGE_VALIDATOR_SHA256}\n"
                ).encode(),
                b"package_validator_sha256=" + b"b" * 64 + b"\n",
                1,
            ),
            record.replace(
                (
                    "lk_analyzer_sha256="
                    f"{VERIFIER.LK_ANALYZER_SHA256}\n"
                ).encode(),
                b"lk_analyzer_sha256=" + b"c" * 64 + b"\n",
                1,
            ),
            record.replace(
                b"candidate_b_b_inventory_sha256="
                + candidate_inventory
                + b"\n",
                b"candidate_b_b_inventory_sha256=" + b"8" * 64 + b"\n",
                1,
            ),
            record + b"candidate_lane_count=4\n",
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    iv.validate_reproducibility_record(mutated, pins)


if __name__ == "__main__":
    unittest.main()
