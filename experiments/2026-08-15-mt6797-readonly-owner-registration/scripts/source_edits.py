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


def bound_vendor_bridge_storage(root: Path) -> None:
    source = root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider.c"

    replace_once(
        source,
        "#include <linux/module.h>\n#include <linux/string.h>\n",
        "#include <linux/module.h>\n#include <linux/slab.h>\n"
        "#include <linux/string.h>\n",
    )
    replace_once(
        source,
        "int mt6797_dvfsp_vendor_provider_bridge_snapshot(\n"
        "\tstruct mt6797_dvfsp_vendor_provider_bridge *bridge,\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_vendor_source_snapshot source;\n"
        "\tstruct mt6797_dvfsp_vendor_source_identity identity;\n"
        "\tstruct mt6797_dvfsp_vendor_source_provenance provenance;\n"
        "\tint ret;\n\n"
        "\tif (!bridge || !bridge->initialized || !bridge->provider ||\n"
        "\t    !bridge->provider->initialized || !bridge->source || !mapped)\n"
        "\t\treturn -ENODEV;\n"
        "\tmemset(&source, 0, sizeof(source));\n"
        "\tret = mt6797_dvfsp_vendor_source_snapshot(bridge->source, &source);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\tmemset(&identity, 0, sizeof(identity));\n"
        "\tret = mt6797_dvfsp_vendor_source_identity(bridge->source, &identity);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\tmemset(&provenance, 0, sizeof(provenance));\n"
        "\tret = mt6797_dvfsp_vendor_source_provenance(bridge->source,\n"
        "\t\t&source, &provenance);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\treturn mt6797_dvfsp_vendor_provider_map(&source, &identity,\n"
        "\t\t&provenance, bridge->owner_handle,\n"
        "\t\tbridge->transition_handle, mapped);\n"
        "}\n",
        "int mt6797_dvfsp_vendor_provider_bridge_snapshot(\n"
        "\tstruct mt6797_dvfsp_vendor_provider_bridge *bridge,\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_vendor_source_snapshot *source;\n"
        "\tstruct mt6797_dvfsp_vendor_source_identity identity;\n"
        "\tstruct mt6797_dvfsp_vendor_source_provenance provenance;\n"
        "\tint ret;\n\n"
        "\tif (!bridge || !bridge->initialized || !bridge->provider ||\n"
        "\t    !bridge->provider->initialized || !bridge->source || !mapped)\n"
        "\t\treturn -ENODEV;\n"
        "\tsource = kzalloc(sizeof(*source), GFP_KERNEL);\n"
        "\tif (!source)\n\t\treturn -ENOMEM;\n"
        "\tret = mt6797_dvfsp_vendor_source_snapshot(bridge->source, source);\n"
        "\tif (ret)\n\t\tgoto out_free;\n"
        "\tmemset(&identity, 0, sizeof(identity));\n"
        "\tret = mt6797_dvfsp_vendor_source_identity(bridge->source, &identity);\n"
        "\tif (ret)\n\t\tgoto out_free;\n"
        "\tmemset(&provenance, 0, sizeof(provenance));\n"
        "\tret = mt6797_dvfsp_vendor_source_provenance(bridge->source,\n"
        "\t\tsource, &provenance);\n"
        "\tif (ret)\n\t\tgoto out_free;\n"
        "\tret = mt6797_dvfsp_vendor_provider_map(source, &identity,\n"
        "\t\t&provenance, bridge->owner_handle,\n"
        "\t\tbridge->transition_handle, mapped);\n\n"
        "out_free:\n"
        "\tkfree(source);\n"
        "\treturn ret;\n"
        "}\n",
    )


def register_validated_owner(root: Path) -> None:
    provider_header = (
        root / "include/linux/soc/mediatek/mt6797-dvfsp-vendor-provider.h"
    )
    provider_source = (
        root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider.c"
    )
    provider_test = (
        root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider-test.c"
    )
    owner_header = (
        root / "include/linux/soc/mediatek/mt6797-dvfsp-vendor-owner.h"
    )
    owner_source = root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-owner.c"
    owner_test = (
        root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-owner-test.c"
    )

    replace_once(
        provider_header,
        "#define MT6797_DVFSP_VENDOR_PROVIDER_ABI\t4\n",
        "#define MT6797_DVFSP_VENDOR_PROVIDER_ABI\t5\n",
    )
    replace_once(
        provider_header,
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped);\n\n"
        "/* Attach the read-only review view to an already dormant calibrated provider. */\n",
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped);\n\n"
        "/* Require one exact vendor, calibrated-state, and owner identity view. */\n"
        "int mt6797_dvfsp_vendor_provider_match_state(\n"
        "\tconst struct mt6797_dvfsp_vendor_provider_snapshot *mapped,\n"
        "\tconst struct mt6797_dvfsp_state_snapshot *snapshot,\n"
        "\tconst struct mt6797_dvfsp_state_owner_identity *identity);\n\n"
        "/* Attach the read-only review view to an already dormant calibrated provider. */\n",
    )
    replace_once(
        provider_source,
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_provider_map);\n\n"
        "int mt6797_dvfsp_vendor_provider_bridge_init(\n",
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_provider_map);\n\n"
        "static bool mt6797_dvfsp_vendor_provider_state_provenance_equal(\n"
        "\tconst struct mt6797_dvfsp_state_provenance *left,\n"
        "\tconst struct mt6797_dvfsp_state_provenance *right)\n"
        "{\n"
        "\treturn left->abi == right->abi &&\n"
        "\t\tleft->source_mask == right->source_mask &&\n"
        "\t\tleft->variant_id == right->variant_id &&\n"
        "\t\tleft->table_epoch == right->table_epoch &&\n"
        "\t\tleft->calibration_handle == right->calibration_handle;\n"
        "}\n\n"
        "static bool mt6797_dvfsp_vendor_provider_provenance_matches(\n"
        "\tconst struct mt6797_dvfsp_vendor_provider_snapshot *mapped,\n"
        "\tconst struct mt6797_dvfsp_state_provenance *provenance)\n"
        "{\n"
        "\treturn provenance->variant_id == mapped->identity.variant_id &&\n"
        "\t\tprovenance->variant_id == mapped->provenance.variant_id &&\n"
        "\t\tprovenance->table_epoch == mapped->identity.table_epoch &&\n"
        "\t\tprovenance->table_epoch == mapped->provenance.table_epoch &&\n"
        "\t\tprovenance->calibration_handle ==\n"
        "\t\t\tmapped->identity.calibration_handle &&\n"
        "\t\tprovenance->calibration_handle ==\n"
        "\t\t\tmapped->provenance.calibration_handle;\n"
        "}\n\n"
        "int mt6797_dvfsp_vendor_provider_match_state(\n"
        "\tconst struct mt6797_dvfsp_vendor_provider_snapshot *mapped,\n"
        "\tconst struct mt6797_dvfsp_state_snapshot *snapshot,\n"
        "\tconst struct mt6797_dvfsp_state_owner_identity *identity)\n"
        "{\n"
        "\tif (!mapped || !snapshot || !identity)\n"
        "\t\treturn -EINVAL;\n"
        "\tif (mapped->abi != MT6797_DVFSP_VENDOR_PROVIDER_ABI ||\n"
        "\t    mapped->mapped_mask != MT6797_DVFSP_VENDOR_PROVIDER_MAPPED_ALL ||\n"
        "\t    mapped->unavailable_mask !=\n"
        "\t\tMT6797_DVFSP_VENDOR_PROVIDER_UNAVAILABLE_REGISTRATION ||\n"
        "\t    !mapped->generation || !mapped->owner_handle ||\n"
        "\t    !mapped->transition_handle ||\n"
        "\t    mapped->identity.abi != MT6797_DVFSP_VENDOR_SOURCE_ABI ||\n"
        "\t    !mapped->identity.variant_id ||\n"
        "\t    !mapped->identity.table_epoch ||\n"
        "\t    !mapped->identity.calibration_handle ||\n"
        "\t    mapped->provenance.abi !=\n"
        "\t\tMT6797_DVFSP_VENDOR_SOURCE_PROVENANCE_ABI ||\n"
        "\t    !mapped->provenance.variant_id ||\n"
        "\t    !mapped->provenance.table_epoch ||\n"
        "\t    !mapped->provenance.calibration_handle ||\n"
        "\t    snapshot->abi != MT6797_DVFSP_STATE_OWNER_ABI ||\n"
        "\t    !snapshot->generation || !snapshot->owner_handle ||\n"
        "\t    !snapshot->transition_handle || !snapshot->cluster_mask ||\n"
        "\t    snapshot->cluster_mask & ~MT6797_DVFSP_STATE_CLUSTER_MASK ||\n"
        "\t    snapshot->provenance.abi !=\n"
        "\t\tMT6797_DVFSP_STATE_PROVENANCE_ABI ||\n"
        "\t    snapshot->provenance.source_mask !=\n"
        "\t\tMT6797_DVFSP_STATE_PROVENANCE_SOURCE_ALL ||\n"
        "\t    identity->abi != MT6797_DVFSP_STATE_OWNER_IDENTITY_ABI ||\n"
        "\t    identity->resource_mask !=\n"
        "\t\tMT6797_DVFSP_STATE_OWNER_RESOURCE_ALL ||\n"
        "\t    identity->cpu_pll_backend !=\n"
        "\t\tMT6797_DVFSP_STATE_OWNER_BACKEND_MCUMIXED_DVFSP ||\n"
        "\t    identity->big_cluster_backend !=\n"
        "\t\tMT6797_DVFSP_STATE_OWNER_BACKEND_BIGIDVFS_SMCCC ||\n"
        "\t    identity->reserved || !identity->owner_handle ||\n"
        "\t    !identity->transition_handle ||\n"
        "\t    identity->provenance.abi !=\n"
        "\t\tMT6797_DVFSP_STATE_PROVENANCE_ABI ||\n"
        "\t    identity->provenance.source_mask !=\n"
        "\t\tMT6797_DVFSP_STATE_PROVENANCE_SOURCE_ALL)\n"
        "\t\treturn -EPROTO;\n"
        "\tif (mapped->generation != snapshot->generation ||\n"
        "\t    mapped->provenance.source_generation != mapped->generation ||\n"
        "\t    mapped->owner_handle != snapshot->owner_handle ||\n"
        "\t    mapped->owner_handle != identity->owner_handle ||\n"
        "\t    mapped->owner_handle != mapped->provenance.owner_handle ||\n"
        "\t    mapped->transition_handle != snapshot->transition_handle ||\n"
        "\t    mapped->transition_handle != identity->transition_handle ||\n"
        "\t    mapped->transition_handle !=\n"
        "\t\tmapped->provenance.transition_handle ||\n"
        "\t    !mt6797_dvfsp_vendor_provider_state_provenance_equal(\n"
        "\t\t&snapshot->provenance, &identity->provenance) ||\n"
        "\t    !mt6797_dvfsp_vendor_provider_provenance_matches(mapped,\n"
        "\t\t&snapshot->provenance))\n"
        "\t\treturn -EAGAIN;\n"
        "\treturn 0;\n"
        "}\n"
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_provider_match_state);\n\n"
        "int mt6797_dvfsp_vendor_provider_bridge_init(\n",
    )

    replace_once(
        provider_test,
        "static void mt6797_dvfsp_vendor_provider_rejects_identity_or_ids(\n",
        "static void mt6797_dvfsp_vendor_provider_matches_state_identity(\n"
        "\tstruct kunit *test)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped;\n"
        "\tstruct mt6797_dvfsp_state_snapshot snapshot = {\n"
        "\t\t.abi = MT6797_DVFSP_STATE_OWNER_ABI,\n"
        "\t\t.cluster_mask = MT6797_DVFSP_STATE_CLUSTER_MASK,\n"
        "\t\t.generation = 9,\n"
        "\t\t.owner_handle = 0x67970023,\n"
        "\t\t.transition_handle = 0x67970022,\n"
        "\t\t.provenance = {\n"
        "\t\t\t.abi = MT6797_DVFSP_STATE_PROVENANCE_ABI,\n"
        "\t\t\t.source_mask =\n"
        "\t\t\t\tMT6797_DVFSP_STATE_PROVENANCE_SOURCE_ALL,\n"
        "\t\t\t.variant_id = 7,\n"
        "\t\t\t.table_epoch = 0x100000002ULL,\n"
        "\t\t\t.calibration_handle = 0x6797abcdULL,\n"
        "\t\t},\n"
        "\t};\n"
        "\tstruct mt6797_dvfsp_state_owner_identity identity = {\n"
        "\t\t.abi = MT6797_DVFSP_STATE_OWNER_IDENTITY_ABI,\n"
        "\t\t.resource_mask = MT6797_DVFSP_STATE_OWNER_RESOURCE_ALL,\n"
        "\t\t.cpu_pll_backend =\n"
        "\t\t\tMT6797_DVFSP_STATE_OWNER_BACKEND_MCUMIXED_DVFSP,\n"
        "\t\t.big_cluster_backend =\n"
        "\t\t\tMT6797_DVFSP_STATE_OWNER_BACKEND_BIGIDVFS_SMCCC,\n"
        "\t\t.owner_handle = 0x67970023,\n"
        "\t\t.transition_handle = 0x67970022,\n"
        "\t};\n\n"
        "\tmapped = kunit_kzalloc(test, sizeof(*mapped), GFP_KERNEL);\n"
        "\tKUNIT_ASSERT_NOT_NULL(test, mapped);\n"
        "\tmt6797_dvfsp_vendor_provider_test_fill();\n"
        "\tKUNIT_ASSERT_EQ(test, mt6797_dvfsp_vendor_provider_map(\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_snapshot,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_identity,\n"
        "\t\t&mt6797_dvfsp_vendor_provider_test_provenance,\n"
        "\t\t0x67970023, 0x67970022, mapped), 0);\n"
        "\tidentity.provenance = snapshot.provenance;\n"
        "\tKUNIT_EXPECT_EQ(test, mt6797_dvfsp_vendor_provider_match_state(\n"
        "\t\tmapped, &snapshot, &identity), 0);\n"
        "\tsnapshot.generation++;\n"
        "\tKUNIT_EXPECT_EQ(test, mt6797_dvfsp_vendor_provider_match_state(\n"
        "\t\tmapped, &snapshot, &identity), -EAGAIN);\n"
        "\tsnapshot.generation--;\n"
        "\tidentity.provenance.table_epoch++;\n"
        "\tKUNIT_EXPECT_EQ(test, mt6797_dvfsp_vendor_provider_match_state(\n"
        "\t\tmapped, &snapshot, &identity), -EAGAIN);\n"
        "}\n\n"
        "static void mt6797_dvfsp_vendor_provider_rejects_identity_or_ids(\n",
    )
    replace_once(
        provider_test,
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_maps_fields),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_identity_or_ids),\n",
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_maps_fields),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_matches_state_identity),\n"
        "\tKUNIT_CASE(mt6797_dvfsp_vendor_provider_rejects_identity_or_ids),\n",
    )

    replace_once(
        owner_header,
        "#define MT6797_DVFSP_VENDOR_OWNER_ABI\t1\n",
        "#define MT6797_DVFSP_VENDOR_OWNER_ABI\t2\n",
    )
    replace_once(
        owner_header,
        " * This object owns only callback composition and provider lifetime. It does\n"
        " * not register a handoff owner or perform a state-changing operation.\n",
        " * This object owns callback composition, provider lifetime, and explicit\n"
        " * read-only handoff registration. It performs no state-changing operation.\n",
    )
    replace_once(
        owner_header,
        "\tstruct mt6797_dvfsp_vendor_provider_bridge provider_bridge;\n"
        "\tconst struct mt6797_dvfsp_vendor_runtime_ops *writer_runtime_ops;\n",
        "\tstruct mt6797_dvfsp_vendor_provider_bridge provider_bridge;\n"
        "\tstruct mt6797_dvfsp_handoff *state_handoff;\n"
        "\tconst struct mt6797_dvfsp_vendor_runtime_ops *writer_runtime_ops;\n",
    )
    replace_once(
        owner_header,
        "\tbool bound;\n\tbool writer_registered;\n};\n",
        "\tbool bound;\n\tbool writer_registered;\n"
        "\tbool state_registered;\n};\n",
    )
    replace_once(
        owner_header,
        "int mt6797_dvfsp_vendor_owner_unregister_writer(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner);\n\n"
        "/* Bind the external vendor lifecycle adapter before its probe can run. */\n",
        "int mt6797_dvfsp_vendor_owner_unregister_writer(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner);\n\n"
        "/* Register only a complete, matching read-only state view. */\n"
        "int mt6797_dvfsp_vendor_owner_register_state(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner,\n"
        "\tstruct mt6797_dvfsp_handoff *handoff);\n\n"
        "/* Remove the state owner before the writer or source lifecycle. */\n"
        "int mt6797_dvfsp_vendor_owner_unregister_state(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner);\n\n"
        "/* Bind the external vendor lifecycle adapter before its probe can run. */\n",
    )

    replace_once(
        owner_source,
        "#include <linux/module.h>\n#include <linux/string.h>\n",
        "#include <linux/module.h>\n#include <linux/slab.h>\n"
        "#include <linux/string.h>\n",
    )
    replace_once(
        owner_source,
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_owner_register_writer);\n\n"
        "int mt6797_dvfsp_vendor_owner_unregister_writer(\n",
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_owner_register_writer);\n\n"
        "static int mt6797_dvfsp_vendor_owner_read_state(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner,\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *mapped,\n"
        "\tstruct mt6797_dvfsp_state_snapshot *snapshot,\n"
        "\tstruct mt6797_dvfsp_state_owner_identity *identity)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tmemset(mapped, 0, sizeof(*mapped));\n"
        "\tret = mt6797_dvfsp_vendor_provider_bridge_snapshot(\n"
        "\t\t&owner->provider_bridge, mapped);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\tmemset(snapshot, 0, sizeof(*snapshot));\n"
        "\tret = mt6797_dvfsp_calibrated_provider_snapshot(\n"
        "\t\t&owner->provider, snapshot);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\tret = mt6797_dvfsp_calibrated_provider_validate(\n"
        "\t\t&owner->provider, snapshot);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\tmemset(identity, 0, sizeof(*identity));\n"
        "\tret = mt6797_dvfsp_calibrated_provider_identify(\n"
        "\t\t&owner->provider, identity);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\treturn mt6797_dvfsp_vendor_provider_match_state(mapped, snapshot,\n"
        "\t\tidentity);\n"
        "}\n\n"
        "int mt6797_dvfsp_vendor_owner_register_state(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner,\n"
        "\tstruct mt6797_dvfsp_handoff *handoff)\n"
        "{\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *before_mapped;\n"
        "\tstruct mt6797_dvfsp_vendor_provider_snapshot *after_mapped;\n"
        "\tstruct mt6797_dvfsp_state_snapshot *before_snapshot;\n"
        "\tstruct mt6797_dvfsp_state_snapshot *after_snapshot;\n"
        "\tstruct mt6797_dvfsp_state_owner_identity before_identity;\n"
        "\tstruct mt6797_dvfsp_state_owner_identity after_identity;\n"
        "\tstruct mt6797_dvfsp_state_owner_identity registered_identity;\n"
        "\tint rollback_ret;\n"
        "\tint ret;\n\n"
        "\tif (!owner || !handoff)\n\t\treturn -EINVAL;\n"
        "\tif (!owner->bound || !owner->writer_integration_bound ||\n"
        "\t    !owner->writer_registered || !owner->provider_bridge.initialized)\n"
        "\t\treturn -ENODEV;\n"
        "\tif (owner->state_registered)\n\t\treturn -EBUSY;\n"
        "\tbefore_mapped = kzalloc(sizeof(*before_mapped), GFP_KERNEL);\n"
        "\tafter_mapped = kzalloc(sizeof(*after_mapped), GFP_KERNEL);\n"
        "\tbefore_snapshot = kzalloc(sizeof(*before_snapshot), GFP_KERNEL);\n"
        "\tafter_snapshot = kzalloc(sizeof(*after_snapshot), GFP_KERNEL);\n"
        "\tif (!before_mapped || !after_mapped || !before_snapshot ||\n"
        "\t    !after_snapshot) {\n"
        "\t\tret = -ENOMEM;\n"
        "\t\tgoto out_free;\n"
        "\t}\n"
        "\tret = mt6797_dvfsp_vendor_owner_read_state(owner, before_mapped,\n"
        "\t\tbefore_snapshot, &before_identity);\n"
        "\tif (ret)\n\t\tgoto out_free;\n"
        "\tret = mt6797_dvfsp_state_owner_arbitration_register(handoff,\n"
        "\t\t&owner->provider.arbitration);\n"
        "\tif (ret)\n\t\tgoto out_free;\n"
        "\towner->state_handoff = handoff;\n"
        "\towner->state_registered = true;\n"
        "\tmemset(&registered_identity, 0, sizeof(registered_identity));\n"
        "\tret = mt6797_dvfsp_handoff_state_owner_identity(handoff,\n"
        "\t\t&registered_identity);\n"
        "\tif (!ret && memcmp(&before_identity, &registered_identity,\n"
        "\t\t\t   sizeof(before_identity)))\n"
        "\t\tret = -EAGAIN;\n"
        "\tif (ret)\n\t\tgoto out_rollback;\n"
        "\tret = mt6797_dvfsp_vendor_owner_read_state(owner, after_mapped,\n"
        "\t\tafter_snapshot, &after_identity);\n"
        "\tif (!ret && (memcmp(before_mapped, after_mapped,\n"
        "\t\t\t    sizeof(*before_mapped)) ||\n"
        "\t\t    memcmp(before_snapshot, after_snapshot,\n"
        "\t\t\t    sizeof(*before_snapshot)) ||\n"
        "\t\t    memcmp(&before_identity, &after_identity,\n"
        "\t\t\t    sizeof(before_identity))))\n"
        "\t\tret = -EAGAIN;\n"
        "\tif (!ret)\n\t\tgoto out_free;\n"
        "\nout_rollback:\n"
        "\trollback_ret = mt6797_dvfsp_state_owner_arbitration_unregister(\n"
        "\t\thandoff, &owner->provider.arbitration);\n"
        "\tif (rollback_ret) {\n"
        "\t\tret = rollback_ret;\n"
        "\t\tgoto out_free;\n"
        "\t}\n"
        "\towner->state_handoff = NULL;\n"
        "\towner->state_registered = false;\n\n"
        "out_free:\n"
        "\tkfree(after_snapshot);\n"
        "\tkfree(before_snapshot);\n"
        "\tkfree(after_mapped);\n"
        "\tkfree(before_mapped);\n"
        "\treturn ret;\n"
        "}\n"
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_owner_register_state);\n\n"
        "int mt6797_dvfsp_vendor_owner_unregister_state(\n"
        "\tstruct mt6797_dvfsp_vendor_owner *owner)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tif (!owner || !owner->bound)\n\t\treturn -EINVAL;\n"
        "\tif (!owner->state_registered || !owner->state_handoff)\n"
        "\t\treturn -ENOENT;\n"
        "\tret = mt6797_dvfsp_state_owner_arbitration_unregister(\n"
        "\t\towner->state_handoff, &owner->provider.arbitration);\n"
        "\tif (ret)\n\t\treturn ret;\n"
        "\towner->state_handoff = NULL;\n"
        "\towner->state_registered = false;\n"
        "\treturn 0;\n"
        "}\n"
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_vendor_owner_unregister_state);\n\n"
        "int mt6797_dvfsp_vendor_owner_unregister_writer(\n",
    )
    replace_once(
        owner_source,
        "\tif (!owner || !owner->bound || !owner->writer_registered)\n"
        "\t\treturn -EINVAL;\n"
        "\tops = owner->ops.writer_registration_ops;\n",
        "\tif (!owner || !owner->bound || !owner->writer_registered)\n"
        "\t\treturn -EINVAL;\n"
        "\tif (owner->state_registered)\n\t\treturn -EBUSY;\n"
        "\tops = owner->ops.writer_registration_ops;\n",
    )
    replace_once(
        owner_source,
        "\tif (owner->writer_registered || owner->ops.writer_registration_ops !=\n"
        "\t\t&mt6797_dvfsp_vendor_owner_integration_registration_ops ||\n",
        "\tif (owner->writer_registered || owner->state_registered ||\n"
        "\t    owner->ops.writer_registration_ops !=\n"
        "\t\t&mt6797_dvfsp_vendor_owner_integration_registration_ops ||\n",
    )
    replace_once(
        owner_source,
        "\tif (owner->writer_registered || owner->writer_integration_bound)\n"
        "\t\treturn -EBUSY;\n",
        "\tif (owner->writer_registered || owner->writer_integration_bound ||\n"
        "\t    owner->state_registered)\n"
        "\t\treturn -EBUSY;\n",
    )

    replace_once(
        owner_test,
        "\tstruct mt6797_dvfsp_vendor_source_identity_observation observation;\n\n"
        "\tmt6797_dvfsp_vendor_test_init_devices(&devices);\n",
        "\tstruct mt6797_dvfsp_vendor_source_identity_observation observation;\n"
        "\tstruct mt6797_dvfsp_handoff *handoff;\n\n"
        "\tmt6797_dvfsp_vendor_test_init_devices(&devices);\n",
    )
    replace_once(
        owner_test,
        "\tKUNIT_EXPECT_TRUE(test, owner.source.initialized);\n"
        "\tKUNIT_ASSERT_EQ(test,\n"
        "\t\tmt6797_dvfsp_vendor_source_identity_observation(&owner.source,\n",
        "\tKUNIT_EXPECT_TRUE(test, owner.source.initialized);\n"
        "\thandoff = kunit_kzalloc(test, sizeof(*handoff), GFP_KERNEL);\n"
        "\tKUNIT_ASSERT_NOT_NULL(test, handoff);\n"
        "\tKUNIT_EXPECT_EQ(test, mt6797_dvfsp_vendor_owner_register_state(\n"
        "\t\t&owner, handoff), -EOPNOTSUPP);\n"
        "\tKUNIT_EXPECT_FALSE(test, owner.state_registered);\n"
        "\tKUNIT_EXPECT_PTR_EQ(test, owner.state_handoff, NULL);\n"
        "\tKUNIT_ASSERT_EQ(test,\n"
        "\t\tmt6797_dvfsp_vendor_source_identity_observation(&owner.source,\n",
    )


PHASES = {
    "widen-epoch": widen_epoch,
    "preserve-snapshot-attribution": preserve_snapshot_attribution,
    "require-vendor-provenance": require_vendor_provenance,
    "bound-vendor-bridge-storage": bound_vendor_bridge_storage,
    "register-validated-owner": register_validated_owner,
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
