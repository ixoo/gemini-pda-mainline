#!/usr/bin/env python3
"""Apply deterministic scheduler-context edits to the exact pair-v6 parent."""

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
    replace_exact(
        path,
        "#include <linux/workqueue.h>\n",
        "#include <linux/workqueue.h>\n"
        "#include <linux/completion.h>\n"
        "#include <linux/err.h>\n"
        "#include <linux/interrupt.h>\n"
        "#include <linux/kthread.h>\n",
    )

    anchor = "static void mt6797_a72_coh_workfn(struct work_struct *work)\n"
    scheduler = r"""#define MT6797_A72_SC_ITERATIONS 262144
#define MT6797_A72_SC_RESCHED_INTERVAL 4096
#define MT6797_A72_SC_RESCHEDS 64
#define MT6797_A72_SC_SPIN_BUDGET (1U << 25)
#define MT6797_A72_SC_TIMEOUT_MS 2000
#define MT6797_A72_SC_HASH_INIT 1469598103934665603ULL
#define MT6797_A72_SC_HASH_PRIME 1099511628211ULL
#define MT6797_A72_SC_HASH8_EXPECTED 0xf678147669874ecdULL
#define MT6797_A72_SC_HASH9_EXPECTED 0xc2274327e9c8104cULL

struct mt6797_a72_sc_result {
	int expected_cpu;
	int start_cpu;
	int end_cpu;
	int task_context;
	int create_error;
	int wake_result;
	int wait_complete;
	int error;
	int stop_result;
	int done;
	int rescheds;
	u64 hash;
};

static struct mt6797_a72_sc_result mt6797_a72_sc_result8;
static struct mt6797_a72_sc_result mt6797_a72_sc_result9;
static struct task_struct *mt6797_a72_sc_task8;
static struct task_struct *mt6797_a72_sc_task9;
static DECLARE_COMPLETION(mt6797_a72_sc_done8);
static DECLARE_COMPLETION(mt6797_a72_sc_done9);
static atomic_t mt6797_a72_sc_reported = ATOMIC_INIT(0);
static atomic_t mt6797_a72_sc_ready = ATOMIC_INIT(0);
static atomic_t mt6797_a72_sc_finished = ATOMIC_INIT(0);

static u64 mt6797_a72_sc_step(u64 value, int cpu, unsigned int iteration)
{
	value ^= (u64)cpu << 57;
	value ^= (u64)iteration * 0x9e3779b97f4a7c15ULL;
	value ^= value << 13;
	value ^= value >> 7;
	value ^= value << 17;
	return value;
}

static int mt6797_a72_sc_thread(void *data)
{
	struct mt6797_a72_sc_result *result = data;
	struct completion *done;
	unsigned int budget = MT6797_A72_SC_SPIN_BUDGET;
	u64 value = 0xd6e8feb86659fd93ULL ^ (u64)result->expected_cpu;
	u64 hash = MT6797_A72_SC_HASH_INIT;
	unsigned int iteration;
	int cpu;
	int error = 0;

	done = result->expected_cpu == 8 ? &mt6797_a72_sc_done8 :
		&mt6797_a72_sc_done9;
	result->task_context = !!(current->flags & PF_KTHREAD) && !in_interrupt();
	cpu = get_cpu();
	put_cpu();
	result->start_cpu = cpu;
	if (!result->task_context)
		error = -EINVAL;
	else if (cpu != result->expected_cpu)
		error = -EXDEV;

	atomic_inc(&mt6797_a72_sc_ready);
	while (atomic_read(&mt6797_a72_sc_ready) != 2) {
		if (!budget--) {
			if (!error)
				error = -ETIMEDOUT;
			break;
		}
		cpu_relax();
	}
	smp_rmb();
	if (!error) {
		for (iteration = 0; iteration < MT6797_A72_SC_ITERATIONS;
		     iteration++) {
			value = mt6797_a72_sc_step(value, result->expected_cpu,
						 iteration);
			hash = (hash ^ value) * MT6797_A72_SC_HASH_PRIME;
			result->done = iteration + 1;
			if (!((iteration + 1) % MT6797_A72_SC_RESCHED_INTERVAL)) {
				cond_resched();
				result->rescheds++;
			}
		}
	}
	cpu = get_cpu();
	put_cpu();
	result->end_cpu = cpu;
	if (!error && cpu != result->expected_cpu)
		error = -EXDEV;
	if (!error && (!(current->flags & PF_KTHREAD) || in_interrupt()))
		error = -EINVAL;
	result->hash = hash;
	result->error = error;
	smp_wmb();
	atomic_inc(&mt6797_a72_sc_finished);
	complete(done);
	return error;
}

static bool mt6797_a72_sc_wait_until(struct completion *done,
				     unsigned long deadline)
{
	unsigned long remaining;

	if (completion_done(done))
		return true;
	if (time_after_eq(jiffies, deadline))
		return false;
	remaining = deadline - jiffies;
	return !!wait_for_completion_timeout(done, remaining);
}

static void mt6797_a72_sc_reset(void)
{
	memset(&mt6797_a72_sc_result8, 0, sizeof(mt6797_a72_sc_result8));
	memset(&mt6797_a72_sc_result9, 0, sizeof(mt6797_a72_sc_result9));
	mt6797_a72_sc_result8.expected_cpu = 8;
	mt6797_a72_sc_result9.expected_cpu = 9;
	mt6797_a72_sc_result8.start_cpu = -1;
	mt6797_a72_sc_result8.end_cpu = -1;
	mt6797_a72_sc_result9.start_cpu = -1;
	mt6797_a72_sc_result9.end_cpu = -1;
	mt6797_a72_sc_result8.create_error = -ECANCELED;
	mt6797_a72_sc_result9.create_error = -ECANCELED;
	mt6797_a72_sc_result8.stop_result = -ECANCELED;
	mt6797_a72_sc_result9.stop_result = -ECANCELED;
	mt6797_a72_sc_task8 = NULL;
	mt6797_a72_sc_task9 = NULL;
	reinit_completion(&mt6797_a72_sc_done8);
	reinit_completion(&mt6797_a72_sc_done9);
	atomic_set(&mt6797_a72_sc_ready, 0);
	atomic_set(&mt6797_a72_sc_finished, 0);
	atomic_set(&mt6797_a72_sc_reported, -1);
}

static bool mt6797_a72_pl_passed(void)
{
	return atomic_read(&mt6797_a72_pl_reported) == 1 &&
	       mt6797_a72_pl_result8.cpu == 8 &&
	       mt6797_a72_pl_result9.cpu == 9 &&
	       !mt6797_a72_pl_result8.error &&
	       !mt6797_a72_pl_result9.error &&
	       mt6797_a72_pl_result8.done == MT6797_A72_PL_ROUNDS &&
	       mt6797_a72_pl_result9.done == MT6797_A72_PL_ROUNDS &&
	       atomic_read(&mt6797_a72_pl_ready) == 2 * MT6797_A72_PL_ROUNDS &&
	       atomic_read(&mt6797_a72_pl_written) == 2 * MT6797_A72_PL_ROUNDS &&
	       atomic_read(&mt6797_a72_pl_verified) == 2 * MT6797_A72_PL_ROUNDS &&
	       mt6797_a72_pl_result8.write_hash != 0 &&
	       mt6797_a72_pl_result9.write_hash != 0 &&
	       mt6797_a72_pl_result8.write_hash ==
		mt6797_a72_pl_result9.read_hash &&
	       mt6797_a72_pl_result9.write_hash ==
		mt6797_a72_pl_result8.read_hash &&
	       !mt6797_a72_pl_result8.bad_round &&
	       !mt6797_a72_pl_result9.bad_round;
}

static void mt6797_a72_sc_run(void)
{
	unsigned long deadline;

	mt6797_a72_sc_task8 = kthread_create_on_cpu(mt6797_a72_sc_thread,
					&mt6797_a72_sc_result8, 8,
					"gemini-a72-sc/%u");
	if (IS_ERR(mt6797_a72_sc_task8)) {
		mt6797_a72_sc_result8.create_error =
			PTR_ERR(mt6797_a72_sc_task8);
		mt6797_a72_sc_task8 = NULL;
	} else {
		mt6797_a72_sc_result8.create_error = 0;
	}
	mt6797_a72_sc_task9 = kthread_create_on_cpu(mt6797_a72_sc_thread,
					&mt6797_a72_sc_result9, 9,
					"gemini-a72-sc/%u");
	if (IS_ERR(mt6797_a72_sc_task9)) {
		mt6797_a72_sc_result9.create_error =
			PTR_ERR(mt6797_a72_sc_task9);
		mt6797_a72_sc_task9 = NULL;
	} else {
		mt6797_a72_sc_result9.create_error = 0;
	}
	if (!mt6797_a72_sc_task8 || !mt6797_a72_sc_task9)
		goto stop;

	mt6797_a72_sc_result8.wake_result =
		wake_up_process(mt6797_a72_sc_task8);
	mt6797_a72_sc_result9.wake_result =
		wake_up_process(mt6797_a72_sc_task9);
	deadline = jiffies + msecs_to_jiffies(MT6797_A72_SC_TIMEOUT_MS);
	mt6797_a72_sc_result8.wait_complete =
		mt6797_a72_sc_wait_until(&mt6797_a72_sc_done8, deadline);
	mt6797_a72_sc_result9.wait_complete =
		mt6797_a72_sc_wait_until(&mt6797_a72_sc_done9, deadline);

stop:
	if (mt6797_a72_sc_task8) {
		mt6797_a72_sc_result8.stop_result =
			kthread_stop(mt6797_a72_sc_task8);
		mt6797_a72_sc_task8 = NULL;
	}
	if (mt6797_a72_sc_task9) {
		mt6797_a72_sc_result9.stop_result =
			kthread_stop(mt6797_a72_sc_task9);
		mt6797_a72_sc_task9 = NULL;
	}
	smp_wmb();
	atomic_set(&mt6797_a72_sc_reported, 1);
}

static void mt6797_a72_coh_workfn(struct work_struct *work)
"""
    replace_exact(path, anchor, scheduler)

    replace_exact(
        path,
        "\tmt6797_a72_pl_reset();\n\tsmp_wmb();\n",
        "\tmt6797_a72_pl_reset();\n\tmt6797_a72_sc_reset();\n\tsmp_wmb();\n",
    )
    replace_exact(
        path,
        "\t\tatomic_set(&mt6797_a72_pl_reported, 2);\n\t\tgoto publish;\n",
        "\t\tatomic_set(&mt6797_a72_pl_reported, 2);\n"
        "\t\tatomic_set(&mt6797_a72_sc_reported, 2);\n\t\tgoto publish;\n",
    )
    old_phase = """\t\tif (mt6797_a72_ml_passed()) {
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
    new_phase = """\t\tif (mt6797_a72_ml_passed()) {
\t\t\tsmp_call_function_many(&targets, mt6797_a72_pl_ipi,
\t\t\t\t\t       NULL, true);
\t\t\tsmp_wmb();
\t\t\tatomic_set(&mt6797_a72_pl_reported, 1);
\t\t\tif (mt6797_a72_pl_passed())
\t\t\t\tmt6797_a72_sc_run();
\t\t\telse
\t\t\t\tatomic_set(&mt6797_a72_sc_reported, 2);
\t\t} else {
\t\t\tatomic_set(&mt6797_a72_pl_reported, 2);
\t\t\tatomic_set(&mt6797_a72_sc_reported, 2);
\t\t}
\t} else {
\t\tatomic_set(&mt6797_a72_ml_reported, 2);
\t\tatomic_set(&mt6797_a72_pl_reported, 2);
\t\tatomic_set(&mt6797_a72_sc_reported, 2);
\t}
publish:
"""
    replace_exact(path, old_phase, new_phase)
    replace_exact(
        path,
        "\t\tatomic_set(&mt6797_a72_pl_reported, 2);\n"
        "\t\tsmp_wmb();\n\t\tatomic_set(&mt6797_a72_coh_reported, 2);\n",
        "\t\tatomic_set(&mt6797_a72_pl_reported, 2);\n"
        "\t\tatomic_set(&mt6797_a72_sc_reported, 2);\n"
        "\t\tsmp_wmb();\n\t\tatomic_set(&mt6797_a72_coh_reported, 2);\n",
    )

    snapshot_anchor = """}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    snapshot = """}

static void mt6797_a72_sc_snapshot(int *reported,
\t\t\t\t   struct mt6797_a72_sc_result *result8,
\t\t\t\t   struct mt6797_a72_sc_result *result9,
\t\t\t\t   int *ready, int *finished)
{
\t*reported = atomic_read(&mt6797_a72_sc_reported);
\tsmp_rmb();
\t*result8 = mt6797_a72_sc_result8;
\t*result9 = mt6797_a72_sc_result9;
\t*ready = atomic_read(&mt6797_a72_sc_ready);
\t*finished = atomic_read(&mt6797_a72_sc_finished);
}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    replace_exact(path, snapshot_anchor, snapshot)

    replace_exact(
        path,
        "\tint pl_verified;\n\tint observed_cpu8 = -1;\n",
        "\tint pl_verified;\n"
        "\tint sc_reported;\n"
        "\tstruct mt6797_a72_sc_result sc_result8;\n"
        "\tstruct mt6797_a72_sc_result sc_result9;\n"
        "\tint sc_ready;\n\tint sc_finished;\n"
        "\tint observed_cpu8 = -1;\n",
    )
    replace_exact(
        path,
        "\tmt6797_a72_pl_snapshot(&pl_reported, &pl_result8, &pl_result9,\n"
        "\t\t\t\t &pl_ready, &pl_written, &pl_verified);\n",
        "\tmt6797_a72_pl_snapshot(&pl_reported, &pl_result8, &pl_result9,\n"
        "\t\t\t\t &pl_ready, &pl_written, &pl_verified);\n"
        "\tmt6797_a72_sc_snapshot(&sc_reported, &sc_result8, &sc_result9,\n"
        "\t\t\t\t &sc_ready, &sc_finished);\n",
    )
    pass_tail = "\t    !pl_result8.bad_round && !pl_result9.bad_round)\n"
    pass_scheduler = """\t    !pl_result8.bad_round && !pl_result9.bad_round &&
\t    sc_reported == 1 && sc_result8.expected_cpu == 8 &&
\t    sc_result9.expected_cpu == 9 && sc_result8.start_cpu == 8 &&
\t    sc_result8.end_cpu == 8 && sc_result9.start_cpu == 9 &&
\t    sc_result9.end_cpu == 9 && sc_result8.task_context == 1 &&
\t    sc_result9.task_context == 1 && !sc_result8.create_error &&
\t    !sc_result9.create_error && sc_result8.wake_result == 1 &&
\t    sc_result9.wake_result == 1 && sc_result8.wait_complete == 1 &&
\t    sc_result9.wait_complete == 1 && !sc_result8.error &&
\t    !sc_result9.error && !sc_result8.stop_result &&
\t    !sc_result9.stop_result &&
\t    sc_result8.stop_result == sc_result8.error &&
\t    sc_result9.stop_result == sc_result9.error &&
\t    sc_result8.done == MT6797_A72_SC_ITERATIONS &&
\t    sc_result9.done == MT6797_A72_SC_ITERATIONS &&
\t    sc_result8.rescheds == MT6797_A72_SC_RESCHEDS &&
\t    sc_result9.rescheds == MT6797_A72_SC_RESCHEDS &&
\t    sc_ready == 2 && sc_finished == 2 &&
\t    sc_result8.hash == MT6797_A72_SC_HASH8_EXPECTED &&
\t    sc_result9.hash == MT6797_A72_SC_HASH9_EXPECTED)
"""
    replace_exact(path, pass_tail, pass_scheduler)
    replace_exact(path, "gemini-a72-pair-v6", "gemini-a72-pair-v7", expected=2)

    old_format = " pl_actual=%016llx\\n\""
    new_format = (
        " pl_actual=%016llx"
        " sc_reported=%d sc_iterations=262144 sc_rescheds=64"
        " sc_expected8=%d sc_start8=%d sc_end8=%d"
        " sc_expected9=%d sc_start9=%d sc_end9=%d"
        " sc_task8=%d sc_task9=%d sc_create8=%d sc_create9=%d"
        " sc_wake8=%d sc_wake9=%d sc_wait8=%d sc_wait9=%d"
        " sc_error8=%d sc_error9=%d sc_stop8=%d sc_stop9=%d"
        " sc_done8=%d sc_done9=%d sc_ready=%d sc_finished=%d"
        " sc_hash8=%016llx sc_hash9=%016llx\\n\""
    )
    replace_exact(path, old_format, new_format, expected=2)

    pass_args = """\t\t\t 0, 0, 0, 0ULL, 0ULL);
"""
    pass_args_new = """\t\t\t 0, 0, 0, 0ULL, 0ULL,
\t\t\t sc_reported,
\t\t\t sc_result8.expected_cpu, sc_result8.start_cpu,
\t\t\t sc_result8.end_cpu, sc_result9.expected_cpu,
\t\t\t sc_result9.start_cpu, sc_result9.end_cpu,
\t\t\t sc_result8.task_context, sc_result9.task_context,
\t\t\t sc_result8.create_error, sc_result9.create_error,
\t\t\t sc_result8.wake_result, sc_result9.wake_result,
\t\t\t sc_result8.wait_complete, sc_result9.wait_complete,
\t\t\t sc_result8.error, sc_result9.error,
\t\t\t sc_result8.stop_result, sc_result9.stop_result,
\t\t\t sc_result8.done, sc_result9.done, sc_ready, sc_finished,
\t\t\t (unsigned long long)sc_result8.hash,
\t\t\t (unsigned long long)sc_result9.hash);
"""
    replace_exact(path, pass_args, pass_args_new)

    fault_args = """\t\t\t (unsigned long long)pl_bad->expected,
\t\t\t (unsigned long long)pl_bad->actual);
"""
    fault_args_new = """\t\t\t (unsigned long long)pl_bad->expected,
\t\t\t (unsigned long long)pl_bad->actual,
\t\t\t sc_reported,
\t\t\t sc_result8.expected_cpu, sc_result8.start_cpu,
\t\t\t sc_result8.end_cpu, sc_result9.expected_cpu,
\t\t\t sc_result9.start_cpu, sc_result9.end_cpu,
\t\t\t sc_result8.task_context, sc_result9.task_context,
\t\t\t sc_result8.create_error, sc_result9.create_error,
\t\t\t sc_result8.wake_result, sc_result9.wake_result,
\t\t\t sc_result8.wait_complete, sc_result9.wait_complete,
\t\t\t sc_result8.error, sc_result9.error,
\t\t\t sc_result8.stop_result, sc_result9.stop_result,
\t\t\t sc_result8.done, sc_result9.done, sc_ready, sc_finished,
\t\t\t (unsigned long long)sc_result8.hash,
\t\t\t (unsigned long long)sc_result9.hash);
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
