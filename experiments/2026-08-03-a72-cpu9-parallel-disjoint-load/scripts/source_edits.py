#!/usr/bin/env python3
"""Apply deterministic parallel-load edits to the exact pair-v5 parent."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != expected:
        raise EditError(f"{path}: expected {expected} edit anchors, found {count}")
    path.write_text(text.replace(old, new))


def edit_psci(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    anchor = "static void mt6797_a72_coh_workfn(struct work_struct *work)\n"
    parallel = r"""#define MT6797_A72_PL_ROUNDS 128
#define MT6797_A72_PL_LINES 1024
#define MT6797_A72_PL_WORDS 8
#define MT6797_A72_PL_SPIN_BUDGET (1U << 26)
#define MT6797_A72_PL_HASH_INIT 1469598103934665603ULL
#define MT6797_A72_PL_HASH_PRIME 1099511628211ULL

struct mt6797_a72_pl_line {
	u64 words[MT6797_A72_PL_WORDS];
} __aligned(64);

struct mt6797_a72_pl_result {
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

static struct mt6797_a72_pl_line
	mt6797_a72_pl_data[MT6797_A72_PL_LINES] __aligned(64);
static struct mt6797_a72_pl_result mt6797_a72_pl_result8;
static struct mt6797_a72_pl_result mt6797_a72_pl_result9;
static atomic_t mt6797_a72_pl_reported = ATOMIC_INIT(0);
static atomic_t mt6797_a72_pl_ready = ATOMIC_INIT(0);
static atomic_t mt6797_a72_pl_written = ATOMIC_INIT(0);
static atomic_t mt6797_a72_pl_verified = ATOMIC_INIT(0);

static u64 mt6797_a72_pl_pattern(int writer, int round, int line, int word)
{
	u64 value = 0xd6e8feb86659fd93ULL;

	value ^= (u64)writer << 60;
	value ^= (u64)round << 32;
	value ^= (u64)line << 8;
	value ^= (u64)word;
	value ^= value << 13;
	value ^= value >> 7;
	value ^= value << 17;
	return value;
}

static u64 mt6797_a72_pl_hash(u64 hash, u64 value)
{
	return (hash ^ value) * MT6797_A72_PL_HASH_PRIME;
}

static int mt6797_a72_pl_wait(atomic_t *counter, int expected,
			      unsigned int *budget)
{
	while (atomic_read(counter) != expected) {
		if (!(*budget)--)
			return -ETIMEDOUT;
		cpu_relax();
	}
	smp_rmb();
	return 0;
}

static void mt6797_a72_pl_write(int writer, int round, u64 *hash)
{
	int line;
	int word;
	int parity = writer == 8 ? 0 : 1;

	for (line = parity; line < MT6797_A72_PL_LINES; line += 2) {
		for (word = 0; word < MT6797_A72_PL_WORDS; word++) {
			u64 value = mt6797_a72_pl_pattern(writer, round,
						 line, word);

			WRITE_ONCE(mt6797_a72_pl_data[line].words[word], value);
			*hash = mt6797_a72_pl_hash(*hash, value);
		}
	}
}

static int mt6797_a72_pl_verify(int writer, int round, u64 *hash,
				struct mt6797_a72_pl_result *result)
{
	int line;
	int word;
	int parity = writer == 8 ? 0 : 1;

	for (line = parity; line < MT6797_A72_PL_LINES; line += 2) {
		for (word = 0; word < MT6797_A72_PL_WORDS; word++) {
			u64 expected = mt6797_a72_pl_pattern(writer, round,
						    line, word);
			u64 actual = READ_ONCE(mt6797_a72_pl_data[line].words[word]);

			*hash = mt6797_a72_pl_hash(*hash, actual);
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

static void mt6797_a72_pl_ipi(void *unused)
{
	unsigned int budget = MT6797_A72_PL_SPIN_BUDGET;
	int cpu = smp_processor_id();
	struct mt6797_a72_pl_result *result;
	u64 write_hash = MT6797_A72_PL_HASH_INIT;
	u64 read_hash = MT6797_A72_PL_HASH_INIT;
	int error = 0;
	int barrier_error;
	int round;

	if (cpu == 8)
		result = &mt6797_a72_pl_result8;
	else if (cpu == 9)
		result = &mt6797_a72_pl_result9;
	else
		return;
	result->cpu = cpu;
	for (round = 1; round <= MT6797_A72_PL_ROUNDS; round++) {
		atomic_inc(&mt6797_a72_pl_ready);
		error = mt6797_a72_pl_wait(&mt6797_a72_pl_ready,
					    2 * round, &budget);
		if (error)
			break;
		mt6797_a72_pl_write(cpu, round, &write_hash);
		smp_wmb();
		atomic_inc(&mt6797_a72_pl_written);
		error = mt6797_a72_pl_wait(&mt6797_a72_pl_written,
					    2 * round, &budget);
		if (error)
			break;
		error = mt6797_a72_pl_verify(cpu == 8 ? 9 : 8, round,
					      &read_hash, result);
		smp_wmb();
		atomic_inc(&mt6797_a72_pl_verified);
		barrier_error = mt6797_a72_pl_wait(&mt6797_a72_pl_verified,
						    2 * round, &budget);
		if (!error)
			error = barrier_error;
		if (error)
			break;
		result->done = round;
	}
	result->write_hash = write_hash;
	result->read_hash = read_hash;
	result->error = error;
}

static void mt6797_a72_pl_reset(void)
{
	memset(&mt6797_a72_pl_result8, 0, sizeof(mt6797_a72_pl_result8));
	memset(&mt6797_a72_pl_result9, 0, sizeof(mt6797_a72_pl_result9));
	mt6797_a72_pl_result8.cpu = -1;
	mt6797_a72_pl_result9.cpu = -1;
	atomic_set(&mt6797_a72_pl_ready, 0);
	atomic_set(&mt6797_a72_pl_written, 0);
	atomic_set(&mt6797_a72_pl_verified, 0);
	atomic_set(&mt6797_a72_pl_reported, -1);
}

static bool mt6797_a72_ml_passed(void)
{
	return atomic_read(&mt6797_a72_ml_reported) == 1 &&
	       mt6797_a72_ml_result8.cpu == 8 &&
	       mt6797_a72_ml_result9.cpu == 9 &&
	       !mt6797_a72_ml_result8.error &&
	       !mt6797_a72_ml_result9.error &&
	       mt6797_a72_ml_result8.done == MT6797_A72_ML_ROUNDS &&
	       mt6797_a72_ml_result9.done == MT6797_A72_ML_ROUNDS &&
	       mt6797_a72_ml_result8.write_hash != 0 &&
	       mt6797_a72_ml_result9.write_hash != 0 &&
	       mt6797_a72_ml_result8.write_hash ==
		mt6797_a72_ml_result9.read_hash &&
	       mt6797_a72_ml_result9.write_hash ==
		mt6797_a72_ml_result8.read_hash &&
	       !mt6797_a72_ml_result8.bad_round &&
	       !mt6797_a72_ml_result9.bad_round;
}

static void mt6797_a72_coh_workfn(struct work_struct *work)
"""
    replace_exact(path, anchor, parallel)

    replace_exact(
        path,
        "\tmt6797_a72_ml_reset();\n\tsmp_wmb();\n",
        "\tmt6797_a72_ml_reset();\n\tmt6797_a72_pl_reset();\n\tsmp_wmb();\n",
    )
    replace_exact(
        path,
        "\t\tatomic_set(&mt6797_a72_ml_reported, 2);\n\t\tgoto publish;\n",
        "\t\tatomic_set(&mt6797_a72_ml_reported, 2);\n"
        "\t\tatomic_set(&mt6797_a72_pl_reported, 2);\n\t\tgoto publish;\n",
    )
    old_phase = """\tif (mt6797_a72_coh_passed()) {
\t\tsmp_call_function_many(&targets, mt6797_a72_ml_ipi, NULL, true);
\t\tsmp_wmb();
\t\tatomic_set(&mt6797_a72_ml_reported, 1);
\t} else {
\t\tatomic_set(&mt6797_a72_ml_reported, 2);
\t}
publish:
"""
    new_phase = """\tif (mt6797_a72_coh_passed()) {
\t\tsmp_call_function_many(&targets, mt6797_a72_ml_ipi, NULL, true);
\t\tsmp_wmb();
\t\tatomic_set(&mt6797_a72_ml_reported, 1);
\t\tif (mt6797_a72_ml_passed()) {
\t\t\tsmp_call_function_many(&targets, mt6797_a72_pl_ipi,
\t\t\t\t\t       NULL, true);
\t\t\tsmp_wmb();
\t\t\tatomic_set(&mt6797_a72_pl_reported, 1);
\t\t} else {
\t\t\tatomic_set(&mt6797_a72_pl_reported, 2);
\t\t}
\t} else {
\t\tatomic_set(&mt6797_a72_ml_reported, 2);
\t\tatomic_set(&mt6797_a72_pl_reported, 2);
\t}
publish:
"""
    replace_exact(path, old_phase, new_phase)
    replace_exact(
        path,
        "\t\tatomic_set(&mt6797_a72_ml_reported, 2);\n"
        "\t\tsmp_wmb();\n\t\tatomic_set(&mt6797_a72_coh_reported, 2);\n",
        "\t\tatomic_set(&mt6797_a72_ml_reported, 2);\n"
        "\t\tatomic_set(&mt6797_a72_pl_reported, 2);\n"
        "\t\tsmp_wmb();\n\t\tatomic_set(&mt6797_a72_coh_reported, 2);\n",
    )

    snapshot_anchor = """}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    snapshot = """}

static void mt6797_a72_pl_snapshot(int *reported,
\t\t\t\t   struct mt6797_a72_pl_result *result8,
\t\t\t\t   struct mt6797_a72_pl_result *result9,
\t\t\t\t   int *ready, int *written, int *verified)
{
\t*reported = atomic_read(&mt6797_a72_pl_reported);
\tsmp_rmb();
\t*result8 = mt6797_a72_pl_result8;
\t*result9 = mt6797_a72_pl_result9;
\t*ready = atomic_read(&mt6797_a72_pl_ready);
\t*written = atomic_read(&mt6797_a72_pl_written);
\t*verified = atomic_read(&mt6797_a72_pl_verified);
}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    replace_exact(path, snapshot_anchor, snapshot)

    replace_exact(
        path,
        "\tstruct mt6797_a72_ml_result ml_result9;\n\tint observed_cpu8 = -1;\n",
        "\tstruct mt6797_a72_ml_result ml_result9;\n"
        "\tint pl_reported;\n"
        "\tstruct mt6797_a72_pl_result pl_result8;\n"
        "\tstruct mt6797_a72_pl_result pl_result9;\n"
        "\tint pl_ready;\n\tint pl_written;\n\tint pl_verified;\n"
        "\tint observed_cpu8 = -1;\n",
    )
    replace_exact(
        path,
        "\tmt6797_a72_ml_snapshot(&ml_reported, &ml_result8, &ml_result9);\n",
        "\tmt6797_a72_ml_snapshot(&ml_reported, &ml_result8, &ml_result9);\n"
        "\tmt6797_a72_pl_snapshot(&pl_reported, &pl_result8, &pl_result9,\n"
        "\t\t\t\t &pl_ready, &pl_written, &pl_verified);\n",
    )
    pass_tail = "\t    !ml_result8.bad_round && !ml_result9.bad_round)\n"
    pass_parallel = """\t    !ml_result8.bad_round && !ml_result9.bad_round &&
\t    pl_reported == 1 && pl_result8.cpu == 8 && pl_result9.cpu == 9 &&
\t    !pl_result8.error && !pl_result9.error &&
\t    pl_result8.done == MT6797_A72_PL_ROUNDS &&
\t    pl_result9.done == MT6797_A72_PL_ROUNDS &&
\t    pl_ready == 2 * MT6797_A72_PL_ROUNDS &&
\t    pl_written == 2 * MT6797_A72_PL_ROUNDS &&
\t    pl_verified == 2 * MT6797_A72_PL_ROUNDS &&
\t    pl_result8.write_hash != 0 && pl_result9.write_hash != 0 &&
\t    pl_result8.write_hash == pl_result9.read_hash &&
\t    pl_result9.write_hash == pl_result8.read_hash &&
\t    !pl_result8.bad_round && !pl_result9.bad_round)
"""
    replace_exact(path, pass_tail, pass_parallel)
    replace_exact(path, "gemini-a72-pair-v5", "gemini-a72-pair-v6", expected=2)

    old_format = " ml_actual=%016llx\\n\""
    new_format = (
        " ml_actual=%016llx"
        " pl_reported=%d pl_rounds=128 pl_lines=1024 pl_words=8"
        " pl_cpu8=%d pl_cpu9=%d pl_error8=%d pl_error9=%d"
        " pl_done8=%d pl_done9=%d pl_ready=%d pl_written=%d pl_verified=%d"
        " pl_hash8w=%016llx pl_hash8r=%016llx"
        " pl_hash9w=%016llx pl_hash9r=%016llx"
        " pl_bad_round=%d pl_bad_line=%d pl_bad_word=%d"
        " pl_expected=%016llx pl_actual=%016llx\\n\""
    )
    replace_exact(path, old_format, new_format, expected=2)

    pass_args = """\t\t\t 0, 0, 0, 0ULL, 0ULL);
"""
    pass_args_new = """\t\t\t 0, 0, 0, 0ULL, 0ULL,
\t\t\t pl_reported, pl_result8.cpu, pl_result9.cpu,
\t\t\t pl_result8.error, pl_result9.error,
\t\t\t pl_result8.done, pl_result9.done,
\t\t\t pl_ready, pl_written, pl_verified,
\t\t\t (unsigned long long)pl_result8.write_hash,
\t\t\t (unsigned long long)pl_result8.read_hash,
\t\t\t (unsigned long long)pl_result9.write_hash,
\t\t\t (unsigned long long)pl_result9.read_hash,
\t\t\t 0, 0, 0, 0ULL, 0ULL);
"""
    replace_exact(path, pass_args, pass_args_new)

    fault_decl = """\t\tstruct mt6797_a72_ml_result *bad = ml_result8.error ?
\t\t\t&ml_result8 : &ml_result9;

"""
    fault_decl_new = """\t\tstruct mt6797_a72_ml_result *bad = ml_result8.error ?
\t\t\t&ml_result8 : &ml_result9;
\t\tstruct mt6797_a72_pl_result *pl_bad = pl_result8.error ?
\t\t\t&pl_result8 : &pl_result9;

"""
    replace_exact(path, fault_decl, fault_decl_new)
    fault_args = """\t\t\t (unsigned long long)bad->expected,
\t\t\t (unsigned long long)bad->actual);
"""
    fault_args_new = """\t\t\t (unsigned long long)bad->expected,
\t\t\t (unsigned long long)bad->actual,
\t\t\t pl_reported, pl_result8.cpu, pl_result9.cpu,
\t\t\t pl_result8.error, pl_result9.error,
\t\t\t pl_result8.done, pl_result9.done,
\t\t\t pl_ready, pl_written, pl_verified,
\t\t\t (unsigned long long)pl_result8.write_hash,
\t\t\t (unsigned long long)pl_result8.read_hash,
\t\t\t (unsigned long long)pl_result9.write_hash,
\t\t\t (unsigned long long)pl_result9.read_hash,
\t\t\t pl_bad->bad_round, pl_bad->bad_line, pl_bad->bad_word,
\t\t\t (unsigned long long)pl_bad->expected,
\t\t\t (unsigned long long)pl_bad->actual);
"""
    replace_exact(path, fault_args, fault_args_new)


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
