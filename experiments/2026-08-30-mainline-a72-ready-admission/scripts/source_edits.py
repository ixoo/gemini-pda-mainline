#!/usr/bin/env python3
"""Deterministic post-0434 config-off and candidate-identity edits."""

from __future__ import annotations

import hashlib
from pathlib import Path


HEADER = "arch/arm64/include/asm/late_cpu_profile.h"
PROFILE = "arch/arm64/kernel/mt6797_psci.c"
PARENT_HASHES = {
    HEADER: "a6bb7d236356cbccb1d29e751f3360f2529b2c04853249179ca87b13779d7bdc",
    PROFILE: "aeb42a1f6ea38a28dbf5afe9195305f2188cad332dda13cef3e2430993f32986",
}

CANDIDATE_CONFIG_INPUTS_SHA256 = (
    "5968c24f1904c0559dea25480c41fbc7"
    "db49e822dc3600d1bdd7632330853f40"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"edit anchor count changed for {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"parent source absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"parent source changed: {relative}: {actual} != {expected}")


HEADER_SCOPE_ANCHOR = r'''struct arm64_late_cpu_profile {
	const char *name;
	u8 target_count;
	enum arm64_late_cpu_cap_state
	(*classify_local_cap)(const struct arm64_cpu_capabilities *cap,
			      const struct arm64_cpu_capabilities *match,
			      const struct arm64_late_cpu_evidence *evidence,
			      unsigned int target);
	int (*validate_plan)(const struct arm64_late_cpu_plan *plan);
	int (*derive_effects)(const struct arm64_late_cpu_plan *plan,
			      struct arm64_late_cpu_effect_plan *effects);
	/* Expected-only production input or an explicit FIXTURE; never RUNTIME. */
	int (*prepare)(struct arm64_late_cpu_evidence *evidence,
		       const struct cpumask *registered_targets);
	int (*verify_system)(const struct arm64_late_cpu_plan *plan,
			     const struct arm64_late_cpu_receipt *receipt);
	int (*finalize_user)(const struct arm64_late_cpu_plan *plan,
			     const struct arm64_late_cpu_receipt *receipt);
};

#ifdef CONFIG_ARM64_LATE_CPU_PROFILE
'''

HEADER_SCOPE_FINAL = HEADER_SCOPE_ANCHOR.replace(
    "\n#ifdef CONFIG_ARM64_LATE_CPU_PROFILE\n",
    "\nint arm64_late_cpu_validate_boot_caps(void);\n\n"
    "#ifdef CONFIG_ARM64_LATE_CPU_PROFILE\n",
)

HEADER_ENABLED_ANCHOR = r'''bool arm64_late_cpu_expected_pair_complete(const struct arm64_late_cpu_plan *plan);
int arm64_late_cpu_validate_boot_caps(void);
int arm64_validate_late_cpu_preflight(unsigned int cpu);
'''

HEADER_ENABLED_FINAL = r'''bool arm64_late_cpu_expected_pair_complete(const struct arm64_late_cpu_plan *plan);
int arm64_validate_late_cpu_preflight(unsigned int cpu);
'''

HEADER_STUB_ANCHOR = r'''static inline int
arm64_validate_late_cpu_expected_target(unsigned int cpu)
{
	return 0;
}
'''

HEADER_STUB_FINAL = r'''static inline int
arm64_validate_late_cpu_preflight(unsigned int cpu)
{
	return 0;
}

static inline int
arm64_validate_late_cpu_expected_target(unsigned int cpu)
{
	return 0;
}
'''

PROFILE_IDENTITY_ANCHOR = r'''#else
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
	0x699f14786e1d64eb, 0x3811f0b6c481c31d,
	0x9e0e77fc96b64eb4, 0xd12ebbbfde3b23b0,
};
#endif
'''

PROFILE_IDENTITY_FINAL = r'''#else
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
	0x5968c24f1904c055, 0x9dea25480c41fbc7,
	0xdb49e822dc3600d1, 0xbdd7632330853f40,
};
#endif
'''


def apply_config_off(root: Path) -> None:
    validate_parent(root)
    header = root / HEADER
    replace_once(header, HEADER_SCOPE_ANCHOR, HEADER_SCOPE_FINAL)
    replace_once(header, HEADER_ENABLED_ANCHOR, HEADER_ENABLED_FINAL)
    replace_once(header, HEADER_STUB_ANCHOR, HEADER_STUB_FINAL)


def apply_identity(root: Path) -> None:
    replace_once(
        root / PROFILE, PROFILE_IDENTITY_ANCHOR, PROFILE_IDENTITY_FINAL
    )


if __name__ == "__main__":
    raise SystemExit("source_edits.py is imported by the generator")
