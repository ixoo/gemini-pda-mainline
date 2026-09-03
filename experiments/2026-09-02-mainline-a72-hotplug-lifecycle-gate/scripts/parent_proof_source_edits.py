#!/usr/bin/env python3
"""Add the disconnected exact CPU8/CPU9 parent-proof producers."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


MEMBERSHIP_CONTRACT = dedent("""\
    #define MT6797_A72_INITIAL_PARENT_PROOF_ABI 1U

    struct mt6797_a72_initial_parent_proof {
    \tu32 abi;
    \tu32 exact;
    \tu32 health;
    \tu32 owner_phase;
    \tu32 hotplug_phase;
    \tu32 members;
    \tu32 retired_mask;
    \tu32 hotplug_retired_mask;
    \tu32 provider_state;
    \tu32 controller_present;
    \tu32 active_present;
    \tu32 hotplug_active_present;
    \tstruct mt6797_a72_transaction_identity cpu8;
    \tstruct mt6797_a72_transaction_identity cpu9;
    \tstruct mt6797_a72_provider_identity provider_identity;
    };

    """)


MEMBERSHIP_DECLARATION = dedent("""\
    #if IS_ENABLED(CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL) && \\
    \tIS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)
    int mt6797_a72_membership_initial_parent_proof(
    \tstruct mt6797_a72_initial_parent_proof *proof);
    #else
    static inline int mt6797_a72_membership_initial_parent_proof(
    \tstruct mt6797_a72_initial_parent_proof *proof)
    {
    \tif (proof)
    \t\t*proof = (struct mt6797_a72_initial_parent_proof){};
    \treturn -EOPNOTSUPP;
    }
    #endif

    """)


MEMBERSHIP_PRODUCER = dedent("""\
    int mt6797_a72_membership_initial_parent_proof(
    \tstruct mt6797_a72_initial_parent_proof *proof)
    {
    \tunsigned long flags;
    \tint ret = -EPERM;

    \tif (!proof)
    \t\treturn -EINVAL;
    \tmemset(proof, 0, sizeof(*proof));
    \tmutex_lock(&a72_transition_lock);
    \traw_spin_lock_irqsave(&a72_state_lock, flags);
    \tif (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
    \t    a72_owner.bootstrap_valid && a72_owner.members_valid &&
    \t    a72_owner.phase == MT6797_A72_PHASE_IDLE &&
    \t    a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_IDLE &&
    \t    a72_owner.members == (BIT(0) | BIT(1)) &&
    \t    a72_owner.retired_mask == (BIT(0) | BIT(1)) &&
    \t    !a72_owner.hotplug_retired_mask &&
    \t    a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
    \t    mt6797_a72_provider_identity_valid(
    \t\t    &a72_owner.provider_identity) &&
    \t    !a72_owner.active.valid && !a72_owner.hotplug_active.valid &&
    \t    !a72_owner.controller && !a72_owner.controller_cookie &&
    \t    mt6797_a72_cpu9_terminal_parent_valid_locked()) {
    \t\tproof->abi = MT6797_A72_INITIAL_PARENT_PROOF_ABI;
    \t\tproof->exact = 1;
    \t\tproof->health = a72_owner.health;
    \t\tproof->owner_phase = a72_owner.phase;
    \t\tproof->hotplug_phase = a72_owner.hotplug_phase;
    \t\tproof->members = a72_owner.members;
    \t\tproof->retired_mask = a72_owner.retired_mask;
    \t\tproof->hotplug_retired_mask =
    \t\t\ta72_owner.hotplug_retired_mask;
    \t\tproof->provider_state = a72_owner.provider_state;
    \t\tproof->controller_present = !!a72_owner.controller;
    \t\tproof->active_present = a72_owner.active.valid;
    \t\tproof->hotplug_active_present =
    \t\t\ta72_owner.hotplug_active.valid;
    \t\tproof->cpu8 = a72_owner.retired[0].identity;
    \t\tproof->cpu9 = a72_owner.retired[1].identity;
    \t\tproof->provider_identity = a72_owner.provider_identity;
    \t\tret = 0;
    \t}
    \traw_spin_unlock_irqrestore(&a72_state_lock, flags);
    \tmutex_unlock(&a72_transition_lock);
    \treturn ret;
    }

    """)


MEMBERSHIP_TEST = dedent("""\
    static void mt6797_a72_initial_parent_proof_test(struct kunit *test)
    {
    \tstruct mt6797_a72_owner_test_state *state = test->priv;
    \tstruct mt6797_a72_initial_parent_proof proof;
    \tint ret;

    \tret = mt6797_a72_membership_initial_parent_proof(NULL);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tmemset(&proof, 0xa5, sizeof(proof));
    \tret = mt6797_a72_membership_initial_parent_proof(&proof);
    \tKUNIT_EXPECT_EQ(test, ret, -EPERM);
    \tKUNIT_EXPECT_EQ(test, proof.abi, 0U);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 0U);

    \tret = mt6797_a72_test_seed_cpu9_terminal(&state->transaction);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \towner_observe(&state->before);
    \tret = mt6797_a72_membership_initial_parent_proof(&proof);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, proof.abi,
    \t\t\tMT6797_A72_INITIAL_PARENT_PROOF_ABI);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 1U);
    \tKUNIT_EXPECT_EQ(test, proof.health,
    \t\t\t(u32)MT6797_A72_OWNER_AVAILABLE);
    \tKUNIT_EXPECT_EQ(test, proof.owner_phase,
    \t\t\t(u32)MT6797_A72_PHASE_IDLE);
    \tKUNIT_EXPECT_EQ(test, proof.hotplug_phase,
    \t\t\t(u32)MT6797_A72_HOTPLUG_IDLE);
    \tKUNIT_EXPECT_EQ(test, proof.members, (u32)(BIT(0) | BIT(1)));
    \tKUNIT_EXPECT_EQ(test, proof.retired_mask,
    \t\t\t(u32)(BIT(0) | BIT(1)));
    \tKUNIT_EXPECT_EQ(test, proof.hotplug_retired_mask, 0U);
    \tKUNIT_EXPECT_EQ(test, proof.provider_state,
    \t\t\t(u32)MT6797_A72_PROVIDER_HELD);
    \tKUNIT_EXPECT_EQ(test, proof.controller_present, 0U);
    \tKUNIT_EXPECT_EQ(test, proof.active_present, 0U);
    \tKUNIT_EXPECT_EQ(test, proof.hotplug_active_present, 0U);
    \tKUNIT_EXPECT_EQ(test, proof.cpu8.target_cpu, 8U);
    \tKUNIT_EXPECT_EQ(test, proof.cpu8.target_mpidr, 0x200ULL);
    \tKUNIT_EXPECT_EQ(test, proof.cpu9.target_cpu, 9U);
    \tKUNIT_EXPECT_EQ(test, proof.cpu9.target_mpidr, 0x201ULL);
    \tKUNIT_EXPECT_EQ(test, proof.provider_identity.generation,
    \t\t\tstate->before.owner.provider_identity.generation);
    \tKUNIT_EXPECT_EQ(test, proof.provider_identity.cookie,
    \t\t\tstate->before.owner.provider_identity.cookie);
    \towner_observe(&state->after);
    \texpect_unchanged(test, &state->before, &state->after);

    \tret = mt6797_a72_hotplug_prepare_down(9, CPUHP_OFFLINE,
    \t\t\t\t\t      true, true, &state->hotplug);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \towner_observe(&state->before);
    \tmemset(&proof, 0xa5, sizeof(proof));
    \tret = mt6797_a72_membership_initial_parent_proof(&proof);
    \tKUNIT_EXPECT_EQ(test, ret, -EPERM);
    \tKUNIT_EXPECT_EQ(test, proof.abi, 0U);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 0U);
    \towner_observe(&state->after);
    \texpect_unchanged(test, &state->before, &state->after);
    }

    """)


BINDER_CONTRACT = dedent("""\
    #define MT6797_A72_BINDER_PARENT_PROOF_ABI 1U
    #define MT6797_A72_BINDER_PARENT_MAX_AGE_MS 5000U
    #define MT6797_A72_BINDER_PARENT_ONLINE_MASK GENMASK(9, 0)

    struct mt6797_a72_binder_parent_identity {
    \tu32 abi;
    \tu32 owner;
    \tu32 operation;
    \tu32 target_cpu;
    \tu32 cpuhp_target;
    \tu64 target_mpidr;
    \tu64 cpu_on_entry_pa;
    \tu64 generation;
    \tu64 cookie;
    };

    struct mt6797_a72_binder_parent_proof {
    \tu32 abi;
    \tu32 exact;
    \tu32 health;
    \tu32 owner_phase;
    \tu32 hotplug_phase;
    \tu32 members;
    \tu32 retired_mask;
    \tu32 hotplug_retired_mask;
    \tu32 provider_state;
    \tu32 controller_present;
    \tu32 active_present;
    \tu32 hotplug_active_present;
    \tu32 online_mask;
    \tu32 online_count;
    \tstruct mt6797_a72_binder_parent_identity cpu8;
    \tstruct mt6797_a72_binder_parent_identity cpu9;
    \tu64 provider_generation;
    \tu64 provider_cookie;
    \tu64 watchdog_identity;
    \tu64 watchdog_takeover_ns;
    \tu64 observed_ns;
    \tu64 watchdog_age_ns;
    };

    """)


BINDER_DECLARATION = dedent("""\
    int mt6797_a72_binder_parent_proof(
    \tstruct mt6797_a72_binder_parent_proof *proof);
    """)


BINDER_STUB = dedent("""\
    static inline int mt6797_a72_binder_parent_proof(
    \tstruct mt6797_a72_binder_parent_proof *proof)
    {
    \tif (proof)
    \t\t*proof = (struct mt6797_a72_binder_parent_proof){};
    \treturn -EOPNOTSUPP;
    }

    """)


BINDER_PROOF = dedent("""\
    static bool mt6797_a72_binder_backend_valid(
    \tconst struct mt6797_a72_binder_backend_ops *ops);

    static void mt6797_a72_binder_copy_parent_identity(
    \tstruct mt6797_a72_binder_parent_identity *destination,
    \tconst struct mt6797_a72_transaction_identity *source)
    {
    \tdestination->abi = source->abi;
    \tdestination->owner = source->owner;
    \tdestination->operation = source->operation;
    \tdestination->target_cpu = source->target_cpu;
    \tdestination->cpuhp_target = source->cpuhp_target;
    \tdestination->target_mpidr = source->target_mpidr;
    \tdestination->cpu_on_entry_pa = source->cpu_on_entry_pa;
    \tdestination->generation = source->generation;
    \tdestination->cookie = source->cookie;
    }

    static int mt6797_a72_binder_parent_proof_locked(
    \tconst struct mt6797_a72_binder *binder,
    \tstruct mt6797_a72_binder_parent_proof *proof)
    {
    \tstruct mt6797_a72_initial_parent_proof membership = { };
    \tstruct mtk_wdt_recovery_validation watchdog = { };
    \tconst struct mt6797_a72_transition_result *result = &binder->result;
    \tconst u32 retained = MT6797_A72_TRANSITION_OWNED_P27 |
    \t\tMT6797_A72_TRANSITION_OWNED_PROVIDER |
    \t\tMT6797_A72_TRANSITION_OWNED_CPU8;
    \tu64 observed_ns;
    \tu32 online_count;
    \tu32 online_mask = 0;
    \tunsigned int cpu;
    \tint ret;

    \tmemset(proof, 0, sizeof(*proof));
    \tif (!mt6797_a72_binder_backend_valid(binder->backend))
    \t\treturn -EPROTO;
    \tret = binder->backend->membership_parent_proof(&membership);
    \tif (ret)
    \t\treturn ret;
    \tfor (cpu = 0; cpu <= MT6797_A72_TRANSITION_CPU9; cpu++)
    \t\tif (binder->backend->cpu_online(cpu))
    \t\t\tonline_mask |= BIT(cpu);
    \tonline_count = binder->backend->cpu_online_count();
    \tret = binder->backend->watchdog_validate(
    \t\tbinder->watchdog, result->watchdog_identity, &watchdog);
    \tif (ret)
    \t\treturn ret;
    \tobserved_ns = binder->backend->monotonic_ns();

    \tif (membership.abi != MT6797_A72_INITIAL_PARENT_PROOF_ABI ||
    \t    membership.exact != 1 ||
    \t    membership.health != MT6797_A72_OWNER_AVAILABLE ||
    \t    membership.owner_phase != MT6797_A72_PHASE_IDLE ||
    \t    membership.hotplug_phase != MT6797_A72_HOTPLUG_IDLE ||
    \t    membership.members != (BIT(0) | BIT(1)) ||
    \t    membership.retired_mask != (BIT(0) | BIT(1)) ||
    \t    membership.hotplug_retired_mask ||
    \t    membership.provider_state != MT6797_A72_PROVIDER_HELD ||
    \t    membership.controller_present || membership.active_present ||
    \t    membership.hotplug_active_present ||
    \t    atomic_read(&binder->boot_claimed) != 1 ||
    \t    atomic_read(&binder->transition.consumed) != 1 ||
    \t    atomic_read_acquire(&binder->transition.lifecycle) !=
    \t\t    MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL ||
    \t    result->terminal != MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF ||
    \t    result->last_stage != MT6797_A72_TRANSITION_STAGE_MEMBERSHIP ||
    \t    result->stage_errno || result->rollback_errno ||
    \t    result->checkpoint_errno || !result->attempted ||
    \t    !result->watchdog_armed || !result->p27_owned ||
    \t    !result->provider_owned || !result->membership_published ||
    \t    !result->cpu8_online || result->cpu9_online ||
    \t    result->rollback_mask || result->retained_mask != retained ||
    \t    result->cpu_requests != 1 || result->cpu_off_requests ||
    \t    result->retries || result->terminal_commits != 1 ||
    \t    !binder->transaction.valid ||
    \t    !binder->transaction.cpu8_success_published ||
    \t    memcmp(&binder->transaction.identity, &membership.cpu8,
    \t\t   sizeof(membership.cpu8)) ||
    \t    memcmp(&binder->transaction.provider_identity,
    \t\t   &membership.provider_identity,
    \t\t   sizeof(membership.provider_identity)) ||
    \t    online_mask != MT6797_A72_BINDER_PARENT_ONLINE_MASK ||
    \t    online_count != 10 || !result->watchdog_identity ||
    \t    !binder->watchdog_takeover_ns ||
    \t    watchdog.identity != result->watchdog_identity ||
    \t    watchdog.owned != 1 || observed_ns < binder->watchdog_takeover_ns)
    \t\treturn -EPROTO;
    \tif (observed_ns - binder->watchdog_takeover_ns >
    \t    MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL)
    \t\treturn -ETIME;

    \tproof->abi = MT6797_A72_BINDER_PARENT_PROOF_ABI;
    \tproof->exact = 1;
    \tproof->health = membership.health;
    \tproof->owner_phase = membership.owner_phase;
    \tproof->hotplug_phase = membership.hotplug_phase;
    \tproof->members = membership.members;
    \tproof->retired_mask = membership.retired_mask;
    \tproof->hotplug_retired_mask = membership.hotplug_retired_mask;
    \tproof->provider_state = membership.provider_state;
    \tproof->controller_present = membership.controller_present;
    \tproof->active_present = membership.active_present;
    \tproof->hotplug_active_present = membership.hotplug_active_present;
    \tproof->online_mask = online_mask;
    \tproof->online_count = online_count;
    \tmt6797_a72_binder_copy_parent_identity(&proof->cpu8,
    \t\t\t\t\t       &membership.cpu8);
    \tmt6797_a72_binder_copy_parent_identity(&proof->cpu9,
    \t\t\t\t\t       &membership.cpu9);
    \tproof->provider_generation = membership.provider_identity.generation;
    \tproof->provider_cookie = membership.provider_identity.cookie;
    \tproof->watchdog_identity = result->watchdog_identity;
    \tproof->watchdog_takeover_ns = binder->watchdog_takeover_ns;
    \tproof->observed_ns = observed_ns;
    \tproof->watchdog_age_ns = observed_ns - binder->watchdog_takeover_ns;
    \treturn 0;
    }

    int mt6797_a72_binder_parent_proof(
    \tstruct mt6797_a72_binder_parent_proof *proof)
    {
    \tstruct mt6797_a72_binder *binder;
    \tint ret;

    \tif (!proof)
    \t\treturn -EINVAL;
    \tmemset(proof, 0, sizeof(*proof));
    \tmutex_lock(&mt6797_a72_binder_publish_lock);
    \tbinder = mt6797_a72_binder_ready();
    \tret = binder ? mt6797_a72_binder_parent_proof_locked(binder, proof) :
    \t\t-EAGAIN;
    \tmutex_unlock(&mt6797_a72_binder_publish_lock);
    \treturn ret;
    }

    """)


BINDER_TEST_SUPPORT = dedent("""\
    static int mt6797_binder_test_parent_proof(
    \tstruct mt6797_a72_initial_parent_proof *proof)
    {
    \tstruct mt6797_binder_test_state *state = mt6797_binder_test_active;
    \tconst struct mt6797_a72_transaction_identity *cpu8 =
    \t\t&state->binder.transaction.identity;

    \tmemset(proof, 0, sizeof(*proof));
    \tif (!state->parent_available)
    \t\treturn -EPERM;
    \tproof->abi = MT6797_A72_INITIAL_PARENT_PROOF_ABI;
    \tproof->exact = 1;
    \tproof->health = MT6797_A72_OWNER_AVAILABLE;
    \tproof->owner_phase = MT6797_A72_PHASE_IDLE;
    \tproof->hotplug_phase = MT6797_A72_HOTPLUG_IDLE;
    \tproof->members = BIT(0) | BIT(1);
    \tproof->retired_mask = BIT(0) | BIT(1);
    \tproof->provider_state = MT6797_A72_PROVIDER_HELD;
    \tproof->cpu8 = *cpu8;
    \tproof->cpu9.abi = MT6797_A72_TRANSACTION_ABI;
    \tproof->cpu9.owner = ARM64_LATE_CPU_STARTUP_OWNER_MEMBERSHIP;
    \tproof->cpu9.operation = ARM64_LATE_CPU_STARTUP_OP_CPU9_UP;
    \tproof->cpu9.target_cpu = 9;
    \tproof->cpu9.cpuhp_target = CPUHP_ONLINE;
    \tproof->cpu9.target_mpidr = 0x201;
    \tproof->cpu9.generation = TEST_CPU9_GENERATION;
    \tproof->cpu9.cookie = TEST_CPU9_COOKIE;
    \tproof->provider_identity = state->binder.transaction.provider_identity;
    \treturn 0;
    }

    static int mt6797_binder_test_watchdog_validate(
    \tstruct device *dev, u64 identity,
    \tstruct mtk_wdt_recovery_validation *validation)
    {
    \tstruct mt6797_binder_test_state *state = mt6797_binder_test_active;

    \t(void)dev;
    \tmemset(validation, 0, sizeof(*validation));
    \tstate->watchdog_validations++;
    \tif (identity != TEST_WATCHDOG_IDENTITY)
    \t\treturn -EACCES;
    \tvalidation->identity = identity;
    \tvalidation->owned = 1;
    \treturn 0;
    }

    static u64 mt6797_binder_test_monotonic_ns(void)
    {
    \treturn mt6797_binder_test_active->monotonic_ns ?:
    \t\tTEST_TAKEOVER_NS;
    }

    static unsigned int mt6797_binder_test_online_count(void)
    {
    \tstruct mt6797_binder_test_state *state = mt6797_binder_test_active;

    \treturn 8 + state->cpu8_online + state->cpu9_online;
    }

    """)


BINDER_TEST = dedent("""\
    static void mt6797_binder_parent_proof_test(struct kunit *test)
    {
    \tstruct mt6797_binder_test_state *state = test->priv;
    \tstruct mt6797_a72_binder_parent_proof proof;
    \tstruct mt6797_a72_binder *before;
    \tint ret;

    \tbefore = kunit_kzalloc(test, sizeof(*before), GFP_KERNEL);
    \tKUNIT_ASSERT_NOT_NULL(test, before);
    \tKUNIT_ASSERT_EQ(test, mt6797_binder_test_run_to_completion(state), 0);
    \tstate->cpu9_online = true;
    \tstate->parent_available = true;
    \tstate->monotonic_ns = TEST_TAKEOVER_NS + 2000000000ULL;
    \t*before = state->binder;
    \tret = mt6797_a72_binder_test_parent_proof(&state->binder, &proof);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, proof.abi,
    \t\t\tMT6797_A72_BINDER_PARENT_PROOF_ABI);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 1U);
    \tKUNIT_EXPECT_EQ(test, proof.members, (u32)(BIT(0) | BIT(1)));
    \tKUNIT_EXPECT_EQ(test, proof.online_mask,
    \t\t\tMT6797_A72_BINDER_PARENT_ONLINE_MASK);
    \tKUNIT_EXPECT_EQ(test, proof.online_count, 10U);
    \tKUNIT_EXPECT_EQ(test, proof.cpu8.target_cpu, 8U);
    \tKUNIT_EXPECT_EQ(test, proof.cpu8.target_mpidr, 0x200ULL);
    \tKUNIT_EXPECT_EQ(test, proof.cpu9.target_cpu, 9U);
    \tKUNIT_EXPECT_EQ(test, proof.cpu9.target_mpidr, 0x201ULL);
    \tKUNIT_EXPECT_EQ(test, proof.provider_generation,
    \t\t\tTEST_PROVIDER_GENERATION);
    \tKUNIT_EXPECT_EQ(test, proof.provider_cookie, TEST_PROVIDER_COOKIE);
    \tKUNIT_EXPECT_EQ(test, proof.watchdog_identity,
    \t\t\tTEST_WATCHDOG_IDENTITY);
    \tKUNIT_EXPECT_EQ(test, proof.watchdog_takeover_ns, TEST_TAKEOVER_NS);
    \tKUNIT_EXPECT_EQ(test, proof.watchdog_age_ns, 2000000000ULL);
    \tKUNIT_EXPECT_EQ(test, state->watchdog_validations, 1U);
    \tKUNIT_EXPECT_EQ(test, memcmp(before, &state->binder,
    \t\t\t\t       sizeof(*before)), 0);

    \tstate->cpu9_online = false;
    \tmemset(&proof, 0xa5, sizeof(proof));
    \tret = mt6797_a72_binder_test_parent_proof(&state->binder, &proof);
    \tKUNIT_EXPECT_EQ(test, ret, -EPROTO);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 0U);
    \tstate->cpu9_online = true;

    \tstate->monotonic_ns = TEST_TAKEOVER_NS + 5000000001ULL;
    \tmemset(&proof, 0xa5, sizeof(proof));
    \tret = mt6797_a72_binder_test_parent_proof(&state->binder, &proof);
    \tKUNIT_EXPECT_EQ(test, ret, -ETIME);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 0U);
    \tstate->monotonic_ns = TEST_TAKEOVER_NS + 2000000000ULL;

    \tstate->parent_available = false;
    \tmemset(&proof, 0xa5, sizeof(proof));
    \tret = mt6797_a72_binder_test_parent_proof(&state->binder, &proof);
    \tKUNIT_EXPECT_EQ(test, ret, -EPERM);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 0U);
    \tstate->parent_available = true;

    \tstate->binder.result.terminal =
    \t\tMT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO;
    \tmemset(&proof, 0xa5, sizeof(proof));
    \tret = mt6797_a72_binder_test_parent_proof(&state->binder, &proof);
    \tKUNIT_EXPECT_EQ(test, ret, -EPROTO);
    \tKUNIT_EXPECT_EQ(test, proof.exact, 0U);
    }

    """)


def edit_membership(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    source = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    test = root / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    replace_once(
        header,
        "struct mt6797_a72_call_budgets {\n",
        MEMBERSHIP_CONTRACT + "struct mt6797_a72_call_budgets {\n",
    )
    replace_once(
        header,
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n",
        MEMBERSHIP_DECLARATION +
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n",
    )
    replace_once(
        source,
        "static bool\nmt6797_a72_cpu9_active_valid_locked(",
        MEMBERSHIP_PRODUCER +
        "static bool\nmt6797_a72_cpu9_active_valid_locked(",
    )
    replace_once(
        test,
        "static void mt6797_a72_hotplug_success_lifecycle(struct kunit *test)\n",
        MEMBERSHIP_TEST +
        "static void mt6797_a72_hotplug_success_lifecycle(struct kunit *test)\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_rejection_one_shot),\n",
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_rejection_one_shot),\n"
        "\tKUNIT_CASE(mt6797_a72_initial_parent_proof_test),\n",
    )


def edit_binder(root: Path) -> None:
    header = root / "include/linux/soc/mediatek/mt6797-a72-binder.h"
    internal = root / "drivers/soc/mediatek/mt6797-a72-binder-internal.h"
    source = root / "drivers/soc/mediatek/mt6797-a72-binder.c"
    test = root / "drivers/soc/mediatek/mt6797-a72-binder-test.c"

    replace_once(
        header,
        "struct mt6797_a72_binder_diagnostic {\n",
        BINDER_CONTRACT + "struct mt6797_a72_binder_diagnostic {\n",
    )
    replace_once(
        header,
        "bool mt6797_a72_binder_available(void);\n",
        "bool mt6797_a72_binder_available(void);\n" + BINDER_DECLARATION,
    )
    replace_once(
        header,
        "static inline bool mt6797_a72_binder_available(void)\n",
        BINDER_STUB + "static inline bool mt6797_a72_binder_available(void)\n",
    )
    replace_once(
        internal,
        "\tint (*membership_finalize_success)(struct mt6797_a72_transaction *transaction);\n",
        "\tint (*membership_finalize_success)(struct mt6797_a72_transaction *transaction);\n"
        "\tint (*membership_parent_proof)(\n"
        "\t\tstruct mt6797_a72_initial_parent_proof *proof);\n",
    )
    replace_once(
        internal,
        "\tint (*watchdog_takeover)(struct device *dev, unsigned int timeout_ms,\n"
        "\t\t\t\t struct mtk_wdt_recovery_result *result);\n",
        "\tint (*watchdog_takeover)(struct device *dev, unsigned int timeout_ms,\n"
        "\t\t\t\t struct mtk_wdt_recovery_result *result);\n"
        "\tint (*watchdog_validate)(\n"
        "\t\tstruct device *dev, u64 identity,\n"
        "\t\tstruct mtk_wdt_recovery_validation *validation);\n"
        "\tu64 (*monotonic_ns)(void);\n",
    )
    replace_once(
        internal,
        "\tbool (*cpu_online)(unsigned int cpu);\n",
        "\tbool (*cpu_online)(unsigned int cpu);\n"
        "\tunsigned int (*cpu_online_count)(void);\n",
    )
    replace_once(
        internal,
        "\tatomic_t boot_claimed;\n",
        "\tatomic_t boot_claimed;\n\tu64 watchdog_takeover_ns;\n",
    )
    replace_once(
        internal,
        "void\nmt6797_a72_binder_test_diagnostic(",
        "int mt6797_a72_binder_test_parent_proof(\n"
        "\tconst struct mt6797_a72_binder *binder,\n"
        "\tstruct mt6797_a72_binder_parent_proof *proof);\n"
        "void\nmt6797_a72_binder_test_diagnostic(",
    )

    replace_once(source, "#include <linux/kernel.h>\n",
                 "#include <linux/kernel.h>\n#include <linux/ktime.h>\n")
    replace_once(
        source,
        "static bool mt6797_a72_binder_cpu_online(unsigned int cpu)\n",
        "static u64 mt6797_a72_binder_monotonic_ns(void)\n"
        "{\n\treturn ktime_get_ns();\n}\n\n"
        "static unsigned int mt6797_a72_binder_cpu_online_count(void)\n"
        "{\n\treturn num_online_cpus();\n}\n\n"
        "static bool mt6797_a72_binder_cpu_online(unsigned int cpu)\n",
    )
    replace_once(
        source,
        "\t.membership_finalize_success =\n"
        "\t\tmt6797_a72_membership_finalize_cpu8_success,\n"
        "\t.watchdog_takeover = mtk_wdt_recovery_takeover,\n",
        "\t.membership_finalize_success =\n"
        "\t\tmt6797_a72_membership_finalize_cpu8_success,\n"
        "\t.membership_parent_proof =\n"
        "\t\tmt6797_a72_membership_initial_parent_proof,\n"
        "\t.watchdog_takeover = mtk_wdt_recovery_takeover,\n"
        "\t.watchdog_validate = mtk_wdt_recovery_validate,\n"
        "\t.monotonic_ns = mt6797_a72_binder_monotonic_ns,\n",
    )
    replace_once(
        source,
        "\t.cpu_online = mt6797_a72_binder_cpu_online,\n",
        "\t.cpu_online = mt6797_a72_binder_cpu_online,\n"
        "\t.cpu_online_count = mt6797_a72_binder_cpu_online_count,\n",
    )
    replace_once(
        source,
        "\t    !ops->membership_finalize_success || !ops->watchdog_takeover ||\n",
        "\t    !ops->membership_finalize_success ||\n"
        "\t    !ops->membership_parent_proof || !ops->watchdog_takeover ||\n"
        "\t    !ops->watchdog_validate || !ops->monotonic_ns ||\n",
    )
    replace_once(
        source,
        "\t    !ops->sram_enable || !ops->dcm_update || !ops->cpu_online ||\n"
        "\t    !ops->ipi_call)\n",
        "\t    !ops->sram_enable || !ops->dcm_update || !ops->cpu_online ||\n"
        "\t    !ops->cpu_online_count || !ops->ipi_call)\n",
    )
    replace_once(
        source,
        "\tstruct mtk_wdt_recovery_result result = { };\n\tint ret;\n\n"
        "\tif (!identity || timeout_ms != MTK_WDT_RECOVERY_TIMEOUT_MS)\n"
        "\t\treturn -EINVAL;\n"
        "\tret = binder->backend->watchdog_takeover(binder->watchdog, timeout_ms,\n",
        "\tstruct mtk_wdt_recovery_result result = { };\n"
        "\tu64 takeover_ns;\n\tint ret;\n\n"
        "\tif (!identity || timeout_ms != MTK_WDT_RECOVERY_TIMEOUT_MS)\n"
        "\t\treturn -EINVAL;\n"
        "\ttakeover_ns = binder->backend->monotonic_ns();\n"
        "\tif (!takeover_ns)\n\t\treturn -EPROTO;\n"
        "\tret = binder->backend->watchdog_takeover(binder->watchdog, timeout_ms,\n",
    )
    replace_once(
        source,
        "\tif (!result.identity || result.owned != 1)\n"
        "\t\treturn -EPROTO;\n"
        "\t*identity = result.identity;\n",
        "\tif (!result.identity || result.owned != 1)\n"
        "\t\treturn -EPROTO;\n"
        "\tbinder->watchdog_takeover_ns = takeover_ns;\n"
        "\t*identity = result.identity;\n",
    )
    replace_once(
        source,
        "int\nmt6797_a72_binder_diagnostic_snapshot(",
        BINDER_PROOF + "int\nmt6797_a72_binder_diagnostic_snapshot(",
    )
    replace_once(
        source,
        "void\nmt6797_a72_binder_test_diagnostic(",
        "int mt6797_a72_binder_test_parent_proof(\n"
        "\tconst struct mt6797_a72_binder *binder,\n"
        "\tstruct mt6797_a72_binder_parent_proof *proof)\n"
        "{\n"
        "\tif (!binder || !proof)\n"
        "\t\treturn -EINVAL;\n"
        "\treturn mt6797_a72_binder_parent_proof_locked(binder, proof);\n"
        "}\n\n"
        "void\nmt6797_a72_binder_test_diagnostic(",
    )
    replace_once(
        source,
        "\tstatic_assert(MT6797_A72_TRANSITION_RECOVERY_MS ==\n"
        "\t\t      MTK_WDT_RECOVERY_TIMEOUT_MS);\n",
        "\tstatic_assert(MT6797_A72_TRANSITION_RECOVERY_MS ==\n"
        "\t\t      MTK_WDT_RECOVERY_TIMEOUT_MS);\n"
        "\tstatic_assert(MT6797_A72_BINDER_PARENT_MAX_AGE_MS <\n"
        "\t\t      MTK_WDT_RECOVERY_TIMEOUT_MS);\n",
    )

    replace_once(
        test,
        "#define TEST_PROVIDER_COOKIE 19ULL\n",
        "#define TEST_PROVIDER_COOKIE 19ULL\n"
        "#define TEST_CPU9_GENERATION 23ULL\n"
        "#define TEST_CPU9_COOKIE 29ULL\n"
        "#define TEST_WATCHDOG_IDENTITY 11ULL\n"
        "#define TEST_TAKEOVER_NS 10000000000ULL\n",
    )
    replace_once(
        test,
        "\tunsigned int membership_rejects;\n",
        "\tunsigned int membership_rejects;\n"
        "\tunsigned int watchdog_validations;\n"
        "\tu64 monotonic_ns;\n",
    )
    replace_once(
        test,
        "\tbool terminal_fails;\n\tbool cpu8_online;\n",
        "\tbool terminal_fails;\n"
        "\tbool cpu8_online;\n"
        "\tbool cpu9_online;\n"
        "\tbool parent_available;\n",
    )
    replace_once(
        test,
        "\ttransaction->identity.cpuhp_target = CPUHP_ONLINE;\n",
        "\ttransaction->identity.owner =\n"
        "\t\tARM64_LATE_CPU_STARTUP_OWNER_MEMBERSHIP;\n"
        "\ttransaction->identity.cpuhp_target = CPUHP_ONLINE;\n"
        "\ttransaction->identity.target_mpidr = 0x200;\n",
    )
    replace_once(
        test,
        "static bool mt6797_binder_test_owns_token(",
        BINDER_TEST_SUPPORT + "static bool mt6797_binder_test_owns_token(",
    )
    replace_once(
        test,
        "\tresult->identity = state->malformed == TEST_MALFORMED_WATCHDOG ? 0 : 11;\n",
        "\tresult->identity = state->malformed == TEST_MALFORMED_WATCHDOG ?\n"
        "\t\t0 : TEST_WATCHDOG_IDENTITY;\n",
    )
    replace_once(
        test,
        "static bool mt6797_binder_test_cpu_online(unsigned int cpu)\n"
        "{\n"
        "\treturn cpu == 8 && mt6797_binder_test_active->cpu8_online;\n"
        "}\n",
        "static bool mt6797_binder_test_cpu_online(unsigned int cpu)\n"
        "{\n"
        "\tstruct mt6797_binder_test_state *state =\n"
        "\t\tmt6797_binder_test_active;\n\n"
        "\tif (cpu < 8)\n\t\treturn true;\n"
        "\tif (cpu == 8)\n\t\treturn state->cpu8_online;\n"
        "\treturn cpu == 9 && state->cpu9_online;\n"
        "}\n",
    )
    replace_once(
        test,
        "\t.membership_finalize_success = mt6797_binder_test_finalize_success,\n"
        "\t.watchdog_takeover = mt6797_binder_test_watchdog,\n",
        "\t.membership_finalize_success = mt6797_binder_test_finalize_success,\n"
        "\t.membership_parent_proof = mt6797_binder_test_parent_proof,\n"
        "\t.watchdog_takeover = mt6797_binder_test_watchdog,\n"
        "\t.watchdog_validate = mt6797_binder_test_watchdog_validate,\n"
        "\t.monotonic_ns = mt6797_binder_test_monotonic_ns,\n",
    )
    replace_once(
        test,
        "\t.cpu_online = mt6797_binder_test_cpu_online,\n",
        "\t.cpu_online = mt6797_binder_test_cpu_online,\n"
        "\t.cpu_online_count = mt6797_binder_test_online_count,\n",
    )
    replace_once(
        test,
        "\tmt6797_a72_binder_test_init(&state->binder, &mt6797_binder_test_ops);\n"
        "\ttest->priv = state;\n",
        "\tstate->monotonic_ns = TEST_TAKEOVER_NS;\n"
        "\tmt6797_a72_binder_test_init(&state->binder, &mt6797_binder_test_ops);\n"
        "\ttest->priv = state;\n",
    )
    replace_once(
        test,
        "static void mt6797_binder_one_shot_test(struct kunit *test)\n",
        BINDER_TEST +
        "static void mt6797_binder_one_shot_test(struct kunit *test)\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_binder_one_shot_test),\n",
        "\tKUNIT_CASE(mt6797_binder_parent_proof_test),\n"
        "\tKUNIT_CASE(mt6797_binder_one_shot_test),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("membership", "binder"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.stage == "membership":
        edit_membership(root)
    else:
        edit_binder(root)


if __name__ == "__main__":
    main()
