#!/usr/bin/env python3
"""Apply the exact CPU8 P30E entry-diagnostic integration."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


MEMBERSHIP = Path("arch/arm64/kernel/mt6797_a72_membership.c")
BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_INTERNAL = Path("drivers/soc/mediatek/mt6797-a72-binder-internal.h")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
BINDER_PUBLIC = Path("include/linux/soc/mediatek/mt6797-a72-binder.h")
ADMISSION = Path("drivers/soc/mediatek/mt6797-a72-admission-controller.c")
SOURCE_FILES = (
    MEMBERSHIP,
    BINDER,
    BINDER_INTERNAL,
    BINDER_TEST,
    BINDER_PUBLIC,
    ADMISSION,
)
PARENT_SHA256 = {
    MEMBERSHIP: "9f8d61346581452bab4e32d4fb67e3f12b7b881c69633990f704497f1e5e003a",
    BINDER: "b8c70da173d036227463e180511c34169f5d27362c7507411c90b000e16c6356",
    BINDER_INTERNAL: "1e9d522d86a94c26b96cfb69f4b25db718bb7753d3ec81918bbcfc629d6dcc19",
    BINDER_TEST: "df796c1d59a7a1e1289bb4a0465281e76846676fa1b807653cd1e2f5ad4531e1",
    BINDER_PUBLIC: "9b25180340cfa83c5be3de13592377eb4f3ea105d504b2fd1b6a4067092156b0",
    ADMISSION: "44c956d7ac41454dbfc46b1984e884d70e4482c4359ef21fad7f78d02e7373f7",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new)


def verify_parent(root: Path) -> None:
    for relative, expected in PARENT_SHA256.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"parent file is absent or unsafe: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(
                f"parent checksum changed for {relative}: {actual} != {expected}"
            )


def apply(root: Path) -> None:
    verify_parent(root)
    membership_path = root / MEMBERSHIP
    binder_path = root / BINDER
    internal_path = root / BINDER_INTERNAL
    test_path = root / BINDER_TEST
    public_path = root / BINDER_PUBLIC
    admission_path = root / ADMISSION

    membership = membership_path.read_text(encoding="utf-8")
    binder = binder_path.read_text(encoding="utf-8")
    internal = internal_path.read_text(encoding="utf-8")
    test = test_path.read_text(encoding="utf-8")
    public = public_path.read_text(encoding="utf-8")
    admission = admission_path.read_text(encoding="utf-8")

    membership = replace_once(
        membership,
        """\tu64 operation;
\tint ret;

\tif (!transaction || !ready || !handoff)""",
        """\tu64 operation;
\tbool cpu8_on_ready;
\tint ret;

\tif (!transaction || !ready || !handoff)""",
        "membership P30E local state",
    )
    membership = replace_once(
        membership,
        """\tmutex_lock(&a72_transition_lock);
\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||
\t    a72_owner.phase != MT6797_A72_PHASE_FROZEN ||
\t    !a72_owner.active.valid || !a72_owner.active.a36_valid ||
\t    !a72_owner.active.p30_token_valid ||
\t    memcmp(&a72_owner.active.identity, identity,
\t\t   sizeof(a72_owner.active.identity)))
\t\tret = -EBUSY;
\telse {""",
        """\tmutex_lock(&a72_transition_lock);
\traw_spin_lock_irqsave(&a72_state_lock, flags);
\tcpu8_on_ready = identity->operation ==
\t\tARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
\t\ta72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
\t\ta72_owner.active.p17_p18_published &&
\t\ta72_owner.active.p27_valid && a72_owner.active.p28_valid &&
\t\ta72_owner.active.p28_preparation.stage ==
\t\t\tMT6797_A72_P28_STAGE_COMPLETE &&
\t\ta72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
\t\ta72_owner.active.provider_acquire_valid &&
\t\ta72_owner.active.budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE;
\tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||
\t    !a72_owner.active.valid || !a72_owner.active.a36_valid ||
\t    !a72_owner.active.p30_token_valid ||
\t    (a72_owner.phase != MT6797_A72_PHASE_FROZEN && !cpu8_on_ready) ||
\t    memcmp(&a72_owner.active.identity, identity,
\t\t   sizeof(a72_owner.active.identity)))
\t\tret = -EBUSY;
\telse {""",
        "CPU8 pre-CPU_ON P30E preparation gate",
    )

    internal = replace_once(
        internal,
        """#include <asm/mt6797_a72_membership.h>

#include \"mt6797-a72-transition-internal.h\"""",
        """#include <asm/mt6797_a72_membership.h>
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
#include <asm/mt6797_a72_p30e.h>
#endif

#include \"mt6797-a72-transition-internal.h\"""",
        "binder P30E type include",
    )
    internal = replace_once(
        internal,
        """\tint (*membership_begin_cpu_on)(struct mt6797_a72_transaction *transaction);
\tint (*membership_publish_success)(struct mt6797_a72_transaction *transaction);""",
        """\tint (*membership_begin_cpu_on)(struct mt6797_a72_transaction *transaction);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tint (*p30e_prepare)(const struct mt6797_a72_transaction *transaction,
\t\t\t     struct mt6797_a72_p30e_handoff *handoff);
\tint (*p30e_arm)(unsigned int cpu,
\t\t\t const struct mt6797_a72_p30e_handoff *handoff);
\tint (*p30e_readback)(unsigned int cpu,
\t\t\t      const struct mt6797_a72_p30e_handoff *handoff,
\t\t\t      struct arm64_mt6797_a72_p30e_wire *copy);
#endif
\tint (*membership_publish_success)(struct mt6797_a72_transaction *transaction);""",
        "binder P30E backend operations",
    )
    internal = replace_once(
        internal,
        """\ts32 p28_complete_ret;
\tbool ledger_begun;""",
        """\ts32 p28_complete_ret;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tstruct mt6797_a72_p30e_handoff p30e_handoff;
\tstruct arm64_mt6797_a72_p30e_wire p30e_snapshot;
\ts32 p30e_prepare_ret;
\ts32 p30e_arm_ret;
\ts32 p30e_readback_ret;
\tbool p30e_prepare_attempted;
\tbool p30e_arm_attempted;
\tbool p30e_armed;
\tbool p30e_readback_attempted;
#endif
\tbool ledger_begun;""",
        "binder P30E state",
    )

    public = replace_once(
        public,
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 2U",
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 3U",
        "binder diagnostic ABI",
    )
    public = replace_once(
        public,
        """\tu32 sram_verified;
\tu32 sram_sealed;
};""",
        """\tu32 sram_verified;
\tu32 sram_sealed;
\tu32 p30e_prepare_attempted;
\ts32 p30e_prepare_ret;
\tu32 p30e_arm_attempted;
\ts32 p30e_arm_ret;
\tu32 p30e_armed;
\tu32 p30e_readback_attempted;
\ts32 p30e_readback_ret;
\tu32 p30e_controller_state;
\tu32 p30e_target_state;
\tu32 p30e_target_sequence;
\tu32 p30e_controller_sequence;
};""",
        "binder diagnostic P30E fields",
    )

    binder = replace_once(
        binder,
        """#include <linux/build_bug.h>
#include <linux/cpu.h>""",
        """#include <linux/build_bug.h>
#include <linux/byteorder/little_endian.h>
#include <linux/cpu.h>""",
        "binder byteorder include",
    )
    binder = replace_once(
        binder,
        """#include <linux/string.h>

#include \"mt6797-a72-binder-internal.h\"""",
        """#include <linux/string.h>

#include <asm/late_cpu_profile.h>

#include \"mt6797-a72-binder-internal.h\"""",
        "binder READY token include",
    )
    binder = replace_once(
        binder,
        """\tsnapshot->sram_effect_attempted = binder->sram.effect_attempted;
\tsnapshot->sram_verified = binder->sram.verified;
\tsnapshot->sram_sealed = binder->sram.sealed;
}""",
        """\tsnapshot->sram_effect_attempted = binder->sram.effect_attempted;
\tsnapshot->sram_verified = binder->sram.verified;
\tsnapshot->sram_sealed = binder->sram.sealed;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tsnapshot->p30e_prepare_attempted = binder->p30e_prepare_attempted;
\tsnapshot->p30e_prepare_ret = binder->p30e_prepare_ret;
\tsnapshot->p30e_arm_attempted = binder->p30e_arm_attempted;
\tsnapshot->p30e_arm_ret = binder->p30e_arm_ret;
\tsnapshot->p30e_armed = binder->p30e_armed;
\tsnapshot->p30e_readback_attempted = binder->p30e_readback_attempted;
\tsnapshot->p30e_readback_ret = binder->p30e_readback_ret;
\tsnapshot->p30e_controller_state = le64_to_cpu(binder->p30e_snapshot.word[
\t\tARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD]);
\tsnapshot->p30e_target_state = le64_to_cpu(binder->p30e_snapshot.word[
\t\tARM64_MT6797_A72_P30E_TARGET_STATE_WORD]);
\tsnapshot->p30e_target_sequence = le64_to_cpu(binder->p30e_snapshot.word[
\t\tARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD]);
\tsnapshot->p30e_controller_sequence = le64_to_cpu(binder->p30e_snapshot.word[
\t\tARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD]);
#endif
}""",
        "binder P30E diagnostic fill",
    )
    binder = replace_once(
        binder,
        """static int mt6797_a72_binder_ipi_call(unsigned int cpu,
\t\t\t\t      smp_call_func_t func, void *info, int wait)
{
\treturn smp_call_function_single(cpu, func, info, wait);
}

static const struct mt6797_a72_binder_backend_ops""",
        """static int mt6797_a72_binder_ipi_call(unsigned int cpu,
\t\t\t\t      smp_call_func_t func, void *info, int wait)
{
\treturn smp_call_function_single(cpu, func, info, wait);
}

#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
static void
mt6797_a72_binder_p30e_request(
\tconst struct mt6797_a72_p30e_handoff *handoff,
\tstruct arm64_mt6797_a72_p30e_request *request)
{
\tmemset(request, 0, sizeof(*request));
\tmemcpy(request->boot_identity, handoff->wire_boot_identity,
\t       sizeof(request->boot_identity));
\tmemcpy(request->target_boot_identity, handoff->target_boot_identity,
\t       sizeof(request->target_boot_identity));
\trequest->slot_pa = handoff->slot_pa;
\trequest->entry_pa = handoff->entry_pa;
\trequest->operation = handoff->operation;
\trequest->generation = handoff->generation;
\trequest->cookie = handoff->cookie;
}

static int
mt6797_a72_binder_p30e_prepare(
\tconst struct mt6797_a72_transaction *transaction,
\tstruct mt6797_a72_p30e_handoff *handoff)
{
\tconst struct arm64_late_cpu_ready_token *ready;

\tready = arm64_get_late_cpu_ready_token();
\treturn ready ? mt6797_a72_membership_prepare_p30e_handoff(
\t\ttransaction, ready, handoff) : -EAGAIN;
}

static int
mt6797_a72_binder_p30e_arm(
\tunsigned int cpu, const struct mt6797_a72_p30e_handoff *handoff)
{
\tstruct arm64_mt6797_a72_p30e_request request;

\tif (!handoff || cpu != MT6797_A72_TRANSITION_CPU8 ||
\t    handoff->target_cpu != cpu ||
\t    handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP)
\t\treturn -EPERM;
\tmt6797_a72_binder_p30e_request(handoff, &request);
\treturn arm64_mt6797_a72_p30e_arm(cpu, &request);
}

static int
mt6797_a72_binder_p30e_readback(
\tunsigned int cpu, const struct mt6797_a72_p30e_handoff *handoff,
\tstruct arm64_mt6797_a72_p30e_wire *copy)
{
\tstruct arm64_mt6797_a72_p30e_request request;

\tif (!handoff || !copy || cpu != MT6797_A72_TRANSITION_CPU8 ||
\t    handoff->target_cpu != cpu ||
\t    handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP)
\t\treturn -EPERM;
\tmt6797_a72_binder_p30e_request(handoff, &request);
\treturn arm64_mt6797_a72_p30e_readback(cpu, &request, copy);
}
#endif

static const struct mt6797_a72_binder_backend_ops""",
        "binder production P30E wrappers",
    )
    binder = replace_once(
        binder,
        """\t.membership_complete_p29 = mt6797_a72_membership_complete_p29_rollback,
\t.membership_begin_cpu_on = mt6797_a72_membership_begin_cpu8_on,
\t.membership_publish_success =""",
        """\t.membership_complete_p29 = mt6797_a72_membership_complete_p29_rollback,
\t.membership_begin_cpu_on = mt6797_a72_membership_begin_cpu8_on,
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\t.p30e_prepare = mt6797_a72_binder_p30e_prepare,
\t.p30e_arm = mt6797_a72_binder_p30e_arm,
\t.p30e_readback = mt6797_a72_binder_p30e_readback,
#endif
\t.membership_publish_success =""",
        "production P30E operation table",
    )
    binder = replace_once(
        binder,
        """static bool
mt6797_a72_binder_backend_valid(const struct mt6797_a72_binder_backend_ops *ops)
{
\treturn ops && ops->ledger_begin && ops->ledger_checkpoint &&
\t\tops->provider_available && ops->membership_preflight &&
\t\tops->membership_validate && ops->membership_claim &&
\t\tops->membership_owns_token && ops->membership_reject &&
\t\tops->membership_begin_p27 && ops->membership_complete_p27 &&
\t\tops->membership_provider_acquire &&
\t\tops->membership_provider_abort && ops->membership_begin_p28 &&
\t\tops->membership_complete_p28 && ops->membership_complete_p29 &&
\t\tops->membership_begin_cpu_on &&
\t\tops->membership_publish_success &&
\t\tops->membership_finalize_success && ops->watchdog_takeover &&
\t\tops->p27_acquire && ops->p27_release && ops->isolation_clear &&
\t\tops->sram_enable && ops->dcm_update && ops->cpu_online &&
\t\tops->ipi_call;
}""",
        """static bool
mt6797_a72_binder_backend_valid(const struct mt6797_a72_binder_backend_ops *ops)
{
\tif (!ops || !ops->ledger_begin || !ops->ledger_checkpoint ||
\t    !ops->provider_available || !ops->membership_preflight ||
\t    !ops->membership_validate || !ops->membership_claim ||
\t    !ops->membership_owns_token || !ops->membership_reject ||
\t    !ops->membership_begin_p27 || !ops->membership_complete_p27 ||
\t    !ops->membership_provider_acquire ||
\t    !ops->membership_provider_abort || !ops->membership_begin_p28 ||
\t    !ops->membership_complete_p28 || !ops->membership_complete_p29 ||
\t    !ops->membership_begin_cpu_on || !ops->membership_publish_success ||
\t    !ops->membership_finalize_success || !ops->watchdog_takeover ||
\t    !ops->p27_acquire || !ops->p27_release || !ops->isolation_clear ||
\t    !ops->sram_enable || !ops->dcm_update || !ops->cpu_online ||
\t    !ops->ipi_call)
\t\treturn false;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tif (!ops->p30e_prepare || !ops->p30e_arm || !ops->p30e_readback)
\t\treturn false;
#endif
\treturn true;
}""",
        "binder backend validation",
    )
    binder = replace_once(
        binder,
        """static int mt6797_a72_binder_cpu_on(void *context, unsigned int cpu)
{
\tstruct mt6797_a72_binder *binder = context;
\tint ret;

\tif (cpu != MT6797_A72_TRANSITION_CPU8 || !binder->cpu_boot)
\t\treturn -EINVAL;
\tret = binder->backend->membership_begin_cpu_on(&binder->transaction);
\tif (ret)
\t\treturn ret;
\treturn binder->cpu_boot(cpu);
}""",
        """#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
static void
mt6797_a72_binder_p30e_readback_once(struct mt6797_a72_binder *binder,
\t\t\t\t     unsigned int cpu)
{
\tif (!binder->p30e_armed || binder->p30e_readback_attempted)
\t\treturn;
\tbinder->p30e_readback_attempted = true;
\tmemset(&binder->p30e_snapshot, 0, sizeof(binder->p30e_snapshot));
\tbinder->p30e_readback_ret = binder->backend->p30e_readback(
\t\tcpu, &binder->p30e_handoff, &binder->p30e_snapshot);
}
#endif

static int mt6797_a72_binder_cpu_on(void *context, unsigned int cpu)
{
\tstruct mt6797_a72_binder *binder = context;
\tint ret;

\tif (cpu != MT6797_A72_TRANSITION_CPU8 || !binder->cpu_boot)
\t\treturn -EINVAL;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tbinder->p30e_prepare_attempted = true;
\tbinder->p30e_prepare_ret = binder->backend->p30e_prepare(
\t\t&binder->transaction, &binder->p30e_handoff);
\tif (binder->p30e_prepare_ret)
\t\treturn binder->p30e_prepare_ret;
#endif
\tret = binder->backend->membership_begin_cpu_on(&binder->transaction);
\tif (ret)
\t\treturn ret;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tbinder->p30e_arm_attempted = true;
\tbinder->p30e_arm_ret = binder->backend->p30e_arm(
\t\tcpu, &binder->p30e_handoff);
\tif (binder->p30e_arm_ret)
\t\treturn binder->p30e_arm_ret;
\tbinder->p30e_armed = true;
#endif
\tret = binder->cpu_boot(cpu);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tif (ret)
\t\tmt6797_a72_binder_p30e_readback_once(binder, cpu);
#endif
\treturn ret;
}""",
        "binder CPU8 P30E arm",
    )
    binder = replace_once(
        binder,
        """\tif (cpu != MT6797_A72_TRANSITION_CPU8)
\t\treturn -EINVAL;
\tlifecycle = atomic_read_acquire(&binder->transition.lifecycle);""",
        """\tif (cpu != MT6797_A72_TRANSITION_CPU8)
\t\treturn -EINVAL;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tmt6797_a72_binder_p30e_readback_once(binder, cpu);
#endif
\tlifecycle = atomic_read_acquire(&binder->transition.lifecycle);""",
        "binder rollback P30E readback",
    )

    test = replace_once(
        test,
        """\tTEST_EVENT_SRAM,
\tTEST_EVENT_CPU_ON,""",
        """\tTEST_EVENT_SRAM,
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tTEST_EVENT_P30E_PREPARE,
\tTEST_EVENT_P30E_ARM,
\tTEST_EVENT_P30E_READBACK,
#endif
\tTEST_EVENT_CPU_ON,""",
        "binder test P30E events",
    )
    test = replace_once(
        test,
        """\tu32 selector_status;
\tu32 selector_xor;
\tbool terminal_fails;""",
        """\tu32 selector_status;
\tu32 selector_xor;
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tu32 p30e_target_state;
\tu32 p30e_prepares;
\tu32 p30e_arms;
\tu32 p30e_readbacks;
#endif
\tbool terminal_fails;""",
        "binder test P30E state",
    )
    test = replace_once(
        test,
        """static int mt6797_binder_test_begin_cpu_on(struct mt6797_a72_transaction *transaction)
{
\treturn transaction && transaction->p28_valid ? 0 : -EPROTO;
}

static int mt6797_binder_test_publish_success""",
        """static int mt6797_binder_test_begin_cpu_on(struct mt6797_a72_transaction *transaction)
{
\treturn transaction && transaction->p28_valid ? 0 : -EPROTO;
}

#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
static int
mt6797_binder_test_p30e_prepare(
\tconst struct mt6797_a72_transaction *transaction,
\tstruct mt6797_a72_p30e_handoff *handoff)
{
\tstruct mt6797_binder_test_state *state = mt6797_binder_test_active;

\tif (!transaction || !transaction->p28_valid || !handoff)
\t\treturn -EPROTO;
\tmemset(handoff, 0, sizeof(*handoff));
\thandoff->target_cpu = 8;
\thandoff->slot_pa = SZ_2K;
\thandoff->entry_pa = SZ_4K;
\thandoff->operation = ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP;
\thandoff->generation = TEST_GENERATION;
\thandoff->cookie = TEST_COOKIE;
\thandoff->wire_boot_identity[0] = 1;
\thandoff->target_boot_identity[0] = 1;
\tstate->p30e_prepares++;
\tmt6797_binder_test_event(TEST_EVENT_P30E_PREPARE);
\treturn 0;
}

static int
mt6797_binder_test_p30e_arm(
\tunsigned int cpu, const struct mt6797_a72_p30e_handoff *handoff)
{
\tstruct mt6797_binder_test_state *state = mt6797_binder_test_active;

\tif (!handoff || cpu != 8 || handoff->target_cpu != 8 ||
\t    handoff->operation != ARM64_MT6797_A72_P30E_OPERATION_CPU8_UP ||
\t    handoff->generation != TEST_GENERATION ||
\t    handoff->cookie != TEST_COOKIE)
\t\treturn -EPROTO;
\tstate->p30e_arms++;
\tmt6797_binder_test_event(TEST_EVENT_P30E_ARM);
\treturn 0;
}

static int
mt6797_binder_test_p30e_readback(
\tunsigned int cpu, const struct mt6797_a72_p30e_handoff *handoff,
\tstruct arm64_mt6797_a72_p30e_wire *copy)
{
\tstruct mt6797_binder_test_state *state = mt6797_binder_test_active;
\tu32 target = state->p30e_target_state;

\tif (!handoff || !copy || cpu != 8 || handoff->target_cpu != 8)
\t\treturn -EPROTO;
\tmemset(copy, 0, sizeof(*copy));
\tcopy->word[ARM64_MT6797_A72_P30E_CONTROLLER_STATE_WORD] =
\t\tcpu_to_le64(ARM64_MT6797_A72_P30E_ARMED);
\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_STATE_WORD] =
\t\tcpu_to_le64(target);
\tcopy->word[ARM64_MT6797_A72_P30E_CONTROLLER_SEQUENCE_WORD] =
\t\tcpu_to_le64(1);
\tcopy->word[ARM64_MT6797_A72_P30E_TARGET_SEQUENCE_WORD] =
\t\tcpu_to_le64(target >= ARM64_MT6797_A72_P30E_TARGET_PUBLISHED);
\tstate->p30e_readbacks++;
\tmt6797_binder_test_event(TEST_EVENT_P30E_READBACK);
\treturn target >= ARM64_MT6797_A72_P30E_TARGET_PUBLISHED ? 0 : -EAGAIN;
}
#endif

static int mt6797_binder_test_publish_success""",
        "binder test P30E backend",
    )
    test = replace_once(
        test,
        """\t.membership_complete_p29 = mt6797_binder_test_complete_p29,
\t.membership_begin_cpu_on = mt6797_binder_test_begin_cpu_on,
\t.membership_publish_success = mt6797_binder_test_publish_success,""",
        """\t.membership_complete_p29 = mt6797_binder_test_complete_p29,
\t.membership_begin_cpu_on = mt6797_binder_test_begin_cpu_on,
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\t.p30e_prepare = mt6797_binder_test_p30e_prepare,
\t.p30e_arm = mt6797_binder_test_p30e_arm,
\t.p30e_readback = mt6797_binder_test_p30e_readback,
#endif
\t.membership_publish_success = mt6797_binder_test_publish_success,""",
        "binder test P30E operations",
    )
    test = replace_once(
        test,
        """\tKUNIT_EXPECT_EQ(test, state->membership_finalizes, 1U);
\tKUNIT_EXPECT_EQ(test, state->binder.result.cpu_off_requests, 0U);""",
        """\tKUNIT_EXPECT_EQ(test, state->membership_finalizes, 1U);
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tKUNIT_EXPECT_EQ(test, state->p30e_prepares, 1U);
\tKUNIT_EXPECT_EQ(test, state->p30e_arms, 1U);
\tKUNIT_EXPECT_EQ(test, state->p30e_readbacks, 0U);
\tKUNIT_EXPECT_LT(test, mt6797_binder_test_find(state,
\t\t\t\t\t      TEST_EVENT_P30E_PREPARE),
\t\t\tmt6797_binder_test_find(state, TEST_EVENT_P30E_ARM));
\tKUNIT_EXPECT_LT(test, mt6797_binder_test_find(state,
\t\t\t\t\t      TEST_EVENT_P30E_ARM),
\t\t\tmt6797_binder_test_find(state, TEST_EVENT_CPU_ON));
#endif
\tKUNIT_EXPECT_EQ(test, state->binder.result.cpu_off_requests, 0U);""",
        "binder success P30E ordering",
    )
    test = replace_once(
        test,
        """static void mt6797_binder_one_shot_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;""",
        """#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
static void mt6797_binder_p30e_readback_test(struct kunit *test)
{
\tstatic const u32 target_states[] = {
\t\tARM64_MT6797_A72_P30E_EMPTY,
\t\tARM64_MT6797_A72_P30E_TARGET_CLAIMED,
\t\tARM64_MT6797_A72_P30E_TARGET_PUBLISHED,
\t};
\tunsigned int i;

\tfor (i = 0; i < ARRAY_SIZE(target_states); i++) {
\t\tstruct mt6797_binder_test_state *state;
\t\tstruct mt6797_a72_binder_diagnostic diagnostic;
\t\tbool publish_p32 = false;
\t\tint ret;

\t\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
\t\tKUNIT_ASSERT_NOT_NULL(test, state);
\t\tmt6797_binder_test_active = state;
\t\tmt6797_a72_binder_test_init(&state->binder,
\t\t\t\t\t    &mt6797_binder_test_ops);
\t\tKUNIT_ASSERT_EQ(test, mt6797_a72_binder_test_boot(
\t\t\t&state->binder, 8, mt6797_binder_test_cpu_boot), 0);
\t\tstate->p30e_target_state = target_states[i];
\t\tret = mt6797_a72_binder_test_failure(&state->binder, 8, -EIO,
\t\t\t\t\t     &publish_p32);
\t\tKUNIT_ASSERT_EQ(test, ret, 0);
\t\tKUNIT_EXPECT_TRUE(test, publish_p32);
\t\tmt6797_a72_binder_test_diagnostic(&state->binder, &diagnostic);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_prepare_attempted, 1U);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_prepare_ret, 0);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_arm_attempted, 1U);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_arm_ret, 0);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_armed, 1U);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_readback_attempted, 1U);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_readback_ret,
\t\t\ttarget_states[i] >= ARM64_MT6797_A72_P30E_TARGET_PUBLISHED ?
\t\t\t0 : -EAGAIN);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_controller_state,
\t\t\t\tARM64_MT6797_A72_P30E_ARMED);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_state,
\t\t\t\ttarget_states[i]);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_target_sequence,
\t\t\t\ttarget_states[i] >=
\t\t\t\tARM64_MT6797_A72_P30E_TARGET_PUBLISHED);
\t\tKUNIT_EXPECT_EQ(test, diagnostic.p30e_controller_sequence, 1U);
\t\tKUNIT_EXPECT_EQ(test, state->p30e_readbacks, 1U);
\t\tret = mt6797_a72_binder_test_failure(&state->binder, 8, -EIO,
\t\t\t\t\t     &publish_p32);
\t\tKUNIT_EXPECT_EQ(test, ret, 0);
\t\tKUNIT_EXPECT_EQ(test, state->p30e_readbacks, 1U);
\t}
}
#endif

static void mt6797_binder_one_shot_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;""",
        "binder P30E readback KUnit",
    )
    test = replace_once(
        test,
        """\tKUNIT_CASE(mt6797_binder_sram_selector_mask_test),
\tKUNIT_CASE(mt6797_binder_one_shot_test),""",
        """\tKUNIT_CASE(mt6797_binder_sram_selector_mask_test),
#ifdef CONFIG_ARM64_MT6797_A72_P30E_WIRE
\tKUNIT_CASE(mt6797_binder_p30e_readback_test),
#endif
\tKUNIT_CASE(mt6797_binder_one_shot_test),""",
        "binder P30E KUnit case",
    )

    admission = replace_once(
        admission,
        """\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   \"sram_effect_attempted=%u sram_verified=%u sram_sealed=%u\\n\",
\t\t\t\t   diagnostic.sram_effect_attempted,
\t\t\t\t   diagnostic.sram_verified,
\t\t\t\t   diagnostic.sram_sealed);""",
        """\tlen += sysfs_emit_at(buf, len,
\t\t\t     \"sram_effect_attempted=%u sram_verified=%u sram_sealed=%u \",
\t\t\t     diagnostic.sram_effect_attempted,
\t\t\t     diagnostic.sram_verified,
\t\t\t     diagnostic.sram_sealed);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     \"p30e_prepare_attempted=%u p30e_prepare_ret=%d \",
\t\t\t     diagnostic.p30e_prepare_attempted,
\t\t\t     diagnostic.p30e_prepare_ret);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     \"p30e_arm_attempted=%u p30e_arm_ret=%d p30e_armed=%u \",
\t\t\t     diagnostic.p30e_arm_attempted,
\t\t\t     diagnostic.p30e_arm_ret, diagnostic.p30e_armed);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     \"p30e_readback_attempted=%u p30e_readback_ret=%d \",
\t\t\t     diagnostic.p30e_readback_attempted,
\t\t\t     diagnostic.p30e_readback_ret);
\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   \"p30e_controller_state=%u p30e_target_state=%u p30e_target_sequence=%u p30e_controller_sequence=%u\\n\",
\t\t\t\t   diagnostic.p30e_controller_state,
\t\t\t\t   diagnostic.p30e_target_state,
\t\t\t\t   diagnostic.p30e_target_sequence,
\t\t\t\t   diagnostic.p30e_controller_sequence);""",
        "admission P30E status",
    )

    membership_path.write_text(membership, encoding="utf-8")
    binder_path.write_text(binder, encoding="utf-8")
    internal_path.write_text(internal, encoding="utf-8")
    test_path.write_text(test, encoding="utf-8")
    public_path.write_text(public, encoding="utf-8")
    admission_path.write_text(admission, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: source_edits.py SOURCE_ROOT")
    apply(Path(sys.argv[1]))
