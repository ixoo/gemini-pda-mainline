#!/usr/bin/env python3
"""Require unsafe retained-CPU8 observer mutations to fail closed."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


MUTATIONS = (
    ("internal", "OBSERVER_CPU 8U", "OBSERVER_CPU 7U"),
    ("internal", "OBSERVER_TIMEOUT_MS 250U", "OBSERVER_TIMEOUT_MS 500U"),
    ("internal", "struct completion completion;", "struct completion *completion;"),
    ("source", "if (wait)", "if (false)"),
    (
        "source",
        "smp_call_function_single(cpu, function, info, 0)",
        "smp_call_function_single(cpu, function, info, 1)",
    ),
    (
        "source",
        "wait_for_completion_timeout(completion, timeout)",
        "wait_for_completion(completion)",
    ),
    (
        "source",
        "snapshot->phase == MT6797_A72_HOTPLUG_OFF_COMMITTED",
        "snapshot->phase == MT6797_A72_HOTPLUG_OFF_PROVEN",
    ),
    (
        "source",
        "snapshot->controller_present == 1",
        "snapshot->controller_present <= 1",
    ),
    (
        "source",
        "!memcmp(&active->identity, identity, sizeof(*identity))",
        "active->identity.cookie == identity->cookie",
    ),
    ("source", "active->off_committed == 1", "active->off_committed <= 1"),
    ("source", "!active->off_proven", "active->off_proven <= 1"),
    (
        "source",
        "observer->ops->current_cpu(observer->ops_context) !=",
        "observer->ops->current_cpu(observer->ops_context) ==",
    ),
    (
        "source",
        "observer->ops->identity_check(observer->ops_context,",
        "cpu8_observer_test_identity(observer->ops_context,",
    ),
    (
        "source",
        "MT6797_A72_CPU8_OBSERVER_IDLE)\n",
        "MT6797_A72_CPU8_OBSERVER_ARMED)\n",
    ),
    (
        "source",
        "false);",
        "true);",
    ),
    (
        "source",
        "MT6797_A72_CPU8_OBSERVER_TIMED_OUT) ==",
        "MT6797_A72_CPU8_OBSERVER_SUCCEEDED) ==",
    ),
    ("test", "KUNIT_CASE(cpu8_observer_cpu_refusal_test),", ""),
    ("test", "KUNIT_CASE(cpu8_observer_timeout_late_callback_test),", ""),
    ("test", "KUNIT_CASE(cpu8_observer_one_shot_test),", ""),
    (
        "kconfig",
        "depends on SMP\n\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR",
        "depends on MTK_MT6797_A72_HOTPLUG_EXECUTOR",
    ),
    (
        "makefile",
        "mt6797-a72-cpu8-observer-test.o",
        "mt6797-a72-cpu8-observer.o",
    ),
)


FILES = {
    "internal": "drivers/soc/mediatek/mt6797-a72-cpu8-observer-internal.h",
    "source": "drivers/soc/mediatek/mt6797-a72-cpu8-observer.c",
    "test": "drivers/soc/mediatek/mt6797-a72-cpu8-observer-test.c",
    "kconfig": "drivers/soc/mediatek/Kconfig",
    "makefile": "drivers/soc/mediatek/Makefile",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = Path(__file__).resolve().parent / "validate_cpu8_observer_source.py"
    rejected = 0
    for index, (label, old, new) in enumerate(MUTATIONS, start=1):
        with tempfile.TemporaryDirectory(
            prefix=f"cpu8-observer-mutation-{index}-"
        ) as name:
            root = Path(name)
            for relative in FILES.values():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            path = root / FILES[label]
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {old}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(validator), "--source-root", str(root)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if completed.returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {index}:{label}")
            rejected += 1
    print("cpu8_observer_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
