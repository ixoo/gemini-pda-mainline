#!/usr/bin/env python3
"""Apply deterministic membership-owner repairs for the default-off binder."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "b43f9e1c8f9a98651a583917b15cd7968c12733b21c077c0eec076dea5b8447e",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "376ba674e7d9afc7be8bb89fef51bf0b3515704f43389d7075f631737edef980",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "9e4fb28bb8ca1037df4086c54bf7ecfb3633a300959d2f95d4973c24870efd30",
    "include/linux/mt6797-a72-provider.h":
        "f3f2d8dfcf992d379e1ce249e08eb15b3c0215a20e7c548b8849bd1bb44db275",
    "arch/arm64/kernel/mt6797_psci.c":
        "7e3329797e0f2eebc4372aa47c84c09e3c2ed85e5121f9492898727db5e4f83d",
    "drivers/soc/mediatek/Kconfig":
        "cf9323cc49aa4fca4991b50f1c8419fdf831e86b9fa7817547aececb18cd83b8",
    "drivers/soc/mediatek/Makefile":
        "9aaf175f2781cffaa5e590d5f0ea1ec347fdc3a26bcf43d1a30537ae55314988",
}

NEW_PATHS = (
    "include/linux/soc/mediatek/mt6797-a72-binder.h",
    "drivers/soc/mediatek/mt6797-a72-binder.c",
    "drivers/soc/mediatek/mt6797-a72-binder-internal.h",
    "drivers/soc/mediatek/mt6797-a72-binder-test.c",
    "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-binder.yaml",
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def replace_region_once(text: str, start: str, end: str, old: str,
                        new: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise SystemExit(f"{label}: start marker missing")
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        raise SystemExit(f"{label}: end marker missing")
    region = text[start_index:end_index]
    replaced = replace_once(region, old, new, label)
    return text[:start_index] + replaced + text[end_index:]


def apply_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "#define MT6797_A72_TRANSACTION_ABI 2\n",
        "#define MT6797_A72_TRANSACTION_ABI 3\n",
        "transaction ABI",
    )
    text = replace_once(
        text,
        "enum mt6797_a72_membership_operation {\n",
        "enum mt6797_a72_public_admission {\n"
        "\tMT6797_A72_PUBLIC_ADMISSION_NONE,\n"
        "\tMT6797_A72_PUBLIC_ADMISSION_PREFLIGHT,\n"
        "\tMT6797_A72_PUBLIC_ADMISSION_CLAIMED,\n"
        "};\n\n"
        "enum mt6797_a72_membership_operation {\n",
        "public admission enum",
    )
    text = replace_once(
        text,
        "\tu32 p28_valid;\n\tu32 p29_valid;\n",
        "\tu32 p28_valid;\n"
        "\tu32 cpu8_success_published;\n"
        "\tu32 p29_valid;\n",
        "success publication field",
    )
    text = replace_once(
        text,
        "int mt6797_a72_membership_validate_up(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\t      enum cpuhp_state target);\n"
        "bool\n",
        "int mt6797_a72_membership_validate_up(unsigned int cpu, int tasks_frozen,\n"
        "\t\t\t\t      enum cpuhp_state target);\n"
        "int mt6797_a72_membership_claim_cpu8("
        "struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_reject_cpu8("
        "struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_begin_cpu8_on("
        "struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_publish_cpu8_success("
        "struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction);\n"
        "bool\n",
        "binder membership prototypes",
    )
    text = replace_once(
        text,
        "void mt6797_a72_membership_test_seed_available_cpu9(void);\n",
        "void mt6797_a72_membership_test_seed_available_cpu9(void);\n"
        "int mt6797_a72_membership_test_publish_cpu8_success("
        "struct mt6797_a72_transaction *transaction,\n"
        "\t\t\t\t\t\t    bool cpu8_online, bool cpu9_online);\n"
        "int mt6797_a72_membership_test_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction,\n"
        "\t\t\t\t\t\t     bool cpu8_online, bool cpu9_online);\n",
        "membership test prototypes",
    )
    path.write_text(text, encoding="utf-8")


def apply_source(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "EXPORT_SYMBOL_GPL(mt6797_a72_provider_unregister);\n\n"
        "int mt6797_a72_provider_acquire(\n",
        "EXPORT_SYMBOL_GPL(mt6797_a72_provider_unregister);\n\n"
        "bool mt6797_a72_provider_available(void)\n"
        "{\n"
        "\tbool available;\n\n"
        "\tmutex_lock(&a72_provider_registry_lock);\n"
        "\tavailable = !!a72_provider_ops;\n"
        "\tmutex_unlock(&a72_provider_registry_lock);\n"
        "\treturn available;\n"
        "}\n"
        "EXPORT_SYMBOL_GPL(mt6797_a72_provider_available);\n\n"
        "int mt6797_a72_provider_acquire(\n",
        "provider presence query",
    )
    text = replace_once(
        text,
        "\tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||\n"
        "\t    a72_owner.phase != MT6797_A72_PHASE_ON_ISSUED ||\n"
        "\t    !transaction->valid || transaction->p32_valid ||\n",
        "\tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||\n"
        "\t    (a72_owner.phase != MT6797_A72_PHASE_ON_ISSUED &&\n"
        "\t     a72_owner.phase != MT6797_A72_PHASE_VERIFYING) ||\n"
        "\t    !transaction->valid || transaction->p32_valid ||\n",
        "P32 verifying admission",
    )
    text = replace_once(
        text,
        "\tif (!transaction ||\n"
        "\t    transaction->provider_rejection_valid ==\n"
        "\t\t    transaction->provider_abort_valid)\n"
        "\t\treturn false;\n\n"
        "\tif (transaction->provider_rejection_valid)\n",
        "\tif (!transaction)\n"
        "\t\treturn false;\n\n"
        "\tif (!transaction->provider_rejection_valid &&\n"
        "\t    !transaction->provider_abort_valid)\n"
        "\t\treturn !transaction->provider_acquire_valid &&\n"
        "\t\t\ttransaction->budgets.provider_acquire ==\n"
        "\t\t\t\tMT6797_A72_BUDGET_AVAILABLE &&\n"
        "\t\t\t!transaction->provider_identity.generation &&\n"
        "\t\t\t!transaction->provider_identity.cookie;\n\n"
        "\tif (transaction->provider_rejection_valid &&\n"
        "\t    transaction->provider_abort_valid)\n"
        "\t\treturn false;\n\n"
        "\tif (transaction->provider_rejection_valid)\n",
        "P29 no-provider predecessor",
    )
    text = replace_region_once(
        text,
        "int mt6797_a72_membership_complete_p29_rollback(\n",
        "static int\nmt6797_a72_membership_check_up(",
        "\t    a72_owner.active.identity.operation !=\n"
        "\t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||\n"
        "\t    a72_owner.members ||\n"
        "\t    a72_owner.provider_state != MT6797_A72_PROVIDER_NONE ||\n",
        "\t    a72_owner.active.identity.operation !=\n"
        "\t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||\n"
        "\t    a72_owner.active.public_preflight !=\n"
        "\t\t    MT6797_A72_PUBLIC_ADMISSION_CLAIMED ||\n"
        "\t    a72_owner.members ||\n"
        "\t    a72_owner.provider_state != MT6797_A72_PROVIDER_NONE ||\n",
        "P29 claimed admission",
    )
    old_gate = '''static int
mt6797_a72_membership_check_up(unsigned int cpu, int tasks_frozen,
\t\t\t       enum cpuhp_state target)
{
\tenum mt6797_a72_membership_operation operation;
\tunsigned long flags;
\tint ret;

\toperation = mt6797_a72_up_operation(cpu);
\tif (operation == MT6797_A72_OPERATION_NONE || target != CPUHP_ONLINE)
\t\treturn -EINVAL;
\tif (tasks_frozen)
\t\treturn -EPERM;

\t/* This leaf-only gate must remain safe under cpu_add_remove_lock. */
\tif (READ_ONCE(a72_owner.health) == MT6797_A72_OWNER_CLOSED)
\t\treturn -EAGAIN;

\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tswitch (a72_owner.health) {
\tcase MT6797_A72_OWNER_CLOSED:
\t\tret = -EAGAIN;
\t\tbreak;
\tcase MT6797_A72_OWNER_FAULTED:
\t\tret = -ESHUTDOWN;
\t\tbreak;
\tcase MT6797_A72_OWNER_AVAILABLE:
\t\tret = -EOPNOTSUPP;
\t\tbreak;
\tdefault:
\t\tret = -EPROTO;
\t\tbreak;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);

\treturn ret;
}

int mt6797_a72_membership_preflight_up(unsigned int cpu,
\t\t\t\t       enum cpuhp_state target)
{
\treturn mt6797_a72_membership_check_up(cpu, 0, target);
}

int mt6797_a72_membership_validate_up(unsigned int cpu, int tasks_frozen,
\t\t\t\t      enum cpuhp_state target)
{
\treturn mt6797_a72_membership_check_up(cpu, tasks_frozen, target);
}
'''
    new_gate = '''static int
mt6797_a72_membership_check_up(unsigned int cpu, int tasks_frozen,
\t\t\t       enum cpuhp_state target, bool preflight)
{
\tstruct mt6797_a72_transaction *transaction;
\tunsigned long flags;
\tint ret = -EPERM;

\tif (cpu != 8 || target != CPUHP_ONLINE)
\t\treturn -EINVAL;
\tif (tasks_frozen)
\t\treturn -EPERM;
\tif (!IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER))
\t\treturn -EOPNOTSUPP;

\t/* This leaf-only gate must remain safe under cpu_add_remove_lock. */
\tif (READ_ONCE(a72_owner.health) == MT6797_A72_OWNER_CLOSED)
\t\treturn -EAGAIN;

\traw_spin_lock_irqsave(&a72_state_lock, flags);
\ttransaction = &a72_owner.active;
\tif (a72_owner.health == MT6797_A72_OWNER_CLOSED) {
\t\tret = -EAGAIN;
\t} else if (a72_owner.health == MT6797_A72_OWNER_FAULTED) {
\t\tret = -ESHUTDOWN;
\t} else if (a72_owner.health != MT6797_A72_OWNER_AVAILABLE) {
\t\tret = -EPROTO;
\t} else if (a72_owner.phase != MT6797_A72_PHASE_ON_ISSUED ||
\t\t   !transaction->valid || !transaction->p17_p18_published ||
\t\t   !transaction->p30_token_valid ||
\t\t   transaction->identity.operation !=
\t\t\t   ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||
\t\t   transaction->identity.target_cpu != 8 ||
\t\t   transaction->identity.cpuhp_target != CPUHP_ONLINE ||
\t\t   transaction->controller_cookie !=
\t\t\t   transaction->identity.cookie ||
\t\t   a72_owner.controller != current ||
\t\t   a72_owner.controller_cookie !=
\t\t\t   transaction->identity.cookie ||
\t\t   a72_owner.members ||
\t\t   a72_owner.provider_state != MT6797_A72_PROVIDER_NONE ||
\t\t   cpu_online(8) || cpu_online(9)) {
\t\tret = -EPERM;
\t} else if (preflight) {
\t\tif (transaction->public_preflight ==
\t\t    MT6797_A72_PUBLIC_ADMISSION_CLAIMED) {
\t\t\tret = -EALREADY;
\t\t} else {
\t\t\ttransaction->public_preflight =
\t\t\t\tMT6797_A72_PUBLIC_ADMISSION_PREFLIGHT;
\t\t\tret = 0;
\t\t}
\t} else if (transaction->public_preflight ==
\t\t   MT6797_A72_PUBLIC_ADMISSION_PREFLIGHT) {
\t\tret = 0;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);

\treturn ret;
}

int mt6797_a72_membership_preflight_up(unsigned int cpu,
\t\t\t\t       enum cpuhp_state target)
{
\treturn mt6797_a72_membership_check_up(cpu, 0, target, true);
}

int mt6797_a72_membership_validate_up(unsigned int cpu, int tasks_frozen,
\t\t\t\t      enum cpuhp_state target)
{
\treturn mt6797_a72_membership_check_up(cpu, tasks_frozen, target, false);
}

int mt6797_a72_membership_claim_cpu8(struct mt6797_a72_transaction *transaction)
{
\tunsigned long flags;
\tint ret = -EPERM;

\tif (!transaction)
\t\treturn -EINVAL;
\tmemset(transaction, 0, sizeof(*transaction));
\tif (!IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER))
\t\treturn -EOPNOTSUPP;

\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
\t    a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
\t    a72_owner.active.valid && a72_owner.active.p17_p18_published &&
\t    a72_owner.active.p30_token_valid &&
\t    a72_owner.active.public_preflight ==
\t\t    MT6797_A72_PUBLIC_ADMISSION_PREFLIGHT &&
\t    a72_owner.active.identity.operation ==
\t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
\t    a72_owner.active.identity.target_cpu == 8 &&
\t    a72_owner.active.identity.cpuhp_target == CPUHP_ONLINE &&
\t    a72_owner.controller == current &&
\t    a72_owner.controller_cookie == a72_owner.active.identity.cookie &&
\t    !a72_owner.members &&
\t    a72_owner.provider_state == MT6797_A72_PROVIDER_NONE &&
\t    !cpu_online(8) && !cpu_online(9)) {
\t\ta72_owner.active.public_preflight =
\t\t\tMT6797_A72_PUBLIC_ADMISSION_CLAIMED;
\t\t*transaction = a72_owner.active;
\t\tret = 0;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);
\treturn ret;
}

int mt6797_a72_membership_reject_cpu8(struct mt6797_a72_transaction *transaction)
{
\tunsigned long flags;
\tint ret = -EPERM;

\tif (!transaction)
\t\treturn -EINVAL;
\tmutex_lock(&a72_transition_lock);
\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
\t    a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
\t    a72_owner.active.valid &&
\t    a72_owner.active.public_preflight ==
\t\t    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
\t    a72_owner.active.p27_preparation.stage !=
\t\t    MT6797_A72_P27_STAGE_COMPLETE &&
\t    !a72_owner.active.p27_valid &&
\t    a72_owner.provider_state == MT6797_A72_PROVIDER_NONE &&
\t    a72_owner.active.p28_preparation.stage ==
\t\t    MT6797_A72_P28_STAGE_NONE &&
\t    !a72_owner.active.p28_valid &&
\t    a72_owner.active.budgets.cpu_on ==
\t\t    MT6797_A72_BUDGET_AVAILABLE &&
\t    !memcmp(&a72_owner.active.identity, &transaction->identity,
\t\t    sizeof(a72_owner.active.identity))) {
\t\ta72_owner.retired[0] = a72_owner.active;
\t\ta72_owner.retired_mask |= BIT(0);
\t\t*transaction = a72_owner.retired[0];
\t\tmemset(&a72_owner.active, 0, sizeof(a72_owner.active));
\t\ta72_owner.controller = NULL;
\t\ta72_owner.controller_cookie = 0;
\t\ta72_owner.phase = MT6797_A72_PHASE_REJECTED;
\t\tret = 0;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);
\tmutex_unlock(&a72_transition_lock);
\treturn ret;
}

int mt6797_a72_membership_begin_cpu8_on(struct mt6797_a72_transaction *transaction)
{
\tunsigned long flags;
\tint ret = -EPERM;

\tif (!transaction)
\t\treturn -EINVAL;
\tmutex_lock(&a72_transition_lock);
\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
\t    a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
\t    a72_owner.active.valid &&
\t    a72_owner.active.public_preflight ==
\t\t    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
\t    a72_owner.active.p27_valid && a72_owner.active.p28_valid &&
\t    a72_owner.active.p28_preparation.stage ==
\t\t    MT6797_A72_P28_STAGE_COMPLETE &&
\t    a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
\t    a72_owner.active.provider_acquire_valid &&
\t    a72_owner.active.budgets.cpu_on ==
\t\t    MT6797_A72_BUDGET_AVAILABLE &&
\t    !memcmp(&a72_owner.active.identity, &transaction->identity,
\t\t    sizeof(a72_owner.active.identity)) &&
\t    !cpu_online(8) && !cpu_online(9)) {
\t\ta72_owner.active.budgets.cpu_on = MT6797_A72_BUDGET_CONSUMED;
\t\t*transaction = a72_owner.active;
\t\tret = 0;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);
\tmutex_unlock(&a72_transition_lock);
\treturn ret;
}

static int mt6797_a72_publish_cpu8_success_state(struct mt6797_a72_transaction *transaction,
\t\t\t\t\t\t bool cpu8_online,
\t\t\t\t\t\t bool cpu9_online)
{
\tunsigned long flags;
\tint ret = -EPERM;

\tif (!transaction)
\t\treturn -EINVAL;
\tmutex_lock(&a72_transition_lock);
\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
\t    a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
\t    a72_owner.active.valid &&
\t    a72_owner.active.public_preflight ==
\t\t    MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
\t    a72_owner.active.p27_valid && a72_owner.active.p28_valid &&
\t    a72_owner.active.p28_preparation.stage ==
\t\t    MT6797_A72_P28_STAGE_COMPLETE &&
\t    a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
\t    a72_owner.active.provider_acquire_valid &&
\t    a72_owner.active.budgets.cpu_on ==
\t\t    MT6797_A72_BUDGET_CONSUMED &&
\t    !a72_owner.active.cpu8_success_published &&
\t    !a72_owner.members && cpu8_online && !cpu9_online &&
\t    !memcmp(&a72_owner.active.identity, &transaction->identity,
\t\t    sizeof(a72_owner.active.identity))) {
\t\ta72_owner.members = BIT(0);
\t\ta72_owner.active.cpu8_success_published = 1;
\t\ta72_owner.phase = MT6797_A72_PHASE_VERIFYING;
\t\t*transaction = a72_owner.active;
\t\tret = 0;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);
\tmutex_unlock(&a72_transition_lock);
\treturn ret;
}

int mt6797_a72_membership_publish_cpu8_success(struct mt6797_a72_transaction *transaction)
{
\treturn mt6797_a72_publish_cpu8_success_state(transaction,
\t\t\t\t\t\t     cpu_online(8), cpu_online(9));
}

static int mt6797_a72_finalize_cpu8_success_state(struct mt6797_a72_transaction *transaction,
\t\t\t\t\t\t  bool cpu8_online,
\t\t\t\t\t\t  bool cpu9_online)
{
\tunsigned long flags;
\tint ret = -EPERM;

\tif (!transaction)
\t\treturn -EINVAL;
\tmutex_lock(&a72_transition_lock);
\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
\t    a72_owner.phase == MT6797_A72_PHASE_VERIFYING &&
\t    a72_owner.active.valid &&
\t    a72_owner.active.cpu8_success_published &&
\t    a72_owner.members == BIT(0) &&
\t    a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
\t    cpu8_online && !cpu9_online &&
\t    !memcmp(&a72_owner.active.identity, &transaction->identity,
\t\t    sizeof(a72_owner.active.identity))) {
\t\ta72_owner.retired[0] = a72_owner.active;
\t\ta72_owner.retired_mask |= BIT(0);
\t\t*transaction = a72_owner.retired[0];
\t\tmemset(&a72_owner.active, 0, sizeof(a72_owner.active));
\t\ta72_owner.controller = NULL;
\t\ta72_owner.controller_cookie = 0;
\t\ta72_owner.phase = MT6797_A72_PHASE_IDLE;
\t\tret = 0;
\t}
\traw_spin_unlock_irqrestore(&a72_state_lock, flags);
\tmutex_unlock(&a72_transition_lock);
\treturn ret;
}

int mt6797_a72_membership_finalize_cpu8_success(struct mt6797_a72_transaction *transaction)
{
\treturn mt6797_a72_finalize_cpu8_success_state(transaction,
\t\t\t\t\t\t      cpu_online(8), cpu_online(9));
}
'''
    text = replace_once(text, old_gate, new_gate, "public admission gate")
    text = replace_once(
        text,
        "void mt6797_a72_membership_test_seed_available_cpu9(void)\n",
        "int mt6797_a72_membership_test_publish_cpu8_success("
        "struct mt6797_a72_transaction *transaction,\n"
        "\t\t\t\t\t\t    bool cpu8_online, bool cpu9_online)\n"
        "{\n"
        "\treturn mt6797_a72_publish_cpu8_success_state(transaction,\n"
        "\t\t\t\t\t\t     cpu8_online, cpu9_online);\n"
        "}\n\n"
        "int mt6797_a72_membership_test_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction,\n"
        "\t\t\t\t\t\t     bool cpu8_online, bool cpu9_online)\n"
        "{\n"
        "\treturn mt6797_a72_finalize_cpu8_success_state(transaction,\n"
        "\t\t\t\t\t\t      cpu8_online, cpu9_online);\n"
        "}\n\n"
        "void mt6797_a72_membership_test_seed_available_cpu9(void)\n",
        "membership success test hooks",
    )
    path.write_text(text, encoding="utf-8")


def apply_membership_tests(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = "static void mt6797_a72_owner_forged_token_rejected"
    addition = r'''#if IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)
static int
mt6797_a72_test_seed_cpu8_claimed(struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_entry_snapshot entry = mt6797_a72_entry_for_up(8);
	struct arm64_late_cpu_ready_token ready = mt6797_a72_ready_token_for_up();
	struct mt6797_a72_a36_prestate prestate = mt6797_a72_prestate_for_up(8);
	int ret;

	mt6797_a72_membership_test_seed_available();
	ret = mt6797_a72_membership_begin_up(8, CPUHP_ONLINE,
					     MT6797_A72_ATTEMPT_CPU8_UP,
					     &entry, &ready, &prestate,
					     transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_publish_up(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_validate_up(8, 0, CPUHP_ONLINE);
	if (ret)
		return ret;
	return mt6797_a72_membership_claim_cpu8(transaction);
}

static int
mt6797_a72_test_seed_cpu8_claimed_p27(struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_p27_preparation preparation;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_begin_p27_preparation(transaction);
	if (ret)
		return ret;
	preparation = mt6797_a72_p27_preparation_for(transaction);
	return mt6797_a72_membership_complete_p27_preparation(transaction,
							     &preparation);
}

static int
mt6797_a72_test_seed_cpu8_claimed_p28(struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_provider_acquire_proof proof;
	struct mt6797_a72_p28_preparation preparation;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed_p27(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_begin_provider_acquire(transaction);
	if (ret)
		return ret;
	proof = mt6797_a72_provider_acquire_proof_for(transaction);
	ret = mt6797_a72_membership_confirm_provider_acquire(transaction, &proof);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_begin_p28_preparation(transaction);
	if (ret)
		return ret;
	preparation = mt6797_a72_p28_preparation_for(transaction);
	return mt6797_a72_membership_complete_p28_preparation(transaction,
							     &preparation);
}

static void mt6797_a72_owner_binder_success_handoff(struct kunit *test)
{
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_owner_snapshot snapshot;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed_p28(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_begin_cpu8_on(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, transaction.budgets.cpu_on,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	KUNIT_EXPECT_EQ(test,
			mt6797_a72_membership_begin_cpu8_on(&transaction),
			-EPERM);
	ret = mt6797_a72_membership_test_publish_cpu8_success(&transaction,
							      true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.phase,
			(u32)MT6797_A72_PHASE_VERIFYING);
	KUNIT_EXPECT_EQ(test, snapshot.members, (u32)BIT(0));
	KUNIT_EXPECT_TRUE(test, snapshot.active.cpu8_success_published);

	ret = mt6797_a72_membership_test_finalize_cpu8_success(&transaction,
							       true, false);
	KUNIT_EXPECT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.phase, (u32)MT6797_A72_PHASE_IDLE);
	KUNIT_EXPECT_EQ(test, snapshot.members, (u32)BIT(0));
	KUNIT_EXPECT_EQ(test, snapshot.retired_mask, (u32)BIT(0));
	KUNIT_EXPECT_FALSE(test, snapshot.active.valid);
	KUNIT_EXPECT_TRUE(test, snapshot.retired[0].cpu8_success_published);
}

static void mt6797_a72_owner_binder_p32_from_verifying(struct kunit *test)
{
	struct cpu_up_rollback_trace trace = { };
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_owner_snapshot snapshot;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed_p28(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_begin_cpu8_on(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_test_publish_cpu8_success(&transaction,
							      true, false);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_publish_p32(8, CPUHP_ONLINE,
						-ENOSPC, &trace);
	KUNIT_EXPECT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.phase, (u32)MT6797_A72_PHASE_FAULT);
	KUNIT_EXPECT_EQ(test, snapshot.members, (u32)BIT(0));
	KUNIT_EXPECT_TRUE(test, snapshot.active.p32_valid);
	KUNIT_EXPECT_EQ(test, snapshot.active.p32.cpu_up_error, -ENOSPC);
}

static void mt6797_a72_owner_binder_clean_rejection(struct kunit *test)
{
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_owner_snapshot snapshot;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_reject_cpu8(&transaction);
	KUNIT_EXPECT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.phase,
			(u32)MT6797_A72_PHASE_REJECTED);
	KUNIT_EXPECT_EQ(test, snapshot.members, (u32)0);
	KUNIT_EXPECT_EQ(test, snapshot.retired_mask, (u32)BIT(0));
	KUNIT_EXPECT_FALSE(test, snapshot.active.valid);
}

static void mt6797_a72_owner_binder_p29_without_provider(struct kunit *test)
{
	struct mt6797_a72_p29_rollback_proof rollback;
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_owner_snapshot snapshot;
	int ret;

	ret = mt6797_a72_test_seed_cpu8_claimed_p27(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	rollback = mt6797_a72_p29_rollback_for(&transaction);
	ret = mt6797_a72_membership_complete_p29_rollback(&transaction,
							  &rollback);
	KUNIT_EXPECT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.phase,
			(u32)MT6797_A72_PHASE_REJECTED);
	KUNIT_EXPECT_TRUE(test, snapshot.retired[0].p29_valid);
	KUNIT_EXPECT_FALSE(test, snapshot.retired[0].provider_acquire_valid);
}
#endif

'''
    text = replace_once(text, anchor, addition + anchor,
                        "membership binder KUnit cases")
    text = replace_once(
        text,
        "\tKUNIT_CASE(mt6797_a72_owner_r03_p29_mutations_rejected),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_forged_token_rejected),\n",
        "\tKUNIT_CASE(mt6797_a72_owner_r03_p29_mutations_rejected),\n"
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)\n"
        "\tKUNIT_CASE(mt6797_a72_owner_binder_success_handoff),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_binder_p32_from_verifying),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_binder_clean_rejection),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_binder_p29_without_provider),\n"
        "#endif\n"
        "\tKUNIT_CASE(mt6797_a72_owner_forged_token_rejected),\n",
        "membership binder KUnit registration",
    )
    path.write_text(text, encoding="utf-8")


def apply_provider_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "void mt6797_a72_provider_unregister(const struct mt6797_a72_provider_ops *ops,\n"
        "\t\t\t\t    void *context);\n",
        "void mt6797_a72_provider_unregister(const struct mt6797_a72_provider_ops *ops,\n"
        "\t\t\t\t    void *context);\n"
        "bool mt6797_a72_provider_available(void);\n",
        "provider presence declaration",
    )
    path.write_text(text, encoding="utf-8")


def apply_psci(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "#include <linux/string.h>\n",
        "#include <linux/string.h>\n"
        "#include <linux/soc/mediatek/mt6797-a72-binder.h>\n",
        "PSCI binder include",
    )
    text = replace_once(
        text,
        "\treturn mt6797_a72_membership_preflight_up(cpu, target);\n",
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER))\n"
        "\t\treturn mt6797_a72_binder_preflight(cpu, target);\n\n"
        "\treturn mt6797_a72_membership_preflight_up(cpu, target);\n",
        "PSCI binder preflight",
    )
    text = replace_once(
        text,
        "\treturn mt6797_a72_membership_validate_up(cpu, tasks_frozen, target);\n",
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER))\n"
        "\t\treturn mt6797_a72_binder_validate(cpu, tasks_frozen, target);\n\n"
        "\treturn mt6797_a72_membership_validate_up(cpu, tasks_frozen, target);\n",
        "PSCI binder validation",
    )
    text = replace_once(
        text,
        "{\n"
        "\tif (cpu != 8 && cpu != 9)\n"
        "\t\treturn 0;\n\n"
        "\treturn mt6797_a72_membership_publish_p32(cpu, state, error, trace);\n"
        "}\n",
        "{\n"
        "\tbool publish_p32 = true;\n"
        "\tint ret;\n\n"
        "\tif (cpu != 8 && cpu != 9)\n"
        "\t\treturn 0;\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) &&\n"
        "\t    cpu == 8) {\n"
        "\t\tret = mt6797_a72_binder_failure(cpu, error, &publish_p32);\n"
        "\t\tif (ret || !publish_p32)\n"
        "\t\t\treturn ret;\n"
        "\t}\n\n"
        "\treturn mt6797_a72_membership_publish_p32(cpu, state, error, trace);\n"
        "}\n",
        "PSCI binder failure-before-P32",
    )
    text = replace_once(
        text,
        "static int mt6797_psci_cpu_boot(unsigned int cpu)\n"
        "{\n"
        "\tpr_warn_ratelimited(\"CPU%u boot rejected: A72 power sequence inactive\\n\",\n"
        "\t\t\t    cpu);\n\n"
        "\treturn -EAGAIN;\n"
        "}\n",
        "#ifdef CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER\n"
        "static int mt6797_psci_cpu_up_secondary_complete(unsigned int cpu)\n"
        "{\n"
        "\treturn mt6797_a72_binder_secondary_complete(cpu);\n"
        "}\n\n"
        "static int mt6797_psci_cpu_up_complete(unsigned int cpu,\n"
        "\t\t\t\t       enum cpuhp_state target)\n"
        "{\n"
        "\treturn mt6797_a72_binder_complete(cpu, target);\n"
        "}\n"
        "#endif\n\n"
        "static int mt6797_psci_cpu_boot(unsigned int cpu)\n"
        "{\n"
        "\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) && cpu == 8)\n"
        "\t\treturn mt6797_a72_binder_cpu_boot(cpu, cpu_psci_ops.cpu_boot);\n\n"
        "\tpr_warn_ratelimited(\"CPU%u boot rejected: A72 power sequence inactive\\n\",\n"
        "\t\t\t    cpu);\n\n"
        "\treturn -EAGAIN;\n"
        "}\n",
        "PSCI binder lifecycle and boot",
    )
    text = replace_once(
        text,
        "#ifdef CONFIG_ARM64_MT6797_A72_P32_ROLLBACK\n"
        "\t.cpu_up_rollback = mt6797_psci_cpu_up_rollback,\n"
        "#endif\n"
        "\t.cpu_boot\t= mt6797_psci_cpu_boot,\n",
        "#ifdef CONFIG_ARM64_MT6797_A72_P32_ROLLBACK\n"
        "\t.cpu_up_rollback = mt6797_psci_cpu_up_rollback,\n"
        "#endif\n"
        "#ifdef CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER\n"
        "\t.cpu_up_secondary_complete =\n"
        "\t\tmt6797_psci_cpu_up_secondary_complete,\n"
        "\t.cpu_up_complete = mt6797_psci_cpu_up_complete,\n"
        "#endif\n"
        "\t.cpu_boot\t= mt6797_psci_cpu_boot,\n",
        "PSCI binder operation table",
    )
    path.write_text(text, encoding="utf-8")


def apply_binder_kconfig(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = "config MTK_MT6797_DVFSP_HANDOFF\n"
    addition = '''config MTK_MT6797_A72_DEFAULT_OFF_BINDER
\tbool "MediaTek MT6797 Cortex-A72 default-off transition binder"
\tdepends on ARM64 && ARCH_MEDIATEK && OF
\tdepends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
\tdepends on ARM64_MT6797_A72_P24_ADMISSION_HOOKS
\tdepends on ARM64_MT6797_A72_P32_ROLLBACK
\tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
\tdepends on ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT
\tdepends on MTK_MT6797_A72_PLATFORM_EFFECTS
\tdepends on MTK_MT6797_A72_TRANSITION_EXECUTOR
\tdepends on MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER
\tdepends on MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER
\tdepends on PSTORE_GEMINI_TRANSITION_LEDGER
\tdefault n
\thelp
\t  Join the existing MT6797 CPU8 membership, retained-ledger,
\t  recovery-watchdog, platform-effect, DA921x provider, SRAM-LDO,
\t  transition-executor, PSCI, and CPU-hotplug lifecycle owners.

\t  The binder is one-shot, accepts only an already armed CPU8
\t  CPUHP_ONLINE transaction, and has no userspace trigger. Its platform
\t  device must name three bound suppliers explicitly. The base Gemini
\t  Device Tree does not instantiate or enable that device, so selecting
\t  this option alone cannot make a CPU request. If unsure, say N.

'''
    text = replace_once(text, anchor, addition + anchor, "binder Kconfig")
    path.write_text(text, encoding="utf-8")


def apply_test_kconfig(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = "config MTK_MT6797_DVFSP_HANDOFF\n"
    addition = '''config MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST
\tbool "KUnit tests for the MT6797 A72 default-off binder"
\tdepends on KUNIT=y
\tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER
\tselect ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST
\tselect MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST
\tdefault n
\thelp
\t  Exercise the binder admission, split lifecycle, owner-response,
\t  terminal-evidence, P32-ordering, and one-shot contracts through
\t  injected operations only. No MMIO, secure call, watchdog, retained
\t  RAM, PSCI, CPU request, CPU_OFF, retry, or device action is used.

'''
    text = replace_once(text, anchor, addition + anchor,
                        "binder test Kconfig")
    path.write_text(text, encoding="utf-8")


def apply_binder_makefile(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST) += "
        "mt6797-a72-transition-test.o\n"
    )
    addition = (
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) += "
        "mt6797-a72-binder.o\n"
    )
    text = replace_once(text, anchor, anchor + addition, "binder Makefile")
    path.write_text(text, encoding="utf-8")


def apply_test_makefile(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) += "
        "mt6797-a72-binder.o\n"
    )
    addition = (
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST) += "
        "mt6797-a72-binder-test.o\n"
    )
    text = replace_once(text, anchor, anchor + addition,
                        "binder test Makefile")
    path.write_text(text, encoding="utf-8")


PUBLIC_HEADER = '''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __LINUX_SOC_MEDIATEK_MT6797_A72_BINDER_H
#define __LINUX_SOC_MEDIATEK_MT6797_A72_BINDER_H

#include <linux/cpuhotplug.h>
#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

typedef int (*mt6797_a72_cpu_boot_fn)(unsigned int cpu);

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)
int mt6797_a72_binder_preflight(unsigned int cpu, enum cpuhp_state target);
int mt6797_a72_binder_validate(unsigned int cpu, int tasks_frozen,
\t\t\t       enum cpuhp_state target);
int mt6797_a72_binder_cpu_boot(unsigned int cpu,
\t\t\t      mt6797_a72_cpu_boot_fn cpu_boot);
int mt6797_a72_binder_secondary_complete(unsigned int cpu);
int mt6797_a72_binder_complete(unsigned int cpu, enum cpuhp_state target);
int mt6797_a72_binder_failure(unsigned int cpu, int error,
\t\t\t      bool *publish_p32);
#else
static inline int
mt6797_a72_binder_preflight(unsigned int cpu, enum cpuhp_state target)
{
\t(void)cpu;
\t(void)target;
\treturn -EOPNOTSUPP;
}

static inline int
mt6797_a72_binder_validate(unsigned int cpu, int tasks_frozen,
\t\t\t   enum cpuhp_state target)
{
\t(void)cpu;
\t(void)tasks_frozen;
\t(void)target;
\treturn -EOPNOTSUPP;
}

static inline int
mt6797_a72_binder_cpu_boot(unsigned int cpu,
\t\t\t  mt6797_a72_cpu_boot_fn cpu_boot)
{
\t(void)cpu;
\t(void)cpu_boot;
\treturn -EOPNOTSUPP;
}

static inline int mt6797_a72_binder_secondary_complete(unsigned int cpu)
{
\t(void)cpu;
\treturn -EOPNOTSUPP;
}

static inline int
mt6797_a72_binder_complete(unsigned int cpu, enum cpuhp_state target)
{
\t(void)cpu;
\t(void)target;
\treturn -EOPNOTSUPP;
}

static inline int
mt6797_a72_binder_failure(unsigned int cpu, int error, bool *publish_p32)
{
\t(void)cpu;
\t(void)error;
\tif (publish_p32)
\t\t*publish_p32 = false;
\treturn -EOPNOTSUPP;
}
#endif

#endif /* __LINUX_SOC_MEDIATEK_MT6797_A72_BINDER_H */
'''


def create_binder_files(root: Path) -> None:
    path = root / NEW_PATHS[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PUBLIC_HEADER, encoding="utf-8")
    source = SCRIPT_DIR.parent / "kernel" / "mt6797-a72-binder.c"
    if not source.is_file() or source.is_symlink():
        raise SystemExit("binder source template is unavailable")
    path = root / NEW_PATHS[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.read_bytes())
    source = SCRIPT_DIR.parent / "kernel" / "mt6797-a72-binder-internal.h"
    if not source.is_file() or source.is_symlink():
        raise SystemExit("binder internal header template is unavailable")
    path = root / NEW_PATHS[2]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.read_bytes())


def create_test_file(root: Path) -> None:
    source = SCRIPT_DIR.parent / "kernel" / "mt6797-a72-binder-test.c"
    if not source.is_file() or source.is_symlink():
        raise SystemExit("binder KUnit template is unavailable")
    path = root / NEW_PATHS[3]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.read_bytes())


def create_binding_file(root: Path) -> None:
    source = (
        SCRIPT_DIR.parent / "kernel" /
        "mediatek,mt6797-a72-binder.yaml"
    )
    if not source.is_file() or source.is_symlink():
        raise SystemExit("binder schema template is unavailable")
    path = root / NEW_PATHS[4]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.read_bytes())


def require_absent(root: Path, paths: tuple[str, ...]) -> None:
    for relative in paths:
        path = root / relative
        if path.exists() or path.is_symlink():
            raise SystemExit(f"new path already exists: {relative}")


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"source path is not an exact file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"parent hash changed: {relative}: {actual} != {expected}"
            )


def apply_owner_stage(root: Path) -> None:
    apply_header(root / "arch/arm64/include/asm/mt6797_a72_membership.h")
    apply_source(root / "arch/arm64/kernel/mt6797_a72_membership.c")
    apply_membership_tests(
        root / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    )
    apply_provider_header(root / "include/linux/mt6797-a72-provider.h")


def apply_binding_stage(root: Path) -> None:
    require_absent(root, (NEW_PATHS[4],))
    create_binding_file(root)


def apply_binder_stage(root: Path) -> None:
    require_absent(root, NEW_PATHS[:3])
    apply_psci(root / "arch/arm64/kernel/mt6797_psci.c")
    apply_binder_kconfig(root / "drivers/soc/mediatek/Kconfig")
    apply_binder_makefile(root / "drivers/soc/mediatek/Makefile")
    create_binder_files(root)


def apply_test_stage(root: Path) -> None:
    require_absent(root, (NEW_PATHS[3],))
    apply_test_kconfig(root / "drivers/soc/mediatek/Kconfig")
    apply_test_makefile(root / "drivers/soc/mediatek/Makefile")
    create_test_file(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_parent(root)
    require_absent(root, NEW_PATHS)
    apply_owner_stage(root)
    apply_binding_stage(root)
    apply_binder_stage(root)
    apply_test_stage(root)


if __name__ == "__main__":
    main()
