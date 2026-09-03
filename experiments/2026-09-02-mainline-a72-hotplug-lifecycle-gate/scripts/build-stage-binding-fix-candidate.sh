#!/usr/bin/env bash

# Source-pin the diagnostic candidate builder and retarget its exact inputs to
# the symbolic stage-binding-fix production package and composed DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4138434d0929ca3894ba8b092031d1e54e7a4046b26f2bd874297a1e1f1e7afb
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/build-postsuccess-diagnostic-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source post-success diagnostic builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-stage-binding-fix.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("35170505f3c42fcdfa6a79c843f8492b9da0fd52",
     "8ae7643c3be90349fbad17e97c9babbb75747f12", 1),
    ("084c2e8176b86a2037d8f2bcf11006daaf211c794694df0f2be2935d65e43b33",
     "0314890897c3c4ed60777a3b0e233670c01e3bbb9add3d662d1efb51d85ca2d3", 1),
    ("84b221e659586e8fd56f805abc0b2a2618d9737aac6f51865d32fc80a02b55ce",
     "5ca5ea6da69b8a4625a3e94b395c15d2f5aeb12f9c01348ba3b5ebab40d5c77f", 1),
    ("9094abdc86db61ef0c4a06670cbce1ef350a8f0b02817fd3b9e5621e2105f89a",
     "3bd51a38ba7931a66d39db455aaa08b587c8b5d8b22368c565f5473c2b0c84e4", 1),
    ("27b5fc867d5db56246a84a42e25ea103da6bb3d6904ebd19732e00c2f6538122",
     "49484d01231f91ee008b575b2ed6cda45c3c2c845ebfd87c5b7061e43a9a6424", 1),
    ("959247f1300578b1ec1652eb4cb1d9a36d7c91c6a82228ccd6a2afb9f136136b",
     "ecf278518608e4fa17c05b933a75c55ec4a31fdb4ceff10bce784754822e834c", 1),
    ("fd015493b0e1df550d2da500b82e9009c96dbcabe867c411846d8dd06e4ae14f",
     "09c4f0b7ebc733286446b586ce397f7f93ded832c4ccd96e48077e363bb995ae", 1),
    ("fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671",
     "c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271", 1),
    ("gemini-a72post", "gemini-a72sym", 1),
    ("gemini-mt6797-a72-postsuccess-diagnostic.boot.img",
     "gemini-mt6797-a72-stage-binding-fix.boot.img", 1),
    ("4f 53 65 b9 7c ab d4 4e 8e 42 75 de f7 88 4b cb 35 33 ca 4f 6 0 12 67 d4 d7 b3 f2 31 9d 5b e4",
     "d4 94 6 2 e7 ad 9c bc 94 73 76 bf b9 dc 42 22 ef 5a 67 1f aa 15 eb 42 a8 21 df 18 52 af 9b a4", 1),
    ("candidate-a72-postsuccess-diagnostic-", "candidate-a72-stage-binding-fix-", 1),
    ("validation=a72-postsuccess-diagnostic-package",
     "validation=a72-stage-binding-fix-package", 1),
    ("validation=a72-postsuccess-diagnostic-build",
     "validation=a72-stage-binding-fix-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding candidate derivation: expected {count}, "
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
