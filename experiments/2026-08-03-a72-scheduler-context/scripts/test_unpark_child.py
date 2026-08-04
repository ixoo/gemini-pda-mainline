#!/usr/bin/env python3
"""Validate the exact kthread-unpark child and pinned lifecycle contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import unpark_edits


class ValidationError(RuntimeError):
    pass


TASK_PHASES = (
    "task-ready-before",
    "task-ready-after",
    "task-start-wait-before",
    "task-start-wait-after",
    "task-work-before",
    "task-work-after",
    "task-done-before",
    "task-done-after",
)
PARENT_PHASES = (
    "create8-before",
    "create8-after",
    "create9-before",
    "create9-after",
    "unpark8-before",
    "unpark8-after",
    "unpark9-before",
    "unpark9-after",
    "ready8-wait-before",
    "ready8-wait-after",
    "ready9-wait-before",
    "ready9-wait-after",
    "release-before",
    "release-after",
    "done8-wait-before",
    "done8-wait-after",
    "done9-wait-before",
    "done9-wait-after",
    "stop8-before",
    "stop8-after",
    "stop9-before",
    "stop9-after",
    "run-exit",
)
LEGACY_PHASES = (
    "wake8-before",
    "wake8-after",
    "wake9-before",
    "wake9-after",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_once(text: str, token: str, message: str) -> None:
    require(text.count(token) == 1, message)


def require_order(text: str, tokens: tuple[str, ...], message: str) -> None:
    positions = []
    for token in tokens:
        require_once(text, token, f"{message}: token count changed: {token}")
        positions.append(text.index(token))
    require(positions == sorted(positions), message)


def _matching_delimiter(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    for offset in range(start, len(text)):
        if text[offset] == opening:
            depth += 1
        elif text[offset] == closing:
            depth -= 1
            if depth == 0:
                return offset
    raise ValidationError(f"unterminated {opening}{closing} block")


def extract_function(text: str, name: str) -> str:
    """Extract one C definition by matching its balanced signature and body."""
    definitions = []
    for match in re.finditer(rf"\b{re.escape(name)}\s*\(", text):
        opening_parenthesis = text.index("(", match.start())
        closing_parenthesis = _matching_delimiter(
            text, opening_parenthesis, "(", ")"
        )
        body_start = closing_parenthesis + 1
        while body_start < len(text) and text[body_start].isspace():
            body_start += 1
        if body_start >= len(text) or text[body_start] != "{":
            continue
        body_end = _matching_delimiter(text, body_start, "{", "}")
        line_start = text.rfind("\n", 0, match.start()) + 1
        definitions.append(text[line_start : body_end + 1])
    require(len(definitions) == 1, f"function definition count changed: {name}")
    return definitions[0]


def scheduler_section(psci: str) -> str:
    start = "#define MT6797_A72_SC_ITERATIONS"
    end = "static void mt6797_a72_coh_workfn"
    require(psci.count(start) == 1, "scheduler start boundary changed")
    require(psci.count(end) == 1, "scheduler end boundary changed")
    return psci.split(start, 1)[1].split(end, 1)[0]


def validate_exact_delta(child: str, parent: str) -> None:
    normalized = child
    for name, old, new in reversed(unpark_edits.TRANSFORMATIONS):
        require(parent.count(old) == 1, f"parent anchor changed: {name}")
        require(new not in parent, f"parent already contains child form: {name}")
        require(normalized.count(new) == 1, f"child replacement changed: {name}")
        require(old not in normalized, f"child retains parent form: {name}")
        normalized = normalized.replace(new, old, 1)
    require(normalized == parent, "child has a non-contract source change")


def validate_activation_source(child: str, parent: str) -> None:
    validate_exact_delta(child, parent)
    child_scheduler = scheduler_section(child)
    parent_scheduler = scheduler_section(parent)

    require(
        parent_scheduler.count("kthread_create_on_cpu(") == 2,
        "phase parent create count changed",
    )
    require(
        parent_scheduler.count("wake_up_process(") == 2,
        "phase parent wake count changed",
    )
    require(
        parent_scheduler.count("kthread_unpark(") == 0,
        "phase parent unexpectedly contains unpark",
    )
    require(
        parent_scheduler.count("kthread_stop(") == 2,
        "phase parent stop count changed",
    )

    require(
        child_scheduler.count("kthread_create_on_cpu(") == 2,
        "child create count changed",
    )
    require(
        child_scheduler.count("kthread_unpark(") == 2,
        "child unpark count changed",
    )
    require(
        child_scheduler.count("wake_up_process(") == 0,
        "child scheduler path retains wake_up_process",
    )
    require(
        child_scheduler.count("kthread_stop(") == 2,
        "child stop count changed",
    )

    for cpu in (8, 9):
        require_once(
            child_scheduler,
            f"kthread_unpark(mt6797_a72_sc_task{cpu});",
            f"CPU{cpu} unpark call changed",
        )
        require_once(
            child_scheduler,
            f"mt6797_a72_sc_result{cpu}.unpark_issued = 1;",
            f"CPU{cpu} unpark publication changed",
        )
        require_order(
            child_scheduler,
            (
                f"phase=unpark{cpu}-before\\n",
                f"kthread_unpark(mt6797_a72_sc_task{cpu});",
                f"mt6797_a72_sc_result{cpu}.unpark_issued = 1;",
                f"phase=unpark{cpu}-after\\n",
            ),
            f"CPU{cpu} unpark operation ordering changed",
        )

    require_order(
        child_scheduler,
        (
            "phase=create9-after\\n",
            "phase=unpark8-before\\n",
            "phase=unpark8-after\\n",
            "phase=unpark9-before\\n",
            "phase=unpark9-after\\n",
            "ready_deadline = jiffies",
        ),
        "create/unpark/ready-deadline ordering changed",
    )

    require_once(child, unpark_edits.PASS_GATE_CHILD, "unpark PASS gate changed")
    require_once(
        child,
        unpark_edits.TERMINAL_FIELDS_CHILD,
        "unpark terminal field schema changed",
    )
    require_once(
        child,
        unpark_edits.TERMINAL_ARGS_CHILD,
        "unpark terminal arguments changed",
    )
    require("sc_wake8=" not in child and "sc_wake9=" not in child,
            "child retains legacy wake terminal fields")
    require("wake_result" not in child, "child retains wake_result")

    expected_phases = TASK_PHASES + PARENT_PHASES
    require(
        child.count("gemini-a72-sc-phase") == len(expected_phases),
        "child phase-marker inventory changed",
    )
    for phase in expected_phases:
        require_once(child, f"phase={phase}\\n", f"phase marker changed: {phase}")
    for phase in LEGACY_PHASES:
        require(f"phase={phase}\\n" not in child, f"legacy phase remains: {phase}")


def validate_lifecycle_source(
    kthread_source: str,
    sched_core: str,
    kthread_header: str,
    sched_header: str,
) -> None:
    create = extract_function(kthread_source, "kthread_create_on_cpu")
    require_order(
        create,
        (
            "set_bit(KTHREAD_IS_PER_CPU, &to_kthread(p)->flags);",
            "to_kthread(p)->cpu = cpu;",
            "kthread_park(p);\n\treturn p;",
        ),
        "create-on-CPU park contract changed",
    )

    parkme = extract_function(kthread_source, "__kthread_parkme")
    require(
        parkme.count("__set_current_state(TASK_PARKED);") == 2,
        "park loop TASK_PARKED state count changed",
    )
    require_order(
        parkme,
        (
            "while (test_bit(KTHREAD_SHOULD_PARK, &self->flags))",
            "schedule();",
            "clear_bit(KTHREAD_IS_PARKED, &self->flags);",
            "__set_current_state(TASK_RUNNING);",
        ),
        "park loop state ordering changed",
    )

    internal_unpark = extract_function(kthread_source, "__kthread_unpark")
    require_order(
        internal_unpark,
        (
            "clear_bit(KTHREAD_SHOULD_PARK, &kthread->flags);",
            "test_and_clear_bit(KTHREAD_IS_PARKED, &kthread->flags)",
            "test_bit(KTHREAD_IS_PER_CPU, &kthread->flags)",
            "__kthread_bind(k, kthread->cpu, TASK_PARKED);",
            "wake_up_state(k, TASK_PARKED);",
        ),
        "internal unpark contract changed",
    )

    public_unpark = extract_function(kthread_source, "kthread_unpark")
    require_order(
        public_unpark,
        (
            "struct kthread *kthread = to_live_kthread(k);",
            "if (kthread)",
            "__kthread_unpark(k, kthread);",
        ),
        "public unpark contract changed",
    )

    stop = extract_function(kthread_source, "kthread_stop")
    require_order(
        stop,
        (
            "set_bit(KTHREAD_SHOULD_STOP, &kthread->flags);",
            "__kthread_unpark(k, kthread);",
            "wake_up_process(k);",
            "wait_for_completion(&kthread->exited);",
        ),
        "stop cleanup-unpark contract changed",
    )

    wake = extract_function(sched_core, "wake_up_process")
    require_once(
        wake,
        "return try_to_wake_up(p, TASK_NORMAL, 0);",
        "wake_up_process state mask changed",
    )
    require("TASK_PARKED" not in wake, "wake_up_process includes TASK_PARKED")

    require_once(
        kthread_header,
        "void kthread_unpark(struct task_struct *k);",
        "kthread_unpark declaration changed",
    )
    require_once(
        sched_header,
        "#define TASK_PARKED\t\t512",
        "TASK_PARKED definition changed",
    )
    require_once(
        sched_header,
        "#define TASK_NORMAL\t\t(TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE)",
        "TASK_NORMAL definition changed",
    )


def validate_contract(
    child: str,
    parent: str,
    kthread_source: str,
    sched_core: str,
    kthread_header: str,
    sched_header: str,
) -> None:
    validate_activation_source(child, parent)
    validate_lifecycle_source(
        kthread_source, sched_core, kthread_header, sched_header
    )


def mutation_cases() -> tuple[tuple[str, str, str, str], ...]:
    public_unpark = (
        "\tif (kthread)\n"
        "\t\t__kthread_unpark(k, kthread);\n"
    )
    stop_unpark = (
        "\t\tset_bit(KTHREAD_SHOULD_STOP, &kthread->flags);\n"
        "\t\t__kthread_unpark(k, kthread);\n"
    )
    return (
        (
            "missing-unpark9",
            "child",
            "\tkthread_unpark(mt6797_a72_sc_task9);\n",
            "",
        ),
        (
            "wrong-unpark9-target",
            "child",
            "kthread_unpark(mt6797_a72_sc_task9);",
            "kthread_unpark(mt6797_a72_sc_task8);",
        ),
        (
            "restored-wake-api",
            "child",
            "kthread_unpark(mt6797_a72_sc_task9);",
            "wake_up_process(mt6797_a72_sc_task9);",
        ),
        (
            "missing-unpark9-publication",
            "child",
            "\tmt6797_a72_sc_result9.unpark_issued = 1;\n",
            "",
        ),
        (
            "publication-before-call",
            "child",
            "\tkthread_unpark(mt6797_a72_sc_task8);\n"
            "\tmt6797_a72_sc_result8.unpark_issued = 1;\n",
            "\tmt6797_a72_sc_result8.unpark_issued = 1;\n"
            "\tkthread_unpark(mt6797_a72_sc_task8);\n",
        ),
        (
            "missing-terminal-unpark9-gate",
            "child",
            "result9->unpark_issued == 1 && result8->ready_complete == 1",
            "result8->ready_complete == 1",
        ),
        (
            "legacy-terminal-schema",
            "child",
            "sc_unpark8=%d sc_unpark9=%d",
            "sc_unpark8=%d sc_wake9=%d",
        ),
        (
            "legacy-phase-schema",
            "child",
            "phase=unpark9-before\\n",
            "phase=wake9-before\\n",
        ),
        (
            "create-park-missing",
            "kthread",
            "\tkthread_park(p);\n",
            "",
        ),
        (
            "parked-state-missing",
            "kthread",
            "\t\tschedule();\n\t\t__set_current_state(TASK_PARKED);\n",
            "\t\tschedule();\n\t\t__set_current_state(TASK_RUNNING);\n",
        ),
        (
            "should-park-clear-missing",
            "kthread",
            "\tclear_bit(KTHREAD_SHOULD_PARK, &kthread->flags);\n",
            "",
        ),
        (
            "is-parked-test-clear-missing",
            "kthread",
            "test_and_clear_bit(KTHREAD_IS_PARKED, &kthread->flags)",
            "test_bit(KTHREAD_IS_PARKED, &kthread->flags)",
        ),
        (
            "unpark-bind-state-changed",
            "kthread",
            "__kthread_bind(k, kthread->cpu, TASK_PARKED);",
            "__kthread_bind(k, kthread->cpu, TASK_UNINTERRUPTIBLE);",
        ),
        (
            "unpark-wake-state-changed",
            "kthread",
            "wake_up_state(k, TASK_PARKED);",
            "wake_up_state(k, TASK_NORMAL);",
        ),
        (
            "public-unpark-call-missing",
            "kthread",
            public_unpark,
            "\tif (kthread)\n\t\treturn;\n",
        ),
        (
            "stop-cleanup-unpark-missing",
            "kthread",
            stop_unpark,
            "\t\tset_bit(KTHREAD_SHOULD_STOP, &kthread->flags);\n",
        ),
        (
            "wake-mask-changed",
            "sched_core",
            "return try_to_wake_up(p, TASK_NORMAL, 0);",
            "return try_to_wake_up(p, TASK_PARKED, 0);",
        ),
        (
            "unpark-declaration-missing",
            "kthread_header",
            "void kthread_unpark(struct task_struct *k);\n",
            "",
        ),
        (
            "task-parked-value-changed",
            "sched_header",
            "#define TASK_PARKED\t\t512",
            "#define TASK_PARKED\t\t511",
        ),
        (
            "task-normal-includes-parked",
            "sched_header",
            "#define TASK_NORMAL\t\t(TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE)",
            "#define TASK_NORMAL\t\t(TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE | TASK_PARKED)",
        ),
    )


def validate_mutations(inputs: dict[str, str]) -> int:
    rejected = 0
    for name, target, old, new in mutation_cases():
        require(
            inputs[target].count(old) == 1,
            f"mutation anchor count changed: {name}",
        )
        mutated = dict(inputs)
        mutated[target] = mutated[target].replace(old, new, 1)
        try:
            validate_contract(
                mutated["child"],
                mutated["parent"],
                mutated["kthread"],
                mutated["sched_core"],
                mutated["kthread_header"],
                mutated["sched_header"],
            )
        except ValidationError:
            rejected += 1
            continue
        raise ValidationError(f"mutation was not rejected: {name}")
    return rejected


def fixture_parent_psci() -> str:
    task_markers = "".join(
        f'\tpr_emerg("gemini-a72-sc-phase cpu=%d phase={phase}\\n", cpu);\n'
        for phase in TASK_PHASES
    )
    parent_tail = (
        '\tpr_emerg("gemini-a72-sc-phase phase=ready8-wait-before\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=ready8-wait-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=ready9-wait-before\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=ready9-wait-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=release-before\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=release-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=done8-wait-before\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=done8-wait-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=done9-wait-before\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=done9-wait-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=stop8-before\\n");\n'
        "\tkthread_stop(mt6797_a72_sc_task8);\n"
        '\tpr_emerg("gemini-a72-sc-phase phase=stop8-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=stop9-before\\n");\n'
        "\tkthread_stop(mt6797_a72_sc_task9);\n"
        '\tpr_emerg("gemini-a72-sc-phase phase=stop9-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=run-exit\\n");\n'
    )
    return (
        "#define MT6797_A72_SC_ITERATIONS 262144\n"
        "struct mt6797_a72_sc_result {\n"
        f"{unpark_edits.FIELD_PARENT}"
        "\tint create_error;\n\tint ready_complete;\n};\n"
        "static int mt6797_a72_sc_thread(void *data)\n{\n"
        "\tint cpu = 8;\n"
        f"{task_markers}"
        "\treturn 0;\n}\n"
        "static void mt6797_a72_sc_run(void)\n{\n"
        "\tunsigned long ready_deadline;\n"
        '\tpr_emerg("gemini-a72-sc-phase phase=create8-before\\n");\n'
        "\tmt6797_a72_sc_task8 = kthread_create_on_cpu(mt6797_a72_sc_thread,\n"
        "\t\t\t&mt6797_a72_sc_result8, 8, \"gemini-a72-sc/%u\");\n"
        '\tpr_emerg("gemini-a72-sc-phase phase=create8-after\\n");\n'
        '\tpr_emerg("gemini-a72-sc-phase phase=create9-before\\n");\n'
        "\tmt6797_a72_sc_task9 = kthread_create_on_cpu(mt6797_a72_sc_thread,\n"
        "\t\t\t&mt6797_a72_sc_result9, 9, \"gemini-a72-sc/%u\");\n"
        '\tpr_emerg("gemini-a72-sc-phase phase=create9-after\\n");\n'
        f"{unpark_edits.ACTIVATE8_PARENT}"
        f"{unpark_edits.ACTIVATE9_PARENT}"
        "\tready_deadline = jiffies + 1;\n"
        f"{parent_tail}"
        "}\n"
        "static void mt6797_a72_coh_workfn(struct work_struct *work)\n{\n}\n"
        "static noinline void mt6797_a72_sc_terminal(bool parent_pass)\n{\n"
        "\tpassed = parent_pass && !result8->create_error &&\n"
        f"{unpark_edits.PASS_GATE_PARENT}"
        "\t\t result9->ready_complete == 1;\n"
        f'\tpr_emerg("gemini-a72-pair-v7 result=%s {unpark_edits.TERMINAL_FIELDS_PARENT}\\n",\n'
        f"{unpark_edits.TERMINAL_ARGS_PARENT}"
        "\t\t passed ? \"pass\" : \"fault\");\n"
        "}\n"
    )


KTHREAD_FIXTURE = r"""
static void __kthread_parkme(struct kthread *self)
{
	__set_current_state(TASK_PARKED);
	while (test_bit(KTHREAD_SHOULD_PARK, &self->flags)) {
		schedule();
		__set_current_state(TASK_PARKED);
	}
	clear_bit(KTHREAD_IS_PARKED, &self->flags);
	__set_current_state(TASK_RUNNING);
}

struct task_struct *kthread_create_on_cpu(int (*threadfn)(void *data),
					  void *data, unsigned int cpu,
					  const char *namefmt)
{
	struct task_struct *p;

	set_bit(KTHREAD_IS_PER_CPU, &to_kthread(p)->flags);
	to_kthread(p)->cpu = cpu;
	kthread_park(p);
	return p;
}

static void __kthread_unpark(struct task_struct *k, struct kthread *kthread)
{
	clear_bit(KTHREAD_SHOULD_PARK, &kthread->flags);
	if (test_and_clear_bit(KTHREAD_IS_PARKED, &kthread->flags)) {
		if (test_bit(KTHREAD_IS_PER_CPU, &kthread->flags))
			__kthread_bind(k, kthread->cpu, TASK_PARKED);
		wake_up_state(k, TASK_PARKED);
	}
}

void kthread_unpark(struct task_struct *k)
{
	struct kthread *kthread = to_live_kthread(k);

	if (kthread)
		__kthread_unpark(k, kthread);
}

int kthread_stop(struct task_struct *k)
{
	struct kthread *kthread = to_live_kthread(k);

	if (kthread) {
		set_bit(KTHREAD_SHOULD_STOP, &kthread->flags);
		__kthread_unpark(k, kthread);
		wake_up_process(k);
		wait_for_completion(&kthread->exited);
	}
	return 0;
}
"""

SCHED_CORE_FIXTURE = r"""
int wake_up_process(struct task_struct *p)
{
	WARN_ON(task_is_stopped_or_traced(p));
	return try_to_wake_up(p, TASK_NORMAL, 0);
}
"""

KTHREAD_HEADER_FIXTURE = "void kthread_unpark(struct task_struct *k);\n"
SCHED_HEADER_FIXTURE = (
    "#define TASK_PARKED\t\t512\n"
    "#define TASK_NORMAL\t\t(TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE)\n"
)


def self_test_inputs() -> dict[str, str]:
    parent = fixture_parent_psci()
    child = unpark_edits.transform_text(parent)
    return {
        "child": child,
        "parent": parent,
        "kthread": KTHREAD_FIXTURE,
        "sched_core": SCHED_CORE_FIXTURE,
        "kthread_header": KTHREAD_HEADER_FIXTURE,
        "sched_header": SCHED_HEADER_FIXTURE,
    }


def source_inputs(source: Path, parent_psci: Path) -> dict[str, str]:
    def read(relative: str) -> str:
        return (source / relative).read_text(encoding="utf-8")

    return {
        "child": read("arch/arm64/kernel/psci.c"),
        "parent": parent_psci.read_text(encoding="utf-8"),
        "kthread": read("kernel/kthread.c"),
        "sched_core": read("kernel/sched/core.c"),
        "kthread_header": read("include/linux/kthread.h"),
        "sched_header": read("include/linux/sched.h"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--parent-psci", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        require(
            args.source is None and args.parent_psci is None,
            "--self-test cannot be combined with source arguments",
        )
        inputs = self_test_inputs()
        fixture = "finite-in-memory"
    else:
        require(
            args.source is not None and args.parent_psci is not None,
            "--source and --parent-psci are required",
        )
        inputs = source_inputs(args.source, args.parent_psci)
        fixture = "pinned-source"

    validate_contract(
        inputs["child"],
        inputs["parent"],
        inputs["kthread"],
        inputs["sched_core"],
        inputs["kthread_header"],
        inputs["sched_header"],
    )
    rejected = validate_mutations(inputs)
    print("validation=a72-scheduler-unpark-source")
    print(f"fixture={fixture}")
    print("exact_parent_equivalence=passed")
    print("lifecycle_source_contract=passed")
    print(f"mutations={rejected}-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValidationError, unpark_edits.EditError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
