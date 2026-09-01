#!/usr/bin/env bash

# Source-pin the production CPU9 assembler and retarget only the exact
# progress-ledger diagnostic package, provenance leaf, and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1ea0f113917809ebd121a9aa9b906e9a0ed01dc43c03d15d1bde6e130435bf91
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-cpu9-progress.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("479f938f96bf34e49b3adef25b844d23d6fb2c4d",
     "630350185c9126f2c96be7295216c5ff1ee08c83", 1),
    ("39074a71cd485c493f530a23858b9be1f37cdca5b35ca0c95f291357e8f62e08",
     "c4e84c90a9843b8d5a7beaf8ce6c7874d1d8e972f14fa91a4e837800ecd0b5f6", 1),
    ("01830c2f38773d501117501e22f55bb12f0c1740f1dac00a3a6993295684c364",
     "4c4f43328c6c824045d118510183b1d7f2fdacd92ddeaf4f6b75a59ad76cf9b8", 1),
    ("3ffcd08ec15642de4470a00d7fdf495318741cfb0bce1c65d13f5bd80001d56b",
     "d450a5135a9689b40699273d09b74cadd873088317603d345ccc66cd25d027a8", 1),
    ("0b2781ca1d8dcf195e7b3f786da0a0a6f2306a391f9bacb7da3f0448e4af7fb1",
     "a657dd5c033d18b3d7638875e6603c6c9486fd9b13c2f9d9f4a9c60c82875534", 1),
    ("59f069542f20c63452eaa55bd4576def05f469bbf0886abf4536c7b6583b2a70",
     "e262795a456a933a16b0658edb699bb3ea444e04bfa842488cf04d794f545a28", 1),
    ("1f66ecf1d94a927d30be74c7ac70ea5f89ad7ebee4aefa8f9f28b75c787a8950",
     "e36f8c48e29548f2156e8155fa0ef1136e9b2be17eaadb76044e554898e91f54", 1),
    ("603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b",
     "08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd", 1),
    ("dd4b935862ce12d7bc2179aba3a81621ab4bdbcfdb069ad9977695a136315ef2",
     "85d3b591cdee4635cf0e5b889011459a4cb7e48f4ddd3ac2df0c20720e1c8833", 1),
    ("fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468",
     "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72", 1),
    ('"readonly RAW_SIZE=6963200"', '"readonly RAW_SIZE=6965248"', 1),
    ("gemini-mt6797-a72-cpu9-controller.boot.img",
     "gemini-mt6797-a72-cpu9-progress.boot.img", 1),
    ("c1 9c 8f 40 26 e8 9f 8f 41 a 76 79 14 d5 e2 26 5c e5 24 2d fb 4c c2 5e e1 88 16 41 da f0 48 a3",
     "ed 3a 4b f0 85 10 bd d5 c1 7 c1 10 18 3b 1c e9 85 df c5 59 4c 8a fa e5 4b df fe 0 6f b5 66 6", 1),
    ("readonly PROFILE=a72-cpu9-controller-candidate",
     "readonly PROFILE=a72-cpu9-progress-candidate", 1),
    ("readonly RELEASE=7.1.3-gemini-cpu9-controller",
     "readonly RELEASE=7.1.3-gemini-cpu9-progress", 1),
    ('CONFIG_LOCALVERSION="-gemini-cpu9-controller"',
     'CONFIG_LOCALVERSION="-gemini-cpu9-progress"', 1),
    ("for symbol in ARM64_MT6797_A72_CPU9_MEMBERSHIP PSTORE_GEMINI_CPU9_TRANSITION_LEDGER MTK_MT6797_A72_CPU9_EXECUTOR",
     "for symbol in ARM64_MT6797_A72_CPU9_MEMBERSHIP PSTORE_GEMINI_CPU9_TRANSITION_LEDGER PSTORE_GEMINI_CPU9_PROGRESS_LEDGER MTK_MT6797_A72_CPU9_EXECUTOR", 1),
    ("production CPU9 symbol is absent",
     "production CPU9 diagnostic symbol is absent", 1),
    ("grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' \"$config\" || die 'live trigger is absent from current Image'\ngrep -q '^CONFIG_KUNIT=y$' \"$config\" && die 'KUnit leaked into production Image'",
     "grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' \"$config\" || die 'live trigger is absent from current Image'\ngrep -qx '# CONFIG_PSTORE_GEMINI_ADMISSION_TRACE is not set' \"$config\" || die 'legacy admission trace was not replaced'\ngrep -q '^CONFIG_KUNIT=y$' \"$config\" && die 'KUnit leaked into production Image'", 1),
    ("PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST",
     "PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST", 1),
    ("experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
     "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor\\\\nvariant=cpu9-progress-ledger", 1),
    ("validation=cpu9-controller-package",
     "validation=cpu9-progress-package", 1),
    ("dt_semantics=unchanged-serviceability-admission-tree-plus-current-CPU9-package-provenance-leaf",
     "dt_semantics=unchanged-serviceability-admission-tree-plus-CPU9-progress-package-provenance-leaf", 1),
    ('output_name="candidate-a72-cpu9-controller-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-progress-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-cpu9-controller-build",
     "validation=a72-cpu9-progress-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress candidate derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
