#!/usr/bin/env python3
"""Apply deterministic pre-P28 provider-owner source changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_region_once(path: Path, start: str, end: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"{path}: source region boundary changed")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    path.write_text(before + replacement + end + after, encoding="utf-8")


def write_new(path: Path, source: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def add_acquire_failstop(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    owner = root / "arch/arm64/kernel/mt6797_a72_membership.c"

    replace_once(
        header,
        "#define MT6797_A72_TRANSACTION_ABI 1\n",
        "#define MT6797_A72_TRANSACTION_ABI 2\n",
    )
    replace_once(
        header,
        "\tMT6797_A72_FAULT_P30_QUARANTINE,\n",
        "\tMT6797_A72_FAULT_P30_QUARANTINE,\n"
        "\tMT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN,\n"
        "\tMT6797_A72_FAULT_PROVIDER_RELEASE_RETURN,\n",
    )

    replacement = dedent("""\
    static bool
    mt6797_a72_provider_acquire_response_valid(
    \tconst struct mt6797_a72_provider_response *response,
    \tconst struct mt6797_a72_transaction *transaction)
    {
    \tif (!response || !transaction)
    \t\treturn false;

    \treturn response->abi == MT6797_A72_PROVIDER_CALL_ABI &&
    \t\tresponse->returned == 1 && response->vote_requested == 1 &&
    \t\tresponse->provider_mutated == 1 && response->rail_mutated == 1 &&
    \t\tresponse->settle_us == MT6797_A72_PROVIDER_ACQUIRE_SETTLE_US &&
    \t\tresponse->da921x_page == MT6797_A72_A36_DA921X_PAGE &&
    \t\tresponse->buckb_enabled == 1 &&
    \t\tresponse->buckb_vsel == MT6797_A72_A36_BUCKB_VSEL &&
    \t\tresponse->origin == MT6797_A72_PROVIDER_ORIGIN_M01 &&
    \t\t!response->reserved && response->origin_generation &&
    \t\tresponse->held_handle.generation == response->origin_generation &&
    \t\tresponse->held_handle.generation ==
    \t\t\ttransaction->identity.generation &&
    \t\tresponse->held_handle.cookie == transaction->identity.cookie;
    }

    static bool
    mt6797_a72_provider_refusal_response_valid(
    \tconst struct mt6797_a72_provider_response *response)
    {
    \tif (!response)
    \t\treturn false;

    \treturn response->abi == MT6797_A72_PROVIDER_CALL_ABI &&
    \t\tresponse->returned == 1 && !response->vote_requested &&
    \t\t!response->provider_mutated && !response->rail_mutated &&
    \t\t!response->settle_us && !response->da921x_page &&
    \t\t!response->buckb_enabled && !response->buckb_vsel &&
    \t\t!response->origin && !response->reserved &&
    \t\t!response->origin_generation &&
    \t\t!response->held_handle.generation &&
    \t\t!response->held_handle.cookie;
    }

    static int
    mt6797_a72_membership_latch_provider_fault(
    \tstruct mt6797_a72_transaction *transaction,
    \tenum mt6797_a72_provider_state expected_state,
    \tenum mt6797_a72_owner_fault cause, int error)
    {
    \tunsigned long flags;
    \tint ret = -EPERM;

    \tif (!transaction || !error)
    \t\treturn -EINVAL;

    \tmutex_lock(&a72_transition_lock);
    \traw_spin_lock_irqsave(&a72_state_lock, flags);
    \tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
    \t    a72_owner.phase == MT6797_A72_PHASE_ON_ISSUED &&
    \t    a72_owner.active.valid &&
    \t    a72_owner.active.identity.operation ==
    \t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
    \t    a72_owner.provider_state == expected_state &&
    \t    !memcmp(&a72_owner.active.identity, &transaction->identity,
    \t\t    sizeof(a72_owner.active.identity))) {
    \t\tif (!a72_owner.first_fault.valid) {
    \t\t\ta72_owner.first_fault.identity =
    \t\t\t\ta72_owner.active.identity;
    \t\t\ta72_owner.first_fault.detail = (u32)error;
    \t\t\ta72_owner.first_fault.cause = cause;
    \t\t\ta72_owner.first_fault.valid = 1;
    \t\t}
    \t\ta72_owner.provider_state = MT6797_A72_PROVIDER_FAULT_UNKNOWN;
    \t\ta72_owner.health = MT6797_A72_OWNER_FAULTED;
    \t\ta72_owner.phase = MT6797_A72_PHASE_FAULT;
    \t\t*transaction = a72_owner.active;
    \t\tret = 0;
    \t}
    \traw_spin_unlock_irqrestore(&a72_state_lock, flags);
    \tmutex_unlock(&a72_transition_lock);
    \treturn ret;
    }

    int mt6797_a72_membership_run_provider_acquire(
    \tstruct mt6797_a72_transaction *transaction,
    \tstruct mt6797_a72_provider_response *response)
    {
    \tstruct mt6797_a72_provider_request request = { };
    \tstruct mt6797_a72_provider_acquire_proof proof = { };
    \tstruct mt6797_a72_provider_rejection rejection = { };
    \tint ret;

    \tif (!transaction || !response)
    \t\treturn -EINVAL;

    \tmemset(response, 0, sizeof(*response));
    \tret = mt6797_a72_membership_begin_provider_acquire(transaction);
    \tif (ret)
    \t\treturn ret;

    \trequest.abi = MT6797_A72_PROVIDER_CALL_ABI;
    \trequest.operation = transaction->identity.operation;
    \trequest.settle_us = MT6797_A72_PROVIDER_ACQUIRE_SETTLE_US;
    \trequest.da921x_page = MT6797_A72_A36_DA921X_PAGE;
    \trequest.buckb_vsel = MT6797_A72_A36_BUCKB_VSEL;
    \trequest.transaction_generation = transaction->identity.generation;
    \trequest.transaction_cookie = transaction->identity.cookie;
    \tret = mt6797_a72_provider_acquire(&request, response);
    \tif (!ret) {
    \t\tif (IS_ENABLED(CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT) &&
    \t\t    !mt6797_a72_provider_acquire_response_valid(response,
    \t\t\t\t\t\t\ttransaction)) {
    \t\t\tret = -EPROTO;
    \t\t\tmt6797_a72_membership_latch_provider_fault(transaction,
    \t\t\t\tMT6797_A72_PROVIDER_ACQUIRE_INFLIGHT,
    \t\t\t\tMT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN, ret);
    \t\t\treturn ret;
    \t\t}
    \t\tproof.abi = MT6797_A72_PROVIDER_ACQUIRE_ABI;
    \t\tproof.operation = transaction->identity.operation;
    \t\tproof.settle_us = response->settle_us;
    \t\tproof.da921x_page = response->da921x_page;
    \t\tproof.buckb_enabled = response->buckb_enabled;
    \t\tproof.buckb_vsel = response->buckb_vsel;
    \t\tproof.origin = response->origin;
    \t\tproof.held_identity.generation =
    \t\t\tresponse->held_handle.generation;
    \t\tproof.held_identity.cookie = response->held_handle.cookie;
    \t\tproof.transaction_generation = transaction->identity.generation;
    \t\tproof.transaction_cookie = transaction->identity.cookie;
    \t\tproof.origin_generation = response->origin_generation;
    \t\tret = mt6797_a72_membership_confirm_provider_acquire(
    \t\t\ttransaction, &proof);
    \t\tif (ret &&
    \t\t    IS_ENABLED(CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT))
    \t\t\tmt6797_a72_membership_latch_provider_fault(transaction,
    \t\t\t\tMT6797_A72_PROVIDER_ACQUIRE_INFLIGHT,
    \t\t\t\tMT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN, ret);
    \t\treturn ret;
    \t}

    \t/* The read-only provider may return a structured refusal before a vote. */
    \tif (ret == -EOPNOTSUPP &&
    \t    mt6797_a72_provider_refusal_response_valid(response)) {
    \t\trejection.abi = MT6797_A72_PROVIDER_REJECT_ABI;
    \t\trejection.operation = transaction->identity.operation;
    \t\trejection.result = MT6797_A72_PROVIDER_REJECTED_BEFORE_VOTE;
    \t\trejection.returned = response->returned;
    \t\trejection.transaction_generation =
    \t\t\ttransaction->identity.generation;
    \t\trejection.transaction_cookie = transaction->identity.cookie;
    \t\tif (!mt6797_a72_membership_reject_provider_acquire(
    \t\t\t    transaction, &rejection))
    \t\t\treturn -EOPNOTSUPP;
    \t}

    \tif (IS_ENABLED(CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT))
    \t\tmt6797_a72_membership_latch_provider_fault(transaction,
    \t\t\tMT6797_A72_PROVIDER_ACQUIRE_INFLIGHT,
    \t\t\tMT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN, ret);
    \treturn ret;
    }

    """)
    replace_region_once(
        owner,
        "int mt6797_a72_membership_run_provider_acquire(",
        "static bool\nmt6797_a72_p28_preparation_valid(",
        replacement,
    )


def add_positive_abort(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    owner = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    kconfig = root / "arch/arm64/Kconfig"

    replace_once(
        kconfig,
        "config ARM64_MT6797_A72_P30E_WIRE\n",
        dedent("""\
        config ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT
        \tbool "MT6797 A72 exact pre-P28 provider abort"
        \tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
        \tdepends on REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION
        \thelp
        \t  Add one CPU8-up-only, default-off abort budget after an exact
        \t  positive provider acquire and before any P28 or CPU_ON effect.
        \t  The owner publishes RELEASE_INFLIGHT before the callback, accepts
        \t  only the complete exact-handle inverse proof, and otherwise enters
        \t  reset-only FAULT_UNKNOWN without retry.

        \t  This option adds no production owner opener or caller, P27/P28
        \t  hardware executor, CPU_ON, CPU_OFF, or device action. Say N outside
        \t  the named Gemini Gate-7 hardware-free integration experiment.

        config ARM64_MT6797_A72_P30E_WIRE
        """),
    )
    replace_once(
        header,
        "#define MT6797_A72_PROVIDER_REJECTED_BEFORE_VOTE 1\n",
        "#define MT6797_A72_PROVIDER_REJECTED_BEFORE_VOTE 1\n"
        "#define MT6797_A72_PROVIDER_ABORT_ABI 1\n"
        "#define MT6797_A72_PROVIDER_ABORT_EXACT_RELEASE 1\n",
    )
    replace_once(
        header,
        "\tu8 provider_release;\n\tu8 reserved[3];\n",
        "\tu8 provider_release;\n\tu8 provider_abort;\n\tu8 reserved[2];\n",
    )
    replace_once(
        header,
        "struct mt6797_a72_p28_preparation {\n",
        dedent("""\
        struct mt6797_a72_provider_abort_proof {
        \tu32 abi;
        \tu32 operation;
        \tu32 result;
        \tu32 returned;
        \tu32 vote_requested;
        \tu32 provider_mutated;
        \tu32 rail_mutated;
        \tu32 settle_us;
        \tu32 da921x_page;
        \tu32 buckb_enabled;
        \tu32 buckb_vsel;
        \tu32 origin;
        \tu32 reserved;
        \tstruct mt6797_a72_provider_identity released_identity;
        \tu64 transaction_generation;
        \tu64 transaction_cookie;
        \tu64 origin_generation;
        };

        struct mt6797_a72_p28_preparation {
        """),
    )
    replace_once(
        header,
        "\tstruct mt6797_a72_provider_rejection provider_rejection;\n",
        "\tstruct mt6797_a72_provider_rejection provider_rejection;\n"
        "\tstruct mt6797_a72_provider_abort_proof provider_abort_proof;\n",
    )
    replace_once(
        header,
        "\tu32 provider_rejection_valid;\n",
        "\tu32 provider_rejection_valid;\n\tu32 provider_abort_valid;\n",
    )
    replace_once(
        header,
        "int mt6797_a72_membership_run_provider_acquire(struct mt6797_a72_transaction *transaction,\n"
        "\tstruct mt6797_a72_provider_response *response);\n",
        "int mt6797_a72_membership_run_provider_acquire(struct mt6797_a72_transaction *transaction,\n"
        "\tstruct mt6797_a72_provider_response *response);\n"
        "int mt6797_a72_membership_begin_provider_abort(\n"
        "\tstruct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_confirm_provider_abort(\n"
        "\tstruct mt6797_a72_transaction *transaction,\n"
        "\tconst struct mt6797_a72_provider_abort_proof *proof);\n"
        "int mt6797_a72_membership_run_provider_abort(\n"
        "\tstruct mt6797_a72_transaction *transaction,\n"
        "\tstruct mt6797_a72_provider_response *response);\n",
    )
    replace_once(
        header,
        "static inline int\nmt6797_a72_membership_begin_p28_preparation(\n",
        dedent("""\
        static inline int
        mt6797_a72_membership_begin_provider_abort(
        \tstruct mt6797_a72_transaction *transaction)
        {
        \tif (transaction)
        \t\tmemset(transaction, 0, sizeof(*transaction));
        \treturn -EOPNOTSUPP;
        }

        static inline int
        mt6797_a72_membership_confirm_provider_abort(
        \tstruct mt6797_a72_transaction *transaction,
        \tconst struct mt6797_a72_provider_abort_proof *proof)
        {
        \t(void)proof;
        \tif (transaction)
        \t\tmemset(transaction, 0, sizeof(*transaction));
        \treturn -EOPNOTSUPP;
        }

        static inline int
        mt6797_a72_membership_run_provider_abort(
        \tstruct mt6797_a72_transaction *transaction,
        \tstruct mt6797_a72_provider_response *response)
        {
        \t(void)response;
        \tif (transaction)
        \t\tmemset(transaction, 0, sizeof(*transaction));
        \treturn -EOPNOTSUPP;
        }

        static inline int
        mt6797_a72_membership_begin_p28_preparation(
        """),
    )
    replace_once(
        owner,
        "\t\tbudgets->postprovider_preparation = MT6797_A72_BUDGET_AVAILABLE;\n",
        "\t\tbudgets->postprovider_preparation = MT6797_A72_BUDGET_AVAILABLE;\n"
        "\t\tif (IS_ENABLED(CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT))\n"
        "\t\t\tbudgets->provider_abort = MT6797_A72_BUDGET_AVAILABLE;\n",
    )

    implementation = dedent("""\
    static bool
    mt6797_a72_provider_abort_proof_valid(
    \tconst struct mt6797_a72_provider_abort_proof *proof,
    \tconst struct mt6797_a72_transaction *transaction)
    {
    \tif (!proof || !transaction)
    \t\treturn false;

    \treturn proof->abi == MT6797_A72_PROVIDER_ABORT_ABI &&
    \t\tproof->operation == ARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
    \t\tproof->result == MT6797_A72_PROVIDER_ABORT_EXACT_RELEASE &&
    \t\tproof->returned == 1 && proof->vote_requested == 1 &&
    \t\tproof->provider_mutated == 1 && proof->rail_mutated == 1 &&
    \t\tproof->settle_us == MT6797_A72_PROVIDER_ACQUIRE_SETTLE_US &&
    \t\tproof->da921x_page == MT6797_A72_A36_DA921X_PAGE &&
    \t\t!proof->buckb_enabled &&
    \t\tproof->buckb_vsel == MT6797_A72_A36_BUCKB_VSEL &&
    \t\tproof->origin == MT6797_A72_PROVIDER_ORIGIN_M01 &&
    \t\t!proof->reserved &&
    \t\tmt6797_a72_provider_identity_valid(&proof->released_identity) &&
    \t\t!memcmp(&proof->released_identity,
    \t\t\t&transaction->provider_acquire_proof.held_identity,
    \t\t\tsizeof(proof->released_identity)) &&
    \t\tproof->transaction_generation ==
    \t\t\ttransaction->identity.generation &&
    \t\tproof->transaction_cookie == transaction->identity.cookie &&
    \t\tproof->origin_generation == proof->released_identity.generation;
    }

    int mt6797_a72_membership_begin_provider_abort(
    \tstruct mt6797_a72_transaction *transaction)
    {
    \tunsigned long flags;
    \tint ret = -EPERM;

    \tif (!transaction)
    \t\treturn -EINVAL;
    \tif (!IS_ENABLED(CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT))
    \t\treturn -EOPNOTSUPP;

    \tmutex_lock(&a72_transition_lock);
    \traw_spin_lock_irqsave(&a72_state_lock, flags);
    \tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||
    \t    a72_owner.phase != MT6797_A72_PHASE_ON_ISSUED ||
    \t    !a72_owner.active.valid || !a72_owner.active.p17_p18_published ||
    \t    !a72_owner.active.p27_valid ||
    \t    a72_owner.active.p27_preparation.stage !=
    \t\t    MT6797_A72_P27_STAGE_COMPLETE ||
    \t    a72_owner.active.identity.operation !=
    \t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||
    \t    a72_owner.members ||
    \t    a72_owner.provider_state != MT6797_A72_PROVIDER_HELD ||
    \t    !a72_owner.active.provider_acquire_valid ||
    \t    !mt6797_a72_provider_identity_valid(&a72_owner.provider_identity) ||
    \t    a72_owner.active.provider_abort_valid ||
    \t    a72_owner.active.budgets.provider_abort !=
    \t\t    MT6797_A72_BUDGET_AVAILABLE ||
    \t    a72_owner.active.p28_preparation.stage !=
    \t\t    MT6797_A72_P28_STAGE_NONE ||
    \t    a72_owner.active.p28_valid ||
    \t    a72_owner.active.budgets.postprovider_preparation !=
    \t\t    MT6797_A72_BUDGET_AVAILABLE ||
    \t    a72_owner.active.budgets.cpu_on != MT6797_A72_BUDGET_AVAILABLE ||
    \t    memcmp(&a72_owner.active.provider_identity,
    \t\t   &a72_owner.provider_identity,
    \t\t   sizeof(a72_owner.provider_identity)) ||
    \t    memcmp(&transaction->provider_identity,
    \t\t   &a72_owner.provider_identity,
    \t\t   sizeof(a72_owner.provider_identity)) ||
    \t    memcmp(&a72_owner.active.identity, &transaction->identity,
    \t\t   sizeof(a72_owner.active.identity)))
    \t\tgoto out_state;

    \ta72_owner.active.budgets.provider_abort =
    \t\tMT6797_A72_BUDGET_CONSUMED;
    \ta72_owner.provider_state = MT6797_A72_PROVIDER_RELEASE_INFLIGHT;
    \t*transaction = a72_owner.active;
    \tret = 0;

    out_state:
    \traw_spin_unlock_irqrestore(&a72_state_lock, flags);
    \tmutex_unlock(&a72_transition_lock);
    \treturn ret;
    }

    int mt6797_a72_membership_confirm_provider_abort(
    \tstruct mt6797_a72_transaction *transaction,
    \tconst struct mt6797_a72_provider_abort_proof *proof)
    {
    \tunsigned long flags;
    \tint ret = -EPERM;

    \tif (!transaction || !proof)
    \t\treturn -EINVAL;
    \tif (!IS_ENABLED(CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT))
    \t\treturn -EOPNOTSUPP;

    \tmutex_lock(&a72_transition_lock);
    \traw_spin_lock_irqsave(&a72_state_lock, flags);
    \tif (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||
    \t    a72_owner.phase != MT6797_A72_PHASE_ON_ISSUED ||
    \t    !a72_owner.active.valid ||
    \t    a72_owner.active.identity.operation !=
    \t\t    ARM64_LATE_CPU_STARTUP_OP_CPU8_UP ||
    \t    a72_owner.members ||
    \t    a72_owner.provider_state != MT6797_A72_PROVIDER_RELEASE_INFLIGHT ||
    \t    a72_owner.active.budgets.provider_abort !=
    \t\t    MT6797_A72_BUDGET_CONSUMED ||
    \t    a72_owner.active.provider_abort_valid ||
    \t    a72_owner.active.p28_preparation.stage !=
    \t\t    MT6797_A72_P28_STAGE_NONE ||
    \t    a72_owner.active.p28_valid ||
    \t    a72_owner.active.budgets.postprovider_preparation !=
    \t\t    MT6797_A72_BUDGET_AVAILABLE ||
    \t    a72_owner.active.budgets.cpu_on != MT6797_A72_BUDGET_AVAILABLE ||
    \t    memcmp(&a72_owner.active.identity, &transaction->identity,
    \t\t   sizeof(a72_owner.active.identity)) ||
    \t    !mt6797_a72_provider_abort_proof_valid(proof, &a72_owner.active))
    \t\tgoto out_state;

    \ta72_owner.active.provider_abort_proof = *proof;
    \ta72_owner.active.provider_abort_valid = 1;
    \tmemset(&a72_owner.provider_identity, 0,
    \t       sizeof(a72_owner.provider_identity));
    \tmemset(&a72_owner.active.provider_identity, 0,
    \t       sizeof(a72_owner.active.provider_identity));
    \ta72_owner.provider_state = MT6797_A72_PROVIDER_NONE;
    \t*transaction = a72_owner.active;
    \tret = 0;

    out_state:
    \traw_spin_unlock_irqrestore(&a72_state_lock, flags);
    \tmutex_unlock(&a72_transition_lock);
    \treturn ret;
    }

    int mt6797_a72_membership_run_provider_abort(
    \tstruct mt6797_a72_transaction *transaction,
    \tstruct mt6797_a72_provider_response *response)
    {
    \tstruct mt6797_a72_provider_abort_proof proof = { };
    \tstruct mt6797_a72_provider_handle handle;
    \tint ret;

    \tif (!transaction || !response)
    \t\treturn -EINVAL;
    \tmemset(response, 0, sizeof(*response));
    \tret = mt6797_a72_membership_begin_provider_abort(transaction);
    \tif (ret)
    \t\treturn ret;

    \thandle.generation = transaction->provider_identity.generation;
    \thandle.cookie = transaction->provider_identity.cookie;
    \tret = mt6797_a72_provider_release(&handle, response);
    \tif (ret)
    \t\tgoto out_fault;

    \tproof.abi = MT6797_A72_PROVIDER_ABORT_ABI;
    \tproof.operation = transaction->identity.operation;
    \tproof.result = MT6797_A72_PROVIDER_ABORT_EXACT_RELEASE;
    \tproof.returned = response->returned;
    \tproof.vote_requested = response->vote_requested;
    \tproof.provider_mutated = response->provider_mutated;
    \tproof.rail_mutated = response->rail_mutated;
    \tproof.settle_us = response->settle_us;
    \tproof.da921x_page = response->da921x_page;
    \tproof.buckb_enabled = response->buckb_enabled;
    \tproof.buckb_vsel = response->buckb_vsel;
    \tproof.origin = response->origin;
    \tproof.reserved = response->reserved;
    \tproof.released_identity.generation = response->held_handle.generation;
    \tproof.released_identity.cookie = response->held_handle.cookie;
    \tproof.transaction_generation = transaction->identity.generation;
    \tproof.transaction_cookie = transaction->identity.cookie;
    \tproof.origin_generation = response->origin_generation;
    \tret = mt6797_a72_membership_confirm_provider_abort(transaction, &proof);
    \tif (!ret)
    \t\treturn 0;

    out_fault:
    \tif (!ret)
    \t\tret = -EPROTO;
    \tmt6797_a72_membership_latch_provider_fault(transaction,
    \t\tMT6797_A72_PROVIDER_RELEASE_INFLIGHT,
    \t\tMT6797_A72_FAULT_PROVIDER_RELEASE_RETURN, ret);
    \treturn ret;
    }

    """)
    replace_once(
        owner,
        "static bool\nmt6797_a72_p28_preparation_valid(",
        implementation + "static bool\nmt6797_a72_p28_preparation_valid(",
    )

    replace_once(
        owner,
        "static bool\nmt6797_a72_p29_rollback_valid(\n",
        dedent("""\
        static bool
        mt6797_a72_p29_provider_predecessor_valid(
        \tconst struct mt6797_a72_transaction *transaction)
        {
        \tif (!transaction ||
        \t    transaction->provider_rejection_valid ==
        \t\t    transaction->provider_abort_valid)
        \t\treturn false;

        \tif (transaction->provider_rejection_valid)
        \t\treturn !transaction->provider_acquire_valid &&
        \t\t\t(!IS_ENABLED(
        \t\t\t\tCONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT) ||
        \t\t\t transaction->budgets.provider_abort ==
        \t\t\t\tMT6797_A72_BUDGET_AVAILABLE);

        \treturn transaction->provider_acquire_valid &&
        \t\ttransaction->provider_abort_valid &&
        \t\ttransaction->budgets.provider_abort ==
        \t\t\tMT6797_A72_BUDGET_CONSUMED &&
        \t\tmt6797_a72_provider_abort_proof_valid(
        \t\t\t&transaction->provider_abort_proof, transaction);
        }

        static bool
        mt6797_a72_p29_rollback_valid(
        """),
    )
    replace_once(
        owner,
        "\t    a72_owner.provider_state != MT6797_A72_PROVIDER_NONE ||\n"
        "\t    !a72_owner.active.provider_rejection_valid ||\n",
        "\t    a72_owner.provider_state != MT6797_A72_PROVIDER_NONE ||\n"
        "\t    a72_owner.provider_identity.generation ||\n"
        "\t    a72_owner.provider_identity.cookie ||\n"
        "\t    a72_owner.active.provider_identity.generation ||\n"
        "\t    a72_owner.active.provider_identity.cookie ||\n"
        "\t    !mt6797_a72_p29_provider_predecessor_valid(&a72_owner.active) ||\n",
    )


def add_injectable_endpoint(root: Path) -> None:
    header = root / "drivers/regulator/da9213-legacy-provider-contract.h"
    driver = root / "drivers/regulator/da9213-legacy-regulator.c"

    replace_once(
        header,
        "#include <linux/mt6797-a72-provider.h>\n",
        "#include <linux/mt6797-a72-provider.h>\n#include <linux/mutex.h>\n",
    )
    replace_once(
        header,
        "struct da9213_legacy_provider_transport_ops {\n",
        dedent("""\
        struct da9213_legacy_provider_endpoint {
        \tstruct i2c_adapter *adapter;
        \tu16 address;
        \tconst struct da9213_legacy_provider_transport_ops *ops;
        \tstruct mutex lock;
        \tstruct da9213_legacy_provider_result transaction;
        };

        struct da9213_legacy_provider_transport_ops {
        """),
    )
    replace_once(
        header,
        "int da9213_legacy_provider_transaction_release(struct i2c_adapter *adapter,\n",
        "int da9213_legacy_provider_test_register(\n"
        "\tstruct da9213_legacy_provider_endpoint *endpoint,\n"
        "\tstruct i2c_adapter *adapter, u16 address,\n"
        "\tconst struct da9213_legacy_provider_transport_ops *ops);\n"
        "void da9213_legacy_provider_test_unregister(\n"
        "\tstruct da9213_legacy_provider_endpoint *endpoint);\n"
        "int da9213_legacy_provider_transaction_release(struct i2c_adapter *adapter,\n",
    )
    replace_once(
        driver,
        "\tstruct mutex provider_transaction_lock; /* Serializes lifecycle. */\n"
        "\tstruct da9213_legacy_provider_result provider_transaction;\n",
        "\tstruct da9213_legacy_provider_endpoint provider_endpoint;\n",
    )
    replace_once(
        driver,
        "\tstruct da9213_legacy *chip = context;\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tint ret;\n"
        "#endif\n\n"
        "\tif (!chip || !request || !response)\n",
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tstruct da9213_legacy_provider_endpoint *endpoint = context;\n"
        "\tint ret;\n"
        "#else\n"
        "\tstruct da9213_legacy *chip = context;\n"
        "#endif\n\n"
        "\tif (!context || !request || !response)\n",
    )
    replace_once(
        driver,
        "\tmutex_lock(&chip->provider_transaction_lock);\n"
        "\tret = da9213_legacy_provider_transaction_acquire(chip->client->adapter,\n"
        "\t\t\t\t\t\t\t chip->client->addr,\n"
        "\t\t\t\t\t\t\t &da9213_legacy_positive_provider_ops,\n"
        "\t\t\t\t\t\t\t request, &chip->provider_transaction,\n"
        "\t\t\t\t\t\t\t response);\n"
        "\tmutex_unlock(&chip->provider_transaction_lock);\n",
        "\tmutex_lock(&endpoint->lock);\n"
        "\tret = da9213_legacy_provider_transaction_acquire(endpoint->adapter,\n"
        "\t\t\t\t\t\t\t endpoint->address, endpoint->ops,\n"
        "\t\t\t\t\t\t\t request, &endpoint->transaction,\n"
        "\t\t\t\t\t\t\t response);\n"
        "\tmutex_unlock(&endpoint->lock);\n",
    )
    replace_once(
        driver,
        "\tstruct da9213_legacy *chip = context;\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tint ret;\n"
        "#endif\n\n"
        "\tif (!chip || !handle || !response)\n",
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tstruct da9213_legacy_provider_endpoint *endpoint = context;\n"
        "\tint ret;\n"
        "#else\n"
        "\tstruct da9213_legacy *chip = context;\n"
        "#endif\n\n"
        "\tif (!context || !handle || !response)\n",
    )
    replace_once(
        driver,
        "\tmutex_lock(&chip->provider_transaction_lock);\n"
        "\tret = da9213_legacy_provider_transaction_release(chip->client->adapter,\n"
        "\t\t\t\t\t\t\t chip->client->addr,\n"
        "\t\t\t\t\t\t\t &da9213_legacy_positive_provider_ops,\n"
        "\t\t\t\t\t\t\t handle, &chip->provider_transaction,\n"
        "\t\t\t\t\t\t\t response);\n"
        "\tmutex_unlock(&chip->provider_transaction_lock);\n",
        "\tmutex_lock(&endpoint->lock);\n"
        "\tret = da9213_legacy_provider_transaction_release(endpoint->adapter,\n"
        "\t\t\t\t\t\t\t endpoint->address, endpoint->ops,\n"
        "\t\t\t\t\t\t\t handle, &endpoint->transaction,\n"
        "\t\t\t\t\t\t\t response);\n"
        "\tmutex_unlock(&endpoint->lock);\n",
    )
    replace_once(
        driver,
        "static void da9213_legacy_provider_unregister(void *context)\n",
        dedent("""\
        #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST)
        int da9213_legacy_provider_test_register(
        \tstruct da9213_legacy_provider_endpoint *endpoint,
        \tstruct i2c_adapter *adapter, u16 address,
        \tconst struct da9213_legacy_provider_transport_ops *ops)
        {
        \tif (!endpoint || !adapter || !ops)
        \t\treturn -EINVAL;

        \tmemset(endpoint, 0, sizeof(*endpoint));
        \tendpoint->adapter = adapter;
        \tendpoint->address = address;
        \tendpoint->ops = ops;
        \tmutex_init(&endpoint->lock);
        \treturn mt6797_a72_provider_register(&da9213_legacy_provider_ops,
        \t\t\t\t\t    endpoint);
        }

        void da9213_legacy_provider_test_unregister(
        \tstruct da9213_legacy_provider_endpoint *endpoint)
        {
        \tmt6797_a72_provider_unregister(&da9213_legacy_provider_ops, endpoint);
        }
        #endif

        static void da9213_legacy_provider_unregister(void *context)
        """),
    )
    replace_once(
        driver,
        "static int da9213_legacy_register_owner(struct da9213_legacy *chip)\n"
        "{\n"
        "\tint ret;\n\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tmutex_init(&chip->provider_transaction_lock);\n"
        "#endif\n"
        "\tret = mt6797_a72_provider_register(&da9213_legacy_provider_ops, chip);\n",
        "static int da9213_legacy_register_owner(struct da9213_legacy *chip)\n"
        "{\n"
        "\tvoid *context = chip;\n"
        "\tint ret;\n\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tchip->provider_endpoint.adapter = chip->client->adapter;\n"
        "\tchip->provider_endpoint.address = chip->client->addr;\n"
        "\tchip->provider_endpoint.ops = &da9213_legacy_positive_provider_ops;\n"
        "\tmutex_init(&chip->provider_endpoint.lock);\n"
        "\tcontext = &chip->provider_endpoint;\n"
        "#endif\n"
        "\tret = mt6797_a72_provider_register(&da9213_legacy_provider_ops,\n"
        "\t\t\t\t\t    context);\n",
    )
    replace_once(
        driver,
        "\tret = devm_add_action_or_reset(chip->dev,\n"
        "\t\t\t\t       da9213_legacy_provider_unregister, chip);\n",
        "\tret = devm_add_action_or_reset(chip->dev,\n"
        "\t\t\t\t       da9213_legacy_provider_unregister, context);\n",
    )


def add_kunit(root: Path, source_dir: Path) -> None:
    arm64_kconfig = root / "arch/arm64/Kconfig"
    membership_header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    membership_source = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    kconfig = root / "drivers/regulator/Kconfig"
    makefile = root / "drivers/regulator/Makefile"
    write_new(
        root / "drivers/regulator/da9213-legacy-membership-test.c",
        source_dir / "da9213-legacy-membership-test.c",
    )
    replace_once(
        arm64_kconfig,
        "config ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n",
        dedent("""\
        config ARM64_MT6797_A72_P24_OWNER_TEST_SEED
        \tbool
        \tdepends on KUNIT=y
        \tdepends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
        \thelp
        \t  Build only the lifecycle reset and test-seeded AVAILABLE helpers.
        \t  This hidden symbol has no production selector or caller.

        config ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST
        """),
    )
    replace_once(
        arm64_kconfig,
        "\tselect ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n"
        "\tselect ARM64_MT6797_A72_P24_ADMISSION_HOOKS\n",
        "\tselect ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n"
        "\tselect ARM64_MT6797_A72_P24_ADMISSION_HOOKS\n"
        "\tselect ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n",
    )
    replace_once(
        membership_header,
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n"
        "void mt6797_a72_membership_test_reset(void);\n",
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n"
        "void mt6797_a72_membership_test_reset(void);\n",
    )
    replace_once(
        membership_source,
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n"
        "void mt6797_a72_membership_test_reset(void)\n",
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n"
        "void mt6797_a72_membership_test_reset(void)\n",
    )
    replace_once(
        kconfig,
        "config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST\n",
        dedent("""\
        config REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST
        \tbool "KUnit tests for the DA921x pre-P28 membership abort"
        \tdepends on KUNIT=y
        \tdepends on REGULATOR_DA9213_LEGACY=y
        \tdepends on REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION
        \tdepends on ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT
        \tdepends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
        \tselect ARM64_MT6797_A72_P24_OWNER_TEST_SEED
        \thelp
        \t  Traverse the production membership owner, provider registry, and
        \t  positive DA921x transaction with an unregistered in-memory adapter.
        \t  Cover exact release/P29 retirement, acquire and release failures,
        \t  malformed returns, stale handles, duplicate abort, and P29 guards.

        \t  The suite performs no physical I2C, MMIO, P28, CPU_ON, CPU_OFF,
        \t  boot-image, or device action. Say N outside the named experiment.

        config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST) += da9213-legacy-provider-test.o\n",
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST) += da9213-legacy-provider-test.o\n"
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST) += da9213-legacy-membership-test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase",
        choices=("failstop", "abort", "endpoint", "kunit"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    source_dir = Path(__file__).resolve().parent.parent / "source"
    if args.phase == "failstop":
        add_acquire_failstop(root)
    elif args.phase == "abort":
        add_positive_abort(root)
    elif args.phase == "endpoint":
        add_injectable_endpoint(root)
    else:
        add_kunit(root, source_dir)


if __name__ == "__main__":
    main()
