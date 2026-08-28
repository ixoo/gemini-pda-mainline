#!/usr/bin/env python3
"""Apply deterministic source-derived CPU8 admission edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "f04be5e5152ca1e88da4b1701b72d266e650e84d28f2de35e40cc5276509182a",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "5bc397338407ab63b263a01d5777da355086c1cfaf642926facff07e37e8d898",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "38a48b325c334a335800e98eadf095243e4f4673428769fe0780494005dc6502",
    "drivers/regulator/da9213-legacy-membership-test.c":
        "946aacfda2f9904a1f61fb10c73a39264aa8e53c790f1739cd28f11bf6d2d0c7",
    "arch/arm64/Kconfig":
        "69571f7b7d9e2a6dbd8d755fdc84d6ae82a8e7d44691ee1f4ff2b81272fc1b11",
    "arch/arm64/Kconfig.platforms":
        "1efe0dba4643b8697787fcc7fd8b2f47e235d2c91497683170ba578804509568",
    "arch/arm64/kernel/Makefile":
        "634ecce25eee183765606e99aa55bba686641e2922f3c6b867ec0a10ccf60e69",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"source path is not an exact file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"source hash changed: {relative}: {actual} != {expected}"
            )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"{path}: expected one anchor: {old.splitlines()[0]}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_header(path: Path) -> None:
    replace_once(
        path,
        " * immutable caller-supplied prestate record. A dormant P17/P18 ledger may\n",
        " * immutable owner-derived prestate record. A dormant P17/P18 ledger may\n",
    )
    replace_once(
        path,
        "#define MT6797_A72_A36_PRESTATE_ABI 1\n",
        "#define MT6797_A72_A36_PRESTATE_ABI 2\n",
    )
    declaration = (
        "int\n"
        "mt6797_a72_membership_begin_up(unsigned int cpu, enum cpuhp_state target,\n"
        "\t\t\t       u32 attempt,\n"
        "\t\t\t       const struct mt6797_a72_entry_snapshot *entry,\n"
        "\t\t\t       const struct arm64_late_cpu_ready_token *ready,\n"
        "\t\t\t       const struct mt6797_a72_a36_prestate *prestate,\n"
        "\t\t\t       struct mt6797_a72_transaction *transaction);\n"
    )
    replace_once(
        path,
        declaration,
        declaration +
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION)\n"
        "int mt6797_a72_membership_begin_cpu8_derived(\n"
        "\tconst struct mt6797_a72_direct_state_snapshot *direct,\n"
        "\tconst struct arm64_late_cpu_ready_token *ready,\n"
        "\tstruct mt6797_a72_transaction *transaction);\n"
        "#else\n"
        "static inline int mt6797_a72_membership_begin_cpu8_derived(\n"
        "\tconst struct mt6797_a72_direct_state_snapshot *direct,\n"
        "\tconst struct arm64_late_cpu_ready_token *ready,\n"
        "\tstruct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\t(void)direct;\n"
        "\t(void)ready;\n"
        "\tif (transaction)\n"
        "\t\tmemset(transaction, 0, sizeof(*transaction));\n"
        "\treturn -EOPNOTSUPP;\n"
        "}\n"
        "#endif\n",
    )


DERIVED_SOURCE = r'''
struct mt6797_a72_derived_workspace {
	struct mt6797_a72_a34_observation observation;
	struct mt6797_a72_entry_snapshot entry;
	struct mt6797_a72_a36_prestate prestate;
};

static struct mt6797_a72_derived_workspace a72_derived_workspace;

static void
mt6797_a72_derive_cpu8_entry(const struct mt6797_a72_direct_state_snapshot *direct,
			     struct mt6797_a72_entry_snapshot *entry)
{
	entry->members = direct->owner.members;
	entry->provider_state = direct->owner.provider_state;
	entry->online_mask = (direct->cpu8_online ? BIT(0) : 0) |
		(direct->cpu9_online ? BIT(1) : 0);
	entry->cpuhp_state_cpu8 = direct->cpu8_online ?
		CPUHP_ONLINE : CPUHP_OFFLINE;
	entry->cpuhp_state_cpu9 = direct->cpu9_online ?
		CPUHP_ONLINE : CPUHP_OFFLINE;
	entry->observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN;
	entry->flags = (direct->cpu8_present ? MT6797_A72_ENTRY_CPU8_PRESENT : 0) |
		(direct->cpu9_present ? MT6797_A72_ENTRY_CPU9_PRESENT : 0) |
		(direct->cpu8_possible ? MT6797_A72_ENTRY_CPU8_POSSIBLE : 0) |
		(direct->cpu9_possible ? MT6797_A72_ENTRY_CPU9_POSSIBLE : 0);
	entry->cpu8_mpidr = direct->cpu8_mpidr;
	entry->cpu9_mpidr = direct->cpu9_mpidr;
}

static void
mt6797_a72_derive_cpu8_prestate(const struct mt6797_a72_direct_state_snapshot *direct,
				const struct mt6797_a72_transaction *transaction,
				struct mt6797_a72_a36_prestate *prestate)
{
	prestate->abi = MT6797_A72_A36_PRESTATE_ABI;
	prestate->operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP;
	prestate->observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN;
	prestate->call_shape = MT6797_A72_A36_CALL_SHAPE_TWO_ARG;
	prestate->cpu8_online = direct->cpu8_online;
	prestate->cpu9_online = direct->cpu9_online;
	prestate->buckb_enabled = direct->source.provider.buckb_cont;
	prestate->buckb_vsel = direct->source.provider.vbuckb_b;
	prestate->spm_218 = direct->source.platform.spm_mp2_cpusys_pwr_con;
	prestate->spm_290 = direct->source.platform.spm_cpu_ext_buck_iso;
	prestate->toprgu_pwrap_reset =
		direct->source.platform.pwrap_reset_asserted;
	prestate->mp2_dcm = direct->source.platform.mp2_sync_dcm;
	prestate->protected_clock_valid =
		direct->source.clock.abi == MT6797_DVFSP_CLOCK_BACKEND_ABI &&
		direct->source.clock.sample_generation != 0;
	prestate->target_mpidr = direct->cpu8_mpidr;
	prestate->secondary_entry_pa = transaction->identity.cpu_on_entry_pa;
	prestate->generation = transaction->identity.generation;
	prestate->cookie = transaction->identity.cookie;
}

int mt6797_a72_membership_begin_cpu8_derived(
	const struct mt6797_a72_direct_state_snapshot *direct,
	const struct arm64_late_cpu_ready_token *ready,
	struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_derived_workspace *workspace = &a72_derived_workspace;
	int ret;

	if (!direct || !transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));

	mutex_lock(&a72_transition_lock);
	memset(workspace, 0, sizeof(*workspace));
	workspace->observation.abi = MT6797_A72_A34_ELIGIBILITY_ABI;
	workspace->observation.direct = *direct;
	workspace->observation.replay.abi = MT6797_A72_A34_REPLAY_ABI;
	workspace->observation.replay.valid = 1;
	workspace->observation.replay.proof =
		MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR;
	ret = mt6797_a72_a34_evaluate(&workspace->observation);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_cpu8_entry(direct, &workspace->entry);
	ret = mt6797_a72_membership_p31_consume_attempt(
		8, CPUHP_ONLINE, MT6797_A72_ATTEMPT_CPU8_UP,
		&workspace->entry);
	if (ret)
		goto out_clear;
	ret = mt6797_a72_membership_validate_entry(
		8, CPUHP_ONLINE, MT6797_A72_ATTEMPT_CPU8_UP,
		&workspace->entry);
	if (ret)
		goto out_clear;
	ret = mt6797_a72_membership_mint_up_token(
		8, CPUHP_ONLINE, MT6797_A72_ATTEMPT_CPU8_UP,
		&workspace->entry, ready, transaction);
	if (ret)
		goto out_clear;

	mt6797_a72_derive_cpu8_prestate(direct, transaction,
					&workspace->prestate);
	ret = mt6797_a72_membership_validate_up_prestate(
		transaction, &workspace->prestate);
	if (ret)
		goto reject_frozen;
	ret = mt6797_a72_membership_bind_a36_prestate(
		&transaction->identity, &workspace->prestate, transaction);
	if (ret)
		goto reject_frozen;
	goto out_clear;

reject_frozen:
	mt6797_a72_membership_reject_frozen(&transaction->identity);
	memset(transaction, 0, sizeof(*transaction));
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	mutex_unlock(&a72_transition_lock);
	return ret;
}

'''


def apply_source(path: Path) -> None:
    replace_once(
        path,
        " * immutable A36 prestate check. A dormant P17/P18 publication ledger may\n",
        " * immutable owner-derived A36 check. A dormant P17/P18 publication ledger may\n",
    )
    replace_once(
        path,
        "\t\t    prestate->da921x_page != MT6797_A72_A36_DA921X_PAGE ||\n",
        "\t\t    prestate->da921x_page ||\n",
    )
    replace_once(
        path,
        "\t\t    prestate->toprgu_pwrap_reset || prestate->mp2_dcm ||\n"
        "\t\t    prestate->secure_sentinels_stable != 1 ||\n"
        "\t\t    prestate->protected_clock_valid != 1 ||\n"
        "\t\t    prestate->pstore_console_available != 1 ||\n"
        "\t\t    prestate->watchdog_owned != 1 ||\n",
        "\t\t    prestate->toprgu_pwrap_reset || prestate->mp2_dcm ||\n"
        "\t\t    prestate->secure_sentinels_stable ||\n"
        "\t\t    prestate->protected_clock_valid != 1 ||\n"
        "\t\t    prestate->pstore_console_available ||\n"
        "\t\t    prestate->watchdog_owned ||\n",
    )
    replace_once(
        path,
        "\t\t    prestate->pstore_console_available ||\n"
        "\t\t    prestate->watchdog_owned != 1 ||\n",
        "\t\t    prestate->pstore_console_available ||\n"
        "\t\t    prestate->watchdog_owned ||\n",
    )
    anchor = (
        "int\n"
        "mt6797_a72_membership_begin_up(unsigned int cpu, enum cpuhp_state target,\n"
    )
    replace_once(
        path, anchor,
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION)\n" +
        DERIVED_SOURCE + "#endif\n\n" + anchor,
    )


def apply_production_kconfig(path: Path) -> None:
    anchor = "config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n"
    addition = (
        "config ARM64_MT6797_A72_DERIVED_ADMISSION\n"
        "\tbool \"Source-derived MT6797 CPU8 admission\"\n"
        "\tdepends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n"
        "\tdepends on ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n"
        "\thelp\n"
        "\t  Derive one CPU8 entry and A36 record from the exact composed\n"
        "\t  current-boot snapshot and immutable READY token. The owner\n"
        "\t  mints and binds its own identity; this option makes no CPU\n"
        "\t  request and performs no hardware operation.\n\n"
    )
    replace_once(path, anchor, addition + anchor)


def apply_fixture_repairs(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    repairs = 0
    for line in (
        "\t\t.watchdog_owned = 1,\n",
        "\t\tprestate.da921x_page = MT6797_A72_A36_DA921X_PAGE;\n",
        "\t\tprestate.secure_sentinels_stable = 1;\n",
        "\t\tprestate.pstore_console_available = 1;\n",
        "\t\t.secure_sentinels_stable = 1,\n",
        "\t\t.pstore_console_available = 1,\n",
    ):
        repairs += text.count(line)
        text = text.replace(line, "")
    page = "\t\t.da921x_page = MT6797_A72_A36_DA921X_PAGE,\n"
    repairs += text.count(page)
    text = text.replace(page, "")
    if repairs != 4:
        raise SystemExit(f"{path}: expected four obsolete A36 assertions")
    path.write_text(text, encoding="utf-8")


def apply_tests(root: Path, reference: Path) -> None:
    kconfig = root / "arch/arm64/Kconfig"
    owner_config = (
        "config ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST\n"
    )
    addition = (
        "config ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST\n"
        "\tbool \"KUnit tests for source-derived MT6797 CPU8 admission\"\n"
        "\tdepends on KUNIT=y\n"
        "\tdepends on HOTPLUG_CPU\n"
        "\tdepends on ARM64_MT6797_A72_P30_PROTOCOL_MODEL\n"
        "\tselect ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n"
        "\tselect ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n"
        "\tselect ARM64_MT6797_A72_DERIVED_ADMISSION\n"
        "\thelp\n"
        "\t  Derive the CPU8 entry and A36 record from one exact composed\n"
        "\t  current-boot snapshot and the immutable READY token. Exercise\n"
        "\t  source rejection, obsolete caller-assertion refusal, and the\n"
        "\t  one-shot owner edge without a CPU or hardware operation.\n\n"
    )
    replace_once(kconfig, owner_config, addition + owner_config)
    makefile = root / "arch/arm64/kernel/Makefile"
    owner_object = (
        "obj-$(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST) += "
        "mt6797_a72_membership_test.o\n"
    )
    replace_once(
        makefile,
        owner_object,
        owner_object +
        "obj-$(CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST) += "
        "mt6797_a72_derived_admission_test.o\n",
    )
    apply_fixture_repairs(
        root / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    )
    apply_fixture_repairs(
        root / "drivers/regulator/da9213-legacy-membership-test.c"
    )
    target = root / "arch/arm64/kernel/mt6797_a72_derived_admission_test.c"
    shutil.copyfile(reference, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("production", "tests"), required=True)
    parser.add_argument("--test-reference", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.stage == "production":
        validate_parent(root)
        apply_header(root / "arch/arm64/include/asm/mt6797_a72_membership.h")
        apply_source(root / "arch/arm64/kernel/mt6797_a72_membership.c")
        apply_production_kconfig(root / "arch/arm64/Kconfig.platforms")
    else:
        if not args.test_reference:
            raise SystemExit("--test-reference is required for tests")
        apply_tests(root, args.test_reference.resolve())


if __name__ == "__main__":
    main()
