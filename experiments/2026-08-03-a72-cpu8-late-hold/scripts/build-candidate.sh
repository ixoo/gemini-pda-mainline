#!/usr/bin/env bash

# Source-pin and mechanically derive the late-hold Android-v0 candidate builder
# from the accepted held-online builder.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod grep jq mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-02-a72-cpu8-held-online/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=65c39fa45b1f76fb85780473feb3b675bd5e6647934e68be2761bc823c07e0fe
[[ -f "$source_builder" && ! -L "$source_builder" &&
	"$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_BUILDER_SHA256" ]] ||
	die 'source held-online candidate builder changed'

bundle=
arguments=("$@")
for ((index = 0; index < ${#arguments[@]}; index++)); do
	if [[ "${arguments[index]}" == --bundle && $((index + 1)) -lt ${#arguments[@]} ]]; then
		bundle=${arguments[index + 1]}
	fi
done
if [[ -n "$bundle" ]]; then
	[[ -f "$bundle/provenance/build.json" && ! -L "$bundle/provenance/build.json" ]] ||
		die 'late compile provenance is missing or unsafe'
	[[ "$(jq -er '.late_patchset_sha256' "$bundle/provenance/build.json")" == \
		f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91 ]] ||
		die 'late-hold patchset changed'
	[[ "$(jq -er '.purpose' "$bundle/provenance/build.json")" == \
		late-hold-compile-review-only ]] || die 'late compile purpose changed'
fi

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-late-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_LATE_SCRIPT_DIR:?missing}"#g;
	s#118ff3cb3e9a2fbee10a44ada748e46bbe9b5312#cc20c4a57fa467ee803d0a4b5b31e5babb7b52b5#g;
	s#9158af17b17e483ec68257378e5c4bd923b254e7242b5ba338f1324eec5f960b#9827c9c8c66501a913e38c255aa8a15e6eaf784f3e7c57d032d76809e80710cf#g;
	s#53046cf314f76f213abafa53a1e79758ff835941d78a47ecc878d0a2e1ad3789#53ba2e4dbc204962e7b195bbda80c5e592375878105702731420b24f9466c475#g;
	s#936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018#2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af#g;
	s#readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3#readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3\nreadonly LATE_PATCHSET_SHA256=f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91#g;
	s#held-online-compile-review-only#late-hold-compile-review-only#g;
	s#\.gemian-a72-held#\.gemian-a72-late#g;
	s#gemian-a72-cpu8-held-online\.boot\.img#gemian-a72-cpu8-late-hold.boot.img#g;
	s#experiment=2026-08-02-a72-cpu8-held-online#experiment=2026-08-03-a72-cpu8-late-hold#g;
	s#printf '\''held_patchset_sha256=%s\\n'\'' "\$HELD_PATCHSET_SHA256"#printf '\''held_patchset_sha256=%s\\n'\'' "\$HELD_PATCHSET_SHA256"\n  printf '\''late_patchset_sha256=%s\\n'\'' "\$LATE_PATCHSET_SHA256"#g;
	s#gemian-a72-cpu8-held-online-\$\{raw_sha256:0:12\}#gemian-a72-cpu8-late-hold-\${raw_sha256:0:12}#g;
	s#validation=gemian-a72-cpu8-held-online-candidate#validation=gemian-a72-cpu8-late-hold-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"

for token in \
	'REPOSITORY_COMMIT=cc20c4a57fa467ee803d0a4b5b31e5babb7b52b5' \
	'LATE_PATCHSET_SHA256=f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91' \
	'KERNEL_SHA256=9827c9c8c66501a913e38c255aa8a15e6eaf784f3e7c57d032d76809e80710cf' \
	'EXPECTED_RAW_SHA256=53ba2e4dbc204962e7b195bbda80c5e592375878105702731420b24f9466c475' \
	'EXPECTED_PADDED_SHA256=2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af' \
	'late-hold-compile-review-only' \
	'gemian-a72-cpu8-late-hold-candidate'; do
	grep -Fq "$token" "$derived" || die "derived builder lacks: $token"
done
! grep -Fq 'held-online-compile-review-only' "$derived" ||
	die 'derived builder retains old compile purpose'
export GEMINI_LATE_SCRIPT_DIR="$script_dir"
"$derived" "$@"
