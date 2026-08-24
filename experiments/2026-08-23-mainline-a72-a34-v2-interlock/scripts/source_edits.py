#!/usr/bin/env python3
"""Apply the frozen A34-v2 and P30-interlock source phases."""

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def edit(path: Path, transform) -> None:
    original = path.read_text()
    updated = transform(original)
    if updated == original:
        raise SystemExit(f"no change produced for {path}")
    path.write_text(updated)


def interlock_header(text: str) -> str:
    text = replace_once(
        text,
        "#include <linux/bits.h>\n#include <linux/types.h>\n",
        "#include <linux/bits.h>\n#include <linux/errno.h>\n#include <linux/types.h>\n",
        "late header errno include",
    )
    text = replace_once(
        text,
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_FAILSTOP\n"
        "int arm64_late_cpu_startup_prepare",
        "#define ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI 1\n\n"
        "struct arm64_late_cpu_bootstrap_claim {\n"
        "\tu32 abi;\n"
        "\tu32 reserved;\n"
        "\tu64 cookie;\n"
        "};\n\n"
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_FAILSTOP\n"
        "int arm64_late_cpu_startup_claim_pristine(\n"
        "\tstruct arm64_late_cpu_bootstrap_claim *claim);\n"
        "int arm64_late_cpu_startup_release_pristine(\n"
        "\tstruct arm64_late_cpu_bootstrap_claim *claim);\n"
        "int arm64_late_cpu_startup_prepare",
        "late header claim declarations",
    )
    text = replace_once(
        text,
        "#else\nstatic inline bool arm64_late_cpu_startup_quarantined(void)\n",
        "#else\nstatic inline int arm64_late_cpu_startup_claim_pristine(\n"
        "\tstruct arm64_late_cpu_bootstrap_claim *claim)\n"
        "{\n"
        "\tif (claim)\n"
        "\t\t*claim = (struct arm64_late_cpu_bootstrap_claim){};\n"
        "\treturn -EOPNOTSUPP;\n"
        "}\n\n"
        "static inline int arm64_late_cpu_startup_release_pristine(\n"
        "\tstruct arm64_late_cpu_bootstrap_claim *claim)\n"
        "{\n"
        "\t(void)claim;\n"
        "\treturn -EOPNOTSUPP;\n"
        "}\n\n"
        "static inline bool arm64_late_cpu_startup_quarantined(void)\n",
        "late header claim stubs",
    )
    return text


def interlock_source(text: str) -> str:
    text = replace_once(
        text,
        "\traw_spinlock_t lock;\n\tatomic_t state;\n",
        "\traw_spinlock_t lock;\n\tatomic_t state;\n"
        "\tu64 bootstrap_claim_cookie;\n\tu64 next_bootstrap_claim_cookie;\n",
        "late control claim fields",
    )
    text = replace_once(
        text,
        "\t.state = ATOMIC_INIT(ARM64_LATE_CPU_STARTUP_FREE),\n"
        "\t.published = COMPLETION_INITIALIZER(late_startup.published),\n",
        "\t.state = ATOMIC_INIT(ARM64_LATE_CPU_STARTUP_FREE),\n"
        "\t.next_bootstrap_claim_cookie = 1,\n"
        "\t.published = COMPLETION_INITIALIZER(late_startup.published),\n",
        "late control claim initializer",
    )
    functions = r'''static bool late_startup_pristine_locked(void)
{
	static const struct arm64_late_cpu_up_token zero_token;
	static const struct arm64_late_cpu_startup_terminal zero_terminal;
	unsigned int i;

	if (atomic_read(&late_startup.state) != ARM64_LATE_CPU_STARTUP_FREE ||
	    late_startup.bootstrap_claim_cookie ||
	    memcmp(&late_startup.token, &zero_token, sizeof(zero_token)) ||
	    memcmp(&late_startup.quarantine_token, &zero_token,
		   sizeof(zero_token)) ||
	    memcmp(&late_startup.terminal, &zero_terminal,
		   sizeof(zero_terminal)) ||
	    late_startup.success_effects ||
	    atomic_read(&late_startup.quarantined) ||
	    late_startup.quarantine_cause || late_startup.retired_mask ||
	    late_startup.completion_consumed || late_startup.online_validated ||
	    late_startup.park_committed || late_startup.stuck_interlock)
		return false;
	for (i = 0; i < ARM64_LATE_CPU_STARTUP_OPERATION_SLOTS; i++)
		if (memcmp(&late_startup.retired_token[i], &zero_token,
			   sizeof(zero_token)))
			return false;
	return true;
}

int arm64_late_cpu_startup_claim_pristine(
	struct arm64_late_cpu_bootstrap_claim *claim)
{
	unsigned long flags;
	u64 cookie;
	int ret = 0;

	if (!claim)
		return -EINVAL;
	*claim = (struct arm64_late_cpu_bootstrap_claim){};
	raw_spin_lock_irqsave(&late_startup.lock, flags);
	if (!late_startup_pristine_locked()) {
		ret = -EBUSY;
		goto out;
	}
	cookie = late_startup.next_bootstrap_claim_cookie++;
	if (!cookie) {
		ret = -EOVERFLOW;
		goto out;
	}
	late_startup.bootstrap_claim_cookie = cookie;
	claim->abi = ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI;
	claim->cookie = cookie;
out:
	raw_spin_unlock_irqrestore(&late_startup.lock, flags);
	return ret;
}

int arm64_late_cpu_startup_release_pristine(
	struct arm64_late_cpu_bootstrap_claim *claim)
{
	unsigned long flags;
	int ret;

	if (!claim || claim->abi != ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI ||
	    claim->reserved || !claim->cookie)
		return -EINVAL;
	raw_spin_lock_irqsave(&late_startup.lock, flags);
	if (claim->cookie != late_startup.bootstrap_claim_cookie) {
		ret = -ESTALE;
	} else {
		late_startup.bootstrap_claim_cookie = 0;
		*claim = (struct arm64_late_cpu_bootstrap_claim){};
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&late_startup.lock, flags);
	return ret;
}

'''
    text = replace_once(
        text,
        "int arm64_late_cpu_startup_prepare(const struct arm64_late_cpu_up_token *token)\n",
        functions
        + "int arm64_late_cpu_startup_prepare(const struct arm64_late_cpu_up_token *token)\n",
        "late claim functions",
    )
    text = replace_once(
        text,
        "\traw_spin_lock_irqsave(&late_startup.lock, flags);\n"
        "\tif (atomic_read(&late_startup.quarantined)) {\n",
        "\traw_spin_lock_irqsave(&late_startup.lock, flags);\n"
        "\tif (late_startup.bootstrap_claim_cookie) {\n"
        "\t\tret = -EBUSY;\n"
        "\t\tgoto out;\n"
        "\t}\n"
        "\tif (atomic_read(&late_startup.quarantined)) {\n",
        "prepare claim exclusion",
    )
    text = replace_once(
        text,
        "\tlate_startup.success_effects = 0;\n"
        "\tlate_startup.quarantine_cause = ARM64_LATE_CPU_QUARANTINE_NONE;\n",
        "\tlate_startup.success_effects = 0;\n"
        "\tlate_startup.bootstrap_claim_cookie = 0;\n"
        "\tlate_startup.next_bootstrap_claim_cookie = 1;\n"
        "\tlate_startup.quarantine_cause = ARM64_LATE_CPU_QUARANTINE_NONE;\n",
        "test reset claim state",
    )
    return text


def interlock_test(text: str) -> str:
    tests = r'''static void late_cpu_startup_bootstrap_claim_excludes_prepare_test(
	struct kunit *test)
{
	struct arm64_late_cpu_startup_snapshot before = {};
	struct arm64_late_cpu_startup_snapshot after = {};
	struct arm64_late_cpu_bootstrap_claim claim;
	struct arm64_late_cpu_bootstrap_claim second;

	arm64_late_cpu_startup_snapshot(&before);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	KUNIT_EXPECT_EQ(test, claim.abi,
			(u32)ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI);
	KUNIT_EXPECT_NE(test, claim.cookie, (u64)0);
	memset(&second, 0xa5, sizeof(second));
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&second), -EBUSY);
	KUNIT_EXPECT_EQ(test, second.abi, (u32)0);
	KUNIT_EXPECT_EQ(test, second.cookie, (u64)0);
	KUNIT_EXPECT_EQ(test, arm64_late_cpu_startup_prepare(&cpu8_token),
			-EBUSY);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);
	arm64_late_cpu_startup_snapshot(&after);
	KUNIT_EXPECT_MEMEQ(test, &before, &after, sizeof(before));
	KUNIT_EXPECT_EQ(test, arm64_late_cpu_startup_prepare(&cpu8_token), 0);
}

static void late_cpu_startup_bootstrap_claim_identity_test(struct kunit *test)
{
	struct arm64_late_cpu_bootstrap_claim claim;
	struct arm64_late_cpu_bootstrap_claim wrong;

	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), 0);
	wrong = claim;
	wrong.cookie++;
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&wrong), -ESTALE);
	KUNIT_EXPECT_EQ(test, arm64_late_cpu_startup_prepare(&cpu8_token),
			-EBUSY);
	KUNIT_ASSERT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), 0);
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_release_pristine(&claim), -EINVAL);
}

static void late_cpu_startup_bootstrap_claim_rejects_nonpristine_test(
	struct kunit *test)
{
	struct arm64_late_cpu_bootstrap_claim claim;

	KUNIT_ASSERT_EQ(test, arm64_late_cpu_startup_prepare(&cpu8_token), 0);
	memset(&claim, 0xa5, sizeof(claim));
	KUNIT_EXPECT_EQ(test,
			arm64_late_cpu_startup_claim_pristine(&claim), -EBUSY);
	KUNIT_EXPECT_EQ(test, claim.abi, (u32)0);
	KUNIT_EXPECT_EQ(test, claim.cookie, (u64)0);
}

'''
    text = replace_once(
        text,
        "static struct kunit_case late_cpu_startup_test_cases[] = {\n",
        tests + "static struct kunit_case late_cpu_startup_test_cases[] = {\n"
        "\tKUNIT_CASE(late_cpu_startup_bootstrap_claim_excludes_prepare_test),\n"
        "\tKUNIT_CASE(late_cpu_startup_bootstrap_claim_identity_test),\n"
        "\tKUNIT_CASE(late_cpu_startup_bootstrap_claim_rejects_nonpristine_test),\n",
        "late claim tests",
    )
    return text


def direct_header(text: str) -> str:
    old = r'''#define MT6797_A72_DIRECT_STATE_ABI 1

struct mt6797_a72_direct_topology {
	u32 cpu8_possible;
	u32 cpu9_possible;
	u32 cpu8_present;
	u32 cpu9_present;
	u32 cpu8_online;
	u32 cpu9_online;
};

struct mt6797_a72_direct_state_snapshot {
	u32 abi;
	u32 valid;
	u32 cpu8_possible;
	u32 cpu9_possible;
	u32 cpu8_present;
	u32 cpu9_present;
	u32 cpu8_online;
	u32 cpu9_online;
	struct mt6797_a72_direct_source_snapshot source;
	struct mt6797_a72_owner_snapshot owner;
};
'''
    new = r'''#define MT6797_A72_DIRECT_STATE_ABI 2

struct mt6797_a72_direct_topology {
	u32 cpu8_possible;
	u32 cpu9_possible;
	u32 cpu8_present;
	u32 cpu9_present;
	u32 cpu8_online;
	u32 cpu9_online;
	u32 cpu8_method_valid;
	u32 cpu9_method_valid;
	u64 cpu8_mpidr;
	u64 cpu9_mpidr;
};

struct mt6797_a72_direct_state_snapshot {
	u32 abi;
	u32 valid;
	u32 cpu8_possible;
	u32 cpu9_possible;
	u32 cpu8_present;
	u32 cpu9_present;
	u32 cpu8_online;
	u32 cpu9_online;
	u32 cpu8_method_valid;
	u32 cpu9_method_valid;
	u64 cpu8_mpidr;
	u64 cpu9_mpidr;
	struct mt6797_a72_direct_source_snapshot source;
	struct mt6797_a72_owner_snapshot owner;
};
'''
    return replace_once(text, old, new, "direct topology ABI")


def direct_source(text: str) -> str:
    text = replace_once(
        text,
        "#include <asm/memory.h>\n#include <asm/mt6797_a72_membership.h>\n",
        "#include <asm/cpu_ops.h>\n#include <asm/memory.h>\n"
        "#include <asm/mt6797_a72_membership.h>\n",
        "direct cpu ops include",
    )
    text = replace_once(
        text,
        "static DEFINE_MUTEX(a72_transition_lock);\n",
        "extern const struct cpu_operations mt6797_psci_ops;\n\n"
        "static DEFINE_MUTEX(a72_transition_lock);\n",
        "direct mt6797 ops declaration",
    )
    text = replace_once(
        text,
        "\t\ttopology->cpu8_present == 1 &&\n"
        "\t\ttopology->cpu9_present == 1 &&\n"
        "\t\t!topology->cpu8_online && !topology->cpu9_online;\n",
        "\t\ttopology->cpu8_present == 1 &&\n"
        "\t\ttopology->cpu9_present == 1 &&\n"
        "\t\t!topology->cpu8_online && !topology->cpu9_online &&\n"
        "\t\ttopology->cpu8_method_valid == 1 &&\n"
        "\t\ttopology->cpu9_method_valid == 1 &&\n"
        "\t\ttopology->cpu8_mpidr == 0x200 &&\n"
        "\t\ttopology->cpu9_mpidr == 0x201;\n",
        "direct target identity validation",
    )
    text = replace_once(
        text,
        "\tobserved->cpu8_online = topology->cpu8_online;\n"
        "\tobserved->cpu9_online = topology->cpu9_online;\n"
        "\t*snapshot = *observed;\n",
        "\tobserved->cpu8_online = topology->cpu8_online;\n"
        "\tobserved->cpu9_online = topology->cpu9_online;\n"
        "\tobserved->cpu8_method_valid = topology->cpu8_method_valid;\n"
        "\tobserved->cpu9_method_valid = topology->cpu9_method_valid;\n"
        "\tobserved->cpu8_mpidr = topology->cpu8_mpidr;\n"
        "\tobserved->cpu9_mpidr = topology->cpu9_mpidr;\n"
        "\t*snapshot = *observed;\n",
        "direct target identity publication",
    )
    text = replace_once(
        text,
        "\ttopology.cpu8_online = cpu_online(8);\n"
        "\ttopology.cpu9_online = cpu_online(9);\n"
        "\tret = mt6797_a72_direct_state_snapshot_locked(&topology, snapshot);\n",
        "\ttopology.cpu8_online = cpu_online(8);\n"
        "\ttopology.cpu9_online = cpu_online(9);\n"
        "\ttopology.cpu8_method_valid =\n"
        "\t\tget_cpu_ops(8) == &mt6797_psci_ops;\n"
        "\ttopology.cpu9_method_valid =\n"
        "\t\tget_cpu_ops(9) == &mt6797_psci_ops;\n"
        "\ttopology.cpu8_mpidr = cpu_logical_map(8);\n"
        "\ttopology.cpu9_mpidr = cpu_logical_map(9);\n"
        "\tret = mt6797_a72_direct_state_snapshot_locked(&topology, snapshot);\n",
        "direct target identity collection",
    )
    return text


def direct_test(text: str) -> str:
    text = replace_once(
        text,
        "\t\t.cpu8_present = 1,\n\t\t.cpu9_present = 1,\n\t};\n",
        "\t\t.cpu8_present = 1,\n\t\t.cpu9_present = 1,\n"
        "\t\t.cpu8_method_valid = 1,\n"
        "\t\t.cpu9_method_valid = 1,\n"
        "\t\t.cpu8_mpidr = 0x200,\n"
        "\t\t.cpu9_mpidr = 0x201,\n\t};\n",
        "direct test topology fixture",
    )
    text = replace_once(
        text,
        "\tKUNIT_EXPECT_EQ(test, observed.cpu8_online, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, observed.cpu9_online, 0U);\n",
        "\tKUNIT_EXPECT_EQ(test, observed.cpu8_online, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, observed.cpu9_online, 0U);\n"
        "\tKUNIT_EXPECT_EQ(test, observed.cpu8_method_valid, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, observed.cpu9_method_valid, 1U);\n"
        "\tKUNIT_EXPECT_EQ(test, observed.cpu8_mpidr, (u64)0x200);\n"
        "\tKUNIT_EXPECT_EQ(test, observed.cpu9_mpidr, (u64)0x201);\n",
        "direct success target identity",
    )
    text = replace_once(
        text,
        "\tfor (index = 0; index < 6; index++) {\n",
        "\tfor (index = 0; index < 10; index++) {\n",
        "direct topology mutation count",
    )
    text = replace_once(
        text,
        "\t\tcase 4:\n"
        "\t\t\ttopology.cpu8_online ^= 1;\n"
        "\t\t\tbreak;\n"
        "\t\tdefault:\n"
        "\t\t\ttopology.cpu9_online ^= 1;\n"
        "\t\t\tbreak;\n",
        "\t\tcase 4:\n"
        "\t\t\ttopology.cpu8_online ^= 1;\n"
        "\t\t\tbreak;\n"
        "\t\tcase 5:\n"
        "\t\t\ttopology.cpu9_online ^= 1;\n"
        "\t\t\tbreak;\n"
        "\t\tcase 6:\n"
        "\t\t\ttopology.cpu8_method_valid ^= 1;\n"
        "\t\t\tbreak;\n"
        "\t\tcase 7:\n"
        "\t\t\ttopology.cpu9_method_valid ^= 1;\n"
        "\t\t\tbreak;\n"
        "\t\tcase 8:\n"
        "\t\t\ttopology.cpu8_mpidr ^= 1;\n"
        "\t\t\tbreak;\n"
        "\t\tdefault:\n"
        "\t\t\ttopology.cpu9_mpidr ^= 1;\n"
        "\t\t\tbreak;\n",
        "direct topology mutation switch",
    )
    return text


def a34_header(text: str) -> str:
    text = replace_once(
        text,
        "#define MT6797_A72_A34_ELIGIBILITY_ABI 1\n"
        "#define MT6797_A72_A34_FIRST_GENERATION 1ULL\n"
        "#define MT6797_A72_A34_FIRST_COOKIE 0xa7200001ULL\n",
        "#define MT6797_A72_A34_ELIGIBILITY_ABI 2\n",
        "A34 ABI and obsolete identity constants",
    )
    start = text.index("enum mt6797_a72_a34_reset_provenance {")
    end = text.index("\n#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR", start)
    replacement = r'''#define MT6797_A72_A34_REPLAY_ABI 1

enum mt6797_a72_a34_replay_proof {
	MT6797_A72_A34_REPLAY_UNKNOWN,
	MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR,
};

struct mt6797_a72_a34_replay {
	u32 abi;
	u32 valid;
	u32 proof;
	u32 private_replay_value;
	u32 reserved[4];
};

struct mt6797_a72_a34_observation {
	u32 abi;
	u32 reserved[3];
	struct mt6797_a72_direct_state_snapshot direct;
	struct mt6797_a72_a34_replay replay;
};
'''
    return text[:start] + replacement + text[end:]


def a34_source(text: str) -> str:
    start = text.index("#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n")
    end_marker = "#endif\n\nstatic bool\nmt6797_a72_p32_target_locked"
    end = text.index(end_marker, start)
    replacement = r'''#ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
static const struct mt6797_a72_a34_observation a34_expected = {
	.abi = MT6797_A72_A34_ELIGIBILITY_ABI,
	.direct = {
		.abi = MT6797_A72_DIRECT_STATE_ABI,
		.valid = 1,
		.cpu8_possible = 1,
		.cpu9_possible = 1,
		.cpu8_present = 1,
		.cpu9_present = 1,
		.cpu8_method_valid = 1,
		.cpu9_method_valid = 1,
		.cpu8_mpidr = 0x200,
		.cpu9_mpidr = 0x201,
		.source = {
			.abi = MT6797_A72_DIRECT_SOURCE_ABI,
			.valid = 1,
			.provider = {
				.abi = MT6797_A72_PROVIDER_STATE_ABI,
				.valid = 1,
				.control_a = 0x7b,
				.status_b = 0xc1,
				.vbuckb_a = 0x46,
				.vbuckb_b = 0x46,
			},
			.platform = {
				.spm_pwr_status = 0x2a00005c,
				.spm_pwr_status_2nd = 0x2a00004c,
				.spm_cpu_pwr_status = 0x00350c08,
				.spm_cpu_pwr_status_2nd = 0x00350cff,
				.spm_mp2_cpusys_pwr_con = 0x00010132,
				.spm_cpu_ext_buck_iso = 0x00000002,
				.valid = true,
			},
			.clock = {
				.abi = MT6797_DVFSP_CLOCK_BACKEND_ABI,
				.sample_generation = 1,
			},
			.bigidvfs = {
				.abi = MT6797_BIGIDVFS_BACKEND_ABI,
				.sample_generation = 1,
			},
		},
		.owner = {
			.diagnostic_blockers = MT6797_A72_BLOCK_MASK,
			.abi = MT6797_A72_TRANSACTION_ABI,
			.health = MT6797_A72_OWNER_CLOSED,
			.phase = MT6797_A72_PHASE_UNINITIALIZED,
			.provider_state = MT6797_A72_PROVIDER_NONE,
		},
	},
	.replay = {
		.abi = MT6797_A72_A34_REPLAY_ABI,
		.valid = 1,
		.proof =
			MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR,
	},
};

int
mt6797_a72_a34_evaluate(const struct mt6797_a72_a34_observation *observation)
{
	if (!observation)
		return -EINVAL;
	if (memcmp(observation, &a34_expected, sizeof(*observation)))
		return -EPERM;
	return 0;
}
'''
    return text[:start] + replacement + "#endif\n\nstatic bool\nmt6797_a72_p32_target_locked" + text[end + len(end_marker):]


def a34_kconfig(text: str) -> str:
    old = r'''	  Exercise both accepted reset-provenance values, null input, every
	  byte mutation, explicit missing provenance, and unchanged CLOSED
	  admission without hardware or CPU operations. The suite has no
	  production hook.
'''
    new = r'''	  Exercise the exact direct-state-v2 and typed primary-BL31 replay
	  fixture, null input, every-byte mutation, missing replay authority,
	  and unchanged CLOSED admission without hardware or CPU operations.
	  The over-strict fixture is not physical evidence and the suite has no
	  production hook.
'''
    return replace_once(text, old, new, "A34 Kconfig help")


def a34_platforms(text: str) -> str:
    old = r'''config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
	bool "Evaluate the exact MT6797 A72 A34 zero-state tuple"
	depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
	help
	  Add a pure, default-off evaluator for the frozen A34 tuple. Its
	  immutable input must carry explicit platform/external-reset
	  provenance and owner-safe private replay-zero proof.

	  This option has no production caller and cannot open the owner,
	  initialize an attempt, call a provider, perform a hardware effect,
	  arm P30, or issue CPU_ON or CPU_OFF.
'''
    new = r'''config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
	bool "Evaluate exact MT6797 A72 direct and replay state"
	depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
	help
	  Add a pure, default-off evaluator for one exact direct-state-v2
	  record and one typed applicable primary-BL31 replay-clear record.
	  The evaluator has no production caller or physical source binding.

	  This option cannot open the owner, initialize an attempt, call a
	  provider, perform a hardware effect, arm P30, or issue CPU_ON or
	  CPU_OFF.
'''
    return replace_once(text, old, new, "A34 platform Kconfig help")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("interlock", "direct", "a34"), required=True)
    args = parser.parse_args()
    root = args.source_root

    if args.phase == "interlock":
        edit(root / "arch/arm64/include/asm/late_cpu_startup.h", interlock_header)
        edit(root / "arch/arm64/kernel/late_cpu_startup.c", interlock_source)
        edit(root / "arch/arm64/kernel/late_cpu_startup_test.c", interlock_test)
    elif args.phase == "direct":
        edit(root / "arch/arm64/include/asm/mt6797_a72_membership.h", direct_header)
        edit(root / "arch/arm64/kernel/mt6797_a72_membership.c", direct_source)
        edit(root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c", direct_test)
    else:
        edit(root / "arch/arm64/include/asm/mt6797_a72_membership.h", a34_header)
        edit(root / "arch/arm64/kernel/mt6797_a72_membership.c", a34_source)
        template = Path(__file__).resolve().parents[1] / "source/mt6797_a72_a34_evaluator_test.c"
        target = root / "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c"
        target.write_text(template.read_text())
        edit(root / "arch/arm64/Kconfig", a34_kconfig)
        edit(root / "arch/arm64/Kconfig.platforms", a34_platforms)


if __name__ == "__main__":
    main()
