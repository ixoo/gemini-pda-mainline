#!/usr/bin/env python3
"""Apply the candidate-only same-boot CPU9 controller source changes."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from textwrap import dedent


HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "7f7a9b28c7410d6f623cd4116f2cedc83ddcc6baf66a9f51f1e83b10c057e334",
    "drivers/soc/mediatek/Makefile":
        "488032814a2266cd7472284f9302c6d22d5cec5b03b7f98bc37548484334690d",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "db846135f220023259655abf79cad85ff8cc5d4c8e6d01a9808de758fb961315",
    "include/linux/soc/mediatek/mt6797-a72-cpu9-binder.h":
        "dcdf69df33bd304b5461478059f8f966384f0527d44657fe87d427f272163f15",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h":
        "752965d98c0492733f396b90f4c518670cd6676d8f22f8b78d7f272da25f1a0f",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c":
        "d97f09e29f321403e3ab7e2200a5cfdd08460263606e79bb9db1537a083ccf85",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c":
        "819a52066baef3aa128c51445f004cb76006daef745b83b731fc6625b3f211b4",
}
NEW_PATHS = (
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-internal.h",
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c",
    "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller-test.c",
)

KCONFIG = dedent("""\
    config MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER
    \tbool "MediaTek MT6797 same-boot CPU9 admission controller"
    \tdepends on MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER
    \tdepends on MTK_MT6797_A72_CPU9_BINDER
    \tdefault n
    \thelp
    \t  Extend the exact one-shot userspace admission trigger so it runs the
    \t  unchanged CPU8 controller, requires its terminal membership proof,
    \t  derives and publishes one retained-cluster CPU9 transaction, stages
    \t  the CPU9 binder, and makes one synchronous add_cpu(9) request.

    \t  CPU8 failure or any missing proof prevents CPU9 derivation and request.
    \t  CPU9 failure retains CPU8, P27, the provider, and the cluster until
    \t  fixed watchdog recovery. No CPU_OFF, retry, cluster reacquisition,
    \t  automatic probe action, or second trigger exists. If unsure, say N.

    config MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER_KUNIT_TEST
    \tbool "KUnit tests for the MT6797 same-boot CPU9 controller"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER
    \tdefault n
    \thelp
    \t  Exercise exact same-task CPU8 proof, CPU9 derive/publish/prepare/request
    \t  order, every stop boundary, one-shot closure, and zero CPU_OFF/retry
    \t  behavior through injected operations only.

    \t  No physical CPU, retained-RAM, watchdog, regulator, clock, MMIO, SMC,
    \t  storage, reboot, or device action is performed.

    """)

BINDER_DIAGNOSTIC = dedent("""\
    #define MT6797_A72_CPU9_BINDER_DIAGNOSTIC_ABI 1U

    struct mt6797_a72_cpu9_binder_diagnostic {
    \tu32 abi;
    \tu32 lifecycle;
    \tu32 terminal;
    \tu32 last_stage;
    \ts32 stage_errno;
    \ts32 checkpoint_errno;
    \tu32 attempted;
    \tu32 cpu_on_accepted;
    \tu32 membership_published;
    \tu32 cpu8_online;
    \tu32 cpu9_online;
    \tu32 cpu_requests;
    \tu32 cpu_off_requests;
    \tu32 retries;
    \tu32 checkpoints;
    \tu32 terminal_commits;
    \tu32 retained_mask;
    \tu32 prepared;
    \tu32 boot_claimed;
    \tu64 cpu8_attempt_id;
    \tu64 cpu9_attempt_id;
    \tu32 p30e_prepare_attempted;
    \ts32 p30e_prepare_ret;
    \tu32 p30e_arm_attempted;
    \ts32 p30e_arm_ret;
    \tu32 p30e_armed;
    \tu32 p30e_readback_attempted;
    \ts32 p30e_readback_ret;
    };

    """)

BINDER_DIAGNOSTIC_SOURCE = dedent("""\
    static void mt6797_a72_cpu9_binder_fill_diagnostic(
    \tconst struct mt6797_a72_cpu9_binder *binder,
    \tstruct mt6797_a72_cpu9_binder_diagnostic *snapshot)
    {
    \tconst struct mt6797_a72_cpu9_executor_result *result = &binder->result;

    \tmemset(snapshot, 0, sizeof(*snapshot));
    \tsnapshot->abi = MT6797_A72_CPU9_BINDER_DIAGNOSTIC_ABI;
    \tsnapshot->lifecycle = atomic_read_acquire(&binder->executor.lifecycle);
    \tsnapshot->terminal = result->terminal;
    \tsnapshot->last_stage = result->last_stage;
    \tsnapshot->stage_errno = result->stage_errno;
    \tsnapshot->checkpoint_errno = result->checkpoint_errno;
    \tsnapshot->attempted = result->attempted;
    \tsnapshot->cpu_on_accepted = result->cpu_on_accepted;
    \tsnapshot->membership_published = result->membership_published;
    \tsnapshot->cpu8_online = result->cpu8_online;
    \tsnapshot->cpu9_online = result->cpu9_online;
    \tsnapshot->cpu_requests = result->cpu_requests;
    \tsnapshot->cpu_off_requests = result->cpu_off_requests;
    \tsnapshot->retries = result->retries;
    \tsnapshot->checkpoints = result->checkpoints;
    \tsnapshot->terminal_commits = result->terminal_commits;
    \tsnapshot->retained_mask = result->retained_mask;
    \tsnapshot->prepared = atomic_read_acquire(&binder->prepared);
    \tsnapshot->boot_claimed = atomic_read_acquire(&binder->boot_claimed);
    \tsnapshot->cpu8_attempt_id = binder->request.cpu8_attempt_id;
    \tsnapshot->cpu9_attempt_id = binder->request.cpu9_attempt_id;
    \tsnapshot->p30e_prepare_attempted = binder->p30e_prepare_attempted;
    \tsnapshot->p30e_prepare_ret = binder->p30e_prepare_ret;
    \tsnapshot->p30e_arm_attempted = binder->p30e_arm_attempted;
    \tsnapshot->p30e_arm_ret = binder->p30e_arm_ret;
    \tsnapshot->p30e_armed = binder->p30e_armed;
    \tsnapshot->p30e_readback_attempted = binder->p30e_readback_attempted;
    \tsnapshot->p30e_readback_ret = binder->p30e_readback_ret;
    }

    int mt6797_a72_cpu9_binder_diagnostic_snapshot(
    \tstruct mt6797_a72_cpu9_binder_diagnostic *snapshot)
    {
    \tint ret = 0;

    \tif (!snapshot)
    \t\treturn -EINVAL;
    \tmemset(snapshot, 0, sizeof(*snapshot));
    \tmutex_lock(&mt6797_a72_cpu9_binder_lock);
    \tif (atomic_read_acquire(&mt6797_a72_cpu9_binder.prepared))
    \t\tmt6797_a72_cpu9_binder_fill_diagnostic(
    \t\t\t&mt6797_a72_cpu9_binder, snapshot);
    \telse
    \t\tret = -EAGAIN;
    \tmutex_unlock(&mt6797_a72_cpu9_binder_lock);
    \treturn ret;
    }

    """)

CPU9_INTEGRATION = dedent("""\
    #if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER)
    static int mt6797_a72_admission_cpu8_proof(
    \tvoid *context, struct mt6797_a72_cpu9_admission_cpu8_proof *proof)
    {
    \tstruct mt6797_a72_admission_controller *controller = context;
    \tstruct mt6797_a72_binder_diagnostic diagnostic;
    \tconst struct mt6797_a72_transaction *transaction =
    \t\t&controller->state.transaction;
    \tint ret;

    \tif (!proof)
    \t\treturn -EINVAL;
    \tmemset(proof, 0, sizeof(*proof));
    \tret = mt6797_a72_binder_diagnostic_snapshot(&diagnostic);
    \tif (ret)
    \t\treturn ret;
    \tif (atomic_read(&controller->state.consumed) != 1 ||
    \t    controller->state.cpu_requests != 1 ||
    \t    controller->state.operation_ret || !transaction->valid ||
    \t    transaction->identity.operation !=
    \t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||
    \t    transaction->identity.target_cpu != 8 ||
    \t    !transaction->identity.generation ||
    \t    diagnostic.abi != MT6797_A72_BINDER_DIAGNOSTIC_ABI ||
    \t    diagnostic.lifecycle != MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL ||
    \t    diagnostic.terminal != MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF ||
    \t    diagnostic.last_stage != MT6797_A72_TRANSITION_STAGE_MEMBERSHIP ||
    \t    diagnostic.stage_errno || diagnostic.rollback_errno ||
    \t    diagnostic.checkpoint_errno || !diagnostic.attempted ||
    \t    !diagnostic.watchdog_armed || !diagnostic.p27_owned ||
    \t    diagnostic.rollback_mask ||
    \t    diagnostic.retained_mask != MT6797_A72_CPU9_RETAINED_REQUIRED ||
    \t    !cpu_online(8) || cpu_online(9))
    \t\treturn -EPROTO;
    \tproof->attempt_id = transaction->identity.generation;
    \tproof->cpu_requests = controller->state.cpu_requests;
    \tproof->lifecycle_terminal = true;
    \tproof->terminal_exact = true;
    \tproof->membership_published = true;
    \tproof->p27_retained = true;
    \tproof->provider_retained = true;
    \tproof->cpu8_online = true;
    \treturn 0;
    }

    static int mt6797_a72_admission_derive_cpu9(
    \tvoid *context, const struct arm64_late_cpu_ready_token *ready,
    \tstruct mt6797_a72_transaction *transaction, u32 *derive_stage)
    {
    \t(void)context;
    \treturn mt6797_a72_membership_derive_cpu9_diagnostic(
    \t\tready, transaction, derive_stage);
    }

    static int mt6797_a72_admission_publish_cpu9(
    \tvoid *context, struct mt6797_a72_transaction *transaction)
    {
    \t(void)context;
    \treturn mt6797_a72_membership_publish_cpu9(transaction);
    }

    static int mt6797_a72_admission_prepare_cpu9(
    \tvoid *context, const struct mt6797_a72_cpu9_executor_request *request)
    {
    \t(void)context;
    \treturn mt6797_a72_cpu9_binder_prepare(request);
    }

    static const struct mt6797_a72_cpu9_admission_ops
    mt6797_a72_cpu9_admission_production_ops = {
    \t.run_cpu8 = mt6797_a72_admission_run_cpu8,
    \t.cpu8_proof = mt6797_a72_admission_cpu8_proof,
    \t.ready_token = mt6797_a72_admission_ready_token,
    \t.derive_cpu9 = mt6797_a72_admission_derive_cpu9,
    \t.publish_cpu9 = mt6797_a72_admission_publish_cpu9,
    \t.prepare_cpu9 = mt6797_a72_admission_prepare_cpu9,
    \t.add_cpu = mt6797_a72_admission_add_cpu,
    };
    #endif

    static int mt6797_a72_admission_execute(void *context)
    {
    #if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER)
    \tstruct mt6797_a72_admission_controller *controller = context;

    \treturn mt6797_a72_cpu9_admission_run(
    \t\t&controller->cpu9, &mt6797_a72_cpu9_admission_production_ops,
    \t\tcontroller);
    #else
    \treturn mt6797_a72_admission_run_cpu8(context);
    #endif
    }

    """)

CPU9_STATUS_HELPERS = dedent("""\
    static u32 mt6797_a72_admission_cpu9_requests(
    \tconst struct mt6797_a72_admission_controller *controller)
    {
    #if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER)
    \treturn READ_ONCE(controller->cpu9.cpu9_requests);
    #else
    \t(void)controller;
    \treturn 0;
    #endif
    }

    static ssize_t mt6797_a72_admission_cpu9_status(
    \tstruct mt6797_a72_admission_controller *controller, char *buf,
    \tssize_t len)
    {
    #if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER)
    \tstruct mt6797_a72_cpu9_binder_diagnostic diagnostic;
    \tint ret;

    \tret = mt6797_a72_cpu9_binder_diagnostic_snapshot(&diagnostic);
    \treturn sysfs_emit_at(
    \t\tbuf, len,
    \t\t" cpu9_controller_consumed=%d cpu9_operation_ret=%d "
    \t\t"cpu9_failure_stage=%u cpu9_derive_stage=%u "
    \t\t"cpu9_binder_snapshot_ret=%d cpu9_abi=%u "
    \t\t"cpu9_lifecycle=%u cpu9_terminal=%u cpu9_last_stage=%u "
    \t\t"cpu9_stage_errno=%d cpu9_checkpoint_errno=%d "
    \t\t"cpu9_attempted=%u cpu9_membership_published=%u "
    \t\t"cpu9_cpu_requests=%u cpu9_cpu_off_requests=%u "
    \t\t"cpu9_retries=%u cpu9_retained_mask=0x%x\\n",
    \t\tatomic_read(&controller->cpu9.consumed),
    \t\tREAD_ONCE(controller->cpu9.operation_ret),
    \t\tREAD_ONCE(controller->cpu9.failure_stage),
    \t\tREAD_ONCE(controller->cpu9.derive_stage), ret,
    \t\tdiagnostic.abi, diagnostic.lifecycle, diagnostic.terminal,
    \t\tdiagnostic.last_stage, diagnostic.stage_errno,
    \t\tdiagnostic.checkpoint_errno, diagnostic.attempted,
    \t\tdiagnostic.membership_published, diagnostic.cpu_requests,
    \t\tdiagnostic.cpu_off_requests, diagnostic.retries,
    \t\tdiagnostic.retained_mask);
    #else
    \t(void)controller;
    \treturn sysfs_emit_at(buf, len, " cpu9_controller=disabled\\n");
    #endif
    }

    """)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"parent source is absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"parent source changed: {relative}: {actual}")
    for relative in NEW_PATHS:
        if (root / relative).exists():
            raise SystemExit(f"new CPU9 controller path already exists: {relative}")


def copy_new(root: Path, relative: str) -> None:
    source = TEMPLATES / Path(relative).name
    target = root / relative
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"template is absent or unsafe: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def apply(root: Path) -> None:
    root = root.resolve()
    validate_parent(root)
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    replace_once(
        kconfig,
        "\t  CPU9, CPU_OFF, retry, reboot, and storage operations remain absent.\n"
        "\t  If unsure, say N.\n\n"
        "config MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST\n",
        "\t  CPU_OFF, retry, reboot, and storage operations remain absent. CPU9\n"
        "\t  remains absent unless the separate same-boot successor is selected.\n"
        "\t  If unsure, say N.\n\n" + KCONFIG +
        "config MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST\n",
    )
    makefile = root / "drivers/soc/mediatek/Makefile"
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER) += "
        "mt6797-a72-admission-controller.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER) += "
        "mt6797-a72-admission-controller.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER) += "
        "mt6797-a72-cpu9-admission-controller.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER_KUNIT_TEST) += "
        "mt6797-a72-cpu9-admission-controller-test.o\n",
    )

    public = root / "include/linux/soc/mediatek/mt6797-a72-cpu9-binder.h"
    replace_once(
        public,
        "struct mt6797_a72_cpu9_executor_request;\n\n",
        "struct mt6797_a72_cpu9_executor_request;\n\n" + BINDER_DIAGNOSTIC,
    )
    replace_once(
        public,
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER)\n"
        "int mt6797_a72_cpu9_binder_prepare(\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER)\n"
        "int mt6797_a72_cpu9_binder_diagnostic_snapshot(\n"
        "\tstruct mt6797_a72_cpu9_binder_diagnostic *snapshot);\n"
        "int mt6797_a72_cpu9_binder_prepare(\n",
    )
    replace_once(
        public,
        "#else\n"
        "static inline int mt6797_a72_cpu9_binder_prepare(\n",
        "#else\n"
        "static inline int mt6797_a72_cpu9_binder_diagnostic_snapshot(\n"
        "\tstruct mt6797_a72_cpu9_binder_diagnostic *snapshot)\n"
        "{\n"
        "\tif (snapshot)\n"
        "\t\t*snapshot = (struct mt6797_a72_cpu9_binder_diagnostic){};\n"
        "\treturn -EOPNOTSUPP;\n"
        "}\n\n"
        "static inline int mt6797_a72_cpu9_binder_prepare(\n",
    )

    internal = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-internal.h"
    replace_once(
        internal,
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST)\n"
        "void mt6797_a72_cpu9_binder_test_init(\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST)\n"
        "void mt6797_a72_cpu9_binder_test_diagnostic(\n"
        "\tconst struct mt6797_a72_cpu9_binder *binder,\n"
        "\tstruct mt6797_a72_cpu9_binder_diagnostic *snapshot);\n"
        "void mt6797_a72_cpu9_binder_test_init(\n",
    )
    binder = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    replace_once(
        binder,
        "int mt6797_a72_cpu9_binder_prepare(\n",
        BINDER_DIAGNOSTIC_SOURCE +
        "int mt6797_a72_cpu9_binder_prepare(\n",
    )
    replace_once(
        binder,
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST)\n"
        "void mt6797_a72_cpu9_binder_test_init(\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST)\n"
        "void mt6797_a72_cpu9_binder_test_diagnostic(\n"
        "\tconst struct mt6797_a72_cpu9_binder *binder,\n"
        "\tstruct mt6797_a72_cpu9_binder_diagnostic *snapshot)\n"
        "{\n"
        "\tmt6797_a72_cpu9_binder_fill_diagnostic(binder, snapshot);\n"
        "}\n\n"
        "void mt6797_a72_cpu9_binder_test_init(\n",
    )
    tests = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder-test.c"
    replace_once(
        tests,
        "\tstruct mt6797_cpu9_binder_test_state state;\n"
        "\tstruct mt6797_a72_cpu9_binder binder;\n"
        "\tint ret;\n\n"
        "\tmt6797_cpu9_binder_test_reset(&binder, &state);\n",
        "\tstruct mt6797_cpu9_binder_test_state state;\n"
        "\tstruct mt6797_a72_cpu9_binder_diagnostic diagnostic;\n"
        "\tstruct mt6797_a72_cpu9_binder binder;\n"
        "\tint ret;\n\n"
        "\tmt6797_cpu9_binder_test_reset(&binder, &state);\n",
    )
    replace_once(
        tests,
        "\tret = mt6797_a72_cpu9_binder_test_complete(&binder, 9, CPUHP_ONLINE);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);\n",
        "\tret = mt6797_a72_cpu9_binder_test_complete(&binder, 9, CPUHP_ONLINE);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\tmt6797_a72_cpu9_binder_test_diagnostic(&binder, &diagnostic);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.abi,\n"
        "\t\t\t(u32)MT6797_A72_CPU9_BINDER_DIAGNOSTIC_ABI);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.lifecycle,\n"
        "\t\t\t(u32)MT6797_A72_CPU9_LIFECYCLE_TERMINAL);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.terminal,\n"
        "\t\t\t(u32)MT6797_A72_CPU9_ONLINE_PROOF);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.cpu_requests, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.cpu_off_requests, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.retries, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.cpu8_attempt_id,\n"
        "\t\t\trequest.cpu8_attempt_id);\n"
        "\tKUNIT_EXPECT_EQ(test, diagnostic.cpu9_attempt_id,\n"
        "\t\t\trequest.cpu9_attempt_id);\n"
        "\tKUNIT_EXPECT_EQ(test, state.ledger_begin_calls, 1U);\n",
    )

    admission = root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    replace_once(
        admission,
        "#include <linux/soc/mediatek/mt6797-a72-binder.h>\n",
        "#include <linux/soc/mediatek/mt6797-a72-binder.h>\n"
        "#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>\n",
    )
    replace_once(
        admission,
        "#include \"mt6797-a72-admission-controller-internal.h\"\n"
        "#include \"mt6797-a72-physical-source-observer-internal.h\"\n",
        "#include \"mt6797-a72-admission-controller-internal.h\"\n"
        "#include \"mt6797-a72-cpu9-admission-controller-internal.h\"\n"
        "#include \"mt6797-a72-physical-source-observer-internal.h\"\n"
        "#include \"mt6797-a72-transition-internal.h\"\n",
    )
    replace_once(
        admission,
        "\tstruct mt6797_a72_admission_controller_state state;\n"
        "\tstruct mt6797_a72_admission_trigger_state trigger;\n",
        "\tstruct mt6797_a72_admission_controller_state state;\n"
        "\tstruct mt6797_a72_cpu9_admission_state cpu9;\n"
        "\tstruct mt6797_a72_admission_trigger_state trigger;\n",
    )
    replace_once(
        admission,
        "static int mt6797_a72_admission_execute(void *context)\n"
        "{\n"
        "\tstruct mt6797_a72_admission_controller *controller = context;\n"
        "\tint ret;\n\n"
        "\tret = mt6797_a72_admission_prepare(controller);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\treturn mt6797_a72_admission_run(&controller->state,\n"
        "\t\t\t\t\t&mt6797_a72_admission_production_ops,\n"
        "\t\t\t\t\tcontroller);\n"
        "}\n\n",
        "static int mt6797_a72_admission_run_cpu8(void *context)\n"
        "{\n"
        "\tstruct mt6797_a72_admission_controller *controller = context;\n"
        "\tint ret;\n\n"
        "\tret = mt6797_a72_admission_prepare(controller);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n"
        "\treturn mt6797_a72_admission_run(&controller->state,\n"
        "\t\t\t\t\t&mt6797_a72_admission_production_ops,\n"
        "\t\t\t\t\tcontroller);\n"
        "}\n\n" + CPU9_INTEGRATION,
    )
    replace_once(
        admission,
        "static ssize_t status_show(struct device *dev, struct device_attribute *attr,\n",
        CPU9_STATUS_HELPERS +
        "static ssize_t status_show(struct device *dev, struct device_attribute *attr,\n",
    )
    replace_once(
        admission,
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"cpu_requests=%u cpu9_requests=0 \",\n"
        "\t\t\t     READ_ONCE(controller->state.cpu_requests));\n",
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"cpu_requests=%u cpu9_requests=%u \",\n"
        "\t\t\t     READ_ONCE(controller->state.cpu_requests),\n"
        "\t\t\t     mt6797_a72_admission_cpu9_requests(controller));\n",
    )
    replace_once(
        admission,
        "\treturn len + sysfs_emit_at(buf, len,\n"
        "\t\t\t\t   \"p30e_target_entry_sp=0x%llx p30e_target_sequence=%u p30e_controller_sequence=%u\\n\",\n"
        "\t\t\t\t   (unsigned long long)diagnostic.p30e_target_entry_sp,\n"
        "\t\t\t\t   diagnostic.p30e_target_sequence,\n"
        "\t\t\t\t   diagnostic.p30e_controller_sequence);\n",
        "\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t     \"p30e_target_entry_sp=0x%llx p30e_target_sequence=%u p30e_controller_sequence=%u\",\n"
        "\t\t\t     (unsigned long long)diagnostic.p30e_target_entry_sp,\n"
        "\t\t\t     diagnostic.p30e_target_sequence,\n"
        "\t\t\t     diagnostic.p30e_controller_sequence);\n"
        "\treturn len + mt6797_a72_admission_cpu9_status(controller, buf, len);\n",
    )
    replace_once(
        admission,
        "\tdev_info(dev, MT6797_A72_ADMISSION_LIVE_TAG\n"
        "\t\t \" state=terminal operation_ret=%d core_consumed=%d entry_trace_ret=%d terminal_trace_ret=%d failure_stage=%u derive_stage=%u requests=%u/0/0 retries=0\\n\",\n"
        "\t\t READ_ONCE(controller->trigger.operation_ret),\n"
        "\t\t atomic_read(&controller->state.consumed),\n"
        "\t\t READ_ONCE(controller->state.trace_entry_ret),\n"
        "\t\t READ_ONCE(controller->state.trace_ret),\n"
        "\t\t READ_ONCE(controller->state.failure_stage),\n"
        "\t\t READ_ONCE(controller->state.derive_stage),\n"
        "\t\t READ_ONCE(controller->state.cpu_requests));\n",
        "\tdev_info(dev, MT6797_A72_ADMISSION_LIVE_TAG\n"
        "\t\t \" state=terminal operation_ret=%d core_consumed=%d entry_trace_ret=%d terminal_trace_ret=%d failure_stage=%u derive_stage=%u requests=%u/%u/0 retries=0\\n\",\n"
        "\t\t READ_ONCE(controller->trigger.operation_ret),\n"
        "\t\t atomic_read(&controller->state.consumed),\n"
        "\t\t READ_ONCE(controller->state.trace_entry_ret),\n"
        "\t\t READ_ONCE(controller->state.trace_ret),\n"
        "\t\t READ_ONCE(controller->state.failure_stage),\n"
        "\t\t READ_ONCE(controller->state.derive_stage),\n"
        "\t\t READ_ONCE(controller->state.cpu_requests),\n"
        "\t\t mt6797_a72_admission_cpu9_requests(controller));\n",
    )
    replace_once(
        admission,
        "\tmt6797_a72_admission_state_init(&controller->state);\n"
        "\tmt6797_a72_admission_trigger_state_init(&controller->trigger);\n",
        "\tmt6797_a72_admission_state_init(&controller->state);\n"
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER)\n"
        "\tmt6797_a72_cpu9_admission_state_init(&controller->cpu9);\n"
        "#endif\n"
        "\tmt6797_a72_admission_trigger_state_init(&controller->trigger);\n",
    )
    replace_once(
        admission,
        "MODULE_DESCRIPTION(\"MT6797 candidate-only one-shot CPU8 admission controller\");\n",
        "MODULE_DESCRIPTION(\"MT6797 candidate-only one-shot A72 admission controller\");\n",
    )
    for relative in NEW_PATHS:
        copy_new(root, relative)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root)
