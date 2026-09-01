#!/usr/bin/env bash

# Source-pin the production CPU9 assembler and retarget only the exact
# configuration-identity repair package, provenance leaf, and container.
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

derived=$(mktemp "$script_dir/.derived-build-a72-cpu9-config-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("479f938f96bf34e49b3adef25b844d23d6fb2c4d",
     "45582eea878418e64cacf5a67d9b0b92821a25ad", 1),
    ("39074a71cd485c493f530a23858b9be1f37cdca5b35ca0c95f291357e8f62e08",
     "aee66bcce2413083638d64be3262aab1d3c92452814967d03d9a7a853c32761c", 1),
    ("01830c2f38773d501117501e22f55bb12f0c1740f1dac00a3a6993295684c364",
     "192a61b071a8c62ad976b058b53b93edfde0f3747ceefcece36309125edff2fe", 1),
    ("59f069542f20c63452eaa55bd4576def05f469bbf0886abf4536c7b6583b2a70",
     "a7732de1428e924187788fb2f971035f0beb4868feee6713bd10d9876e44265f", 1),
    ("1f66ecf1d94a927d30be74c7ac70ea5f89ad7ebee4aefa8f9f28b75c787a8950",
     "5effbb29c9b04aae9bf159d3923f2948c9f308593510bfa4f2ae5f7301d62b6a", 1),
    ("603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b",
     "ca7e95162c9e222d47991f6580682354cbb445d994a954950455ca5e6b9c80c3", 1),
    ("dd4b935862ce12d7bc2179aba3a81621ab4bdbcfdb069ad9977695a136315ef2",
     "e7ea9113a5288990ea54205339ea67b18056fcb4461b5dbecaf2ab45e96a1e15", 1),
    ("fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468",
     "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562", 1),
    ("gemini-mt6797-a72-cpu9-controller.boot.img",
     "gemini-mt6797-a72-cpu9-config-identity-repair.boot.img", 1),
    ("c1 9c 8f 40 26 e8 9f 8f 41 a 76 79 14 d5 e2 26 5c e5 24 2d fb 4c c2 5e e1 88 16 41 da f0 48 a3",
     "51 bc d3 55 84 f2 e2 f7 ce 76 b1 4b 11 92 e7 a2 2a 42 23 43 53 e7 2d a7 f7 1f 3e 87 19 db 5b cb", 1),
    ("experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor",
     "experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor\\\\nrepair=production-config-input-identity", 1),
    ("validation=cpu9-controller-package",
     "validation=cpu9-config-identity-repair-package", 1),
    ("dt_semantics=unchanged-serviceability-admission-tree-plus-current-CPU9-package-provenance-leaf",
     "dt_semantics=unchanged-serviceability-admission-tree-plus-repaired-CPU9-package-provenance-leaf", 1),
    ('output_name="candidate-a72-cpu9-controller-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-config-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-cpu9-controller-build",
     "validation=a72-cpu9-config-identity-repair-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired CPU9 candidate derivation: expected {count}, "
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
