#!/usr/bin/env python3
"""Apply the exact A72 effect-plan stage-ledger diagnostic."""

from __future__ import annotations

import hashlib
from pathlib import Path


MT_TARGET = Path("arch/arm64/kernel/mt6797_psci.c")
CORE_TARGET = Path("arch/arm64/kernel/cpufeature.c")
PARENT_SHA256 = {
    MT_TARGET: "395d216791ca6fd02488a4dde2da4b66350bbb67dee431566d9b048c44366716",
    CORE_TARGET: "ff82c04592982358c890221be228ceef6e1627c7b9cf754088653a940c7affe4",
}

MT_START = "static int __init\nmt6797_a72_derive_effects("
MT_END = "\nstatic bool __init\nmt6797_a72_identity_empty("
CORE_START = "int __init arm64_plan_late_cpu_effects("
CORE_END = "\n#endif\n\n#define HWCAP_CPUID_MATCH"

MT_HELPER = '''static int __init
mt6797_a72_effect_diagnostic(const char *stage, int target, int ret)
{
\tpr_info("A72_EFFECT_DERIVE_V1 stage=%s target=%d ret=%d\\n",
\t\tstage, target, ret);
\treturn ret;
}

'''

MT_REPLACEMENTS = (
    (
        '''\tif (!plan || !effects || plan->abi != ARM64_LATE_CPU_PLAN_ABI ||
\t    !plan->local_caps_planned || plan->effects_planned ||
\t    !mt6797_a72_effects_empty(effects) ||
\t    arm64_late_cpu_target_impl_override_active())
\t\treturn -EINVAL;''',
        '''\tif (!plan || !effects || plan->abi != ARM64_LATE_CPU_PLAN_ABI ||
\t    !plan->local_caps_planned || plan->effects_planned ||
\t    !mt6797_a72_effects_empty(effects) ||
\t    arm64_late_cpu_target_impl_override_active())
\t\treturn mt6797_a72_effect_diagnostic("preconditions", -1,
\t\t\t\t\t\t   -EINVAL);''',
    ),
    (
        '''\t    plan->evidence.system_cap.ssbs > 1)
\t\treturn -EAGAIN;''',
        '''\t    plan->evidence.system_cap.ssbs > 1)
\t\treturn mt6797_a72_effect_diagnostic("system-evidence", -1,
\t\t\t\t\t\t   -EAGAIN);''',
    ),
    (
        '''\t    plan->evidence.system_cap.bhb_system_method)
\t\treturn -EOPNOTSUPP;''',
        '''\t    plan->evidence.system_cap.bhb_system_method)
\t\treturn mt6797_a72_effect_diagnostic("system-policy", -1,
\t\t\t\t\t\t   -EOPNOTSUPP);''',
    ),
    (
        '''\tif (!mt6797_a72_policy_equal(&plan->evidence.target_policy[0],
\t\t\t\t     &plan->evidence.target_policy[1]))
\t\treturn -EOPNOTSUPP;''',
        '''\tif (!mt6797_a72_policy_equal(&plan->evidence.target_policy[0],
\t\t\t\t     &plan->evidence.target_policy[1]))
\t\treturn mt6797_a72_effect_diagnostic("policy-pair", -1,
\t\t\t\t\t\t   -EOPNOTSUPP);''',
    ),
    (
        '''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
\tif (!arm64_late_cpu_expected_pair_complete(plan))
\t\treturn -EAGAIN;
#endif''',
        '''#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
\tif (!arm64_late_cpu_expected_pair_complete(plan))
\t\treturn mt6797_a72_effect_diagnostic("expected-pair", -1,
\t\t\t\t\t\t   -EAGAIN);
#endif''',
    ),
    (
        '''#endif
\t\tif (ret)
\t\t\treturn ret;
\t\tif (!mt6797_a72_effect_state_matches_cap(''',
        '''#endif
\t\tif (ret)
\t\t\treturn mt6797_a72_effect_diagnostic("target-effects",
\t\t\t\t\t\t\t   target, ret);
\t\tif (!mt6797_a72_effect_state_matches_cap(''',
    ),
    (
        '''\t\t    !mt6797_a72_effect_state_matches_cap(
\t\t\t    plan, target, ARM64_SPECTRE_V4,
\t\t\t    effects->target[target].spectre_v4_state))
\t\t\treturn -EINVAL;''',
        '''\t\t    !mt6797_a72_effect_state_matches_cap(
\t\t\t    plan, target, ARM64_SPECTRE_V4,
\t\t\t    effects->target[target].spectre_v4_state))
\t\t\treturn mt6797_a72_effect_diagnostic("target-v2-v4-match",
\t\t\t\t\t\t\t   target, -EINVAL);''',
    ),
    (
        '''\t\tif (ret)
\t\t\treturn ret;
#endif
\t\tif (!mt6797_a72_effect_state_matches_cap(''',
        '''\t\tif (ret)
\t\t\treturn mt6797_a72_effect_diagnostic("target-bhb-effects",
\t\t\t\t\t\t\t   target, ret);
#endif
\t\tif (!mt6797_a72_effect_state_matches_cap(''',
    ),
    (
        '''\t\tif (!mt6797_a72_effect_state_matches_cap(
\t\t\t    plan, target, ARM64_SPECTRE_BHB,
\t\t\t    effects->target[target].bhb_mitigation_state))
\t\t\treturn -EINVAL;''',
        '''\t\tif (!mt6797_a72_effect_state_matches_cap(
\t\t\t    plan, target, ARM64_SPECTRE_BHB,
\t\t\t    effects->target[target].bhb_mitigation_state))
\t\t\treturn mt6797_a72_effect_diagnostic("target-bhb-match",
\t\t\t\t\t\t\t   target, -EINVAL);''',
    ),
    (
        '''\t\tif (!mt6797_a72_v2_effect_equal(
\t\t\t    &effects->target[first_target],
\t\t\t    &effects->target[target]))
\t\t\treturn -EOPNOTSUPP;''',
        '''\t\tif (!mt6797_a72_v2_effect_equal(
\t\t\t    &effects->target[first_target],
\t\t\t    &effects->target[target]))
\t\t\treturn mt6797_a72_effect_diagnostic("v2-pair", target,
\t\t\t\t\t\t\t   -EOPNOTSUPP);''',
    ),
    (
        '''\t\tif (!mt6797_a72_v4_effect_equal(
\t\t\t    &effects->target[first_target],
\t\t\t    &effects->target[target]))
\t\t\treturn -EOPNOTSUPP;''',
        '''\t\tif (!mt6797_a72_v4_effect_equal(
\t\t\t    &effects->target[first_target],
\t\t\t    &effects->target[target]))
\t\t\treturn mt6797_a72_effect_diagnostic("v4-pair", target,
\t\t\t\t\t\t\t   -EOPNOTSUPP);''',
    ),
    (
        '''\t\tif (!mt6797_a72_bhb_effect_equal(
\t\t\t    &effects->target[first_target],
\t\t\t    &effects->target[target]))
\t\t\treturn -EOPNOTSUPP;''',
        '''\t\tif (!mt6797_a72_bhb_effect_equal(
\t\t\t    &effects->target[first_target],
\t\t\t    &effects->target[target]))
\t\t\treturn mt6797_a72_effect_diagnostic("bhb-pair", target,
\t\t\t\t\t\t\t   -EOPNOTSUPP);''',
    ),
    (
        '''\t\tif (ret)
\t\t\treturn ret;
\t\teffects->bhb.system_method |= late_bhb_system_method;''',
        '''\t\tif (ret)
\t\t\treturn mt6797_a72_effect_diagnostic("bhb-system-method",
\t\t\t\t\t\t\t   first_target, ret);
\t\teffects->bhb.system_method |= late_bhb_system_method;''',
    ),
    (
        '''\teffects->speculative_at_finalization =
\t\ttest_bit(ARM64_WORKAROUND_SPECULATIVE_AT,
\t\t\t plan->target_local_caps);

\treturn 0;''',
        '''\teffects->speculative_at_finalization =
\t\ttest_bit(ARM64_WORKAROUND_SPECULATIVE_AT,
\t\t\t plan->target_local_caps);

\treturn mt6797_a72_effect_diagnostic("complete", -1, 0);''',
    ),
)

CORE_REPLACEMENTS = (
    (
        '''\tif (!draft || !profile || !profile->derive_effects ||
\t    !draft->local_caps_planned || draft->effects_planned ||
\t    !late_cpu_effect_plan_empty(&draft->effects))
\t\treturn -EINVAL;''',
        '''\tif (!draft || !profile || !profile->derive_effects ||
\t    !draft->local_caps_planned || draft->effects_planned ||
\t    !late_cpu_effect_plan_empty(&draft->effects)) {
\t\tpr_info("ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=preconditions ret=%d\\n",
\t\t\t-EINVAL);
\t\treturn -EINVAL;
\t}''',
    ),
    (
        '''\tret = profile->derive_effects(draft, &effects);
\tif (ret)
\t\treturn ret;
\tret = validate_late_cpu_effect_plan(draft, profile, &effects);
\tif (ret)
\t\treturn ret;

\tdraft->effects = effects;
\tdraft->effects_planned = 1;
\treturn 0;''',
        '''\tret = profile->derive_effects(draft, &effects);
\tif (ret) {
\t\tpr_info("ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=derive ret=%d\\n",
\t\t\tret);
\t\treturn ret;
\t}
\tret = validate_late_cpu_effect_plan(draft, profile, &effects);
\tif (ret) {
\t\tpr_info("ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=validate ret=%d\\n",
\t\t\tret);
\t\treturn ret;
\t}

\tdraft->effects = effects;
\tdraft->effects_planned = 1;
\tpr_info("ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=complete ret=0\\n");
\treturn 0;''',
    ),
)

STAGES = (
    "preconditions", "system-evidence", "system-policy", "policy-pair",
    "expected-pair", "target-effects", "target-v2-v4-match",
    "target-bhb-effects", "target-bhb-match", "v2-pair", "v4-pair",
    "bhb-pair", "bhb-system-method", "complete",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} count changed: {count}")
    return text.replace(old, new, 1)


def function_slice(text: str, start: str, end: str, label: str) -> tuple[str, str, str]:
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"{label} boundary changed")
    before, rest = text.split(start, 1)
    body, after = rest.split(end, 1)
    return before, start + body, end + after


def validate_parent(root: Path) -> None:
    for target, expected in PARENT_SHA256.items():
        path = root / target
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"unsafe or missing source: {target}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"parent changed for {target}: {actual}")
    mt = (root / MT_TARGET).read_text(encoding="utf-8")
    core = (root / CORE_TARGET).read_text(encoding="utf-8")
    if "A72_EFFECT_DERIVE_V1" in mt or "ARM64_LATE_CPU_EFFECT_PLAN_V1" in core:
        raise SystemExit("stage ledger already present")
    function_slice(mt, MT_START, MT_END, "MT6797 derivation")
    function_slice(core, CORE_START, CORE_END, "core planner")


def apply(root: Path) -> None:
    validate_parent(root)
    mt_path = root / MT_TARGET
    mt = mt_path.read_text(encoding="utf-8")
    before, function, after = function_slice(
        mt, MT_START, MT_END, "MT6797 derivation"
    )
    function = MT_HELPER + function
    for index, (old, new) in enumerate(MT_REPLACEMENTS, 1):
        function = replace_once(function, old, new, f"MT replacement {index}")
    mt_path.write_text(before + function + after, encoding="utf-8")

    core_path = root / CORE_TARGET
    core = core_path.read_text(encoding="utf-8")
    before, function, after = function_slice(
        core, CORE_START, CORE_END, "core planner"
    )
    for index, (old, new) in enumerate(CORE_REPLACEMENTS, 1):
        function = replace_once(function, old, new, f"core replacement {index}")
    core_path.write_text(before + function + after, encoding="utf-8")
    validate_result(root)


def validate_result(root: Path) -> None:
    mt = (root / MT_TARGET).read_text(encoding="utf-8")
    core = (root / CORE_TARGET).read_text(encoding="utf-8")
    if mt.count("A72_EFFECT_DERIVE_V1") != 1:
        raise SystemExit("MT6797 diagnostic format count changed")
    if mt.count("mt6797_a72_effect_diagnostic(") != len(STAGES) + 1:
        raise SystemExit("MT6797 diagnostic call count changed")
    for stage in STAGES:
        if mt.count(f'"{stage}"') != 1:
            raise SystemExit(f"MT6797 stage count changed: {stage}")
    if core.count("ARM64_LATE_CPU_EFFECT_PLAN_V1") != 4:
        raise SystemExit("core diagnostic format count changed")
    for stage in ("preconditions", "derive", "validate", "complete"):
        if core.count(f"stage={stage}") != 1:
            raise SystemExit(f"core stage count changed: {stage}")
    if mt.count("mt6797_a72_derive_effects(") != 1:
        raise SystemExit("MT6797 derivation call graph changed")
    if core.count("arm64_plan_late_cpu_effects(") != 1:
        raise SystemExit("core planner call graph changed")
