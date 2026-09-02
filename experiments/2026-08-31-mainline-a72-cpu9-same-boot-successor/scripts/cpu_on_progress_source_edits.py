#!/usr/bin/env python3
"""Apply the exact post-0478 CPU9 CPU_ON substage diagnostic."""

from __future__ import annotations

from pathlib import Path


PARENT_HASHES = {
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h":
        "8d66245215f05e67b81a7107320460a4a98a2263228aa09d6fc12c4fa14c49dd",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c":
        "68cba6b174e5e26d3f5d59a5855ef9a8f70f0802d0b9f38b02921508d147d490",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c":
        "a92e56ffedbb63b72069cff2474feced5da7fe29531095f4700d7a76cfbbacc9",
    "fs/pstore/Kconfig":
        "95082f5a20b0c4bf1311ee2d02bf069c74704f1d36ef8fdb3d6e70fe26263b52",
    "fs/pstore/gemini_cpu9_progress_ledger.c":
        "646ffe743066e57b3b28d155844cef028912d4af3e3f5512125080ffb6029afd",
    "fs/pstore/gemini_cpu9_progress_ledger_internal.h":
        "d1923ea07dd3c15a4786d8d88249f7faacfa8e519550053437a60158a06107f7",
    "fs/pstore/gemini_cpu9_progress_ledger_test.c":
        "f715e092c6105675c07b2dcc1482a85399cde1e9e7f15dbf06070123b14a4fbd",
    "include/linux/gemini_cpu9_progress_ledger.h":
        "b6a1a8a5ece70855d9b126f2f033c02b929fd33f12ad04bfea572c26570903a7",
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"CPU_ON progress anchor changed: {path}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root: Path) -> None:
    header = root / "include/linux/gemini_cpu9_progress_ledger.h"
    replace_once(
        header,
        "enum gemini_cpu9_progress_stage {\n"
        "\tGEMINI_CPU9_PROGRESS_CPU8_PROOF = 1,\n"
        "\tGEMINI_CPU9_PROGRESS_READY_TOKEN,\n"
        "\tGEMINI_CPU9_PROGRESS_DERIVE,\n"
        "\tGEMINI_CPU9_PROGRESS_PUBLISH,\n"
        "\tGEMINI_CPU9_PROGRESS_PREPARE,\n"
        "\tGEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH,\n"
        "\tGEMINI_CPU9_PROGRESS_BINDER_ENTRY,\n"
        "\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER,\n"
        "\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN,\n"
        "\tGEMINI_CPU9_PROGRESS_ADD_CPU_RETURN,\n"
        "};",
        "enum gemini_cpu9_progress_stage {\n"
        "\tGEMINI_CPU9_PROGRESS_CPU8_PROOF = 1,\n"
        "\tGEMINI_CPU9_PROGRESS_READY_TOKEN,\n"
        "\tGEMINI_CPU9_PROGRESS_DERIVE,\n"
        "\tGEMINI_CPU9_PROGRESS_PUBLISH,\n"
        "\tGEMINI_CPU9_PROGRESS_PREPARE,\n"
        "\tGEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH,\n"
        "\tGEMINI_CPU9_PROGRESS_BINDER_ENTRY,\n"
        "\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER,\n"
        "\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN,\n"
        "\tGEMINI_CPU9_PROGRESS_ADD_CPU_RETURN,\n"
        "};\n\n"
        "enum gemini_cpu9_cpu_on_progress_stage {\n"
        "\tGEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE = 1,\n"
        "\tGEMINI_CPU9_CPU_ON_PROGRESS_MEMBERSHIP_BEGIN,\n"
        "\tGEMINI_CPU9_CPU_ON_PROGRESS_P30E_ARM,\n"
        "\tGEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT,\n"
        "};",
    )
    replace_once(
        header,
        "int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id, u32 stage);",
        "int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id, u32 stage);\n"
        "int gemini_cpu9_cpu_on_progress_checkpoint(u64 cpu9_attempt_id,\n"
        "\t\t\t\t\t     u32 phase, u32 stage);",
    )
    replace_once(
        header,
        "static inline int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id,\n"
        "\t\t\t\t\t\t  u32 stage)\n"
        "{\n"
        "\treturn -EOPNOTSUPP;\n"
        "}",
        "static inline int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id,\n"
        "\t\t\t\t\t\t  u32 stage)\n"
        "{\n"
        "\treturn -EOPNOTSUPP;\n"
        "}\n\n"
        "static inline int\n"
        "gemini_cpu9_cpu_on_progress_checkpoint(u64 cpu9_attempt_id, u32 phase,\n"
        "\t\t\t\t\tu32 stage)\n"
        "{\n"
        "\treturn -EOPNOTSUPP;\n"
        "}",
    )

    internal = root / "fs/pstore/gemini_cpu9_progress_ledger_internal.h"
    replace_once(
        internal,
        "struct gemini_cpu9_progress_owner {\n"
        "\tstruct gemini_transition_ledger_owner ledger;\n"
        "\tbool attempted;\n"
        "};",
        "struct gemini_cpu9_progress_owner {\n"
        "\tstruct gemini_transition_ledger_owner ledger;\n"
        "\tbool attempted;\n"
        "};\n\n"
        "struct gemini_cpu9_cpu_on_progress_owner {\n"
        "\tstruct gemini_transition_ledger_owner ledger;\n"
        "\tbool attempted;\n"
        "};",
    )
    replace_once(
        internal,
        "int cpu9_progress_owner_checkpoint(\n"
        "\tstruct gemini_cpu9_progress_owner *owner,\n"
        "\tconst struct gemini_transition_ledger_ops *ops, void *context,\n"
        "\tu64 cpu8_attempt_id, u32 stage);",
        "int cpu9_progress_owner_checkpoint(\n"
        "\tstruct gemini_cpu9_progress_owner *owner,\n"
        "\tconst struct gemini_transition_ledger_ops *ops, void *context,\n"
        "\tu64 cpu8_attempt_id, u32 stage);\n"
        "int cpu9_cpu_on_progress_owner_begin(\n"
        "\tstruct gemini_cpu9_cpu_on_progress_owner *owner,\n"
        "\tconst struct gemini_transition_ledger_ops *cpu9_ops,\n"
        "\tvoid *cpu9_context,\n"
        "\tconst struct gemini_transition_ledger_ops *progress_ops,\n"
        "\tvoid *progress_context, u64 cpu9_attempt_id);\n"
        "int cpu9_cpu_on_progress_owner_checkpoint(\n"
        "\tstruct gemini_cpu9_cpu_on_progress_owner *owner,\n"
        "\tconst struct gemini_transition_ledger_ops *ops, void *context,\n"
        "\tu64 cpu9_attempt_id, u32 phase, u32 stage);",
    )

    ledger = root / "fs/pstore/gemini_cpu9_progress_ledger.c"
    replace_once(
        ledger,
        "#define GEMINI_CPU9_PROGRESS_BASE \\\n"
        "\t(GEMINI_CPU9_PROGRESS_CPU8_BASE + 2 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE)\n"
        "#define GEMINI_CPU9_PROGRESS_RESERVE_SIZE 0x000e0000ULL",
        "#define GEMINI_CPU9_TRANSITION_BASE \\\n"
        "\t(GEMINI_CPU9_PROGRESS_CPU8_BASE + GEMINI_TRANSITION_LEDGER_SLOT_SIZE)\n"
        "#define GEMINI_CPU9_PROGRESS_BASE \\\n"
        "\t(GEMINI_CPU9_PROGRESS_CPU8_BASE + 2 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE)\n"
        "#define GEMINI_CPU9_CPU_ON_PROGRESS_BASE \\\n"
        "\t(GEMINI_CPU9_PROGRESS_CPU8_BASE + 3 * GEMINI_TRANSITION_LEDGER_SLOT_SIZE)\n"
        "#define GEMINI_CPU9_PROGRESS_RESERVE_SIZE 0x000e0000ULL",
    )
    cpu_on_owner = r'''
static int cpu9_cpu_on_progress_validate_cpu9(
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu9_attempt_id)
{
	struct gemini_transition_ledger_record latest;
	u32 copy = 0;

	if (ops->read(context, 0) !=
		    GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE ||
	    ops->read(context, 1) != GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES ||
	    ops->read(context, 2) != GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES)
		return -ENODATA;
	if (!gemini_transition_ledger_read_latest(ops, context, &latest, &copy))
		return -EBADMSG;
	if (latest.attempt_id != cpu9_attempt_id)
		return -EACCES;
	if (latest.phase != GEMINI_TRANSITION_LEDGER_BEFORE ||
	    latest.stage != GEMINI_CPU9_LEDGER_CPU_ON || latest.terminal)
		return -EPERM;
	return 0;
}

int cpu9_cpu_on_progress_owner_begin(
	struct gemini_cpu9_cpu_on_progress_owner *owner,
	const struct gemini_transition_ledger_ops *cpu9_ops,
	void *cpu9_context,
	const struct gemini_transition_ledger_ops *progress_ops,
	void *progress_context, u64 cpu9_attempt_id)
{
	int ret;

	if (!owner || !cpu9_ops || !cpu9_ops->read || !progress_ops ||
	    !progress_ops->read || !cpu9_attempt_id)
		return -EINVAL;
	if (owner->attempted)
		return -EALREADY;
	owner->attempted = true;
	ret = cpu9_cpu_on_progress_validate_cpu9(
		cpu9_ops, cpu9_context, cpu9_attempt_id);
	if (ret)
		return ret;
	if (!cpu9_progress_lane_empty(progress_ops, progress_context))
		return progress_ops->read(progress_context, 0) ==
				GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&
		       progress_ops->read(progress_context, 1) ==
				GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES &&
		       progress_ops->read(progress_context, 2) ==
				GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES ?
			-EALREADY : -EUCLEAN;
	ret = gemini_transition_ledger_owner_begin(
		&owner->ledger, progress_ops, progress_context, cpu9_attempt_id);
	if (ret)
		return ret;
	return gemini_transition_ledger_owner_checkpoint(
		&owner->ledger, progress_ops, progress_context, cpu9_attempt_id,
		GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE, 0);
}

int cpu9_cpu_on_progress_owner_checkpoint(
	struct gemini_cpu9_cpu_on_progress_owner *owner,
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu9_attempt_id, u32 phase, u32 stage)
{
	int ret;

	if (!owner || phase < GEMINI_TRANSITION_LEDGER_BEFORE ||
	    phase > GEMINI_TRANSITION_LEDGER_AFTER ||
	    stage < GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE ||
	    stage > GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT ||
	    (phase == GEMINI_TRANSITION_LEDGER_BEFORE &&
	     stage == GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE))
		return -EINVAL;
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner->ledger, ops, context, cpu9_attempt_id, phase, stage, 0);
	if (!ret && phase == GEMINI_TRANSITION_LEDGER_AFTER &&
	    stage == GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT) {
		owner->ledger.active = false;
		owner->ledger.sealed = true;
	}
	return ret;
}
'''
    replace_once(
        ledger,
        "static bool gemini_cpu9_progress_exact_dt(void)",
        cpu_on_owner + "\nstatic bool gemini_cpu9_progress_exact_dt(void)",
    )
    replace_once(
        ledger,
        "static struct gemini_cpu9_progress_owner gemini_cpu9_progress_owner;\n"
        "static void __iomem *gemini_cpu9_progress_slot;",
        "static struct gemini_cpu9_progress_owner gemini_cpu9_progress_owner;\n"
        "static void __iomem *gemini_cpu9_progress_slot;\n"
        "static struct gemini_cpu9_cpu_on_progress_owner\n"
        "\tgemini_cpu9_cpu_on_progress_owner;\n"
        "static void __iomem *gemini_cpu9_cpu_on_progress_slot;",
    )
    public_checkpoint = r'''
int gemini_cpu9_cpu_on_progress_checkpoint(u64 cpu9_attempt_id, u32 phase,
					   u32 stage)
{
	void __iomem *cpu9_slot;
	void __iomem *progress_slot;
	int ret;

	mutex_lock(&gemini_cpu9_progress_lock);
	if (!gemini_cpu9_cpu_on_progress_owner.attempted) {
		if (phase != GEMINI_TRANSITION_LEDGER_BEFORE ||
		    stage != GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE) {
			ret = -EINVAL;
			goto out_unlock;
		}
		if (!gemini_cpu9_progress_exact_dt()) {
			ret = -ENODEV;
			goto out_unlock;
		}
		cpu9_slot = ioremap_wc(GEMINI_CPU9_TRANSITION_BASE,
				       GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
		if (!cpu9_slot) {
			ret = -ENOMEM;
			goto out_unlock;
		}
		progress_slot = ioremap_wc(GEMINI_CPU9_CPU_ON_PROGRESS_BASE,
					   GEMINI_TRANSITION_LEDGER_SLOT_SIZE);
		if (!progress_slot) {
			ret = -ENOMEM;
			goto out_unmap_cpu9;
		}
		ret = cpu9_cpu_on_progress_owner_begin(
			&gemini_cpu9_cpu_on_progress_owner,
			&gemini_cpu9_progress_mmio_ops, cpu9_slot,
			&gemini_cpu9_progress_mmio_ops, progress_slot,
			cpu9_attempt_id);
		if (ret)
			iounmap(progress_slot);
		else
			gemini_cpu9_cpu_on_progress_slot = progress_slot;
out_unmap_cpu9:
		iounmap(cpu9_slot);
		goto out_unlock;
	}
	if (!gemini_cpu9_cpu_on_progress_slot) {
		ret = -EALREADY;
		goto out_unlock;
	}
	ret = cpu9_cpu_on_progress_owner_checkpoint(
		&gemini_cpu9_cpu_on_progress_owner,
		&gemini_cpu9_progress_mmio_ops,
		gemini_cpu9_cpu_on_progress_slot, cpu9_attempt_id, phase, stage);
	if (ret || (phase == GEMINI_TRANSITION_LEDGER_AFTER &&
		    stage == GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT)) {
		iounmap(gemini_cpu9_cpu_on_progress_slot);
		gemini_cpu9_cpu_on_progress_slot = NULL;
	}
out_unlock:
	mutex_unlock(&gemini_cpu9_progress_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_cpu9_cpu_on_progress_checkpoint);
'''
    replace_once(
        ledger,
        "MODULE_DESCRIPTION(\"Gemini CPU9 pre-ledger retained progress ledger\");",
        public_checkpoint +
        "\nMODULE_DESCRIPTION(\"Gemini CPU9 retained progress ledgers\");",
    )

    kconfig = root / "fs/pstore/Kconfig"
    replace_once(
        kconfig,
        "\t  request, watchdog, SMC, cluster effect, reset, storage, or boot policy.\n",
        "\t  request, watchdog, SMC, cluster effect, reset, storage, or boot policy.\n"
        "\n"
        "\t  Also expose eight ordered before/after boundaries in the fourth\n"
        "\t  record around CPU9 P30E prepare, membership begin, P30E arm, and\n"
        "\t  the existing CPU boot callback. This independent lane requires\n"
        "\t  record 1 at exact BEFORE CPU_ON and adds no effect or request.\n",
    )

    binder_internal = (
        root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h"
    )
    replace_once(
        binder_internal,
        "\tint (*progress_checkpoint)(u64 cpu8_attempt_id, u32 stage);",
        "\tint (*progress_checkpoint)(u64 cpu8_attempt_id, u32 stage);\n"
        "\tint (*cpu_on_progress_checkpoint)(u64 cpu9_attempt_id, u32 phase,\n"
        "\t\t\t\t\t  u32 stage);",
    )

    binder = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    replace_once(
        binder,
        "\treturn ops && ops->progress_checkpoint && ops->ledger_begin &&",
        "\treturn ops && ops->progress_checkpoint &&\n"
        "\t       ops->cpu_on_progress_checkpoint && ops->ledger_begin &&",
    )
    replace_once(
        binder,
        "\t\t.progress_checkpoint = gemini_cpu9_progress_checkpoint,",
        "\t\t.progress_checkpoint = gemini_cpu9_progress_checkpoint,\n"
        "\t\t.cpu_on_progress_checkpoint =\n"
        "\t\t\tgemini_cpu9_cpu_on_progress_checkpoint,",
    )
    old_cpu_on = r'''static int mt6797_a72_cpu9_binder_cpu_on(void *context, unsigned int cpu)
{
	struct mt6797_a72_cpu9_binder *binder = context;
	int ret;

	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !binder->cpu_boot)
		return -EINVAL;
	binder->p30e_prepare_attempted = true;
	binder->p30e_prepare_ret = binder->backend->p30e_prepare(
		&binder->transaction, &binder->p30e_handoff);
	if (binder->p30e_prepare_ret)
		return binder->p30e_prepare_ret;
	ret = binder->backend->membership_begin_cpu_on(&binder->transaction);
	if (ret)
		return ret;
	binder->p30e_arm_attempted = true;
	binder->p30e_arm_ret =
		binder->backend->p30e_arm(cpu, &binder->p30e_handoff);
	if (binder->p30e_arm_ret)
		return binder->p30e_arm_ret;
	binder->p30e_armed = true;
	ret = binder->cpu_boot(cpu);
	if (ret)
		mt6797_a72_cpu9_binder_readback_once(binder, cpu);
	return ret;
}
'''
    new_cpu_on = r'''static int mt6797_a72_cpu9_binder_cpu_on(void *context, unsigned int cpu)
{
	struct mt6797_a72_cpu9_binder *binder = context;
	int ret;

	if (cpu != MT6797_A72_CPU9_EXECUTOR_CPU9 || !binder->cpu_boot)
		return -EINVAL;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE);
	if (ret)
		return ret;
	binder->p30e_prepare_attempted = true;
	binder->p30e_prepare_ret = binder->backend->p30e_prepare(
		&binder->transaction, &binder->p30e_handoff);
	if (binder->p30e_prepare_ret)
		return binder->p30e_prepare_ret;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE);
	if (ret)
		return ret;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_CPU_ON_PROGRESS_MEMBERSHIP_BEGIN);
	if (ret)
		return ret;
	ret = binder->backend->membership_begin_cpu_on(&binder->transaction);
	if (ret)
		return ret;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_CPU_ON_PROGRESS_MEMBERSHIP_BEGIN);
	if (ret)
		return ret;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_CPU_ON_PROGRESS_P30E_ARM);
	if (ret)
		return ret;
	binder->p30e_arm_attempted = true;
	binder->p30e_arm_ret =
		binder->backend->p30e_arm(cpu, &binder->p30e_handoff);
	if (binder->p30e_arm_ret)
		return binder->p30e_arm_ret;
	binder->p30e_armed = true;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_CPU_ON_PROGRESS_P30E_ARM);
	if (ret)
		return ret;
	ret = binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT);
	if (ret)
		return ret;
	ret = binder->cpu_boot(cpu);
	if (ret) {
		mt6797_a72_cpu9_binder_readback_once(binder, cpu);
		return ret;
	}
	return binder->backend->cpu_on_progress_checkpoint(
		binder->request.cpu9_attempt_id, GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT);
}
'''
    replace_once(binder, old_cpu_on, new_cpu_on)

    tests = root / "fs/pstore/gemini_cpu9_progress_ledger_test.c"
    cpu_on_tests = r'''
static int cpu9_progress_test_seed_cpu9(
	struct cpu9_progress_test_state *state, u64 attempt_id)
{
	struct gemini_transition_ledger_owner owner = {};
	int ret;

	cpu9_progress_test_empty(state);
	ret = gemini_transition_ledger_owner_begin(
		&owner, &cpu9_progress_test_ops, state, attempt_id);
	if (ret)
		return ret;
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, state, attempt_id,
		GEMINI_TRANSITION_LEDGER_BEFORE, GEMINI_CPU9_LEDGER_PRESTATE, 0);
	if (ret)
		return ret;
	ret = gemini_transition_ledger_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, state, attempt_id,
		GEMINI_TRANSITION_LEDGER_AFTER, GEMINI_CPU9_LEDGER_PRESTATE, 0);
	if (ret)
		return ret;
	return gemini_transition_ledger_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, state, attempt_id,
		GEMINI_TRANSITION_LEDGER_BEFORE, GEMINI_CPU9_LEDGER_CPU_ON, 0);
}

static void cpu9_cpu_on_progress_sequence_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu9;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_cpu_on_progress_owner owner = {};
	struct gemini_transition_ledger_record latest;
	u32 stage;

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu9(&cpu9, 2), 0);
	cpu9_progress_test_empty(&progress);
	KUNIT_ASSERT_EQ(test, cpu9_cpu_on_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu9,
		&cpu9_progress_test_ops, &progress, 2), 0);
	for (stage = GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE;
	     stage <= GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT; stage++) {
		KUNIT_ASSERT_EQ(test, cpu9_cpu_on_progress_owner_checkpoint(
			&owner, &cpu9_progress_test_ops, &progress, 2,
			GEMINI_TRANSITION_LEDGER_AFTER, stage), 0);
		if (stage != GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT)
			KUNIT_ASSERT_EQ(test,
				cpu9_cpu_on_progress_owner_checkpoint(
					&owner, &cpu9_progress_test_ops, &progress, 2,
					GEMINI_TRANSITION_LEDGER_BEFORE, stage + 1), 0);
	}
	KUNIT_ASSERT_TRUE(test, cpu9_progress_test_latest(&progress, &latest));
	KUNIT_EXPECT_EQ(test, latest.generation, 8U);
	KUNIT_EXPECT_EQ(test, latest.phase,
			(u32)GEMINI_TRANSITION_LEDGER_AFTER);
	KUNIT_EXPECT_EQ(test, latest.stage,
			(u32)GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT);
	KUNIT_EXPECT_EQ(test, progress.writes, 82U);
	KUNIT_EXPECT_TRUE(test, owner.ledger.sealed);
}

static void cpu9_cpu_on_progress_gates_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu9;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_cpu_on_progress_owner owner = {};

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu9(&cpu9, 2), 0);
	memset(&progress, 0xff, sizeof(progress));
	KUNIT_EXPECT_EQ(test, cpu9_cpu_on_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu9,
		&cpu9_progress_test_ops, &progress, 3), -EACCES);
	memset(&owner, 0, sizeof(owner));
	KUNIT_ASSERT_EQ(test, cpu9_cpu_on_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu9,
		&cpu9_progress_test_ops, &progress, 2), 0);
	KUNIT_EXPECT_EQ(test, progress.words[0],
			GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE);
	KUNIT_EXPECT_EQ(test, cpu9_cpu_on_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu9,
		&cpu9_progress_test_ops, &progress, 2), -EALREADY);
}

static void cpu9_cpu_on_progress_ordering_test(struct kunit *test)
{
	struct cpu9_progress_test_state cpu9;
	struct cpu9_progress_test_state progress;
	struct gemini_cpu9_cpu_on_progress_owner owner = {};

	KUNIT_ASSERT_EQ(test, cpu9_progress_test_seed_cpu9(&cpu9, 2), 0);
	cpu9_progress_test_empty(&progress);
	KUNIT_ASSERT_EQ(test, cpu9_cpu_on_progress_owner_begin(
		&owner, &cpu9_progress_test_ops, &cpu9,
		&cpu9_progress_test_ops, &progress, 2), 0);
	KUNIT_EXPECT_EQ(test, cpu9_cpu_on_progress_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, &progress, 2,
		GEMINI_TRANSITION_LEDGER_BEFORE,
		GEMINI_CPU9_CPU_ON_PROGRESS_MEMBERSHIP_BEGIN), -EINVAL);
	KUNIT_EXPECT_EQ(test, cpu9_cpu_on_progress_owner_checkpoint(
		&owner, &cpu9_progress_test_ops, &progress, 3,
		GEMINI_TRANSITION_LEDGER_AFTER,
		GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE), -EACCES);
}
'''
    replace_once(
        tests,
        "static struct kunit_case cpu9_progress_cases[] = {",
        cpu_on_tests + "\nstatic struct kunit_case cpu9_progress_cases[] = {",
    )
    replace_once(
        tests,
        "\tKUNIT_CASE(cpu9_progress_ordering_test),\n\t{ }",
        "\tKUNIT_CASE(cpu9_progress_ordering_test),\n"
        "\tKUNIT_CASE(cpu9_cpu_on_progress_sequence_test),\n"
        "\tKUNIT_CASE(cpu9_cpu_on_progress_gates_test),\n"
        "\tKUNIT_CASE(cpu9_cpu_on_progress_ordering_test),\n"
        "\t{ }",
    )

    binder_tests = (
        root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c"
    )
    replace_once(
        binder_tests,
        "\tMT6797_CPU9_BINDER_FAIL_PROGRESS,",
        "\tMT6797_CPU9_BINDER_FAIL_PROGRESS,\n"
        "\tMT6797_CPU9_BINDER_FAIL_CPU_ON_PROGRESS,",
    )
    replace_once(
        binder_tests,
        "\tu32 fail_progress_stage;",
        "\tu32 fail_progress_stage;\n"
        "\tunsigned int cpu_on_progress_checkpoint_calls;\n"
        "\tu32 cpu_on_progress_phases[8];\n"
        "\tu32 cpu_on_progress_stages[8];\n"
        "\tu32 fail_cpu_on_progress_call;",
    )
    test_callback = r'''
static int mt6797_cpu9_binder_test_cpu_on_progress_checkpoint(
	u64 cpu9_attempt_id, u32 phase, u32 stage)
{
	struct mt6797_cpu9_binder_test_state *state =
		mt6797_cpu9_binder_test_active;
	unsigned int call = state->cpu_on_progress_checkpoint_calls;

	if (call < ARRAY_SIZE(state->cpu_on_progress_stages)) {
		state->cpu_on_progress_phases[call] = phase;
		state->cpu_on_progress_stages[call] = stage;
	}
	state->cpu_on_progress_checkpoint_calls++;
	if (cpu9_attempt_id !=
	    mt6797_cpu9_binder_test_request().cpu9_attempt_id)
		return -EPROTO;
	return state->failure == MT6797_CPU9_BINDER_FAIL_CPU_ON_PROGRESS &&
	       state->fail_cpu_on_progress_call == call + 1 ? -EIO : 0;
}
'''
    replace_once(
        binder_tests,
        "static int mt6797_cpu9_binder_test_ledger_begin(u64 cpu8_attempt_id,",
        test_callback +
        "\nstatic int mt6797_cpu9_binder_test_ledger_begin(u64 cpu8_attempt_id,",
    )
    replace_once(
        binder_tests,
        "\t\t.progress_checkpoint =\n"
        "\t\t\tmt6797_cpu9_binder_test_progress_checkpoint,",
        "\t\t.progress_checkpoint =\n"
        "\t\t\tmt6797_cpu9_binder_test_progress_checkpoint,\n"
        "\t\t.cpu_on_progress_checkpoint =\n"
        "\t\t\tmt6797_cpu9_binder_test_cpu_on_progress_checkpoint,",
    )
    success_checks = r'''
	KUNIT_EXPECT_EQ(test, state.cpu_on_progress_checkpoint_calls, 8U);
	KUNIT_EXPECT_EQ(test, state.cpu_on_progress_phases[0],
			(u32)GEMINI_TRANSITION_LEDGER_BEFORE);
	KUNIT_EXPECT_EQ(test, state.cpu_on_progress_stages[0],
			(u32)GEMINI_CPU9_CPU_ON_PROGRESS_P30E_PREPARE);
	KUNIT_EXPECT_EQ(test, state.cpu_on_progress_phases[7],
			(u32)GEMINI_TRANSITION_LEDGER_AFTER);
	KUNIT_EXPECT_EQ(test, state.cpu_on_progress_stages[7],
			(u32)GEMINI_CPU9_CPU_ON_PROGRESS_CPU_BOOT);
'''
    replace_once(
        binder_tests,
        "\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);",
        success_checks +
        "\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);",
    )
    progress_failure_test = r'''
static void mt6797_cpu9_binder_cpu_on_progress_failures_test(
	struct kunit *test)
{
	unsigned int failure_call;

	for (failure_call = 1; failure_call <= 8; failure_call++) {
		struct mt6797_a72_cpu9_executor_request request =
			mt6797_cpu9_binder_test_request();
		struct mt6797_cpu9_binder_test_state state;
		struct mt6797_a72_cpu9_binder binder;
		int ret;

		mt6797_cpu9_binder_test_reset(&binder, &state);
		state.failure = MT6797_CPU9_BINDER_FAIL_CPU_ON_PROGRESS;
		state.fail_cpu_on_progress_call = failure_call;
		KUNIT_ASSERT_EQ(test,
				mt6797_a72_cpu9_binder_test_prepare(&binder,
								    &request),
				0);
		ret = mt6797_a72_cpu9_binder_test_boot(
			&binder, 9, mt6797_cpu9_binder_test_cpu_boot);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test, state.cpu_on_progress_checkpoint_calls,
				failure_call);
		KUNIT_EXPECT_EQ(test, state.p30e_prepare_calls,
				failure_call >= 2 ? 1U : 0U);
		KUNIT_EXPECT_EQ(test, state.cpu_on_begin_calls,
				failure_call >= 4 ? 1U : 0U);
		KUNIT_EXPECT_EQ(test, state.p30e_arm_calls,
				failure_call >= 6 ? 1U : 0U);
		KUNIT_EXPECT_EQ(test, state.cpu_boot_calls,
				failure_call >= 8 ? 1U : 0U);
		KUNIT_EXPECT_EQ(test, binder.result.cpu_requests, 1U);
		KUNIT_EXPECT_EQ(test, binder.result.cpu_off_requests, 0U);
		KUNIT_EXPECT_EQ(test, binder.result.retries, 0U);
	}
}
'''
    replace_once(
        binder_tests,
        "static void mt6797_cpu9_binder_secondary_failure_test(struct kunit *test)",
        progress_failure_test +
        "\nstatic void mt6797_cpu9_binder_secondary_failure_test(struct kunit *test)",
    )
    replace_once(
        binder_tests,
        "\tKUNIT_CASE(mt6797_cpu9_binder_cpu_on_failures_test),",
        "\tKUNIT_CASE(mt6797_cpu9_binder_cpu_on_failures_test),\n"
        "\tKUNIT_CASE(mt6797_cpu9_binder_cpu_on_progress_failures_test),",
    )
