#!/usr/bin/env python3
"""Add decision-changing phase markers to the exact rejected start-gate child."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise EditError(f"{path}: expected one marker anchor, found {count}")
    path.write_text(text.replace(old, new))


def mark(
    path: Path,
    anchor: str,
    phase: str,
    before: bool = True,
    indent: str = "\t",
) -> None:
    marker = f'{indent}pr_emerg("gemini-a72-sc-phase phase={phase}\\n");\n'
    replace_exact(path, anchor, marker + anchor if before else anchor + marker)


def task_mark(path: Path, anchor: str, phase: str, before: bool = True) -> None:
    marker = (
        f'\tpr_emerg("gemini-a72-sc-phase cpu=%d phase={phase}\\n", '
        "result->expected_cpu);\n"
    )
    replace_exact(path, anchor, marker + anchor if before else anchor + marker)


def edit(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"

    task_mark(path, "\tatomic_inc(&mt6797_a72_sc_ready);\n", "task-ready-before")
    task_mark(path, "\tcomplete(ready);\n", "task-ready-after", before=False)
    task_mark(
        path,
        "\tresult->start_complete = !!wait_for_completion_timeout(\n",
        "task-start-wait-before",
    )
    task_mark(
        path,
        "\t\tmsecs_to_jiffies(MT6797_A72_SC_READY_TIMEOUT_MS));\n",
        "task-start-wait-after",
        before=False,
    )
    task_mark(
        path,
        "\tif (!error) {\n\t\tfor (iteration = 0; iteration < MT6797_A72_SC_ITERATIONS;\n",
        "task-work-before",
    )
    task_mark(
        path,
        "\tresult->hash = hash;\n",
        "task-work-after",
    )
    task_mark(path, "\tcomplete(done);\n", "task-done-before")
    task_mark(
        path,
        "\treturn error;\n}\n\nstatic bool mt6797_a72_sc_wait_until",
        "task-done-after",
    )

    mark(path, "\tmt6797_a72_sc_task8 = kthread_create_on_cpu(\n", "create8-before")
    mark(path, "\tmt6797_a72_sc_task9 = kthread_create_on_cpu(\n", "create9-before")
    mark(path, "\tif (IS_ERR(mt6797_a72_sc_task8)) {\n", "create8-after")
    mark(path, "\tif (IS_ERR(mt6797_a72_sc_task9)) {\n", "create9-after")
    mark(path, "\tmt6797_a72_sc_result8.wake_result =\n", "wake8-before")
    mark(path, "\tmt6797_a72_sc_result9.wake_result =\n", "wake9-before")
    mark(
        path,
        "\t\twake_up_process(mt6797_a72_sc_task8);\n",
        "wake8-after",
        before=False,
    )
    mark(
        path,
        "\t\twake_up_process(mt6797_a72_sc_task9);\n",
        "wake9-after",
        before=False,
    )
    mark(path, "\tmt6797_a72_sc_result8.ready_complete =\n", "ready8-wait-before")
    mark(path, "\tmt6797_a72_sc_result9.ready_complete =\n", "ready9-wait-before")
    mark(
        path,
        "\t\tmt6797_a72_sc_wait_until(&mt6797_a72_sc_ready8, ready_deadline);\n",
        "ready8-wait-after",
        before=False,
    )
    mark(
        path,
        "\t\tmt6797_a72_sc_wait_until(&mt6797_a72_sc_ready9, ready_deadline);\n",
        "ready9-wait-after",
        before=False,
    )
    mark(path, "\tcomplete_all(&mt6797_a72_sc_start);\n", "release-before")
    mark(path, "\tcomplete_all(&mt6797_a72_sc_start);\n", "release-after", before=False)
    mark(path, "\tmt6797_a72_sc_result8.wait_complete =\n", "done8-wait-before")
    mark(path, "\tmt6797_a72_sc_result9.wait_complete =\n", "done9-wait-before")
    mark(
        path,
        "\t\tmt6797_a72_sc_wait_until(&mt6797_a72_sc_done8, done_deadline);\n",
        "done8-wait-after",
        before=False,
    )
    mark(
        path,
        "\t\tmt6797_a72_sc_wait_until(&mt6797_a72_sc_done9, done_deadline);\n",
        "done9-wait-after",
        before=False,
    )
    mark(path, "\t\tmt6797_a72_sc_result8.stop_result =\n", "stop8-before", indent="\t\t")
    mark(path, "\t\tmt6797_a72_sc_result9.stop_result =\n", "stop9-before", indent="\t\t")
    mark(
        path,
        "\t\t\tkthread_stop(mt6797_a72_sc_task8);\n",
        "stop8-after",
        before=False,
        indent="\t\t",
    )
    mark(
        path,
        "\t\t\tkthread_stop(mt6797_a72_sc_task9);\n",
        "stop9-after",
        before=False,
        indent="\t\t",
    )
    mark(path, "\tsmp_wmb();\n\tatomic_set(&mt6797_a72_sc_reported, 1);\n", "run-exit")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    edit(args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
