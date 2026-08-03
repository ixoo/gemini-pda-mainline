#!/usr/bin/env python3
"""Apply deterministic bounded-coherency edits to the exact terminal parent."""

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
    anchor = """#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
extern void mt6797_a72_hps_down_snapshot(int *reported, int *cpu, int *error,
\t\t\t\t\t int *count);
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    replacement = """#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE
extern void mt6797_a72_hps_down_snapshot(int *reported, int *cpu, int *error,
\t\t\t\t\t int *count);

#define MT6797_A72_COH_ROUNDS 1024
#define MT6797_A72_COH_SPIN_BUDGET (1U << 24)

static atomic_t mt6797_a72_coh_reported = ATOMIC_INIT(0);
static atomic_t mt6797_a72_coh_rounds = ATOMIC_INIT(0);
static atomic_t mt6797_a72_coh_cpu8 = ATOMIC_INIT(-1);
static atomic_t mt6797_a72_coh_cpu9 = ATOMIC_INIT(-1);
static atomic_t mt6797_a72_coh_error8 = ATOMIC_INIT(0);
static atomic_t mt6797_a72_coh_error9 = ATOMIC_INIT(0);
static atomic_t mt6797_a72_coh_final_seq8 = ATOMIC_INIT(0);
static atomic_t mt6797_a72_coh_final_seq9 = ATOMIC_INIT(0);
static int mt6797_a72_coh_turn;
static int mt6797_a72_coh_seq8;
static int mt6797_a72_coh_seq9;

static int mt6797_a72_coh_wait_turn(int expected, unsigned int *budget)
{
\twhile (READ_ONCE(mt6797_a72_coh_turn) != expected) {
\t\tif (!(*budget)--)
\t\t\treturn -ETIMEDOUT;
\t\tcpu_relax();
\t}
\tsmp_rmb();
\treturn 0;
}

static void mt6797_a72_coh_ipi(void *unused)
{
\tunsigned int budget = MT6797_A72_COH_SPIN_BUDGET;
\tint cpu = smp_processor_id();
\tint error = 0;
\tint round;

\tif (cpu == 8) {
\t\tatomic_set(&mt6797_a72_coh_cpu8, cpu);
\t\tfor (round = 1; round <= MT6797_A72_COH_ROUNDS; round++) {
\t\t\terror = mt6797_a72_coh_wait_turn(8, &budget);
\t\t\tif (error)
\t\t\t\tbreak;
\t\t\tif (round > 1 && READ_ONCE(mt6797_a72_coh_seq9) != round - 1) {
\t\t\t\terror = -EIO;
\t\t\t\tbreak;
\t\t\t}
\t\t\tWRITE_ONCE(mt6797_a72_coh_seq8, round);
\t\t\tsmp_wmb();
\t\t\tWRITE_ONCE(mt6797_a72_coh_turn, 9);
\t\t}
\t\tif (!error) {
\t\t\terror = mt6797_a72_coh_wait_turn(8, &budget);
\t\t\tif (!error && READ_ONCE(mt6797_a72_coh_seq9) !=
\t\t\t    MT6797_A72_COH_ROUNDS)
\t\t\t\terror = -EIO;
\t\t}
\t\tatomic_set(&mt6797_a72_coh_error8, error);
\t} else if (cpu == 9) {
\t\tatomic_set(&mt6797_a72_coh_cpu9, cpu);
\t\tfor (round = 1; round <= MT6797_A72_COH_ROUNDS; round++) {
\t\t\terror = mt6797_a72_coh_wait_turn(9, &budget);
\t\t\tif (error)
\t\t\t\tbreak;
\t\t\tif (READ_ONCE(mt6797_a72_coh_seq8) != round) {
\t\t\t\terror = -EIO;
\t\t\t\tbreak;
\t\t\t}
\t\t\tWRITE_ONCE(mt6797_a72_coh_seq9, round);
\t\t\tsmp_wmb();
\t\t\tWRITE_ONCE(mt6797_a72_coh_turn, 8);
\t\t}
\t\tatomic_set(&mt6797_a72_coh_error9, error);
\t}
}

static void mt6797_a72_coh_workfn(struct work_struct *work)
{
\tcpumask_t targets;

\tatomic_set(&mt6797_a72_coh_reported, -1);
\tatomic_set(&mt6797_a72_coh_rounds, 0);
\tatomic_set(&mt6797_a72_coh_cpu8, -1);
\tatomic_set(&mt6797_a72_coh_cpu9, -1);
\tatomic_set(&mt6797_a72_coh_error8, 0);
\tatomic_set(&mt6797_a72_coh_error9, 0);
\tWRITE_ONCE(mt6797_a72_coh_seq8, 0);
\tWRITE_ONCE(mt6797_a72_coh_seq9, 0);
\tWRITE_ONCE(mt6797_a72_coh_turn, 8);
\tsmp_wmb();
\tif (smp_processor_id() != 0) {
\t\tatomic_set(&mt6797_a72_coh_error8, -EXDEV);
\t\tatomic_set(&mt6797_a72_coh_error9, -EXDEV);
\t\tgoto publish;
\t}
\tcpumask_clear(&targets);
\tcpumask_set_cpu(8, &targets);
\tcpumask_set_cpu(9, &targets);
\tsmp_call_function_many(&targets, mt6797_a72_coh_ipi, NULL, true);
\tatomic_set(&mt6797_a72_coh_rounds, MT6797_A72_COH_ROUNDS);
publish:
\tatomic_set(&mt6797_a72_coh_final_seq8,
\t\t   READ_ONCE(mt6797_a72_coh_seq8));
\tatomic_set(&mt6797_a72_coh_final_seq9,
\t\t   READ_ONCE(mt6797_a72_coh_seq9));
\tsmp_wmb();
\tatomic_set(&mt6797_a72_coh_reported, 1);
}

static DECLARE_WORK(mt6797_a72_coh_work, mt6797_a72_coh_workfn);

static void mt6797_a72_coh_schedule(void)
{
\tif (!schedule_work_on(0, &mt6797_a72_coh_work)) {
\t\tatomic_set(&mt6797_a72_coh_error8, -EBUSY);
\t\tatomic_set(&mt6797_a72_coh_error9, -EBUSY);
\t\tsmp_wmb();
\t\tatomic_set(&mt6797_a72_coh_reported, 2);
\t}
}

static void mt6797_a72_coh_snapshot(int *reported, int *rounds,
\t\t\t\t    int *cpu8, int *cpu9,
\t\t\t\t    int *error8, int *error9,
\t\t\t\t    int *seq8, int *seq9)
{
\t*reported = atomic_read(&mt6797_a72_coh_reported);
\tsmp_rmb();
\t*rounds = atomic_read(&mt6797_a72_coh_rounds);
\t*cpu8 = atomic_read(&mt6797_a72_coh_cpu8);
\t*cpu9 = atomic_read(&mt6797_a72_coh_cpu9);
\t*error8 = atomic_read(&mt6797_a72_coh_error8);
\t*error9 = atomic_read(&mt6797_a72_coh_error9);
\t*seq8 = atomic_read(&mt6797_a72_coh_final_seq8);
\t*seq9 = atomic_read(&mt6797_a72_coh_final_seq9);
}
#endif

static void mt6797_a72_hold_workfn(struct work_struct *work)
"""
    replace_once(path, anchor, replacement)

    old = """\tint hps_count;
\tint observed_cpu8 = -1;
"""
    new = """\tint hps_count;
\tint coh_reported;
\tint coh_rounds;
\tint coh_cpu8;
\tint coh_cpu9;
\tint coh_error8;
\tint coh_error9;
\tint coh_seq8;
\tint coh_seq9;
\tint observed_cpu8 = -1;
"""
    replace_once(path, old, new)

    old = """\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
"""
    new = """\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (sample == 2)
\t\t\tmt6797_a72_coh_schedule();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
"""
    replace_once(path, old, new)

    old = """\tmt6797_a72_hps_down_snapshot(&hps_reported, &hps_cpu,
\t\t\t\t      &hps_error, &hps_count);
\tpr_emerg("gemini-a72-pair-v3 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d\\n",
\t\t hps_reported, hps_cpu, hps_error, hps_count);
"""
    new = """\tmt6797_a72_hps_down_snapshot(&hps_reported, &hps_cpu,
\t\t\t\t      &hps_error, &hps_count);
\tmt6797_a72_coh_snapshot(&coh_reported, &coh_rounds,
\t\t\t\t &coh_cpu8, &coh_cpu9,
\t\t\t\t &coh_error8, &coh_error9,
\t\t\t\t &coh_seq8, &coh_seq9);
\tif (coh_reported == 1 && coh_rounds == MT6797_A72_COH_ROUNDS &&
\t    coh_cpu8 == 8 && coh_cpu9 == 9 && !coh_error8 && !coh_error9 &&
\t    coh_seq8 == MT6797_A72_COH_ROUNDS &&
\t    coh_seq9 == MT6797_A72_COH_ROUNDS)
\t\tpr_emerg("gemini-a72-pair-v4 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d\\n",
\t\t\t hps_reported, hps_cpu, hps_error, hps_count,
\t\t\t coh_reported, coh_rounds, coh_cpu8, coh_cpu9,
\t\t\t coh_error8, coh_error9, coh_seq8, coh_seq9);
\telse
\t\tpr_emerg("gemini-a72-pair-v4 result=fault sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3 hps_reported=%d hps_cpu=%d hps_error=%d hps_count=%d coh_reported=%d coh_rounds=%d coh_cpu8=%d coh_cpu9=%d coh_error8=%d coh_error9=%d coh_seq8=%d coh_seq9=%d\\n",
\t\t\t hps_reported, hps_cpu, hps_error, hps_count,
\t\t\t coh_reported, coh_rounds, coh_cpu8, coh_cpu9,
\t\t\t coh_error8, coh_error9, coh_seq8, coh_seq9);
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
