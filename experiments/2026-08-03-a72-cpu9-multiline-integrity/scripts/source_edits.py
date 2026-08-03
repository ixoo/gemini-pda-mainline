#!/usr/bin/env python3
"""Apply deterministic multiline-integrity edits to the exact pair-v4 parent."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise EditError(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def edit_psci(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    anchor = """static void mt6797_a72_coh_workfn(struct work_struct *work)
"""
    replacement = """#define MT6797_A72_ML_ROUNDS 64
#define MT6797_A72_ML_LINES 256
#define MT6797_A72_ML_WORDS 8
#define MT6797_A72_ML_SPIN_BUDGET (1U << 24)
#define MT6797_A72_ML_HASH_INIT 1469598103934665603ULL
#define MT6797_A72_ML_HASH_PRIME 1099511628211ULL

struct mt6797_a72_ml_line {
	u64 words[MT6797_A72_ML_WORDS];
} __aligned(64);

struct mt6797_a72_ml_result {
	int cpu;
	int error;
	int done;
	u64 write_hash;
	u64 read_hash;
	int bad_round;
	int bad_line;
	int bad_word;
	u64 expected;
	u64 actual;
};

static struct mt6797_a72_ml_line
	mt6797_a72_ml_data[MT6797_A72_ML_LINES] __aligned(64);
static struct mt6797_a72_ml_result mt6797_a72_ml_result8;
static struct mt6797_a72_ml_result mt6797_a72_ml_result9;
static atomic_t mt6797_a72_ml_reported = ATOMIC_INIT(0);
static int mt6797_a72_ml_turn;

static u64 mt6797_a72_ml_pattern(int writer, int round, int line, int word)
{
	u64 value = 0x9e3779b97f4a7c15ULL;

	value ^= (u64)writer << 60;
	value ^= (u64)round << 32;
	value ^= (u64)line << 8;
	value ^= (u64)word;
	value ^= value << 13;
	value ^= value >> 7;
	value ^= value << 17;
	return value;
}

static u64 mt6797_a72_ml_hash(u64 hash, u64 value)
{
	return (hash ^ value) * MT6797_A72_ML_HASH_PRIME;
}

static int mt6797_a72_ml_wait_turn(int expected, unsigned int *budget)
{
	while (READ_ONCE(mt6797_a72_ml_turn) != expected) {
		if (!(*budget)--)
			return -ETIMEDOUT;
		cpu_relax();
	}
	smp_rmb();
	return 0;
}

static void mt6797_a72_ml_write(int writer, int round, u64 *hash)
{
	int line;
	int word;

	for (line = 0; line < MT6797_A72_ML_LINES; line++) {
		for (word = 0; word < MT6797_A72_ML_WORDS; word++) {
			u64 value = mt6797_a72_ml_pattern(writer, round,
							 line, word);

			WRITE_ONCE(mt6797_a72_ml_data[line].words[word], value);
			*hash = mt6797_a72_ml_hash(*hash, value);
		}
	}
}

static int mt6797_a72_ml_verify(int writer, int round, u64 *hash,
				struct mt6797_a72_ml_result *result)
{
	int line;
	int word;

	for (line = 0; line < MT6797_A72_ML_LINES; line++) {
		for (word = 0; word < MT6797_A72_ML_WORDS; word++) {
			u64 expected = mt6797_a72_ml_pattern(writer, round,
							    line, word);
			u64 actual = READ_ONCE(mt6797_a72_ml_data[line].words[word]);

			*hash = mt6797_a72_ml_hash(*hash, actual);
			if (actual != expected) {
				result->bad_round = round;
				result->bad_line = line;
				result->bad_word = word;
				result->expected = expected;
				result->actual = actual;
				return -EILSEQ;
			}
		}
	}
	return 0;
}

static void mt6797_a72_ml_ipi(void *unused)
{
	unsigned int budget = MT6797_A72_ML_SPIN_BUDGET;
	int cpu = smp_processor_id();
	struct mt6797_a72_ml_result *result;
	u64 write_hash = MT6797_A72_ML_HASH_INIT;
	u64 read_hash = MT6797_A72_ML_HASH_INIT;
	int error = 0;
	int round;

	if (cpu == 8)
		result = &mt6797_a72_ml_result8;
	else if (cpu == 9)
		result = &mt6797_a72_ml_result9;
	else
		return;
	result->cpu = cpu;
	for (round = 1; round <= MT6797_A72_ML_ROUNDS; round++) {
		error = mt6797_a72_ml_wait_turn(cpu, &budget);
		if (error)
			break;
		if (cpu == 8) {
			mt6797_a72_ml_write(8, round, &write_hash);
			smp_wmb();
			WRITE_ONCE(mt6797_a72_ml_turn, 9);
			error = mt6797_a72_ml_wait_turn(8, &budget);
			if (error)
				break;
			error = mt6797_a72_ml_verify(9, round, &read_hash,
						      result);
		} else {
			error = mt6797_a72_ml_verify(8, round, &read_hash,
						      result);
			if (!error)
				mt6797_a72_ml_write(9, round, &write_hash);
		}
		if (error)
			break;
		result->done = round;
		if (cpu == 9) {
			smp_wmb();
			WRITE_ONCE(mt6797_a72_ml_turn, 8);
		}
	}
	result->write_hash = write_hash;
	result->read_hash = read_hash;
	result->error = error;
}

static void mt6797_a72_ml_reset(void)
{
	memset(&mt6797_a72_ml_result8, 0, sizeof(mt6797_a72_ml_result8));
	memset(&mt6797_a72_ml_result9, 0, sizeof(mt6797_a72_ml_result9));
	mt6797_a72_ml_result8.cpu = -1;
	mt6797_a72_ml_result9.cpu = -1;
	WRITE_ONCE(mt6797_a72_ml_turn, 8);
	atomic_set(&mt6797_a72_ml_reported, -1);
}

static bool mt6797_a72_coh_passed(void)
{
	return atomic_read(&mt6797_a72_coh_rounds) == MT6797_A72_COH_ROUNDS &&
	       atomic_read(&mt6797_a72_coh_cpu8) == 8 &&
	       atomic_read(&mt6797_a72_coh_cpu9) == 9 &&
	       atomic_read(&mt6797_a72_coh_error8) == 0 &&
	       atomic_read(&mt6797_a72_coh_error9) == 0 &&
	       READ_ONCE(mt6797_a72_coh_seq8) == MT6797_A72_COH_ROUNDS &&
	       READ_ONCE(mt6797_a72_coh_seq9) == MT6797_A72_COH_ROUNDS;
}

static void mt6797_a72_coh_workfn(struct work_struct *work)
"""
    replace_once(path, anchor, replacement)

    old = """static void mt6797_a72_coh_workfn(struct work_struct *work)
{
	cpumask_t targets;

	atomic_set(&mt6797_a72_coh_reported, -1);
	atomic_set(&mt6797_a72_coh_rounds, 0);
	atomic_set(&mt6797_a72_coh_cpu8, -1);
	atomic_set(&mt6797_a72_coh_cpu9, -1);
	atomic_set(&mt6797_a72_coh_error8, 0);
	atomic_set(&mt6797_a72_coh_error9, 0);
	WRITE_ONCE(mt6797_a72_coh_seq8, 0);
	WRITE_ONCE(mt6797_a72_coh_seq9, 0);
	WRITE_ONCE(mt6797_a72_coh_turn, 8);
	smp_wmb();
	if (smp_processor_id() != 0) {
		atomic_set(&mt6797_a72_coh_error8, -EXDEV);
		atomic_set(&mt6797_a72_coh_error9, -EXDEV);
		goto publish;
	}
	cpumask_clear(&targets);
	cpumask_set_cpu(8, &targets);
	cpumask_set_cpu(9, &targets);
	smp_call_function_many(&targets, mt6797_a72_coh_ipi, NULL, true);
	atomic_set(&mt6797_a72_coh_rounds, MT6797_A72_COH_ROUNDS);
publish:
	atomic_set(&mt6797_a72_coh_final_seq8,
		   READ_ONCE(mt6797_a72_coh_seq8));
	atomic_set(&mt6797_a72_coh_final_seq9,
		   READ_ONCE(mt6797_a72_coh_seq9));
	smp_wmb();
	atomic_set(&mt6797_a72_coh_reported, 1);
}
"""
    new = """static void mt6797_a72_coh_workfn(struct work_struct *work)
{
	cpumask_t targets;

	atomic_set(&mt6797_a72_coh_reported, -1);
	atomic_set(&mt6797_a72_coh_rounds, 0);
	atomic_set(&mt6797_a72_coh_cpu8, -1);
	atomic_set(&mt6797_a72_coh_cpu9, -1);
	atomic_set(&mt6797_a72_coh_error8, 0);
	atomic_set(&mt6797_a72_coh_error9, 0);
	WRITE_ONCE(mt6797_a72_coh_seq8, 0);
	WRITE_ONCE(mt6797_a72_coh_seq9, 0);
	WRITE_ONCE(mt6797_a72_coh_turn, 8);
	mt6797_a72_ml_reset();
	smp_wmb();
	if (smp_processor_id() != 0) {
		atomic_set(&mt6797_a72_coh_error8, -EXDEV);
		atomic_set(&mt6797_a72_coh_error9, -EXDEV);
		atomic_set(&mt6797_a72_ml_reported, 2);
		goto publish;
	}
	cpumask_clear(&targets);
	cpumask_set_cpu(8, &targets);
	cpumask_set_cpu(9, &targets);
	smp_call_function_many(&targets, mt6797_a72_coh_ipi, NULL, true);
	atomic_set(&mt6797_a72_coh_rounds, MT6797_A72_COH_ROUNDS);
	if (mt6797_a72_coh_passed()) {
		smp_call_function_many(&targets, mt6797_a72_ml_ipi, NULL, true);
		smp_wmb();
		atomic_set(&mt6797_a72_ml_reported, 1);
	} else {
		atomic_set(&mt6797_a72_ml_reported, 2);
	}
publish:
	atomic_set(&mt6797_a72_coh_final_seq8,
		   READ_ONCE(mt6797_a72_coh_seq8));
	atomic_set(&mt6797_a72_coh_final_seq9,
		   READ_ONCE(mt6797_a72_coh_seq9));
	smp_wmb();
	atomic_set(&mt6797_a72_coh_reported, 1);
}
"""
    replace_once(path, old, new)

    old = """	if (!schedule_work_on(0, &mt6797_a72_coh_work)) {
		atomic_set(&mt6797_a72_coh_error8, -EBUSY);
		atomic_set(&mt6797_a72_coh_error9, -EBUSY);
		smp_wmb();
		atomic_set(&mt6797_a72_coh_reported, 2);
	}
"""
    new = """	if (!schedule_work_on(0, &mt6797_a72_coh_work)) {
		atomic_set(&mt6797_a72_coh_error8, -EBUSY);
		atomic_set(&mt6797_a72_coh_error9, -EBUSY);
		atomic_set(&mt6797_a72_ml_reported, 2);
		smp_wmb();
		atomic_set(&mt6797_a72_coh_reported, 2);
	}
"""
    replace_once(path, old, new)

    anchor = """}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    replacement = """}

static void mt6797_a72_ml_snapshot(int *reported,
				   struct mt6797_a72_ml_result *result8,
				   struct mt6797_a72_ml_result *result9)
{
	*reported = atomic_read(&mt6797_a72_ml_reported);
	smp_rmb();
	*result8 = mt6797_a72_ml_result8;
	*result9 = mt6797_a72_ml_result9;
}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    replace_once(path, anchor, replacement)

    old = """	int coh_seq8;
	int coh_seq9;
	int observed_cpu8 = -1;
"""
    new = """	int coh_seq8;
	int coh_seq9;
	int ml_reported;
	struct mt6797_a72_ml_result ml_result8;
	struct mt6797_a72_ml_result ml_result9;
	int observed_cpu8 = -1;
"""
    replace_once(path, old, new)

    old = """	mt6797_a72_coh_snapshot(&coh_reported, &coh_rounds,
				 &coh_cpu8, &coh_cpu9,
				 &coh_error8, &coh_error9,
				 &coh_seq8, &coh_seq9);
	if (coh_reported == 1 && coh_rounds == MT6797_A72_COH_ROUNDS &&
	    coh_cpu8 == 8 && coh_cpu9 == 9 && !coh_error8 && !coh_error9 &&
	    coh_seq8 == MT6797_A72_COH_ROUNDS &&
	    coh_seq9 == MT6797_A72_COH_ROUNDS)
		pr_emerg("gemini-a72-pair-v4 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d\\n",
			 hps_reported, hps_cpu, hps_error, hps_count,
			 coh_reported, coh_rounds, coh_cpu8, coh_cpu9,
			 coh_error8, coh_error9, coh_seq8, coh_seq9);
	else
		pr_emerg("gemini-a72-pair-v4 result=fault sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d\\n",
			 hps_reported, hps_cpu, hps_error, hps_count,
			 coh_reported, coh_rounds, coh_cpu8, coh_cpu9,
			 coh_error8, coh_error9, coh_seq8, coh_seq9);
"""
    new = """	mt6797_a72_coh_snapshot(&coh_reported, &coh_rounds,
				 &coh_cpu8, &coh_cpu9,
				 &coh_error8, &coh_error9,
				 &coh_seq8, &coh_seq9);
	mt6797_a72_ml_snapshot(&ml_reported, &ml_result8, &ml_result9);
	if (hps_reported == 1 && hps_cpu == 9 && hps_error == -EPERM &&
	    hps_count > 0 &&
	    coh_reported == 1 && coh_rounds == MT6797_A72_COH_ROUNDS &&
	    coh_cpu8 == 8 && coh_cpu9 == 9 && !coh_error8 && !coh_error9 &&
	    coh_seq8 == MT6797_A72_COH_ROUNDS &&
	    coh_seq9 == MT6797_A72_COH_ROUNDS &&
	    ml_reported == 1 && ml_result8.cpu == 8 && ml_result9.cpu == 9 &&
	    !ml_result8.error && !ml_result9.error &&
	    ml_result8.done == MT6797_A72_ML_ROUNDS &&
	    ml_result9.done == MT6797_A72_ML_ROUNDS &&
	    ml_result8.write_hash != 0 && ml_result9.write_hash != 0 &&
	    ml_result8.write_hash == ml_result9.read_hash &&
	    ml_result9.write_hash == ml_result8.read_hash &&
	    !ml_result8.bad_round && !ml_result9.bad_round)
		pr_emerg("gemini-a72-pair-v5 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d ml_reported=%d ml_rounds=64 ml_lines=256 ml_words=8 ml_cpu8=%d ml_cpu9=%d ml_error8=%d ml_error9=%d ml_done8=%d ml_done9=%d ml_hash8w=%016llx ml_hash8r=%016llx ml_hash9w=%016llx ml_hash9r=%016llx ml_bad_round=%d ml_bad_line=%d ml_bad_word=%d ml_expected=%016llx ml_actual=%016llx\\n",
			 hps_reported, hps_cpu, hps_error, hps_count,
			 coh_reported, coh_rounds, coh_cpu8, coh_cpu9,
			 coh_error8, coh_error9, coh_seq8, coh_seq9,
			 ml_reported, ml_result8.cpu, ml_result9.cpu,
			 ml_result8.error, ml_result9.error,
			 ml_result8.done, ml_result9.done,
			 (unsigned long long)ml_result8.write_hash,
			 (unsigned long long)ml_result8.read_hash,
			 (unsigned long long)ml_result9.write_hash,
			 (unsigned long long)ml_result9.read_hash,
			 0, 0, 0, 0ULL, 0ULL);
	else {
		struct mt6797_a72_ml_result *bad = ml_result8.error ?
			&ml_result8 : &ml_result9;

		pr_emerg("gemini-a72-pair-v5 result=fault sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d ml_reported=%d ml_rounds=64 ml_lines=256 ml_words=8 ml_cpu8=%d ml_cpu9=%d ml_error8=%d ml_error9=%d ml_done8=%d ml_done9=%d ml_hash8w=%016llx ml_hash8r=%016llx ml_hash9w=%016llx ml_hash9r=%016llx ml_bad_round=%d ml_bad_line=%d ml_bad_word=%d ml_expected=%016llx ml_actual=%016llx\\n",
			 hps_reported, hps_cpu, hps_error, hps_count,
			 coh_reported, coh_rounds, coh_cpu8, coh_cpu9,
			 coh_error8, coh_error9, coh_seq8, coh_seq9,
			 ml_reported, ml_result8.cpu, ml_result9.cpu,
			 ml_result8.error, ml_result9.error,
			 ml_result8.done, ml_result9.done,
			 (unsigned long long)ml_result8.write_hash,
			 (unsigned long long)ml_result8.read_hash,
			 (unsigned long long)ml_result9.write_hash,
			 (unsigned long long)ml_result9.read_hash,
			 bad->bad_round, bad->bad_line, bad->bad_word,
			 (unsigned long long)bad->expected,
			 (unsigned long long)bad->actual);
	}
"""
    replace_once(path, old, new)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise EditError("source is not a directory")
    edit_psci(source)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EditError as exc:
        raise SystemExit(f"error: {exc}")
