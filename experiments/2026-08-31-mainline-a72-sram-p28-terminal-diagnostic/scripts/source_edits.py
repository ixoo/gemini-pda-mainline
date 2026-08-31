#!/usr/bin/env python3
"""Apply the exact read-only CPU8 SRAM/P28 terminal diagnostic."""

from __future__ import annotations

import hashlib
from pathlib import Path


ADMISSION = Path("drivers/soc/mediatek/mt6797-a72-admission-controller.c")
INTERNAL = Path("drivers/soc/mediatek/mt6797-a72-binder-internal.h")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
PUBLIC = Path("include/linux/soc/mediatek/mt6797-a72-binder.h")
SOURCE_FILES = (ADMISSION, INTERNAL, BINDER_TEST, BINDER, PUBLIC)
PARENT_SHA256 = {
    ADMISSION: "38f985000151499470913257477231c083a2fbbfd54c548490f1a3d79c169ff1",
    INTERNAL: "983027a19c26b8003edda69062200478bce11f16092e06a19d07d79d6fa1d138",
    BINDER_TEST: "8e81bb54711f697e03030ae31d7e7f43dec9c2d16704e3f93ad88823076e8f48",
    BINDER: "467d46d5b8f029c46b2728041ae530ebef5c67fe8d9936657f0aa282a66a1e7a",
    PUBLIC: "85d9231c89aefa9537e43eb76cd1d7af50125d16d0537c2a448157a7157c8322",
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
    admission_path = root / ADMISSION
    internal_path = root / INTERNAL
    test_path = root / BINDER_TEST
    binder_path = root / BINDER
    public_path = root / PUBLIC
    admission = admission_path.read_text(encoding="utf-8")
    internal = internal_path.read_text(encoding="utf-8")
    test = test_path.read_text(encoding="utf-8")
    binder = binder_path.read_text(encoding="utf-8")
    public = public_path.read_text(encoding="utf-8")

    public = replace_once(
        public,
        "#include <linux/cpuhotplug.h>\n",
        "#include <linux/bits.h>\n#include <linux/cpuhotplug.h>\n",
        "public bits include",
    )
    public = replace_once(
        public,
        "#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 1U\n",
        """#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 2U

#define MT6797_A72_BINDER_SRAM_MATCH_ABI\t\tBIT(0)
#define MT6797_A72_BINDER_SRAM_MATCH_ATTEMPTED\tBIT(1)
#define MT6797_A72_BINDER_SRAM_MATCH_COMPLETED\tBIT(2)
#define MT6797_A72_BINDER_SRAM_MATCH_VOLTAGE\tBIT(3)
#define MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_FIRST\tBIT(4)
#define MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_SECOND\tBIT(5)
#define MT6797_A72_BINDER_SRAM_MATCH_ATTEMPT_ID\tBIT(6)
#define MT6797_A72_BINDER_SRAM_MATCH_COOKIE\tBIT(7)
#define MT6797_A72_BINDER_SRAM_MATCH_ERROR\t\tBIT(8)
#define MT6797_A72_BINDER_SRAM_MATCH_EFFECT\t\tBIT(9)
#define MT6797_A72_BINDER_SRAM_MATCH_VERIFIED\tBIT(10)
#define MT6797_A72_BINDER_SRAM_MATCH_SEALED\t\tBIT(11)
#define MT6797_A72_BINDER_SRAM_REQUIRED_MASK\t\tGENMASK(11, 0)
""",
        "diagnostic ABI and SRAM mask",
    )
    public = replace_once(
        public,
        """\tu32 p27_release_bpll;
\tu32 p27_release_owned;
\tu32 p27_release_sealed;
};""",
        """\tu32 p27_release_bpll;
\tu32 p27_release_owned;
\tu32 p27_release_sealed;
\tu32 p28_begin_attempted;
\ts32 p28_begin_ret;
\tu32 p28_begun;
\tu32 sram_returned;
\ts32 sram_ret;
\tu32 sram_match_mask;
\tu32 sram_required_mask;
\tu32 p28_complete_attempted;
\ts32 p28_complete_ret;
\tu32 sram_abi;
\tu32 sram_attempted;
\tu32 sram_completed;
\tu32 sram_requested_mv_x100;
\tu32 sram_selector_first;
\tu32 sram_calibration_first;
\tu32 sram_selector_second;
\tu32 sram_calibration_second;
\tu64 sram_attempt_id;
\tu64 sram_cookie;
\ts32 sram_error;
\tu32 sram_effect_attempted;
\tu32 sram_verified;
\tu32 sram_sealed;
};""",
        "public diagnostic fields",
    )

    internal = replace_once(
        internal,
        """\tmt6797_a72_cpu_boot_fn cpu_boot;
\tatomic_t boot_claimed;
\tbool ledger_begun;
\tbool p28_begun;
};""",
        """\tmt6797_a72_cpu_boot_fn cpu_boot;
\tatomic_t boot_claimed;
\ts32 p28_begin_ret;
\ts32 sram_ret;
\ts32 p28_complete_ret;
\tbool ledger_begun;
\tbool p28_begin_attempted;
\tbool p28_begun;
\tbool sram_returned;
\tbool p28_complete_attempted;
};""",
        "binder diagnostic state",
    )

    binder = replace_once(
        binder,
        """#define MT6797_A72_BINDER_DCM_COMPLETE \\
\t(MT6797_A72_BINDER_ISOLATION_COMPLETE | \\
\t MT6797_A72_EFFECT_DCM_TOGGLE | MT6797_A72_EFFECT_DCM_FINAL)

static DEFINE_MUTEX(mt6797_a72_binder_publish_lock);""",
        """#define MT6797_A72_BINDER_DCM_COMPLETE \\
\t(MT6797_A72_BINDER_ISOLATION_COMPLETE | \\
\t MT6797_A72_EFFECT_DCM_TOGGLE | MT6797_A72_EFFECT_DCM_FINAL)
#define MT6797_A72_BINDER_SRAM_COMPLETE \\
\t(MT6797_BIGIDVFS_SRAM_SERVICE | MT6797_BIGIDVFS_SRAM_SETTLE | \\
\t MT6797_BIGIDVFS_SRAM_SELECTOR_FIRST | \\
\t MT6797_BIGIDVFS_SRAM_CALIBRATION_FIRST | \\
\t MT6797_BIGIDVFS_SRAM_SELECTOR_SECOND | \\
\t MT6797_BIGIDVFS_SRAM_CALIBRATION_SECOND | \\
\t MT6797_BIGIDVFS_SRAM_SELECTOR_VALID | \\
\t MT6797_BIGIDVFS_SRAM_CALIBRATION_VALID)

static DEFINE_MUTEX(mt6797_a72_binder_publish_lock);""",
        "SRAM complete mask",
    )
    binder = replace_once(
        binder,
        """bool mt6797_a72_binder_available(void)
{
\tbool available;

\tmutex_lock(&mt6797_a72_binder_publish_lock);
\tavailable = !!mt6797_a72_binder_ready();
\tmutex_unlock(&mt6797_a72_binder_publish_lock);
\treturn available;
}

static void
mt6797_a72_binder_fill_diagnostic""",
        """bool mt6797_a72_binder_available(void)
{
\tbool available;

\tmutex_lock(&mt6797_a72_binder_publish_lock);
\tavailable = !!mt6797_a72_binder_ready();
\tmutex_unlock(&mt6797_a72_binder_publish_lock);
\treturn available;
}

static u32
mt6797_a72_binder_sram_match_mask(const struct mt6797_a72_binder *binder)
{
\tconst struct mt6797_bigidvfs_sram_result *sram = &binder->sram;
\tu32 mask = 0;

\tif (sram->abi == MT6797_BIGIDVFS_SRAM_OWNER_ABI)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_ABI;
\tif (sram->attempted_steps == MT6797_A72_BINDER_SRAM_COMPLETE)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_ATTEMPTED;
\tif (sram->completed_steps == MT6797_A72_BINDER_SRAM_COMPLETE)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_COMPLETED;
\tif (sram->requested_mv_x100 == MT6797_BIGIDVFS_SRAM_TARGET_MV_X100)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_VOLTAGE;
\tif (sram->selector_first == MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_FIRST;
\tif (sram->selector_second == MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_SECOND;
\tif (sram->attempt_id == binder->transaction.identity.generation)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_ATTEMPT_ID;
\tif (sram->cookie == binder->transaction.identity.cookie)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_COOKIE;
\tif (!sram->error)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_ERROR;
\tif (sram->effect_attempted)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_EFFECT;
\tif (sram->verified)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_VERIFIED;
\tif (sram->sealed)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SEALED;
\treturn mask;
}

static void
mt6797_a72_binder_fill_diagnostic""",
        "SRAM match helper",
    )
    binder = replace_once(
        binder,
        """\tsnapshot->p27_release_bpll = release->bpll_ordering_value;
\tsnapshot->p27_release_owned = release->p27_owned;
\tsnapshot->p27_release_sealed = release->sealed;
}""",
        """\tsnapshot->p27_release_bpll = release->bpll_ordering_value;
\tsnapshot->p27_release_owned = release->p27_owned;
\tsnapshot->p27_release_sealed = release->sealed;
\tsnapshot->p28_begin_attempted = binder->p28_begin_attempted;
\tsnapshot->p28_begin_ret = binder->p28_begin_ret;
\tsnapshot->p28_begun = binder->p28_begun;
\tsnapshot->sram_returned = binder->sram_returned;
\tsnapshot->sram_ret = binder->sram_ret;
\tsnapshot->sram_match_mask = mt6797_a72_binder_sram_match_mask(binder);
\tsnapshot->sram_required_mask = MT6797_A72_BINDER_SRAM_REQUIRED_MASK;
\tsnapshot->p28_complete_attempted = binder->p28_complete_attempted;
\tsnapshot->p28_complete_ret = binder->p28_complete_ret;
\tsnapshot->sram_abi = binder->sram.abi;
\tsnapshot->sram_attempted = binder->sram.attempted_steps;
\tsnapshot->sram_completed = binder->sram.completed_steps;
\tsnapshot->sram_requested_mv_x100 = binder->sram.requested_mv_x100;
\tsnapshot->sram_selector_first = binder->sram.selector_first;
\tsnapshot->sram_calibration_first = binder->sram.calibration_first;
\tsnapshot->sram_selector_second = binder->sram.selector_second;
\tsnapshot->sram_calibration_second = binder->sram.calibration_second;
\tsnapshot->sram_attempt_id = binder->sram.attempt_id;
\tsnapshot->sram_cookie = binder->sram.cookie;
\tsnapshot->sram_error = binder->sram.error;
\tsnapshot->sram_effect_attempted = binder->sram.effect_attempted;
\tsnapshot->sram_verified = binder->sram.verified;
\tsnapshot->sram_sealed = binder->sram.sealed;
}""",
        "diagnostic snapshot fill",
    )
    binder = replace_once(
        binder,
        """\tret = binder->backend->membership_begin_p28(&binder->transaction);
\tif (ret)
\t\treturn ret;
\tbinder->p28_begun = true;""",
        """\tbinder->p28_begin_attempted = true;
\tret = binder->backend->membership_begin_p28(&binder->transaction);
\tbinder->p28_begin_ret = ret;
\tif (ret)
\t\treturn ret;
\tbinder->p28_begun = true;""",
        "P28 begin diagnostic",
    )
    binder = replace_once(
        binder,
        """static int mt6797_a72_binder_sram(void *context)
{
\tstruct mt6797_a72_binder *binder = context;
\tstruct mt6797_a72_p28_preparation preparation = { };
\tstruct mt6797_bigidvfs_sram_request request = { };
\tu32 all_steps = MT6797_BIGIDVFS_SRAM_SERVICE |
\t\tMT6797_BIGIDVFS_SRAM_SETTLE |
\t\tMT6797_BIGIDVFS_SRAM_SELECTOR_FIRST |
\t\tMT6797_BIGIDVFS_SRAM_CALIBRATION_FIRST |
\t\tMT6797_BIGIDVFS_SRAM_SELECTOR_SECOND |
\t\tMT6797_BIGIDVFS_SRAM_CALIBRATION_SECOND |
\t\tMT6797_BIGIDVFS_SRAM_SELECTOR_VALID |
\t\tMT6797_BIGIDVFS_SRAM_CALIBRATION_VALID;
\tint ret;

\tif (!binder->p28_begun)
\t\treturn -EPROTO;
\trequest.abi = MT6797_BIGIDVFS_SRAM_OWNER_ABI;
\trequest.cpu = MT6797_A72_TRANSITION_CPU8;
\trequest.attempt_id = binder->transaction.identity.generation;
\trequest.cookie = binder->transaction.identity.cookie;
\trequest.provider_held = true;
\trequest.isolation_crossed = true;
\tret = binder->backend->sram_enable(binder->bigidvfs, &request,
\t\t\t\t\t   &binder->sram);
\tif (ret)
\t\treturn ret;
\tif (binder->sram.abi != MT6797_BIGIDVFS_SRAM_OWNER_ABI ||
\t    binder->sram.attempted_steps != all_steps ||
\t    binder->sram.completed_steps != all_steps ||
\t    binder->sram.requested_mv_x100 !=
\t\t    MT6797_BIGIDVFS_SRAM_TARGET_MV_X100 ||
\t    binder->sram.selector_first != MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED ||
\t    binder->sram.selector_second != MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED ||
\t    binder->sram.attempt_id != binder->transaction.identity.generation ||
\t    binder->sram.cookie != binder->transaction.identity.cookie ||
\t    binder->sram.error || !binder->sram.effect_attempted ||
\t    !binder->sram.verified || !binder->sram.sealed)
\t\treturn -EPROTO;

\tpreparation.abi = MT6797_A72_P28_PREPARATION_ABI;
\tpreparation.operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP;
\tpreparation.stage = MT6797_A72_P28_STAGE_COMPLETE;
\tpreparation.effect_mask = MT6797_A72_P28_EFFECT_MASK;
\tpreparation.isolation_from = MT6797_A72_P28_ISOLATION_FROM;
\tpreparation.isolation_to = MT6797_A72_P28_ISOLATION_TO;
\tpreparation.pwrap_deasserted = 1;
\tpreparation.software_guard_released = 1;
\tpreparation.wait_before_sram_us = MT6797_A72_P28_WAIT_US;
\tpreparation.sram_ldo_mv = MT6797_A72_P28_SRAM_LDO_MV;
\tpreparation.wait_after_sram_us = MT6797_A72_P28_WAIT_US;
\tpreparation.selector = MT6797_A72_P28_SELECTOR;
\tpreparation.calibration_stable = 1;
\tpreparation.calibration_valid = 1;
\tpreparation.provider_identity = binder->transaction.provider_identity;
\tpreparation.transaction_generation =
\t\tbinder->transaction.identity.generation;
\tpreparation.transaction_cookie = binder->transaction.identity.cookie;
\treturn binder->backend->membership_complete_p28(&binder->transaction,
\t\t\t\t\t\t\t&preparation);
}""",
        """static int mt6797_a72_binder_sram(void *context)
{
\tstruct mt6797_a72_binder *binder = context;
\tstruct mt6797_a72_p28_preparation preparation = { };
\tstruct mt6797_bigidvfs_sram_request request = { };
\tint ret;

\tif (!binder->p28_begun)
\t\treturn -EPROTO;
\trequest.abi = MT6797_BIGIDVFS_SRAM_OWNER_ABI;
\trequest.cpu = MT6797_A72_TRANSITION_CPU8;
\trequest.attempt_id = binder->transaction.identity.generation;
\trequest.cookie = binder->transaction.identity.cookie;
\trequest.provider_held = true;
\trequest.isolation_crossed = true;
\tmemset(&binder->sram, 0, sizeof(binder->sram));
\tbinder->sram_returned = false;
\tbinder->sram_ret = 0;
\tbinder->p28_complete_attempted = false;
\tbinder->p28_complete_ret = 0;
\tret = binder->backend->sram_enable(binder->bigidvfs, &request,
\t\t\t\t\t   &binder->sram);
\tbinder->sram_ret = ret;
\tbinder->sram_returned = true;
\tif (ret)
\t\treturn ret;
\tif (mt6797_a72_binder_sram_match_mask(binder) !=
\t    MT6797_A72_BINDER_SRAM_REQUIRED_MASK)
\t\treturn -EPROTO;

\tpreparation.abi = MT6797_A72_P28_PREPARATION_ABI;
\tpreparation.operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP;
\tpreparation.stage = MT6797_A72_P28_STAGE_COMPLETE;
\tpreparation.effect_mask = MT6797_A72_P28_EFFECT_MASK;
\tpreparation.isolation_from = MT6797_A72_P28_ISOLATION_FROM;
\tpreparation.isolation_to = MT6797_A72_P28_ISOLATION_TO;
\tpreparation.pwrap_deasserted = 1;
\tpreparation.software_guard_released = 1;
\tpreparation.wait_before_sram_us = MT6797_A72_P28_WAIT_US;
\tpreparation.sram_ldo_mv = MT6797_A72_P28_SRAM_LDO_MV;
\tpreparation.wait_after_sram_us = MT6797_A72_P28_WAIT_US;
\tpreparation.selector = MT6797_A72_P28_SELECTOR;
\tpreparation.calibration_stable = 1;
\tpreparation.calibration_valid = 1;
\tpreparation.provider_identity = binder->transaction.provider_identity;
\tpreparation.transaction_generation =
\t\tbinder->transaction.identity.generation;
\tpreparation.transaction_cookie = binder->transaction.identity.cookie;
\tbinder->p28_complete_attempted = true;
\tret = binder->backend->membership_complete_p28(&binder->transaction,
\t\t\t\t\t\t       &preparation);
\tbinder->p28_complete_ret = ret;
\treturn ret;
}""",
        "SRAM diagnostic boundary",
    )

    admission = replace_once(
        admission,
        """\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "p27r_bpll=0x%x p27r_owned=%u p27r_sealed=%u\\n",
\t\t\t\t   diagnostic.p27_release_bpll,
\t\t\t\t   diagnostic.p27_release_owned,
\t\t\t\t   diagnostic.p27_release_sealed);""",
        """\tlen += sysfs_emit_at(buf, len,
\t\t\t     "p27r_bpll=0x%x p27r_owned=%u p27r_sealed=%u ",
\t\t\t     diagnostic.p27_release_bpll,
\t\t\t     diagnostic.p27_release_owned,
\t\t\t     diagnostic.p27_release_sealed);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "p28_begin_attempted=%u p28_begin_ret=%d p28_begun=%u ",
\t\t\t     diagnostic.p28_begin_attempted,
\t\t\t     diagnostic.p28_begin_ret, diagnostic.p28_begun);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "sram_returned=%u sram_ret=%d sram_match=0x%x ",
\t\t\t     diagnostic.sram_returned, diagnostic.sram_ret,
\t\t\t     diagnostic.sram_match_mask);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "sram_required=0x%x p28_complete_attempted=%u ",
\t\t\t     diagnostic.sram_required_mask,
\t\t\t     diagnostic.p28_complete_attempted);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "p28_complete_ret=%d sram_abi=%u ",
\t\t\t     diagnostic.p28_complete_ret, diagnostic.sram_abi);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "sram_attempted=0x%x sram_completed=0x%x sram_mv=%u ",
\t\t\t     diagnostic.sram_attempted, diagnostic.sram_completed,
\t\t\t     diagnostic.sram_requested_mv_x100);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "sram_selector_first=0x%x sram_calibration_first=0x%x ",
\t\t\t     diagnostic.sram_selector_first,
\t\t\t     diagnostic.sram_calibration_first);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "sram_selector_second=0x%x sram_calibration_second=0x%x ",
\t\t\t     diagnostic.sram_selector_second,
\t\t\t     diagnostic.sram_calibration_second);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "sram_attempt_id=%llu sram_cookie=%llu sram_error=%d ",
\t\t\t     (unsigned long long)diagnostic.sram_attempt_id,
\t\t\t     (unsigned long long)diagnostic.sram_cookie,
\t\t\t     diagnostic.sram_error);
\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "sram_effect_attempted=%u sram_verified=%u sram_sealed=%u\\n",
\t\t\t\t   diagnostic.sram_effect_attempted,
\t\t\t\t   diagnostic.sram_verified,
\t\t\t\t   diagnostic.sram_sealed);""",
        "admission status SRAM fields",
    )

    test = replace_once(
        test,
        """static void mt6797_binder_one_shot_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;
\tint ret;

\tKUNIT_ASSERT_EQ(test, mt6797_binder_test_run_to_completion(state), 0);
\tret = mt6797_a72_binder_test_boot(&state->binder, 8,
\t\t\t\t\t  mt6797_binder_test_cpu_boot);
\tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
\tKUNIT_EXPECT_EQ(test, state->cpu_boots, 1U);
}""",
        """static void mt6797_binder_sram_diagnostic_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;
\tstruct mt6797_a72_binder_diagnostic diagnostic;
\tu32 expected = MT6797_A72_BINDER_SRAM_REQUIRED_MASK &
\t\t~MT6797_A72_BINDER_SRAM_MATCH_SEALED;
\tint ret;

\tstate->malformed = TEST_MALFORMED_SRAM;
\tret = mt6797_a72_binder_test_boot(&state->binder, 8,
\t\t\t\t\t  mt6797_binder_test_cpu_boot);
\tKUNIT_ASSERT_EQ(test, ret, -EPROTO);
\tmt6797_a72_binder_test_diagnostic(&state->binder, &diagnostic);
\tKUNIT_EXPECT_EQ(test, diagnostic.abi,
\t\t\tMT6797_A72_BINDER_DIAGNOSTIC_ABI);
\tKUNIT_EXPECT_EQ(test, diagnostic.terminal,
\t\t\t(u32)MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO);
\tKUNIT_EXPECT_EQ(test, diagnostic.last_stage,
\t\t\t(u32)MT6797_A72_TRANSITION_STAGE_SRAM);
\tKUNIT_EXPECT_EQ(test, diagnostic.stage_errno, -EPROTO);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_begin_attempted, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_begin_ret, 0);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_begun, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_returned, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_ret, 0);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_match_mask, expected);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_required_mask,
\t\t\tMT6797_A72_BINDER_SRAM_REQUIRED_MASK);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_complete_attempted, 0U);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_complete_ret, 0);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_attempt_id, TEST_GENERATION);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_cookie, TEST_COOKIE);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_error, 0);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_effect_attempted, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_verified, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_sealed, 0U);
}

static void mt6797_binder_one_shot_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;
\tstruct mt6797_a72_binder_diagnostic diagnostic;
\tint ret;

\tKUNIT_ASSERT_EQ(test, mt6797_binder_test_run_to_completion(state), 0);
\tmt6797_a72_binder_test_diagnostic(&state->binder, &diagnostic);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_begin_attempted, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_begin_ret, 0);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_begun, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_returned, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_ret, 0);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_match_mask,
\t\t\tMT6797_A72_BINDER_SRAM_REQUIRED_MASK);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_complete_attempted, 1U);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_complete_ret, 0);
\tret = mt6797_a72_binder_test_boot(&state->binder, 8,
\t\t\t\t\t  mt6797_binder_test_cpu_boot);
\tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
\tKUNIT_EXPECT_EQ(test, state->cpu_boots, 1U);
}""",
        "SRAM diagnostic KUnit",
    )
    test = replace_once(
        test,
        """\tKUNIT_CASE(mt6797_binder_malformed_owners_test),
\tKUNIT_CASE(mt6797_binder_p27_diagnostic_test),
\tKUNIT_CASE(mt6797_binder_one_shot_test),""",
        """\tKUNIT_CASE(mt6797_binder_malformed_owners_test),
\tKUNIT_CASE(mt6797_binder_p27_diagnostic_test),
\tKUNIT_CASE(mt6797_binder_sram_diagnostic_test),
\tKUNIT_CASE(mt6797_binder_one_shot_test),""",
        "SRAM diagnostic KUnit case",
    )

    admission_path.write_text(admission, encoding="utf-8")
    internal_path.write_text(internal, encoding="utf-8")
    test_path.write_text(test, encoding="utf-8")
    binder_path.write_text(binder, encoding="utf-8")
    public_path.write_text(public, encoding="utf-8")
