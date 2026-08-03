#!/usr/bin/env python3
"""Apply the late CPU8 sample to the exact held-online parent."""

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


def late_probe(source: Path) -> None:
    psci = source / "arch/arm64/kernel/psci.c"
    old = '''\tret = smp_call_function_single(8, mt6797_a72_hold_ipi,
\t\t\t\t       &observed_cpu, 1);
\tif (ret || observed_cpu != 8 || !cpu_online(8) || cpu_online(9)) {
\t\tpr_emerg("gemini-a72-hold-v1 result=fault sample=%d cpu=%d cpu8=%d cpu9=%d error=%d\\n",
\t\t\t sample, observed_cpu, cpu_online(8), cpu_online(9), ret);
\t\tconsole_lock();
\t\tconsole_unlock();
\t\treturn;
\t}
\tatomic_inc(&mt6797_a72_hold_hits);
\tif (sample == 1) {
\t\tpr_emerg("gemini-a72-hold-v1 result=sample sample=1 cpu=8 cpu8=1 cpu9=0 online=%u\\n",
\t\t\t num_online_cpus());
\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t\t   msecs_to_jiffies(5000))) {
\t\t\tpr_emerg("gemini-a72-hold-v1 result=fault sample=2 cpu=-1 cpu8=%d cpu9=%d error=%d\\n",
\t\t\t\t cpu_online(8), cpu_online(9), -EBUSY);
\t\t\tconsole_lock();
\t\t\tconsole_unlock();
\t\t}
\t\treturn;
\t}
\tpr_emerg("gemini-a72-hold-v1 result=pass sample=2 cpu=8 cpu8=1 cpu9=0\\n");
\tconsole_lock();
\tconsole_unlock();
'''
    new = '''\tret = smp_call_function_single(8, mt6797_a72_hold_ipi,
\t\t\t\t       &observed_cpu, 1);
\tif (ret || observed_cpu != 8 || !cpu_online(8) || cpu_online(9)) {
\t\tpr_emerg("gemini-a72-hold-v2 result=fault sample=%d cpu=%d cpu8=%d cpu9=%d hits=%d error=%d\\n",
\t\t\t sample, observed_cpu, cpu_online(8), cpu_online(9),
\t\t\t atomic_read(&mt6797_a72_hold_hits), ret);
\t\tconsole_lock();
\t\tconsole_unlock();
\t\treturn;
\t}
\tatomic_inc(&mt6797_a72_hold_hits);
\tif (sample < 3) {
\t\tunsigned long delay = sample == 1 ? 5000 : 4000;

\t\tpr_emerg("gemini-a72-hold-v2 result=sample sample=%d cpu=8 cpu8=1 cpu9=0 hits=%d online=%u\\n",
\t\t\t sample, atomic_read(&mt6797_a72_hold_hits),
\t\t\t num_online_cpus());
\t\tconsole_lock();
\t\tconsole_unlock();
\t\tif (!schedule_delayed_work(&mt6797_a72_hold_work,
\t\t\t\t\t   msecs_to_jiffies(delay))) {
\t\t\tpr_emerg("gemini-a72-hold-v2 result=fault sample=%d cpu=-1 cpu8=%d cpu9=%d hits=%d error=%d\\n",
\t\t\t\t sample + 1, cpu_online(8), cpu_online(9),
\t\t\t\t atomic_read(&mt6797_a72_hold_hits), -EBUSY);
\t\t\tconsole_lock();
\t\t\tconsole_unlock();
\t\t}
\t\treturn;
\t}
\tpr_emerg("gemini-a72-hold-v2 result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3\\n");
\tconsole_lock();
\tconsole_unlock();
'''
    replace_once(psci, old, new)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / ".git").exists():
        raise EditError(f"not a Git source tree: {source}")
    late_probe(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
