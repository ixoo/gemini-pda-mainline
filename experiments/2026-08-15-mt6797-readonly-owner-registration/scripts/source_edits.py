#!/usr/bin/env python3
"""Apply one deterministic read-only owner-registration prerequisite."""

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def replace_count(path: Path, old: str, new: str, expected: int) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != expected:
        raise SystemExit(
            f"{path}: expected {expected} edit anchors, found {count}"
        )
    path.write_text(text.replace(old, new))


def widen_epoch(root: Path) -> None:
    handoff = root / "include/linux/soc/mediatek/mt6797-dvfsp-handoff.h"
    test = root / "drivers/soc/mediatek/mt6797-dvfsp-calibrated-provider-test.c"

    replace_once(
        handoff,
        "#define MT6797_DVFSP_STATE_PROVENANCE_ABI\t\t1\n",
        "#define MT6797_DVFSP_STATE_PROVENANCE_ABI\t\t2\n",
    )
    replace_once(
        handoff,
        "struct mt6797_dvfsp_state_provenance {\n"
        "\tu32 abi;\n\tu32 source_mask;\n\tu32 variant_id;\n"
        "\tu32 table_epoch;\n\tu64 calibration_handle;\n};\n",
        "struct mt6797_dvfsp_state_provenance {\n"
        "\tu32 abi;\n\tu32 source_mask;\n\tu32 variant_id;\n"
        "\tu64 table_epoch;\n\tu64 calibration_handle;\n};\n",
    )
    replace_once(
        test,
        "static struct kunit_case mt6797_dvfsp_provider_test_cases[] = {\n",
        "static void mt6797_dvfsp_provider_preserves_wide_epoch(\n"
        "\tstruct kunit *test)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_state_provenance provenance = {\n"
        "\t\t.abi = MT6797_DVFSP_STATE_PROVENANCE_ABI,\n"
        "\t\t.table_epoch = 0x100000002ULL,\n"
        "\t};\n\n"
        "\tKUNIT_EXPECT_EQ(test, provenance.table_epoch, 0x100000002ULL);\n"
        "\tKUNIT_EXPECT_EQ(test, sizeof(provenance.table_epoch),\n"
        "\t\tsizeof(u64));\n"
        "}\n\n"
        "static struct kunit_case mt6797_dvfsp_provider_test_cases[] = {\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_dvfsp_provider_binds_and_exits),\n\t{ }\n",
        "\tKUNIT_CASE(mt6797_dvfsp_provider_binds_and_exits),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_provider_preserves_wide_epoch),\n"
        "\t{ }\n",
    )


def preserve_snapshot_attribution(root: Path) -> None:
    source = root / "drivers/soc/mediatek/mt6797-dvfsp-state-snapshot.c"
    test = root / "drivers/soc/mediatek/mt6797-dvfsp-calibrated-provider-test.c"

    replace_once(
        source,
        "\tsnapshot->generation = input->generation;\n\n"
        "\tfor (i = 0; i < MT6797_DVFSP_STATE_CLUSTER_COUNT; i++) {\n",
        "\tsnapshot->generation = input->generation;\n"
        "\tsnapshot->owner_handle = input->owner_handle;\n"
        "\tsnapshot->transition_handle = input->transition_handle;\n"
        "\tsnapshot->provenance = input->provenance;\n\n"
        "\tfor (i = 0; i < MT6797_DVFSP_STATE_CLUSTER_COUNT; i++) {\n",
    )
    replace_once(
        test,
        "#include <linux/soc/mediatek/mt6797-dvfsp-calibrated-provider.h>\n",
        "#include <linux/soc/mediatek/mt6797-dvfsp-calibrated-provider.h>\n"
        "#include <linux/soc/mediatek/mt6797-dvfsp-state-snapshot.h>\n",
    )
    replace_once(
        test,
        "static struct kunit_case mt6797_dvfsp_provider_test_cases[] = {\n",
        "static void mt6797_dvfsp_provider_snapshot_keeps_attribution(\n"
        "\tstruct kunit *test)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_clock_state clock = {\n"
        "\t\t.abi = MT6797_DVFSP_CLOCK_STATE_ABI,\n"
        "\t\t.clock_sample_generation = 1,\n"
        "\t\t.big_sample_generation = 1,\n"
        "\t};\n"
        "\tstruct mt6797_dvfsp_calibration_state calibration = {\n"
        "\t\t.abi = MT6797_DVFSP_CALIBRATION_STATE_ABI,\n"
        "\t\t.phase = MT6797_DVFSP_CALIBRATION_STATE_PHASE_MON,\n"
        "\t\t.bank_mask = MT6797_DVFSP_CALIBRATION_STATE_BANK_ALL,\n"
        "\t\t.thermal_generation = 1,\n"
        "\t\t.clock_owner_generation = 1,\n"
        "\t\t.rail_owner_generation = 1,\n"
        "\t\t.source_generation = 9,\n"
        "\t};\n"
        "\tstruct mt6797_dvfsp_state_snapshot_input input = {\n"
        "\t\t.abi = MT6797_DVFSP_STATE_SNAPSHOT_ABI,\n"
        "\t\t.generation = 9,\n"
        "\t\t.owner_handle = 0x67970031,\n"
        "\t\t.transition_handle = 0x67970030,\n"
        "\t\t.clock = &clock,\n"
        "\t\t.calibration = &calibration,\n"
        "\t\t.provenance = {\n"
        "\t\t\t.abi = MT6797_DVFSP_STATE_PROVENANCE_ABI,\n"
        "\t\t\t.source_mask = MT6797_DVFSP_STATE_PROVENANCE_SOURCE_ALL,\n"
        "\t\t\t.variant_id = 274,\n"
        "\t\t\t.table_epoch = 0x100000002ULL,\n"
        "\t\t\t.calibration_handle = 0x6797abcdULL,\n"
        "\t\t},\n"
        "\t};\n"
        "\tstruct mt6797_dvfsp_state_snapshot snapshot;\n"
        "\tunsigned int i;\n\n"
        "\tcalibration.provenance = input.provenance;\n"
        "\tfor (i = 0; i < MT6797_DVFSP_STATE_CLUSTER_COUNT; i++) {\n"
        "\t\tstruct mt6797_dvfsp_calibration_table_entry *entry =\n"
        "\t\t\t&calibration.cluster[i].table[0];\n\n"
        "\t\tcalibration.cluster[i].table_count = 1;\n"
        "\t\tentry->frequency_khz = 100000 + i;\n"
        "\t\tentry->vproc_uv = 800000;\n"
        "\t\tentry->vsram_uv = 820000;\n"
        "\t\tentry->ppm_limit_khz = 200000;\n"
        "\t\tclock.cluster[i].frequency_khz = entry->frequency_khz;\n"
        "\t\tinput.state_flags[i] = MT6797_DVFSP_STATE_FLAG_PRESENT |\n"
        "\t\t\tMT6797_DVFSP_STATE_FLAG_ON;\n"
        "\t\tinput.frequency_khz[i] = entry->frequency_khz;\n"
        "\t\tinput.voltage_uv[i] = entry->vproc_uv;\n"
        "\t\tinput.vsram_uv[i] = entry->vsram_uv;\n"
        "\t\tinput.ceiling_khz[i] = 200000;\n"
        "\t\tinput.floor_khz[i] = 50000;\n"
        "\t}\n\n"
        "\tKUNIT_ASSERT_EQ(test, mt6797_dvfsp_state_snapshot_assemble(\n"
        "\t\t&input, &snapshot), 0);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.generation, input.generation);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.owner_handle, input.owner_handle);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.transition_handle,\n"
        "\t\tinput.transition_handle);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.provenance.table_epoch,\n"
        "\t\tinput.provenance.table_epoch);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.provenance.calibration_handle,\n"
        "\t\tinput.provenance.calibration_handle);\n"
        "}\n\n"
        "static struct kunit_case mt6797_dvfsp_provider_test_cases[] = {\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_dvfsp_provider_preserves_wide_epoch),\n\t{ }\n",
        "\tKUNIT_CASE(mt6797_dvfsp_provider_preserves_wide_epoch),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_provider_snapshot_keeps_attribution),\n"
        "\t{ }\n",
    )


def require_vendor_provenance(root: Path) -> None:
    header = root / "include/linux/soc/mediatek/mt6797-dvfsp-vendor-provider.h"
    source = root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider.c"
    test = root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider-test.c"

    replace_once(
        header,
        "#define MT6797_DVFSP_VENDOR_PROVIDER_ABI\t3\n",
        "#define MT6797_DVFSP_VENDOR_PROVIDER_ABI\t4\n",
    )
    replace_once(
        header,
        "\tstruct mt6797_dvfsp_vendor_source_identity identity;\n"
        "\tu32 policy_row_count;\n",
        "\tstruct mt6797_dvfsp_vendor_source_identity identity;\n"
        "\tstruct mt6797_dvfsp_vendor_source_provenance provenance;\n"
        "\tu32 policy_row_count;\n",
    )
    replace_once(
        header,
        "\tconst struct mt6797_dvfsp_vendor_source_identity *identity,\n"
        "\tu64 owner_handle, u64 transition_handle,\n",
        "\tconst struct mt6797_dvfsp_vendor_source_identity *identity,\n"
        "\tconst struct mt6797_dvfsp_vendor_source_provenance *provenance,\n"
        "\tu64 owner_handle, u64 transition_handle,\n",
    )

    replace_once(
        source,
        "\tconst struct mt6797_dvfsp_vendor_source_identity *identity,\n"
        "\tu64 owner_handle, u64 transition_handle)\n",
        "\tconst struct mt6797_dvfsp_vendor_source_identity *identity,\n"
        "\tconst struct mt6797_dvfsp_vendor_source_provenance *provenance,\n"
        "\tu64 owner_handle, u64 transition_handle)\n",
    )
    replace_once(
        source,
        "\t    !identity->variant_id || !identity->table_epoch ||\n"
        "\t    !identity->calibration_handle)\n",
        "\t    !identity->variant_id || !identity->table_epoch ||\n"
        "\t    !identity->calibration_handle || !provenance ||\n"
        "\t    provenance->abi != MT6797_DVFSP_VENDOR_SOURCE_PROVENANCE_ABI ||\n"
        "\t    provenance->variant_id != identity->variant_id ||\n"
        "\t    provenance->table_epoch != identity->table_epoch ||\n"
        "\t    provenance->calibration_handle !=\n"
        "\t\tidentity->calibration_handle ||\n"
        "\t    provenance->source_generation != source->generation ||\n"
        "\t    provenance->owner_handle != source->owner_handle ||\n"
        "\t    provenance->transition_handle != source->transition_handle)\n",
    )
    replace_once(
        source,
        "\tconst struct mt6797_dvfsp_vendor_source_identity *identity,\n"
        "\tu64 owner_handle, u64 transition_handle,\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped)\n",
        "\tconst struct mt6797_dvfsp_vendor_source_identity *identity,\n"
        "\tconst struct mt6797_dvfsp_vendor_source_provenance *provenance,\n"
        "\tu64 owner_handle, u64 transition_handle,\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped)\n",
    )
    replace_once(
        source,
        "\tret = mt6797_dvfsp_vendor_provider_source_check(source, identity,\n"
        "\t\t\towner_handle, transition_handle);\n",
        "\tret = mt6797_dvfsp_vendor_provider_source_check(source, identity,\n"
        "\t\t\tprovenance, owner_handle, transition_handle);\n",
    )
    replace_once(
        source,
        "\tmapped->identity = *identity;\n\n",
        "\tmapped->identity = *identity;\n"
        "\tmapped->provenance = *provenance;\n\n",
    )
    replace_once(
        source,
        "\tstruct mt6797_dvfsp_vendor_source_identity identity;\n\tint ret;\n",
        "\tstruct mt6797_dvfsp_vendor_source_identity identity;\n"
        "\tstruct mt6797_dvfsp_vendor_source_provenance provenance;\n"
        "\tint ret;\n",
    )
    replace_once(
        source,
        "\tret = mt6797_dvfsp_vendor_source_identity(bridge->source, &identity);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\treturn mt6797_dvfsp_vendor_provider_map(&source, &identity,\n"
        "\t\tbridge->owner_handle, bridge->transition_handle, mapped);\n",
        "\tret = mt6797_dvfsp_vendor_source_identity(bridge->source, &identity);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\tmemset(&provenance, 0, sizeof(provenance));\n"
        "\tret = mt6797_dvfsp_vendor_source_provenance(bridge->source,\n"
        "\t\t&source, &provenance);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\treturn mt6797_dvfsp_vendor_provider_map(&source, &identity,\n"
        "\t\t&provenance, bridge->owner_handle,\n"
        "\t\tbridge->transition_handle, mapped);\n",
    )

    replace_once(
        test,
        "static struct mt6797_dvfsp_vendor_source_identity\n"
        "\tmt6797_dvfsp_vendor_provider_test_identity;\n",
        "static struct mt6797_dvfsp_vendor_source_identity\n"
        "\tmt6797_dvfsp_vendor_provider_test_identity;\n"
        "static struct mt6797_dvfsp_vendor_source_provenance\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance;\n",
    )
    replace_once(
        test,
        "static const struct mt6797_dvfsp_vendor_source_ops\n"
        "mt6797_dvfsp_vendor_provider_test_source_ops = {\n",
        "static int mt6797_dvfsp_vendor_provider_test_read_observation(\n"
        "\tvoid *context,\n"
        "\tstruct mt6797_dvfsp_vendor_source_identity_observation *observation)\n"
        "{\n"
        "\tmemset(observation, 0, sizeof(*observation));\n"
        "\tobservation->abi =\n"
        "\t\tMT6797_DVFSP_VENDOR_SOURCE_IDENTITY_OBSERVATION_ABI;\n"
        "\tobservation->source_mask = MT6797_DVFSP_VENDOR_SOURCE_IDENTITY_ALL;\n"
        "\tobservation->function_word = 0x22;\n"
        "\tobservation->date_word = 0x70;\n"
        "\tobservation->cpu_bin_level = 1;\n"
        "\tobservation->eem_ate_version = 6;\n"
        "\tobservation->ppm_table_type = 1;\n"
        "\treturn 0;\n"
        "}\n\n"
        "static int mt6797_dvfsp_vendor_provider_test_read_provenance(\n"
        "\tvoid *context,\n"
        "\tconst struct mt6797_dvfsp_vendor_source_snapshot *snapshot,\n"
        "\tstruct mt6797_dvfsp_vendor_source_provenance *provenance)\n"
        "{\n"
        "\t*provenance = mt6797_dvfsp_vendor_provider_test_provenance;\n"
        "\treturn 0;\n"
        "}\n\n"
        "static const struct mt6797_dvfsp_vendor_source_ops\n"
        "mt6797_dvfsp_vendor_provider_test_source_ops = {\n",
    )
    replace_once(
        test,
        "\t.read_identity = mt6797_dvfsp_vendor_provider_test_read_identity,\n};\n",
        "\t.read_identity = mt6797_dvfsp_vendor_provider_test_read_identity,\n"
        "\t.read_identity_observation =\n"
        "\t\tmt6797_dvfsp_vendor_provider_test_read_observation,\n"
        "\t.read_provenance =\n"
        "\t\tmt6797_dvfsp_vendor_provider_test_read_provenance,\n"
        "};\n",
    )
    replace_once(
        test,
        "\tmt6797_dvfsp_vendor_provider_test_identity.calibration_handle =\n"
        "\t\t0x6797abcdULL;\n}\n",
        "\tmt6797_dvfsp_vendor_provider_test_identity.calibration_handle =\n"
        "\t\t0x6797abcdULL;\n"
        "\tmemset(&mt6797_dvfsp_vendor_provider_test_provenance, 0,\n"
        "\t       sizeof(mt6797_dvfsp_vendor_provider_test_provenance));\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.abi =\n"
        "\t\tMT6797_DVFSP_VENDOR_SOURCE_PROVENANCE_ABI;\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.variant_id = 7;\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.table_epoch =\n"
        "\t\t0x100000002ULL;\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.calibration_handle =\n"
        "\t\t0x6797abcdULL;\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.source_generation = 9;\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.owner_handle =\n"
        "\t\t0x67970023;\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.transition_handle =\n"
        "\t\t0x67970022;\n"
        "}\n",
    )
    replace_count(
        test,
        "\t\t&mt6797_dvfsp_vendor_provider_test_identity,\n"
        "\t\t0x67970023, 0x67970022, &mapped)",
        "\t\t&mt6797_dvfsp_vendor_provider_test_identity,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_provenance,\n"
        "\t\t0x67970023, 0x67970022, &mapped)",
        5,
    )
    replace_once(
        test,
        "\tKUNIT_EXPECT_EQ(test, mapped.identity.calibration_handle,\n"
        "\t\t0x6797abcdULL);\n}\n",
        "\tKUNIT_EXPECT_EQ(test, mapped.identity.calibration_handle,\n"
        "\t\t0x6797abcdULL);\n"
        "\tKUNIT_EXPECT_EQ(test, mapped.provenance.source_generation, 9ULL);\n"
        "\tKUNIT_EXPECT_EQ(test, mapped.provenance.table_epoch,\n"
        "\t\t0x100000002ULL);\n"
        "\tKUNIT_EXPECT_EQ(test, mapped.provenance.calibration_handle,\n"
        "\t\t0x6797abcdULL);\n"
        "}\n",
    )
    replace_once(
        test,
        "static void mt6797_dvfsp_vendor_provider_rejects_bad_clock_or_rail(\n",
        "static void mt6797_dvfsp_vendor_provider_rejects_provenance_mismatch(\n"
        "\tstruct kunit *test)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot mapped;\n\n"
        "\tmt6797_dvfsp_vendor_provider_test_fill();\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.table_epoch++;\n"
        "\tKUNIT_EXPECT_EQ(test, mt6797_dvfsp_vendor_provider_map(\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_snapshot,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_identity,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_provenance,\n"
        "\t\t0x67970023, 0x67970022, &mapped), -EPROTO);\n"
        "\tmt6797_dvfsp_vendor_provider_test_fill();\n"
        "\tmt6797_dvfsp_vendor_provider_test_provenance.source_generation++;\n"
        "\tKUNIT_EXPECT_EQ(test, mt6797_dvfsp_vendor_provider_map(\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_snapshot,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_identity,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_provenance,\n"
        "\t\t0x67970023, 0x67970022, &mapped), -EPROTO);\n"
        "}\n\n"
        "static void mt6797_dvfsp_vendor_provider_rejects_bad_clock_or_rail(\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_identity_or_ids),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_bad_eem_units),\n",
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_identity_or_ids),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_provenance_mismatch),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_bad_eem_units),\n",
    )


PHASES = {
    "widen-epoch": widen_epoch,
    "preserve-snapshot-attribution": preserve_snapshot_attribution,
    "require-vendor-provenance": require_vendor_provenance,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"source root is not a directory: {root}")
    PHASES[args.phase](root)


if __name__ == "__main__":
    main()
