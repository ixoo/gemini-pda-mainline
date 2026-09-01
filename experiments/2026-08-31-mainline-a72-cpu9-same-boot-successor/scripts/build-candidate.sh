#!/usr/bin/env bash

# Source-pin the proven provenance/serviceability assembler and retarget its
# exact package, production CPU9 configuration, provenance leaf, and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6296d289d39e508b2d61b67d4df8ddde1e704c5bba555d2e7e7d350665dc5a67
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-cpu9-controller.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
extra = '''replacements = (
    ("readonly PROFILE=a72-admission-live-trigger-candidate",
     "readonly PROFILE=a72-cpu9-controller-candidate", 1),
    ("readonly RELEASE=7.1.3-gemini-a72-admission-live",
     "readonly RELEASE=7.1.3-gemini-cpu9-controller", 1),
    (''' + repr('''grep -qx 'CONFIG_LOCALVERSION="-gemini-a72-admission-live"' "$config" || die 'local version changed'
grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' "$config" || die 'live trigger is absent from current Image' '''.rstrip()) + ''', ''' + repr('''grep -qx 'CONFIG_LOCALVERSION="-gemini-cpu9-controller"' "$config" || die 'local version changed'
for symbol in ARM64_MT6797_A72_CPU9_MEMBERSHIP PSTORE_GEMINI_CPU9_TRANSITION_LEDGER MTK_MT6797_A72_CPU9_EXECUTOR MTK_MT6797_A72_CPU9_BINDER MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER; do
    grep -qx "CONFIG_${symbol}=y" "$config" || die "production CPU9 symbol is absent: $symbol"
done
grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' "$config" || die 'live trigger is absent from current Image'
grep -q '^CONFIG_KUNIT=y$' "$config" && die 'KUnit leaked into production Image'
for symbol in PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER_KUNIT_TEST; do
    grep -q "^CONFIG_${symbol}=y$" "$config" && die "CPU9 KUnit suite leaked into production Image: $symbol"
done''') + ''', 1),
'''
if text.count("replacements = (\n") != 1:
    raise SystemExit("unsafe CPU9 candidate derivation: replacement table changed")
text = text.replace("replacements = (\n", extra, 1)
replacements = (
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99",
     "479f938f96bf34e49b3adef25b844d23d6fb2c4d", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c",
     "39074a71cd485c493f530a23858b9be1f37cdca5b35ca0c95f291357e8f62e08", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce",
     "01830c2f38773d501117501e22f55bb12f0c1740f1dac00a3a6993295684c364", 1),
    ("9b9118fd53b7b290803c52745b5fb8ab2559c0ba83765d30b6111d1bd01914d7",
     "3ffcd08ec15642de4470a00d7fdf495318741cfb0bce1c65d13f5bd80001d56b", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b",
     "0b2781ca1d8dcf195e7b3f786da0a0a6f2306a391f9bacb7da3f0448e4af7fb1", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda",
     "59f069542f20c63452eaa55bd4576def05f469bbf0886abf4536c7b6583b2a70", 1),
    ("b17e485aa14119a7c56bea6ccc657b7d583ee1069642035b1201ae8848172634",
     "1f66ecf1d94a927d30be74c7ac70ea5f89ad7ebee4aefa8f9f28b75c787a8950", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2",
     "603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa",
     "dd4b935862ce12d7bc2179aba3a81621ab4bdbcfdb069ad9977695a136315ef2", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a",
     "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468", 1),
    ('"readonly RAW_SIZE=6948864"', '"readonly RAW_SIZE=6963200"', 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img",
     "gemini-mt6797-a72-cpu9-controller.boot.img", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a",
     "c1 9c 8f 40 26 e8 9f 8f 41 a 76 79 14 d5 e2 26 5c e5 24 2d fb 4c c2 5e e1 88 16 41 da f0 48 a3", 1),
    ("experiment=2026-08-30-mainline-a72-provenance-serviceability-composition",
     "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor", 1),
    (r"candidate_cpu8_request_paths=1\\ncpu8_requests=0\\ncpu9_requests=0",
     r"candidate_cpu8_request_paths=1\\ncandidate_cpu9_request_paths=1\\ncpu8_requests_during_validation=0\\ncpu9_requests_during_validation=0", 1),
    ("validation=provenance-serviceability-package",
     "validation=cpu9-controller-package", 1),
    ("dt_semantics=serviceability-admission-tree-plus-package-exact-provenance-leaf",
     "dt_semantics=unchanged-serviceability-admission-tree-plus-current-CPU9-package-provenance-leaf", 1),
    ('output_name="candidate-a72-provenance-serviceability-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-controller-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-provenance-serviceability-build",
     "validation=a72-cpu9-controller-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 candidate derivation: expected {count}, "
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
